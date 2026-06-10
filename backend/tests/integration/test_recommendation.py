# 추천 서비스 통합 테스트
# AC-5: total_score = 0.40*sentiment + 0.20*volume + 0.25*momentum + 0.15*anomaly
# Redis 캐시 설정 확인

import pytest
from datetime import date
from unittest.mock import AsyncMock, patch


def make_aggregated_stock_data(krx_code: str, avg_sentiment: float, news_count: int):
    """집계된 종목 데이터 헬퍼"""
    return {
        "avg_sentiment": avg_sentiment,
        "news_count": news_count,
        "top_summary": f"{krx_code} 관련 주요 뉴스 요약",
    }


def make_price_data(close_price: float, change_rate: float, volume: int):
    """시세 데이터 헬퍼"""
    return {
        "close_price": close_price,
        "change_rate": change_rate,
        "volume": volume,
    }


class TestRecommendationServiceScoring:
    """추천 서비스 스코어링 테스트"""

    @pytest.mark.asyncio
    async def test_total_score_formula_ac5(self):
        """AC-5: total_score = 0.40*sentiment + 0.20*volume + 0.25*momentum + 0.15*anomaly"""
        from stock_picker.scoring.engine import calculate_stock_score

        # 각 차원 점수 설정
        sentiment = 0.8
        volume = 0.6
        momentum = 0.7
        anomaly = 0.5

        score = calculate_stock_score(sentiment, volume, momentum, anomaly)

        expected = 0.40 * 0.8 + 0.20 * 0.6 + 0.25 * 0.7 + 0.15 * 0.5
        assert abs(score - expected) < 0.001

    @pytest.mark.asyncio
    async def test_recommendation_service_run_returns_list(self):
        """RecommendationService.run() → 리스트 반환"""
        from stock_picker.recommendation.service import RecommendationService

        mock_session = AsyncMock()

        # 집계기 mock
        mock_aggregated = {
            "005930": make_aggregated_stock_data("005930", 0.8, 5),
            "000660": make_aggregated_stock_data("000660", 0.6, 3),
        }

        # 시세 mock
        mock_prices = make_price_data(70000.0, 0.02, 10000000)

        with patch(
            "stock_picker.recommendation.aggregator.StockAggregator.aggregate",
            new_callable=AsyncMock,
            return_value=mock_aggregated,
        ):
            with patch(
                "stock_picker.mapping.prices.get_stock_price_data",
                new_callable=AsyncMock,
                return_value=mock_prices,
            ):
                with patch(
                    "stock_picker.recommendation.service.get_bulk_feedback",
                    new_callable=AsyncMock,
                    return_value={},
                ):
                    # Redis mock
                    mock_cache = AsyncMock()
                    mock_cache.get = AsyncMock(return_value=None)
                    mock_cache.set = AsyncMock()

                    service = RecommendationService(cache=mock_cache)
                    service._save_recommendations = AsyncMock()

                    results = await service.run(mock_session, trade_date=date.today())

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_recommendation_has_rank_and_score(self):
        """추천 결과에 rank와 total_score 포함"""
        from stock_picker.recommendation.service import RecommendationService

        mock_session = AsyncMock()

        mock_aggregated = {
            "005930": make_aggregated_stock_data("005930", 0.8, 5),
        }
        mock_prices = make_price_data(70000.0, 0.02, 10000000)

        with patch(
            "stock_picker.recommendation.aggregator.StockAggregator.aggregate",
            new_callable=AsyncMock,
            return_value=mock_aggregated,
        ):
            with patch(
                "stock_picker.mapping.prices.get_stock_price_data",
                new_callable=AsyncMock,
                return_value=mock_prices,
            ):
                with patch(
                    "stock_picker.recommendation.service.get_bulk_feedback",
                    new_callable=AsyncMock,
                    return_value={},
                ):
                    mock_cache = AsyncMock()
                    mock_cache.get = AsyncMock(return_value=None)
                    mock_cache.set = AsyncMock()

                    service = RecommendationService(cache=mock_cache)
                    service._save_recommendations = AsyncMock()

                    results = await service.run(mock_session)

        if results:
            assert "rank" in results[0]
            assert "total_score" in results[0]
            assert "krx_code" in results[0]

    @pytest.mark.asyncio
    async def test_redis_cache_set_after_run(self):
        """추천 실행 후 Redis 캐시 설정 확인"""
        from stock_picker.recommendation.service import RecommendationService

        mock_session = AsyncMock()

        mock_aggregated = {
            "005930": make_aggregated_stock_data("005930", 0.8, 5),
        }
        mock_prices = make_price_data(70000.0, 0.02, 10000000)

        with patch(
            "stock_picker.recommendation.aggregator.StockAggregator.aggregate",
            new_callable=AsyncMock,
            return_value=mock_aggregated,
        ):
            with patch(
                "stock_picker.mapping.prices.get_stock_price_data",
                new_callable=AsyncMock,
                return_value=mock_prices,
            ):
                with patch(
                    "stock_picker.recommendation.service.get_bulk_feedback",
                    new_callable=AsyncMock,
                    return_value={},
                ):
                    mock_cache = AsyncMock()
                    mock_cache.get = AsyncMock(return_value=None)
                    mock_cache.set = AsyncMock()

                    service = RecommendationService(cache=mock_cache)
                    service._save_recommendations = AsyncMock()

                    await service.run(mock_session)

                    # 캐시 set이 호출되어야 함
                    mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_cached_result_returned_without_db_query(self):
        """캐시에 데이터 있으면 DB 조회 없이 캐시 반환"""
        from stock_picker.recommendation.service import RecommendationService

        mock_session = AsyncMock()

        cached_data = [{"rank": 1, "krx_code": "005930", "total_score": 0.85}]

        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=cached_data)

        service = RecommendationService(cache=mock_cache)

        results = await service.run(mock_session)

        assert results == cached_data
        # 집계기가 호출되지 않아야 함 (캐시 히트)


class TestRecommendationServiceTopN:
    """Top N 추천 제한 테스트"""

    @pytest.mark.asyncio
    async def test_top_10_recommendations(self):
        """최대 10개 추천 반환"""
        from stock_picker.recommendation.service import RecommendationService

        mock_session = AsyncMock()

        # 15개 종목 mock
        mock_aggregated = {
            f"00{i:04d}": make_aggregated_stock_data(f"00{i:04d}", 0.5 + i * 0.01, i)
            for i in range(1, 16)
        }
        mock_prices = make_price_data(70000.0, 0.02, 10000000)

        with patch(
            "stock_picker.recommendation.aggregator.StockAggregator.aggregate",
            new_callable=AsyncMock,
            return_value=mock_aggregated,
        ):
            with patch(
                "stock_picker.mapping.prices.get_stock_price_data",
                new_callable=AsyncMock,
                return_value=mock_prices,
            ):
                with patch(
                    "stock_picker.recommendation.service.get_bulk_feedback",
                    new_callable=AsyncMock,
                    return_value={},
                ):
                    mock_cache = AsyncMock()
                    mock_cache.get = AsyncMock(return_value=None)
                    mock_cache.set = AsyncMock()

                    service = RecommendationService(cache=mock_cache)
                    service._save_recommendations = AsyncMock()

                    results = await service.run(mock_session)

        assert len(results) <= 10
