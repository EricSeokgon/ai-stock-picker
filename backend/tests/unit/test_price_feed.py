# price_feed 유닛 테스트 — FinanceDataReader mock
from unittest.mock import patch

import pandas as pd


class TestGetCurrentPrice:
    """get_current_price 유닛 테스트"""

    def test_valid_krx_code_returns_price_dict(self):
        """유효한 종목코드 — 가격 딕셔너리 반환"""
        # FinanceDataReader mock 데이터 (2일치)
        mock_df = pd.DataFrame(
            {"Close": [70000.0, 72000.0]},
            index=pd.date_range("2024-01-01", periods=2),
        )

        with patch("FinanceDataReader.DataReader", return_value=mock_df):
            from stock_picker.realtime.price_feed import get_current_price

            result = get_current_price("005930")

        assert result is not None
        assert result["krx_code"] == "005930"
        assert result["price"] == 72000.0
        # 등락률: (72000 - 70000) / 70000 * 100 ≈ 2.86
        assert abs(result["change_pct"] - 2.86) < 0.01
        assert "timestamp" in result

    def test_invalid_code_returns_none(self):
        """빈 데이터 반환 시 None"""
        mock_df = pd.DataFrame()

        with patch("FinanceDataReader.DataReader", return_value=mock_df):
            from stock_picker.realtime.price_feed import get_current_price

            result = get_current_price("INVALID")

        assert result is None

    def test_exception_returns_none(self):
        """FinanceDataReader 예외 발생 시 None 반환 (연결 유지)"""
        with patch("FinanceDataReader.DataReader", side_effect=Exception("네트워크 오류")):
            from stock_picker.realtime.price_feed import get_current_price

            result = get_current_price("005930")

        assert result is None

    def test_single_row_change_pct_zero(self):
        """데이터 1건이면 등락률 0.0"""
        mock_df = pd.DataFrame(
            {"Close": [50000.0]},
            index=pd.date_range("2024-01-01", periods=1),
        )

        with patch("FinanceDataReader.DataReader", return_value=mock_df):
            from stock_picker.realtime.price_feed import get_current_price

            result = get_current_price("000660")

        assert result is not None
        assert result["change_pct"] == 0.0

    def test_result_cached_after_success(self):
        """성공 결과가 캐시에 저장되는지 확인"""
        mock_df = pd.DataFrame(
            {"Close": [10000.0, 11000.0]},
            index=pd.date_range("2024-01-01", periods=2),
        )

        with patch("FinanceDataReader.DataReader", return_value=mock_df):
            from stock_picker.realtime import price_feed

            price_feed._price_cache.clear()
            result = price_feed.get_current_price("035420")

        assert "035420" in price_feed._price_cache
        assert price_feed._price_cache["035420"]["price"] == 11000.0
        # 반환값도 캐시에 저장된 내용과 일치해야 한다
        assert result is not None
        assert result["price"] == 11000.0
