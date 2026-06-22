# 포트폴리오 리스크 분석 단위 테스트 (SPEC-STOCK-027)
# TDD RED-GREEN-REFACTOR 사이클
# asyncio_mode = "auto" — @pytest.mark.asyncio 불필요
import json
import math
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest


# ──────────────────────────────────────────────────────────────
# 순수 함수 테스트 (T1-2)
# ──────────────────────────────────────────────────────────────

class TestCorrelationMatrix:
    """상관관계 행렬 계산 순수 함수 테스트"""

    def test_correlation_matrix_diagonal_is_one(self):
        """동일 종목 자기 자신과의 상관관계는 1.0이어야 한다"""
        from stock_picker.portfolio.risk_analysis import _correlation_matrix

        returns = {
            "AAPL": np.array([0.01, -0.02, 0.03, 0.01, -0.01]),
            "TSLA": np.array([0.05, -0.03, 0.02, -0.01, 0.04]),
        }
        result = _correlation_matrix(returns)
        assert result["AAPL"]["AAPL"] == pytest.approx(1.0)
        assert result["TSLA"]["TSLA"] == pytest.approx(1.0)

    def test_correlation_matrix_range(self):
        """모든 상관계수는 [-1, 1] 범위 내에 있어야 한다"""
        from stock_picker.portfolio.risk_analysis import _correlation_matrix

        returns = {
            "A": np.array([0.01, -0.02, 0.03, 0.01, -0.01]),
            "B": np.array([0.05, -0.03, 0.02, -0.01, 0.04]),
            "C": np.array([-0.01, 0.02, -0.01, 0.03, 0.00]),
        }
        result = _correlation_matrix(returns)
        for ticker_i, row in result.items():
            for ticker_j, val in row.items():
                assert -1.0 <= val <= 1.0, f"{ticker_i}-{ticker_j} 상관계수 범위 초과: {val}"

    def test_correlation_negative(self):
        """음의 상관관계를 가진 수익률 시리즈는 음의 상관계수를 반환해야 한다"""
        from stock_picker.portfolio.risk_analysis import _correlation_matrix

        # A와 B는 완전 음의 상관
        x = np.array([0.01, 0.02, -0.01, 0.03, -0.02])
        returns = {
            "A": x,
            "B": -x,
        }
        result = _correlation_matrix(returns)
        assert result["A"]["B"] < 0.0, "음의 상관 시리즈에서 상관계수는 음수여야 한다"

    def test_correlation_insufficient_days(self):
        """공통 거래일이 2개 미만인 종목 쌍은 0.0을 반환해야 한다 (NaN 금지)"""
        from stock_picker.portfolio.risk_analysis import _correlation_matrix

        # 길이 1짜리 배열 → corrcoef 계산 불가 → 0.0 반환
        returns = {
            "A": np.array([0.01]),
            "B": np.array([0.02]),
        }
        result = _correlation_matrix(returns)
        assert result["A"]["B"] == pytest.approx(0.0)
        assert not math.isnan(result["A"]["B"]), "NaN이 포함되면 안 된다"


class TestAnnualizedVolatility:
    """연환산 변동성 계산 순수 함수 테스트"""

    def test_annualized_volatility_formula(self):
        """알려진 std에 대해 std × √252 × 100 공식을 검증한다"""
        from stock_picker.portfolio.risk_analysis import _annualized_volatility

        # 표준편차 0.01인 수익률 배열
        returns = np.full(252, 0.01)
        returns = returns - returns.mean() + 0.0  # mean=0으로 조정
        # 직접 생성: std = 0.01
        returns = np.array([0.01, -0.01] * 50)  # std ≈ 0.01
        actual_std = np.std(returns, ddof=1)
        expected_vol = actual_std * math.sqrt(252) * 100

        result = _annualized_volatility(returns)
        assert result == pytest.approx(expected_vol, rel=1e-6)


class TestPortfolioVolatility:
    """포트폴리오 변동성 계산 순수 함수 테스트"""

    def test_portfolio_volatility_single_asset(self):
        """단일 자산 포트폴리오의 변동성은 해당 자산의 변동성과 동일해야 한다"""
        from stock_picker.portfolio.risk_analysis import (
            _annualized_volatility,
            _portfolio_volatility,
        )

        returns = np.array([0.01, -0.02, 0.03, -0.01, 0.02, 0.00, -0.01, 0.02])
        aligned_returns = {"AAPL": returns}
        weights = np.array([1.0])

        port_vol = _portfolio_volatility(weights, aligned_returns)
        asset_vol = _annualized_volatility(returns)
        assert port_vol == pytest.approx(asset_vol, rel=1e-4)


class TestDiversificationBenefit:
    """분산 효과 계산 순수 함수 테스트"""

    def test_diversification_benefit_negative_clamped(self):
        """포트폴리오 변동성이 가중평균 변동성보다 클 때 0.0으로 클램핑되어야 한다"""
        from stock_picker.portfolio.risk_analysis import _diversification_benefit

        # port_vol > weighted_avg_vol → benefit이 음수 → 0.0으로 클램프
        port_vol = 30.0
        weights = np.array([0.5, 0.5])
        vols = [20.0, 20.0]  # weighted_avg = 20.0

        result = _diversification_benefit(port_vol, weights, vols)
        assert result == pytest.approx(0.0)

    def test_diversification_benefit_positive(self):
        """분산된 포트폴리오는 양의 분산 효과를 가져야 한다"""
        from stock_picker.portfolio.risk_analysis import _diversification_benefit

        # port_vol < weighted_avg_vol → 양의 분산 효과
        port_vol = 15.0
        weights = np.array([0.5, 0.5])
        vols = [25.0, 25.0]  # weighted_avg = 25.0

        result = _diversification_benefit(port_vol, weights, vols)
        # (1 - 15/25) * 100 = 40.0
        assert result == pytest.approx(40.0, rel=1e-4)
        assert result > 0.0


# ──────────────────────────────────────────────────────────────
# 오케스트레이션 함수 테스트 (T1-4)
# ──────────────────────────────────────────────────────────────

def _make_portfolio(portfolio_id: int = 1, user_id: int = 1):
    """테스트용 포트폴리오 Mock 객체 생성"""
    portfolio = MagicMock()
    portfolio.id = portfolio_id
    portfolio.user_id = user_id
    return portfolio


def _make_holding(krx_code: str = "005930", quantity: int = 10, avg_buy_price: float = 70000.0):
    """테스트용 보유 종목 Mock 객체 생성"""
    holding = MagicMock()
    holding.krx_code = krx_code
    holding.quantity = quantity
    holding.avg_buy_price = avg_buy_price
    return holding


def _make_price_history(krx_code: str, n: int = 10) -> list[dict]:
    """결정론적 가격 이력 생성 (테스트용)"""
    prices = []
    base = 70000.0
    for i in range(n):
        prices.append({
            "date": f"2026-01-{i + 1:02d}",
            "close": base * (1 + 0.01 * (i % 5 - 2)),
        })
    return prices


def _make_risk_result_json() -> str:
    """캐시 히트용 JSON 픽스처"""
    return json.dumps({
        "correlation_matrix": {"005930": {"005930": 1.0}},
        "holdings_volatility": [
            {
                "krx_code": "005930",
                "name": "삼성전자",
                "annualized_volatility_pct": 28.5,
                "price_data_days": 85,
            }
        ],
        "portfolio_volatility_pct": 28.5,
        "diversification_benefit_pct": 0.0,
        "period_days": 90,
        "calculated_at": "2026-06-18T00:00:00",
    })


class TestRiskAnalysisOrchestration:
    """calculate_risk_analysis 오케스트레이션 테스트 (T1-4)"""

    async def test_risk_analysis_cache_hit_skips_fdr(self):
        """Redis 캐시 히트 시 FDR을 호출하지 않아야 한다"""
        from stock_picker.portfolio.risk_analysis import calculate_risk_analysis

        db = MagicMock()
        redis = AsyncMock()

        portfolio = _make_portfolio()
        holding = _make_holding()

        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = [holding]

        cached_json = _make_risk_result_json()
        redis.get = AsyncMock(return_value=cached_json)

        with patch(
            "stock_picker.portfolio.risk_analysis._fetch_stock_prices",
        ) as mock_fdr:
            result = await calculate_risk_analysis(
                portfolio_id=1, user_id=1, db=db, redis=redis, period=90
            )

        mock_fdr.assert_not_called()
        assert result.portfolio_volatility_pct == pytest.approx(28.5)

    async def test_risk_analysis_cache_miss_calls_fdr(self):
        """캐시 미스 시 FDR을 호출하고 결과를 캐시에 저장해야 한다"""
        from stock_picker.portfolio.risk_analysis import calculate_risk_analysis

        db = MagicMock()
        redis = AsyncMock()

        portfolio = _make_portfolio()
        h1 = _make_holding("005930", 10, 70000.0)
        h2 = _make_holding("000660", 5, 120000.0)

        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = [h1, h2]

        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()

        price_data_1 = _make_price_history("005930", 10)
        price_data_2 = _make_price_history("000660", 10)

        with patch(
            "stock_picker.portfolio.risk_analysis._fetch_stock_prices",
            side_effect=[price_data_1, price_data_2],
        ) as mock_fdr:
            result = await calculate_risk_analysis(
                portfolio_id=1, user_id=1, db=db, redis=redis, period=90
            )

        assert mock_fdr.call_count == 2
        redis.setex.assert_called_once()
        assert result.period_days == 90

    async def test_risk_analysis_refresh_ignores_cache(self):
        """refresh=True이면 캐시가 있어도 FDR을 호출해야 한다"""
        from stock_picker.portfolio.risk_analysis import calculate_risk_analysis

        db = MagicMock()
        redis = AsyncMock()

        portfolio = _make_portfolio()
        h1 = _make_holding("005930", 10, 70000.0)
        h2 = _make_holding("000660", 5, 120000.0)

        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = [h1, h2]

        # 캐시가 있어도 refresh=True이면 무시
        redis.get = AsyncMock(return_value=_make_risk_result_json())
        redis.setex = AsyncMock()

        price_data_1 = _make_price_history("005930", 10)
        price_data_2 = _make_price_history("000660", 10)

        with patch(
            "stock_picker.portfolio.risk_analysis._fetch_stock_prices",
            side_effect=[price_data_1, price_data_2],
        ) as mock_fdr:
            result = await calculate_risk_analysis(
                portfolio_id=1, user_id=1, db=db, redis=redis, period=90, refresh=True
            )

        assert mock_fdr.call_count == 2

    async def test_risk_analysis_redis_unavailable_graceful(self):
        """Redis 장애 시 캐시 없이 계산을 수행해야 한다"""
        from stock_picker.portfolio.risk_analysis import calculate_risk_analysis

        db = MagicMock()
        redis = AsyncMock()

        portfolio = _make_portfolio()
        h1 = _make_holding("005930", 10, 70000.0)
        h2 = _make_holding("000660", 5, 120000.0)

        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = [h1, h2]

        # Redis 조회 시 예외 발생
        redis.get = AsyncMock(side_effect=Exception("Redis 연결 실패"))
        redis.setex = AsyncMock(side_effect=Exception("Redis 저장 실패"))

        price_data_1 = _make_price_history("005930", 10)
        price_data_2 = _make_price_history("000660", 10)

        with patch(
            "stock_picker.portfolio.risk_analysis._fetch_stock_prices",
            side_effect=[price_data_1, price_data_2],
        ):
            result = await calculate_risk_analysis(
                portfolio_id=1, user_id=1, db=db, redis=redis, period=90
            )

        # Redis 실패에도 결과가 반환되어야 한다
        assert result is not None
        assert result.period_days == 90

    async def test_risk_analysis_fdr_failure_excludes_stock(self):
        """한 종목의 FDR 조회가 실패하면 해당 종목을 제외하고 계속해야 한다"""
        from stock_picker.portfolio.risk_analysis import calculate_risk_analysis

        db = MagicMock()
        redis = AsyncMock()

        portfolio = _make_portfolio()
        h1 = _make_holding("005930", 10, 70000.0)
        h2 = _make_holding("000660", 5, 120000.0)
        h3 = _make_holding("035420", 3, 300000.0)  # 이 종목 FDR 실패

        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = [h1, h2, h3]

        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()

        price_data_1 = _make_price_history("005930", 10)
        price_data_2 = _make_price_history("000660", 10)

        # 세 번째 종목은 빈 데이터 반환 (실패 시나리오)
        def side_effect(krx_code, period):
            if krx_code == "035420":
                return []  # 빈 데이터
            elif krx_code == "005930":
                return price_data_1
            else:
                return price_data_2

        with patch(
            "stock_picker.portfolio.risk_analysis._fetch_stock_prices",
            side_effect=side_effect,
        ):
            result = await calculate_risk_analysis(
                portfolio_id=1, user_id=1, db=db, redis=redis, period=90
            )

        # 실패 종목 제외, 2개 유효 종목으로 결과 반환
        valid_codes = [h.krx_code for h in result.holdings_volatility]
        assert "035420" not in valid_codes
        assert len(valid_codes) == 2

    async def test_risk_analysis_fewer_than_two_valid_raises_400(self):
        """유효 종목이 2개 미만이면 HTTP 400을 발생시켜야 한다"""
        from fastapi import HTTPException

        from stock_picker.portfolio.risk_analysis import calculate_risk_analysis

        db = MagicMock()
        redis = AsyncMock()

        portfolio = _make_portfolio()
        h1 = _make_holding("005930", 10, 70000.0)  # 유일한 보유, FDR 실패

        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = [h1]

        redis.get = AsyncMock(return_value=None)

        with patch(
            "stock_picker.portfolio.risk_analysis._fetch_stock_prices",
            return_value=[],  # 빈 데이터
        ):
            with pytest.raises(HTTPException) as exc_info:
                await calculate_risk_analysis(
                    portfolio_id=1, user_id=1, db=db, redis=redis, period=90
                )

        assert exc_info.value.status_code == 400


# ──────────────────────────────────────────────────────────────
# T-007: 해외 자산 리스크 분석 지원 (SPEC-STOCK-028)
# ──────────────────────────────────────────────────────────────

def _make_holding_with_market(
    krx_code: str = "005930",
    quantity: int = 10,
    avg_buy_price: float = 70000.0,
    market: str = "KRX",
    currency: str = "KRW",
):
    """market/currency 속성을 가진 테스트용 보유 종목 Mock 생성"""
    holding = MagicMock()
    holding.krx_code = krx_code
    holding.quantity = quantity
    holding.avg_buy_price = avg_buy_price
    holding.market = market
    holding.currency = currency
    return holding


class TestRiskAnalysisForeignAssetSupport:
    """T-007: 혼합 KRX+NASDAQ 포트폴리오 리스크 분석 테스트"""

    async def test_mixed_krx_nasdaq_portfolio_uses_fdr_for_foreign(self):
        """혼합 KRX+NASDAQ 포트폴리오에서 외국 종목 가격도 FDR로 조회하여 계산에 포함된다"""
        from stock_picker.portfolio.risk_analysis import calculate_risk_analysis

        db = MagicMock()
        redis = AsyncMock()

        portfolio = _make_portfolio()
        h_krx = _make_holding_with_market("005930", 10, 70000.0, "KRX", "KRW")
        h_nasdaq = _make_holding_with_market("AAPL", 5, 150.0, "NASDAQ", "USD")

        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = [h_krx, h_nasdaq]

        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()

        krx_prices = _make_price_history("005930", n=20)
        nasdaq_prices = _make_price_history("AAPL", n=20)

        def side_effect(code, period):
            if code == "005930":
                return krx_prices
            if code == "AAPL":
                return nasdaq_prices
            return []

        with patch(
            "stock_picker.portfolio.risk_analysis._fetch_stock_prices",
            side_effect=side_effect,
        ):
            with patch(
                "stock_picker.portfolio.risk_analysis.fx_rate_module.get_usd_krw_rate",
                new=AsyncMock(return_value=1350.0),
            ):
                result = await calculate_risk_analysis(
                    portfolio_id=1, user_id=1, db=db, redis=redis, period=90
                )

        # 두 종목 모두 변동성 결과에 포함되어야 한다
        codes = [hv.krx_code for hv in result.holdings_volatility]
        assert "005930" in codes
        assert "AAPL" in codes

    async def test_weights_use_krw_converted_value_for_usd_holdings(self):
        """USD 보유 종목 가중치 계산 시 KRW 환산 금액(USD price × fx_rate)을 사용한다"""
        from stock_picker.portfolio.risk_analysis import calculate_risk_analysis

        db = MagicMock()
        redis = AsyncMock()

        portfolio = _make_portfolio()
        # KRX: 10주 × 100,000원 = 1,000,000원
        h_krx = _make_holding_with_market("005930", 10, 100000.0, "KRX", "KRW")
        # NASDAQ: 5주 × 200 USD × 1000 fx_rate = 1,000,000원 → 동일 비중
        h_nasdaq = _make_holding_with_market("AAPL", 5, 200.0, "NASDAQ", "USD")

        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = [h_krx, h_nasdaq]

        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()

        krx_prices = _make_price_history("005930", n=20)
        nasdaq_prices = _make_price_history("AAPL", n=20)

        def side_effect(code, period):
            return krx_prices if code == "005930" else nasdaq_prices

        with patch(
            "stock_picker.portfolio.risk_analysis._fetch_stock_prices",
            side_effect=side_effect,
        ):
            with patch(
                "stock_picker.portfolio.risk_analysis.fx_rate_module.get_usd_krw_rate",
                new=AsyncMock(return_value=1000.0),
            ):
                result = await calculate_risk_analysis(
                    portfolio_id=1, user_id=1, db=db, redis=redis, period=90
                )

        # 결과 스키마 구조가 변경되지 않아야 한다
        assert hasattr(result, "correlation_matrix")
        assert hasattr(result, "holdings_volatility")
        assert hasattr(result, "portfolio_volatility_pct")
        assert hasattr(result, "diversification_benefit_pct")
        # 두 종목 모두 포함되어야 한다
        assert len(result.holdings_volatility) == 2

    async def test_insufficient_foreign_data_excluded_gracefully(self):
        """데이터 부족한 외국 종목은 gracefully 제외된다 (KRX 동일 동작)"""
        from stock_picker.portfolio.risk_analysis import calculate_risk_analysis

        db = MagicMock()
        redis = AsyncMock()

        portfolio = _make_portfolio()
        h1 = _make_holding_with_market("005930", 10, 70000.0, "KRX", "KRW")
        h2 = _make_holding_with_market("000660", 5, 100000.0, "KRX", "KRW")
        h3 = _make_holding_with_market("AAPL", 3, 150.0, "NASDAQ", "USD")  # 데이터 없음

        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = [h1, h2, h3]

        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()

        krx_prices_1 = _make_price_history("005930", n=20)
        krx_prices_2 = _make_price_history("000660", n=20)

        def side_effect(code, period):
            if code == "005930":
                return krx_prices_1
            if code == "000660":
                return krx_prices_2
            return []  # AAPL 데이터 없음

        with patch(
            "stock_picker.portfolio.risk_analysis._fetch_stock_prices",
            side_effect=side_effect,
        ):
            with patch(
                "stock_picker.portfolio.risk_analysis.fx_rate_module.get_usd_krw_rate",
                new=AsyncMock(return_value=1350.0),
            ):
                result = await calculate_risk_analysis(
                    portfolio_id=1, user_id=1, db=db, redis=redis, period=90
                )

        codes = [hv.krx_code for hv in result.holdings_volatility]
        assert "AAPL" not in codes
        assert "005930" in codes
        assert "000660" in codes

    async def test_response_schema_unchanged_for_foreign_portfolio(self):
        """해외 자산 포함 포트폴리오도 응답 스키마 구조가 동일하다"""
        from stock_picker.portfolio.risk_analysis import calculate_risk_analysis
        from stock_picker.portfolio.schemas import RiskAnalysisResult

        db = MagicMock()
        redis = AsyncMock()

        portfolio = _make_portfolio()
        h_krx = _make_holding_with_market("005930", 10, 70000.0, "KRX", "KRW")
        h_nasdaq = _make_holding_with_market("TSLA", 2, 200.0, "NASDAQ", "USD")

        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = [h_krx, h_nasdaq]

        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()

        prices = _make_price_history("any", n=20)

        with patch(
            "stock_picker.portfolio.risk_analysis._fetch_stock_prices",
            return_value=prices,
        ):
            with patch(
                "stock_picker.portfolio.risk_analysis.fx_rate_module.get_usd_krw_rate",
                new=AsyncMock(return_value=1350.0),
            ):
                result = await calculate_risk_analysis(
                    portfolio_id=1, user_id=1, db=db, redis=redis, period=90
                )

        assert isinstance(result, RiskAnalysisResult)

    async def test_krx_only_portfolio_backward_compatible(self):
        """KRX 전용 포트폴리오는 기존과 동일하게 동작한다 (역방향 호환성)"""
        from stock_picker.portfolio.risk_analysis import calculate_risk_analysis

        db = MagicMock()
        redis = AsyncMock()

        portfolio = _make_portfolio()
        h1 = _make_holding_with_market("005930", 10, 70000.0, "KRX", "KRW")
        h2 = _make_holding_with_market("000660", 5, 100000.0, "KRX", "KRW")

        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = [h1, h2]

        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()

        prices = _make_price_history("any", n=20)

        with patch(
            "stock_picker.portfolio.risk_analysis._fetch_stock_prices",
            return_value=prices,
        ):
            result = await calculate_risk_analysis(
                portfolio_id=1, user_id=1, db=db, redis=redis, period=90
            )

        codes = [hv.krx_code for hv in result.holdings_volatility]
        assert "005930" in codes
        assert "000660" in codes
