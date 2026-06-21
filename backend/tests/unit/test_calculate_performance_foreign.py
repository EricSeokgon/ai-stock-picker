# calculate_performance — 해외 자산(NYSE/NASDAQ) 지원 테스트 (SPEC-STOCK-028 T-006)
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from stock_picker.portfolio import service
from stock_picker.db.models import Portfolio, PortfolioHolding


def _make_portfolio(id: int = 1, user_id: int = 1) -> Portfolio:
    p = Portfolio()
    p.id = id
    p.user_id = user_id
    p.name = "테스트"
    p.holdings = []
    return p


def _make_holding(
    id: int = 1,
    portfolio_id: int = 1,
    krx_code: str = "AAPL",
    quantity: int = 5,
    avg_buy_price: Decimal = Decimal("180.00"),
    market: str = "NYSE",
    currency: str = "USD",
) -> PortfolioHolding:
    h = PortfolioHolding()
    h.id = id
    h.portfolio_id = portfolio_id
    h.krx_code = krx_code
    h.quantity = quantity
    h.avg_buy_price = avg_buy_price
    h.market = market
    h.currency = currency
    return h


class TestCalculatePerformanceForeignAsset:
    """calculate_performance — 해외 자산 KRW 환산 및 수익률 계산"""

    @pytest.mark.asyncio
    async def test_foreign_asset_converts_price_to_krw(self):
        """해외 종목: USD 현재가 × fx_rate = KRW 환산가로 수익률 계산"""
        db = MagicMock()
        portfolio = _make_portfolio()
        holding = _make_holding(
            krx_code="AAPL", quantity=5,
            avg_buy_price=Decimal("180.00"),
            market="NYSE", currency="USD",
        )
        portfolio.holdings = [holding]

        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = [holding]

        redis = AsyncMock()

        # USD 현재가 190.0, 환율 1300.0
        with (
            patch("stock_picker.portfolio.service._fetch_foreign_price", return_value=190.0),
            patch("stock_picker.portfolio.fx_rate.get_usd_krw_rate", return_value=1300.0),
        ):
            result = await service.calculate_performance(db, 1, 1, redis)

        # 매수가: 180 * 1300 = 234000 KRW
        # 현재가: 190 * 1300 = 247000 KRW
        # 수익률: (247000 - 234000) / 234000 * 100 ≈ 5.56%
        assert len(result["holdings"]) == 1
        hp = result["holdings"][0]
        assert hp["krx_code"] == "AAPL"
        assert hp["return_pct"] == pytest.approx(5.56, abs=0.01)
        assert hp["fx_rate_used"] == pytest.approx(1300.0)
        assert hp["market"] == "NYSE"
        assert hp["currency"] == "USD"

    @pytest.mark.asyncio
    async def test_foreign_asset_price_unavailable_sets_flag(self):
        """해외 종목 현재가 미수신 시 price_unavailable=True, 수익률 0%"""
        db = MagicMock()
        portfolio = _make_portfolio()
        holding = _make_holding()
        portfolio.holdings = [holding]

        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = [holding]

        redis = AsyncMock()

        with (
            patch("stock_picker.portfolio.service._fetch_foreign_price", return_value=None),
            patch("stock_picker.portfolio.fx_rate.get_usd_krw_rate", return_value=1300.0),
        ):
            result = await service.calculate_performance(db, 1, 1, redis)

        hp = result["holdings"][0]
        assert hp["price_unavailable"] is True
        assert hp["return_pct"] == 0.0

    @pytest.mark.asyncio
    async def test_krx_holding_still_uses_existing_get_current_price(self):
        """KRX 종목은 기존 get_current_price 사용 (하위 호환)"""
        db = MagicMock()
        portfolio = _make_portfolio()
        krx_holding = _make_holding(
            krx_code="005930", quantity=10,
            avg_buy_price=Decimal("70000"),
            market="KRX", currency="KRW",
        )
        portfolio.holdings = [krx_holding]

        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = [krx_holding]

        redis = AsyncMock()

        with patch(
            "stock_picker.portfolio.service.get_current_price",
            return_value={"price": 75000.0},
        ):
            result = await service.calculate_performance(db, 1, 1, redis)

        hp = result["holdings"][0]
        assert hp["krx_code"] == "005930"
        assert hp["return_pct"] == pytest.approx(7.14, abs=0.01)
        assert hp["fx_rate_used"] is None

    @pytest.mark.asyncio
    async def test_foreign_sector_returns_empty_string(self):
        """해외 종목 섹터는 None/빈 문자열 반환 (예외 없음)"""
        db = MagicMock()
        portfolio = _make_portfolio()
        holding = _make_holding()
        portfolio.holdings = [holding]

        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = [holding]

        redis = AsyncMock()

        with (
            patch("stock_picker.portfolio.service._fetch_foreign_price", return_value=190.0),
            patch("stock_picker.portfolio.fx_rate.get_usd_krw_rate", return_value=1300.0),
        ):
            result = await service.calculate_performance(db, 1, 1, redis)

        hp = result["holdings"][0]
        # 섹터는 빈 문자열 또는 "기타" — 예외 없이 반환되어야 함
        assert isinstance(hp.get("sector", ""), str)
