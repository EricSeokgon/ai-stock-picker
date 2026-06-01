# Redis 캐시 추상화 - 추천 결과 캐싱
import json
from typing import Any

import structlog

log = structlog.get_logger()


class RecommendationCache:
    """Redis 기반 추천 결과 캐시.

    추천 결과를 Redis에 JSON으로 저장하여 동일 요청에서 DB 재조회를 방지한다.
    """

    TTL_SECONDS = 1800  # 30분

    def __init__(self, redis_client: Any) -> None:
        """
        Args:
            redis_client: redis.asyncio 클라이언트 인스턴스
        """
        self._redis = redis_client

    async def get(self, key: str) -> list | None:
        """캐시에서 추천 결과 조회.

        Args:
            key: Redis 키

        Returns:
            저장된 추천 목록. 없으면 None.
        """
        try:
            raw = await self._redis.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as e:
            log.warning("캐시 읽기 실패", key=key, error=str(e))
            return None

    async def set(self, key: str, data: list) -> None:
        """추천 결과를 Redis에 저장.

        Args:
            key: Redis 키
            data: 저장할 추천 목록
        """
        try:
            serialized = json.dumps(data, ensure_ascii=False, default=str)
            await self._redis.setex(key, self.TTL_SECONDS, serialized)
        except Exception as e:
            log.warning("캐시 쓰기 실패", key=key, error=str(e))
