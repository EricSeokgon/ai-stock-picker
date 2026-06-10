# 점수 조정 단위 테스트 (SPEC-STOCK-009 TASK-008)
import pytest

from stock_picker.feedback.weighting import apply_feedback_adjustment
from stock_picker.scoring.engine import (
    calculate_stock_score,
    decompose_score,
)


class TestApplyFeedbackAdjustment:
    """apply_feedback_adjustment 함수 단위 테스트."""

    def test_apply_no_feedback(self):
        """계수 0.0이면 조정 없음 — adjusted=base, feedback_score=0.0."""
        adjusted, fb_score = apply_feedback_adjustment(0.5, 0.0)
        assert adjusted == pytest.approx(0.5)
        assert fb_score == pytest.approx(0.0)

    def test_apply_positive(self):
        """양의 계수 적용 시 점수 증가."""
        adjusted, fb_score = apply_feedback_adjustment(0.5, 0.1)
        assert adjusted == pytest.approx(0.6)
        assert fb_score == pytest.approx(0.1)

    def test_apply_negative(self):
        """음의 계수 적용 시 점수 감소."""
        adjusted, fb_score = apply_feedback_adjustment(0.5, -0.1)
        assert adjusted == pytest.approx(0.4)
        assert fb_score == pytest.approx(-0.1)

    def test_clamp_above_one(self):
        """조정 후 1.0 초과 시 1.0으로 클램프."""
        adjusted, fb_score = apply_feedback_adjustment(0.95, 0.15)
        assert adjusted == pytest.approx(1.0)
        # 실제 적용된 delta는 요청값보다 작아야 함
        assert fb_score == pytest.approx(0.05, abs=1e-9)

    def test_clamp_below_zero(self):
        """조정 후 0.0 미만 시 0.0으로 클램프."""
        adjusted, fb_score = apply_feedback_adjustment(0.05, -0.15)
        assert adjusted == pytest.approx(0.0)
        # 실제 적용된 delta는 요청값보다 작은 절대값이어야 함
        assert fb_score == pytest.approx(-0.05, abs=1e-9)

    def test_no_adjustment_at_boundary_one(self):
        """base=1.0, 계수 양수 → adjusted=1.0, feedback_score=0.0."""
        adjusted, fb_score = apply_feedback_adjustment(1.0, 0.1)
        assert adjusted == pytest.approx(1.0)
        assert fb_score == pytest.approx(0.0)

    def test_no_adjustment_at_boundary_zero(self):
        """base=0.0, 계수 음수 → adjusted=0.0, feedback_score=0.0."""
        adjusted, fb_score = apply_feedback_adjustment(0.0, -0.1)
        assert adjusted == pytest.approx(0.0)
        assert fb_score == pytest.approx(0.0)

    def test_return_types_are_float(self):
        """반환값이 항상 float 튜플이어야 한다."""
        adjusted, fb_score = apply_feedback_adjustment(0.5, 0.05)
        assert isinstance(adjusted, float)
        assert isinstance(fb_score, float)


class TestDecomposeScore:
    """decompose_score 함수 단위 테스트."""

    def test_decompose_returns_four_factors(self):
        """4개 요인 반환."""
        result = decompose_score(0.5, 0.5, 0.5, 0.5)
        assert len(result) == 4

    def test_decompose_factor_names(self):
        """요인 이름이 올바르게 반환되어야 한다."""
        result = decompose_score(0.5, 0.3, 0.7, 0.2)
        names = [item["factor"] for item in result]
        assert names == ["sentiment", "volume", "momentum", "anomaly"]

    def test_decompose_sum_equals_base_score(self):
        """기여도 합계 ≈ calculate_stock_score 결과."""
        s, v, m, a = 0.6, 0.4, 0.8, 0.3
        expected_total = calculate_stock_score(s, v, m, a)
        factors = decompose_score(s, v, m, a)
        contribution_sum = sum(f["contribution"] for f in factors)
        assert contribution_sum == pytest.approx(expected_total, abs=1e-9)

    def test_decompose_zero_inputs(self):
        """모든 입력이 0.0이면 기여도도 모두 0."""
        result = decompose_score(0.0, 0.0, 0.0, 0.0)
        for item in result:
            assert item["contribution"] == pytest.approx(0.0)

    def test_decompose_contribution_equals_weight_times_score(self):
        """기여도 = 가중치 × 요인 점수."""
        result = decompose_score(0.7, 0.5, 0.6, 0.4)
        for item in result:
            expected = item["weight"] * item["factor_score"]
            assert item["contribution"] == pytest.approx(expected, abs=1e-9)

    def test_decompose_weights_sum_to_one(self):
        """4요인 가중치 합 = 1.0."""
        result = decompose_score(0.5, 0.5, 0.5, 0.5)
        weight_sum = sum(f["weight"] for f in result)
        assert weight_sum == pytest.approx(1.0, abs=1e-9)
