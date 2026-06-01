# 추천 엔드포인트 - 당일 Top 10 추천 리스트 반환 + 종목 추천 근거 상세
import json
from datetime import date, datetime, timezone
from typing import Union

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from stock_picker.api.deps import get_cache, get_session
from stock_picker.api.schemas import (
    ContributingNewsItem,
    PreparingResponse,
    RecommendationDetailResponse,
    RecommendationItem,
    RecommendationsResponse,
)
from stock_picker.db.models import AnalysisResult, Article, Recommendation, StockMention
from stock_picker.recommendation.cache import RecommendationCache

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


# @MX:ANCHOR: [AUTO] 추천 조회 API - 프론트엔드 주요 진입점
# @MX:REASON: React 대시보드에서 폴링하는 핵심 엔드포인트 (AC-7, AC-10)


@router.get("", response_model=Union[RecommendationsResponse, PreparingResponse])
async def get_recommendations(
    cache: RecommendationCache = Depends(get_cache),
) -> Union[RecommendationsResponse, PreparingResponse]:
    """당일 추천 리스트 반환.

    Redis 캐시가 존재하면 즉시 반환 (AC-7).
    데이터가 없으면 preparing 상태 반환 (AC-10).
    """
    today = date.today()
    cache_key = f"recommendations:{today.isoformat()}"

    raw = await cache.get(cache_key)

    if raw is None:
        # 데이터 아직 준비 안 됨
        return PreparingResponse(last_updated=None)

    # raw가 list인지 JSON 문자열인지 처리
    if isinstance(raw, str):
        items_data: list = json.loads(raw)
    else:
        items_data = raw

    items = [RecommendationItem(**item) for item in items_data]
    last_updated = datetime.now(tz=timezone.utc)

    return RecommendationsResponse(
        trade_date=today,
        recommendations=items,
        last_updated=last_updated,
    )


@router.get("/{krx_code}", response_model=RecommendationDetailResponse)
async def get_recommendation_detail(
    krx_code: str,
    session: AsyncSession = Depends(get_session),
) -> RecommendationDetailResponse:
    """종목 추천 근거 상세 (REQ-WEB-002, AC-8).

    당일 가장 최근 Recommendation을 조회하고, 해당 종목의 기여 기사를 함께 반환한다.

    Args:
        krx_code: KRX 종목코드
        session: DB 세션 의존성

    Returns:
        RecommendationDetailResponse: 종목 추천 근거 상세

    Raises:
        HTTPException 404: 해당 krx_code의 추천 데이터가 없을 경우
    """
    # 당일 해당 종목의 최근 추천 데이터 조회
    stmt = (
        select(Recommendation)
        .where(Recommendation.krx_code == krx_code)
        .order_by(Recommendation.computed_at.desc())
    )
    result = await session.execute(stmt)
    rec = result.scalar_one_or_none()

    if rec is None:
        raise HTTPException(status_code=404, detail=f"추천 데이터를 찾을 수 없습니다: {krx_code}")

    # 해당 종목의 기여 기사 조회 (StockMention → Article → AnalysisResult)
    news_stmt = (
        select(
            Article.title,
            AnalysisResult.summary,
            AnalysisResult.sentiment,
            Article.published_at,
        )
        .join(StockMention, StockMention.article_id == Article.id)
        .join(AnalysisResult, AnalysisResult.article_id == Article.id)
        .where(StockMention.krx_code == krx_code)
        .order_by(Article.published_at.desc())
        .limit(10)
    )
    news_result = await session.execute(news_stmt)
    news_rows = news_result.all()

    contributing_news = [
        ContributingNewsItem(
            title=row.title,
            summary=row.summary,
            sentiment=row.sentiment,
            published_at=row.published_at or datetime.now(tz=timezone.utc),
        )
        for row in news_rows
    ]

    trade_date = (
        rec.trade_date.date()
        if hasattr(rec.trade_date, "date")
        else rec.trade_date
    )

    return RecommendationDetailResponse(
        krx_code=rec.krx_code,
        trade_date=trade_date,
        total_score=float(rec.total_score),
        sentiment_score=float(rec.sentiment_score),
        volume_score=float(rec.volume_score),
        momentum_score=float(rec.momentum_score),
        anomaly_score=float(rec.anomaly_score),
        reasoning=rec.reasoning or "",
        contributing_news=contributing_news,
    )
