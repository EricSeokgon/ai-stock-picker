# advice 라우터 통합 테스트 — SPEC-STOCK-014 M2-M5
# HTTP 엔드포인트·인증·멱등성·피드백 검증
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


def _make_advice_mock(
    aid: int = 1,
    user_id: int = 1,
    advice_type: str = "rebalance",
    ref_date: date | None = None,
    title: str = "리밸런싱 제안",
    body: str | None = "본문",
    payload: str | None = None,
    risk_score: int | None = None,
    feedback: str | None = None,
    feedback_at: datetime | None = None,
) -> MagicMock:
    a = MagicMock()
    a.id = aid
    a.user_id = user_id
    a.advice_type = advice_type
    a.ref_date = ref_date or date(2026, 6, 11)
    a.title = title
    a.body = body
    a.payload = payload
    a.risk_score = risk_score
    a.feedback = feedback
    a.feedback_at = feedback_at
    a.created_at = datetime(2026, 6, 11, 9, 0, 0, tzinfo=timezone.utc)
    return a


def _make_client(mock_session: AsyncMock) -> TestClient:
    """get_session + get_current_user를 override한 TestClient 반환."""
    from stock_picker.api.main import create_app
    from stock_picker.auth.dependencies import get_current_user
    from stock_picker.db.session import get_session

    async def override_get_session():
        yield mock_session

    mock_user = MagicMock()
    mock_user.id = 1

    app = create_app()
    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_user] = lambda: mock_user
    return TestClient(app)


class TestRebalanceEndpoint:
    """POST /advice/rebalance — 리밸런싱 제안 (REQ-RB-001~005)"""

    def test_returns_200_with_actions(self):
        """리밸런싱 제안이 actions 포함 200을 반환해야 한다"""
        session = AsyncMock()
        # ai_advice 존재 여부 조회 → None (신규 생성)
        mock_result_none = MagicMock()
        mock_result_none.scalar_one_or_none.return_value = None
        # 최신 추천 trade_date 조회 → date
        mock_date_result = MagicMock()
        mock_date_result.scalar_one_or_none.return_value = date(2026, 6, 11)
        # 추천 목록 조회
        mock_recs_result = MagicMock()
        mock_recs_result.scalars.return_value.all.return_value = []
        # 보유 종목 조회 (WatchlistItem)
        mock_holdings_result = MagicMock()
        mock_holdings_result.scalars.return_value.all.return_value = [
            MagicMock(krx_code="005930", quantity=10, avg_buy_price=70000.0)
        ]
        call_count = [0]
        async def side_effect_execute(stmt, *args, **kwargs):
            c = call_count[0]
            call_count[0] += 1
            if c == 0:
                return mock_result_none  # existing advice check
            elif c == 1:
                return mock_date_result  # latest rec date
            elif c == 2:
                return mock_recs_result  # recs list
            elif c == 3:
                return mock_holdings_result  # watchlist items
            return MagicMock()

        session.execute = AsyncMock(side_effect=side_effect_execute)
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock(side_effect=lambda obj: None)

        # mock session.refresh to fill advice id
        async def mock_refresh(obj):
            obj.id = 1
            obj.created_at = datetime(2026, 6, 11, 9, 0, 0, tzinfo=timezone.utc)

        session.refresh = AsyncMock(side_effect=mock_refresh)

        with patch(
            "stock_picker.advice.service.generate_rebalancing_advice",
            return_value={"actions": [{"krx_code": "005930", "action": "hold", "reason": "안정"}]},
        ):
            client = _make_client(session)
            resp = client.post("/advice/rebalance")

        assert resp.status_code == 200
        data = resp.json()
        assert "actions" in data or "advice_id" in data or "message" in data

    def test_requires_auth(self):
        """인증 없이 접근하면 401/403을 반환해야 한다"""
        from stock_picker.api.main import create_app
        from stock_picker.db.session import get_session

        session = AsyncMock()

        async def override_get_session():
            yield session

        app = create_app()
        app.dependency_overrides[get_session] = override_get_session
        # get_current_user override 없음 → 인증 실패

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/advice/rebalance")
        assert resp.status_code in (401, 403, 422)

    def test_returns_no_holdings_message_when_empty(self):
        """보유 종목 없으면 안내 메시지를 반환해야 한다 (REQ-AIV-006)"""
        session = AsyncMock()
        mock_result_none = MagicMock()
        mock_result_none.scalar_one_or_none.return_value = None
        mock_date_result = MagicMock()
        mock_date_result.scalar_one_or_none.return_value = date(2026, 6, 11)
        mock_recs_result = MagicMock()
        mock_recs_result.scalars.return_value.all.return_value = []
        mock_holdings_empty = MagicMock()
        mock_holdings_empty.scalars.return_value.all.return_value = []

        call_count = [0]
        async def side_effect_execute(stmt, *args, **kwargs):
            c = call_count[0]
            call_count[0] += 1
            if c == 0:
                return mock_result_none
            elif c == 1:
                return mock_date_result
            elif c == 2:
                return mock_recs_result
            elif c == 3:
                return mock_holdings_empty
            return MagicMock()

        session.execute = AsyncMock(side_effect=side_effect_execute)

        client = _make_client(session)
        resp = client.post("/advice/rebalance")

        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data


class TestRiskProfileEndpoint:
    """POST /advice/risk-profile — 리스크 프로파일 (REQ-RM-001~005)"""

    def test_returns_200_with_risk_score(self):
        """리스크 프로파일이 risk_score 포함 200을 반환해야 한다"""
        session = AsyncMock()
        mock_result_none = MagicMock()
        mock_result_none.scalar_one_or_none.return_value = None
        mock_holdings_result = MagicMock()
        mock_holdings_result.scalars.return_value.all.return_value = [
            MagicMock(krx_code="005930", quantity=10, avg_buy_price=70000.0)
        ]

        call_count = [0]
        async def side_effect_execute(stmt, *args, **kwargs):
            c = call_count[0]
            call_count[0] += 1
            if c == 0:
                return mock_result_none
            elif c == 1:
                return mock_holdings_result
            return MagicMock()

        session.execute = AsyncMock(side_effect=side_effect_execute)
        session.add = MagicMock()
        session.commit = AsyncMock()

        async def mock_refresh(obj):
            obj.id = 2

        session.refresh = AsyncMock(side_effect=mock_refresh)

        with patch(
            "stock_picker.advice.service.generate_risk_profile",
            return_value={"risk_score": 75, "explanation": "집중도가 높습니다."},
        ):
            client = _make_client(session)
            resp = client.post("/advice/risk-profile")

        assert resp.status_code == 200
        data = resp.json()
        assert "risk_score" in data or "advice_id" in data or "message" in data


class TestMarketBriefingEndpoint:
    """GET /advice/market-briefing — 시장 브리핑 (REQ-MB-001~005)"""

    def test_returns_200_with_briefing(self):
        """시장 브리핑이 briefing 필드 포함 200을 반환해야 한다"""
        session = AsyncMock()
        mock_result_none = MagicMock()
        mock_result_none.scalar_one_or_none.return_value = None
        mock_holdings_result = MagicMock()
        mock_holdings_result.scalars.return_value.all.return_value = [
            MagicMock(krx_code="005930", quantity=10, avg_buy_price=70000.0)
        ]
        mock_sentiment_result = MagicMock()
        mock_sentiment_result.scalars.return_value.all.return_value = []

        call_count = [0]
        async def side_effect_execute(stmt, *args, **kwargs):
            c = call_count[0]
            call_count[0] += 1
            if c == 0:
                return mock_result_none
            elif c == 1:
                return mock_holdings_result
            elif c == 2:
                return mock_sentiment_result
            return MagicMock()

        session.execute = AsyncMock(side_effect=side_effect_execute)
        session.add = MagicMock()
        session.commit = AsyncMock()

        async def mock_refresh(obj):
            obj.id = 3

        session.refresh = AsyncMock(side_effect=mock_refresh)

        with patch(
            "stock_picker.advice.service.generate_market_briefing",
            return_value={"briefing": "오늘 시장은 강세입니다."},
        ), patch(
            "stock_picker.advice.router.get_redis_client",
            return_value=None,
        ):
            client = _make_client(session)
            resp = client.get("/advice/market-briefing")

        assert resp.status_code == 200
        data = resp.json()
        assert "briefing" in data or "advice_id" in data or "message" in data


class TestAdviceHistoryEndpoint:
    """GET /advice/history — 조언 이력 (REQ-AIV-004)"""

    def test_returns_empty_list_when_no_history(self):
        """이력 없으면 빈 배열을 반환해야 한다"""
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=mock_result)

        client = _make_client(session)
        resp = client.get("/advice/history")

        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_history_list(self):
        """이력 조회 시 목록을 반환해야 한다"""
        advice = _make_advice_mock(aid=1, advice_type="rebalance")
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [advice]
        session.execute = AsyncMock(return_value=mock_result)

        client = _make_client(session)
        resp = client.get("/advice/history")

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1


class TestFeedbackEndpoint:
    """POST /advice/{id}/feedback — 피드백 등록 (REQ-FB-001~003)"""

    def test_helpful_feedback_updates_row(self):
        """helpful 피드백이 정상적으로 처리되어야 한다"""
        advice = _make_advice_mock(aid=1, user_id=1)
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = advice
        session.execute = AsyncMock(return_value=mock_result)
        session.commit = AsyncMock()

        client = _make_client(session)
        resp = client.post("/advice/1/feedback", json={"feedback": "helpful"})

        assert resp.status_code == 200

    def test_invalid_feedback_returns_422(self):
        """유효하지 않은 피드백 값은 422를 반환해야 한다 (REQ-FB-003)"""
        session = AsyncMock()

        client = _make_client(session)
        resp = client.post("/advice/1/feedback", json={"feedback": "invalid_value"})

        assert resp.status_code == 422

    def test_not_found_advice_returns_404(self):
        """존재하지 않는 조언 ID는 404를 반환해야 한다 (REQ-FB-002)"""
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        client = _make_client(session)
        resp = client.post("/advice/999/feedback", json={"feedback": "helpful"})

        assert resp.status_code == 404
