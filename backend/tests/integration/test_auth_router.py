# 인증 라우터 통합 테스트 (TestClient + 공유 인메모리 SQLite)
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from stock_picker.db.models import User


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
    """각 테스트마다 완전히 새로운 인메모리 DB + TestClient 생성"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # 모든 스레드가 같은 연결 공유
    )
    # User 테이블만 생성 (SQLite는 PostgreSQL ARRAY 미지원)
    User.__table__.create(bind=engine, checkfirst=True)

    app = _build_app(engine)
    with TestClient(app) as c:
        yield c

    # 테스트 종료 후 테이블 삭제
    User.__table__.drop(bind=engine, checkfirst=True)


class TestRegister:
    """POST /auth/register 테스트"""

    def test_register_success(self, client):
        """유효한 데이터로 회원가입 시 201 반환"""
        resp = client.post("/auth/register", json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123",
        })
        assert resp.status_code == 201
        body = resp.json()
        assert body["username"] == "testuser"
        assert "password" not in body
        assert "hashed_password" not in body

    def test_register_duplicate_username_returns_409(self, client):
        """중복 사용자명 회원가입 시 409 반환"""
        payload = {"username": "dupuser", "email": "dup1@example.com", "password": "pass1234"}
        client.post("/auth/register", json=payload)
        resp = client.post("/auth/register", json={
            "username": "dupuser",
            "email": "dup2@example.com",
            "password": "pass1234",
        })
        assert resp.status_code == 409

    def test_register_duplicate_email_returns_409(self, client):
        """중복 이메일 회원가입 시 409 반환"""
        payload = {"username": "user1", "email": "same@example.com", "password": "pass1234"}
        client.post("/auth/register", json=payload)
        resp = client.post("/auth/register", json={
            "username": "user2",
            "email": "same@example.com",
            "password": "pass1234",
        })
        assert resp.status_code == 409


class TestLogin:
    """POST /auth/login 테스트"""

    def _register(self, client, username="loginuser", email="login@example.com"):
        client.post("/auth/register", json={
            "username": username,
            "email": email,
            "password": "correctpass123",
        })

    def test_login_success_returns_tokens(self, client):
        """올바른 자격증명으로 로그인 시 토큰 쌍 반환"""
        self._register(client)
        resp = client.post("/auth/login", json={
            "username": "loginuser",
            "password": "correctpass123",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    def test_login_wrong_password_returns_401(self, client):
        """틀린 비밀번호로 로그인 시 401 반환"""
        self._register(client)
        resp = client.post("/auth/login", json={
            "username": "loginuser",
            "password": "wrongpass",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user_returns_401(self, client):
        """존재하지 않는 사용자 로그인 시 401 반환"""
        resp = client.post("/auth/login", json={
            "username": "nobody",
            "password": "anypass",
        })
        assert resp.status_code == 401


class TestMe:
    """GET /auth/me 테스트"""

    def _get_token(self, client):
        client.post("/auth/register", json={
            "username": "meuser",
            "email": "me@example.com",
            "password": "mypass123",
        })
        resp = client.post("/auth/login", json={
            "username": "meuser",
            "password": "mypass123",
        })
        return resp.json()["access_token"]

    def test_me_with_valid_token(self, client):
        """유효한 Bearer 토큰으로 /auth/me 호출 시 200 반환"""
        token = self._get_token(client)
        resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["username"] == "meuser"

    def test_me_without_token_returns_401(self, client):
        """토큰 없이 /auth/me 호출 시 401 반환"""
        resp = client.get("/auth/me")
        assert resp.status_code == 401

    def test_me_with_invalid_token_returns_401(self, client):
        """잘못된 토큰으로 /auth/me 호출 시 401 반환"""
        resp = client.get("/auth/me", headers={"Authorization": "Bearer invalid.token"})
        assert resp.status_code == 401
