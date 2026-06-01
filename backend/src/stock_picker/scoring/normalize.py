# 점수 정규화 유틸리티 - 외부 의존성 없는 순수 함수
import math
from datetime import datetime


def minmax_normalize(values: list[float]) -> list[float]:
    """
    Min-Max 정규화: 입력값을 0.0~1.0 범위로 변환.

    Args:
        values: 정규화할 실수 리스트

    Returns:
        0.0~1.0 범위로 정규화된 리스트.
        빈 리스트 입력 시 빈 리스트 반환.
        모든 값이 동일하면 0.0 리스트 반환.
        단일 값이면 [1.0] 반환.
    """
    if not values:
        return []

    if len(values) == 1:
        return [1.0]

    min_val = min(values)
    max_val = max(values)

    # 모든 값이 동일한 경우: 변동성 없음 → 0.0 반환
    if max_val == min_val:
        return [0.0] * len(values)

    # Min-Max 정규화 공식: (x - min) / (max - min)
    return [(v - min_val) / (max_val - min_val) for v in values]


def time_decay_weights(
    timestamps: list[datetime],
    half_life_hours: float = 24.0,
) -> list[float]:
    """
    시간 감쇠 가중치 계산: 최신 항목에 더 높은 가중치 부여.

    지수 감쇠 공식: weight = 2^(-elapsed_hours / half_life_hours)
    이후 합이 1.0이 되도록 정규화.

    Args:
        timestamps: 타임스탬프 리스트 (timezone-aware 권장)
        half_life_hours: 감쇠 반감기 시간 (기본 24시간)

    Returns:
        합이 1.0인 정규화된 가중치 리스트.
        빈 리스트 입력 시 빈 리스트 반환.
        모든 타임스탬프가 동일하면 균등 가중치 반환.
    """
    if not timestamps:
        return []

    if len(timestamps) == 1:
        return [1.0]

    # 가장 최신 타임스탬프 기준으로 경과 시간 계산
    max_ts = max(timestamps)

    # 각 타임스탬프의 경과 시간(시간 단위) 계산
    elapsed_hours = []
    for ts in timestamps:
        # timezone-naive와 timezone-aware 혼합 처리
        if ts.tzinfo is None and max_ts.tzinfo is not None:
            elapsed = (max_ts.replace(tzinfo=None) - ts).total_seconds() / 3600
        elif ts.tzinfo is not None and max_ts.tzinfo is None:
            elapsed = (max_ts - ts.replace(tzinfo=None)).total_seconds() / 3600
        else:
            elapsed = (max_ts - ts).total_seconds() / 3600
        elapsed_hours.append(max(0.0, elapsed))

    # 지수 감쇠 가중치: w_i = 2^(-t_i / half_life)
    raw_weights = [
        math.pow(2.0, -elapsed / half_life_hours)
        for elapsed in elapsed_hours
    ]

    # 합이 1.0이 되도록 정규화
    total = sum(raw_weights)
    if total == 0:
        # 모두 0인 엣지 케이스 (이론상 발생 불가)
        return [1.0 / len(timestamps)] * len(timestamps)

    return [w / total for w in raw_weights]
