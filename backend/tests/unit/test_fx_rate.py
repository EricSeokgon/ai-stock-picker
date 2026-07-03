# FX rate 서비스 유닛 테스트 (SPEC-STOCK-028 T-003)
# Redis 캐시 hit/miss/fallback 및 KST 날짜 키 형식 검증
from unittest.mock import AsyncMock, patch

import pytest


class TestGetUsdKrwRate:
    """get_usd_krw_rate — Redis 캐시 + FDR fallback 패턴 검증"""

    @pytest.mark.asyncio
    async def test_cache_miss_calls_fdr_and_caches_result(self):
        """캐시 미스 시 FDR 호출 후 Redis setex로 TTL>=3600s 캐싱"""
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)  # 캐시 미스
        redis.setex = AsyncMock()

        with patch(
            "stock_picker.portfolio.fx_rate._fetch_usd_krw_sync",
            return_value=1320.5,
        ):
            from stock_picker.portfolio import fx_rate
            rate = await fx_rate.get_usd_krw_rate(redis)

        assert rate == pytest.approx(1320.5)
        # setex가 호출되었고 TTL >= 3600
        redis.setex.assert_called_once()
        call_args = redis.setex.call_args
        # setex(key, ttl, value) 형태
        ttl_arg = call_args[0][1]
        assert ttl_arg >= 3600

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_value_without_fdr(self):
        """캐시 히트 시 FDR 미호출, 캐시 값 반환"""
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=b"1350.0")

        with patch(
            "stock_picker.portfolio.fx_rate._fetch_usd_krw_sync",
        ) as mock_fdr:
            from stock_picker.portfolio import fx_rate
            rate = await fx_rate.get_usd_krw_rate(redis)

        assert rate == pytest.approx(1350.0)
        mock_fdr.assert_not_called()

    @pytest.mark.asyncio
    async def test_fallback_when_fdr_and_redis_fail(self):
        """FDR과 Redis 모두 실패 시 _FALLBACK_RATE=1350.0 반환, WARNING 로그"""
        redis = AsyncMock()
        redis.get = AsyncMock(side_effect=Exception("Redis 연결 실패"))
        redis.setex = AsyncMock()

        with patch(
            "stock_picker.portfolio.fx_rate._fetch_usd_krw_sync",
            side_effect=Exception("FDR 실패"),
        ):
            from stock_picker.portfolio import fx_rate
            with patch.object(fx_rate.logger, "warning") as mock_warn:
                rate = await fx_rate.get_usd_krw_rate(redis)

        assert rate == pytest.approx(fx_rate._FALLBACK_RATE)
        assert mock_warn.called

    @pytest.mark.asyncio
    async def test_cache_key_includes_kst_date(self):
        """캐시 키가 KST 날짜 문자열 포함 형식인지 검증"""
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()

        with patch(
            "stock_picker.portfolio.fx_rate._fetch_usd_krw_sync",
            return_value=1300.0,
        ):
            from stock_picker.portfolio import fx_rate
            await fx_rate.get_usd_krw_rate(redis)

        # setex 첫 번째 인수 = 키
        key_used = redis.setex.call_args[0][0]
        # 형식: fx:USD:KRW:{YYYY-MM-DD}
        assert key_used.startswith("fx:USD:KRW:")
        date_part = key_used.split("fx:USD:KRW:")[1]
        # YYYY-MM-DD 형식 확인
        assert len(date_part) == 10
        assert date_part[4] == "-"
        assert date_part[7] == "-"
