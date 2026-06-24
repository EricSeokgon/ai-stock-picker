# 배당 수익률 분석 강화 단위 테스트 (SPEC-STOCK-033)
# TDD RED-GREEN-REFACTOR 사이클
# asyncio_mode = "auto" — @pytest.mark.asyncio 불필요
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ──────────────────────────────────────────────────────────────
# NFR-001: scipy 미사용 검증
# ──────────────────────────────────────────────────────────────


class TestNoScipyInDividendYield:
    """scipy import 금지 검증 (NFR-001)"""

    def test_no_scipy_in_dividend_yield(self):
        """dividend_yield.py는 scipy를 import하면 안 된다"""
        import ast
        import os

        module_path = os.path.join(
            os.path.dirname(__file__),
            "../../src/stock_picker/portfolio/dividend_yield.py",
        )
        module_path = os.path.normpath(module_path)
        with open(module_path) as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert "scipy" not in alias.name, "scipy import 금지 (NFR-001)"
                else:
                    assert node.module is None or "scipy" not in node.module, \
                        "scipy import 금지 (NFR-001)"


# ──────────────────────────────────────────────────────────────
# 순수 함수 테스트 — calculate_dividend_summary
# ──────────────────────────────────────────────────────────────


def _make_holding_data(
    krx_code: str,
    stock_name: str,
    shares: int,
    current_price: float,
    annual_dps: float,
) -> dict:
    """테스트용 보유 종목 딕셔너리 생성 헬퍼"""
    return {
        "krx_code": krx_code,
        "stock_name": stock_name,
        "shares": shares,
        "current_price": current_price,
        "annual_dps": annual_dps,
    }


class TestCalculateDividendSummary:
    """calculate_dividend_summary 순수 함수 테스트"""

    def test_basic_summary_with_dividend_data(self):
        """배당 데이터 있는 보유 종목 → 올바른 가중 평균 수익률 계산"""
        from stock_picker.portfolio.dividend_yield import calculate_dividend_summary

        holdings = [
            _make_holding_data("005930", "삼성전자", 10, 70_000.0, 1_400.0),  # 2% yield
        ]
        result = calculate_dividend_summary(portfolio_id=1, holdings=holdings)

        assert result.portfolio_id == 1
        # estimated_annual_dividend = 10 * 1400 = 14,000
        assert abs(result.total_annual_dividend - 14_000.0) < 0.01
        # dividend_yield_pct = 1400 / 70000 * 100 = 2.0%
        assert abs(result.portfolio_dividend_yield_pct - 2.0) < 0.01

    def test_holding_with_no_dividend_data(self):
        """배당 데이터 없는 보유 종목 → annual_dps=0, yield=0"""
        from stock_picker.portfolio.dividend_yield import calculate_dividend_summary

        holdings = [
            _make_holding_data("000270", "기아", 5, 110_000.0, 0.0),
        ]
        result = calculate_dividend_summary(portfolio_id=2, holdings=holdings)

        assert result.total_annual_dividend == 0.0
        assert result.portfolio_dividend_yield_pct == 0.0
        assert len(result.holdings) == 1
        assert result.holdings[0].dividend_yield_pct == 0.0

    def test_empty_holdings_returns_zero(self):
        """보유 종목 없음 → total=0, yield=0"""
        from stock_picker.portfolio.dividend_yield import calculate_dividend_summary

        result = calculate_dividend_summary(portfolio_id=3, holdings=[])

        assert result.total_annual_dividend == 0.0
        assert result.portfolio_dividend_yield_pct == 0.0
        assert result.holdings == []

    def test_weighted_yield_formula(self):
        """가중 평균 수익률 공식: Σ(value_i * yield_i) / total_value (단순 평균 아님)"""
        from stock_picker.portfolio.dividend_yield import calculate_dividend_summary

        # A: 100주 @ 100원, DPS=2 → yield=2%, 가치=10,000원
        # B: 100주 @ 10원, DPS=1 → yield=10%, 가치=1,000원
        # 가중 평균 = (10000*2 + 1000*10) / (10000+1000) = 30000/11000 ≈ 2.727%
        holdings = [
            _make_holding_data("AAA", "A종목", 100, 100.0, 2.0),
            _make_holding_data("BBB", "B종목", 100, 10.0, 1.0),
        ]
        result = calculate_dividend_summary(portfolio_id=4, holdings=holdings)

        expected_yield = (10_000 * 2.0 + 1_000 * 10.0) / (10_000 + 1_000)
        assert abs(result.portfolio_dividend_yield_pct - expected_yield) < 0.001

    def test_zero_total_value_yields_zero_pct(self):
        """total_portfolio_value=0이면 portfolio_dividend_yield_pct=0"""
        from stock_picker.portfolio.dividend_yield import calculate_dividend_summary

        # current_price=0 → 포트폴리오 가치 0
        holdings = [
            _make_holding_data("AAA", "A종목", 0, 0.0, 0.0),
        ]
        result = calculate_dividend_summary(portfolio_id=5, holdings=holdings)

        assert result.portfolio_dividend_yield_pct == 0.0

    def test_holding_dividend_yield_pct_per_stock(self):
        """각 보유 종목별 dividend_yield_pct = annual_dps / current_price * 100"""
        from stock_picker.portfolio.dividend_yield import calculate_dividend_summary

        holdings = [
            _make_holding_data("005930", "삼성전자", 10, 70_000.0, 1_400.0),
        ]
        result = calculate_dividend_summary(portfolio_id=6, holdings=holdings)

        h = result.holdings[0]
        assert h.krx_code == "005930"
        assert abs(h.dividend_yield_pct - 2.0) < 0.001
        assert abs(h.annual_dps - 1_400.0) < 0.01
        assert abs(h.estimated_annual_dividend - 14_000.0) < 0.01

    def test_total_portfolio_value_field(self):
        """total_portfolio_value = Σ(shares * current_price)"""
        from stock_picker.portfolio.dividend_yield import calculate_dividend_summary

        holdings = [
            _make_holding_data("005930", "삼성전자", 10, 70_000.0, 1_400.0),
            _make_holding_data("000660", "SK하이닉스", 5, 80_000.0, 800.0),
        ]
        result = calculate_dividend_summary(portfolio_id=7, holdings=holdings)

        expected_value = 10 * 70_000 + 5 * 80_000
        assert abs(result.total_portfolio_value - expected_value) < 0.01


# ──────────────────────────────────────────────────────────────
# 순수 함수 테스트 — calculate_drip_projection
# ──────────────────────────────────────────────────────────────


class TestCalculateDripProjection:
    """calculate_drip_projection 순수 함수 테스트 (DRIP 복리 공식)"""

    def test_year_0_equals_initial_value(self):
        """year 0 = initial_value, cumulative_return=0"""
        from stock_picker.portfolio.dividend_yield import calculate_drip_projection

        result = calculate_drip_projection(
            portfolio_id=1,
            initial_value=1_000_000.0,
            dividend_yield_pct=5.0,
            reinvest_rate=1.0,
            years=3,
        )

        year0 = result.years[0]
        assert year0.year == 0
        assert abs(year0.portfolio_value - 1_000_000.0) < 0.01
        assert abs(year0.cumulative_return_pct - 0.0) < 0.001

    def test_year_1_drip_formula(self):
        """year 1: value[1] = initial * (1 + yield * rate), correct cumulative"""
        from stock_picker.portfolio.dividend_yield import calculate_drip_projection

        initial = 1_000_000.0
        yield_pct = 5.0
        rate = 1.0

        result = calculate_drip_projection(
            portfolio_id=1,
            initial_value=initial,
            dividend_yield_pct=yield_pct,
            reinvest_rate=rate,
            years=3,
        )

        year1 = result.years[1]
        expected_value = initial * (1 + yield_pct / 100 * rate)  # 1,050,000
        expected_cumulative = (expected_value / initial - 1) * 100  # 5.0%

        assert abs(year1.portfolio_value - expected_value) < 0.01
        assert abs(year1.cumulative_return_pct - expected_cumulative) < 0.001

    def test_reinvest_rate_zero_flat_portfolio(self):
        """reinvest_rate=0 → 포트폴리오 가치 유지 (복리 없음)"""
        from stock_picker.portfolio.dividend_yield import calculate_drip_projection

        result = calculate_drip_projection(
            portfolio_id=1,
            initial_value=1_000_000.0,
            dividend_yield_pct=5.0,
            reinvest_rate=0.0,  # 전혀 재투자 안 함
            years=5,
        )

        for yr in result.years:
            assert abs(yr.portfolio_value - 1_000_000.0) < 0.01

    def test_correct_number_of_years(self):
        """years 파라미터만큼 + 1 (year 0 포함) 데이터 포인트 생성"""
        from stock_picker.portfolio.dividend_yield import calculate_drip_projection

        result = calculate_drip_projection(
            portfolio_id=1,
            initial_value=1_000_000.0,
            dividend_yield_pct=5.0,
            reinvest_rate=1.0,
            years=10,
        )

        assert len(result.years) == 11  # year 0~10

    def test_disclaimer_present(self):
        """disclaimer 문자열이 결과에 포함되어야 한다"""
        from stock_picker.portfolio.dividend_yield import calculate_drip_projection

        result = calculate_drip_projection(
            portfolio_id=1,
            initial_value=1_000_000.0,
            dividend_yield_pct=5.0,
            reinvest_rate=1.0,
            years=5,
        )

        assert result.disclaimer != ""
        assert "참고용" in result.disclaimer or "시뮬레이션" in result.disclaimer

    def test_annual_dividend_uses_previous_year_value(self):
        """annual_dividend[t] = value[t-1] * yield (value[t] 아님)"""
        from stock_picker.portfolio.dividend_yield import calculate_drip_projection

        initial = 1_000_000.0
        yield_pct = 5.0

        result = calculate_drip_projection(
            portfolio_id=1,
            initial_value=initial,
            dividend_yield_pct=yield_pct,
            reinvest_rate=1.0,
            years=3,
        )

        # year 1: annual_dividend = value[0] * yield/100 = 1,000,000 * 0.05 = 50,000
        year1 = result.years[1]
        expected_annual_div = initial * yield_pct / 100
        assert abs(year1.annual_dividend - expected_annual_div) < 0.01

    def test_compounding_effect_over_multiple_years(self):
        """복리 효과 — year 2 가치가 단리보다 크다"""
        from stock_picker.portfolio.dividend_yield import calculate_drip_projection

        initial = 1_000_000.0
        yield_pct = 5.0

        result = calculate_drip_projection(
            portfolio_id=1,
            initial_value=initial,
            dividend_yield_pct=yield_pct,
            reinvest_rate=1.0,
            years=3,
        )

        year2 = result.years[2]
        # 단리 2년: 1,000,000 + 2*50,000 = 1,100,000
        simple_interest_2yr = initial + 2 * (initial * yield_pct / 100)
        # 복리는 더 커야 한다
        assert year2.portfolio_value > simple_interest_2yr

    def test_result_fields(self):
        """DRIPProjection 필드 검증"""
        from stock_picker.portfolio.dividend_yield import calculate_drip_projection

        result = calculate_drip_projection(
            portfolio_id=42,
            initial_value=500_000.0,
            dividend_yield_pct=3.0,
            reinvest_rate=0.5,
            years=5,
        )

        assert result.portfolio_id == 42
        assert abs(result.initial_value - 500_000.0) < 0.01
        assert abs(result.dividend_yield_pct - 3.0) < 0.001
        assert abs(result.reinvest_rate - 0.5) < 0.001


# ──────────────────────────────────────────────────────────────
# 순수 함수 테스트 — calculate_dividend_calendar
# ──────────────────────────────────────────────────────────────


def _make_div_event(
    krx_code: str,
    stock_name: str,
    ex_dividend_date: date,
    payment_date,
    dps: float,
    shares: int,
) -> dict:
    """테스트용 배당 이벤트 딕셔너리 생성 헬퍼"""
    return {
        "krx_code": krx_code,
        "stock_name": stock_name,
        "ex_dividend_date": ex_dividend_date,
        "payment_date": payment_date,
        "dps": dps,
        "shares": shares,
    }


class TestCalculateDividendCalendar:
    """calculate_dividend_calendar 순수 함수 테스트"""

    def test_events_grouped_by_month(self):
        """이벤트가 월별로 올바르게 그룹화되어야 한다"""
        from stock_picker.portfolio.dividend_yield import calculate_dividend_calendar

        events = [
            _make_div_event("005930", "삼성전자", date(2025, 3, 28), date(2025, 4, 20), 1400.0, 10),
            _make_div_event("000660", "SK하이닉스", date(2025, 3, 29), None, 800.0, 5),
            _make_div_event("035420", "NAVER", date(2025, 6, 28), date(2025, 7, 20), 500.0, 20),
        ]
        result = calculate_dividend_calendar(portfolio_id=1, year=2025, events=events)

        assert result.portfolio_id == 1
        assert result.year == 2025
        # 3월에 2개, 6월에 1개
        assert 3 in result.months
        assert 6 in result.months
        assert len(result.months[3]) == 2
        assert len(result.months[6]) == 1

    def test_events_with_none_payment_date_are_valid(self):
        """payment_date=None인 이벤트도 유효하게 처리되어야 한다"""
        from stock_picker.portfolio.dividend_yield import calculate_dividend_calendar

        events = [
            _make_div_event("000660", "SK하이닉스", date(2025, 3, 29), None, 800.0, 5),
        ]
        result = calculate_dividend_calendar(portfolio_id=1, year=2025, events=events)

        assert 3 in result.months
        event = result.months[3][0]
        assert event.payment_date is None
        assert event.krx_code == "000660"

    def test_year_filter_excludes_different_years(self):
        """다른 연도의 이벤트는 제외되어야 한다"""
        from stock_picker.portfolio.dividend_yield import calculate_dividend_calendar

        events = [
            _make_div_event("005930", "삼성전자", date(2024, 3, 28), None, 1400.0, 10),  # 2024
            _make_div_event("000660", "SK하이닉스", date(2025, 3, 28), None, 800.0, 5),  # 2025
        ]
        result = calculate_dividend_calendar(portfolio_id=1, year=2025, events=events)

        # 2025년 이벤트만 포함
        total_events = sum(len(v) for v in result.months.values())
        assert total_events == 1
        assert result.months[3][0].krx_code == "000660"

    def test_estimated_total_calculation(self):
        """estimated_total = shares * dps"""
        from stock_picker.portfolio.dividend_yield import calculate_dividend_calendar

        events = [
            _make_div_event("005930", "삼성전자", date(2025, 3, 28), None, 1400.0, 10),
        ]
        result = calculate_dividend_calendar(portfolio_id=1, year=2025, events=events)

        event = result.months[3][0]
        assert abs(event.estimated_total - 14_000.0) < 0.01


# ──────────────────────────────────────────────────────────────
# API 엔드포인트 테스트 (소유권 404)
# ──────────────────────────────────────────────────────────────


class TestDividendYieldAPIOwnership:
    """API 소유권 검증 테스트 (HTTP 404 반환)"""

    @pytest.mark.asyncio
    async def test_summary_returns_404_when_not_owned(self):
        """소유하지 않은 포트폴리오 summary 조회 시 404를 반환해야 한다"""
        from fastapi import HTTPException
        from stock_picker.portfolio.dividend_yield import get_dividend_summary

        with patch(
            "stock_picker.portfolio.dividend_yield.portfolio_service.get_portfolio_with_holdings",
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_dividend_summary(
                    portfolio_id=9999,
                    user_id=1,
                    db=MagicMock(),
                    redis=AsyncMock(),
                )
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_calendar_returns_404_when_not_owned(self):
        """소유하지 않은 포트폴리오 calendar 조회 시 404를 반환해야 한다"""
        from fastapi import HTTPException
        from stock_picker.portfolio.dividend_yield import get_dividend_calendar

        with patch(
            "stock_picker.portfolio.dividend_yield.portfolio_service.get_portfolio_with_holdings",
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_dividend_calendar(
                    portfolio_id=9999,
                    user_id=1,
                    db=MagicMock(),
                    redis=AsyncMock(),
                    year=2025,
                )
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_drip_returns_404_when_not_owned(self):
        """소유하지 않은 포트폴리오 drip 조회 시 404를 반환해야 한다"""
        from fastapi import HTTPException
        from stock_picker.portfolio.dividend_yield import get_drip_projection

        with patch(
            "stock_picker.portfolio.dividend_yield.portfolio_service.get_portfolio_with_holdings",
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_drip_projection(
                    portfolio_id=9999,
                    user_id=1,
                    db=MagicMock(),
                    redis=AsyncMock(),
                    years=10,
                    reinvest_rate=1.0,
                )
            assert exc_info.value.status_code == 404


# ──────────────────────────────────────────────────────────────
# 서비스 오케스트레이션 테스트 (커버리지 향상)
# ──────────────────────────────────────────────────────────────


def _make_holding_mock(krx_code: str, quantity: int, avg_buy_price: float) -> MagicMock:
    """테스트용 holding ORM 목 객체 생성"""
    h = MagicMock()
    h.krx_code = krx_code
    h.quantity = quantity
    h.avg_buy_price = avg_buy_price
    return h


class TestGetDividendSummaryService:
    """get_dividend_summary 서비스 오케스트레이션 테스트"""

    @pytest.mark.asyncio
    async def test_returns_summary_with_holdings(self):
        """보유 종목 있을 때 DividendSummary 반환"""
        from stock_picker.portfolio.dividend_yield import get_dividend_summary

        portfolio_mock = MagicMock()
        portfolio_mock.holdings = [
            _make_holding_mock("005930", 10, 70_000.0),
        ]

        div_info = {
            "krx_code": "005930",
            "name": "삼성전자",
            "dps": 1400.0,
            "dividend_yield": 2.0,
            "dividend_available": True,
        }

        with patch(
            "stock_picker.portfolio.dividend_yield.portfolio_service.get_portfolio_with_holdings",
            return_value=portfolio_mock,
        ), patch(
            "stock_picker.portfolio.dividend_yield.get_dividend_info",
            new_callable=AsyncMock,
            return_value=div_info,
        ):
            result = await get_dividend_summary(
                portfolio_id=1,
                user_id=1,
                db=MagicMock(),
                redis=AsyncMock(),
            )

        assert result.portfolio_id == 1
        assert len(result.holdings) == 1
        assert result.holdings[0].krx_code == "005930"

    @pytest.mark.asyncio
    async def test_empty_holdings_returns_zero_summary(self):
        """보유 종목 없을 때 빈 요약 반환"""
        from stock_picker.portfolio.dividend_yield import get_dividend_summary

        portfolio_mock = MagicMock()
        portfolio_mock.holdings = []

        with patch(
            "stock_picker.portfolio.dividend_yield.portfolio_service.get_portfolio_with_holdings",
            return_value=portfolio_mock,
        ):
            result = await get_dividend_summary(
                portfolio_id=1,
                user_id=1,
                db=MagicMock(),
                redis=AsyncMock(),
            )

        assert result.total_annual_dividend == 0.0
        assert result.holdings == []


class TestGetDividendCalendarService:
    """get_dividend_calendar 서비스 오케스트레이션 테스트"""

    @pytest.mark.asyncio
    async def test_returns_calendar_with_available_dividends(self):
        """배당 가능 종목이 있으면 캘린더 반환"""
        from stock_picker.portfolio.dividend_yield import get_dividend_calendar

        portfolio_mock = MagicMock()
        portfolio_mock.holdings = [
            _make_holding_mock("005930", 10, 70_000.0),
        ]

        div_info = {
            "krx_code": "005930",
            "name": "삼성전자",
            "dps": 1400.0,
            "dividend_yield": 2.0,
            "ex_dividend_month": 3,
            "dividend_available": True,
        }

        with patch(
            "stock_picker.portfolio.dividend_yield.portfolio_service.get_portfolio_with_holdings",
            return_value=portfolio_mock,
        ), patch(
            "stock_picker.portfolio.dividend_yield.get_dividend_info",
            new_callable=AsyncMock,
            return_value=div_info,
        ):
            result = await get_dividend_calendar(
                portfolio_id=1,
                user_id=1,
                db=MagicMock(),
                redis=AsyncMock(),
                year=2025,
            )

        assert result.portfolio_id == 1
        assert result.year == 2025
        assert 3 in result.months

    @pytest.mark.asyncio
    async def test_skips_holdings_without_ex_month(self):
        """ex_dividend_month 없는 종목은 캘린더에서 제외"""
        from stock_picker.portfolio.dividend_yield import get_dividend_calendar

        portfolio_mock = MagicMock()
        portfolio_mock.holdings = [
            _make_holding_mock("000660", 5, 80_000.0),
        ]

        div_info = {
            "krx_code": "000660",
            "name": "SK하이닉스",
            "dps": 800.0,
            "dividend_yield": 1.0,
            "ex_dividend_month": None,  # 없음
            "dividend_available": True,
        }

        with patch(
            "stock_picker.portfolio.dividend_yield.portfolio_service.get_portfolio_with_holdings",
            return_value=portfolio_mock,
        ), patch(
            "stock_picker.portfolio.dividend_yield.get_dividend_info",
            new_callable=AsyncMock,
            return_value=div_info,
        ):
            result = await get_dividend_calendar(
                portfolio_id=1,
                user_id=1,
                db=MagicMock(),
                redis=AsyncMock(),
                year=2025,
            )

        assert result.months == {}


class TestGetDripProjectionService:
    """get_drip_projection 서비스 오케스트레이션 테스트"""

    @pytest.mark.asyncio
    async def test_returns_drip_projection(self):
        """포트폴리오 있을 때 DRIP 시뮬레이션 반환"""
        from stock_picker.portfolio.dividend_yield import get_drip_projection

        portfolio_mock = MagicMock()
        portfolio_mock.holdings = [
            _make_holding_mock("005930", 10, 70_000.0),
        ]

        div_info = {
            "krx_code": "005930",
            "name": "삼성전자",
            "dps": 1400.0,
            "dividend_yield": 2.0,
            "dividend_available": True,
        }

        with patch(
            "stock_picker.portfolio.dividend_yield.portfolio_service.get_portfolio_with_holdings",
            return_value=portfolio_mock,
        ), patch(
            "stock_picker.portfolio.dividend_yield.get_dividend_info",
            new_callable=AsyncMock,
            return_value=div_info,
        ):
            result = await get_drip_projection(
                portfolio_id=1,
                user_id=1,
                db=MagicMock(),
                redis=AsyncMock(),
                years=5,
                reinvest_rate=1.0,
            )

        assert result.portfolio_id == 1
        assert len(result.years) == 6  # year 0~5
        assert result.disclaimer != ""

    @pytest.mark.asyncio
    async def test_empty_portfolio_uses_default_initial_value(self):
        """보유 종목 없으면 기본 초기값 1,000,000원 사용"""
        from stock_picker.portfolio.dividend_yield import get_drip_projection

        portfolio_mock = MagicMock()
        portfolio_mock.holdings = []

        with patch(
            "stock_picker.portfolio.dividend_yield.portfolio_service.get_portfolio_with_holdings",
            return_value=portfolio_mock,
        ):
            result = await get_drip_projection(
                portfolio_id=1,
                user_id=1,
                db=MagicMock(),
                redis=AsyncMock(),
                years=3,
                reinvest_rate=1.0,
            )

        assert abs(result.initial_value - 1_000_000.0) < 0.01


# ──────────────────────────────────────────────────────────────
# 스키마 검증 테스트
# ──────────────────────────────────────────────────────────────


class TestDividendYieldSchemas:
    """Pydantic 스키마 검증 테스트"""

    def test_holding_dividend_schema(self):
        """DividendHolding 스키마 생성 검증 (SPEC-033 전용 클래스)"""
        from stock_picker.portfolio.schemas import DividendHolding

        h = DividendHolding(
            krx_code="005930",
            stock_name="삼성전자",
            shares=10,
            annual_dps=1400.0,
            dividend_yield_pct=2.0,
            estimated_annual_dividend=14000.0,
        )
        assert h.krx_code == "005930"
        assert h.shares == 10
        assert abs(h.estimated_annual_dividend - 14000.0) < 0.01

    def test_dividend_summary_schema(self):
        """DividendSummary 스키마 생성 검증"""
        from stock_picker.portfolio.schemas import DividendHolding, DividendSummary

        h = DividendHolding(
            krx_code="005930",
            stock_name="삼성전자",
            shares=10,
            annual_dps=1400.0,
            dividend_yield_pct=2.0,
            estimated_annual_dividend=14000.0,
        )
        summary = DividendSummary(
            portfolio_id=1,
            total_portfolio_value=700_000.0,
            total_annual_dividend=14_000.0,
            portfolio_dividend_yield_pct=2.0,
            holdings=[h],
        )
        assert summary.portfolio_id == 1
        assert len(summary.holdings) == 1

    def test_drip_year_data_schema(self):
        """DRIPYearData 스키마 생성 검증"""
        from stock_picker.portfolio.schemas import DRIPYearData

        yr = DRIPYearData(
            year=1,
            portfolio_value=1_050_000.0,
            annual_dividend=50_000.0,
            cumulative_return_pct=5.0,
        )
        assert yr.year == 1
        assert abs(yr.cumulative_return_pct - 5.0) < 0.001

    def test_drip_projection_schema(self):
        """DRIPProjection 스키마 생성 검증 (disclaimer 필수)"""
        from stock_picker.portfolio.schemas import DRIPProjection, DRIPYearData

        projection = DRIPProjection(
            portfolio_id=1,
            initial_value=1_000_000.0,
            dividend_yield_pct=5.0,
            reinvest_rate=1.0,
            years=[
                DRIPYearData(year=0, portfolio_value=1_000_000.0, annual_dividend=0.0, cumulative_return_pct=0.0),
            ],
            disclaimer="배당률 고정, 가격 성장 미반영 — 참고용 시뮬레이션입니다",
        )
        assert projection.disclaimer != ""
        assert "참고용" in projection.disclaimer

    def test_dividend_event_schema(self):
        """DividendEvent 스키마 생성 검증 (payment_date Optional)"""
        from stock_picker.portfolio.schemas import DividendEvent

        evt = DividendEvent(
            krx_code="005930",
            stock_name="삼성전자",
            ex_dividend_date=date(2025, 3, 28),
            payment_date=None,
            dps=1400.0,
            shares=10,
            estimated_total=14_000.0,
        )
        assert evt.payment_date is None
        assert abs(evt.estimated_total - 14_000.0) < 0.01

    def test_dividend_calendar_schema(self):
        """DividendCalendar 스키마 생성 검증"""
        from stock_picker.portfolio.schemas import DividendCalendar, DividendEvent

        evt = DividendEvent(
            krx_code="005930",
            stock_name="삼성전자",
            ex_dividend_date=date(2025, 3, 28),
            payment_date=None,
            dps=1400.0,
            shares=10,
            estimated_total=14_000.0,
        )
        cal = DividendCalendar(
            portfolio_id=1,
            year=2025,
            months={3: [evt]},
        )
        assert cal.year == 2025
        assert 3 in cal.months
        assert len(cal.months[3]) == 1
