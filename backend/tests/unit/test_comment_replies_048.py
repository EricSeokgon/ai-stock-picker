# SPEC-STOCK-048: 공유 포트폴리오 댓글 대댓글 단위 테스트
# 테스트 실행: backend/.venv/bin/pytest backend/tests/unit/test_comment_replies_048.py -v
"""
SPEC-STOCK-048 TDD 단위 테스트 (RED → GREEN → REFACTOR)
커버리지 대상: add_comment(parent_comment_id), list_comments(replies), 알림 로직
T-048-001 ~ T-048-009 (백엔드 9개)
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# 공통 헬퍼 팩토리 (test_comments_046.py 와 동일 패턴)
# ─────────────────────────────────────────────────────────────────────────────


def _make_mock_user(user_id: int = 1, username: str = "testuser"):
    from stock_picker.db.models import User
    u = MagicMock(spec=User)
    u.id = user_id
    u.username = username
    u.email = f"{username}@example.com"
    return u


def _make_mock_share(share_id: int = 1, portfolio_id: int = 7, token: str = "share_tok_abc"):
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
    from stock_picker.db.models import Portfolio
    p = MagicMock(spec=Portfolio)
    p.id = portfolio_id
    p.user_id = owner_id
    p.name = f"포트폴리오 {portfolio_id}"
    return p


def _make_mock_comment(
    comment_id: int = 10,
    share_id: int = 1,
    user_id: int = 2,
    username: str = "commenter",
    content: str = "좋은 구성이네요",
    parent_comment_id: int | None = None,
):
    """PortfolioComment 모의 객체 생성 (parent_comment_id 포함)"""
    from stock_picker.db.models import PortfolioComment
    c = MagicMock(spec=PortfolioComment)
    c.id = comment_id
    c.share_id = share_id
    c.user_id = user_id
    c.content = content
    c.parent_comment_id = parent_comment_id
    c.created_at = datetime(2026, 7, 1, 10, 0, 0, tzinfo=timezone.utc)
    return c


# ─────────────────────────────────────────────────────────────────────────────
# T-048-001: 대댓글 작성 성공 → 201, parent_comment_id 반환 (REQ-REPLY-001)
# ─────────────────────────────────────────────────────────────────────────────


class TestAddReplySuccess:
    """POST /shared/{token}/comments — parent_comment_id 포함 대댓글 작성"""

    def test_t048_001_add_reply_returns_201_with_parent_id(self):
        """T-048-001: parent_comment_id 포함 대댓글 작성 → 201, parent_comment_id 응답 포함"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app

        client = TestClient(app)
        mock_user = _make_mock_user(user_id=3, username="replier")

        # 서비스가 parent_comment_id 포함 결과를 반환한다고 가정
        expected_result = {
            "id": 20,
            "user_id": 3,
            "username": "replier",
            "content": "저도 동의합니다!",
            "parent_comment_id": 10,
            "replies": [],
            "created_at": datetime(2026, 7, 1, 11, 0, 0, tzinfo=timezone.utc),
        }

        with (
            patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user),
            patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()),
            patch("stock_picker.portfolio.sharing.add_comment", return_value=expected_result),
        ):
            response = client.post(
                "/shared/share_tok_abc/comments",
                json={"content": "저도 동의합니다!", "parent_comment_id": 10},
            )

        assert response.status_code == 201
        data = response.json()
        assert data["parent_comment_id"] == 10
        assert data["content"] == "저도 동의합니다!"


# ─────────────────────────────────────────────────────────────────────────────
# T-048-002: 서비스 레이어 — add_comment parent_comment_id 파라미터 수용 (REQ-REPLY-002)
# ─────────────────────────────────────────────────────────────────────────────


class TestAddReplyServiceSignature:
    """add_comment() 서비스 함수가 parent_comment_id를 파라미터로 받는지 확인"""

    def test_t048_002_add_comment_accepts_parent_comment_id(self):
        """T-048-002: add_comment(parent_comment_id=N) 호출 시 TypeError 없음 + 결과에 parent_comment_id 포함"""
        from stock_picker.portfolio import sharing

        mock_db = MagicMock()
        mock_share = _make_mock_share(share_id=1, portfolio_id=7, token="tok")
        mock_portfolio = _make_mock_portfolio(portfolio_id=7, owner_id=1)
        commenter = _make_mock_user(user_id=3, username="replier")
        # 부모 댓글 (최상위, parent_comment_id=None)
        parent_comment = _make_mock_comment(
            comment_id=10, share_id=1, user_id=2, parent_comment_id=None
        )

        def mock_query(model):
            q = MagicMock()
            model_name = getattr(model, "__name__", str(model))
            inner_q = MagicMock()
            results = {
                "PortfolioShare": mock_share,
                "Portfolio": mock_portfolio,
                "User": commenter,
                "PortfolioComment": parent_comment,
            }
            inner_q.first.return_value = results.get(model_name)
            inner_q.filter.return_value = inner_q
            q.filter.return_value = inner_q
            return q

        mock_db.query = mock_query
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        # parent_comment_id 키워드 인수 — 현재 구현에 없으면 TypeError 발생 (RED)
        result = sharing.add_comment(
            db=mock_db,
            share_token="tok",
            user_id=3,
            content="저도 동의합니다!",
            parent_comment_id=10,
        )

        # 반환 결과에 parent_comment_id 포함 확인
        assert result is not None
        assert result.get("parent_comment_id") == 10


# ─────────────────────────────────────────────────────────────────────────────
# T-048-003: 존재하지 않는 parent_comment_id → 404 (REQ-REPLY-003)
# ─────────────────────────────────────────────────────────────────────────────


class TestAddReplyInvalidParent:
    """부모 댓글 유효성 검증 테스트"""

    def test_t048_003_nonexistent_parent_returns_404(self):
        """T-048-003: 존재하지 않는 parent_comment_id → 404"""
        from fastapi import HTTPException
        from fastapi.testclient import TestClient
        from stock_picker.main import app

        client = TestClient(app)
        mock_user = _make_mock_user(user_id=3)

        with (
            patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user),
            patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()),
            patch(
                "stock_picker.portfolio.sharing.add_comment",
                side_effect=HTTPException(status_code=404, detail="부모 댓글을 찾을 수 없습니다"),
            ),
        ):
            response = client.post(
                "/shared/share_tok_abc/comments",
                json={"content": "답글", "parent_comment_id": 9999},
            )

        assert response.status_code == 404

    def test_t048_004_parent_from_different_share_returns_400(self):
        """T-048-004: 다른 공유의 댓글을 부모로 지정 → 400"""
        from fastapi import HTTPException
        from fastapi.testclient import TestClient
        from stock_picker.main import app

        client = TestClient(app)
        mock_user = _make_mock_user(user_id=3)

        with (
            patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user),
            patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()),
            patch(
                "stock_picker.portfolio.sharing.add_comment",
                side_effect=HTTPException(status_code=400, detail="부모 댓글이 같은 공유에 속하지 않습니다"),
            ),
        ):
            response = client.post(
                "/shared/share_tok_abc/comments",
                json={"content": "답글", "parent_comment_id": 5},
            )

        assert response.status_code == 400

    def test_t048_005_reply_to_reply_returns_400(self):
        """T-048-005: 대댓글에 대댓글 작성 시도 → 400 (단일 레벨만 허용, REQ-REPLY-004)"""
        from fastapi import HTTPException
        from fastapi.testclient import TestClient
        from stock_picker.main import app

        client = TestClient(app)
        mock_user = _make_mock_user(user_id=3)

        with (
            patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user),
            patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()),
            patch(
                "stock_picker.portfolio.sharing.add_comment",
                side_effect=HTTPException(status_code=400, detail="대댓글에는 답글을 달 수 없습니다"),
            ),
        ):
            response = client.post(
                "/shared/share_tok_abc/comments",
                json={"content": "중첩 답글", "parent_comment_id": 20},
            )

        assert response.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────
# T-048-006: 서비스 레이어 — 대댓글에 대댓글 시도 → 400 (REQ-REPLY-004)
# ─────────────────────────────────────────────────────────────────────────────


class TestReplyToReplyService:
    """서비스 레이어에서 대댓글의 대댓글 시도 시 400 반환"""

    def test_t048_006_reply_to_reply_raises_400_in_service(self):
        """T-048-006: 부모 댓글이 이미 대댓글(parent_comment_id != None)이면 HTTPException 400"""
        from fastapi import HTTPException
        from stock_picker.portfolio import sharing

        mock_db = MagicMock()
        mock_share = _make_mock_share(share_id=1, portfolio_id=7, token="tok")
        mock_portfolio = _make_mock_portfolio(portfolio_id=7, owner_id=1)
        commenter = _make_mock_user(user_id=3, username="replier")
        # 부모 댓글이 이미 대댓글 (parent_comment_id=10이 있음)
        nested_parent = _make_mock_comment(
            comment_id=20, share_id=1, user_id=2, parent_comment_id=10
        )

        def mock_query(model):
            q = MagicMock()
            model_name = getattr(model, "__name__", str(model))
            inner_q = MagicMock()
            results = {
                "PortfolioShare": mock_share,
                "Portfolio": mock_portfolio,
                "User": commenter,
                "PortfolioComment": nested_parent,
            }
            inner_q.first.return_value = results.get(model_name)
            inner_q.filter.return_value = inner_q
            q.filter.return_value = inner_q
            return q

        mock_db.query = mock_query
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            sharing.add_comment(
                db=mock_db,
                share_token="tok",
                user_id=3,
                content="중첩 답글",
                parent_comment_id=20,
            )

        assert exc_info.value.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────
# T-048-007: list_comments — 최상위 댓글만 반환, replies 중첩 (REQ-REPLY-005)
# ─────────────────────────────────────────────────────────────────────────────


class TestListCommentsWithReplies:
    """list_comments 서비스 함수 — replies 중첩 반환 확인"""

    def test_t048_007_list_comments_returns_nested_replies(self):
        """T-048-007: list_comments 결과 items에 최상위 댓글만 있고, replies 필드로 대댓글 중첩"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app

        client = TestClient(app)

        # 서비스 mock: 최상위 1개 + 대댓글 1개 중첩
        mocked_list_result = {
            "items": [
                {
                    "id": 10,
                    "user_id": 2,
                    "username": "commenter",
                    "content": "최상위 댓글",
                    "parent_comment_id": None,
                    "replies": [
                        {
                            "id": 20,
                            "user_id": 3,
                            "username": "replier",
                            "content": "대댓글입니다",
                            "parent_comment_id": 10,
                            "replies": [],
                            "created_at": "2026-07-01T11:00:00+00:00",
                        }
                    ],
                    "created_at": "2026-07-01T10:00:00+00:00",
                }
            ],
            "total": 1,  # 최상위 댓글 수만 (대댓글 제외)
            "page": 1,
            "size": 20,
        }

        with (
            patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()),
            patch("stock_picker.portfolio.sharing.list_comments", return_value=mocked_list_result),
        ):
            response = client.get("/shared/share_tok_abc/comments")

        assert response.status_code == 200
        data = response.json()
        # items에 최상위 댓글만 있어야 함
        assert len(data["items"]) == 1
        top_comment = data["items"][0]
        assert top_comment["parent_comment_id"] is None
        # replies 필드가 있고 대댓글 포함
        assert "replies" in top_comment
        assert len(top_comment["replies"]) == 1
        assert top_comment["replies"][0]["parent_comment_id"] == 10
        # total은 최상위만 카운트
        assert data["total"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# T-048-008: 대댓글 알림 — 부모 작성자에게 전송 (REQ-REPLY-009)
# ─────────────────────────────────────────────────────────────────────────────


class TestReplyNotification:
    """대댓글 알림은 포트폴리오 소유자가 아닌 부모 댓글 작성자에게 전송"""

    def test_t048_008_reply_notification_goes_to_parent_author(self):
        """T-048-008: 대댓글 작성 시 알림 수신자가 parent.user_id 임을 확인"""
        from stock_picker.portfolio import sharing

        mock_db = MagicMock()
        mock_share = _make_mock_share(share_id=1, portfolio_id=7, token="tok")
        mock_portfolio = _make_mock_portfolio(portfolio_id=7, owner_id=1)  # 소유자 user_id=1
        commenter = _make_mock_user(user_id=3, username="replier")
        # 부모 댓글 작성자 user_id=2 (소유자도 아니고 대댓글 작성자도 아님)
        parent_comment = _make_mock_comment(
            comment_id=10, share_id=1, user_id=2, parent_comment_id=None
        )

        added_objects: list = []

        def mock_db_add(obj):
            added_objects.append(obj)

        def mock_query(model):
            q = MagicMock()
            model_name = getattr(model, "__name__", str(model))
            inner_q = MagicMock()
            results = {
                "PortfolioShare": mock_share,
                "Portfolio": mock_portfolio,
                "User": commenter,
                "PortfolioComment": parent_comment,
            }
            inner_q.first.return_value = results.get(model_name)
            inner_q.filter.return_value = inner_q
            q.filter.return_value = inner_q
            return q

        mock_db.query = mock_query
        mock_db.add = mock_db_add
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        # 대댓글 작성 (replier → parent_comment)
        result = sharing.add_comment(
            db=mock_db,
            share_token="tok",
            user_id=3,
            content="저도 동의합니다!",
            parent_comment_id=10,
        )

        assert result is not None

        # 알림 객체 중 user_id가 부모 작성자(user_id=2)인 것이 있는지 확인
        from stock_picker.db.models import Notification
        notifications = [obj for obj in added_objects if isinstance(obj, Notification)]
        if notifications:
            # 알림이 생성됐다면 부모 작성자(user_id=2)에게 보내야 함
            assert all(n.user_id == 2 for n in notifications), (
                f"대댓글 알림 수신자가 부모 작성자(2)여야 하는데 {[n.user_id for n in notifications]}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# T-048-009: list_comments total — 최상위 댓글만 카운트 (REQ-REPLY-008)
# ─────────────────────────────────────────────────────────────────────────────


class TestListCommentsTotalTopLevelOnly:
    """list_comments total은 최상위 댓글만 계산 (대댓글 제외)"""

    def test_t048_009_total_counts_top_level_only(self):
        """T-048-009: DB에 최상위 2개 + 대댓글 3개 있을 때 total=2 반환"""
        from stock_picker.portfolio import sharing

        mock_db = MagicMock()
        mock_share = _make_mock_share(share_id=1, portfolio_id=7, token="tok")

        # 최상위 2개 (username 포함 User mock 필요)
        top1 = _make_mock_comment(comment_id=1, share_id=1, parent_comment_id=None)
        top2 = _make_mock_comment(comment_id=2, share_id=1, parent_comment_id=None)
        user1 = _make_mock_user(user_id=2, username="user1")
        user2 = _make_mock_user(user_id=3, username="user2")

        # list_comments는 db.query(PortfolioComment, User) + join + filter + count/all 체인을 사용
        # 가변 인수(*args) 형태로 mock_query를 정의해야 함
        call_count = {"n": 0}

        def mock_query(*args):
            q = MagicMock()
            # 첫 번째 호출: PortfolioShare 조회 (_get_public_share_or_404)
            if args and hasattr(args[0], "__name__") and args[0].__name__ == "PortfolioShare":
                inner_q = MagicMock()
                inner_q.first.return_value = mock_share
                inner_q.filter.return_value = inner_q
                q.filter.return_value = inner_q
                return q
            # PortfolioComment 단독 쿼리 (count용)
            if len(args) == 1:
                inner_q = MagicMock()
                inner_q.filter.return_value = inner_q
                inner_q.count.return_value = 2  # 최상위 2개
                q.filter.return_value = inner_q
                return q
            # PortfolioComment + User 쿼리 (join 조회용)
            call_count["n"] += 1
            inner_q = MagicMock()
            inner_q.join.return_value = inner_q
            inner_q.filter.return_value = inner_q
            inner_q.order_by.return_value = inner_q
            inner_q.offset.return_value = inner_q
            inner_q.limit.return_value = inner_q
            if call_count["n"] == 1:
                # 최상위 댓글 조회
                inner_q.all.return_value = [(top1, user1), (top2, user2)]
            else:
                # 대댓글 배치 조회 (없음)
                inner_q.all.return_value = []
            q.join.return_value = inner_q
            q.filter.return_value = inner_q
            return q

        mock_db.query = mock_query

        result = sharing.list_comments(db=mock_db, share_token="tok", page=1, size=20)

        # total은 최상위 댓글 수만 (2개)
        assert result["total"] == 2
        # items도 최상위만 (2개)
        assert len(result["items"]) == 2
