# 추천 근거 생성 - 종목 점수 기반 한국어 설명 생성 순수 함수
# 외부 의존성 없음 (stdlib만 사용)

# 각 차원의 한국어 설명 템플릿
_FACTOR_LABELS = {
    "sentiment": "뉴스 감성",
    "volume": "거래량",
    "momentum": "가격 모멘텀",
    "anomaly": "이상거래 탐지",
}

# 차원별 긍정 설명 키워드
_FACTOR_DESCRIPTIONS = {
    "sentiment": "긍정적 뉴스 감성 점수",
    "volume": "거래량 급증",
    "momentum": "상승 모멘텀",
    "anomaly": "이상 거래 신호 급등",
}


def generate_reasoning(
    krx_code: str,
    sentiment_score: float,
    volume_score: float,
    momentum_score: float,
    anomaly_score: float,
    top_article_summary: str | None = None,
) -> str:
    """
    종목 추천 근거를 한국어 문장으로 생성.

    가장 높은 기여 차원을 주요 근거로 명시하고,
    기사 요약이 있으면 추가 컨텍스트로 포함한다.

    Args:
        krx_code: KRX 종목코드 (예: "005930")
        sentiment_score: 뉴스 감성 점수 (0.0~1.0)
        volume_score: 거래량 점수 (0.0~1.0)
        momentum_score: 모멘텀 점수 (0.0~1.0)
        anomaly_score: 이상거래 점수 (0.0~1.0)
        top_article_summary: 주요 기사 요약 (선택)

    Returns:
        한국어 추천 근거 문장
    """
    # 각 차원의 가중치 적용 기여도 계산
    weighted_contributions = {
        "sentiment": sentiment_score * 0.40,
        "volume": volume_score * 0.20,
        "momentum": momentum_score * 0.25,
        "anomaly": anomaly_score * 0.15,
    }

    # 주요 기여 차원 식별
    dominant_factor = max(weighted_contributions, key=lambda k: weighted_contributions[k])

    # 차원별 점수 매핑
    scores = {
        "sentiment": sentiment_score,
        "volume": volume_score,
        "momentum": momentum_score,
        "anomaly": anomaly_score,
    }
    dominant_score = scores[dominant_factor]
    dominant_desc = _FACTOR_DESCRIPTIONS[dominant_factor]

    # 기본 추천 근거 문장 생성
    reasoning = (
        f"[{krx_code}] {dominant_desc}(점수 {dominant_score:.2f})이(가) "
        f"주요 추천 근거입니다."
    )

    # 보조 요인 추가 (상위 2개 차원)
    sorted_factors = sorted(
        weighted_contributions.items(),
        key=lambda x: x[1],
        reverse=True,
    )
    secondary_parts = []
    for factor, _ in sorted_factors[1:2]:  # 2위 차원만 추가
        score = scores[factor]
        if score > 0.3:  # 유의미한 점수인 경우만 포함
            secondary_parts.append(f"{_FACTOR_LABELS[factor]} {score:.2f}")

    if secondary_parts:
        reasoning += f" 추가 요인: {', '.join(secondary_parts)}."

    # 기사 요약 포함 (제공된 경우)
    if top_article_summary:
        reasoning += f" 관련 뉴스: {top_article_summary}"

    return reasoning
