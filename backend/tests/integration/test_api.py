# FastAPI 엔드포인트 통합 테스트
# TestClient 사용, DB와 Redis는 mock
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# 헬퍼: 샘플 추천 데이터
# ---------------------------------------------------------------------------

def _sample_recommendations() -> list[dict]:
    """테스트용 추천 리스트 (10개)"""
    return [
        {
            "rank": i,
            "krx_code": f"00{i:04d}",
            "total_score": round(1.0 - i * 0.05, 3),
            "sentiment_score": 0.8,
            "volume_score": 0.7,
            "momentum_score": 0.6,
            "anomaly_score": 0.5,
            "reasoning": f"종목 {i} 분석 결과",
            "trade_date": "2026-06-01",
        }
        for i in range(1, 11)
    ]


def _make_client() -> TestClient:
    """앱 임포트 후 TestClient 반환"""
    from stock_picker.api.main import create_app

    app = create_app()
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    def test_health_returns_ok(self) -> None:
        """헬스 체크 엔드포인트가 status:ok를 반환해야 한다 (DB·Redis mock)."""
        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=False)
        mock_conn.execute = AsyncMock()
        mock_engine = MagicMock()
        mock_engine.connect = MagicMock(return_value=mock_conn)

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.aclose = AsyncMock()

        with (
            patch("stock_picker.api.routes.health.engine", mock_engine),
            patch("stock_picker.api.deps.get_redis_client", return_value=mock_redis),
        ):
            client = _make_client()
            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["db"] == "ok"
        assert data["redis"] == "ok"


# ---------------------------------------------------------------------------
# GET /recommendations
# ---------------------------------------------------------------------------


class TestRecommendationsEndpoint:
    def test_cache_hit_returns_top10(self) -> None:
        """Redis 캐시 히트 시 Top 10 리스트와 200을 반환한다 (AC-7)."""
        recs = _sample_recommendations()
        cached_json = json.dumps(recs, ensure_ascii=False)

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=cached_json)

        with patch("stock_picker.api.deps.get_redis_client", return_value=mock_redis):
            client = _make_client()
            response = client.get("/recommendations")

        assert response.status_code == 200
        body = response.json()
        assert "recommendations" in body
        assert len(body["recommendations"]) == 10
        assert body["recommendations"][0]["rank"] == 1

    def test_cache_miss_returns_preparing(self) -> None:
        """데이터 없을 때 status:preparing과 200을 반환한다 (AC-10)."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        with patch("stock_picker.api.deps.get_redis_client", return_value=mock_redis):
            client = _make_client()
            response = client.get("/recommendations")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "preparing"
        assert body["last_updated"] is None

    def test_response_contains_disclaimer(self) -> None:
        """응답에 면책 고지(disclaimer) 키가 포함되어야 한다."""
        recs = _sample_recommendations()
        cached_json = json.dumps(recs, ensure_ascii=False)

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=cached_json)

        with patch("stock_picker.api.deps.get_redis_client", return_value=mock_redis):
            client = _make_client()
            response = client.get("/recommendations")

        body = response.json()
        assert "disclaimer" in body
        assert len(body["disclaimer"]) > 0

    def test_preparing_response_contains_disclaimer(self) -> None:
        """preparing 상태 응답에도 disclaimer가 포함되어야 한다."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        with patch("stock_picker.api.deps.get_redis_client", return_value=mock_redis):
            client = _make_client()
            response = client.get("/recommendations")

        body = response.json()
        assert "disclaimer" in body

    def test_recommendation_item_schema(self) -> None:
        """추천 항목이 필수 필드를 모두 포함해야 한다."""
        recs = _sample_recommendations()
        cached_json = json.dumps(recs, ensure_ascii=False)

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=cached_json)

        with patch("stock_picker.api.deps.get_redis_client", return_value=mock_redis):
            client = _make_client()
            response = client.get("/recommendations")

        item = response.json()["recommendations"][0]
        required_fields = {
            "rank", "krx_code", "total_score",
            "sentiment_score", "volume_score", "momentum_score",
            "anomaly_score", "reasoning",
        }
        assert required_fields.issubset(item.keys())


# ---------------------------------------------------------------------------
# GET /news
# ---------------------------------------------------------------------------


class TestNewsEndpoint:
    def test_news_returns_20_items(self) -> None:
        """최근 뉴스 20개를 반환해야 한다 (REQ-WEB-004)."""
        # DB 세션을 mock하여 20개 기사 반환
        fake_articles = [
            MagicMock(
                title=f"뉴스 제목 {i}",
                content=f"본문 {i}",
                url=f"https://example.com/{i}",
                source="테스트",
                published_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
                analysis_results=[
                    MagicMock(sentiment="positive", summary=f"요약 {i}")
                ],
            )
            for i in range(20)
        ]

        mock_session = AsyncMock()
        # scalars().all() 패턴 지원
        mock_result = MagicMock()
        mock_result.all.return_value = fake_articles
        mock_scalars = MagicMock()
        mock_scalars.return_value = mock_result
        mock_execute_result = MagicMock()
        mock_execute_result.scalars = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_execute_result)

        async def override_get_session():
            yield mock_session

        from stock_picker.api.main import create_app
        from stock_picker.db.session import get_session

        app = create_app()
        app.dependency_overrides[get_session] = override_get_session

        client = TestClient(app)
        response = client.get("/news")

        assert response.status_code == 200
        body = response.json()
        assert "news" in body
        assert body["total"] == 20
        assert len(body["news"]) == 20

    def test_news_item_schema(self) -> None:
        """뉴스 항목이 필수 필드를 포함해야 한다."""
        fake_articles = [
            MagicMock(
                title="삼성전자 호실적",
                content="삼성전자가 분기 최대 실적을 기록했다.",
                url="https://example.com/1",
                source="한국경제",
                published_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
                analysis_results=[
                    MagicMock(sentiment="positive", summary="호실적 요약")
                ],
            )
        ]

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = fake_articles
        mock_scalars = MagicMock()
        mock_scalars.return_value = mock_result
        mock_execute_result = MagicMock()
        mock_execute_result.scalars = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_execute_result)

        async def override_get_session():
            yield mock_session

        from stock_picker.api.main import create_app
        from stock_picker.db.session import get_session

        app = create_app()
        app.dependency_overrides[get_session] = override_get_session

        client = TestClient(app)
        response = client.get("/news")

        assert response.status_code == 200
        item = response.json()["news"][0]
        required_fields = {"title", "summary", "sentiment", "source", "url", "published_at"}
        assert required_fields.issubset(item.keys())

    def test_news_empty_returns_empty_list(self) -> None:
        """뉴스가 없으면 빈 리스트를 반환해야 한다."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_scalars = MagicMock()
        mock_scalars.return_value = mock_result
        mock_execute_result = MagicMock()
        mock_execute_result.scalars = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_execute_result)

        async def override_get_session():
            yield mock_session

        from stock_picker.api.main import create_app
        from stock_picker.db.session import get_session

        app = create_app()
        app.dependency_overrides[get_session] = override_get_session

        client = TestClient(app)
        response = client.get("/news")

        assert response.status_code == 200
        body = response.json()
        assert body["news"] == []
        assert body["total"] == 0
