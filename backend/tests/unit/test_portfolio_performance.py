# SPEC-STOCK-017 성과 분류·섹터 집계 단위 테스트
# SPEC-STOCK-028 T-006: calculate_performance async 전환 반영
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from stock_picker.portfolio import service
from stock_picker.portfolio.utils import get_sector
from stock_picker.db.models import Portfolio, PortfolioHolding


def _make_portfolio(id: int = 1, user_id: int = 1, name: str = "테스트") -> Portfolio:
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
    market: str = "KRX",
    currency: str = "KRW",
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


# ────────────────────────────────────────────────────────────────────────────
# REQ-PERF-001: 수익률 계산 — (현재가 − 매입가) / 매입가 × 100
# ────────────────────────────────────────────────────────────────────────────
class TestReturnPctCalculation:
    """수익률 계산 공식 검증"""

    @pytest.mark.asyncio
    async def test_positive_return_is_correct(self):
        """매입가 70000 → 현재가 75000: 수익률 ≈ +7.14%"""
        db = MagicMock()
        portfolio = _make_portfolio()
        holding = _make_holding(avg_buy_price=Decimal("70000"), quantity=10)
        portfolio.holdings = [holding]

        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = [holding]
        redis = AsyncMock()

        with patch(
            "stock_picker.portfolio.service.get_current_price",
            return_value={"price": 75000.0},
        ):
            result = await service.calculate_performance(db, portfolio_id=1, user_id=1, redis=redis)

        assert result["holdings"][0]["return_pct"] == pytest.approx(7.14, abs=0.01)

    @pytest.mark.asyncio
    async def test_negative_return_is_correct(self):
        """매입가 70000 → 현재가 63000: 수익률 = -10.00%"""
        db = MagicMock()
        portfolio = _make_portfolio()
        holding = _make_holding(avg_buy_price=Decimal("70000"), quantity=10)
        portfolio.holdings = [holding]

        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = [holding]
        redis = AsyncMock()

        with patch(
            "stock_picker.portfolio.service.get_current_price",
            return_value={"price": 63000.0},
        ):
            result = await service.calculate_performance(db, portfolio_id=1, user_id=1, redis=redis)

        assert result["holdings"][0]["return_pct"] == pytest.approx(-10.0, abs=0.01)


# ────────────────────────────────────────────────────────────────────────────
# REQ-PERF-003: 성과 분류 — high / normal / low
# ────────────────────────────────────────────────────────────────────────────
class TestHoldingClassification:
    """보유 종목 성과 분류 검증"""

    async def _run(self, buy_price: float, current_price: float, quantity: int = 10) -> dict:
        """공통 setup — 단일 holding 성과 계산"""
        db = MagicMock()
        portfolio = _make_portfolio()
        holding = _make_holding(
            avg_buy_price=Decimal(str(buy_price)), quantity=quantity
        )
        portfolio.holdings = [holding]

        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = [holding]
        redis = AsyncMock()

        with patch(
            "stock_picker.portfolio.service.get_current_price",
            return_value={"price": current_price},
        ):
            result = await service.calculate_performance(db, portfolio_id=1, user_id=1, redis=redis)

        return result["holdings"][0]

    @pytest.mark.asyncio
    async def test_high_when_return_above_5_pct(self):
        """수익률 >= +5.0% → classification = 'high'"""
        holding = await self._run(70000, 75000)
        assert holding["classification"] == "high"

    @pytest.mark.asyncio
    async def test_high_boundary_exactly_5_pct(self):
        """수익률 = +5.0% → classification = 'high'"""
        holding = await self._run(100000, 105000)
        assert holding["classification"] == "high"

    @pytest.mark.asyncio
    async def test_normal_when_return_between_minus5_and_plus5(self):
        """수익률 0% → classification = 'normal'"""
        holding = await self._run(70000, 70000)
        assert holding["classification"] == "normal"

    @pytest.mark.asyncio
    async def test_normal_just_below_high(self):
        """수익률 +4.99% → classification = 'normal'"""
        # 100000 → 104990 = +4.99%
        holding = await self._run(100000, 104990)
        assert holding["classification"] == "normal"

    @pytest.mark.asyncio
    async def test_low_when_return_below_minus5_pct(self):
        """수익률 <= -5.0% → classification = 'low'"""
        holding = await self._run(70000, 63000)
        assert holding["classification"] == "low"

    @pytest.mark.asyncio
    async def test_low_boundary_exactly_minus5_pct(self):
        """수익률 = -5.0% → classification = 'low'"""
        holding = await self._run(100000, 95000)
        assert holding["classification"] == "low"


# ────────────────────────────────────────────────────────────────────────────
# REQ-PERF-007·008: 가격 실패 / 0 나눗셈 방지
# ────────────────────────────────────────────────────────────────────────────
class TestPriceUnavailable:
    """현재가 조회 실패 처리"""

    @pytest.mark.asyncio
    async def test_price_unavailable_flag_set_when_get_current_price_returns_none(self):
        """get_current_price → None 시 price_unavailable=True, return_pct=0"""
        db = MagicMock()
        portfolio = _make_portfolio()
        holding = _make_holding(avg_buy_price=Decimal("70000"), quantity=5)
        portfolio.holdings = [holding]

        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = [holding]
        redis = AsyncMock()

        with patch(
            "stock_picker.portfolio.service.get_current_price",
            return_value=None,
        ):
            result = await service.calculate_performance(db, portfolio_id=1, user_id=1, redis=redis)

        h = result["holdings"][0]
        assert h["price_unavailable"] is True
        assert h["return_pct"] == 0.0

    @pytest.mark.asyncio
    async def test_zero_buy_price_yields_return_pct_zero(self):
        """매입가 0 → 0 나눗셈 방지 → return_pct=0.0"""
        db = MagicMock()
        portfolio = _make_portfolio()
        holding = _make_holding(avg_buy_price=Decimal("0"), quantity=10)
        portfolio.holdings = [holding]

        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = [holding]
        redis = AsyncMock()

        with patch(
            "stock_picker.portfolio.service.get_current_price",
            return_value={"price": 50000.0},
        ):
            result = await service.calculate_performance(db, portfolio_id=1, user_id=1, redis=redis)

        assert result["holdings"][0]["return_pct"] == 0.0


# ────────────────────────────────────────────────────────────────────────────
# REQ-PERF-009: 빈 포트폴리오
# ────────────────────────────────────────────────────────────────────────────
class TestEmptyPortfolio:
    """빈 포트폴리오 응답 검증"""

    @pytest.mark.asyncio
    async def test_empty_holdings_returns_zero_summary(self):
        """보유 종목 없을 때 빈 holdings + 0 값"""
        db = MagicMock()
        portfolio = _make_portfolio()
        portfolio.holdings = []

        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = []
        redis = AsyncMock()

        result = await service.calculate_performance(db, portfolio_id=1, user_id=1, redis=redis)

        assert result["holdings"] == []
        assert result["total_invested"] == 0.0
        assert result["total_current"] == 0.0
        assert result["total_return_pct"] == 0.0
        assert result["classification_summary"]["high"]["count"] == 0
        assert result["classification_summary"]["normal"]["count"] == 0
        assert result["classification_summary"]["low"]["count"] == 0
        assert result["sector_performance"] == []


# ────────────────────────────────────────────────────────────────────────────
# REQ-PERF-004: 섹터별 수익률 집계
# ────────────────────────────────────────────────────────────────────────────
class TestSectorPerformance:
    """섹터별 수익률 집계 검증"""

    @pytest.mark.asyncio
    async def test_sector_performance_groups_same_sector(self):
        """동일 섹터 종목들이 하나의 섹터 항목으로 집계됨"""
        db = MagicMock()
        portfolio = _make_portfolio()
        # 005930 and 005380 둘 다 "005" prefix → "전자/반도체" 섹터
        h1 = _make_holding(id=1, krx_code="005930", quantity=10, avg_buy_price=Decimal("70000"))
        h2 = _make_holding(id=2, krx_code="005380", quantity=5, avg_buy_price=Decimal("200000"))
        portfolio.holdings = [h1, h2]

        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = [h1, h2]
        redis = AsyncMock()

        def mock_price(krx_code: str):
            prices = {"005930": 75000.0, "005380": 200000.0}
            p = prices.get(krx_code, 0.0)
            return {"price": p} if p > 0 else None

        with patch("stock_picker.portfolio.service.get_current_price", side_effect=mock_price):
            result = await service.calculate_performance(db, portfolio_id=1, user_id=1, redis=redis)

        sectors = {s["sector"]: s for s in result["sector_performance"]}
        assert "전자/반도체" in sectors
        # 005380은 현재가 = 매입가이므로 return_pct = 0, 합산 수익률은 투자금 가중 평균
        elec_sector = sectors["전자/반도체"]
        assert elec_sector["holding_count"] == 2

    @pytest.mark.asyncio
    async def test_sector_performance_sorted_by_invested_desc(self):
        """sector_performance는 투자금 내림차순 정렬"""
        db = MagicMock()
        portfolio = _make_portfolio()
        # 01 prefix → 자동차, 투자금 적음
        h_auto = _make_holding(id=1, krx_code="012330", quantity=1, avg_buy_price=Decimal("100000"))
        # 005 prefix → 전자/반도체, 투자금 많음
        h_elec = _make_holding(id=2, krx_code="005930", quantity=100, avg_buy_price=Decimal("70000"))
        portfolio.holdings = [h_auto, h_elec]

        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = [h_auto, h_elec]
        redis = AsyncMock()

        def mock_price(krx_code: str):
            return {"price": float({"012330": 100000, "005930": 70000}[krx_code])}

        with patch("stock_picker.portfolio.service.get_current_price", side_effect=mock_price):
            result = await service.calculate_performance(db, portfolio_id=1, user_id=1, redis=redis)

        invested_values = [s["invested"] for s in result["sector_performance"]]
        assert invested_values == sorted(invested_values, reverse=True)


# ────────────────────────────────────────────────────────────────────────────
# REQ-PERF-006: classification_summary 검증
# ────────────────────────────────────────────────────────────────────────────
class TestClassificationSummary:
    """classification_summary 필드 검증"""

    @pytest.mark.asyncio
    async def test_classification_summary_counts_are_correct(self):
        """고/일반/저수익 종목 수 집계"""
        db = MagicMock()
        portfolio = _make_portfolio()
        # 수익률 +7.14% → high
        h1 = _make_holding(id=1, krx_code="005930", quantity=10, avg_buy_price=Decimal("70000"))
        # 수익률 0% → normal
        h2 = _make_holding(id=2, krx_code="000660", quantity=5, avg_buy_price=Decimal("100000"))
        # 수익률 -10% → low
        h3 = _make_holding(id=3, krx_code="012330", quantity=3, avg_buy_price=Decimal("50000"))
        portfolio.holdings = [h1, h2, h3]

        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = [h1, h2, h3]
        redis = AsyncMock()

        def mock_price(krx_code: str):
            prices = {"005930": 75000.0, "000660": 100000.0, "012330": 45000.0}
            return {"price": prices[krx_code]}

        with patch("stock_picker.portfolio.service.get_current_price", side_effect=mock_price):
            result = await service.calculate_performance(db, portfolio_id=1, user_id=1, redis=redis)

        summary = result["classification_summary"]
        assert summary["high"]["count"] == 1
        assert summary["normal"]["count"] == 1
        assert summary["low"]["count"] == 1

    @pytest.mark.asyncio
    async def test_classification_summary_invested_pct_sums_to_100(self):
        """invested_pct 합계는 100.0"""
        db = MagicMock()
        portfolio = _make_portfolio()
        h1 = _make_holding(id=1, krx_code="005930", quantity=10, avg_buy_price=Decimal("70000"))
        h2 = _make_holding(id=2, krx_code="000660", quantity=5, avg_buy_price=Decimal("100000"))
        portfolio.holdings = [h1, h2]

        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = [h1, h2]
        redis = AsyncMock()

        def mock_price(krx_code: str):
            prices = {"005930": 75000.0, "000660": 100000.0}
            return {"price": prices[krx_code]}

        with patch("stock_picker.portfolio.service.get_current_price", side_effect=mock_price):
            result = await service.calculate_performance(db, portfolio_id=1, user_id=1, redis=redis)

        summary = result["classification_summary"]
        total_pct = (
            summary["high"]["invested_pct"]
            + summary["normal"]["invested_pct"]
            + summary["low"]["invested_pct"]
        )
        assert total_pct == pytest.approx(100.0, abs=0.1)
