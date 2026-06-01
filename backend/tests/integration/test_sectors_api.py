# 섹터 트렌드 API 통합 테스트 (TASK-024)
# GET /sectors/trends → 섹터 트렌드 시계열 반환
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


def _make_client() -> TestClient:
    """앱 임포트 후 TestClient 반환."""
    from stock_picker.api.main import create_app

    app = create_app()
    return TestClient(app)


def _make_sector_trend_row(
    sector: str = "반도체",
    trade_date: date | None = None,
    trend_score: float = 0.75,
    news_volume: int = 10,
    avg_sentiment: float = 0.5,
) -> MagicMock:
    """테스트용 SectorTrend Mock 생성."""
    row = MagicMock()
    row.sector = sector
    row.trade_date = datetime.combine(
        trade_date or date(2026, 6, 1), datetime.min.time(), tzinfo=timezone.utc
    )
    row.trend_score = trend_score
    row.news_volume = news_volume
    row.avg_sentiment = avg_sentiment
    return row


class TestSectorTrendsEndpoint:
    """GET /sectors/trends 엔드포인트 테스트"""

    def test_returns_200_with_trend_list(self):
        """GET /sectors/trends는 200과 트렌드 리스트를 반환해야 한다"""
        from stock_picker.api.main import create_app
        from stock_picker.db.session import get_session

        trends = [
            _make_sector_trend_row("반도체", date(2026, 6, 1), 0.80),
            _make_sector_trend_row("IT", date(2026, 6, 1), 0.65),
        ]

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = trends
        mock_scalars = MagicMock()
        mock_scalars.return_value = mock_result
        mock_execute_result = MagicMock()
        mock_execute_result.scalars = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_execute_result)

        async def override_get_session():
            yield mock_session

        app = create_app()
        app.dependency_overrides[get_session] = override_get_session

        client = TestClient(app)
        response = client.get("/sectors/trends")

        assert response.status_code == 200
        body = response.json()
        assert "trends" in body
        assert len(body["trends"]) == 2

    def test_response_schema_fields(self):
        """응답 스키마에 필수 필드가 포함되어야 한다"""
        from stock_picker.api.main import create_app
        from stock_picker.db.session import get_session

        trends = [_make_sector_trend_row("반도체")]

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = trends
        mock_scalars = MagicMock()
        mock_scalars.return_value = mock_result
        mock_execute_result = MagicMock()
        mock_execute_result.scalars = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_execute_result)

        async def override_get_session():
            yield mock_session

        app = create_app()
        app.dependency_overrides[get_session] = override_get_session

        client = TestClient(app)
        response = client.get("/sectors/trends")
        body = response.json()

        item = body["trends"][0]
        required_fields = {"sector", "trade_date", "trend_score", "news_volume", "avg_sentiment"}
        assert required_fields.issubset(item.keys())

    def test_empty_db_returns_empty_list(self):
        """DB가 비어있으면 빈 리스트를 반환해야 한다 (에러 아님)"""
        from stock_picker.api.main import create_app
        from stock_picker.db.session import get_session

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

        app = create_app()
        app.dependency_overrides[get_session] = override_get_session

        client = TestClient(app)
        response = client.get("/sectors/trends")

        assert response.status_code == 200
        body = response.json()
        assert body["trends"] == []

    def test_cache_hit_does_not_query_db(self):
        """캐시 히트 시 DB를 조회하지 않아야 한다"""
        import json
        from stock_picker.api.main import create_app
        from stock_picker.db.session import get_session

        cached_data = {
            "trends": [
                {
                    "sector": "반도체",
                    "trade_date": "2026-06-01",
                    "trend_score": 0.80,
                    "news_volume": 15,
                    "avg_sentiment": 0.6,
                }
            ],
            "days": 7,
        }

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()  # 호출되면 안 됨

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=json.dumps(cached_data, ensure_ascii=False))

        async def override_get_session():
            yield mock_session

        app = create_app()
        app.dependency_overrides[get_session] = override_get_session

        with patch("stock_picker.api.deps.get_redis_client", return_value=mock_redis):
            client = TestClient(app)
            response = client.get("/sectors/trends")

        # 캐시 히트 시 DB execute 호출 없어야 함
        mock_session.execute.assert_not_called()
        assert response.status_code == 200

    def test_days_query_param_accepted(self):
        """?days=N 쿼리 파라미터를 수용해야 한다"""
        from stock_picker.api.main import create_app
        from stock_picker.db.session import get_session

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

        app = create_app()
        app.dependency_overrides[get_session] = override_get_session

        client = TestClient(app)
        response = client.get("/sectors/trends?days=14")

        assert response.status_code == 200
        body = response.json()
        assert body["days"] == 14
