# FinanceDataReader 비동기 래퍼 단위 테스트

import pytest
import asyncio
from unittest.mock import patch
import pandas as pd


class TestGetStockPriceData:
    """get_stock_price_data 함수 단위 테스트"""

    @pytest.mark.asyncio
    async def test_normal_call_returns_price_dict(self):
        """정상 호출 → 시세 딕셔너리 반환"""
        from stock_picker.mapping.prices import get_stock_price_data

        # 샘플 DataFrame mock
        sample_df = pd.DataFrame({
            "Close": [70000.0, 71000.0, 72000.0],
            "Volume": [10000000, 11000000, 12000000],
            "Change": [0.01, 0.014, 0.014],
        })

        with patch("FinanceDataReader.DataReader", return_value=sample_df):
            result = await get_stock_price_data("005930")

        assert result is not None
        assert "close_price" in result
        assert "volume" in result
        assert result["close_price"] == 72000.0

    @pytest.mark.asyncio
    async def test_normal_call_includes_change_rate(self):
        """정상 호출 → change_rate 포함 확인"""
        from stock_picker.mapping.prices import get_stock_price_data

        sample_df = pd.DataFrame({
            "Close": [70000.0, 71000.0, 72000.0],
            "Volume": [10000000, 11000000, 12000000],
            "Change": [0.01, 0.014, 0.014],
        })

        with patch("FinanceDataReader.DataReader", return_value=sample_df):
            result = await get_stock_price_data("005930")

        assert "change_rate" in result
        assert isinstance(result["change_rate"], float)

    @pytest.mark.asyncio
    async def test_datareader_exception_returns_none(self):
        """DataReader 예외 → None 반환 (E-5)"""
        from stock_picker.mapping.prices import get_stock_price_data

        with patch("FinanceDataReader.DataReader", side_effect=Exception("API error")):
            result = await get_stock_price_data("999999")

        assert result is None

    @pytest.mark.asyncio
    async def test_empty_dataframe_returns_none(self):
        """빈 DataFrame → None 반환"""
        from stock_picker.mapping.prices import get_stock_price_data

        empty_df = pd.DataFrame()

        with patch("FinanceDataReader.DataReader", return_value=empty_df):
            result = await get_stock_price_data("005930")

        assert result is None

    @pytest.mark.asyncio
    async def test_uses_run_in_executor_for_sync_library(self):
        """동기 라이브러리 격리 - run_in_executor 사용 확인"""
        from stock_picker.mapping import prices

        sample_df = pd.DataFrame({
            "Close": [70000.0],
            "Volume": [10000000],
            "Change": [0.01],
        })

        executor_called = False

        async def mock_run_in_executor(loop, executor, func, *args):
            nonlocal executor_called
            executor_called = True
            return func(*args)

        with patch("FinanceDataReader.DataReader", return_value=sample_df):
            loop = asyncio.get_event_loop()
            with patch.object(loop, "run_in_executor", side_effect=mock_run_in_executor):
                await prices.get_stock_price_data("005930")

        assert executor_called
