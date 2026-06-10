# 추천 피드백 가중치 통합 테스트 (SPEC-STOCK-009 TASK-009)
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def _make_client_with_db(mock_session: AsyncMock) -> TestClient:
    """DB 세션 Override된 TestClient 반환."""
    from stock_picker.api.main import create_app
    from stock_picker.db.session import get_session

    async def override_get_session():
        yield mock_session

    app = create_app()
    app.dependency_overrides[get_session] = override_get_session
    return TestClient(app)


def _make_recommendation_row(
    krx_code: str = "005930",
    rank: int = 1,
    total_score: float = 0.75,
    sentiment_score: float = 0.8,
    volume_score: float = 0.6,
    momentum_score: float = 0.7,
    anomaly_score: float = 0.5,
    reasoning: str = "테스트 근거",
    explanation: str | None = "테스트 설명",
    base_score: float | None = None,
    feedback_score: float | None = None,
    trade_date: date | None = None,
) -> MagicMock:
    """테스트용 Recommendation Mock 행."""
    row = MagicMock()
    row.krx_code = krx_code
    row.rank = rank
    row.total_score = total_score
    row.sentiment_score = sentiment_score
    row.volume_score = volume_score
    row.momentum_score = momentum_score
    row.anomaly_score = anomaly_score
    row.reasoning = reasoning
    row.explanation = explanation
    row.base_score = base_score
    row.feedback_score = feedback_score
    row.trade_date = datetime.combine(
        trade_date or date(2026, 6, 10),
        datetime.min.time(),
        tzinfo=timezone.utc,
    )
    row.computed_at = datetime.now(tz=timezone.utc)
    return row


def _make_session_with_recommendation(rec_row: MagicMock) -> AsyncMock:
    """scalar_one_or_none() → rec_row, scalars().all() → [] 반환하는 Mock 세션."""
    session = AsyncMock()

    # 첫 번째 execute 호출: Recommendation 조회
    mock_rec_result = MagicMock()
    mock_rec_result.scalar_one_or_none.return_value = rec_row

    # 두 번째 execute 호출: 기여 기사 조회 (빈 목록)
    mock_news_result = MagicMock()
    mock_news_result.all.return_value = []

    # 순서대로 반환
    session.execute = AsyncMock(side_effect=[mock_rec_result, mock_news_result])
    return session


class TestRecommendationDetailWithFeedbackScores:
    """추천 상세 API에서 base_score / feedback_score / score_breakdown 반환 테스트."""

    def test_detail_includes_base_score_and_feedback_score(self):
        """상세 API 응답에 base_score, feedback_score 필드가 포함되어야 한다."""
        rec = _make_recommendation_row(
            base_score=0.70,
            feedback_score=0.05,
            total_score=0.75,
        )
        session = _make_session_with_recommendation(rec)
        client = _make_client_with_db(session)

        response = client.get("/recommendations/005930")

        assert response.status_code == 200
        body = response.json()
        assert "base_score" in body
        assert "feedback_score" in body
        assert body["base_score"] == pytest.approx(0.70, abs=1e-3)
        assert body["feedback_score"] == pytest.approx(0.05, abs=1e-3)

    def test_detail_base_score_none_for_old_data(self):
        """구 데이터 (base_score=None)에서도 응답이 정상 반환되어야 한다."""
        rec = _make_recommendation_row(base_score=None, feedback_score=None)
        session = _make_session_with_recommendation(rec)
        client = _make_client_with_db(session)

        response = client.get("/recommendations/005930")

        assert response.status_code == 200
        body = response.json()
        # nullable 필드는 None (JSON null) 이어야 함
        assert body["base_score"] is None
        assert body["feedback_score"] is None

    def test_detail_includes_score_breakdown(self):
        """상세 API 응답에 score_breakdown 필드가 포함되어야 한다."""
        rec = _make_recommendation_row()
        session = _make_session_with_recommendation(rec)
        client = _make_client_with_db(session)

        response = client.get("/recommendations/005930")

        assert response.status_code == 200
        body = response.json()
        assert "score_breakdown" in body
        breakdown = body["score_breakdown"]
        assert "factors" in breakdown
        assert len(breakdown["factors"]) == 4

    def test_detail_score_breakdown_factor_names(self):
        """score_breakdown 요인 이름이 올바른 순서로 반환되어야 한다."""
        rec = _make_recommendation_row()
        session = _make_session_with_recommendation(rec)
        client = _make_client_with_db(session)

        response = client.get("/recommendations/005930")

        body = response.json()
        factor_names = [f["factor"] for f in body["score_breakdown"]["factors"]]
        assert factor_names == ["sentiment", "volume", "momentum", "anomaly"]

    def test_detail_score_breakdown_contribution_sum(self):
        """score_breakdown 기여도 합계 ≈ sentiment+volume+momentum+anomaly 가중 합."""
        rec = _make_recommendation_row(
            sentiment_score=0.8,
            volume_score=0.6,
            momentum_score=0.7,
            anomaly_score=0.5,
        )
        session = _make_session_with_recommendation(rec)
        client = _make_client_with_db(session)

        response = client.get("/recommendations/005930")

        body = response.json()
        factors = body["score_breakdown"]["factors"]
        total_contribution = sum(f["contribution"] for f in factors)

        from stock_picker.scoring.engine import calculate_stock_score
        expected = calculate_stock_score(0.8, 0.6, 0.7, 0.5)
        assert total_contribution == pytest.approx(expected, abs=1e-6)


class TestRecommendationListWithFeedbackScores:
    """추천 목록 API에서 base_score / feedback_score 필드 반환 테스트."""

    def test_list_response_includes_nullable_base_score(self):
        """추천 목록 항목에 base_score nullable 필드가 존재해야 한다."""
        from stock_picker.api.schemas import RecommendationItem
        # Pydantic 스키마 수준 검증
        item = RecommendationItem(
            rank=1,
            krx_code="005930",
            total_score=0.75,
            sentiment_score=0.8,
            volume_score=0.6,
            momentum_score=0.7,
            anomaly_score=0.5,
            reasoning="테스트",
        )
        assert item.base_score is None
        assert item.feedback_score is None

    def test_list_response_accepts_base_score_values(self):
        """base_score와 feedback_score 값이 있으면 올바르게 저장된다."""
        from stock_picker.api.schemas import RecommendationItem
        item = RecommendationItem(
            rank=1,
            krx_code="005930",
            total_score=0.75,
            sentiment_score=0.8,
            volume_score=0.6,
            momentum_score=0.7,
            anomaly_score=0.5,
            reasoning="테스트",
            base_score=0.70,
            feedback_score=0.05,
        )
        assert item.base_score == pytest.approx(0.70)
        assert item.feedback_score == pytest.approx(0.05)


class TestBulkFeedbackService:
    """get_bulk_feedback 함수 통합 테스트."""

    @pytest.mark.asyncio
    async def test_bulk_feedback_empty_codes_returns_empty(self):
        """빈 종목 코드 목록이면 빈 dict 반환."""
        from stock_picker.feedback.service import get_bulk_feedback

        mock_session = AsyncMock()
        result = await get_bulk_feedback(mock_session, [])
        assert result == {}

    @pytest.mark.asyncio
    async def test_bulk_feedback_no_votes_returns_zeros(self):
        """투표가 없는 종목은 up=0, down=0 반환."""
        from stock_picker.feedback.service import get_bulk_feedback

        mock_session = AsyncMock()
        # 쿼리 결과가 빈 경우 시뮬레이션
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await get_bulk_feedback(mock_session, ["005930", "000660"])

        assert result["005930"] == {"up": 0, "down": 0}
        assert result["000660"] == {"up": 0, "down": 0}

    @pytest.mark.asyncio
    async def test_bulk_feedback_aggregates_correctly(self):
        """GROUP BY 결과를 종목별로 올바르게 집계한다."""
        from stock_picker.feedback.service import get_bulk_feedback

        mock_session = AsyncMock()

        # 반환할 행 mock
        row1 = MagicMock()
        row1.krx_code = "005930"
        row1.vote = "up"
        row1.cnt = 5

        row2 = MagicMock()
        row2.krx_code = "005930"
        row2.vote = "down"
        row2.cnt = 2

        row3 = MagicMock()
        row3.krx_code = "000660"
        row3.vote = "up"
        row3.cnt = 3

        mock_result = MagicMock()
        mock_result.all.return_value = [row1, row2, row3]
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await get_bulk_feedback(mock_session, ["005930", "000660"])

        assert result["005930"]["up"] == 5
        assert result["005930"]["down"] == 2
        assert result["000660"]["up"] == 3
        assert result["000660"]["down"] == 0

    @pytest.mark.asyncio
    async def test_bulk_feedback_single_query_not_n_plus_1(self):
        """N+1 방지: 여러 종목이라도 execute는 1회만 호출."""
        from stock_picker.feedback.service import get_bulk_feedback

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        await get_bulk_feedback(mock_session, ["005930", "000660", "035720"])

        # DB execute는 1회만 호출되어야 함 (N+1 쿼리 방지)
        assert mock_session.execute.call_count == 1
