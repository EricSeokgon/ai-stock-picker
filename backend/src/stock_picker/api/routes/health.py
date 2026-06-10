# 헬스 체크 라우터 — DB·Redis 연결 상태 점검 포함
import logging

from fastapi import APIRouter
from sqlalchemy import text

from stock_picker.db.session import engine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict[str, str]:
    """DB·Redis 연결 상태를 포함한 헬스 체크.

    DB 장애 시 status=error, Redis 미연결/장애 시 redis=unavailable(기동은 계속).
    컨테이너 healthcheck 및 무인증 사용 가능.
    """
    db_status = "ok"
    redis_status = "ok"

    # DB 점검 — SELECT 1
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        logger.warning("헬스 체크: DB 연결 실패")
        db_status = "error"

    # Redis 점검 — PING (graceful: 실패해도 status는 유지)
    try:
        import redis.asyncio as aioredis

        from stock_picker.api.deps import get_redis_client
        client: aioredis.Redis = get_redis_client()
        try:
            await client.ping()
        finally:
            await client.aclose()
    except Exception:
        logger.debug("헬스 체크: Redis 연결 불가 (unavailable)")
        redis_status = "unavailable"

    overall = "ok" if db_status == "ok" else "error"
    return {"status": overall, "db": db_status, "redis": redis_status}
