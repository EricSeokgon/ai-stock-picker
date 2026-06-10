# 섹터 트렌드 API (REQ-WEB-003, AC-9, SPEC-STOCK-008)
import json
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from stock_picker.api.deps import get_cache, get_session
from stock_picker.api.schemas import (
    SectorDetailResponse,
    SectorRankingItem,
    SectorRankingResponse,
    SectorStockItem,
    SectorTrendItem,
    SectorTrendsResponse,
)
from stock_picker.db.models import AnalysisResult, Article, SectorTrend, StockMention
from stock_picker.recommendation.cache import RecommendationCache

router = APIRouter(prefix="/sectors", tags=["sectors"])

# 캐시 키 형식
_SECTOR_CACHE_KEY_FORMAT = "sector_trends:{days}"
_SECTOR_RANKING_KEY_FORMAT = "sector_ranking:{sort}:{limit}:{days}"
_SECTOR_DETAIL_KEY_FORMAT = "sector_detail:{sector}:{days}"


@router.get("/trends", response_model=SectorTrendsResponse)
async def get_sector_trends(
    days: int = 7,
    cache: RecommendationCache = Depends(get_cache),
    session: AsyncSession = Depends(get_session),
) -> SectorTrendsResponse:
    """섹터별 트렌드 스코어 시계열 (캐시 우선).

    Args:
        days: 최근 N일 데이터 조회
        cache: Redis 캐시 의존성
        session: DB 세션 의존성

    Returns:
        SectorTrendsResponse: 섹터 트렌드 목록
    """
    cache_key = _SECTOR_CACHE_KEY_FORMAT.format(days=days)

    # 1단계: 캐시 조회
    raw = await cache.get(cache_key)
    if raw is not None:
        if isinstance(raw, str):
            cached_data: dict[str, Any] = json.loads(raw)
        else:
            cached_data = raw
        trends = [SectorTrendItem(**item) for item in cached_data["trends"]]
        return SectorTrendsResponse(trends=trends, days=cached_data.get("days", days))

    # 2단계: DB 조회
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
    stmt = select(SectorTrend).where(SectorTrend.trade_date >= cutoff)
    result = await session.execute(stmt)
    rows = result.scalars().all()

    trends = [
        SectorTrendItem(
            sector=row.sector,
            trade_date=row.trade_date.date() if hasattr(row.trade_date, "date") else row.trade_date,
            trend_score=float(row.trend_score),
            news_volume=row.news_volume,
            avg_sentiment=float(row.avg_sentiment),
        )
        for row in rows
    ]

    return SectorTrendsResponse(trends=trends, days=days)


@router.get("/ranking", response_model=SectorRankingResponse)
async def get_sector_ranking(
    sort: Annotated[Literal["score", "sentiment", "volume"], Query()] = "score",
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    days: Annotated[int, Query(ge=1)] = 1,
    cache: RecommendationCache = Depends(get_cache),
    session: AsyncSession = Depends(get_session),
) -> SectorRankingResponse:
    """섹터 랭킹 조회 — 최근 N일 데이터를 기준으로 정렬.

    Args:
        sort: 정렬 기준 (score | sentiment | volume)
        limit: 최대 반환 섹터 수 (1-50)
        days: 최근 N일 데이터 조회
        cache: Redis 캐시 의존성
        session: DB 세션 의존성

    Returns:
        SectorRankingResponse: 정렬된 섹터 랭킹
    """
    cache_key = _SECTOR_RANKING_KEY_FORMAT.format(sort=sort, limit=limit, days=days)

    # 캐시 조회
    raw = await cache.get(cache_key)
    if raw is not None:
        if isinstance(raw, str):
            cached_data: dict[str, Any] = json.loads(raw)
        else:
            cached_data = raw
        sectors = [SectorRankingItem(**item) for item in cached_data["sectors"]]
        return SectorRankingResponse(
            sort=cached_data["sort"],
            limit=cached_data["limit"],
            sectors=sectors,
            total=cached_data["total"],
        )

    # DB 조회: 최근 N일 중 가장 최신 데이터
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
    stmt = select(SectorTrend).where(SectorTrend.trade_date >= cutoff)
    result = await session.execute(stmt)
    rows = result.scalars().all()

    # 정렬 기준에 따라 내림차순 정렬
    sort_key_map: dict[str, str] = {
        "score": "trend_score",
        "sentiment": "avg_sentiment",
        "volume": "news_volume",
    }
    attr = sort_key_map[sort]
    sorted_rows = sorted(rows, key=lambda r: float(getattr(r, attr)), reverse=True)[:limit]

    sectors = [
        SectorRankingItem(
            sector=row.sector,
            trade_date=row.trade_date.date() if hasattr(row.trade_date, "date") else row.trade_date,
            news_volume=row.news_volume,
            avg_sentiment=float(row.avg_sentiment),
            trend_score=float(row.trend_score),
        )
        for row in sorted_rows
    ]

    return SectorRankingResponse(sort=sort, limit=limit, sectors=sectors, total=len(sectors))


@router.get("/{sector}/detail", response_model=SectorDetailResponse)
async def get_sector_detail(
    sector: str,
    days: Annotated[int, Query(ge=1)] = 7,
    cache: RecommendationCache = Depends(get_cache),
    session: AsyncSession = Depends(get_session),
) -> SectorDetailResponse:
    """섹터 상세 조회 — 트렌드 시계열 및 구성 종목.

    Args:
        sector: 섹터 이름
        days: 최근 N일 트렌드 데이터
        cache: Redis 캐시 의존성
        session: DB 세션 의존성

    Returns:
        SectorDetailResponse: 트렌드 시계열 + 구성 종목 목록

    Raises:
        HTTPException: 해당 섹터 데이터가 없을 때 404
    """
    cache_key = _SECTOR_DETAIL_KEY_FORMAT.format(sector=sector, days=days)

    # 캐시 조회
    raw = await cache.get(cache_key)
    if raw is not None:
        if isinstance(raw, str):
            cached_data: dict[str, Any] = json.loads(raw)
        else:
            cached_data = raw
        trends = [SectorTrendItem(**item) for item in cached_data["trends"]]
        stocks = [SectorStockItem(**item) for item in cached_data["stocks"]]
        return SectorDetailResponse(
            sector=cached_data["sector"],
            days=cached_data["days"],
            trends=trends,
            stocks=stocks,
            total_stocks=cached_data["total_stocks"],
        )

    # 트렌드 시계열 조회
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
    trend_stmt = (
        select(SectorTrend)
        .where(SectorTrend.sector == sector, SectorTrend.trade_date >= cutoff)
        .order_by(SectorTrend.trade_date)
    )
    trend_result = await session.execute(trend_stmt)
    trend_rows = trend_result.scalars().all()

    if not trend_rows:
        raise HTTPException(
            status_code=404,
            detail=f"섹터 데이터를 찾을 수 없습니다: {sector}",
        )

    trends = [
        SectorTrendItem(
            sector=row.sector,
            trade_date=row.trade_date.date() if hasattr(row.trade_date, "date") else row.trade_date,
            trend_score=float(row.trend_score),
            news_volume=row.news_volume,
            avg_sentiment=float(row.avg_sentiment),
        )
        for row in trend_rows
    ]

    # 구성 종목 조회: StockMention → Article → AnalysisResult where sector IN sector_tags
    # sector_tags는 PostgreSQL ARRAY이므로 contains([sector])로 필터링
    # @MX:NOTE: [AUTO] ARRAY contains 필터 - PostgreSQL 전용 구문
    stock_stmt = (
        select(StockMention.krx_code, func.count(StockMention.id).label("mention_count"))
        .join(Article, StockMention.article_id == Article.id)
        .join(AnalysisResult, AnalysisResult.article_id == Article.id)
        .where(
            StockMention.krx_code.isnot(None),
            AnalysisResult.sector_tags.contains([sector]),
        )
        .group_by(StockMention.krx_code)
        .order_by(func.count(StockMention.id).desc())
        .limit(20)
    )
    stock_result = await session.execute(stock_stmt)
    stock_rows = stock_result.all()

    stocks = [
        SectorStockItem(krx_code=row.krx_code, mention_count=row.mention_count)
        for row in stock_rows
    ]

    return SectorDetailResponse(
        sector=sector,
        days=days,
        trends=trends,
        stocks=stocks,
        total_stocks=len(stocks),
    )
