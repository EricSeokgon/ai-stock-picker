# SPEC-STOCK-021: 뉴스피드·AI 시장 템포 서비스 레이어
# REQ-NEWS-SENT-*, REQ-NEWS-FEED-*, REQ-NEWS-FETCH-*, REQ-NEWS-CACHE-*
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from stock_picker.analysis.sentiment_label import score_to_label
from stock_picker.api.schemas import MarketSentimentResponse, StockNewsItem
from stock_picker.collectors.service import CollectorService
from stock_picker.analysis.worker import AnalysisWorker
from stock_picker.db.models import Article, AnalysisResult, StockMention

logger = logging.getLogger(__name__)

# @MX:NOTE: [AUTO] 캐시 키 상수 — TTL 1800s(30분) 유지
# @MX:SPEC: SPEC-STOCK-021 REQ-NEWS-CACHE-001/002
_CACHE_TTL = 1800
_MARKET_SENTIMENT_CACHE_KEY = "market_sentiment:24h"
_STOCK_NEWS_CACHE_PREFIX = "news:"


async def get_market_sentiment(
    *,
    redis: Any,
    db: AsyncSession,
) -> MarketSentimentResponse:
    """24시간 분석 기사 기반 시장 전체 감성 집계.

    REQ-NEWS-SENT-001/003/004 구현.
    Redis 캐시 우선, 미스 시 DB 집계, 결과를 Redis에 저장.
    Redis 장애 시 DB fallback (REQ-NEWS-CACHE-003).
    """
    # 캐시 조회 (장애 시 무시)
    cached: str | None = None
    try:
        cached = await redis.get(_MARKET_SENTIMENT_CACHE_KEY)
    except Exception:
        logger.warning("Redis get 실패 — DB fallback 사용")

    if cached is not None:
        data = json.loads(cached)
        return MarketSentimentResponse(**data)

    # DB 집계: 최근 24시간 분석 완료 기사
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    stmt = (
        select(
            func.avg(AnalysisResult.sentiment_score).label("avg_score"),
            func.count(
                case((AnalysisResult.sentiment == "positive", 1))
            ).label("positive"),
            func.count(
                case((AnalysisResult.sentiment == "negative", 1))
            ).label("negative"),
            func.count(
                case((AnalysisResult.sentiment == "neutral", 1))
            ).label("neutral"),
            func.count(AnalysisResult.id).label("total"),
        )
        .join(Article, AnalysisResult.article_id == Article.id)
        .where(Article.collected_at >= cutoff)
    )

    result = await db.execute(stmt)
    row = result.fetchone()

    avg_score: float | None = float(row.avg_score) if row.avg_score is not None else None
    label: str | None = score_to_label(avg_score)
    positive = int(row.positive) if row.positive else 0
    negative = int(row.negative) if row.negative else 0
    neutral = int(row.neutral) if row.neutral else 0
    total = int(row.total) if row.total else 0

    as_of = datetime.now(timezone.utc)
    response = MarketSentimentResponse(
        avg_score=avg_score,
        label=label,
        positive=positive,
        negative=negative,
        neutral=neutral,
        total=total,
        as_of=as_of,
    )

    # 캐시 저장 (장애 시 무시)
    try:
        payload = json.dumps({
            "avg_score": avg_score,
            "label": label,
            "positive": positive,
            "negative": negative,
            "neutral": neutral,
            "total": total,
            "as_of": as_of.isoformat(),
        })
        await redis.setex(_MARKET_SENTIMENT_CACHE_KEY, _CACHE_TTL, payload)
    except Exception:
        logger.warning("Redis setex 실패 — 캐시 저장 건너뜀")

    return response


async def get_news_by_stock(
    *,
    krx_code: str,
    limit: int,
    redis: Any,
    db: AsyncSession,
) -> list[StockNewsItem]:
    """특정 종목 뉴스 조회 (REQ-NEWS-FEED-002).

    StockMention.krx_code 필터 → Article → AnalysisResult 조인.
    Redis 캐시 우선, 미스 시 DB 조회.
    """
    cache_key = f"{_STOCK_NEWS_CACHE_PREFIX}{krx_code}"

    # 캐시 조회
    cached: str | None = None
    try:
        cached = await redis.get(cache_key)
    except Exception:
        logger.warning("Redis get 실패 — DB fallback 사용")

    if cached is not None:
        items_data = json.loads(cached)
        return [StockNewsItem(**item) for item in items_data]

    # DB 조회: StockMention.krx_code 필터
    stmt = (
        select(Article)
        .join(StockMention, StockMention.article_id == Article.id)
        .where(StockMention.krx_code == krx_code)
        .where(Article.status.in_(["analyzed", "collected"]))
        .options(selectinload(Article.analysis_results))
        .order_by(Article.published_at.desc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    articles = result.scalars().all()

    items: list[StockNewsItem] = []
    for article in articles:
        ar = article.analysis_results[0] if article.analysis_results else None
        items.append(StockNewsItem(
            id=article.id,
            title=article.title,
            source=article.source,
            published_at=article.published_at or datetime.now(timezone.utc),
            url=article.url,
            sentiment=ar.sentiment if ar else None,
            sentiment_score=float(ar.sentiment_score) if ar and ar.sentiment_score is not None else None,
            sentiment_label=ar.sentiment_label if ar else None,
            ai_summary=ar.summary if ar else None,
        ))

    # 캐시 저장
    try:
        payload = json.dumps([item.model_dump(mode="json") for item in items])
        await redis.setex(cache_key, _CACHE_TTL, payload)
    except Exception:
        logger.warning("Redis setex 실패 — 캐시 저장 건너뜀")

    return items


async def trigger_news_fetch(
    *,
    db: AsyncSession,
    redis: Any,
) -> dict[str, int]:
    """수동 뉴스 수집·분석 트리거 (REQ-NEWS-FETCH-001/002/003).

    수집 또는 분석 실패 시 부분 결과 반환 (500 없이).
    """
    collected = 0
    analyzed = 0

    # 수집
    try:
        svc = CollectorService()
        collect_result = await svc.collect_all(db)
        collected = sum(collect_result.values())
    except Exception as e:
        logger.error("뉴스 수집 실패: %s", e)

    # 분석
    try:
        worker = AnalysisWorker()
        analysis_result = await worker.run(db)
        analyzed = analysis_result.get("analyzed", 0)
    except Exception as e:
        logger.error("뉴스 분석 실패: %s", e)

    return {"collected": collected, "analyzed": analyzed}
