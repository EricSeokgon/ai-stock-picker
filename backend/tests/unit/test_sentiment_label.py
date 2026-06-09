# sentiment_label.py 단위 테스트 — 경계값 및 엣지케이스 검증
import pytest

from stock_picker.analysis.sentiment_label import score_to_label


class TestScoreToLabel:
    """score_to_label 함수 단위 테스트"""

    def test_none_input_returns_none(self):
        """None 입력 시 None 반환"""
        assert score_to_label(None) is None

    # ── 매우긍정 경계 ──────────────────────────────────────────────────────────
    def test_score_exactly_0_6_is_매우긍정(self):
        """0.6 이상은 매우긍정"""
        assert score_to_label(0.6) == "매우긍정"

    def test_score_above_0_6_is_매우긍정(self):
        """0.6 초과도 매우긍정"""
        assert score_to_label(1.0) == "매우긍정"

    def test_score_0_61_is_매우긍정(self):
        """0.61 (0.6 초과)도 매우긍정"""
        assert score_to_label(0.61) == "매우긍정"

    # ── 긍정 경계 ──────────────────────────────────────────────────────────────
    def test_score_0_59_is_긍정(self):
        """0.59 (0.6 미만, 0.2 이상)는 긍정"""
        assert score_to_label(0.59) == "긍정"

    def test_score_exactly_0_2_is_긍정(self):
        """0.2 이상은 긍정"""
        assert score_to_label(0.2) == "긍정"

    def test_score_0_4_is_긍정(self):
        """0.4 (0.2~0.6 사이)는 긍정"""
        assert score_to_label(0.4) == "긍정"

    # ── 중립 경계 ──────────────────────────────────────────────────────────────
    def test_score_0_19_is_중립(self):
        """0.19 (0.2 미만, -0.2 초과)는 중립"""
        assert score_to_label(0.19) == "중립"

    def test_score_0_is_중립(self):
        """0.0은 중립"""
        assert score_to_label(0.0) == "중립"

    def test_score_minus_0_19_is_중립(self):
        """-0.19 (-0.2 초과)는 중립"""
        assert score_to_label(-0.19) == "중립"

    def test_score_just_above_minus_0_2_is_중립(self):
        """-0.2 경계: -0.2는 부정 (-0.2 초과 아님)"""
        # -0.2 는 score > -0.2 조건에 해당하지 않으므로 부정
        assert score_to_label(-0.2) == "부정"

    # ── 부정 경계 ──────────────────────────────────────────────────────────────
    def test_score_exactly_minus_0_2_is_부정(self):
        """-0.2는 부정 (score > -0.2 조건 불충족)"""
        assert score_to_label(-0.2) == "부정"

    def test_score_minus_0_4_is_부정(self):
        """-0.4 (-0.6 초과, -0.2 이하)는 부정"""
        assert score_to_label(-0.4) == "부정"

    def test_score_just_above_minus_0_6_is_부정(self):
        """-0.59 (-0.6 초과)는 부정"""
        assert score_to_label(-0.59) == "부정"

    # ── 매우부정 경계 ──────────────────────────────────────────────────────────
    def test_score_exactly_minus_0_6_is_매우부정(self):
        """-0.6은 매우부정 (score > -0.6 조건 불충족)"""
        assert score_to_label(-0.6) == "매우부정"

    def test_score_minus_1_is_매우부정(self):
        """-1.0은 매우부정"""
        assert score_to_label(-1.0) == "매우부정"

    def test_score_minus_0_61_is_매우부정(self):
        """-0.61 (-0.6 미만)은 매우부정"""
        assert score_to_label(-0.61) == "매우부정"

    # ── 반환 타입 검증 ──────────────────────────────────────────────────────────
    @pytest.mark.parametrize(
        "score,expected",
        [
            (1.0, "매우긍정"),
            (0.6, "매우긍정"),
            (0.5, "긍정"),
            (0.2, "긍정"),
            (0.1, "중립"),
            (0.0, "중립"),
            (-0.1, "중립"),
            (-0.2, "부정"),
            (-0.5, "부정"),
            (-0.6, "매우부정"),
            (-1.0, "매우부정"),
        ],
        ids=[
            "max",
            "threshold_매우긍정",
            "mid_긍정",
            "threshold_긍정",
            "small_positive",
            "zero",
            "small_negative",
            "threshold_부정",
            "mid_부정",
            "threshold_매우부정",
            "min",
        ],
    )
    def test_parametrized_labels(self, score: float, expected: str):
        """파라미터화된 경계값 테스트"""
        assert score_to_label(score) == expected
