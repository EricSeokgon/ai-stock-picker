# 감성 점수 → 5단계 라벨 변환 유틸리티
# TASK-008: score_to_label 함수 — analysis worker에서 AnalysisResult.sentiment_label에 저장
from __future__ import annotations

# 5단계 라벨 경계값 (오름차순)
# @MX:NOTE: [AUTO] 임계값은 -1.0~1.0 스케일 기준으로 정규화된 감성 점수에 적용
THRESHOLDS: dict[str, float] = {
    "매우긍정": 0.6,
    "긍정": 0.2,
    "중립": -0.2,
    "부정": -0.6,
}


def score_to_label(score: float | None) -> str | None:
    """감성 점수를 5단계 라벨로 변환.

    Args:
        score: 감성 점수 (-1.0 ~ 1.0). None이면 None 반환.

    Returns:
        "매우긍정" | "긍정" | "중립" | "부정" | "매우부정" | None
    """
    if score is None:
        return None

    if score >= 0.6:
        return "매우긍정"
    if score >= 0.2:
        return "긍정"
    if score > -0.2:
        return "중립"
    if score > -0.6:
        return "부정"
    return "매우부정"
