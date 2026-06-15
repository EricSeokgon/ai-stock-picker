# SPEC-STOCK-021: 뉴스피드·AI 시장 템포 단위 테스트
# REQ-NEWS-SENT-*, REQ-NEWS-FEED-*, REQ-NEWS-FETCH-*, REQ-NEWS-CACHE-*
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import json
import pytest


# ---------------------------------------------------------------------------
# M1 — 시장 감성 집계: get_market_sentiment
# ---------------------------------------------------------------------------

class TestGetMarketSentimentEmpty:
    """REQ-NEWS-SENT-004: 대상 기사 0건이면 avg_score=None, label=None 반환"""

    @pytest.mark.asyncio
    async def test_empty_returns_none_score_and_none_label(self):
        """분석 기사 0건 → avg_score None, label None, total 0"""
        from stock_picker.news.sentiment_service import get_market_sentiment

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()

        db = AsyncMock()
        # DB 집계 결과: 0건
        mock_row = MagicMock()
        mock_row.avg_score = None
        mock_row.positive = 0
        mock_row.negative = 0
        mock_row.neutral = 0
        mock_row.total = 0
        db.execute = AsyncMock(return_value=MagicMock(fetchone=MagicMock(return_value=mock_row)))

        result = await get_market_sentiment(redis=redis, db=db)

        assert result.avg_score is None
        assert result.label is None
        assert result.total == 0
        assert result.positive == 0
        assert result.negative == 0
        assert result.neutral == 0


class TestGetMarketSentimentPositive:
    """REQ-NEWS-SENT-001/003: 양성 기사 다수면 avg_score > 0, label '긍정' 계열"""

    @pytest.mark.asyncio
    async def test_positive_articles_return_positive_label(self):
        """평균 점수 0.5 → label '긍정' 또는 '매우긍정'"""
        from stock_picker.news.sentiment_service import get_market_sentiment

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()

        db = AsyncMock()
        mock_row = MagicMock()
        mock_row.avg_score = 0.5
        mock_row.positive = 8
        mock_row.negative = 1
        mock_row.neutral = 1
        mock_row.total = 10
        db.execute = AsyncMock(return_value=MagicMock(fetchone=MagicMock(return_value=mock_row)))

        result = await get_market_sentiment(redis=redis, db=db)

        assert result.avg_score is not None
        assert result.avg_score > 0
        assert result.label in ("긍정", "매우긍정")
        assert result.total == 10

    @pytest.mark.asyncio
    async def test_negative_articles_return_negative_label(self):
        """평균 점수 -0.4 → label '부정' 계열"""
        from stock_picker.news.sentiment_service import get_market_sentiment

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()

        db = AsyncMock()
        mock_row = MagicMock()
        mock_row.avg_score = -0.4
        mock_row.positive = 1
        mock_row.negative = 7
        mock_row.neutral = 2
        mock_row.total = 10
        db.execute = AsyncMock(return_value=MagicMock(fetchone=MagicMock(return_value=mock_row)))

        result = await get_market_sentiment(redis=redis, db=db)

        assert result.avg_score is not None
        assert result.avg_score < 0
        assert result.label in ("부정", "매우부정")


class TestGetMarketSentimentCacheHit:
    """REQ-NEWS-CACHE-002: Redis 캐시 히트 시 DB 호출 없이 캐시에서 반환"""

    @pytest.mark.asyncio
    async def test_cache_hit_skips_db(self):
        """Redis 캐시 히트 → DB execute 호출 없음"""
        from stock_picker.news.sentiment_service import get_market_sentiment

        cached_data = json.dumps({
            "avg_score": 0.3,
            "label": "긍정",
            "positive": 5,
            "negative": 2,
            "neutral": 3,
            "total": 10,
            "as_of": datetime.now(timezone.utc).isoformat(),
        })

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=cached_data)

        db = AsyncMock()
        db.execute = AsyncMock()

        result = await get_market_sentiment(redis=redis, db=db)

        assert result.avg_score == 0.3
        assert result.label == "긍정"
        db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss_sets_cache(self):
        """캐시 미스 → DB 조회 후 Redis setex 호출"""
        from stock_picker.news.sentiment_service import get_market_sentiment

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()

        db = AsyncMock()
        mock_row = MagicMock()
        mock_row.avg_score = 0.2
        mock_row.positive = 4
        mock_row.negative = 3
        mock_row.neutral = 3
        mock_row.total = 10
        db.execute = AsyncMock(return_value=MagicMock(fetchone=MagicMock(return_value=mock_row)))

        await get_market_sentiment(redis=redis, db=db)

        redis.setex.assert_called_once()
        call_args = redis.setex.call_args
        # 첫 번째 인수가 캐시 키
        assert "market_sentiment" in call_args[0][0]
        # 두 번째 인수가 TTL 1800
        assert call_args[0][1] == 1800

    @pytest.mark.asyncio
    async def test_redis_unavailable_falls_back_to_db(self):
        """REQ-NEWS-CACHE-003: Redis 장애 → DB 직접 조회, 예외 미발생"""
        from stock_picker.news.sentiment_service import get_market_sentiment

        redis = AsyncMock()
        redis.get = AsyncMock(side_effect=ConnectionError("Redis unavailable"))
        redis.setex = AsyncMock(side_effect=ConnectionError("Redis unavailable"))

        db = AsyncMock()
        mock_row = MagicMock()
        mock_row.avg_score = 0.1
        mock_row.positive = 3
        mock_row.negative = 3
        mock_row.neutral = 4
        mock_row.total = 10
        db.execute = AsyncMock(return_value=MagicMock(fetchone=MagicMock(return_value=mock_row)))

        # 예외 없이 완료되어야 함
        result = await get_market_sentiment(redis=redis, db=db)
        assert result.total == 10


# ---------------------------------------------------------------------------
# M2 — 종목별 뉴스 필터: get_news_by_stock
# ---------------------------------------------------------------------------

class TestGetNewsByStock:
    """REQ-NEWS-FEED-002: krx_code 필터 시 해당 종목 기사만 반환"""

    @pytest.mark.asyncio
    async def test_returns_articles_for_krx_code(self):
        """krx_code='005930' 조회 → 해당 종목 기사 반환"""
        from stock_picker.news.sentiment_service import get_news_by_stock

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()

        db = AsyncMock()
        # DB 조회 결과 mock
        mock_article = MagicMock()
        mock_article.id = 1
        mock_article.title = "삼성전자 실적 발표"
        mock_article.source = "한국경제"
        mock_article.published_at = datetime.now(timezone.utc)
        mock_article.url = "http://example.com/1"
        mock_article.analysis_results = [MagicMock(
            sentiment="positive",
            sentiment_score=0.7,
            sentiment_label="긍정",
            summary="삼성전자 호실적",
        )]

        db.execute = AsyncMock(return_value=MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_article])))
        ))

        results = await get_news_by_stock(krx_code="005930", limit=10, redis=redis, db=db)

        assert len(results) == 1
        assert results[0].title == "삼성전자 실적 발표"

    @pytest.mark.asyncio
    async def test_empty_result_for_unknown_stock(self):
        """존재하지 않는 종목 → 빈 리스트 반환 (REQ-NEWS-FEED-005)"""
        from stock_picker.news.sentiment_service import get_news_by_stock

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()

        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        ))

        results = await get_news_by_stock(krx_code="999999", limit=10, redis=redis, db=db)

        assert results == []

    @pytest.mark.asyncio
    async def test_cache_hit_for_krx_code(self):
        """REQ-NEWS-CACHE-001: news:{krx_code} 캐시 히트 → DB 미호출"""
        from stock_picker.news.sentiment_service import get_news_by_stock

        cached = json.dumps([{
            "id": 1,
            "title": "캐시 기사",
            "source": "소스",
            "published_at": datetime.now(timezone.utc).isoformat(),
            "url": "http://example.com/1",
            "sentiment": "positive",
            "sentiment_score": 0.5,
            "sentiment_label": "긍정",
            "ai_summary": "요약",
        }])

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=cached)

        db = AsyncMock()
        db.execute = AsyncMock()

        results = await get_news_by_stock(krx_code="005930", limit=10, redis=redis, db=db)

        assert len(results) == 1
        db.execute.assert_not_called()


# ---------------------------------------------------------------------------
# M3 — 수동 트리거: trigger_news_fetch
# ---------------------------------------------------------------------------

class TestTriggerNewsFetch:
    """REQ-NEWS-FETCH-001/002/003: 수동 트리거 동작"""

    @pytest.mark.asyncio
    async def test_trigger_returns_collected_and_analyzed_counts(self):
        """수집/분석 성공 → collected/analyzed 건수 반환"""
        from stock_picker.news.sentiment_service import trigger_news_fetch

        db = AsyncMock()
        redis = AsyncMock()

        with patch("stock_picker.news.sentiment_service.CollectorService") as MockCollector, \
             patch("stock_picker.news.sentiment_service.AnalysisWorker") as MockWorker:

            mock_svc = MockCollector.return_value
            mock_svc.collect_all = AsyncMock(return_value={"hankyung": 3, "mk": 2, "naver": 1})

            mock_worker = MockWorker.return_value
            mock_worker.run = AsyncMock(return_value={"analyzed": 5, "failed": 0})

            result = await trigger_news_fetch(db=db, redis=redis)

        assert result["collected"] >= 0
        assert result["analyzed"] >= 0

    @pytest.mark.asyncio
    async def test_trigger_graceful_on_collector_failure(self):
        """REQ-NEWS-FETCH-003: 수집 실패 시 500 없이 partial 결과 반환"""
        from stock_picker.news.sentiment_service import trigger_news_fetch

        db = AsyncMock()
        redis = AsyncMock()

        with patch("stock_picker.news.sentiment_service.CollectorService") as MockCollector, \
             patch("stock_picker.news.sentiment_service.AnalysisWorker") as MockWorker:

            mock_svc = MockCollector.return_value
            mock_svc.collect_all = AsyncMock(side_effect=Exception("수집 실패"))

            mock_worker = MockWorker.return_value
            mock_worker.run = AsyncMock(return_value={"analyzed": 0, "failed": 0})

            # 예외 없이 완료 되어야 함
            result = await trigger_news_fetch(db=db, redis=redis)

        assert "collected" in result
        assert "analyzed" in result


# ---------------------------------------------------------------------------
# 스키마 검증
# ---------------------------------------------------------------------------

class TestMarketSentimentResponseSchema:
    """MarketSentimentResponse Pydantic 스키마 검증"""

    def test_schema_with_all_fields(self):
        """모든 필드 정상 직렬화"""
        from stock_picker.api.schemas import MarketSentimentResponse

        now = datetime.now(timezone.utc)
        resp = MarketSentimentResponse(
            avg_score=0.3,
            label="긍정",
            positive=5,
            negative=2,
            neutral=3,
            total=10,
            as_of=now,
        )
        assert resp.avg_score == 0.3
        assert resp.label == "긍정"
        assert resp.total == 10

    def test_schema_with_none_score(self):
        """avg_score None, label None 허용"""
        from stock_picker.api.schemas import MarketSentimentResponse

        resp = MarketSentimentResponse(
            avg_score=None,
            label=None,
            positive=0,
            negative=0,
            neutral=0,
            total=0,
            as_of=datetime.now(timezone.utc),
        )
        assert resp.avg_score is None
        assert resp.label is None


class TestNewsFetchResultSchema:
    """NewsFetchResult Pydantic 스키마 검증"""

    def test_schema_fields(self):
        """collected/analyzed 필드 확인"""
        from stock_picker.api.schemas import NewsFetchResult

        result = NewsFetchResult(collected=5, analyzed=3)
        assert result.collected == 5
        assert result.analyzed == 3
