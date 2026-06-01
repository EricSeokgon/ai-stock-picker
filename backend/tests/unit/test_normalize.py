# 정규화 유틸리티 테스트 - 순수 함수 검증
from datetime import datetime, timezone, timedelta
import pytest


class TestMinmaxNormalize:
    """minmax_normalize 함수 테스트"""

    def test_empty_list_returns_empty_list(self):
        """빈 리스트 입력 시 빈 리스트를 반환해야 한다"""
        from stock_picker.scoring.normalize import minmax_normalize
        result = minmax_normalize([])
        assert result == []

    def test_single_value_returns_one(self):
        """단일 값 입력 시 1.0을 반환해야 한다"""
        from stock_picker.scoring.normalize import minmax_normalize
        result = minmax_normalize([5.0])
        assert result == [1.0]

    def test_all_same_values_returns_zeros(self):
        """모든 값이 동일하면 0.0을 반환해야 한다"""
        from stock_picker.scoring.normalize import minmax_normalize
        result = minmax_normalize([3.0, 3.0, 3.0])
        assert result == [0.0, 0.0, 0.0]

    def test_normal_case_returns_zero_to_one_range(self):
        """정상 케이스에서 0~1 범위로 정규화되어야 한다"""
        from stock_picker.scoring.normalize import minmax_normalize
        result = minmax_normalize([0.0, 5.0, 10.0])
        assert len(result) == 3
        assert result[0] == pytest.approx(0.0)
        assert result[1] == pytest.approx(0.5)
        assert result[2] == pytest.approx(1.0)

    def test_all_values_within_zero_to_one(self):
        """정규화 결과는 모두 0.0 이상 1.0 이하여야 한다"""
        from stock_picker.scoring.normalize import minmax_normalize
        values = [10.0, -5.0, 0.0, 3.0, 100.0, -100.0]
        result = minmax_normalize(values)
        assert all(0.0 <= v <= 1.0 for v in result)

    def test_max_value_becomes_one(self):
        """최댓값은 1.0으로 정규화되어야 한다"""
        from stock_picker.scoring.normalize import minmax_normalize
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = minmax_normalize(values)
        assert result[-1] == pytest.approx(1.0)

    def test_min_value_becomes_zero(self):
        """최솟값은 0.0으로 정규화되어야 한다"""
        from stock_picker.scoring.normalize import minmax_normalize
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = minmax_normalize(values)
        assert result[0] == pytest.approx(0.0)


class TestTimeDecayWeights:
    """time_decay_weights 함수 테스트"""

    def _make_timestamps(self, hours_ago_list: list[float]) -> list[datetime]:
        """현재 기준 N시간 전 타임스탬프 생성 헬퍼"""
        now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        return [
            now - timedelta(hours=h)
            for h in hours_ago_list
        ]

    def test_most_recent_gets_highest_weight(self):
        """가장 최근 타임스탬프가 가장 높은 가중치를 받아야 한다"""
        from stock_picker.scoring.normalize import time_decay_weights
        timestamps = self._make_timestamps([0.0, 12.0, 24.0])  # 방금, 12시간 전, 24시간 전
        weights = time_decay_weights(timestamps)
        assert weights[0] > weights[1] > weights[2]

    def test_weights_sum_to_approx_one(self):
        """가중치의 합은 1.0에 가까워야 한다"""
        from stock_picker.scoring.normalize import time_decay_weights
        timestamps = self._make_timestamps([0.0, 6.0, 12.0, 24.0])
        weights = time_decay_weights(timestamps)
        assert sum(weights) == pytest.approx(1.0, abs=1e-6)

    def test_all_same_timestamps_get_equal_weights(self):
        """모든 타임스탬프가 동일하면 균등 가중치를 받아야 한다"""
        from stock_picker.scoring.normalize import time_decay_weights
        now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        timestamps = [now, now, now, now]
        weights = time_decay_weights(timestamps)
        expected = 1.0 / len(timestamps)
        assert all(w == pytest.approx(expected) for w in weights)

    def test_empty_list_returns_empty_list(self):
        """빈 리스트 입력 시 빈 리스트를 반환해야 한다"""
        from stock_picker.scoring.normalize import time_decay_weights
        result = time_decay_weights([])
        assert result == []

    def test_single_timestamp_returns_one(self):
        """단일 타임스탬프 입력 시 [1.0]을 반환해야 한다"""
        from stock_picker.scoring.normalize import time_decay_weights
        now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = time_decay_weights([now])
        assert result == [pytest.approx(1.0)]

    def test_half_life_affects_decay_rate(self):
        """반감기 설정이 감쇠율에 영향을 미쳐야 한다"""
        from stock_picker.scoring.normalize import time_decay_weights
        # 24시간 전 타임스탬프
        timestamps = self._make_timestamps([0.0, 24.0])

        # 반감기 24시간: 24시간 전 기사는 최신 기사의 절반 weight
        weights_24h = time_decay_weights(timestamps, half_life_hours=24.0)
        # 반감기 12시간: 24시간 전 기사는 더 작은 weight
        weights_12h = time_decay_weights(timestamps, half_life_hours=12.0)

        # 긴 반감기일수록 오래된 기사의 상대적 weight가 높아야 함
        ratio_24h = weights_24h[1] / weights_24h[0]
        ratio_12h = weights_12h[1] / weights_12h[0]
        assert ratio_24h > ratio_12h

    def test_all_weights_positive(self):
        """모든 가중치는 양수여야 한다"""
        from stock_picker.scoring.normalize import time_decay_weights
        timestamps = self._make_timestamps([0.0, 24.0, 72.0, 168.0])
        weights = time_decay_weights(timestamps)
        assert all(w > 0 for w in weights)
