# 포트폴리오 백테스팅 단위 테스트 (SPEC-STOCK-029)
# TDD RED-GREEN-REFACTOR 사이클
# asyncio_mode = "auto" — @pytest.mark.asyncio 불필요
from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


# ──────────────────────────────────────────────────────────────
# T-001: Pydantic 스키마 테스트
# ──────────────────────────────────────────────────────────────


class TestBacktestRequest:
    """BacktestRequest 스키마 검증 테스트"""

    def test_valid_dates_pass(self):
        """유효한 날짜 범위(시작 < 종료)는 ValidationError 없이 생성된다"""

        from stock_picker.portfolio.schemas import BacktestRequest

        req = BacktestRequest(start_date=date(2024, 1, 1), end_date=date(2024, 6, 30))
        assert req.start_date == date(2024, 1, 1)
        assert req.end_date == date(2024, 6, 30)

    def test_start_equals_end_raises(self):
        """시작일 == 종료일이면 ValidationError가 발생한다"""
        from pydantic import ValidationError

        from stock_picker.portfolio.schemas import BacktestRequest

        with pytest.raises(ValidationError):
            BacktestRequest(start_date=date(2024, 1, 1), end_date=date(2024, 1, 1))

    def test_start_after_end_raises(self):
        """시작일 > 종료일이면 ValidationError가 발생한다"""
        from pydantic import ValidationError

        from stock_picker.portfolio.schemas import BacktestRequest

        with pytest.raises(ValidationError):
            BacktestRequest(start_date=date(2024, 6, 30), end_date=date(2024, 1, 1))


class TestBacktestResult:
    """BacktestResult 스키마 직렬화 테스트"""

    def test_result_has_required_fields(self):
        """BacktestResult는 daily/mdd/sharpe_ratio/total_return 필드를 포함해야 한다"""
        from stock_picker.portfolio.schemas import BacktestResult, DailyReturn

        result = BacktestResult(
            daily=[
                DailyReturn(
                    date="2024-01-02",
                    portfolio_value=1.0,
                    daily_return=0.0,
                    cumulative_return=0.0,
                )
            ],
            mdd=-0.05,
            sharpe_ratio=1.2,
            total_return=0.10,
            period_days=5,
            excluded_tickers=[],
            used_tickers=["005930"],
            disclaimer="본 백테스팅 결과는 과거 데이터 기반 시뮬레이션입니다.",
        )
        assert result.mdd == -0.05
        assert result.sharpe_ratio == 1.2
        assert result.total_return == 0.10
        assert len(result.daily) == 1

    def test_disclaimer_field_exists(self):
        """응답에 disclaimer 필드가 포함되어야 한다 (REQ-PBT-NFR-003)"""
        from stock_picker.portfolio.schemas import BacktestResult

        result = BacktestResult(
            daily=[],
            mdd=0.0,
            sharpe_ratio=0.0,
            total_return=0.0,
            period_days=0,
            excluded_tickers=[],
            used_tickers=[],
            disclaimer="투자 권유가 아니며 정보 제공 목적으로만 활용하시기 바랍니다.",
        )
        assert "disclaimer" in result.model_dump()
        assert result.disclaimer != ""


# ──────────────────────────────────────────────────────────────
# T-002: _normalize_weights 순수 함수 테스트
# ──────────────────────────────────────────────────────────────


class TestNormalizeWeights:
    """비중 정규화 함수 테스트"""

    def test_already_normalized(self):
        """합이 1.0인 비중은 그대로 반환된다"""
        from stock_picker.portfolio.backtest import _normalize_weights

        weights = [0.6, 0.4]
        result = _normalize_weights(weights)
        assert sum(result) == pytest.approx(1.0)
        assert result[0] == pytest.approx(0.6)
        assert result[1] == pytest.approx(0.4)

    def test_integer_weights_normalized(self):
        """정수형 비중(60, 40)은 0.6, 0.4로 정규화된다"""
        from stock_picker.portfolio.backtest import _normalize_weights

        result = _normalize_weights([60, 40])
        assert result[0] == pytest.approx(0.6)
        assert result[1] == pytest.approx(0.4)
        assert sum(result) == pytest.approx(1.0)

    def test_unequal_weights_normalized(self):
        """불균등 비중도 합이 1.0이 되도록 정규화된다"""
        from stock_picker.portfolio.backtest import _normalize_weights

        result = _normalize_weights([1, 2, 3])
        assert sum(result) == pytest.approx(1.0)
        assert result[0] == pytest.approx(1 / 6)
        assert result[1] == pytest.approx(2 / 6)
        assert result[2] == pytest.approx(3 / 6)

    def test_single_weight(self):
        """단일 비중은 1.0이 된다"""
        from stock_picker.portfolio.backtest import _normalize_weights

        result = _normalize_weights([100])
        assert result[0] == pytest.approx(1.0)


# ──────────────────────────────────────────────────────────────
# T-003: _align_close_series 내부 조인 테스트
# ──────────────────────────────────────────────────────────────


class TestAlignCloseSeries:
    """종가 시계열 내부 조인 정렬 테스트"""

    def test_common_dates_only(self):
        """두 종목의 공통 날짜만 반환한다"""
        from stock_picker.portfolio.backtest import _align_close_series

        price_data = {
            "A": [
                {"date": "2024-01-02", "close": 100.0},
                {"date": "2024-01-03", "close": 105.0},
                {"date": "2024-01-04", "close": 103.0},
            ],
            "B": [
                {"date": "2024-01-03", "close": 50.0},
                {"date": "2024-01-04", "close": 52.0},
                {"date": "2024-01-05", "close": 51.0},
            ],
        }
        dates, closes = _align_close_series(price_data)
        assert dates == ["2024-01-03", "2024-01-04"]
        assert closes["A"] == pytest.approx([105.0, 103.0])
        assert closes["B"] == pytest.approx([50.0, 52.0])

    def test_single_ticker_all_dates(self):
        """단일 종목은 모든 날짜가 반환된다"""
        from stock_picker.portfolio.backtest import _align_close_series

        price_data = {
            "A": [
                {"date": "2024-01-02", "close": 100.0},
                {"date": "2024-01-03", "close": 105.0},
            ],
        }
        dates, closes = _align_close_series(price_data)
        assert dates == ["2024-01-02", "2024-01-03"]
        assert closes["A"] == pytest.approx([100.0, 105.0])

    def test_dates_sorted_ascending(self):
        """날짜는 오름차순 정렬되어 반환된다"""
        from stock_picker.portfolio.backtest import _align_close_series

        price_data = {
            "A": [
                {"date": "2024-01-04", "close": 103.0},
                {"date": "2024-01-02", "close": 100.0},
                {"date": "2024-01-03", "close": 105.0},
            ],
        }
        dates, closes = _align_close_series(price_data)
        assert dates == ["2024-01-02", "2024-01-03", "2024-01-04"]


# ──────────────────────────────────────────────────────────────
# T-004: _daily_portfolio_values 테스트
# ──────────────────────────────────────────────────────────────


class TestDailyPortfolioValues:
    """일별 포트폴리오 가치 계산 테스트"""

    def test_single_ticker_100_pct(self):
        """단일 종목 100% 비중 — 포트폴리오 가치 비율 = 종가 비율"""
        from stock_picker.portfolio.backtest import _daily_portfolio_values

        aligned_closes = {"A": [100.0, 110.0, 99.0]}
        weights = [1.0]
        tickers = ["A"]
        values = _daily_portfolio_values(aligned_closes, weights, tickers)
        # 100.0 기준으로 정규화된 값
        assert values[0] == pytest.approx(1.0)
        assert values[1] == pytest.approx(1.1)
        assert values[2] == pytest.approx(0.99)

    def test_two_equal_weight_tickers(self):
        """두 종목 균등 비중(50/50) — 가중 평균 가치"""
        from stock_picker.portfolio.backtest import _daily_portfolio_values

        aligned_closes = {
            "A": [100.0, 110.0],
            "B": [100.0, 90.0],
        }
        weights = [0.5, 0.5]
        tickers = ["A", "B"]
        values = _daily_portfolio_values(aligned_closes, weights, tickers)
        assert values[0] == pytest.approx(1.0)
        # A: +10%, B: -10% → 평균 0%
        assert values[1] == pytest.approx(1.0)

    def test_weighted_different_starts(self):
        """비중 적용 시 초기값 1.0으로 정규화된다"""
        from stock_picker.portfolio.backtest import _daily_portfolio_values

        aligned_closes = {
            "A": [50.0, 55.0],
            "B": [200.0, 220.0],
        }
        weights = [0.6, 0.4]
        tickers = ["A", "B"]
        values = _daily_portfolio_values(aligned_closes, weights, tickers)
        assert values[0] == pytest.approx(1.0)
        # A: 55/50 = 1.1, B: 220/200 = 1.1 → 포트폴리오도 1.1
        assert values[1] == pytest.approx(1.1)


# ──────────────────────────────────────────────────────────────
# T-004b: _compute_returns 테스트
# ──────────────────────────────────────────────────────────────


class TestComputeReturns:
    """일별/누적 수익률 계산 테스트"""

    def test_basic_returns(self):
        """[100, 110, 99] 기반 정규화 값에서 일별 수익률 계산"""
        from stock_picker.portfolio.backtest import _compute_returns

        # 이미 1.0 기준 정규화된 포트폴리오 가치 시계열
        values = [1.0, 1.1, 0.99]
        daily, cumulative = _compute_returns(values)
        # 첫째 날 daily_return = 0
        assert daily[0] == pytest.approx(0.0)
        # 둘째 날: (1.1 - 1.0) / 1.0 = 0.1
        assert daily[1] == pytest.approx(0.1)
        # 셋째 날: (0.99 - 1.1) / 1.1 ≈ -0.1
        assert daily[2] == pytest.approx(-0.1, rel=1e-5)
        # cumulative: 첫날 = 0, 마지막날 = (0.99/1.0 - 1)
        assert cumulative[0] == pytest.approx(0.0)
        assert cumulative[-1] == pytest.approx(-0.01, rel=1e-4)

    def test_single_value_returns_zero(self):
        """값이 1개인 경우 수익률 모두 0"""
        from stock_picker.portfolio.backtest import _compute_returns

        daily, cumulative = _compute_returns([1.0])
        assert daily == [0.0]
        assert cumulative == [0.0]


# ──────────────────────────────────────────────────────────────
# T-005: _fetch_price_series_sync 테스트
# ──────────────────────────────────────────────────────────────


class TestFetchPriceSeriesSync:
    """FDR 가격 시계열 조회 동기 함수 테스트"""

    def test_returns_list_of_dicts_with_date_and_close(self):
        """FDR DataFrame 반환 시 {date, close} 딕셔너리 목록으로 변환한다"""
        mock_df = pd.DataFrame(
            {"Close": [100.0, 105.0, 103.0]},
            index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
        )
        mock_df.index.name = "Date"

        with patch("FinanceDataReader.DataReader", return_value=mock_df):
            from stock_picker.portfolio.backtest import _fetch_price_series_sync

            result = _fetch_price_series_sync("005930", date(2024, 1, 2), date(2024, 1, 4))

        assert len(result) == 3
        assert result[0]["date"] == "2024-01-02"
        assert result[0]["close"] == pytest.approx(100.0)

    def test_empty_dataframe_returns_empty_list(self):
        """빈 DataFrame 반환 시 빈 목록 반환 (예외 없음)"""
        mock_df = pd.DataFrame()

        with patch("FinanceDataReader.DataReader", return_value=mock_df):
            from stock_picker.portfolio.backtest import _fetch_price_series_sync

            result = _fetch_price_series_sync("INVALID", date(2024, 1, 1), date(2024, 1, 31))

        assert result == []

    def test_nan_rows_excluded(self):
        """NaN 종가는 제외된다"""

        mock_df = pd.DataFrame(
            {"Close": [100.0, float("nan"), 103.0]},
            index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
        )

        with patch("FinanceDataReader.DataReader", return_value=mock_df):
            from stock_picker.portfolio.backtest import _fetch_price_series_sync

            result = _fetch_price_series_sync("005930", date(2024, 1, 2), date(2024, 1, 4))

        assert len(result) == 2
        assert all(not pd.isna(r["close"]) for r in result)

    def test_lowercase_close_column(self):
        """'close' 소문자 컬럼도 인식한다"""
        mock_df = pd.DataFrame(
            {"close": [100.0, 105.0]},
            index=pd.to_datetime(["2024-01-02", "2024-01-03"]),
        )

        with patch("FinanceDataReader.DataReader", return_value=mock_df):
            from stock_picker.portfolio.backtest import _fetch_price_series_sync

            result = _fetch_price_series_sync("005930", date(2024, 1, 2), date(2024, 1, 3))

        assert len(result) == 2

    def test_exception_returns_empty_list(self):
        """FDR 예외 발생 시 빈 목록 반환 (예외 전파 금지)"""
        with patch("FinanceDataReader.DataReader", side_effect=Exception("network error")):
            from stock_picker.portfolio.backtest import _fetch_price_series_sync

            result = _fetch_price_series_sync("005930", date(2024, 1, 1), date(2024, 1, 31))

        assert result == []


# ──────────────────────────────────────────────────────────────
# T-006: run_portfolio_backtest 오케스트레이션 테스트
# ──────────────────────────────────────────────────────────────


def _make_mock_holding(ticker: str, quantity: int = 10, weight: float = 50.0, currency: str = "KRW"):
    """테스트용 보유 종목 MockObject 생성 헬퍼"""
    h = MagicMock()
    h.krx_code = ticker
    h.quantity = quantity
    h.avg_buy_price = 10000.0
    h.currency = currency
    h.market = "KRX" if currency == "KRW" else "NASDAQ"
    # weight 속성은 portfolio holding에 없으나 퍼센트로 사용
    h.weight_pct = weight
    return h


def _make_mock_portfolio(holdings: list):
    """테스트용 포트폴리오 MockObject 생성 헬퍼"""
    p = MagicMock()
    p.id = 1
    p.user_id = 1
    p.name = "테스트 포트폴리오"
    p.holdings = holdings
    return p


_PRICES_A = [
    {"date": "2024-01-02", "close": 100.0},
    {"date": "2024-01-03", "close": 105.0},
    {"date": "2024-01-04", "close": 103.0},
]
_PRICES_B = [
    {"date": "2024-01-02", "close": 50.0},
    {"date": "2024-01-03", "close": 55.0},
    {"date": "2024-01-04", "close": 52.0},
]


class TestRunPortfolioBacktest:
    """run_portfolio_backtest 오케스트레이션 테스트"""

    @pytest.mark.asyncio
    async def test_happy_path_two_tickers(self):
        """두 종목 포트폴리오 → BacktestResult 반환 (200 OK)"""
        from stock_picker.portfolio.backtest import run_portfolio_backtest

        holdings = [_make_mock_holding("A"), _make_mock_holding("B")]
        mock_portfolio = _make_mock_portfolio(holdings)

        with (
            patch(
                "stock_picker.portfolio.backtest.get_portfolio_with_holdings",
                return_value=mock_portfolio,
            ),
            patch(
                "stock_picker.portfolio.backtest._fetch_price_series_sync",
                side_effect=[_PRICES_A, _PRICES_B],
            ),
            patch(
                "stock_picker.portfolio.backtest.get_usd_krw_rate",
                return_value=1350.0,
            ),
        ):
            result = await run_portfolio_backtest(
                portfolio_id=1,
                user_id=1,
                db=MagicMock(),
                redis=MagicMock(),
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
            )

        assert len(result.daily) == 3
        assert result.used_tickers == ["A", "B"]
        assert result.excluded_tickers == []
        assert result.mdd <= 0.0
        assert result.period_days == 3
        assert "투자 권유가 아니며 정보 제공 목적" in result.disclaimer

    @pytest.mark.asyncio
    async def test_portfolio_not_found_raises_404(self):
        """포트폴리오 없음 → HTTPException 404"""
        from fastapi import HTTPException

        from stock_picker.portfolio.backtest import run_portfolio_backtest

        with patch(
            "stock_picker.portfolio.backtest.get_portfolio_with_holdings",
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await run_portfolio_backtest(
                    portfolio_id=999,
                    user_id=1,
                    db=MagicMock(),
                    redis=MagicMock(),
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 31),
                )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_empty_holdings_raises_400(self):
        """보유 종목 없음 → HTTPException 400 (REQ-PBT-021)"""
        from fastapi import HTTPException

        from stock_picker.portfolio.backtest import run_portfolio_backtest

        mock_portfolio = _make_mock_portfolio([])

        with patch(
            "stock_picker.portfolio.backtest.get_portfolio_with_holdings",
            return_value=mock_portfolio,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await run_portfolio_backtest(
                    portfolio_id=1,
                    user_id=1,
                    db=MagicMock(),
                    redis=MagicMock(),
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 31),
                )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_all_tickers_fail_raises_422(self):
        """전 종목 FDR 조회 실패 → HTTPException 422 (REQ-PBT-022)"""
        from fastapi import HTTPException

        from stock_picker.portfolio.backtest import run_portfolio_backtest

        holdings = [_make_mock_holding("INVALID1"), _make_mock_holding("INVALID2")]
        mock_portfolio = _make_mock_portfolio(holdings)

        with (
            patch(
                "stock_picker.portfolio.backtest.get_portfolio_with_holdings",
                return_value=mock_portfolio,
            ),
            patch(
                "stock_picker.portfolio.backtest._fetch_price_series_sync",
                return_value=[],
            ),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await run_portfolio_backtest(
                    portfolio_id=1,
                    user_id=1,
                    db=MagicMock(),
                    redis=MagicMock(),
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 31),
                )
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_partial_ticker_failure_excluded(self):
        """일부 종목 FDR 실패 → excluded_tickers에 포함, used_tickers에서 제외 (AC-5)"""
        from stock_picker.portfolio.backtest import run_portfolio_backtest

        holdings = [
            _make_mock_holding("A"),
            _make_mock_holding("INVALID"),
        ]
        mock_portfolio = _make_mock_portfolio(holdings)

        with (
            patch(
                "stock_picker.portfolio.backtest.get_portfolio_with_holdings",
                return_value=mock_portfolio,
            ),
            patch(
                "stock_picker.portfolio.backtest._fetch_price_series_sync",
                side_effect=[_PRICES_A, []],
            ),
            patch(
                "stock_picker.portfolio.backtest.get_usd_krw_rate",
                return_value=1350.0,
            ),
        ):
            result = await run_portfolio_backtest(
                portfolio_id=1,
                user_id=1,
                db=MagicMock(),
                redis=MagicMock(),
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
            )

        assert "INVALID" in result.excluded_tickers
        assert "A" in result.used_tickers
        assert "INVALID" not in result.used_tickers

    @pytest.mark.asyncio
    async def test_usd_ticker_applies_fx_rate(self):
        """USD 통화 종목이 있으면 USD→KRW 환율 적용 (AC-4, REQ-PBT-013)"""
        from stock_picker.portfolio.backtest import run_portfolio_backtest

        holdings = [
            _make_mock_holding("005930", currency="KRW"),
            _make_mock_holding("AAPL", currency="USD"),
        ]
        mock_portfolio = _make_mock_portfolio(holdings)

        prices_aapl = [
            {"date": "2024-01-02", "close": 185.0},
            {"date": "2024-01-03", "close": 190.0},
            {"date": "2024-01-04", "close": 188.0},
        ]

        with (
            patch(
                "stock_picker.portfolio.backtest.get_portfolio_with_holdings",
                return_value=mock_portfolio,
            ),
            patch(
                "stock_picker.portfolio.backtest._fetch_price_series_sync",
                side_effect=[_PRICES_A, prices_aapl],
            ),
            patch(
                "stock_picker.portfolio.backtest.get_usd_krw_rate",
                return_value=1350.0,
            ) as mock_rate,
        ):
            result = await run_portfolio_backtest(
                portfolio_id=1,
                user_id=1,
                db=MagicMock(),
                redis=MagicMock(),
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
            )

        # get_usd_krw_rate가 호출되어야 함
        mock_rate.assert_called_once()
        assert "AAPL" in result.used_tickers
        assert "005930" in result.used_tickers

    @pytest.mark.asyncio
    async def test_fx_rate_failure_uses_fallback(self):
        """환율 조회 실패 시 fallback 1350.0 사용, 200 반환 (REQ-PBT-015, AC-7)"""
        from stock_picker.portfolio.backtest import run_portfolio_backtest

        holdings = [_make_mock_holding("AAPL", currency="USD")]
        mock_portfolio = _make_mock_portfolio(holdings)

        with (
            patch(
                "stock_picker.portfolio.backtest.get_portfolio_with_holdings",
                return_value=mock_portfolio,
            ),
            patch(
                "stock_picker.portfolio.backtest._fetch_price_series_sync",
                return_value=_PRICES_A,
            ),
            patch(
                "stock_picker.portfolio.backtest.get_usd_krw_rate",
                return_value=1350.0,  # fallback이 반환됨을 시뮬레이션
            ),
        ):
            result = await run_portfolio_backtest(
                portfolio_id=1,
                user_id=1,
                db=MagicMock(),
                redis=MagicMock(),
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
            )

        assert result is not None
        assert len(result.daily) > 0

    @pytest.mark.asyncio
    async def test_mdd_is_non_positive(self):
        """MDD는 0 이하 음수 값이어야 한다 (AC-9)"""
        from stock_picker.portfolio.backtest import run_portfolio_backtest

        holdings = [_make_mock_holding("A")]
        mock_portfolio = _make_mock_portfolio(holdings)

        prices_volatile = [
            {"date": "2024-01-02", "close": 100.0},
            {"date": "2024-01-03", "close": 120.0},
            {"date": "2024-01-04", "close": 80.0},
        ]

        with (
            patch(
                "stock_picker.portfolio.backtest.get_portfolio_with_holdings",
                return_value=mock_portfolio,
            ),
            patch(
                "stock_picker.portfolio.backtest._fetch_price_series_sync",
                return_value=prices_volatile,
            ),
            patch(
                "stock_picker.portfolio.backtest.get_usd_krw_rate",
                return_value=1350.0,
            ),
        ):
            result = await run_portfolio_backtest(
                portfolio_id=1,
                user_id=1,
                db=MagicMock(),
                redis=MagicMock(),
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
            )

        assert result.mdd <= 0.0

    @pytest.mark.asyncio
    async def test_single_asset_value_ratio(self):
        """단일 자산 100% — 포트폴리오 가치 비율 = 종가 비율 (AC-3)"""
        from stock_picker.portfolio.backtest import run_portfolio_backtest

        holdings = [_make_mock_holding("A")]
        mock_portfolio = _make_mock_portfolio(holdings)

        prices = [
            {"date": "2024-01-02", "close": 100.0},
            {"date": "2024-01-03", "close": 150.0},
        ]

        with (
            patch(
                "stock_picker.portfolio.backtest.get_portfolio_with_holdings",
                return_value=mock_portfolio,
            ),
            patch(
                "stock_picker.portfolio.backtest._fetch_price_series_sync",
                return_value=prices,
            ),
            patch(
                "stock_picker.portfolio.backtest.get_usd_krw_rate",
                return_value=1350.0,
            ),
        ):
            result = await run_portfolio_backtest(
                portfolio_id=1,
                user_id=1,
                db=MagicMock(),
                redis=MagicMock(),
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
            )

        # 첫날 portfolio_value=1.0, 둘째날 = 1.5 (150/100)
        assert result.daily[0].portfolio_value == pytest.approx(1.0)
        assert result.daily[1].portfolio_value == pytest.approx(1.5)
        # 총 수익률 = 150/100 - 1 = 0.5
        assert result.total_return == pytest.approx(0.5, rel=1e-4)

    @pytest.mark.asyncio
    async def test_disclaimer_contains_required_text(self):
        """disclaimer에 '투자 권유가 아니며 정보 제공 목적' 문구가 포함된다 (REQ-PBT-NFR-003)"""
        from stock_picker.portfolio.backtest import run_portfolio_backtest

        holdings = [_make_mock_holding("A")]
        mock_portfolio = _make_mock_portfolio(holdings)

        with (
            patch(
                "stock_picker.portfolio.backtest.get_portfolio_with_holdings",
                return_value=mock_portfolio,
            ),
            patch(
                "stock_picker.portfolio.backtest._fetch_price_series_sync",
                return_value=_PRICES_A,
            ),
            patch(
                "stock_picker.portfolio.backtest.get_usd_krw_rate",
                return_value=1350.0,
            ),
        ):
            result = await run_portfolio_backtest(
                portfolio_id=1,
                user_id=1,
                db=MagicMock(),
                redis=MagicMock(),
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
            )

        assert "투자 권유가 아니며 정보 제공 목적" in result.disclaimer
