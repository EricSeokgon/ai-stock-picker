# 추천 엔드포인트 - 당일 Top 10 추천 리스트 반환
import json
from datetime import date, datetime, timezone
from typing import Union

from fastapi import APIRouter, Depends

from stock_picker.api.deps import get_cache
from stock_picker.api.schemas import (
    PreparingResponse,
    RecommendationItem,
    RecommendationsResponse,
)
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
