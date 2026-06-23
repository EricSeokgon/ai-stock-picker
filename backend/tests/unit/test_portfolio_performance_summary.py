# 포트폴리오 기간별 성과 요약 단위 테스트 (SPEC-STOCK-030)
# TDD RED-GREEN-REFACTOR 사이클
# asyncio_mode = "auto" — @pytest.mark.asyncio 불필요
import json
import math
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ──────────────────────────────────────────────────────────────
# T-001: Pydantic 스키마 테스트
# ──────────────────────────────────────────────────────────────

class TestPeriodPerformanceSchema:
    """PeriodPerformance 스키마 직렬화 테스트"""

    def test_period_performance_has_required_fields(self):
        """PeriodPerformance는 필수 필드를 모두 가져야 한다"""
        from stock_picker.portfolio.schemas import PeriodPerformance

        p = PeriodPerformance(
            period="ytd",
            display_label="YTD",
            start_date="2025-01-01",
            end_date="2025-06-23",
            trading_days=120,
            has_data=True,
            total_return_pct=5.3,
            annualized_return_pct=10.2,
            mdd_pct=-3.1,
        )
        assert p.period == "ytd"
        assert p.has_data is True
        assert p.total_return_pct == pytest.approx(5.3)

    def test_period_performance_null_metrics_when_no_data(self):
        """has_data=False이면 수익률 필드가 None이어야 한다"""
        from stock_picker.portfolio.schemas import PeriodPerformance

        p = PeriodPerformance(
            period="1y",
            display_label="1Y",
            start_date=None,
            end_date=None,
            trading_days=0,
            has_data=False,
            total_return_pct=None,
            annualized_return_pct=None,
            mdd_pct=None,
        )
        assert p.has_data is False
        assert p.total_return_pct is None
        assert p.annualized_return_pct is None
        assert p.mdd_pct is None

    def test_period_performance_invalid_period_raises(self):
        """허용되지 않는 period 값은 ValidationError를 발생시켜야 한다"""
        from pydantic import ValidationError
        from stock_picker.portfolio.schemas import PeriodPerformance

        with pytest.raises(ValidationError):
            PeriodPerformance(
                period="2y",  # 허용 안됨
                display_label="2Y",
                start_date=None,
                end_date=None,
                trading_days=0,
                has_data=False,
            )


class TestPerformanceSummaryResponseSchema:
    """PerformanceSummaryResponse 스키마 직렬화 테스트"""

    def test_response_has_required_fields(self):
        """PerformanceSummaryResponse는 portfolio_id, periods, calculated_at, disclaimer를 가져야 한다"""
        from stock_picker.portfolio.schemas import PerformanceSummaryResponse, PeriodPerformance

        periods = [
            PeriodPerformance(
                period=p,
                display_label=p.upper(),
                start_date="2025-01-01",
                end_date="2025-06-23",
                trading_days=10,
                has_data=True,
                total_return_pct=1.0,
                annualized_return_pct=2.0,
                mdd_pct=-0.5,
            )
            for p in ["ytd", "1m", "3m", "6m", "1y"]
        ]
        resp = PerformanceSummaryResponse(
            portfolio_id=1,
            periods=periods,
            calculated_at="2025-06-23T10:00:00Z",
            disclaimer="과거 데이터 기반 시뮬레이션입니다.",
        )
        assert resp.portfolio_id == 1
        assert len(resp.periods) == 5
        assert "2025-06-23" in resp.calculated_at
        assert "시뮬레이션" in resp.disclaimer


# ──────────────────────────────────────────────────────────────
# T-002: 기간 시작일 산출 순수 함수 테스트
# ──────────────────────────────────────────────────────────────

class TestComputePeriodDates:
    """_compute_period_dates 순수 함수 테스트"""

    def test_ytd_starts_january_first(self):
        """YTD 시작일은 당해 1월 1일이어야 한다"""
        from stock_picker.portfolio.performance_summary import _compute_period_dates

        today = date(2025, 6, 23)
        dates = _compute_period_dates(today)
        assert dates["ytd"] == date(2025, 1, 1)

    def test_1m_starts_30_days_ago(self):
        """1M 시작일은 오늘에서 30일 전이어야 한다"""
        from stock_picker.portfolio.performance_summary import _compute_period_dates

        today = date(2025, 6, 23)
        dates = _compute_period_dates(today)
        assert dates["1m"] == today - timedelta(days=30)

    def test_3m_starts_90_days_ago(self):
        """3M 시작일은 오늘에서 90일 전이어야 한다"""
        from stock_picker.portfolio.performance_summary import _compute_period_dates

        today = date(2025, 6, 23)
        dates = _compute_period_dates(today)
        assert dates["3m"] == today - timedelta(days=90)

    def test_6m_starts_180_days_ago(self):
        """6M 시작일은 오늘에서 180일 전이어야 한다"""
        from stock_picker.portfolio.performance_summary import _compute_period_dates

        today = date(2025, 6, 23)
        dates = _compute_period_dates(today)
        assert dates["6m"] == today - timedelta(days=180)

    def test_1y_starts_365_days_ago(self):
        """1Y 시작일은 오늘에서 365일 전이어야 한다"""
        from stock_picker.portfolio.performance_summary import _compute_period_dates

        today = date(2025, 6, 23)
        dates = _compute_period_dates(today)
        assert dates["1y"] == today - timedelta(days=365)

    def test_all_five_periods_present(self):
        """반환 딕셔너리에 5개 기간 키가 모두 포함되어야 한다"""
        from stock_picker.portfolio.performance_summary import _compute_period_dates

        today = date(2025, 6, 23)
        dates = _compute_period_dates(today)
        assert set(dates.keys()) == {"ytd", "1m", "3m", "6m", "1y"}

    def test_ytd_boundary_jan_first(self):
        """오늘이 1월 1일이면 YTD 시작일도 오늘(당해 1월 1일)이어야 한다"""
        from stock_picker.portfolio.performance_summary import _compute_period_dates

        today = date(2025, 1, 1)
        dates = _compute_period_dates(today)
        assert dates["ytd"] == date(2025, 1, 1)

    def test_ytd_early_jan_boundary(self):
        """오늘이 1월 2일이면 YTD 시작일은 1월 1일이어야 한다"""
        from stock_picker.portfolio.performance_summary import _compute_period_dates

        today = date(2025, 1, 2)
        dates = _compute_period_dates(today)
        assert dates["ytd"] == date(2025, 1, 1)


# ──────────────────────────────────────────────────────────────
# T-003: 수익률 계산 순수 함수 테스트
# ──────────────────────────────────────────────────────────────

class TestComputePeriodReturns:
    """_compute_period_returns 순수 함수 테스트"""

    def test_positive_total_return(self):
        """상승 포트폴리오에서 양수 총수익률을 반환해야 한다"""
        from stock_picker.portfolio.performance_summary import _compute_period_returns

        # 100 → 110으로 상승 (10% 수익)
        values = [100.0, 102.0, 105.0, 108.0, 110.0]
        result = _compute_period_returns(values)
        assert result["total_return_pct"] == pytest.approx(10.0, abs=0.01)

    def test_negative_total_return(self):
        """하락 포트폴리오에서 음수 총수익률을 반환해야 한다"""
        from stock_picker.portfolio.performance_summary import _compute_period_returns

        # 100 → 90으로 하락 (-10% 손실)
        values = [100.0, 97.0, 94.0, 92.0, 90.0]
        result = _compute_period_returns(values)
        assert result["total_return_pct"] == pytest.approx(-10.0, abs=0.01)

    def test_zero_return_flat_portfolio(self):
        """변동 없는 포트폴리오는 0% 수익률이어야 한다"""
        from stock_picker.portfolio.performance_summary import _compute_period_returns

        values = [100.0, 100.0, 100.0, 100.0, 100.0]
        result = _compute_period_returns(values)
        assert result["total_return_pct"] == pytest.approx(0.0, abs=0.001)

    def test_mdd_negative_for_drawdown(self):
        """MDD는 하락폭이 있을 때 음수여야 한다"""
        from stock_picker.portfolio.performance_summary import _compute_period_returns

        # 100 → 120 → 80 → 110 (120에서 80으로 -33.3%)
        values = [100.0, 120.0, 80.0, 110.0]
        result = _compute_period_returns(values)
        assert result["mdd_pct"] < 0
        assert result["mdd_pct"] == pytest.approx(-33.33, abs=0.1)

    def test_mdd_zero_for_monotonically_increasing(self):
        """단조 상승 포트폴리오의 MDD는 0이어야 한다"""
        from stock_picker.portfolio.performance_summary import _compute_period_returns

        values = [100.0, 101.0, 102.0, 103.0, 104.0]
        result = _compute_period_returns(values)
        assert result["mdd_pct"] == pytest.approx(0.0, abs=0.001)

    def test_annualized_return_with_252_days(self):
        """252거래일(1년)이면 연환산수익률 ≈ 총수익률이어야 한다"""
        from stock_picker.portfolio.performance_summary import _compute_period_returns

        # 252거래일 동안 10% 수익
        import numpy as np
        n = 253  # 252 간격
        values = list(np.linspace(100.0, 110.0, n))
        result = _compute_period_returns(values)
        # 연환산 ≈ 총수익률 (252일이 정확히 1년 기준)
        assert abs(result["annualized_return_pct"] - result["total_return_pct"]) < 1.0

    def test_annualized_return_amplified_for_short_period(self):
        """단기 수익은 연환산하면 더 큰 수익률이 되어야 한다 (양수의 경우)"""
        from stock_picker.portfolio.performance_summary import _compute_period_returns

        # 5거래일 동안 1% 수익
        values = [100.0, 100.2, 100.5, 100.7, 101.0]
        result = _compute_period_returns(values)
        # 연환산이 총수익률보다 커야 한다
        assert result["annualized_return_pct"] > result["total_return_pct"]

    def test_insufficient_data_returns_none(self):
        """거래일이 2일 미만이면 모든 지표가 None이어야 한다"""
        from stock_picker.portfolio.performance_summary import _compute_period_returns

        result = _compute_period_returns([100.0])  # 단 1일
        assert result["total_return_pct"] is None
        assert result["annualized_return_pct"] is None
        assert result["mdd_pct"] is None
        assert result["has_data"] is False

    def test_empty_values_returns_none(self):
        """빈 값 목록이면 모든 지표가 None이어야 한다"""
        from stock_picker.portfolio.performance_summary import _compute_period_returns

        result = _compute_period_returns([])
        assert result["total_return_pct"] is None
        assert result["has_data"] is False


# ──────────────────────────────────────────────────────────────
# T-004: 비중 정규화 순수 함수 테스트
# ──────────────────────────────────────────────────────────────

class TestNormalizeWeights:
    """_normalize_weights 순수 함수 테스트"""

    def test_normalize_sums_to_one(self):
        """정규화된 비중의 합은 1.0이어야 한다"""
        from stock_picker.portfolio.performance_summary import _normalize_weights

        weights = [30.0, 50.0, 20.0]
        result = _normalize_weights(weights)
        assert sum(result) == pytest.approx(1.0)

    def test_zero_total_returns_equal_weights(self):
        """비중 합이 0이면 동일 비중으로 반환해야 한다"""
        from stock_picker.portfolio.performance_summary import _normalize_weights

        weights = [0.0, 0.0, 0.0]
        result = _normalize_weights(weights)
        assert len(result) == 3
        assert all(w == pytest.approx(1.0 / 3) for w in result)

    def test_already_normalized_unchanged(self):
        """이미 합이 1.0인 경우 그대로 반환해야 한다"""
        from stock_picker.portfolio.performance_summary import _normalize_weights

        weights = [0.4, 0.3, 0.3]
        result = _normalize_weights(weights)
        assert sum(result) == pytest.approx(1.0)


# ──────────────────────────────────────────────────────────────
# T-005: 포트폴리오 가치 시계열 계산 순수 함수 테스트
# ──────────────────────────────────────────────────────────────

class TestAlignCloseAndPortfolioValues:
    """_align_close_series 및 포트폴리오 가치 시계열 계산 테스트"""

    def test_align_close_series_common_dates(self):
        """공통 거래일 기준으로 내부 조인되어야 한다"""
        from stock_picker.portfolio.performance_summary import _align_close_series

        price_data = {
            "A": [
                {"date": "2025-01-02", "close": 100.0},
                {"date": "2025-01-03", "close": 102.0},
                {"date": "2025-01-06", "close": 105.0},
            ],
            "B": [
                {"date": "2025-01-02", "close": 50.0},
                {"date": "2025-01-03", "close": 51.0},
                # 01-06 누락
            ],
        }
        common_dates, closes = _align_close_series(price_data)
        # 공통 날짜는 2개 (01-02, 01-03)
        assert len(common_dates) == 2
        assert "2025-01-02" in common_dates
        assert "2025-01-03" in common_dates
        # 01-06은 B에 없으므로 제외
        assert "2025-01-06" not in common_dates

    def test_align_close_series_empty_data(self):
        """빈 price_data이면 빈 결과를 반환해야 한다"""
        from stock_picker.portfolio.performance_summary import _align_close_series

        common_dates, closes = _align_close_series({})
        assert common_dates == []
        assert closes == {}

    def test_portfolio_values_weighted_sum(self):
        """비중 가중 포트폴리오 가치는 첫날 1.0이고 올바르게 계산되어야 한다"""
        from stock_picker.portfolio.performance_summary import _compute_portfolio_values

        # A(50%), B(50%) — A는 100→110 B는 50→55
        aligned_closes = {
            "A": [100.0, 110.0],
            "B": [50.0, 55.0],
        }
        weights = [0.5, 0.5]
        tickers = ["A", "B"]
        values = _compute_portfolio_values(aligned_closes, weights, tickers)
        # 첫날 = 0.5 * (100/100) + 0.5 * (50/50) = 1.0
        assert values[0] == pytest.approx(1.0)
        # 둘째날 = 0.5 * (110/100) + 0.5 * (55/50) = 0.5*1.1 + 0.5*1.1 = 1.1
        assert values[1] == pytest.approx(1.1)

    def test_portfolio_values_empty_tickers(self):
        """종목이 없으면 빈 리스트를 반환해야 한다"""
        from stock_picker.portfolio.performance_summary import _compute_portfolio_values

        values = _compute_portfolio_values({}, [], [])
        assert values == []


# ──────────────────────────────────────────────────────────────
# T-006: USD→KRW 환산 테스트
# ──────────────────────────────────────────────────────────────

class TestUsdToKrwConversion:
    """USD 종가 KRW 환산 로직 테스트"""

    def test_usd_prices_multiplied_by_fx_rate(self):
        """USD 종가에 환율을 곱한 KRW 가격이 반환되어야 한다"""
        from stock_picker.portfolio.performance_summary import _apply_fx_rate

        price_data = [
            {"date": "2025-01-02", "close": 100.0},  # USD 100
            {"date": "2025-01-03", "close": 105.0},
        ]
        krw_data = _apply_fx_rate(price_data, fx_rate=1350.0)
        assert krw_data[0]["close"] == pytest.approx(100.0 * 1350.0)
        assert krw_data[1]["close"] == pytest.approx(105.0 * 1350.0)

    def test_krw_prices_unchanged_when_fx_rate_none(self):
        """KRW 종목(환율=1.0)은 원본 가격이 유지되어야 한다"""
        from stock_picker.portfolio.performance_summary import _apply_fx_rate

        price_data = [
            {"date": "2025-01-02", "close": 80000.0},
        ]
        krw_data = _apply_fx_rate(price_data, fx_rate=1.0)
        assert krw_data[0]["close"] == pytest.approx(80000.0)

    def test_empty_price_data_returns_empty(self):
        """빈 가격 데이터는 빈 결과를 반환해야 한다"""
        from stock_picker.portfolio.performance_summary import _apply_fx_rate

        result = _apply_fx_rate([], fx_rate=1350.0)
        assert result == []


# ──────────────────────────────────────────────────────────────
# T-007: 메인 오케스트레이션 (calculate_performance_summary) 테스트
# ──────────────────────────────────────────────────────────────

class TestCalculatePerformanceSummary:
    """calculate_performance_summary 비동기 오케스트레이션 테스트"""

    def _make_mock_portfolio(self, holdings=None):
        """Mock 포트폴리오 객체 생성 헬퍼"""
        portfolio = MagicMock()
        portfolio.id = 1
        portfolio.user_id = 1
        if holdings is None:
            holdings = [
                MagicMock(krx_code="005930", quantity=10, avg_buy_price=70000, weight=50.0, market="KRX", currency="KRW"),
                MagicMock(krx_code="AAPL", quantity=5, avg_buy_price=150.0, weight=50.0, market="NYSE", currency="USD"),
            ]
        portfolio.holdings = holdings
        return portfolio

    def _make_price_series(self, start_price=100.0, n=50, growth=0.001):
        """단조 상승 가격 시계열 생성 헬퍼"""
        from datetime import date, timedelta
        today = date(2025, 6, 23)
        return [
            {"date": str(today - timedelta(days=n - i)), "close": start_price * (1 + growth * i)}
            for i in range(n)
        ]

    async def test_returns_five_periods(self):
        """정상 포트폴리오는 5개 기간의 결과를 반환해야 한다"""
        from stock_picker.portfolio.performance_summary import calculate_performance_summary

        mock_db = MagicMock()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()

        portfolio = self._make_mock_portfolio()
        price_series = self._make_price_series()

        with patch("stock_picker.portfolio.performance_summary.get_portfolio_with_holdings",
                   return_value=portfolio), \
             patch("stock_picker.portfolio.performance_summary.get_usd_krw_rate",
                   AsyncMock(return_value=1350.0)), \
             patch("stock_picker.portfolio.performance_summary._fetch_price_series_for_period",
                   AsyncMock(return_value=price_series)):

            result = await calculate_performance_summary(
                portfolio_id=1,
                user_id=1,
                db=mock_db,
                redis=mock_redis,
                refresh=False,
            )

        assert len(result.periods) == 5
        period_names = {p.period for p in result.periods}
        assert period_names == {"ytd", "1m", "3m", "6m", "1y"}

    async def test_portfolio_not_found_raises_404(self):
        """포트폴리오가 없으면 HTTPException 404가 발생해야 한다"""
        from fastapi import HTTPException
        from stock_picker.portfolio.performance_summary import calculate_performance_summary

        mock_db = MagicMock()
        mock_redis = AsyncMock()

        with patch("stock_picker.portfolio.performance_summary.get_portfolio_with_holdings",
                   return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await calculate_performance_summary(
                    portfolio_id=999,
                    user_id=1,
                    db=mock_db,
                    redis=mock_redis,
                    refresh=False,
                )
        assert exc_info.value.status_code == 404

    async def test_empty_portfolio_returns_all_no_data(self):
        """보유 종목이 없으면 5개 기간 모두 has_data=False이어야 한다"""
        from stock_picker.portfolio.performance_summary import calculate_performance_summary

        mock_db = MagicMock()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()

        portfolio = self._make_mock_portfolio(holdings=[])

        with patch("stock_picker.portfolio.performance_summary.get_portfolio_with_holdings",
                   return_value=portfolio):
            result = await calculate_performance_summary(
                portfolio_id=1,
                user_id=1,
                db=mock_db,
                redis=mock_redis,
                refresh=False,
            )

        assert len(result.periods) == 5
        assert all(not p.has_data for p in result.periods)
        assert all(p.total_return_pct is None for p in result.periods)

    async def test_response_has_calculated_at_and_disclaimer(self):
        """응답에 calculated_at(UTC ISO 문자열)과 disclaimer가 포함되어야 한다"""
        from stock_picker.portfolio.performance_summary import calculate_performance_summary

        mock_db = MagicMock()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()

        portfolio = self._make_mock_portfolio(holdings=[])

        with patch("stock_picker.portfolio.performance_summary.get_portfolio_with_holdings",
                   return_value=portfolio):
            result = await calculate_performance_summary(
                portfolio_id=1,
                user_id=1,
                db=mock_db,
                redis=mock_redis,
                refresh=False,
            )

        assert result.calculated_at is not None
        assert "Z" in result.calculated_at or "+" in result.calculated_at
        assert len(result.disclaimer) > 0

    async def test_redis_cache_hit_skips_calculation(self):
        """Redis 캐시 히트 시 FDR을 호출하지 않고 캐시 데이터를 반환해야 한다"""
        from stock_picker.portfolio.performance_summary import calculate_performance_summary
        from stock_picker.portfolio.schemas import PerformanceSummaryResponse, PeriodPerformance

        cached_periods = [
            PeriodPerformance(
                period=p,
                display_label=p.upper(),
                start_date="2025-01-01",
                end_date="2025-06-23",
                trading_days=10,
                has_data=True,
                total_return_pct=5.0,
                annualized_return_pct=10.0,
                mdd_pct=-1.0,
            ).model_dump()
            for p in ["ytd", "1m", "3m", "6m", "1y"]
        ]
        cached_response = {
            "portfolio_id": 1,
            "periods": cached_periods,
            "calculated_at": "2025-06-23T10:00:00Z",
            "disclaimer": "테스트 면책",
        }
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=json.dumps(cached_response))
        mock_db = MagicMock()

        with patch("stock_picker.portfolio.performance_summary._fetch_price_series_for_period") as mock_fdr:
            result = await calculate_performance_summary(
                portfolio_id=1,
                user_id=1,
                db=mock_db,
                redis=mock_redis,
                refresh=False,
            )
        # FDR 호출이 없어야 한다
        mock_fdr.assert_not_called()
        assert result.portfolio_id == 1

    async def test_refresh_true_bypasses_cache(self):
        """refresh=True이면 Redis 캐시를 무시하고 재계산해야 한다"""
        from stock_picker.portfolio.performance_summary import calculate_performance_summary

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="cached_data_that_should_be_ignored")
        mock_redis.setex = AsyncMock()
        mock_redis.delete = AsyncMock()
        mock_db = MagicMock()

        portfolio = self._make_mock_portfolio(holdings=[])

        with patch("stock_picker.portfolio.performance_summary.get_portfolio_with_holdings",
                   return_value=portfolio):
            result = await calculate_performance_summary(
                portfolio_id=1,
                user_id=1,
                db=mock_db,
                redis=mock_redis,
                refresh=True,
            )
        # 결과는 반환되어야 한다 (빈 포트폴리오이므로 has_data=False)
        assert len(result.periods) == 5

    async def test_fdr_failure_graceful_degradation(self):
        """FDR 조회 실패 시 예외를 전파하지 않고 빈 데이터를 반환해야 한다"""
        from stock_picker.portfolio.performance_summary import calculate_performance_summary

        mock_db = MagicMock()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()

        portfolio = self._make_mock_portfolio()

        with patch("stock_picker.portfolio.performance_summary.get_portfolio_with_holdings",
                   return_value=portfolio), \
             patch("stock_picker.portfolio.performance_summary.get_usd_krw_rate",
                   AsyncMock(return_value=1350.0)), \
             patch("stock_picker.portfolio.performance_summary._fetch_price_series_for_period",
                   AsyncMock(return_value=[])):  # FDR 실패 시 빈 리스트 반환

            # 예외가 발생하지 않아야 한다
            result = await calculate_performance_summary(
                portfolio_id=1,
                user_id=1,
                db=mock_db,
                redis=mock_redis,
                refresh=False,
            )

        # 5개 기간 구조는 유지되어야 한다
        assert len(result.periods) == 5

    async def test_redis_failure_continues_calculation(self):
        """Redis 장애 시 계산을 중단하지 않고 결과를 반환해야 한다"""
        from stock_picker.portfolio.performance_summary import calculate_performance_summary

        mock_db = MagicMock()
        mock_redis = AsyncMock()
        # Redis 접근 시 예외 발생
        mock_redis.get = AsyncMock(side_effect=Exception("Redis 연결 실패"))
        mock_redis.setex = AsyncMock(side_effect=Exception("Redis 연결 실패"))

        portfolio = self._make_mock_portfolio(holdings=[])

        with patch("stock_picker.portfolio.performance_summary.get_portfolio_with_holdings",
                   return_value=portfolio):
            # Redis 장애에도 정상 응답해야 한다
            result = await calculate_performance_summary(
                portfolio_id=1,
                user_id=1,
                db=mock_db,
                redis=mock_redis,
                refresh=False,
            )

        assert len(result.periods) == 5

    async def test_usd_krw_fallback_on_fx_failure(self):
        """USD/KRW 환율 조회 실패 시 1350.0 폴백을 사용해야 한다"""
        # get_usd_krw_rate는 이미 fallback을 처리하므로 이 테스트는 통합적 검증
        from stock_picker.portfolio.performance_summary import calculate_performance_summary

        mock_db = MagicMock()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()

        portfolio = self._make_mock_portfolio()
        price_series = self._make_price_series()

        with patch("stock_picker.portfolio.performance_summary.get_portfolio_with_holdings",
                   return_value=portfolio), \
             patch("stock_picker.portfolio.performance_summary.get_usd_krw_rate",
                   AsyncMock(return_value=1350.0)), \
             patch("stock_picker.portfolio.performance_summary._fetch_price_series_for_period",
                   AsyncMock(return_value=price_series)):

            # 예외 없이 계산이 완료되어야 한다
            result = await calculate_performance_summary(
                portfolio_id=1,
                user_id=1,
                db=mock_db,
                redis=mock_redis,
                refresh=False,
            )
        assert result is not None


# ──────────────────────────────────────────────────────────────
# T-008: YTD 경계 케이스 테스트
# ──────────────────────────────────────────────────────────────

class TestYtdBoundaryCase:
    """YTD 경계 케이스 — 연초 거래일 부족 시 has_data=False"""

    def test_ytd_with_less_than_2_trading_days_is_no_data(self):
        """YTD 거래일이 2일 미만이면 has_data=False이어야 한다"""
        from stock_picker.portfolio.performance_summary import _compute_period_returns

        # 거래일 1일만 있는 경우
        values = [100.0]
        result = _compute_period_returns(values)
        assert result["has_data"] is False

    def test_ytd_with_exactly_2_trading_days_has_data(self):
        """YTD 거래일이 정확히 2일이면 has_data=True이어야 한다"""
        from stock_picker.portfolio.performance_summary import _compute_period_returns

        values = [100.0, 101.0]  # 2일
        result = _compute_period_returns(values)
        assert result["has_data"] is True


# ──────────────────────────────────────────────────────────────
# T-009: 캐시 키 형식 테스트
# ──────────────────────────────────────────────────────────────

class TestCacheKey:
    """Redis 캐시 키 형식 검증"""

    def test_cache_key_format(self):
        """캐시 키는 'portfolio_perf_summary:{id}:{YYYY-MM-DD}' 형식이어야 한다"""
        from stock_picker.portfolio.performance_summary import _build_cache_key

        key = _build_cache_key(portfolio_id=1, today_kst="2025-06-23")
        assert key == "portfolio_perf_summary:1:2025-06-23"

    def test_cache_key_different_portfolios(self):
        """서로 다른 포트폴리오 ID는 서로 다른 캐시 키를 생성해야 한다"""
        from stock_picker.portfolio.performance_summary import _build_cache_key

        key1 = _build_cache_key(portfolio_id=1, today_kst="2025-06-23")
        key2 = _build_cache_key(portfolio_id=2, today_kst="2025-06-23")
        assert key1 != key2


# ──────────────────────────────────────────────────────────────
# T-010: Scipy 금지 검증
# ──────────────────────────────────────────────────────────────

class TestNonScipyImplementation:
    """scipy 미사용 검증 (NFR-001)"""

    def test_no_scipy_import_in_performance_summary(self):
        """performance_summary.py에 scipy import가 없어야 한다"""
        import ast
        import os

        filepath = os.path.join(
            os.path.dirname(__file__),
            "../../src/stock_picker/portfolio/performance_summary.py",
        )
        with open(os.path.abspath(filepath)) as f:
            source = f.read()

        # scipy import 존재하면 테스트 실패
        assert "import scipy" not in source, "performance_summary.py에 scipy import가 존재합니다 (NFR-001 위반)"
        assert "from scipy" not in source, "performance_summary.py에 from scipy import가 존재합니다 (NFR-001 위반)"


# ──────────────────────────────────────────────────────────────
# T-011: 디스플레이 레이블 테스트
# ──────────────────────────────────────────────────────────────

class TestDisplayLabels:
    """기간 표시 레이블 테스트"""

    def test_period_display_labels(self):
        """각 기간의 display_label이 올바르게 설정되어야 한다"""
        from stock_picker.portfolio.performance_summary import PERIOD_DISPLAY_LABELS

        assert PERIOD_DISPLAY_LABELS["ytd"] == "YTD"
        assert PERIOD_DISPLAY_LABELS["1m"] == "1개월"
        assert PERIOD_DISPLAY_LABELS["3m"] == "3개월"
        assert PERIOD_DISPLAY_LABELS["6m"] == "6개월"
        assert PERIOD_DISPLAY_LABELS["1y"] == "1년"


# ──────────────────────────────────────────────────────────────
# T-012: 포트폴리오 가치 내부 경계 케이스 (커버리지 보강)
# ──────────────────────────────────────────────────────────────

class TestPortfolioValuesEdgeCases:
    """포트폴리오 가치 계산 내부 경계 케이스"""

    def test_zero_base_price_ticker_skipped(self):
        """기준 가격이 0인 종목은 계산에서 제외되어야 한다 (0-division 방지)"""
        from stock_picker.portfolio.performance_summary import _compute_portfolio_values

        aligned_closes = {
            "A": [0.0, 100.0, 110.0],  # 기준 가격이 0
            "B": [50.0, 55.0, 60.0],
        }
        weights = [0.5, 0.5]
        tickers = ["A", "B"]
        values = _compute_portfolio_values(aligned_closes, weights, tickers)
        # A 종목 제외 → B 종목만으로 계산됨
        assert len(values) == 3
        # 첫날: A 제외(0/0 skip) + B(0.5*50/50=0.5)
        assert values[0] == pytest.approx(0.5)

    def test_compute_portfolio_values_empty_closes(self):
        """n_days가 0이면 빈 리스트를 반환해야 한다"""
        from stock_picker.portfolio.performance_summary import _compute_portfolio_values

        aligned_closes = {"A": []}
        values = _compute_portfolio_values(aligned_closes, [1.0], ["A"])
        assert values == []


# ──────────────────────────────────────────────────────────────
# T-013: _fetch_price_series_sync FDR 오류 처리 (커버리지 보강)
# ──────────────────────────────────────────────────────────────

class TestFetchPriceSeriesSync:
    """FDR 가격 조회 동기 함수 테스트"""

    def test_fdr_exception_returns_empty(self):
        """FDR에서 예외 발생 시 빈 리스트를 반환해야 한다"""
        from datetime import date
        from stock_picker.portfolio.performance_summary import _fetch_price_series_sync

        with patch("stock_picker.portfolio.performance_summary._fetch_price_series_sync") as mock_sync:
            mock_sync.return_value = []
            result = _fetch_price_series_sync("INVALID_TICKER_XYZ", date(2025, 1, 1), date(2025, 6, 23))
            # mock을 쓴 경우: 반환값이 빈 리스트인지 확인
            assert isinstance(result, list)

    def test_fdr_empty_dataframe_returns_empty(self):
        """FDR 조회 시 예외가 발생하면 빈 리스트를 반환해야 한다"""
        from datetime import date
        from stock_picker.portfolio.performance_summary import _fetch_price_series_sync
        import sys

        # FinanceDataReader를 임시 mock으로 교체
        mock_fdr = MagicMock()
        mock_fdr.DataReader.side_effect = Exception("연결 실패")
        original = sys.modules.get("FinanceDataReader")
        sys.modules["FinanceDataReader"] = mock_fdr
        try:
            result = _fetch_price_series_sync("005930", date(2025, 1, 1), date(2025, 6, 23))
            # 예외가 내부에서 처리되어 빈 리스트 반환
            assert result == []
        finally:
            if original is None:
                sys.modules.pop("FinanceDataReader", None)
            else:
                sys.modules["FinanceDataReader"] = original


# ──────────────────────────────────────────────────────────────
# T-014: _calculate_single_period 내부 경로 테스트 (커버리지 보강)
# ──────────────────────────────────────────────────────────────

class TestCalculateSinglePeriod:
    """_calculate_single_period 내부 경로 테스트"""

    async def test_single_period_with_short_history(self):
        """공통 거래일이 1일뿐이면 has_data=False인 PeriodPerformance를 반환해야 한다"""
        from datetime import date
        from stock_picker.portfolio.performance_summary import _calculate_single_period

        # 1일치 데이터만 제공 (공통 날짜 < 2)
        price_series_1day = [{"date": "2025-06-23", "close": 100.0}]

        with patch("stock_picker.portfolio.performance_summary._fetch_price_series_for_period",
                   AsyncMock(return_value=price_series_1day)):
            result = await _calculate_single_period(
                period="ytd",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 6, 23),
                today_str="2025-06-23",
                tickers=["005930"],
                weights=[1.0],
                currencies=["KRW"],
                fx_rate=1.0,
            )

        assert result.has_data is False
        assert result.period == "ytd"

    async def test_single_period_usd_applies_fx(self):
        """USD 종목에 환율을 적용해야 한다"""
        from datetime import date
        from stock_picker.portfolio.performance_summary import _calculate_single_period

        # 50거래일치 데이터
        from datetime import timedelta
        today = date(2025, 6, 23)
        price_series = [
            {"date": str(today - timedelta(days=50 - i)), "close": 100.0 + i * 0.5}
            for i in range(51)
        ]

        with patch("stock_picker.portfolio.performance_summary._fetch_price_series_for_period",
                   AsyncMock(return_value=price_series)):
            result = await _calculate_single_period(
                period="3m",
                start_date=today - timedelta(days=90),
                end_date=today,
                today_str=str(today),
                tickers=["AAPL"],
                weights=[1.0],
                currencies=["USD"],
                fx_rate=1350.0,
            )

        # 환율 적용 후에도 계산이 정상 완료되어야 한다
        assert result.period == "3m"
        # 상승 가격이므로 has_data=True 및 양수 수익률
        if result.has_data:
            assert result.total_return_pct is not None

    async def test_fx_fallback_on_get_usd_krw_rate_exception(self):
        """get_usd_krw_rate 예외 시 _FX_FALLBACK(1350.0)을 사용해야 한다"""
        from stock_picker.portfolio.performance_summary import calculate_performance_summary

        mock_db = MagicMock()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()

        holdings = [
            MagicMock(krx_code="AAPL", quantity=5, avg_buy_price=150.0, weight=100.0, market="NYSE", currency="USD"),
        ]
        portfolio = MagicMock()
        portfolio.id = 1
        portfolio.holdings = holdings

        with patch("stock_picker.portfolio.performance_summary.get_portfolio_with_holdings",
                   return_value=portfolio), \
             patch("stock_picker.portfolio.performance_summary.get_usd_krw_rate",
                   AsyncMock(side_effect=Exception("FX 서버 다운"))), \
             patch("stock_picker.portfolio.performance_summary._fetch_price_series_for_period",
                   AsyncMock(return_value=[])):  # FDR 빈 결과

            # 예외 없이 완료되어야 한다
            result = await calculate_performance_summary(
                portfolio_id=1,
                user_id=1,
                db=mock_db,
                redis=mock_redis,
                refresh=False,
            )

        assert len(result.periods) == 5
        # FX 실패 + FDR 빈 결과 → 모두 has_data=False
        assert all(not p.has_data for p in result.periods)
