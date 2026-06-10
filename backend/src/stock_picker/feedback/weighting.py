# 피드백 기반 점수 조정 순수 함수 (SPEC-STOCK-009 TASK-002, TASK-004)
# 외부 의존성 없음 (stdlib만 사용)

# 최대 조정 크기 (절대값 기준)
MAX_ADJ = 0.15

# 신뢰도 계산 기준 최소 투표 수
MIN_VOTES_FOR_CONFIDENCE = 5


# @MX:ANCHOR: [AUTO] 피드백 계수 계산 - 가중치 서비스와 테스트에서 참조
# @MX:REASON: weighting 서비스, 단위 테스트, 통합 테스트에서 3개 이상 호출


def calculate_feedback_coefficient(up: int, down: int) -> float:
    """신뢰도 가중 피드백 계수 계산.

    투표 수에 비례하는 신뢰도를 반영하여 피드백 계수를 계산한다.
    투표가 없으면 0.0을 반환하여 조정 없음을 보장한다.

    알고리즘:
        - net = (up - down) / (up + down)  → [-1.0, 1.0] 정규화
        - confidence = min((up + down) / MIN_VOTES_FOR_CONFIDENCE, 1.0)
        - coefficient = net * confidence * MAX_ADJ
        - [-MAX_ADJ, +MAX_ADJ] 범위로 클램프

    Args:
        up: 좋아요 투표 수 (0 이상)
        down: 싫어요 투표 수 (0 이상)

    Returns:
        피드백 계수 ([-MAX_ADJ, +MAX_ADJ] 범위)
    """
    total = up + down
    if total == 0:
        return 0.0

    # 정규화된 순 투표값 [-1.0, 1.0]
    net = (up - down) / total

    # 신뢰도: 투표 수가 MIN_VOTES_FOR_CONFIDENCE에 가까울수록 1.0에 근접
    confidence = min(total / MIN_VOTES_FOR_CONFIDENCE, 1.0)

    coefficient = net * confidence * MAX_ADJ

    # [-MAX_ADJ, +MAX_ADJ] 범위 클램프
    return max(-MAX_ADJ, min(MAX_ADJ, coefficient))


def apply_feedback_adjustment(
    base_score: float,
    feedback_coefficient: float,
) -> tuple[float, float]:
    """기본 점수에 피드백 계수를 적용하여 조정 점수 반환.

    Args:
        base_score: 피드백 조정 전 기본 점수 (0.0~1.0)
        feedback_coefficient: 피드백 계수 ([-MAX_ADJ, +MAX_ADJ])

    Returns:
        (adjusted_score, feedback_score) 튜플
            adjusted_score: 조정 후 점수 (0.0~1.0으로 클램프)
            feedback_score: 실제 적용된 델타 (adjusted_score - base_score)
    """
    adjusted_score = max(0.0, min(1.0, base_score + feedback_coefficient))
    # 클램프 후 실제 적용된 조정량 계산
    applied_delta = adjusted_score - base_score
    return adjusted_score, applied_delta
