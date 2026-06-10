# 스코어링 엔진 - 종목 점수 계산 및 순위화 순수 함수
# 외부 의존성 없음 (stdlib만 사용)

# 종목 점수 가중치 - 합계 1.0
WEIGHT_SENTIMENT = 0.40  # 뉴스 감성 분석 점수
WEIGHT_VOLUME = 0.20     # 거래량 이상 점수
WEIGHT_MOMENTUM = 0.25   # 가격 모멘텀 점수
WEIGHT_ANOMALY = 0.15    # 이상거래 탐지 점수


def calculate_stock_score(
    sentiment: float | None,
    volume: float | None,
    momentum: float | None,
    anomaly: float | None,
) -> float:
    """
    종목 종합 점수 계산.

    각 차원 점수에 가중치를 곱하여 가중 합산한다.
    None 입력은 0.0으로 처리한다.

    가중치:
        - sentiment (감성): 40%
        - volume (거래량): 20%
        - momentum (모멘텀): 25%
        - anomaly (이상거래): 15%

    Args:
        sentiment: 뉴스 감성 점수 (0.0~1.0), None 허용
        volume: 거래량 점수 (0.0~1.0), None 허용
        momentum: 모멘텀 점수 (0.0~1.0), None 허용
        anomaly: 이상거래 점수 (0.0~1.0), None 허용

    Returns:
        가중 합산 종합 점수 (0.0~1.0)
    """
    # None은 0.0으로 처리
    s = sentiment if sentiment is not None else 0.0
    v = volume if volume is not None else 0.0
    m = momentum if momentum is not None else 0.0
    a = anomaly if anomaly is not None else 0.0

    return (
        WEIGHT_SENTIMENT * s
        + WEIGHT_VOLUME * v
        + WEIGHT_MOMENTUM * m
        + WEIGHT_ANOMALY * a
    )


def decompose_score(
    sentiment: float,
    volume: float,
    momentum: float,
    anomaly: float,
) -> list[dict]:
    """4요인 가중 기여도 분해.

    calculate_stock_score와 동일한 가중치를 사용하되, 각 요인의
    기여도를 개별적으로 계산하여 반환한다.
    None 입력은 허용하지 않으며, 0.0으로 전달해야 한다.

    Args:
        sentiment: 감성 점수 (0.0~1.0)
        volume: 거래량 점수 (0.0~1.0)
        momentum: 모멘텀 점수 (0.0~1.0)
        anomaly: 이상거래 점수 (0.0~1.0)

    Returns:
        [{"factor", "weight", "factor_score", "contribution"}, ...] 형태 목록.
        기여도 합계 ≈ calculate_stock_score 결과 (부동소수점 오차 범위 내).
    """
    return [
        {
            "factor": "sentiment",
            "weight": WEIGHT_SENTIMENT,
            "factor_score": sentiment,
            "contribution": WEIGHT_SENTIMENT * sentiment,
        },
        {
            "factor": "volume",
            "weight": WEIGHT_VOLUME,
            "factor_score": volume,
            "contribution": WEIGHT_VOLUME * volume,
        },
        {
            "factor": "momentum",
            "weight": WEIGHT_MOMENTUM,
            "factor_score": momentum,
            "contribution": WEIGHT_MOMENTUM * momentum,
        },
        {
            "factor": "anomaly",
            "weight": WEIGHT_ANOMALY,
            "factor_score": anomaly,
            "contribution": WEIGHT_ANOMALY * anomaly,
        },
    ]


def rank_stocks(
    scores: dict[str, float],
    top_n: int = 10,
) -> list[tuple[str, float]]:
    """
    종목 점수를 내림차순으로 정렬하여 상위 N개 반환.

    Args:
        scores: {종목코드: 점수} 딕셔너리
        top_n: 반환할 최대 종목 수 (기본 10)

    Returns:
        [(종목코드, 점수), ...] 형태의 내림차순 정렬 리스트.
        종목 수가 top_n보다 적으면 전체 반환.
    """
    if not scores:
        return []

    # 점수 기준 내림차순 정렬
    sorted_stocks = sorted(scores.items(), key=lambda item: item[1], reverse=True)

    # 상위 N개 반환
    return sorted_stocks[:top_n]
