# RecommendationCache 단위 테스트 (파생 캐시 메서드 포함)
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from stock_picker.recommendation.cache import RecommendationCache


# ─── 픽스처 ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_redis() -> AsyncMock:
    """비동기 Redis 클라이언트 목."""
    client = AsyncMock()
    return client


@pytest.fixture
def cache(mock_redis: AsyncMock) -> RecommendationCache:
    """테스트용 RecommendationCache 인스턴스."""
    return RecommendationCache(mock_redis)


# ─── get_derived 테스트 ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_derived_returns_none_on_miss(
    cache: RecommendationCache, mock_redis: AsyncMock
) -> None:
    """캐시 미스 시 None 반환."""
    mock_redis.get.return_value = None

    result = await cache.get_derived("recommendations:top:5")

    assert result is None
    mock_redis.get.assert_called_once_with("recommendations:top:5")


@pytest.mark.asyncio
async def test_get_derived_returns_data_on_hit(
    cache: RecommendationCache, mock_redis: AsyncMock
) -> None:
    """캐시 히트 시 저장된 데이터 반환."""
    sample_data = [{"krx_code": "005930", "total_score": 0.9}]
    mock_redis.get.return_value = json.dumps(sample_data)

    result = await cache.get_derived("recommendations:top:5")

    assert result == sample_data


@pytest.mark.asyncio
async def test_get_derived_returns_none_on_redis_error(
    cache: RecommendationCache, mock_redis: AsyncMock
) -> None:
    """Redis ConnectionError 시 None 반환 (예외 전파 없음)."""
    mock_redis.get.side_effect = ConnectionError("Redis 연결 실패")

    result = await cache.get_derived("recommendations:top:5")

    assert result is None  # 예외가 호출자로 전파되지 않음


# ─── set_derived 테스트 ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_set_derived_stores_with_ttl(
    cache: RecommendationCache, mock_redis: AsyncMock
) -> None:
    """set_derived 호출 시 TTL과 함께 데이터 저장."""
    sample_data = [{"krx_code": "005930", "total_score": 0.9}]

    await cache.set_derived("recommendations:top:5", sample_data, ttl=900)

    mock_redis.setex.assert_called_once()
    call_args = mock_redis.setex.call_args
    assert call_args[0][0] == "recommendations:top:5"  # 키
    assert call_args[0][1] == 900  # TTL
    stored = json.loads(call_args[0][2])
    assert stored == sample_data


@pytest.mark.asyncio
async def test_set_derived_default_ttl(
    cache: RecommendationCache, mock_redis: AsyncMock
) -> None:
    """기본 TTL(1800초) 사용 확인."""
    await cache.set_derived("recommendations:top:10", [])

    call_args = mock_redis.setex.call_args
    assert call_args[0][1] == 1800


@pytest.mark.asyncio
async def test_set_derived_ignores_redis_error(
    cache: RecommendationCache, mock_redis: AsyncMock
) -> None:
    """Redis 오류 시 예외 전파 없음."""
    mock_redis.setex.side_effect = ConnectionError("Redis 연결 실패")

    # 예외가 발생하지 않아야 함
    await cache.set_derived("recommendations:top:5", [])


# ─── invalidate_derived 테스트 ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_invalidate_derived_deletes_matching_keys(
    cache: RecommendationCache, mock_redis: AsyncMock
) -> None:
    """패턴에 매칭되는 키들을 삭제."""
    # scan이 각 패턴에 대해 키를 반환하도록 설정
    # scan(cursor, match=pattern, count=100) → (next_cursor, keys)
    # cursor=0으로 종료 신호

    def scan_side_effect(cursor, match, count):
        if match == "recommendations:top:*":
            if cursor == 0:
                return (0, [b"recommendations:top:5", b"recommendations:top:10"])
        elif match == "recommendations:sector:*":
            if cursor == 0:
                return (0, [b"recommendations:sector:IT"])
        return (0, [])

    mock_redis.scan = AsyncMock(side_effect=scan_side_effect)
    mock_redis.delete = AsyncMock()

    await cache.invalidate_derived()

    # delete가 각 패턴에 대해 호출됐는지 확인
    assert mock_redis.delete.call_count == 2  # top:* 1번, sector:* 1번


@pytest.mark.asyncio
async def test_invalidate_derived_ignores_redis_error(
    cache: RecommendationCache, mock_redis: AsyncMock
) -> None:
    """Redis 오류 시 예외 전파 없음."""
    mock_redis.scan = AsyncMock(side_effect=ConnectionError("Redis 연결 실패"))

    # 예외가 발생하지 않아야 함
    await cache.invalidate_derived()


@pytest.mark.asyncio
async def test_invalidate_derived_empty_keys(
    cache: RecommendationCache, mock_redis: AsyncMock
) -> None:
    """삭제할 키가 없어도 정상 동작."""
    mock_redis.scan = AsyncMock(return_value=(0, []))
    mock_redis.delete = AsyncMock()

    await cache.invalidate_derived()

    mock_redis.delete.assert_not_called()


# ─── build_derived_key 테스트 ────────────────────────────────────────────────


def test_build_derived_key_limit_only(cache: RecommendationCache) -> None:
    """limit만 있을 때 키 형식."""
    key = cache.build_derived_key(limit=5)
    assert key == "recommendations:top:5"


def test_build_derived_key_sector_only(cache: RecommendationCache) -> None:
    """sector만 있을 때 키 형식."""
    key = cache.build_derived_key(sector="IT")
    assert key == "recommendations:sector:IT"


def test_build_derived_key_both(cache: RecommendationCache) -> None:
    """limit + sector 조합 키 형식."""
    key = cache.build_derived_key(limit=3, sector="금융")
    assert key == "recommendations:top:3:sector:금융"


def test_build_derived_key_none(cache: RecommendationCache) -> None:
    """파라미터 없을 때 기본 키 형식."""
    key = cache.build_derived_key()
    assert key == "recommendations:top:all"


# ─── 기존 get/set 메서드 하위 호환성 테스트 ─────────────────────────────────


@pytest.mark.asyncio
async def test_existing_get_still_works(
    cache: RecommendationCache, mock_redis: AsyncMock
) -> None:
    """기존 get() 메서드가 그대로 동작함."""
    mock_redis.get.return_value = json.dumps([{"rank": 1, "krx_code": "005930"}])

    result = await cache.get("recommendations:2025-01-01")

    assert result is not None
    assert result[0]["krx_code"] == "005930"


@pytest.mark.asyncio
async def test_existing_set_still_works(
    cache: RecommendationCache, mock_redis: AsyncMock
) -> None:
    """기존 set() 메서드가 그대로 동작함."""
    await cache.set("recommendations:2025-01-01", [{"rank": 1}])

    mock_redis.setex.assert_called_once()
    assert mock_redis.setex.call_args[0][0] == "recommendations:2025-01-01"
    assert mock_redis.setex.call_args[0][1] == 1800  # 기존 TTL_SECONDS
