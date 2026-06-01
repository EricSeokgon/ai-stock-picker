# 추천 근거 상세 API 통합 테스트 (TASK-025)
# GET /recommendations/{krx_code} → 종목 추천 근거 상세
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient


def _make_recommendation_row(
    krx_code: str = "005930",
    trade_date: date | None = None,
    total_score: float = 0.82,
    sentiment_score: float = 0.75,
    volume_score: float = 0.60,
    momentum_score: float = 0.55,
    anomaly_score: float = 0.40,
    reasoning: str = "삼성전자 분석 결과 긍정적 트렌드",
) -> MagicMock:
    """테스트용 Recommendation Mock 생성."""
    row = MagicMock()
    row.krx_code = krx_code
    row.trade_date = datetime.combine(
        trade_date or date(2026, 6, 1), datetime.min.time(), tzinfo=timezone.utc
    )
    row.total_score = total_score
    row.sentiment_score = sentiment_score
    row.volume_score = volume_score
    row.momentum_score = momentum_score
    row.anomaly_score = anomaly_score
    row.reasoning = reasoning
    return row


def _make_contributing_news(
    title: str = "삼성전자 호실적",
    summary: str = "삼성전자가 분기 최대 실적을 기록했다",
    sentiment: str = "positive",
    hours_ago: float = 2.0,
) -> MagicMock:
    """테스트용 기사+분석 Mock 생성."""
    published_at = datetime.now(tz=timezone.utc)
    article = MagicMock()
    article.title = title
    article.summary = summary
    article.sentiment = sentiment
    article.published_at = published_at
    return article


class TestRecommendationDetailEndpoint:
    """GET /recommendations/{krx_code} 엔드포인트 테스트"""

    def test_valid_krx_code_returns_200(self):
        """유효한 krx_code는 200을 반환해야 한다"""
        from stock_picker.api.main import create_app
        from stock_picker.db.session import get_session

        rec = _make_recommendation_row("005930")
        news = [_make_contributing_news() for _ in range(3)]

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        # 첫 번째 execute: Recommendation 조회
        # 두 번째 execute: 기사 조회
        rec_result = MagicMock()
        rec_result.scalar_one_or_none = MagicMock(return_value=rec)

        news_result = MagicMock()
        news_result.all = MagicMock(return_value=news)

        mock_session.execute = AsyncMock(side_effect=[rec_result, news_result])

        async def override_get_session():
            yield mock_session

        app = create_app()
        app.dependency_overrides[get_session] = override_get_session

        client = TestClient(app)
        response = client.get("/recommendations/005930")

        assert response.status_code == 200

    def test_invalid_krx_code_returns_404(self):
        """존재하지 않는 krx_code는 404를 반환해야 한다"""
        from stock_picker.api.main import create_app
        from stock_picker.db.session import get_session

        mock_session = AsyncMock()
        rec_result = MagicMock()
        rec_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=rec_result)

        async def override_get_session():
            yield mock_session

        app = create_app()
        app.dependency_overrides[get_session] = override_get_session

        client = TestClient(app)
        response = client.get("/recommendations/INVALID")

        assert response.status_code == 404

    def test_response_contains_score_breakdown(self):
        """응답에 세부 점수 항목이 포함되어야 한다"""
        from stock_picker.api.main import create_app
        from stock_picker.db.session import get_session

        rec = _make_recommendation_row("005930")
        news = [_make_contributing_news()]

        rec_result = MagicMock()
        rec_result.scalar_one_or_none = MagicMock(return_value=rec)
        news_result = MagicMock()
        news_result.all = MagicMock(return_value=news)

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[rec_result, news_result])

        async def override_get_session():
            yield mock_session

        app = create_app()
        app.dependency_overrides[get_session] = override_get_session

        client = TestClient(app)
        response = client.get("/recommendations/005930")
        body = response.json()

        required_fields = {
            "krx_code", "trade_date", "total_score",
            "sentiment_score", "volume_score", "momentum_score", "anomaly_score",
            "reasoning", "contributing_news", "disclaimer",
        }
        assert required_fields.issubset(body.keys())

    def test_response_contains_contributing_news(self):
        """응답에 contributing_news 리스트가 포함되어야 한다"""
        from stock_picker.api.main import create_app
        from stock_picker.db.session import get_session

        rec = _make_recommendation_row("005930")
        news = [_make_contributing_news() for _ in range(3)]

        rec_result = MagicMock()
        rec_result.scalar_one_or_none = MagicMock(return_value=rec)
        news_result = MagicMock()
        news_result.all = MagicMock(return_value=news)

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[rec_result, news_result])

        async def override_get_session():
            yield mock_session

        app = create_app()
        app.dependency_overrides[get_session] = override_get_session

        client = TestClient(app)
        response = client.get("/recommendations/005930")
        body = response.json()

        assert "contributing_news" in body
        assert isinstance(body["contributing_news"], list)
        assert len(body["contributing_news"]) == 3

    def test_contributing_news_item_schema(self):
        """contributing_news 항목이 필수 필드를 포함해야 한다"""
        from stock_picker.api.main import create_app
        from stock_picker.db.session import get_session

        rec = _make_recommendation_row("005930")
        news = [_make_contributing_news()]

        rec_result = MagicMock()
        rec_result.scalar_one_or_none = MagicMock(return_value=rec)
        news_result = MagicMock()
        news_result.all = MagicMock(return_value=news)

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[rec_result, news_result])

        async def override_get_session():
            yield mock_session

        app = create_app()
        app.dependency_overrides[get_session] = override_get_session

        client = TestClient(app)
        response = client.get("/recommendations/005930")
        body = response.json()

        news_item = body["contributing_news"][0]
        required_news_fields = {"title", "summary", "sentiment", "published_at"}
        assert required_news_fields.issubset(news_item.keys())

    def test_response_contains_disclaimer(self):
        """응답에 면책 고지가 포함되어야 한다"""
        from stock_picker.api.main import create_app
        from stock_picker.db.session import get_session

        rec = _make_recommendation_row("005930")
        news = []

        rec_result = MagicMock()
        rec_result.scalar_one_or_none = MagicMock(return_value=rec)
        news_result = MagicMock()
        news_result.all = MagicMock(return_value=news)

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[rec_result, news_result])

        async def override_get_session():
            yield mock_session

        app = create_app()
        app.dependency_overrides[get_session] = override_get_session

        client = TestClient(app)
        response = client.get("/recommendations/005930")
        body = response.json()

        assert "disclaimer" in body
        assert len(body["disclaimer"]) > 0
