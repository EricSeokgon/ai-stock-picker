# 섹터 트렌드 집계 서비스 (REQ-TREND-001~003)
# 기사 분석 결과를 섹터별로 집계하여 트렌드 스코어를 산출한다.
import math
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import structlog

log = structlog.get_logger()

# 시간 감쇠 반감기: 24시간
# 공식: weight = exp(-ln(2) * hours_elapsed / 24)
_HALF_LIFE_HOURS = 24.0

# 트렌드 스코어 가중치 (감성 70%, 볼륨 30%)
_SENTIMENT_WEIGHT = 0.70
_VOLUME_WEIGHT = 0.30


def _compute_time_decay(published_at: datetime) -> float:
    """기사 발행 시각 기준 시간 감쇠 가중치 계산.

    Args:
        published_at: 기사 발행 일시 (timezone-aware)

    Returns:
        시간 감쇠 가중치 0.0~1.0
    """
    now = datetime.now(tz=timezone.utc)
    # timezone-naive인 경우 UTC로 간주
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    hours_elapsed = (now - published_at).total_seconds() / 3600.0
    hours_elapsed = max(0.0, hours_elapsed)
    return math.exp(-math.log(2) * hours_elapsed / _HALF_LIFE_HOURS)


def compute_trend_score(
    avg_sentiment: float,
    news_volume: int,
    time_decay_weight: float,
    max_volume: int,
) -> float:
    """섹터 트렌드 스코어 산출.

    sentiment를 0~1로 변환 후 볼륨 정규화값과 시간 감쇠 가중치 적용.

    Args:
        avg_sentiment: 평균 감성 점수 (-1.0 ~ 1.0)
        news_volume: 해당 섹터 뉴스 수
        time_decay_weight: 시간 감쇠 가중치 (0.0 ~ 1.0)
        max_volume: 볼륨 정규화 기준 최대값

    Returns:
        트렌드 스코어 0.0~1.0
    """
    # sentiment -1..1 → 0..1 변환
    normalized_sentiment = (avg_sentiment + 1.0) / 2.0
    # 볼륨 정규화 (max_volume=0이면 0으로 처리)
    normalized_volume = news_volume / max_volume if max_volume > 0 else 0.0
    # 볼륨이 max를 초과하면 클리핑
    normalized_volume = min(1.0, normalized_volume)

    # 가중 합산 후 시간 감쇠 적용
    raw = _SENTIMENT_WEIGHT * normalized_sentiment + _VOLUME_WEIGHT * normalized_volume
    return min(1.0, max(0.0, raw * time_decay_weight))


def aggregate_by_articles(
    articles: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """기사 분석 결과 딕셔너리 목록에서 섹터별 트렌드 데이터를 집계.

    # @MX:ANCHOR: [AUTO] 섹터 트렌드 집계 핵심 로직 - trend_aggregator의 주요 공개 함수
    # @MX:REASON: 스케줄러 파이프라인과 테스트에서 직접 호출하는 공개 집계 인터페이스

    Args:
        articles: 기사+분석 정보 딕셔너리 목록
            각 항목: {article_id, analysis_id, sector_tags, sentiment_score, published_at}

    Returns:
        섹터명 → 집계 데이터 딕셔너리
        각 값: {news_volume, avg_sentiment, avg_decay_weight, trend_score}
    """
    if not articles:
        return {}

    # 섹터별 데이터 누적
    sector_data: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "sentiment_sum": 0.0,
            "decay_weight_sum": 0.0,
            "news_volume": 0,
        }
    )

    for article in articles:
        published_at: datetime = article["published_at"]
        sentiment_score: float = float(article["sentiment_score"])
        sector_tags: list[str] = article.get("sector_tags", [])

        decay_weight = _compute_time_decay(published_at)

        # 하나의 기사가 복수 섹터에 기여
        for sector in sector_tags:
            sector_data[sector]["news_volume"] += 1
            sector_data[sector]["sentiment_sum"] += sentiment_score
            sector_data[sector]["decay_weight_sum"] += decay_weight

    if not sector_data:
        return {}

    # 전체 최대 볼륨 (정규화 기준)
    max_volume = max(d["news_volume"] for d in sector_data.values())

    result: dict[str, dict[str, Any]] = {}
    for sector, data in sector_data.items():
        vol = data["news_volume"]
        avg_sentiment = data["sentiment_sum"] / vol if vol > 0 else 0.0
        avg_decay = data["decay_weight_sum"] / vol if vol > 0 else 0.0

        trend_score = compute_trend_score(
            avg_sentiment=avg_sentiment,
            news_volume=vol,
            time_decay_weight=avg_decay,
            max_volume=max_volume,
        )

        result[sector] = {
            "news_volume": vol,
            "avg_sentiment": avg_sentiment,
            "avg_decay_weight": avg_decay,
            "trend_score": trend_score,
        }

    log.debug("섹터 트렌드 집계 완료", sector_count=len(result))
    return result
