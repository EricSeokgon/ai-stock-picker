# 이메일 구독 라우터 통합 테스트 — TestClient + 인메모리 SQLite
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from stock_picker.db.models import EmailSubscription, User


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
    User.__table__.create(bind=engine, checkfirst=True)
    EmailSubscription.__table__.create(bind=engine, checkfirst=True)

    app = _build_app(engine)
    with TestClient(app) as c:
        yield c

    EmailSubscription.__table__.drop(bind=engine, checkfirst=True)
    User.__table__.drop(bind=engine, checkfirst=True)


def _register_and_login(
    client,
    username="emailuser",
    email="emailuser@test.com",
    password="pass1234",
) -> str:
    """회원가입 + 로그인 후 Bearer 토큰 반환"""
    client.post(
        "/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    resp = client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )
    return resp.json()["access_token"]


class TestSubscribeEmail:
    """POST /notifications/email"""

    def test_subscribe_creates_and_returns(self, client):
        """이메일 구독 등록 성공"""
        token = _register_and_login(client)
        resp = client.post(
            "/notifications/email",
            json={"email": "subscribe@example.com"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "subscribe@example.com"
        assert data["is_active"] is True

    def test_resubscribe_reactivates(self, client):
        """재구독 시 기존 구독 재활성화"""
        token = _register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}

        # 최초 구독
        client.post("/notifications/email", json={"email": "first@example.com"}, headers=headers)
        # 구독 해지
        client.delete("/notifications/email", headers=headers)
        # 재구독
        resp = client.post(
            "/notifications/email",
            json={"email": "second@example.com"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is True
        assert resp.json()["email"] == "second@example.com"

    def test_invalid_email_returns_422(self, client):
        """잘못된 이메일 형식 — 422"""
        token = _register_and_login(client)
        resp = client.post(
            "/notifications/email",
            json={"email": "not-an-email"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    def test_unauthenticated_returns_401(self, client):
        """인증 없으면 401"""
        resp = client.post(
            "/notifications/email",
            json={"email": "no@auth.com"},
        )
        assert resp.status_code == 401


class TestUnsubscribeEmail:
    """DELETE /notifications/email"""

    def test_unsubscribe_returns_message(self, client):
        """이메일 구독 해지 — 200 + 메시지"""
        token = _register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}

        # 먼저 구독
        client.post(
            "/notifications/email",
            json={"email": "tosub@example.com"},
            headers=headers,
        )

        resp = client.delete("/notifications/email", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["message"] == "구독이 해지되었습니다."

    def test_unsubscribe_when_not_subscribed_returns_200(self, client):
        """구독 없이 해지해도 200 반환 (멱등성)"""
        token = _register_and_login(client)
        resp = client.delete(
            "/notifications/email",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    def test_unauthenticated_returns_401(self, client):
        """인증 없으면 401"""
        resp = client.delete("/notifications/email")
        assert resp.status_code == 401
