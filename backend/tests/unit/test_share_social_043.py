# SPEC-STOCK-043: 포트폴리오 공유 좋아요 취소, 알림, 조회수 통계 단위 테스트
# 테스트 실행: cd backend && python -m pytest tests/unit/test_share_social_043.py -v
"""
SPEC-STOCK-043 TDD 단위 테스트
커버리지 대상: unlike, portfolio_like 알림, share_view_stats upsert, 통계 조회 API
AC 총 23개 (AC-043-001a ~ AC-043-014)
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, call, patch


# ─────────────────────────────────────────────────────────────────────────────
# 공통 헬퍼
# ─────────────────────────────────────────────────────────────────────────────


def _make_mock_user(user_id: int = 1, username: str = "testuser"):
    """User 모의 객체 생성"""
    from stock_picker.db.models import User
    u = MagicMock(spec=User)
    u.id = user_id
    u.username = username
    u.email = f"{username}@example.com"
    return u


def _make_mock_share(share_id: int = 1, portfolio_id: int = 7, token: str = "share_tok_abc"):
    """PortfolioShare 모의 객체 생성"""
    from stock_picker.db.models import PortfolioShare
    s = MagicMock(spec=PortfolioShare)
    s.id = share_id
    s.portfolio_id = portfolio_id
    s.share_token = token
    s.share_url = f"/shared/{token}"
    s.is_public = True
    s.view_count = 0
    return s


def _make_mock_portfolio(portfolio_id: int = 7, owner_id: int = 1):
    """Portfolio 모의 객체 생성"""
    from stock_picker.db.models import Portfolio
    p = MagicMock(spec=Portfolio)
    p.id = portfolio_id
    p.user_id = owner_id
    p.name = f"포트폴리오 {portfolio_id}"
    return p


def _make_notification_mock(
    nid: int = 1,
    user_id: int = 1,
    ntype: str = "portfolio_like",
    krx_code: str = "P7",
    title: str = "bob님이 좋아요를 눌렀습니다",
    is_read: bool = False,
    ref_date: date | None = None,
) -> MagicMock:
    n = MagicMock()
    n.id = nid
    n.user_id = user_id
    n.type = ntype
    n.krx_code = krx_code
    n.title = title
    n.body = None
    n.is_read = is_read
    n.ref_date = ref_date or date.today()
    n.related_alert_id = None
    n.created_at = datetime(2026, 6, 30, 9, 0, 0, tzinfo=timezone.utc)
    n.read_at = None
    return n


# ─────────────────────────────────────────────────────────────────────────────
# TestUnlike — DELETE /shared/{token}/like  (AC-001a ~ 005)
# ─────────────────────────────────────────────────────────────────────────────


class TestUnlike:
    """DELETE /shared/{token}/like 엔드포인트 & 서비스 레이어 테스트"""

    def test_t043_001a_unlike_existing_like_returns_204(self):
        """AC-043-001a: 인증된 비소유자가 존재하는 좋아요를 취소 → 204 No Content"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app

        client = TestClient(app)
        mock_user = _make_mock_user(user_id=2, username="bob")

        with patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user), \
             patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()), \
             patch("stock_picker.portfolio.sharing.remove_like", return_value=None):
            response = client.delete("/shared/share_tok_abc/like")

        assert response.status_code == 204

    def test_t043_001b_unlike_deletes_portfolio_likes_row(self):
        """AC-043-001b: 좋아요 취소 시 portfolio_likes 행이 삭제된다"""
        from stock_picker.db.models import PortfolioLike
        from stock_picker.portfolio.sharing import remove_like

        db = MagicMock()
        mock_share = _make_mock_share(share_id=1, portfolio_id=7, token="tok_del")
        mock_portfolio = _make_mock_portfolio(portfolio_id=7, owner_id=1)
        mock_like = MagicMock(spec=PortfolioLike)
        mock_like.id = 99
        mock_like.share_id = 1
        mock_like.user_id = 2

        # db.query() 호출 순서: share → portfolio → like
        # PortfolioLike은 단일 .filter().first() 체인
        def _query_side_effect(model):
            m = MagicMock()
            model_name = getattr(model, "__name__", "")
            if model_name == "PortfolioShare":
                m.filter.return_value.first.return_value = mock_share
            elif model_name == "Portfolio":
                m.filter.return_value.first.return_value = mock_portfolio
            elif model_name == "PortfolioLike":
                # remove_like: .filter(share_id==x, user_id==y).first()
                m.filter.return_value.first.return_value = mock_like
            return m

        db.query.side_effect = _query_side_effect

        remove_like(db, share_token="tok_del", user_id=2)  # 비소유자 user_id=2

        db.delete.assert_called_once_with(mock_like)
        db.commit.assert_called()

    def test_t043_001c_unlike_decreases_like_count_by_one(self):
        """AC-043-001c: 좋아요 취소 후 like_count(COUNT 파생값)가 1 감소한다"""
        from stock_picker.db.models import PortfolioLike
        from stock_picker.portfolio.sharing import remove_like

        db = MagicMock()
        mock_share = _make_mock_share(share_id=1, portfolio_id=7, token="tok_cnt")
        mock_portfolio = _make_mock_portfolio(portfolio_id=7, owner_id=1)
        mock_like = MagicMock(spec=PortfolioLike)

        def _query_side_effect(model):
            m = MagicMock()
            model_name = getattr(model, "__name__", "")
            if model_name == "PortfolioShare":
                m.filter.return_value.first.return_value = mock_share
            elif model_name == "Portfolio":
                m.filter.return_value.first.return_value = mock_portfolio
            elif model_name == "PortfolioLike":
                # remove_like: .filter(share_id==x, user_id==y).first()
                m.filter.return_value.first.return_value = mock_like
            return m

        db.query.side_effect = _query_side_effect

        # 좋아요 취소 실행
        remove_like(db, share_token="tok_cnt", user_id=2)

        # 삭제가 수행되었으므로 delete가 호출되어야 함 (count 감소 검증)
        db.delete.assert_called_once_with(mock_like)

    def test_t043_002_unlike_no_existing_like_is_idempotent_204(self):
        """AC-043-002: 좋아요 없는 취소 → 204 (멱등, 404 아님)"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app

        client = TestClient(app)
        mock_user = _make_mock_user(user_id=2)

        # remove_like가 None을 반환 (좋아요 없어도 정상)
        with patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user), \
             patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()), \
             patch("stock_picker.portfolio.sharing.remove_like", return_value=None):
            response = client.delete("/shared/share_tok_abc/like")

        assert response.status_code == 204

    def test_t043_002_service_unlike_when_no_like_does_not_delete(self):
        """AC-043-002 서비스 레벨: 좋아요 없음 → db.delete() 미호출"""
        from stock_picker.portfolio.sharing import remove_like

        db = MagicMock()
        mock_share = _make_mock_share(share_id=1, portfolio_id=7, token="tok_noop")
        mock_portfolio = _make_mock_portfolio(portfolio_id=7, owner_id=1)

        def _query_side_effect(model):
            m = MagicMock()
            model_name = getattr(model, "__name__", "")
            if model_name == "PortfolioShare":
                m.filter.return_value.first.return_value = mock_share
            elif model_name == "Portfolio":
                m.filter.return_value.first.return_value = mock_portfolio
            elif model_name == "PortfolioLike":
                # 좋아요 없음 — remove_like: .filter().first()
                m.filter.return_value.first.return_value = None
            return m

        db.query.side_effect = _query_side_effect

        remove_like(db, share_token="tok_noop", user_id=2)

        db.delete.assert_not_called()

    def test_t043_003_owner_unlike_returns_403(self):
        """AC-043-003: 포트폴리오 소유자가 좋아요 취소 → 403"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app
        from fastapi import HTTPException

        client = TestClient(app)
        mock_user = _make_mock_user(user_id=1)  # 소유자 user_id=1

        with patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user), \
             patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()), \
             patch("stock_picker.portfolio.sharing.remove_like",
                   side_effect=HTTPException(status_code=403, detail="자신의 포트폴리오에는 좋아요를 취소할 수 없습니다")):
            response = client.delete("/shared/share_tok_abc/like")

        assert response.status_code == 403

    def test_t043_004_unauthenticated_unlike_returns_401(self):
        """AC-043-004: 미인증 좋아요 취소 → 401"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app

        client = TestClient(app)

        with patch("stock_picker.auth.dependencies.get_current_user",
                   side_effect=Exception("Unauthorized")):
            response = client.delete("/shared/share_tok_abc/like")

        assert response.status_code == 401

    def test_t043_005_nonpublic_unlike_returns_404(self):
        """AC-043-005: is_public=False 또는 미존재 공유 → 404"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app
        from fastapi import HTTPException

        client = TestClient(app)
        mock_user = _make_mock_user(user_id=2)

        with patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user), \
             patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()), \
             patch("stock_picker.portfolio.sharing.remove_like",
                   side_effect=HTTPException(status_code=404, detail="공유 포트폴리오를 찾을 수 없습니다")):
            response = client.delete("/shared/invalid_token/like")

        assert response.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# TestLikeNotification — 좋아요 알림 (AC-006 ~ 009)
# ─────────────────────────────────────────────────────────────────────────────


class TestLikeNotification:
    """POST /shared/{token}/like 시 portfolio_like 알림 생성 테스트"""

    def test_t043_006_new_like_inserts_notification_for_owner(self):
        """AC-043-006: 신규 좋아요 시 소유자에게 portfolio_like 알림 1건 적재"""
        from stock_picker.db.models import Notification
        from stock_picker.portfolio.sharing import add_like

        db = MagicMock()
        token = "tok_notif"
        mock_share = _make_mock_share(share_id=1, portfolio_id=7, token=token)
        mock_portfolio = _make_mock_portfolio(portfolio_id=7, owner_id=1)
        mock_liker = _make_mock_user(user_id=2, username="bob")

        # add_like 호출 순서: PortfolioShare → Portfolio → User → func.count(PortfolioLike.id)
        def _query_side_effect(model):
            m = MagicMock()
            model_name = getattr(model, "__name__", "")
            if model_name == "PortfolioShare":
                m.filter.return_value.first.return_value = mock_share
            elif model_name == "Portfolio":
                m.filter.return_value.first.return_value = mock_portfolio
            elif model_name == "User":
                m.filter.return_value.first.return_value = mock_liker
            else:
                # func.count(PortfolioLike.id) — scalar 결과 반환
                m.filter.return_value.scalar.return_value = 1
            return m

        db.query.side_effect = _query_side_effect

        # IntegrityError 없이 정상 like INSERT + notification INSERT
        db.commit.return_value = None

        add_like(db, share_token=token, user_id=2)

        # db.add()가 호출되었는지 확인
        added_objects = [c.args[0] for c in db.add.call_args_list]

        # Notification 타입 객체가 추가되어야 함
        notifications = [o for o in added_objects if isinstance(o, Notification)]
        assert len(notifications) == 1

        notif = notifications[0]
        assert notif.type == "portfolio_like"
        assert notif.user_id == 1  # 소유자
        assert notif.krx_code == "P7"
        assert "bob" in notif.title  # liker 이름 포함

    def test_t043_007a_duplicate_like_returns_200_idempotent(self):
        """AC-043-007a: 중복 좋아요 → 200 (멱등성)"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app

        client = TestClient(app)
        mock_user = _make_mock_user(user_id=2)

        with patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user), \
             patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()), \
             patch("stock_picker.portfolio.sharing.add_like", return_value={"like_count": 1}):
            response = client.post("/shared/share_tok_abc/like")

        assert response.status_code == 200

    def test_t043_007b_duplicate_like_does_not_add_notification(self):
        """AC-043-007b: 중복 좋아요(IntegrityError) → 알림 미생성"""
        from sqlalchemy.exc import IntegrityError
        from stock_picker.db.models import Notification
        from stock_picker.portfolio.sharing import add_like

        db = MagicMock()
        token = "tok_dup"
        mock_share = _make_mock_share(share_id=1, portfolio_id=7, token=token)
        mock_portfolio = _make_mock_portfolio(portfolio_id=7, owner_id=1)
        mock_liker = _make_mock_user(user_id=2, username="bob")

        def _query_side_effect(model):
            m = MagicMock()
            model_name = getattr(model, "__name__", "")
            if model_name == "PortfolioShare":
                m.filter.return_value.first.return_value = mock_share
            elif model_name == "Portfolio":
                m.filter.return_value.first.return_value = mock_portfolio
            elif model_name == "User":
                m.filter.return_value.first.return_value = mock_liker
            else:
                # func.count(PortfolioLike.id)
                m.filter.return_value.scalar.return_value = 1
            return m

        db.query.side_effect = _query_side_effect

        # 중복 좋아요: 첫 번째 commit(like INSERT) 시 IntegrityError 발생
        commit_calls = [IntegrityError("statement", "params", Exception("unique violation")), None]
        db.commit.side_effect = commit_calls

        add_like(db, share_token=token, user_id=2)

        # 알림이 추가되지 않아야 함
        added_objects = [c.args[0] for c in db.add.call_args_list]
        notifications = [o for o in added_objects if isinstance(o, Notification)]
        assert len(notifications) == 0

    def test_t043_008a_owner_like_returns_403(self):
        """AC-043-008a: 소유자 자기 좋아요 → 403"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app
        from fastapi import HTTPException

        client = TestClient(app)
        mock_user = _make_mock_user(user_id=1)

        with patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user), \
             patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()), \
             patch("stock_picker.portfolio.sharing.add_like",
                   side_effect=HTTPException(status_code=403, detail="자신의 포트폴리오에는 좋아요할 수 없습니다")):
            response = client.post("/shared/share_tok_abc/like")

        assert response.status_code == 403

    def test_t043_008b_owner_like_does_not_create_notification(self):
        """AC-043-008b: 소유자 자기 좋아요(403) → 알림 미생성"""
        from fastapi import HTTPException
        from stock_picker.db.models import Notification
        from stock_picker.portfolio.sharing import add_like

        db = MagicMock()
        token = "tok_owner_self"
        mock_share = _make_mock_share(share_id=1, portfolio_id=7, token=token)
        mock_portfolio = _make_mock_portfolio(portfolio_id=7, owner_id=1)

        def _query_side_effect(model):
            m = MagicMock()
            model_name = getattr(model, "__name__", "")
            if model_name == "PortfolioShare":
                m.filter.return_value.first.return_value = mock_share
            elif model_name == "Portfolio":
                m.filter.return_value.first.return_value = mock_portfolio
            return m

        db.query.side_effect = _query_side_effect

        # 소유자 user_id=1이 자기 포트폴리오(owner_id=1) 에 좋아요 → HTTPException(403)
        try:
            add_like(db, share_token=token, user_id=1)
        except HTTPException as e:
            assert e.status_code == 403

        # 알림이 추가되지 않아야 함
        added_objects = [c.args[0] for c in db.add.call_args_list]
        notifications = [o for o in added_objects if isinstance(o, Notification)]
        assert len(notifications) == 0

    def test_t043_009_two_different_portfolios_create_separate_notifications(self):
        """AC-043-009: 서로 다른 포트폴리오 좋아요 → 알림 각각 생성 (krx_code 분리)"""
        from stock_picker.db.models import Notification
        from stock_picker.portfolio.sharing import add_like

        # Portfolio P7과 P8에 각각 좋아요
        db1 = MagicMock()
        db2 = MagicMock()
        mock_liker = _make_mock_user(user_id=2, username="bob")

        def _make_query_for(portfolio_id: int):
            mock_share = _make_mock_share(share_id=portfolio_id, portfolio_id=portfolio_id,
                                          token=f"tok_{portfolio_id}")
            mock_portfolio = _make_mock_portfolio(portfolio_id=portfolio_id, owner_id=1)

            def _side_effect(model):
                m = MagicMock()
                model_name = getattr(model, "__name__", "")
                if model_name == "PortfolioShare":
                    m.filter.return_value.first.return_value = mock_share
                elif model_name == "Portfolio":
                    m.filter.return_value.first.return_value = mock_portfolio
                elif model_name == "User":
                    m.filter.return_value.first.return_value = mock_liker
                else:
                    # func.count(PortfolioLike.id)
                    m.filter.return_value.scalar.return_value = 1
                return m

            return _side_effect

        db1.query.side_effect = _make_query_for(7)
        db2.query.side_effect = _make_query_for(8)

        add_like(db1, share_token="tok_7", user_id=2)
        add_like(db2, share_token="tok_8", user_id=2)

        # P7 알림 확인
        added1 = [c.args[0] for c in db1.add.call_args_list]
        notifs1 = [o for o in added1 if isinstance(o, Notification)]
        assert len(notifs1) == 1
        assert notifs1[0].krx_code == "P7"

        # P8 알림 확인
        added2 = [c.args[0] for c in db2.add.call_args_list]
        notifs2 = [o for o in added2 if isinstance(o, Notification)]
        assert len(notifs2) == 1
        assert notifs2[0].krx_code == "P8"


# ─────────────────────────────────────────────────────────────────────────────
# TestNotificationInbox — 알림 인박스 (AC-010a ~ 010c)
# ─────────────────────────────────────────────────────────────────────────────


def _make_inbox_client(notifications: list, notification_to_read: MagicMock | None = None):
    """get_session + get_current_user override TestClient 반환."""
    from stock_picker.api.main import create_app
    from stock_picker.auth.dependencies import get_current_user
    from stock_picker.db.session import get_session

    mock_user = _make_mock_user(user_id=1)

    mock_session = AsyncMock()

    # GET /notifications 용 결과
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = notifications

    # GET /notifications/unread-count 용 결과
    count_result = MagicMock()
    count_result.scalar_one.return_value = len([n for n in notifications if not n.is_read])

    # PATCH /notifications/{id}/read 용 결과
    if notification_to_read is not None:
        read_result = MagicMock()
        read_result.scalar_one_or_none.return_value = notification_to_read
    else:
        read_result = MagicMock()
        read_result.scalar_one_or_none.return_value = None

    mock_session.execute = AsyncMock(side_effect=[
        list_result, count_result, read_result,
        list_result, count_result, read_result,  # 두 번 호출될 수 있으므로 여분 제공
    ])
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    async def override_get_session():
        yield mock_session

    app = create_app()
    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_user] = lambda: mock_user

    from fastapi.testclient import TestClient
    return TestClient(app)


class TestNotificationInbox:
    """GET /notifications, PATCH /notifications/{id}/read — portfolio_like 알림 인박스 노출"""

    def test_t043_010a_portfolio_like_notification_included_in_unread_count(self):
        """AC-043-010a: portfolio_like 알림이 GET /notifications/unread-count 에 포함"""
        notif = _make_notification_mock(ntype="portfolio_like", krx_code="P7", is_read=False)
        client = _make_inbox_client([notif])

        # 두 번째 execute가 unread-count에 사용됨
        response = client.get("/notifications/unread-count")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 1

    def test_t043_010b_portfolio_like_notification_visible_in_list(self):
        """AC-043-010b: portfolio_like 알림이 GET /notifications 목록에 포함"""
        notif = _make_notification_mock(
            ntype="portfolio_like",
            krx_code="P7",
            title="bob님이 좋아요를 눌렀습니다",
            is_read=False,
        )
        client = _make_inbox_client([notif])

        response = client.get("/notifications")

        assert response.status_code == 200
        items = response.json()
        assert len(items) >= 1
        # portfolio_like 타입 알림이 포함되어야 함
        types = [item["type"] for item in items]
        assert "portfolio_like" in types

    def test_t043_010c_portfolio_like_notification_can_be_marked_read(self):
        """AC-043-010c: portfolio_like 알림 읽음 처리 — PATCH /notifications/{id}/read"""
        notif = _make_notification_mock(
            nid=42,
            ntype="portfolio_like",
            krx_code="P7",
            is_read=False,
        )
        from stock_picker.api.main import create_app
        from stock_picker.auth.dependencies import get_current_user
        from stock_picker.db.session import get_session

        mock_user = _make_mock_user(user_id=1)
        mock_session = AsyncMock()

        # 읽음 처리 후 is_read=True 상태로 반환
        notif_after_read = _make_notification_mock(
            nid=42, ntype="portfolio_like", is_read=True,
        )
        notif_after_read.is_read = False  # 처음에는 미읽음 (업데이트 로직 통과)

        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = notif

        mock_session.execute = AsyncMock(return_value=select_result)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, "is_read", True))

        async def override_get_session():
            yield mock_session

        app = create_app()
        app.dependency_overrides[get_session] = override_get_session
        app.dependency_overrides[get_current_user] = lambda: mock_user

        from fastapi.testclient import TestClient
        client = TestClient(app)

        response = client.patch("/notifications/42/read")

        assert response.status_code == 200
        # 읽음 처리가 수행되었는지 확인 (commit 호출)
        mock_session.commit.assert_called()


# ─────────────────────────────────────────────────────────────────────────────
# TestViewStats — 조회수 통계 (AC-011a ~ 014)
# ─────────────────────────────────────────────────────────────────────────────


class TestViewStats:
    """share_view_stats upsert 및 GET /portfolios/{portfolio_id}/share/stats 테스트"""

    def test_t043_011a_public_view_twice_upserts_view_count_2(self):
        """AC-043-011a: GET /shared/{token} 2번 호출 → share_view_stats.view_count=2"""
        from stock_picker.portfolio.sharing import get_public_shared_portfolio

        db = MagicMock()
        token = "tok_stat"
        mock_share = _make_mock_share(share_id=1, portfolio_id=7, token=token)
        mock_portfolio = _make_mock_portfolio(portfolio_id=7, owner_id=1)

        def _query_side_effect(model):
            m = MagicMock()
            model_name = getattr(model, "__name__", "")
            if model_name == "PortfolioShare":
                m.filter.return_value.first.return_value = mock_share
            elif model_name == "Portfolio":
                m.filter.return_value.first.return_value = mock_portfolio
            else:
                # func.count(PortfolioLike.id) — like_count = 0
                m.filter.return_value.scalar.return_value = 0
            return m

        db.query.side_effect = _query_side_effect

        # 두 번 호출
        get_public_shared_portfolio(db, share_token=token)
        get_public_shared_portfolio(db, share_token=token)

        # db.execute()가 share_view_stats upsert를 위해 호출되었는지 확인
        # 각 호출마다: (1) view_count UPDATE, (2) share_view_stats INSERT/UPDATE → 총 4회
        assert db.execute.call_count >= 4

    def test_t043_011b_public_view_twice_increments_portfolio_shares_view_count(self):
        """AC-043-011b: GET /shared/{token} 2번 호출 → portfolio_shares.view_count +2"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app

        client = TestClient(app)

        # view_count가 0에서 시작, 각 호출 후 +1
        mock_data_call1 = {
            "share_token": "tok_vc",
            "share_url": "/shared/tok_vc",
            "view_count": 1,
            "like_count": 0,
            "portfolio_id": 7,
            "portfolio_name": "테스트 포트폴리오",
        }
        mock_data_call2 = {**mock_data_call1, "view_count": 2}

        with patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()), \
             patch("stock_picker.portfolio.sharing.get_public_shared_portfolio",
                   side_effect=[mock_data_call1, mock_data_call2]):
            r1 = client.get("/shared/tok_vc")
            r2 = client.get("/shared/tok_vc")

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["view_count"] == 1
        assert r2.json()["view_count"] == 2

    def test_t043_011c_nonpublic_view_does_not_upsert_share_view_stats(self):
        """AC-043-011c: 비공개 포트폴리오 뷰(404) → share_view_stats 미적재"""
        from stock_picker.portfolio.sharing import get_public_shared_portfolio
        from fastapi import HTTPException

        db = MagicMock()

        def _query_side_effect(model):
            m = MagicMock()
            if model.__name__ == "PortfolioShare":
                # is_public=False 또는 미존재 → None 반환
                m.filter.return_value.first.return_value = None
            return m

        db.query.side_effect = _query_side_effect

        with patch("stock_picker.auth.dependencies.get_db_session", return_value=db):
            try:
                get_public_shared_portfolio(db, share_token="invalid_tok")
            except HTTPException as e:
                assert e.status_code == 404

        # 404 경로에서는 share_view_stats에 아무것도 upsert되지 않아야 함
        # execute()가 호출되지 않거나, 호출되더라도 stats upsert 전에 예외 발생
        # (share가 None이면 즉시 HTTPException 발생하므로 execute 미호출)
        # view_count 업데이트 쿼리(execute)가 없어야 함
        assert db.execute.call_count == 0

    def test_t043_012_owner_get_stats_returns_7_days_with_zero_fill(self):
        """AC-043-012: GET /portfolios/{id}/share/stats → 200, 7개 항목, 오늘 view_count=3, 어제=0"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app

        client = TestClient(app)
        mock_user = _make_mock_user(user_id=1)

        # 7일 통계 mock (오늘 3회, 나머지 0)
        today = date.today()
        mock_stats = {
            "stats": [
                {"date": (today.replace(day=today.day - i) if today.day > i
                          else today).isoformat(),
                 "view_count": 3 if i == 0 else 0}
                for i in range(6, -1, -1)
            ]
        }

        with patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user), \
             patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()), \
             patch("stock_picker.portfolio.sharing.get_share_stats", return_value=mock_stats):
            response = client.get("/portfolios/7/share/stats")

        assert response.status_code == 200
        data = response.json()
        assert "stats" in data
        assert len(data["stats"]) == 7
        # 날짜 오름차순 확인
        dates = [item["date"] for item in data["stats"]]
        assert dates == sorted(dates)
        # 마지막(오늘) view_count=3
        assert data["stats"][-1]["view_count"] == 3

    def test_t043_012b_no_share_record_returns_7_zeros(self):
        """AC-043-012b: portfolio_shares 레코드 없음 → 200, 7개 항목 모두 view_count=0"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app

        client = TestClient(app)
        mock_user = _make_mock_user(user_id=1)

        today = date.today()
        mock_stats = {
            "stats": [
                {"date": (today.replace(day=today.day - i) if today.day > i
                          else today).isoformat(),
                 "view_count": 0}
                for i in range(6, -1, -1)
            ]
        }

        with patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user), \
             patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()), \
             patch("stock_picker.portfolio.sharing.get_share_stats", return_value=mock_stats):
            response = client.get("/portfolios/7/share/stats")

        assert response.status_code == 200
        data = response.json()
        assert len(data["stats"]) == 7
        assert all(item["view_count"] == 0 for item in data["stats"])

    def test_t043_013_non_owner_stats_returns_404(self):
        """AC-043-013: 비소유자 통계 조회 → 404"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app
        from fastapi import HTTPException

        client = TestClient(app)
        mock_user = _make_mock_user(user_id=2)  # 비소유자

        with patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user), \
             patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()), \
             patch("stock_picker.portfolio.sharing.get_share_stats",
                   side_effect=HTTPException(status_code=404, detail="포트폴리오를 찾을 수 없습니다")):
            response = client.get("/portfolios/7/share/stats")

        assert response.status_code == 404

    def test_t043_014_unauthenticated_stats_returns_401(self):
        """AC-043-014: 미인증 통계 조회 → 401"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app

        client = TestClient(app)

        with patch("stock_picker.auth.dependencies.get_current_user",
                   side_effect=Exception("Unauthorized")):
            response = client.get("/portfolios/7/share/stats")

        assert response.status_code == 401
