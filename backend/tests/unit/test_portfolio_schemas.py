# 포트폴리오 스키마 유닛 테스트 — 해외 자산 필드 및 market-currency 유효성 검증 (SPEC-STOCK-028)
from decimal import Decimal

import pytest
from pydantic import ValidationError

from stock_picker.portfolio.schemas import HoldingCreate, HoldingResponse, HoldingPerformance


class TestHoldingCreateForeignAsset:
    """HoldingCreate — market/currency 필드 및 유효성 검증"""

    def test_default_market_and_currency_are_krx_krw(self):
        """기본값: market=KRX, currency=KRW"""
        h = HoldingCreate(krx_code="005930", quantity=10, avg_buy_price=Decimal("70000"))
        assert h.market == "KRX"
        assert h.currency == "KRW"

    def test_nyse_with_usd_is_valid(self):
        """NYSE + USD 조합은 유효"""
        h = HoldingCreate(
            krx_code="AAPL", quantity=5, avg_buy_price=Decimal("180.00"),
            market="NYSE", currency="USD",
        )
        assert h.market == "NYSE"
        assert h.currency == "USD"

    def test_nasdaq_with_usd_is_valid(self):
        """NASDAQ + USD 조합은 유효"""
        h = HoldingCreate(
            krx_code="MSFT", quantity=2, avg_buy_price=Decimal("420.00"),
            market="NASDAQ", currency="USD",
        )
        assert h.market == "NASDAQ"
        assert h.currency == "USD"

    def test_krx_with_usd_raises_validation_error(self):
        """KRX + USD 조합은 ValidationError 발생"""
        with pytest.raises(ValidationError):
            HoldingCreate(
                krx_code="005930", quantity=10, avg_buy_price=Decimal("70000"),
                market="KRX", currency="USD",
            )

    def test_nyse_with_krw_raises_validation_error(self):
        """NYSE + KRW 조합은 ValidationError 발생"""
        with pytest.raises(ValidationError):
            HoldingCreate(
                krx_code="AAPL", quantity=5, avg_buy_price=Decimal("180.00"),
                market="NYSE", currency="KRW",
            )

    def test_invalid_market_raises_validation_error(self):
        """지원하지 않는 market 값은 ValidationError 발생"""
        with pytest.raises(ValidationError):
            HoldingCreate(
                krx_code="AAPL", quantity=5, avg_buy_price=Decimal("180.00"),
                market="TSE", currency="JPY",
            )


class TestHoldingResponseIncludesMarketCurrency:
    """HoldingResponse — market/currency 필드 포함 여부 검증"""

    def test_response_has_market_and_currency(self):
        """응답에 market, currency 필드가 포함되어야 함"""
        from datetime import datetime
        h = HoldingResponse(
            id=1,
            portfolio_id=1,
            krx_code="005930",
            quantity=10,
            avg_buy_price=Decimal("70000"),
            added_at=datetime.now(),
            market="KRX",
            currency="KRW",
        )
        assert h.market == "KRX"
        assert h.currency == "KRW"


class TestHoldingPerformanceForeignAsset:
    """HoldingPerformance — market, currency, fx_rate_used 필드 검증"""

    def test_has_market_currency_fx_rate_fields(self):
        """HoldingPerformance에 market, currency, fx_rate_used 필드가 있어야 함"""
        hp = HoldingPerformance(
            krx_code="AAPL",
            quantity=5,
            avg_buy_price=180.0,
            current_price=190.0,
            return_pct=5.56,
            market="NYSE",
            currency="USD",
            fx_rate_used=1320.5,
        )
        assert hp.market == "NYSE"
        assert hp.currency == "USD"
        assert hp.fx_rate_used == pytest.approx(1320.5)

    def test_fx_rate_used_defaults_to_none(self):
        """fx_rate_used 기본값은 None (KRX 종목)"""
        hp = HoldingPerformance(
            krx_code="005930",
            quantity=10,
            avg_buy_price=70000.0,
            current_price=75000.0,
            return_pct=7.14,
        )
        assert hp.fx_rate_used is None
