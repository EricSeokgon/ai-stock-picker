# 관심종목 라우터 통합 테스트 — TestClient + 인메모리 SQLite
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from stock_picker.db.models import User, WatchlistItem


def _build_app(engine):
    """주어진 엔진으로 FastAPI 앱 + 의존성 override 구성"""
    from stock_picker.api.main import create_app
    from stock_picker.auth import dependencies as auth_deps

    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_session():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[auth_deps.get_db_session] = override_get_session
    return app


@pytest.fixture
def client():
    """각 테스트마다 새로운 인메모리 DB + TestClient 생성"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # SQLite 호환 테이블만 생성
    User.__table__.create(bind=engine, checkfirst=True)
    WatchlistItem.__table__.create(bind=engine, checkfirst=True)

    app = _build_app(engine)
    with TestClient(app) as c:
        yield c

    WatchlistItem.__table__.drop(bind=engine, checkfirst=True)
    User.__table__.drop(bind=engine, checkfirst=True)


def _register_and_login(client, username="watchuser", email="watch@test.com", password="pass1234"):
    """회원가입 + 로그인 후 Bearer 토큰 반환"""
    client.post("/auth/register", json={
        "username": username,
        "email": email,
        "password": password,
    })
    resp = client.post("/auth/login", json={"username": username, "password": password})
    return resp.json()["access_token"]


class TestListWatchlist:
    """GET /watchlist 테스트"""

    def test_returns_empty_list_initially(self, client):
        """초기 관심종목 목록은 빈 배열"""
        token = _register_and_login(client)
        resp = client.get("/watchlist", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_requires_auth(self, client):
        """인증 없이 요청 시 401"""
        resp = client.get("/watchlist")
        assert resp.status_code == 401


class TestAddWatchlist:
    """POST /watchlist 테스트"""

    def test_adds_item_returns_201(self, client):
        """관심종목 추가 — 201 반환"""
        token = _register_and_login(client)
        resp = client.post(
            "/watchlist",
            json={"krx_code": "005930"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["krx_code"] == "005930"
        assert "id" in body
        assert "added_at" in body

    def test_duplicate_returns_409(self, client):
        """중복 추가 — 409 Conflict"""
        token = _register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}
        client.post("/watchlist", json={"krx_code": "000660"}, headers=headers)
        resp = client.post("/watchlist", json={"krx_code": "000660"}, headers=headers)
        assert resp.status_code == 409

    def test_requires_auth(self, client):
        """인증 없이 추가 시 401"""
        resp = client.post("/watchlist", json={"krx_code": "005930"})
        assert resp.status_code == 401

    def test_list_shows_added_item(self, client):
        """추가 후 목록 조회 시 종목 포함"""
        token = _register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}
        client.post("/watchlist", json={"krx_code": "035420"}, headers=headers)
        resp = client.get("/watchlist", headers=headers)
        assert resp.status_code == 200
        codes = [item["krx_code"] for item in resp.json()]
        assert "035420" in codes


class TestDeleteWatchlist:
    """DELETE /watchlist/{krx_code} 테스트"""

    def test_deletes_existing_item(self, client):
        """존재하는 종목 삭제 — 204 No Content"""
        token = _register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}
        client.post("/watchlist", json={"krx_code": "005930"}, headers=headers)
        resp = client.delete("/watchlist/005930", headers=headers)
        assert resp.status_code == 204

    def test_delete_nonexistent_returns_404(self, client):
        """없는 종목 삭제 — 404 Not Found"""
        token = _register_and_login(client)
        resp = client.delete(
            "/watchlist/NONE99",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    def test_requires_auth(self, client):
        """인증 없이 삭제 시 401"""
        resp = client.delete("/watchlist/005930")
        assert resp.status_code == 401

    def test_delete_removes_from_list(self, client):
        """삭제 후 목록에서 제거 확인"""
        token = _register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}
        client.post("/watchlist", json={"krx_code": "005930"}, headers=headers)
        client.delete("/watchlist/005930", headers=headers)
        resp = client.get("/watchlist", headers=headers)
        codes = [item["krx_code"] for item in resp.json()]
        assert "005930" not in codes
