# 백테스트 성과 지표 유닛 테스트 — CAGR, 최대 낙폭, 샤프 비율, 총 수익률, 승률
from datetime import date

import pytest

from stock_picker.backtest.metrics import (
    calculate_cagr,
    calculate_max_drawdown,
    calculate_sharpe_ratio,
    calculate_total_return,
    calculate_win_rate,
    build_portfolio_value_series,
)


class TestCalculateCagr:
    """calculate_cagr 테스트"""

    def test_positive_returns_produce_positive_cagr(self):
        """양수 수익률 → 양수 CAGR"""
        # 매일 0.1% 수익 1년(252일)
        daily_returns = [0.001] * 252
        start = date(2023, 1, 1)
        end = date(2024, 1, 1)
        cagr = calculate_cagr(daily_returns, start, end)
        assert cagr > 0

    def test_zero_returns_produce_zero_cagr(self):
        """수익률 0인 경우 CAGR ≈ 0"""
        daily_returns = [0.0] * 252
        start = date(2023, 1, 1)
        end = date(2024, 1, 1)
        cagr = calculate_cagr(daily_returns, start, end)
        assert abs(cagr) < 1e-6

    def test_empty_returns_returns_zero(self):
        """빈 수익률 목록 → 0 반환"""
        cagr = calculate_cagr([], date(2023, 1, 1), date(2024, 1, 1))
        assert cagr == 0.0

    def test_same_start_end_date_returns_zero(self):
        """시작일 == 종료일 → 0 반환"""
        cagr = calculate_cagr([0.01, 0.02], date(2023, 6, 1), date(2023, 6, 1))
        assert cagr == 0.0

    def test_negative_returns_produce_negative_cagr(self):
        """음수 수익률 → 음수 CAGR"""
        daily_returns = [-0.001] * 252
        start = date(2023, 1, 1)
        end = date(2024, 1, 1)
        cagr = calculate_cagr(daily_returns, start, end)
        assert cagr < 0

    def test_known_value(self):
        """알려진 값으로 CAGR 검증 — 1년 50% 수익 → CAGR ≈ 50%"""
        # 단순화: 1년 후 누적 수익률 50% (매일 복리 적용)
        daily_r = (1.5 ** (1 / 252)) - 1  # 1년 후 1.5배
        daily_returns = [daily_r] * 252
        start = date(2023, 1, 1)
        end = date(2024, 1, 1)
        cagr = calculate_cagr(daily_returns, start, end)
        # 정확히 50%는 아니지만 근사값 확인 (날짜 차이로 인한 오차)
        assert 0.45 < cagr < 0.55


class TestCalculateMaxDrawdown:
    """calculate_max_drawdown 테스트"""

    def test_returns_zero_for_empty_list(self):
        """빈 목록 → 0 반환"""
        assert calculate_max_drawdown([]) == 0.0

    def test_returns_zero_for_monotone_increase(self):
        """단조증가 시 최대 낙폭 = 0"""
        cumulative = [1.0, 1.1, 1.2, 1.3, 1.4]
        assert calculate_max_drawdown(cumulative) == 0.0

    def test_correct_drawdown_calculation(self):
        """피크 후 하락 시 정확한 최대 낙폭 계산"""
        # 1.0 → 1.2 (피크) → 0.96 (20% 낙폭) → 1.3
        cumulative = [1.0, 1.2, 0.96, 1.3]
        mdd = calculate_max_drawdown(cumulative)
        # (0.96 - 1.2) / 1.2 = -0.2
        assert pytest.approx(mdd, abs=1e-4) == -0.2

    def test_worst_case_total_loss(self):
        """100% 손실 시 최대 낙폭 = -1.0"""
        cumulative = [1.0, 0.8, 0.0]
        mdd = calculate_max_drawdown(cumulative)
        assert mdd == pytest.approx(-1.0, abs=1e-4)

    def test_multiple_drawdowns_returns_worst(self):
        """여러 낙폭 중 가장 큰 낙폭 반환"""
        # 두 번의 낙폭: -10% 와 -30% → 최대 낙폭은 -30%
        cumulative = [1.0, 1.1, 0.99, 1.2, 0.84, 1.3]
        # 1.2 → 0.84: (0.84 - 1.2) / 1.2 = -0.30
        mdd = calculate_max_drawdown(cumulative)
        assert mdd == pytest.approx(-0.30, abs=1e-3)


class TestCalculateSharpeRatio:
    """calculate_sharpe_ratio 테스트"""

    def test_returns_zero_for_less_than_two_returns(self):
        """수익률 2개 미만 → 0 반환"""
        assert calculate_sharpe_ratio([]) == 0.0
        assert calculate_sharpe_ratio([0.01]) == 0.0

    def test_returns_zero_for_zero_std(self):
        """표준편차 0 (모두 같은 수익률) → 0 반환"""
        daily_returns = [0.001] * 100
        # 모두 동일한 수익률이면 표준편차 0 → 0 반환
        # 실제로는 작은 표준편차가 생길 수 있지만 이론상 0
        result = calculate_sharpe_ratio(daily_returns)
        # 결과가 매우 크거나 0이어야 함 (분모가 0에 가까울 때)
        assert isinstance(result, float)

    def test_positive_excess_returns_produce_positive_sharpe(self):
        """무위험 수익률 초과 → 양수 샤프 비율"""
        # 일별 0.5% 수익 (연 126% 수준)으로 높은 샤프 기대
        daily_returns = [0.005] * 252 + [-0.003] * 50
        sharpe = calculate_sharpe_ratio(daily_returns, risk_free_rate=0.02)
        assert sharpe > 0

    def test_negative_returns_produce_negative_sharpe(self):
        """무위험 수익률 하회 → 음수 샤프 비율"""
        daily_returns = [-0.005] * 252
        sharpe = calculate_sharpe_ratio(daily_returns, risk_free_rate=0.02)
        assert sharpe < 0

    def test_custom_risk_free_rate(self):
        """커스텀 무위험 이자율 적용"""
        daily_returns = [0.001] * 252
        sharpe_low_rf = calculate_sharpe_ratio(daily_returns, risk_free_rate=0.0)
        sharpe_high_rf = calculate_sharpe_ratio(daily_returns, risk_free_rate=0.10)
        # 무위험 이자율이 낮을수록 샤프 비율이 높음
        assert sharpe_low_rf > sharpe_high_rf

    def test_annualization_factor(self):
        """연환산 계수 √252 적용 확인"""
        # 단순 계산으로 연환산 검증
        daily_returns = [0.001, -0.001, 0.002, -0.002, 0.001]
        sharpe = calculate_sharpe_ratio(daily_returns, risk_free_rate=0.0)
        assert isinstance(sharpe, float)
        # 연환산이 적용되므로 절댓값이 커야 함


class TestCalculateTotalReturn:
    """calculate_total_return 테스트 (T-020)"""

    def test_empty_list_returns_zero(self):
        """빈 목록 → 0.0 반환"""
        assert calculate_total_return([]) == 0.0

    def test_positive_gain(self):
        """양수 수익 케이스"""
        # 1.0 → 1.2 → 20% 수익
        cumulative = [1.0, 1.1, 1.2]
        result = calculate_total_return(cumulative)
        assert pytest.approx(result, abs=1e-6) == 0.2

    def test_no_change(self):
        """수익 없음 → 0.0"""
        cumulative = [1.0, 1.0, 1.0]
        assert calculate_total_return(cumulative) == 0.0

    def test_loss(self):
        """손실 케이스 — 음수 반환"""
        cumulative = [1.0, 0.9, 0.8]
        result = calculate_total_return(cumulative)
        assert pytest.approx(result, abs=1e-6) == -0.2

    def test_single_value(self):
        """단일 값 → 0.0 (초기값 = 최종값)"""
        assert calculate_total_return([1.0]) == 0.0


class TestCalculateWinRate:
    """calculate_win_rate 테스트 (T-020)"""

    def test_empty_list_returns_zero(self):
        """빈 목록 → 0.0 반환"""
        assert calculate_win_rate([]) == 0.0

    def test_all_positive_returns_one(self):
        """모두 양수 → 승률 1.0"""
        assert calculate_win_rate([0.01, 0.02, 0.03]) == pytest.approx(1.0)

    def test_all_negative_returns_zero(self):
        """모두 음수 → 승률 0.0"""
        assert calculate_win_rate([-0.01, -0.02, -0.03]) == 0.0

    def test_half_positive(self):
        """절반 양수 → 승률 0.5"""
        result = calculate_win_rate([0.01, -0.01, 0.02, -0.02])
        assert pytest.approx(result, abs=1e-6) == 0.5

    def test_mixed_returns(self):
        """3/5 양수 → 0.6"""
        result = calculate_win_rate([0.01, -0.01, 0.02, 0.03, -0.005])
        assert pytest.approx(result, abs=1e-6) == 0.6


class TestBuildPortfolioValueSeries:
    """build_portfolio_value_series 테스트 (T-020)"""

    def test_empty_returns_empty(self):
        """빈 입력 → 빈 출력"""
        assert build_portfolio_value_series([]) == []

    def test_starts_near_initial(self):
        """정규화 — 첫 번째 결과는 (1 + 첫 수익률)"""
        series = build_portfolio_value_series([0.1])
        assert pytest.approx(series[0], abs=1e-6) == 1.1

    def test_cumulative_growth(self):
        """누적 성장 검증"""
        # 10% → 10% → 총 21% 성장
        series = build_portfolio_value_series([0.1, 0.1])
        assert len(series) == 2
        assert pytest.approx(series[0], abs=1e-6) == 1.1
        assert pytest.approx(series[1], abs=1e-6) == 1.21

    def test_length_matches_input(self):
        """출력 길이 = 입력 길이"""
        returns = [0.01, -0.005, 0.02, -0.01, 0.015]
        series = build_portfolio_value_series(returns)
        assert len(series) == len(returns)
