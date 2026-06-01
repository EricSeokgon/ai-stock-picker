# 섹터 트렌드 집계 서비스 단위 테스트 (TASK-019)
import math
from datetime import datetime, timedelta, timezone

import pytest


def make_article_with_analysis(
    sector_tags: list[str],
    sentiment_score: float,
    hours_ago: float,
    article_id: int = 1,
    analysis_id: int = 1,
) -> dict:
    """테스트용 기사+분석 데이터 딕셔너리 생성 헬퍼."""
    now = datetime.now(tz=timezone.utc)
    published_at = now - timedelta(hours=hours_ago)
    return {
        "article_id": article_id,
        "analysis_id": analysis_id,
        "sector_tags": sector_tags,
        "sentiment_score": sentiment_score,
        "published_at": published_at,
    }


class TestComputeTrendScore:
    """compute_trend_score 순수 함수 테스트"""

    def test_all_max_inputs_return_one(self):
        """최대 입력값(감성=1.0, 볼륨=max, 감쇠=1.0)이면 1.0에 가까워야 한다"""
        from stock_picker.recommendation.trend_aggregator import compute_trend_score

        result = compute_trend_score(
            avg_sentiment=1.0,
            news_volume=10,
            time_decay_weight=1.0,
            max_volume=10,
        )
        # 0.70 * 1.0 + 0.30 * 1.0 = 1.0, 감쇠=1.0 → 1.0
        assert result == pytest.approx(1.0)

    def test_all_zero_inputs_return_zero(self):
        """sentiment=-1.0, volume=0 이면 결과는 0이어야 한다"""
        from stock_picker.recommendation.trend_aggregator import compute_trend_score

        result = compute_trend_score(
            avg_sentiment=-1.0,
            news_volume=0,
            time_decay_weight=1.0,
            max_volume=10,
        )
        # normalized_sentiment = 0, normalized_volume = 0 → 0
        assert result == pytest.approx(0.0)

    def test_time_decay_halves_score(self):
        """시간 감쇠 0.5 적용 시 스코어가 절반이 되어야 한다"""
        from stock_picker.recommendation.trend_aggregator import compute_trend_score

        full = compute_trend_score(
            avg_sentiment=0.0,  # normalized_sentiment = 0.5
            news_volume=10,
            time_decay_weight=1.0,
            max_volume=10,
        )
        half = compute_trend_score(
            avg_sentiment=0.0,
            news_volume=10,
            time_decay_weight=0.5,
            max_volume=10,
        )
        assert half == pytest.approx(full * 0.5)

    def test_score_range_is_0_to_1(self):
        """결과 스코어는 항상 0..1 범위여야 한다"""
        from stock_picker.recommendation.trend_aggregator import compute_trend_score

        result = compute_trend_score(
            avg_sentiment=1.0,
            news_volume=100,  # max_volume보다 크면 정규화해도 범위 초과 방지
            time_decay_weight=1.0,
            max_volume=10,
        )
        assert 0.0 <= result <= 1.0

    def test_max_volume_zero_does_not_raise(self):
        """max_volume=0일 때 ZeroDivisionError 없이 0을 반환해야 한다"""
        from stock_picker.recommendation.trend_aggregator import compute_trend_score

        result = compute_trend_score(
            avg_sentiment=0.5,
            news_volume=5,
            time_decay_weight=1.0,
            max_volume=0,
        )
        # normalized_volume = 0 (max_volume=0이면 0으로 처리)
        assert 0.0 <= result <= 1.0

    def test_neutral_sentiment_gives_half_base(self):
        """중립 감성(0.0)은 정규화 후 0.5가 되어야 한다"""
        from stock_picker.recommendation.trend_aggregator import compute_trend_score

        # volume=0이면 볼륨 기여 없음 → 0.70 * 0.5 = 0.35
        result = compute_trend_score(
            avg_sentiment=0.0,
            news_volume=0,
            time_decay_weight=1.0,
            max_volume=10,
        )
        assert result == pytest.approx(0.35)


class TestAggregateByArticles:
    """aggregate_by_articles 함수 테스트 (DB 미사용 버전)"""

    def test_empty_input_returns_empty(self):
        """빈 입력은 빈 딕셔너리를 반환해야 한다"""
        from stock_picker.recommendation.trend_aggregator import aggregate_by_articles

        result = aggregate_by_articles([])
        assert result == {}

    def test_24h_ago_article_weight_is_half(self):
        """24시간 전 기사의 시간 감쇠 가중치는 ~0.5여야 한다"""
        from stock_picker.recommendation.trend_aggregator import aggregate_by_articles

        articles = [
            make_article_with_analysis(
                sector_tags=["반도체"],
                sentiment_score=1.0,
                hours_ago=24.0,
            )
        ]
        result = aggregate_by_articles(articles)
        # 반도체 섹터 존재해야 함
        assert "반도체" in result
        # 시간 감쇠: exp(-ln2 * 24/24) = 0.5
        expected_decay = math.exp(-math.log(2) * 24 / 24)
        assert result["반도체"]["avg_decay_weight"] == pytest.approx(expected_decay, rel=1e-3)

    def test_recent_article_weight_near_one(self):
        """최근 기사(0시간 전)의 시간 감쇠 가중치는 ~1.0이어야 한다"""
        from stock_picker.recommendation.trend_aggregator import aggregate_by_articles

        articles = [
            make_article_with_analysis(
                sector_tags=["IT"],
                sentiment_score=0.8,
                hours_ago=0.0,
            )
        ]
        result = aggregate_by_articles(articles)
        assert "IT" in result
        # exp(0) = 1.0
        assert result["IT"]["avg_decay_weight"] == pytest.approx(1.0, rel=1e-3)

    def test_multiple_articles_same_sector_aggregated(self):
        """동일 섹터 복수 기사는 합산/평균으로 집계해야 한다"""
        from stock_picker.recommendation.trend_aggregator import aggregate_by_articles

        articles = [
            make_article_with_analysis(
                sector_tags=["반도체"],
                sentiment_score=0.8,
                hours_ago=1.0,
                article_id=1,
                analysis_id=1,
            ),
            make_article_with_analysis(
                sector_tags=["반도체"],
                sentiment_score=0.4,
                hours_ago=2.0,
                article_id=2,
                analysis_id=2,
            ),
        ]
        result = aggregate_by_articles(articles)
        assert "반도체" in result
        assert result["반도체"]["news_volume"] == 2

    def test_multi_sector_article_contributes_to_all(self):
        """복수 섹터 태그를 가진 기사는 모든 섹터에 기여해야 한다"""
        from stock_picker.recommendation.trend_aggregator import aggregate_by_articles

        articles = [
            make_article_with_analysis(
                sector_tags=["IT", "반도체"],
                sentiment_score=0.6,
                hours_ago=0.5,
            )
        ]
        result = aggregate_by_articles(articles)
        assert "IT" in result
        assert "반도체" in result

    def test_48h_ago_article_weight_is_quarter(self):
        """48시간 전 기사의 시간 감쇠 가중치는 ~0.25여야 한다"""
        from stock_picker.recommendation.trend_aggregator import aggregate_by_articles

        articles = [
            make_article_with_analysis(
                sector_tags=["금융"],
                sentiment_score=0.5,
                hours_ago=48.0,
            )
        ]
        result = aggregate_by_articles(articles)
        expected_decay = math.exp(-math.log(2) * 48 / 24)
        assert result["금융"]["avg_decay_weight"] == pytest.approx(expected_decay, rel=1e-3)

    def test_trend_score_is_in_0_to_1_range(self):
        """집계 결과의 trend_score는 0..1 범위여야 한다"""
        from stock_picker.recommendation.trend_aggregator import aggregate_by_articles

        articles = [
            make_article_with_analysis(
                sector_tags=["자동차"],
                sentiment_score=0.9,
                hours_ago=0.0,
            )
        ]
        result = aggregate_by_articles(articles)
        score = result["자동차"]["trend_score"]
        assert 0.0 <= score <= 1.0
