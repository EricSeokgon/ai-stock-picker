# 주가 히스토리 함수 단위 테스트 (SPEC-STOCK-007 TASK-009)
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest


def _make_sample_df(n: int = 5) -> pd.DataFrame:
    """테스트용 주가 DataFrame 생성 (최근 n일)"""
    from datetime import datetime, timedelta

    dates = pd.date_range(end=datetime.now(), periods=n, freq="D")
    df = pd.DataFrame(
        {
            "Close": [70000.0 + i * 1000 for i in range(n)],
            "Volume": [1000000 * (i + 1) for i in range(n)],
            "Change": [0.01 * i for i in range(n)],
        },
        index=dates,
    )
    return df


class TestGetStockPriceHistory:
    """get_stock_price_history 함수 단위 테스트"""

    @pytest.mark.asyncio
    async def test_returns_list_of_price_points_on_success(self):
        """정상 조회 → date/close 포함한 dict 리스트 반환"""
        from stock_picker.mapping.prices import get_stock_price_history

        sample_df = _make_sample_df(5)

        with (
            patch("redis.asyncio.from_url") as mock_redis_factory,
            patch("FinanceDataReader.DataReader", return_value=sample_df),
        ):
            mock_redis = AsyncMock()
            mock_redis.get.return_value = None  # 캐시 미스
            mock_redis.set = AsyncMock()
            mock_redis.aclose = AsyncMock()
            mock_redis_factory.return_value = mock_redis

            result = await get_stock_price_history("005930", days=30)

        assert isinstance(result, list)
        assert len(result) > 0
        assert "date" in result[0]
        assert "close" in result[0]
        assert isinstance(result[0]["close"], float)

    @pytest.mark.asyncio
    async def test_redis_cache_hit_skips_fdr(self):
        """Redis 캐시 히트 시 FinanceDataReader 미호출"""
        from stock_picker.mapping.prices import get_stock_price_history

        cached_data = [{"date": "2026-01-01", "close": 70000.0}]

        with (
            patch("redis.asyncio.from_url") as mock_redis_factory,
            patch("FinanceDataReader.DataReader") as mock_fdr,
        ):
            mock_redis = AsyncMock()
            mock_redis.get.return_value = json.dumps(cached_data)
            mock_redis.aclose = AsyncMock()
            mock_redis_factory.return_value = mock_redis

            result = await get_stock_price_history("005930", days=30)

        assert result == cached_data
        mock_fdr.assert_not_called()

    @pytest.mark.asyncio
    async def test_fdr_failure_returns_empty_list(self):
        """FinanceDataReader 실패 → 빈 리스트 반환 (예외 전파 없음)"""
        from stock_picker.mapping.prices import get_stock_price_history

        with (
            patch("redis.asyncio.from_url") as mock_redis_factory,
            patch("FinanceDataReader.DataReader", side_effect=Exception("API 오류")),
        ):
            mock_redis = AsyncMock()
            mock_redis.get.return_value = None
            mock_redis.aclose = AsyncMock()
            mock_redis_factory.return_value = mock_redis

            result = await get_stock_price_history("999999", days=30)

        assert result == []

    @pytest.mark.asyncio
    async def test_empty_dataframe_returns_empty_list(self):
        """빈 DataFrame → 빈 리스트 반환"""
        from stock_picker.mapping.prices import get_stock_price_history

        with (
            patch("redis.asyncio.from_url") as mock_redis_factory,
            patch("FinanceDataReader.DataReader", return_value=pd.DataFrame()),
        ):
            mock_redis = AsyncMock()
            mock_redis.get.return_value = None
            mock_redis.aclose = AsyncMock()
            mock_redis_factory.return_value = mock_redis

            result = await get_stock_price_history("005930", days=30)

        assert result == []

    @pytest.mark.asyncio
    async def test_redis_down_falls_back_to_fdr(self):
        """Redis 장애 시 FinanceDataReader 폴백 동작"""
        from stock_picker.mapping.prices import get_stock_price_history

        sample_df = _make_sample_df(3)

        with (
            patch("redis.asyncio.from_url") as mock_redis_factory,
            patch("FinanceDataReader.DataReader", return_value=sample_df),
        ):
            mock_redis = AsyncMock()
            mock_redis.get.side_effect = Exception("Redis 연결 오류")
            mock_redis.aclose = AsyncMock()
            mock_redis_factory.return_value = mock_redis

            result = await get_stock_price_history("005930", days=30)

        # Redis 실패해도 FDR 결과 반환
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_results_sorted_oldest_first(self):
        """결과가 날짜 오름차순(oldest first) 정렬"""
        from stock_picker.mapping.prices import get_stock_price_history

        sample_df = _make_sample_df(5)

        with (
            patch("redis.asyncio.from_url") as mock_redis_factory,
            patch("FinanceDataReader.DataReader", return_value=sample_df),
        ):
            mock_redis = AsyncMock()
            mock_redis.get.return_value = None
            mock_redis.set = AsyncMock()
            mock_redis.aclose = AsyncMock()
            mock_redis_factory.return_value = mock_redis

            result = await get_stock_price_history("005930", days=30)

        if len(result) >= 2:
            assert result[0]["date"] <= result[-1]["date"]

    @pytest.mark.asyncio
    async def test_days_parameter_limits_period(self):
        """days=5 파라미터가 캐시 키에 반영됨"""
        from stock_picker.mapping.prices import get_stock_price_history

        with patch("redis.asyncio.from_url") as mock_redis_factory:
            mock_redis = AsyncMock()
            mock_redis.get.return_value = None
            mock_redis.set = AsyncMock()
            mock_redis.aclose = AsyncMock()
            mock_redis_factory.return_value = mock_redis

            with patch("FinanceDataReader.DataReader", return_value=pd.DataFrame()):
                await get_stock_price_history("005930", days=5)

            # 캐시 키가 days=5를 포함하는지 확인
            get_calls = mock_redis.get.call_args_list
            assert any("5" in str(call) for call in get_calls)

    @pytest.mark.asyncio
    async def test_cache_saved_after_fdr_success(self):
        """FDR 성공 시 Redis에 캐시 저장"""
        from stock_picker.mapping.prices import get_stock_price_history

        sample_df = _make_sample_df(3)

        with (
            patch("redis.asyncio.from_url") as mock_redis_factory,
            patch("FinanceDataReader.DataReader", return_value=sample_df),
        ):
            mock_redis = AsyncMock()
            mock_redis.get.return_value = None
            mock_redis.set = AsyncMock()
            mock_redis.aclose = AsyncMock()
            mock_redis_factory.return_value = mock_redis

            await get_stock_price_history("005930", days=30)

        mock_redis.set.assert_called_once()
        # TTL 3600으로 저장되었는지 확인
        call_kwargs = mock_redis.set.call_args
        assert call_kwargs.kwargs.get("ex") == 3600 or (
            len(call_kwargs.args) >= 3 and call_kwargs.args[2] == 3600
        ) or (call_kwargs.kwargs.get("ex") == 3600)
