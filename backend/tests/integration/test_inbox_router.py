# 알림 인박스 라우터 통합 테스트 (SPEC-STOCK-013 M2)
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient


def _make_notification_mock(
    nid: int = 1,
    user_id: int = 1,
    ntype: str = "price_alert",
    krx_code: str = "005930",
    title: str = "테스트 알림",
    body: str | None = "알림 본문",
    is_read: bool = False,
    ref_date: date | None = None,
    related_alert_id: int | None = None,
) -> MagicMock:
    n = MagicMock()
    n.id = nid
    n.user_id = user_id
    n.type = ntype
    n.krx_code = krx_code
    n.title = title
    n.body = body
    n.is_read = is_read
    n.ref_date = ref_date or date(2026, 6, 11)
    n.related_alert_id = related_alert_id
    n.created_at = datetime(2026, 6, 11, 9, 0, 0, tzinfo=timezone.utc)
    n.read_at = None
    return n


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


class TestGetNotifications:
    def test_returns_empty_list_when_no_notifications(self):
        """알림 없을 때 빈 배열 반환"""
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=mock_result)

        client = _make_client(session)
        resp = client.get("/notifications/")

        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_notifications_list(self):
        """알림 목록 반환 — id, type, krx_code 포함"""
        notif = _make_notification_mock(nid=1, ntype="rec_new", krx_code="005930")
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [notif]
        session.execute = AsyncMock(return_value=mock_result)

        client = _make_client(session)
        resp = client.get("/notifications/")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == 1
        assert data[0]["type"] == "rec_new"
        assert data[0]["krx_code"] == "005930"
        assert data[0]["is_read"] is False

    def test_unread_only_param_accepted(self):
        """unread_only=true 파라미터 수용"""
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=mock_result)

        client = _make_client(session)
        resp = client.get("/notifications/?unread_only=true")

        assert resp.status_code == 200


class TestGetUnreadCount:
    def test_returns_zero_count(self):
        """미읽음 0개 반환"""
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 0
        session.execute = AsyncMock(return_value=mock_result)

        client = _make_client(session)
        resp = client.get("/notifications/unread-count")

        assert resp.status_code == 200
        assert resp.json() == {"count": 0}

    def test_returns_nonzero_count(self):
        """미읽음 3개 반환"""
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 3
        session.execute = AsyncMock(return_value=mock_result)

        client = _make_client(session)
        resp = client.get("/notifications/unread-count")

        assert resp.status_code == 200
        assert resp.json() == {"count": 3}


class TestMarkAsRead:
    def test_returns_404_when_not_found(self):
        """존재하지 않는 알림 — 404 반환"""
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        client = _make_client(session)
        resp = client.patch("/notifications/99/read")

        assert resp.status_code == 404

    def test_marks_notification_as_read(self):
        """읽음 처리 후 is_read=True 반환"""
        notif = _make_notification_mock(nid=1, is_read=False)
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = notif
        session.execute = AsyncMock(return_value=mock_result)
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        client = _make_client(session)
        resp = client.patch("/notifications/1/read")

        assert resp.status_code == 200
        # is_read가 True로 설정되었는지 확인
        assert notif.is_read is True
        session.commit.assert_called_once()

    def test_already_read_no_commit(self):
        """이미 읽음 상태 — commit 없이 반환"""
        notif = _make_notification_mock(nid=1, is_read=True)
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = notif
        session.execute = AsyncMock(return_value=mock_result)
        session.commit = AsyncMock()

        client = _make_client(session)
        resp = client.patch("/notifications/1/read")

        assert resp.status_code == 200
        session.commit.assert_not_called()


class TestMarkAllRead:
    def test_returns_updated_count(self):
        """전체 읽음 처리 — 업데이트 건수 반환"""
        session = AsyncMock()
        mock_result = MagicMock()
        # RETURNING clause 결과 2건
        mock_result.fetchall.return_value = [(1,), (2,)]
        session.execute = AsyncMock(return_value=mock_result)
        session.commit = AsyncMock()

        client = _make_client(session)
        resp = client.patch("/notifications/read-all")

        assert resp.status_code == 200
        assert resp.json() == {"updated": 2}
        session.commit.assert_called_once()

    def test_returns_zero_when_all_already_read(self):
        """모두 읽음 — 0 반환"""
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        session.execute = AsyncMock(return_value=mock_result)
        session.commit = AsyncMock()

        client = _make_client(session)
        resp = client.patch("/notifications/read-all")

        assert resp.status_code == 200
        assert resp.json() == {"updated": 0}
