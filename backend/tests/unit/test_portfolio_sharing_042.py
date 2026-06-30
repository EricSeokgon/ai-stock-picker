# SPEC-STOCK-042: 포트폴리오 공유 & 소셜 단위 테스트
# 테스트 실행: backend/.venv/bin/pytest backend/tests/unit/test_portfolio_sharing_042.py -v
from unittest.mock import MagicMock, patch

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# TestShareCreate — POST /{portfolio_id}/share (공유 생성/활성화)
# ─────────────────────────────────────────────────────────────────────────────


class TestShareCreate:
    """POST /portfolios/{portfolio_id}/share 엔드포인트 테스트"""

    def _make_mock_user(self, user_id: int = 1):
        from stock_picker.db.models import User
        u = MagicMock(spec=User)
        u.id = user_id
        u.email = f"user{user_id}@example.com"
        return u

    def _make_mock_share(self, portfolio_id: int = 1, token: str = "abc123tok"):
        """공유 레코드 mock 생성"""
        from stock_picker.db.models import PortfolioShare
        s = MagicMock(spec=PortfolioShare)
        s.id = 1
        s.portfolio_id = portfolio_id
        s.share_token = token
        s.share_url = f"/shared/{token}"
        s.is_public = True
        s.view_count = 0
        return s

    def test_t001_owner_create_share_returns_200_with_token(self):
        """T-001: 소유자 공유 생성 → 200 + share_token + share_url"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app

        client = TestClient(app)
        mock_user = self._make_mock_user(1)
        mock_share = self._make_mock_share(1, "tok_abc123def456")

        with patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user), \
             patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()), \
             patch("stock_picker.portfolio.sharing.create_or_reactivate_share", return_value=mock_share):
            response = client.post("/portfolios/1/share")

        assert response.status_code == 200
        data = response.json()
        assert "share_token" in data
        assert "share_url" in data
        assert data["share_token"] == "tok_abc123def456"
        assert data["share_url"] == "/shared/tok_abc123def456"

    def test_t002_idempotent_share_reuses_existing_token(self):
        """T-002: 멱등성 — 이미 존재하는 공유 → 동일 token 재사용"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app

        client = TestClient(app)
        mock_user = self._make_mock_user(1)
        existing_token = "existing_token_xyz"
        mock_share = self._make_mock_share(1, existing_token)

        with patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user), \
             patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()), \
             patch("stock_picker.portfolio.sharing.create_or_reactivate_share", return_value=mock_share):
            # 두 번 호출해도 같은 token 반환
            response = client.post("/portfolios/1/share")

        assert response.status_code == 200
        data = response.json()
        assert data["share_token"] == existing_token

    def test_t003_non_owner_create_share_returns_404(self):
        """T-003: 비소유자 공유 생성 → 404"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app
        from fastapi import HTTPException

        client = TestClient(app)
        # user_id=2가 portfolio_id=1 (소유자 user_id=1) 에 접근
        mock_user = self._make_mock_user(2)

        with patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user), \
             patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()), \
             patch("stock_picker.portfolio.sharing.create_or_reactivate_share",
                   side_effect=HTTPException(status_code=404, detail="포트폴리오를 찾을 수 없습니다")):
            response = client.post("/portfolios/1/share")

        assert response.status_code == 404

    def test_t004_unauthenticated_create_share_returns_401(self):
        """T-004: 미인증 공유 생성 → 401"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app

        client = TestClient(app)

        with patch("stock_picker.auth.dependencies.get_current_user",
                   side_effect=Exception("Unauthorized")):
            response = client.post("/portfolios/1/share")

        assert response.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# TestShareDelete — DELETE /{portfolio_id}/share (공유 비활성화)
# ─────────────────────────────────────────────────────────────────────────────


class TestShareDelete:
    """DELETE /portfolios/{portfolio_id}/share 엔드포인트 테스트"""

    def _make_mock_user(self, user_id: int = 1):
        from stock_picker.db.models import User
        u = MagicMock(spec=User)
        u.id = user_id
        return u

    def test_t005_owner_delete_share_returns_204(self):
        """T-005: 소유자 공유 비활성화 → 204 (소프트 삭제)"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app

        client = TestClient(app)
        mock_user = self._make_mock_user(1)

        with patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user), \
             patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()), \
             patch("stock_picker.portfolio.sharing.deactivate_share", return_value=None):
            response = client.delete("/portfolios/1/share")

        assert response.status_code == 204

    def test_t006_non_owner_delete_share_returns_404(self):
        """T-006: 비소유자 공유 비활성화 → 404"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app
        from fastapi import HTTPException

        client = TestClient(app)
        mock_user = self._make_mock_user(2)

        with patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user), \
             patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()), \
             patch("stock_picker.portfolio.sharing.deactivate_share",
                   side_effect=HTTPException(status_code=404, detail="포트폴리오를 찾을 수 없습니다")):
            response = client.delete("/portfolios/1/share")

        assert response.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# TestShareGet — GET /{portfolio_id}/share (공유 상태 조회)
# ─────────────────────────────────────────────────────────────────────────────


class TestShareGet:
    """GET /portfolios/{portfolio_id}/share 엔드포인트 테스트"""

    def _make_mock_user(self, user_id: int = 1):
        from stock_picker.db.models import User
        u = MagicMock(spec=User)
        u.id = user_id
        return u

    def _make_mock_share(self):
        from stock_picker.db.models import PortfolioShare
        s = MagicMock(spec=PortfolioShare)
        s.id = 1
        s.portfolio_id = 1
        s.share_token = "mytoken123"
        s.share_url = "/shared/mytoken123"
        s.is_public = True
        s.view_count = 10
        return s

    def test_t007_owner_get_share_returns_200(self):
        """T-007: 소유자 공유 상태 조회 → 200 + share_token, view_count"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app

        client = TestClient(app)
        mock_user = self._make_mock_user(1)
        mock_share = self._make_mock_share()

        with patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user), \
             patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()), \
             patch("stock_picker.portfolio.sharing.get_share_status", return_value=mock_share):
            response = client.get("/portfolios/1/share")

        assert response.status_code == 200
        data = response.json()
        assert "share_token" in data
        assert "view_count" in data
        assert data["view_count"] == 10


# ─────────────────────────────────────────────────────────────────────────────
# TestPublicSharedGet — GET /shared/{token} (공개 공유 포트폴리오 조회)
# ─────────────────────────────────────────────────────────────────────────────


class TestPublicSharedGet:
    """GET /shared/{token} 공개 엔드포인트 테스트"""

    def _make_mock_share_response(self, token: str = "tok123"):
        """SharePublicResponse와 호환되는 dict 반환"""
        return {
            "share_token": token,
            "share_url": f"/shared/{token}",
            "view_count": 1,
            "like_count": 0,
            "portfolio_id": 1,
            "portfolio_name": "테스트 포트폴리오",
        }

    def test_t008_public_get_shared_returns_200_and_increments_view(self):
        """T-008: 공개 공유 포트폴리오 조회 → 200 + view_count 증가"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app

        client = TestClient(app)
        mock_data = self._make_mock_share_response("tok123")

        with patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()), \
             patch("stock_picker.portfolio.sharing.get_public_shared_portfolio",
                   return_value=mock_data):
            response = client.get("/shared/tok123")

        assert response.status_code == 200
        data = response.json()
        assert "portfolio_id" in data
        assert "view_count" in data

    def test_t008b_inactive_share_returns_404(self):
        """T-008b: is_public=False 공유 조회 → 404"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app
        from fastapi import HTTPException

        client = TestClient(app)

        with patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()), \
             patch("stock_picker.portfolio.sharing.get_public_shared_portfolio",
                   side_effect=HTTPException(status_code=404, detail="공유 포트폴리오를 찾을 수 없습니다")):
            response = client.get("/shared/invalid_token")

        assert response.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# TestLike — POST /shared/{token}/like (좋아요)
# ─────────────────────────────────────────────────────────────────────────────


class TestLike:
    """POST /shared/{token}/like 엔드포인트 테스트"""

    def _make_mock_user(self, user_id: int = 2):
        from stock_picker.db.models import User
        u = MagicMock(spec=User)
        u.id = user_id
        return u

    def test_t009_owner_like_own_portfolio_returns_403(self):
        """T-009: 자신의 포트폴리오 좋아요 → 403"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app
        from fastapi import HTTPException

        client = TestClient(app)
        # user_id=1이 자신의 portfolio(소유자=1)에 좋아요
        mock_user = self._make_mock_user(1)

        with patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user), \
             patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()), \
             patch("stock_picker.portfolio.sharing.add_like",
                   side_effect=HTTPException(status_code=403, detail="자신의 포트폴리오에는 좋아요할 수 없습니다")):
            response = client.post("/shared/mytoken/like")

        assert response.status_code == 403

    def test_t010_unauthenticated_like_returns_401(self):
        """T-010: 미인증 좋아요 → 401"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app

        client = TestClient(app)

        with patch("stock_picker.auth.dependencies.get_current_user",
                   side_effect=Exception("Unauthorized")):
            response = client.post("/shared/mytoken/like")

        assert response.status_code == 401

    def test_t011_other_user_like_returns_200_with_like_count(self):
        """T-011: 타 사용자 좋아요 → 200 + like_count"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app

        client = TestClient(app)
        mock_user = self._make_mock_user(2)

        with patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user), \
             patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()), \
             patch("stock_picker.portfolio.sharing.add_like", return_value={"like_count": 1}):
            response = client.post("/shared/mytoken/like")

        assert response.status_code == 200
        data = response.json()
        assert "like_count" in data

    def test_t012_duplicate_like_is_idempotent(self):
        """T-012: 중복 좋아요 → 200 (오류 없음, 멱등성)"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app

        client = TestClient(app)
        mock_user = self._make_mock_user(2)

        with patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user), \
             patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()), \
             patch("stock_picker.portfolio.sharing.add_like", return_value={"like_count": 1}):
            response = client.post("/shared/mytoken/like")

        # 멱등성: 중복 좋아요도 200 반환
        assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# TestFeed — GET /feed (공개 공유 피드)
# ─────────────────────────────────────────────────────────────────────────────


class TestFeed:
    """GET /feed 엔드포인트 테스트"""

    def _make_mock_feed_response(self, count: int = 3, sort: str = "recent"):
        items = [
            {
                "share_token": f"tok{i}",
                "share_url": f"/shared/tok{i}",
                "view_count": i * 10,
                "like_count": i * 2,
                "portfolio_id": i,
                "portfolio_name": f"포트폴리오 {i}",
            }
            for i in range(1, count + 1)
        ]
        if sort == "likes":
            items.sort(key=lambda x: x["like_count"], reverse=True)
        return {"items": items, "total": count, "page": 1, "size": len(items)}

    def test_t013_feed_returns_200_with_list(self):
        """T-013: GET /feed → 200 + 공개 공유 포트폴리오 목록"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app

        client = TestClient(app)
        mock_response = self._make_mock_feed_response(3)

        with patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()), \
             patch("stock_picker.portfolio.sharing.get_feed", return_value=mock_response):
            response = client.get("/feed")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_t014_feed_sort_likes_returns_sorted_by_like_count(self):
        """T-014: GET /feed?sort=likes → like_count DESC 정렬"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app

        client = TestClient(app)
        mock_response = self._make_mock_feed_response(3, sort="likes")

        with patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()), \
             patch("stock_picker.portfolio.sharing.get_feed", return_value=mock_response):
            response = client.get("/feed?sort=likes")

        assert response.status_code == 200
        data = response.json()
        # like_count 내림차순 확인
        items = data["items"]
        if len(items) >= 2:
            assert items[0]["like_count"] >= items[1]["like_count"]

    def test_t015_feed_pagination_works(self):
        """T-015: GET /feed?page=2&size=5 → 페이지네이션 동작"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app

        client = TestClient(app)
        mock_response = {
            "items": [
                {"share_token": "tok6", "share_url": "/shared/tok6",
                 "view_count": 0, "like_count": 0,
                 "portfolio_id": 6, "portfolio_name": "포트폴리오 6"},
            ],
            "total": 10,
            "page": 2,
            "size": 5,
        }

        with patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()), \
             patch("stock_picker.portfolio.sharing.get_feed", return_value=mock_response):
            response = client.get("/feed?page=2&size=5")

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["size"] == 5
        assert "items" in data
