# Redis 캐시 추상화 - 추천 결과 캐싱
import json
from typing import Any

import structlog

log = structlog.get_logger()


class RecommendationCache:
    """Redis 기반 추천 결과 캐시.

    추천 결과를 Redis에 JSON으로 저장하여 동일 요청에서 DB 재조회를 방지한다.
    파생 키(필터/정렬 결과)는 별도 키 공간(recommendations:top:*, recommendations:sector:*)에 저장한다.
    """

    TTL_SECONDS = 1800  # 30분
    DERIVED_TTL_SECONDS = 1800  # 파생 캐시 TTL: 30분

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
                log.debug("캐시 미스", key=key)
                return None
            log.debug("캐시 히트", key=key)
            return json.loads(raw)
        except Exception as e:
            log.warning("Redis 오류 (폴백)", error=str(e))
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
            log.warning("Redis 오류 (폴백)", error=str(e))

    # ─── 파생 캐시 메서드 ────────────────────────────────────────────────────

    async def get_derived(self, key: str) -> list[dict] | None:
        """파생 캐시 키에서 데이터 조회.

        # @MX:ANCHOR: [AUTO] 파생 캐시 조회 진입점 — recommendations 라우터에서 호출
        # @MX:REASON: 필터/정렬 결과를 캐시하여 반복 계산 방지, Redis 장애 시 None 반환으로 폴백

        Args:
            key: 파생 캐시 키 (build_derived_key()로 생성)

        Returns:
            캐시 히트 시 추천 목록(dict 리스트). 미스 또는 Redis 오류 시 None.
        """
        try:
            raw = await self._redis.get(key)
            if raw is None:
                log.debug("캐시 미스", key=key)
                return None
            log.debug("캐시 히트", key=key)
            return json.loads(raw)
        except Exception as e:
            log.warning("Redis 오류 (폴백)", error=str(e))
            return None

    async def set_derived(self, key: str, data: list[dict], ttl: int = 1800) -> None:
        """파생 캐시 키에 데이터 저장.

        Args:
            key: 파생 캐시 키
            data: 저장할 추천 목록(dict 리스트)
            ttl: 만료 시간(초). 기본 1800초(30분).
        """
        try:
            serialized = json.dumps(data, ensure_ascii=False, default=str)
            await self._redis.setex(key, ttl, serialized)
        except Exception as e:
            log.warning("Redis 오류 (폴백)", error=str(e))

    async def invalidate_derived(self) -> None:
        """파생 캐시 키 전체 삭제.

        recommendations:top:* 및 recommendations:sector:* 패턴에 해당하는 키를 모두 삭제한다.
        Redis 오류 발생 시 조용히 무시한다.
        """
        patterns = ["recommendations:top:*", "recommendations:sector:*"]
        total_deleted = 0
        try:
            for pattern in patterns:
                cursor = 0
                while True:
                    cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)
                    if keys:
                        await self._redis.delete(*keys)
                        total_deleted += len(keys)
                    if cursor == 0:
                        break
            log.info("파생 캐시 무효화", count=total_deleted)
        except Exception as e:
            log.warning("Redis 오류 (폴백)", error=str(e))

    def build_derived_key(
        self,
        limit: int | None = None,
        sector: str | None = None,
    ) -> str:
        """파생(필터/정렬) 추천 캐시 키 생성.

        키 형식:
        - limit만: recommendations:top:{limit}
        - sector만: recommendations:sector:{sector}
        - 둘 다: recommendations:top:{limit}:sector:{sector}
        - 둘 다 없음: recommendations:top:all

        Args:
            limit: 반환 개수 제한
            sector: 섹터 필터 문자열

        Returns:
            Redis 캐시 키 문자열
        """
        if limit is not None and sector is not None:
            return f"recommendations:top:{limit}:sector:{sector}"
        if limit is not None:
            return f"recommendations:top:{limit}"
        if sector is not None:
            return f"recommendations:sector:{sector}"
        return "recommendations:top:all"
