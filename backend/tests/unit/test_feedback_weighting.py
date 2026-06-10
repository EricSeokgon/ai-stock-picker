# 피드백 계수 계산 단위 테스트 (SPEC-STOCK-009 TASK-008)
import pytest

from stock_picker.feedback.weighting import (
    MAX_ADJ,
    MIN_VOTES_FOR_CONFIDENCE,
    calculate_feedback_coefficient,
)


class TestCalculateFeedbackCoefficient:
    """calculate_feedback_coefficient 함수 단위 테스트."""

    def test_zero_votes_returns_zero(self):
        """투표 0건이면 0.0 반환."""
        assert calculate_feedback_coefficient(0, 0) == 0.0

    def test_all_up_max_confidence(self):
        """충분한 up 투표만 있으면 MAX_ADJ 반환."""
        # MIN_VOTES_FOR_CONFIDENCE 이상의 up 투표 → 신뢰도 1.0
        result = calculate_feedback_coefficient(100, 0)
        assert result == pytest.approx(MAX_ADJ, abs=1e-9)

    def test_all_down_max_confidence(self):
        """충분한 down 투표만 있으면 -MAX_ADJ 반환."""
        result = calculate_feedback_coefficient(0, 100)
        assert result == pytest.approx(-MAX_ADJ, abs=1e-9)

    def test_clamp_high(self):
        """극단적 up 투표에서 MAX_ADJ로 클램프."""
        result = calculate_feedback_coefficient(10000, 0)
        assert result == pytest.approx(MAX_ADJ, abs=1e-9)

    def test_clamp_low(self):
        """극단적 down 투표에서 -MAX_ADJ로 클램프."""
        result = calculate_feedback_coefficient(0, 10000)
        assert result == pytest.approx(-MAX_ADJ, abs=1e-9)

    def test_confidence_scaling(self):
        """투표 수가 적으면 같은 비율이라도 계수가 작아야 한다."""
        # 동일 비율 (up 100%) 이지만 투표 수 차이
        small = calculate_feedback_coefficient(1, 0)   # 투표 1건 — 낮은 신뢰도
        large = calculate_feedback_coefficient(100, 0)  # 투표 100건 — 높은 신뢰도
        assert small < large

    def test_mixed_votes(self):
        """up > down인 경우 양의 계수 반환."""
        result = calculate_feedback_coefficient(3, 2)
        # net = (3-2)/(3+2) = 0.2, total=5, confidence=1.0
        # coefficient = 0.2 * 1.0 * 0.15 = 0.03
        assert result > 0.0
        assert result < MAX_ADJ

    def test_equal_votes_returns_zero(self):
        """up == down이면 0.0 반환 (net = 0)."""
        result = calculate_feedback_coefficient(5, 5)
        assert result == pytest.approx(0.0, abs=1e-9)

    def test_partial_confidence(self):
        """신뢰도가 MIN_VOTES_FOR_CONFIDENCE 미만이면 감소된 계수 반환."""
        # MIN_VOTES_FOR_CONFIDENCE = 5, 투표 1건 up → confidence = 1/5 = 0.2
        result = calculate_feedback_coefficient(1, 0)
        expected = 1.0 * (1 / MIN_VOTES_FOR_CONFIDENCE) * MAX_ADJ
        assert result == pytest.approx(expected, abs=1e-9)

    def test_return_type_is_float(self):
        """반환값이 항상 float 타입이어야 한다."""
        assert isinstance(calculate_feedback_coefficient(0, 0), float)
        assert isinstance(calculate_feedback_coefficient(5, 3), float)
