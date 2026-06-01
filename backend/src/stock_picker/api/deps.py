# FastAPI 의존성 주입 - Redis 및 DB 세션
import os

import redis.asyncio as aioredis

from stock_picker.db.session import get_session  # noqa: F401  재-export용

# ---------------------------------------------------------------------------
# Redis 의존성
# ---------------------------------------------------------------------------

_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# @MX:NOTE: [AUTO] Redis 연결은 모듈 레벨에서 생성하지 않고 매 요청마다 풀에서 꺼낸다.
# 테스트 시 get_redis_client를 mock으로 교체하면 된다.


def get_redis_client() -> aioredis.Redis:
    """Redis 클라이언트 반환. 의존성 주입 대상."""
    return aioredis.from_url(_REDIS_URL, decode_responses=True)


async def get_cache():
    """RecommendationCache 인스턴스를 FastAPI 의존성으로 제공."""
    from stock_picker.recommendation.cache import RecommendationCache

    redis_client = get_redis_client()
    try:
        yield RecommendationCache(redis_client)
    finally:
        await redis_client.aclose()
