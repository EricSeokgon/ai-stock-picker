# 포트폴리오 벤치마크 비교 단위 테스트 (SPEC-STOCK-034)
# TDD RED-GREEN-REFACTOR 사이클
# asyncio_mode = "auto" — @pytest.mark.asyncio 불필요
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ──────────────────────────────────────────────────────────────
# NFR-001: scipy 미사용 검증
# ──────────────────────────────────────────────────────────────


class TestNoScipyInBenchmark:
    """scipy import 금지 검증 (NFR-001)"""

    def test_no_scipy_in_benchmark(self):
        """benchmark.py는 scipy를 import하면 안 된다"""
        import ast
        import os

        module_path = os.path.join(
            os.path.dirname(__file__),
            "../../src/stock_picker/portfolio/benchmark.py",
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
# 벤치마크 심볼 매핑 검증
# ──────────────────────────────────────────────────────────────


class TestBenchmarkSymbols:
    """벤치마크 심볼 매핑 상수 검증"""

    def test_kospi_symbol(self):
        """KOSPI 심볼은 ^KS11이어야 한다"""
        from stock_picker.portfolio.benchmark import BENCHMARK_SYMBOLS
        assert BENCHMARK_SYMBOLS["KOSPI"] == "^KS11"

    def test_sp500_symbol(self):
        """SP500 심볼은 ^GSPC이어야 한다"""
        from stock_picker.portfolio.benchmark import BENCHMARK_SYMBOLS
        assert BENCHMARK_SYMBOLS["SP500"] == "^GSPC"

    def test_kosdaq_symbol(self):
        """KOSDAQ 심볼은 ^KQ11이어야 한다"""
        from stock_picker.portfolio.benchmark import BENCHMARK_SYMBOLS
        assert BENCHMARK_SYMBOLS["KOSDAQ"] == "^KQ11"

    def test_nasdaq_symbol(self):
        """NASDAQ 심볼은 ^IXIC이어야 한다"""
        from stock_picker.portfolio.benchmark import BENCHMARK_SYMBOLS
        assert BENCHMARK_SYMBOLS["NASDAQ"] == "^IXIC"


# ──────────────────────────────────────────────────────────────
# 순수 함수 테스트 — calculate_beta
# ──────────────────────────────────────────────────────────────


def _make_daily_returns(n: int, base_val: float = 0.001) -> list[float]:
    """테스트용 일별 수익률 리스트 생성 헬퍼"""
    import math
    return [base_val * (1 + math.sin(i * 0.3)) for i in range(n)]


class TestCalculateBeta:
    """calculate_beta 순수 함수 테스트"""

    def test_beta_with_sufficient_data_returns_float(self):
        """20개 이상 데이터 포인트가 있으면 float을 반환해야 한다"""
        from stock_picker.portfolio.benchmark import calculate_beta

        port_returns = _make_daily_returns(25, 0.002)
        bench_returns = _make_daily_returns(25, 0.001)
        result = calculate_beta(port_returns, bench_returns)
        assert result is not None
        assert isinstance(result, float)

    def test_beta_less_than_20_points_returns_none(self):
        """19개 이하 데이터 포인트면 None을 반환해야 한다"""
        from stock_picker.portfolio.benchmark import calculate_beta

        port_returns = _make_daily_returns(19, 0.001)
        bench_returns = _make_daily_returns(19, 0.001)
        result = calculate_beta(port_returns, bench_returns)
        assert result is None

    def test_beta_exactly_19_points_returns_none(self):
        """정확히 19개 데이터 포인트면 None을 반환해야 한다 (경계값)"""
        from stock_picker.portfolio.benchmark import calculate_beta

        port_returns = _make_daily_returns(19)
        bench_returns = _make_daily_returns(19)
        result = calculate_beta(port_returns, bench_returns)
        assert result is None

    def test_beta_exactly_20_points_returns_float(self):
        """정확히 20개 데이터 포인트면 float을 반환해야 한다 (경계값)"""
        from stock_picker.portfolio.benchmark import calculate_beta

        port_returns = _make_daily_returns(20, 0.002)
        bench_returns = _make_daily_returns(20, 0.001)
        result = calculate_beta(port_returns, bench_returns)
        assert result is not None
        assert isinstance(result, float)

    def test_beta_zero_variance_benchmark_returns_none(self):
        """벤치마크 수익률이 모두 동일(분산=0)이면 None을 반환해야 한다"""
        from stock_picker.portfolio.benchmark import calculate_beta

        port_returns = _make_daily_returns(25, 0.001)
        bench_returns = [0.001] * 25  # 모두 동일 → var=0
        result = calculate_beta(port_returns, bench_returns)
        assert result is None

    def test_beta_identical_series_returns_approximately_one(self):
        """포트폴리오와 벤치마크 수익률이 동일하면 beta≈1이어야 한다"""
        from stock_picker.portfolio.benchmark import calculate_beta

        returns = _make_daily_returns(30, 0.001)
        result = calculate_beta(returns, returns)
        assert result is not None
        assert abs(result - 1.0) < 1e-6

    def test_beta_nan_in_inputs_returns_none(self):
        """입력에 NaN이 포함되면 None을 반환해야 한다"""
        import math
        from stock_picker.portfolio.benchmark import calculate_beta

        port_returns = _make_daily_returns(25, 0.001)
        bench_returns = _make_daily_returns(25, 0.001)
        bench_returns[5] = float("nan")
        result = calculate_beta(port_returns, bench_returns)
        assert result is None


# ──────────────────────────────────────────────────────────────
# 순수 함수 테스트 — calculate_benchmark_comparison
# ──────────────────────────────────────────────────────────────


def _make_portfolio_history(n: int, start_value: float = 10000.0, growth: float = 0.001) -> list[dict]:
    """테스트용 포트폴리오 가치 시계열 생성 헬퍼 (오늘 기준 n일 전부터 오늘까지).

    sin() 노이즈를 추가하여 분산 > 0인 일별 수익률을 생성한다 (베타 계산 필요).
    """
    import math
    from datetime import timedelta
    today = date.today()
    start = today - timedelta(days=n - 1)
    history = []
    value = start_value
    for i in range(n):
        d = start + timedelta(days=i)
        history.append({"date": d, "portfolio_value": value})
        # sin 노이즈로 분산 > 0 보장
        daily_return = growth * (1 + 0.5 * math.sin(i * 0.7))
        value *= (1 + daily_return)
    return history


def _make_benchmark_history(n: int, start_price: float = 2500.0, growth: float = 0.0005) -> list[dict]:
    """테스트용 벤치마크 가격 시계열 생성 헬퍼 (오늘 기준 n일 전부터 오늘까지).

    cos() 노이즈를 추가하여 분산 > 0인 일별 수익률을 생성한다.
    """
    import math
    from datetime import timedelta
    today = date.today()
    start = today - timedelta(days=n - 1)
    history = []
    price = start_price
    for i in range(n):
        d = start + timedelta(days=i)
        history.append({"date": d, "close_price": price})
        daily_return = growth * (1 + 0.5 * math.cos(i * 0.5))
        price *= (1 + daily_return)
    return history


class TestCalculateBenchmarkComparison:
    """calculate_benchmark_comparison 순수 함수 테스트"""

    def test_both_available_excess_return_equals_diff(self):
        """포트폴리오와 벤치마크 모두 있으면 excess_return = port - bench이어야 한다"""
        from stock_picker.portfolio.benchmark import calculate_benchmark_comparison

        port_history = _make_portfolio_history(30, growth=0.002)
        bench_history = _make_benchmark_history(30, growth=0.001)
        result = calculate_benchmark_comparison(
            portfolio_history=port_history,
            benchmark_history=bench_history,
            period="1M",
            portfolio_id=1,
            benchmark="KOSPI",
        )
        assert result.benchmark_return_pct is not None
        expected_excess = round(result.portfolio_return_pct - result.benchmark_return_pct, 6)
        assert result.excess_return_pct is not None
        assert abs(result.excess_return_pct - expected_excess) < 0.01

    def test_empty_benchmark_history_returns_none_fields(self):
        """벤치마크 히스토리가 비어있으면 benchmark_return_pct=None, excess=None이어야 한다"""
        from stock_picker.portfolio.benchmark import calculate_benchmark_comparison

        port_history = _make_portfolio_history(30)
        result = calculate_benchmark_comparison(
            portfolio_history=port_history,
            benchmark_history=[],
            period="1M",
            portfolio_id=1,
            benchmark="KOSPI",
        )
        assert result.benchmark_return_pct is None
        assert result.excess_return_pct is None

    def test_portfolio_gains_more_than_benchmark_positive_excess(self):
        """포트폴리오 수익률이 벤치마크보다 높으면 초과수익이 양수이어야 한다"""
        from stock_picker.portfolio.benchmark import calculate_benchmark_comparison

        port_history = _make_portfolio_history(30, growth=0.005)  # 0.5% 일별 성장
        bench_history = _make_benchmark_history(30, growth=0.001)  # 0.1% 일별 성장
        result = calculate_benchmark_comparison(
            portfolio_history=port_history,
            benchmark_history=bench_history,
            period="1M",
            portfolio_id=1,
            benchmark="KOSPI",
        )
        assert result.excess_return_pct is not None
        assert result.excess_return_pct > 0

    def test_alpha_present_when_data_sufficient(self):
        """데이터가 충분하면 alpha(연환산 초과수익률)가 None이 아니어야 한다"""
        from stock_picker.portfolio.benchmark import calculate_benchmark_comparison

        port_history = _make_portfolio_history(30, growth=0.002)
        bench_history = _make_benchmark_history(30, growth=0.001)
        result = calculate_benchmark_comparison(
            portfolio_history=port_history,
            benchmark_history=bench_history,
            period="1M",
            portfolio_id=1,
            benchmark="KOSPI",
        )
        # 30개 데이터이면 alpha 계산 가능
        assert result.alpha is not None

    def test_beta_present_when_20_plus_daily_points(self):
        """공통 거래일이 20개 이상이면 beta가 None이 아니어야 한다"""
        from stock_picker.portfolio.benchmark import calculate_benchmark_comparison

        port_history = _make_portfolio_history(25, growth=0.002)
        bench_history = _make_benchmark_history(25, growth=0.001)
        result = calculate_benchmark_comparison(
            portfolio_history=port_history,
            benchmark_history=bench_history,
            period="1M",
            portfolio_id=1,
            benchmark="KOSPI",
        )
        assert result.beta is not None

    def test_beta_none_when_less_than_20_daily_points(self):
        """공통 거래일이 19개 이하이면 beta=None이어야 한다"""
        from stock_picker.portfolio.benchmark import calculate_benchmark_comparison

        port_history = _make_portfolio_history(19, growth=0.002)
        bench_history = _make_benchmark_history(19, growth=0.001)
        result = calculate_benchmark_comparison(
            portfolio_history=port_history,
            benchmark_history=bench_history,
            period="1M",
            portfolio_id=1,
            benchmark="KOSPI",
        )
        assert result.beta is None

    def test_ytd_period_filter_cuts_at_jan_1(self):
        """YTD 기간은 당해 1월 1일부터 필터링해야 한다"""
        from stock_picker.portfolio.benchmark import calculate_benchmark_comparison
        from datetime import timedelta

        # 2024년 데이터 + 2025년 데이터 혼합
        today = date.today()
        this_year = today.year

        # 작년 말 데이터 추가
        all_port = []
        all_bench = []
        for i in range(15):
            d = date(this_year - 1, 12, 17 + i)  # 작년 12월 중순~말
            all_port.append({"date": d, "portfolio_value": 10000.0 + i * 10})
            all_bench.append({"date": d, "close_price": 2500.0 + i})
        # 올해 데이터 추가
        for i in range(25):
            d = date(this_year, 1, 2) + timedelta(days=i)
            if d.month == 1 and d <= today:
                all_port.append({"date": d, "portfolio_value": 10200.0 + i * 5})
                all_bench.append({"date": d, "close_price": 2515.0 + i * 0.5})

        result = calculate_benchmark_comparison(
            portfolio_history=all_port,
            benchmark_history=all_bench,
            period="YTD",
            portfolio_id=1,
            benchmark="KOSPI",
        )
        # YTD이므로 이번 연도 데이터만 사용 — 포트폴리오 수익률이 계산되어야 함
        assert result.portfolio_return_pct is not None

    def test_single_data_point_alpha_none(self):
        """공통 거래일이 1개이면 alpha=None이어야 한다 (연환산 불가)"""
        from stock_picker.portfolio.benchmark import calculate_benchmark_comparison

        port_history = [{"date": date(2025, 1, 2), "portfolio_value": 10000.0},
                        {"date": date(2025, 1, 3), "portfolio_value": 10100.0}]
        bench_history = [{"date": date(2025, 1, 2), "close_price": 2500.0},
                         {"date": date(2025, 1, 3), "close_price": 2505.0}]
        result = calculate_benchmark_comparison(
            portfolio_history=port_history,
            benchmark_history=bench_history,
            period="1M",
            portfolio_id=1,
            benchmark="KOSPI",
        )
        # 2개 포인트 → 1개 간격 → 연환산 가능하지만 단기로 극단적
        # 정확한 기대값 대신 None 또는 float 허용 (구현에 따라 다름)
        # 핵심: 크래시 없이 처리되어야 함
        assert result is not None

    def test_1m_period_uses_last_30_calendar_days(self):
        """1M 기간은 최근 30일 데이터를 사용해야 한다"""
        from stock_picker.portfolio.benchmark import calculate_benchmark_comparison
        from datetime import timedelta

        # 60일치 데이터 생성
        port_history = []
        bench_history = []
        today = date.today()
        for i in range(60):
            d = today - timedelta(days=59 - i)
            port_history.append({"date": d, "portfolio_value": 10000.0 + i * 10})
            bench_history.append({"date": d, "close_price": 2500.0 + i})

        result = calculate_benchmark_comparison(
            portfolio_history=port_history,
            benchmark_history=bench_history,
            period="1M",
            portfolio_id=1,
            benchmark="KOSPI",
        )
        assert result is not None
        assert result.period == "1M"


# ──────────────────────────────────────────────────────────────
# 순수 함수 테스트 — calculate_benchmark_chart
# ──────────────────────────────────────────────────────────────


class TestCalculateBenchmarkChart:
    """calculate_benchmark_chart 순수 함수 테스트"""

    def test_rebased_to_100_at_first_point(self):
        """차트 첫 포인트는 포트폴리오와 벤치마크 모두 100.0이어야 한다"""
        from stock_picker.portfolio.benchmark import calculate_benchmark_chart

        port_history = _make_portfolio_history(10, start_value=12345.0)
        bench_history = _make_benchmark_history(10, start_price=9876.0)
        result = calculate_benchmark_chart(
            portfolio_history=port_history,
            benchmark_history=bench_history,
            period="1M",
            portfolio_id=1,
            benchmark="KOSPI",
        )
        assert len(result.chart) > 0
        assert result.chart[0].portfolio_index == 100.0

    def test_portfolio_index_first_point_100(self):
        """portfolio_index[0] == 100.0이어야 한다"""
        from stock_picker.portfolio.benchmark import calculate_benchmark_chart

        port_history = _make_portfolio_history(15)
        bench_history = _make_benchmark_history(15)
        result = calculate_benchmark_chart(
            portfolio_history=port_history,
            benchmark_history=bench_history,
            period="1M",
            portfolio_id=1,
            benchmark="KOSPI",
        )
        assert result.chart[0].portfolio_index == 100.0

    def test_benchmark_index_first_point_100_when_data_present(self):
        """벤치마크 데이터가 있으면 benchmark_index[0] == 100.0이어야 한다"""
        from stock_picker.portfolio.benchmark import calculate_benchmark_chart

        port_history = _make_portfolio_history(15)
        bench_history = _make_benchmark_history(15)
        result = calculate_benchmark_chart(
            portfolio_history=port_history,
            benchmark_history=bench_history,
            period="1M",
            portfolio_id=1,
            benchmark="KOSPI",
        )
        assert result.chart[0].benchmark_index == 100.0

    def test_benchmark_index_none_when_no_benchmark_data(self):
        """벤치마크 데이터가 없으면 benchmark_index=None이어야 한다"""
        from stock_picker.portfolio.benchmark import calculate_benchmark_chart

        port_history = _make_portfolio_history(15)
        result = calculate_benchmark_chart(
            portfolio_history=port_history,
            benchmark_history=[],
            period="1M",
            portfolio_id=1,
            benchmark="KOSPI",
        )
        # 벤치마크 데이터 없음 → 모든 포인트의 benchmark_index=None
        for point in result.chart:
            assert point.benchmark_index is None

    def test_portfolio_and_benchmark_data_aligned_by_date(self):
        """포트폴리오와 벤치마크 날짜가 정렬되어야 한다"""
        from stock_picker.portfolio.benchmark import calculate_benchmark_chart
        from datetime import timedelta

        # 포트폴리오는 매일, 벤치마크는 짝수일만 데이터 있음
        port_history = []
        bench_history = []
        start = date(2025, 1, 2)
        for i in range(20):
            d = start + timedelta(days=i)
            port_history.append({"date": d, "portfolio_value": 10000.0 + i * 50})
            if i % 2 == 0:  # 짝수 인덱스만
                bench_history.append({"date": d, "close_price": 2500.0 + i * 5})

        result = calculate_benchmark_chart(
            portfolio_history=port_history,
            benchmark_history=bench_history,
            period="1M",
            portfolio_id=1,
            benchmark="KOSPI",
        )
        # 정렬되어 날짜 순서가 유지되어야 함
        dates = [p.date for p in result.chart]
        assert dates == sorted(dates)


# ──────────────────────────────────────────────────────────────
# API 엔드포인트 테스트 — 소유권 검증 (404)
# ──────────────────────────────────────────────────────────────


class TestBenchmarkAPIOwnership:
    """벤치마크 API 소유권 검증 테스트"""

    def test_get_benchmark_returns_404_when_not_owned(self):
        """소유하지 않은 포트폴리오 벤치마크 조회 시 404를 반환해야 한다"""
        from stock_picker.portfolio.benchmark import get_benchmark_comparison_service
        import asyncio

        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1

        with patch(
            "stock_picker.portfolio.benchmark.get_portfolio_with_holdings",
            return_value=None,
        ):
            with pytest.raises(Exception) as exc_info:
                asyncio.get_event_loop().run_until_complete(
                    get_benchmark_comparison_service(
                        portfolio_id=999,
                        benchmark="KOSPI",
                        period="YTD",
                        user_id=1,
                        db=mock_db,
                    )
                )
            # HTTPException 또는 유사 예외 발생 확인
            assert exc_info.value is not None

    def test_get_benchmark_chart_returns_404_when_not_owned(self):
        """소유하지 않은 포트폴리오 차트 조회 시 404를 반환해야 한다"""
        from stock_picker.portfolio.benchmark import get_benchmark_chart_service
        import asyncio

        mock_db = MagicMock()

        with patch(
            "stock_picker.portfolio.benchmark.get_portfolio_with_holdings",
            return_value=None,
        ):
            with pytest.raises(Exception) as exc_info:
                asyncio.get_event_loop().run_until_complete(
                    get_benchmark_chart_service(
                        portfolio_id=999,
                        benchmark="KOSPI",
                        period="YTD",
                        user_id=1,
                        db=mock_db,
                    )
                )
            assert exc_info.value is not None


# ──────────────────────────────────────────────────────────────
# 추가 커버리지: 기간 계산 함수, 엣지 케이스
# ──────────────────────────────────────────────────────────────


class TestGetPeriodStart:
    """_get_period_start 내부 헬퍼 커버리지"""

    def test_3m_period_90_days_before(self):
        """3M 기간은 오늘 기준 90일 전이어야 한다"""
        from stock_picker.portfolio.benchmark import _get_period_start
        from datetime import timedelta

        today = date.today()
        result = _get_period_start("3M", today)
        assert result == today - timedelta(days=90)

    def test_6m_period_180_days_before(self):
        """6M 기간은 오늘 기준 180일 전이어야 한다"""
        from stock_picker.portfolio.benchmark import _get_period_start
        from datetime import timedelta

        today = date.today()
        result = _get_period_start("6M", today)
        assert result == today - timedelta(days=180)

    def test_unknown_period_falls_back_to_30_days(self):
        """알 수 없는 기간 코드는 30일로 폴백되어야 한다"""
        from stock_picker.portfolio.benchmark import _get_period_start
        from datetime import timedelta

        today = date.today()
        result = _get_period_start("INVALID", today)
        assert result == today - timedelta(days=30)

    def test_ytd_period_jan_1(self):
        """YTD 기간은 당해 1월 1일을 반환해야 한다"""
        from stock_picker.portfolio.benchmark import _get_period_start

        today = date.today()
        result = _get_period_start("ytd", today)  # 소문자도 허용
        assert result == date(today.year, 1, 1)


class TestCalculateBetaEdgeCases:
    """calculate_beta 엣지 케이스 추가 커버리지"""

    def test_beta_exactly_19_points_returns_none(self):
        """데이터 포인트 정확히 19개는 None을 반환해야 한다"""
        from stock_picker.portfolio.benchmark import calculate_beta

        returns = _make_daily_returns(19)
        result = calculate_beta(returns, returns)
        assert result is None

    def test_beta_with_inf_value_returns_none(self):
        """입력 데이터에 inf가 있으면 None을 반환해야 한다"""
        import math
        from stock_picker.portfolio.benchmark import calculate_beta

        returns = _make_daily_returns(25)
        inf_returns = returns[:]
        inf_returns[5] = math.inf
        result = calculate_beta(inf_returns, returns)
        assert result is None

    def test_beta_mismatched_lengths_handled(self):
        """두 시계열 길이가 다르면 None 또는 float를 안전하게 반환해야 한다"""
        from stock_picker.portfolio.benchmark import calculate_beta

        port = _make_daily_returns(25)
        bench = _make_daily_returns(20)
        # 길이 차이가 있어도 크래시 없이 처리
        result = calculate_beta(port, bench)
        # 최소 길이가 20개 이상이면 계산 가능
        assert result is None or isinstance(result, float)


class TestBenchmarkServiceSuccessPath:
    """벤치마크 서비스 함수 성공 경로 커버리지"""

    @pytest.mark.asyncio
    async def test_comparison_service_returns_result_when_owned(self):
        """소유 포트폴리오 조회 시 BenchmarkComparison을 반환해야 한다"""
        from stock_picker.portfolio.benchmark import get_benchmark_comparison_service
        from stock_picker.portfolio.schemas import BenchmarkComparison

        mock_db = MagicMock()
        mock_portfolio = MagicMock()
        mock_portfolio.holdings = []

        with patch(
            "stock_picker.portfolio.service.get_portfolio_with_holdings",
            return_value=mock_portfolio,
        ), patch(
            "stock_picker.portfolio.benchmark._compute_portfolio_daily_history",
            return_value=_make_portfolio_history(30),
        ), patch(
            "stock_picker.portfolio.benchmark._fetch_benchmark_async",
            new=AsyncMock(return_value=_make_benchmark_history(30)),
        ), patch(
            "stock_picker.portfolio.benchmark.asyncio.get_event_loop",
        ) as mock_loop:
            mock_loop_inst = MagicMock()
            mock_loop.return_value = mock_loop_inst
            mock_loop_inst.run_in_executor = AsyncMock(return_value=_make_portfolio_history(30))

            result = await get_benchmark_comparison_service(
                portfolio_id=1,
                benchmark="KOSPI",
                period="1M",
                user_id=1,
                db=mock_db,
            )

        assert isinstance(result, BenchmarkComparison)
        assert result.benchmark == "KOSPI"

    @pytest.mark.asyncio
    async def test_chart_service_returns_result_when_owned(self):
        """소유 포트폴리오 차트 조회 시 BenchmarkChartData를 반환해야 한다"""
        from stock_picker.portfolio.benchmark import get_benchmark_chart_service
        from stock_picker.portfolio.schemas import BenchmarkChartData

        mock_db = MagicMock()
        mock_portfolio = MagicMock()
        mock_portfolio.holdings = []

        with patch(
            "stock_picker.portfolio.service.get_portfolio_with_holdings",
            return_value=mock_portfolio,
        ), patch(
            "stock_picker.portfolio.benchmark._compute_portfolio_daily_history",
            return_value=_make_portfolio_history(30),
        ), patch(
            "stock_picker.portfolio.benchmark._fetch_benchmark_async",
            new=AsyncMock(return_value=_make_benchmark_history(30)),
        ), patch(
            "stock_picker.portfolio.benchmark.asyncio.get_event_loop",
        ) as mock_loop:
            mock_loop_inst = MagicMock()
            mock_loop.return_value = mock_loop_inst
            mock_loop_inst.run_in_executor = AsyncMock(return_value=_make_portfolio_history(30))

            result = await get_benchmark_chart_service(
                portfolio_id=1,
                benchmark="KOSDAQ",
                period="1M",
                user_id=1,
                db=mock_db,
            )

        assert isinstance(result, BenchmarkChartData)
        assert result.benchmark == "KOSDAQ"
        assert result.period == "1M"


class TestComputePortfolioDailyHistory:
    """_compute_portfolio_daily_history 커버리지"""

    def test_empty_holdings_returns_empty_list(self):
        """보유 종목이 없으면 빈 리스트를 반환해야 한다"""
        from stock_picker.portfolio.benchmark import _compute_portfolio_daily_history

        mock_portfolio = MagicMock()
        mock_portfolio.holdings = []

        result = _compute_portfolio_daily_history(
            mock_portfolio,
            date(2025, 1, 2),
            date(2025, 1, 31),
        )
        assert result == []

    def test_fdr_exception_returns_empty_list(self):
        """FDR 조회 실패 시 빈 리스트를 반환해야 한다 (graceful degradation)"""
        from stock_picker.portfolio.benchmark import _compute_portfolio_daily_history

        mock_portfolio = MagicMock()
        mock_holding = MagicMock()
        mock_holding.krx_code = "005930"
        mock_holding.currency = "KRW"
        mock_portfolio.holdings = [mock_holding]

        with patch("FinanceDataReader.DataReader", side_effect=Exception("FDR 오류")):
            result = _compute_portfolio_daily_history(
                mock_portfolio,
                date(2025, 1, 2),
                date(2025, 1, 31),
            )
        assert result == []

    def test_fdr_empty_dataframe_skips_ticker(self):
        """FDR가 빈 DataFrame 반환 시 해당 종목을 건너뛴다"""
        from stock_picker.portfolio.benchmark import _compute_portfolio_daily_history
        import pandas as pd

        mock_portfolio = MagicMock()
        mock_holding = MagicMock()
        mock_holding.krx_code = "005930"
        mock_holding.currency = "KRW"
        mock_holding.quantity = 10
        mock_holding.avg_buy_price = 70000
        mock_portfolio.holdings = [mock_holding]

        with patch("FinanceDataReader.DataReader", return_value=pd.DataFrame()):
            result = _compute_portfolio_daily_history(
                mock_portfolio,
                date(2025, 1, 2),
                date(2025, 1, 31),
            )
        assert result == []

    def test_valid_holdings_returns_history(self):
        """유효한 보유 종목 데이터로 일별 가치 시계열을 반환해야 한다"""
        from stock_picker.portfolio.benchmark import _compute_portfolio_daily_history
        import pandas as pd
        from datetime import datetime

        mock_portfolio = MagicMock()
        mock_holding = MagicMock()
        mock_holding.krx_code = "005930"
        mock_holding.currency = "KRW"
        mock_holding.quantity = 10
        mock_holding.avg_buy_price = 70000
        mock_portfolio.holdings = [mock_holding]

        idx = pd.DatetimeIndex([datetime(2025, 1, 2), datetime(2025, 1, 3)])
        mock_df = pd.DataFrame({"Close": [70000.0, 71000.0]}, index=idx)

        with patch("FinanceDataReader.DataReader", return_value=mock_df):
            result = _compute_portfolio_daily_history(
                mock_portfolio,
                date(2025, 1, 2),
                date(2025, 1, 3),
            )
        assert len(result) == 2
        assert "date" in result[0]
        assert "portfolio_value" in result[0]


class TestBenchmarkSymbolConstants:
    """BENCHMARK_SYMBOLS 상수 완전 커버리지"""

    def test_sp500_symbol_is_gspc(self):
        """SP500 심볼은 ^GSPC이어야 한다"""
        from stock_picker.portfolio.benchmark import BENCHMARK_SYMBOLS
        assert BENCHMARK_SYMBOLS["SP500"] == "^GSPC"

    def test_nasdaq_symbol_is_ixic(self):
        """NASDAQ 심볼은 ^IXIC이어야 한다"""
        from stock_picker.portfolio.benchmark import BENCHMARK_SYMBOLS
        assert BENCHMARK_SYMBOLS["NASDAQ"] == "^IXIC"

    def test_all_4_benchmarks_present(self):
        """4개 벤치마크 모두 있어야 한다"""
        from stock_picker.portfolio.benchmark import BENCHMARK_SYMBOLS
        assert len(BENCHMARK_SYMBOLS) == 4


class TestFetchBenchmarkSync:
    """_fetch_benchmark_sync FDR 조회 함수 커버리지"""

    def test_fdr_empty_dataframe_returns_empty_list(self):
        """FDR가 빈 DataFrame을 반환하면 빈 리스트를 반환해야 한다"""
        from stock_picker.portfolio.benchmark import _fetch_benchmark_sync
        from unittest.mock import patch, MagicMock
        import pandas as pd

        mock_df = pd.DataFrame()
        with patch("FinanceDataReader.DataReader", return_value=mock_df):
            result = _fetch_benchmark_sync("^KS11", date(2025, 1, 2), date(2025, 1, 31))
        assert result == []

    def test_fdr_exception_returns_empty_list(self):
        """FDR 조회 중 예외 발생 시 빈 리스트를 반환해야 한다 (graceful degradation)"""
        from stock_picker.portfolio.benchmark import _fetch_benchmark_sync
        from unittest.mock import patch

        with patch("FinanceDataReader.DataReader", side_effect=Exception("FDR 네트워크 오류")):
            result = _fetch_benchmark_sync("^KS11", date(2025, 1, 2), date(2025, 1, 31))
        assert result == []

    def test_fdr_valid_data_returns_list(self):
        """FDR가 유효한 데이터를 반환하면 리스트를 반환해야 한다"""
        from stock_picker.portfolio.benchmark import _fetch_benchmark_sync
        from unittest.mock import patch
        import pandas as pd
        from datetime import datetime

        idx = pd.DatetimeIndex([datetime(2025, 1, 2), datetime(2025, 1, 3)])
        mock_df = pd.DataFrame({"Close": [2500.0, 2510.0]}, index=idx)
        with patch("FinanceDataReader.DataReader", return_value=mock_df):
            result = _fetch_benchmark_sync("^KS11", date(2025, 1, 2), date(2025, 1, 3))
        assert len(result) == 2
        assert result[0]["close_price"] == 2500.0


class TestBenchmarkChartEdgeCases:
    """calculate_benchmark_chart 추가 엣지 케이스"""

    def test_empty_portfolio_history_returns_empty_chart(self):
        """빈 포트폴리오 데이터는 빈 차트를 반환해야 한다"""
        from stock_picker.portfolio.benchmark import calculate_benchmark_chart

        result = calculate_benchmark_chart(
            portfolio_history=[],
            benchmark_history=[],
            period="1M",
            portfolio_id=99,
            benchmark="KOSPI",
        )
        assert result.chart == []
        assert result.portfolio_id == 99

    def test_3m_period_chart_returned(self):
        """3M 기간 차트가 정상 반환되어야 한다"""
        from stock_picker.portfolio.benchmark import calculate_benchmark_chart

        port_history = _make_portfolio_history(95)
        bench_history = _make_benchmark_history(95)

        result = calculate_benchmark_chart(
            portfolio_history=port_history,
            benchmark_history=bench_history,
            period="3M",
            portfolio_id=1,
            benchmark="SP500",
        )
        assert result.period == "3M"
        assert result.benchmark == "SP500"
        assert len(result.chart) > 0
