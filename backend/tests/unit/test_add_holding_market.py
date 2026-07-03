# add_holding 서비스 — market/currency 파라미터 및 409 충돌 처리 테스트 (SPEC-STOCK-028 T-005)
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
import sqlalchemy.exc

from stock_picker.portfolio import service
from stock_picker.db.models import PortfolioHolding


class TestAddHoldingWithMarket:
    """add_holding — market/currency 파라미터 지원 검증"""

    def test_add_holding_default_market_is_krx(self):
        """market 기본값이 KRX인지 검증"""
        db = MagicMock()
        captured: list[PortfolioHolding] = []

        def mock_add(holding: PortfolioHolding) -> None:
            captured.append(holding)

        db.add.side_effect = mock_add

        service.add_holding(
            db,
            portfolio_id=1,
            krx_code="005930",
            quantity=10,
            avg_buy_price=Decimal("70000"),
        )

        assert len(captured) == 1
        assert captured[0].market == "KRX"
        assert captured[0].currency == "KRW"

    def test_add_holding_with_nyse_market(self):
        """NYSE market과 USD currency로 holding 생성"""
        db = MagicMock()
        captured: list[PortfolioHolding] = []

        def mock_add(holding: PortfolioHolding) -> None:
            captured.append(holding)

        db.add.side_effect = mock_add

        service.add_holding(
            db,
            portfolio_id=1,
            krx_code="AAPL",
            quantity=5,
            avg_buy_price=Decimal("180.00"),
            market="NYSE",
            currency="USD",
        )

        assert captured[0].market == "NYSE"
        assert captured[0].currency == "USD"
        assert captured[0].krx_code == "AAPL"

    def test_add_holding_integrity_error_propagates(self):
        """중복 종목 삽입 시 IntegrityError 전파 (router에서 409 처리)"""
        db = MagicMock()
        db.commit.side_effect = sqlalchemy.exc.IntegrityError(
            "UNIQUE constraint failed", params=None, orig=None
        )

        with pytest.raises(sqlalchemy.exc.IntegrityError):
            service.add_holding(
                db,
                portfolio_id=1,
                krx_code="005930",
                quantity=10,
                avg_buy_price=Decimal("70000"),
            )
