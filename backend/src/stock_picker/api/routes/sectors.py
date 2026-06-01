# 섹터 트렌드 API (REQ-WEB-003, AC-9)
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from stock_picker.api.deps import get_cache, get_session
from stock_picker.api.schemas import SectorTrendItem, SectorTrendsResponse
from stock_picker.db.models import SectorTrend
from stock_picker.recommendation.cache import RecommendationCache

router = APIRouter(prefix="/sectors", tags=["sectors"])

# 캐시 키 형식
_SECTOR_CACHE_KEY_FORMAT = "sector_trends:{days}"


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
