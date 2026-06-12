# 포트폴리오 서비스 유닛 테스트 — mock DB + 성과 계산 검증
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from stock_picker.portfolio import service
from stock_picker.db.models import Portfolio, PortfolioHolding


def _make_portfolio(id: int = 1, user_id: int = 1, name: str = "테스트 포트폴리오") -> Portfolio:
    """테스트용 Portfolio 인스턴스 생성"""
    p = Portfolio()
    p.id = id
    p.user_id = user_id
    p.name = name
    p.holdings = []
    return p


def _make_holding(
    id: int = 1,
    portfolio_id: int = 1,
    krx_code: str = "005930",
    quantity: int = 10,
    avg_buy_price: Decimal = Decimal("70000.00"),
) -> PortfolioHolding:
    """테스트용 PortfolioHolding 인스턴스 생성"""
    h = PortfolioHolding()
    h.id = id
    h.portfolio_id = portfolio_id
    h.krx_code = krx_code
    h.quantity = quantity
    h.avg_buy_price = avg_buy_price
    return h


class TestCreatePortfolio:
    """create_portfolio 테스트"""

    def test_creates_and_returns_portfolio(self):
        """포트폴리오 생성 후 반환값 검증"""
        db = MagicMock()

        # db.refresh는 포트폴리오 속성을 업데이트하는 것처럼 시뮬레이션
        def mock_refresh(portfolio):
            portfolio.id = 1

        db.refresh.side_effect = mock_refresh

        portfolio = service.create_portfolio(db, user_id=1, name="내 포트폴리오")

        db.add.assert_called_once()
        db.commit.assert_called_once()
        assert portfolio.user_id == 1
        assert portfolio.name == "내 포트폴리오"

    def test_commits_to_db(self):
        """DB 커밋이 호출되는지 검증"""
        db = MagicMock()
        service.create_portfolio(db, user_id=2, name="포트폴리오B")
        db.commit.assert_called_once()


class TestListPortfolios:
    """list_portfolios 테스트"""

    def test_returns_user_portfolios(self):
        """사용자 ID로 필터링된 포트폴리오 목록 반환"""
        db = MagicMock()
        expected = [_make_portfolio(1, 1), _make_portfolio(2, 1)]
        db.query.return_value.filter.return_value.all.return_value = expected

        result = service.list_portfolios(db, user_id=1)
        assert result == expected

    def test_returns_empty_when_no_portfolios(self):
        """포트폴리오가 없을 때 빈 목록 반환"""
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []

        result = service.list_portfolios(db, user_id=99)
        assert result == []


class TestGetPortfolioWithHoldings:
    """get_portfolio_with_holdings 테스트"""

    def test_returns_none_when_not_found(self):
        """포트폴리오 미발견 시 None 반환"""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        result = service.get_portfolio_with_holdings(db, portfolio_id=999, user_id=1)
        assert result is None

    def test_returns_portfolio_with_holdings(self):
        """포트폴리오와 보유 종목을 함께 반환"""
        db = MagicMock()
        portfolio = _make_portfolio()
        holdings = [_make_holding()]

        # 첫 번째 query().filter().first()는 portfolio 반환
        db.query.return_value.filter.return_value.first.return_value = portfolio
        # 두 번째 query().filter().all()는 holdings 반환
        db.query.return_value.filter.return_value.all.return_value = holdings

        result = service.get_portfolio_with_holdings(db, portfolio_id=1, user_id=1)
        assert result is not None


class TestAddHolding:
    """add_holding 테스트"""

    def test_adds_holding_to_portfolio(self):
        """보유 종목 추가 후 반환값 검증"""
        db = MagicMock()

        def mock_refresh(holding):
            holding.id = 1

        db.refresh.side_effect = mock_refresh

        holding = service.add_holding(
            db,
            portfolio_id=1,
            krx_code="005930",
            quantity=10,
            avg_buy_price=Decimal("70000"),
        )

        db.add.assert_called_once()
        db.commit.assert_called_once()
        assert holding.krx_code == "005930"
        assert holding.quantity == 10

    def test_holding_values_preserved(self):
        """추가한 종목 정보가 정확히 저장되는지 검증"""
        db = MagicMock()
        holding = service.add_holding(
            db,
            portfolio_id=5,
            krx_code="000660",
            quantity=20,
            avg_buy_price=Decimal("150000"),
        )
        assert holding.portfolio_id == 5
        assert holding.krx_code == "000660"
        assert holding.quantity == 20


class TestRemoveHolding:
    """remove_holding 테스트"""

    def test_deletes_existing_holding(self):
        """존재하는 보유 종목 삭제"""
        db = MagicMock()
        holding = _make_holding()
        db.query.return_value.filter.return_value.first.return_value = holding

        service.remove_holding(db, holding_id=1)

        db.delete.assert_called_once_with(holding)
        db.commit.assert_called_once()

    def test_noop_when_holding_not_found(self):
        """존재하지 않는 보유 종목 삭제 시 에러 없이 통과"""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        # 예외 없이 실행되어야 함
        service.remove_holding(db, holding_id=999)
        db.delete.assert_not_called()


class TestCalculatePerformance:
    """calculate_performance 테스트"""

    def test_returns_empty_when_portfolio_not_found(self):
        """포트폴리오 미발견 시 빈 성과 반환"""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        result = service.calculate_performance(db, portfolio_id=999, user_id=1)

        assert result["holdings"] == []
        assert result["total_invested"] == 0.0
        assert result["total_current"] == 0.0
        assert result["total_return_pct"] == 0.0

    def test_calculates_positive_return(self):
        """수익 발생 시 양수 수익률 계산"""
        db = MagicMock()
        portfolio = _make_portfolio()
        holding = _make_holding(avg_buy_price=Decimal("70000"), quantity=10)
        portfolio.holdings = [holding]

        # get_portfolio_with_holdings가 portfolio 반환하도록 설정
        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = [holding]

        # 현재가를 75000으로 mocking (SPEC-STOCK-017: get_current_price → dict 반환)
        with patch(
            "stock_picker.portfolio.service.get_current_price",
            return_value={"price": 75000.0},
        ):
            result = service.calculate_performance(db, portfolio_id=1, user_id=1)

        assert result["total_invested"] == 700000.0
        assert result["total_current"] == 750000.0
        assert result["total_return_pct"] == pytest.approx(7.14, abs=0.01)

    def test_calculates_negative_return(self):
        """손실 발생 시 음수 수익률 계산"""
        db = MagicMock()
        portfolio = _make_portfolio()
        holding = _make_holding(avg_buy_price=Decimal("70000"), quantity=10)
        portfolio.holdings = [holding]

        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = [holding]

        with patch(
            "stock_picker.portfolio.service.get_current_price",
            return_value={"price": 63000.0},
        ):
            result = service.calculate_performance(db, portfolio_id=1, user_id=1)

        assert result["total_return_pct"] == pytest.approx(-10.0, abs=0.01)

    def test_uses_buy_price_when_current_price_unavailable(self):
        """현재가 조회 실패 시 매수가로 대체 (수익률 0%)"""
        db = MagicMock()
        portfolio = _make_portfolio()
        holding = _make_holding(avg_buy_price=Decimal("70000"), quantity=5)
        portfolio.holdings = [holding]

        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = [holding]

        with patch(
            "stock_picker.portfolio.service.get_current_price",
            return_value=None,
        ):
            result = service.calculate_performance(db, portfolio_id=1, user_id=1)

        assert result["total_return_pct"] == 0.0
