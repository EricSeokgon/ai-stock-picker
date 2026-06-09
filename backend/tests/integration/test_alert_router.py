# 가격 알림 라우터 통합 테스트 — TestClient + 인메모리 SQLite
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from stock_picker.db.models import EmailSubscription, User, WatchlistAlert


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
    # SQLite 호환 테이블 생성
    User.__table__.create(bind=engine, checkfirst=True)
    WatchlistAlert.__table__.create(bind=engine, checkfirst=True)
    EmailSubscription.__table__.create(bind=engine, checkfirst=True)

    app = _build_app(engine)
    with TestClient(app) as c:
        yield c

    WatchlistAlert.__table__.drop(bind=engine, checkfirst=True)
    EmailSubscription.__table__.drop(bind=engine, checkfirst=True)
    User.__table__.drop(bind=engine, checkfirst=True)


def _register_and_login(
    client,
    username="alertuser",
    email="alert@test.com",
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


class TestCreateAlert:
    """POST /watchlist/alerts"""

    def test_creates_alert_returns_201(self, client):
        """알림 생성 성공 — 201 반환"""
        token = _register_and_login(client)
        resp = client.post(
            "/watchlist/alerts",
            json={"krx_code": "005930", "target_price": 80000.0, "direction": "above"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["krx_code"] == "005930"
        assert data["target_price"] == 80000.0
        assert data["direction"] == "above"
        assert data["is_active"] is True
        assert "id" in data

    def test_unauthenticated_returns_401(self, client):
        """인증 없으면 401"""
        resp = client.post(
            "/watchlist/alerts",
            json={"krx_code": "005930", "target_price": 80000.0, "direction": "above"},
        )
        assert resp.status_code == 401

    def test_invalid_direction_returns_422(self, client):
        """잘못된 direction 값 — 422"""
        token = _register_and_login(client)
        resp = client.post(
            "/watchlist/alerts",
            json={"krx_code": "005930", "target_price": 80000.0, "direction": "sideways"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    def test_invalid_target_price_returns_422(self, client):
        """음수 목표가 — 422"""
        token = _register_and_login(client)
        resp = client.post(
            "/watchlist/alerts",
            json={"krx_code": "005930", "target_price": -100.0, "direction": "above"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422


class TestListAlerts:
    """GET /watchlist/alerts"""

    def test_returns_user_alerts(self, client):
        """사용자의 알림 목록 반환"""
        token = _register_and_login(client)
        # 알림 2개 등록
        for krx in ["005930", "000660"]:
            client.post(
                "/watchlist/alerts",
                json={"krx_code": krx, "target_price": 80000.0, "direction": "above"},
                headers={"Authorization": f"Bearer {token}"},
            )

        resp = client.get(
            "/watchlist/alerts",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_unauthenticated_returns_401(self, client):
        """인증 없으면 401"""
        resp = client.get("/watchlist/alerts")
        assert resp.status_code == 401

    def test_returns_only_own_alerts(self, client):
        """다른 사용자의 알림은 보이지 않음"""
        token1 = _register_and_login(client, "user1", "user1@test.com")
        token2 = _register_and_login(client, "user2", "user2@test.com")

        # user1 알림 등록
        client.post(
            "/watchlist/alerts",
            json={"krx_code": "005930", "target_price": 80000.0, "direction": "above"},
            headers={"Authorization": f"Bearer {token1}"},
        )

        # user2 조회 — user1 알림 안 보여야 함
        resp = client.get(
            "/watchlist/alerts",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert resp.status_code == 200
        assert resp.json() == []


class TestDeleteAlert:
    """DELETE /watchlist/alerts/{id}"""

    def test_deletes_own_alert_returns_204(self, client):
        """본인 알림 삭제 — 204"""
        token = _register_and_login(client)
        create_resp = client.post(
            "/watchlist/alerts",
            json={"krx_code": "005930", "target_price": 80000.0, "direction": "above"},
            headers={"Authorization": f"Bearer {token}"},
        )
        alert_id = create_resp.json()["id"]

        resp = client.delete(
            f"/watchlist/alerts/{alert_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204

    def test_delete_nonexistent_returns_404(self, client):
        """존재하지 않는 알림 삭제 — 404"""
        token = _register_and_login(client)
        resp = client.delete(
            "/watchlist/alerts/99999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    def test_delete_other_users_alert_returns_403(self, client):
        """다른 사용자의 알림 삭제 — 403"""
        token1 = _register_and_login(client, "owner1", "owner1@test.com")
        token2 = _register_and_login(client, "other1", "other1@test.com")

        create_resp = client.post(
            "/watchlist/alerts",
            json={"krx_code": "005930", "target_price": 80000.0, "direction": "above"},
            headers={"Authorization": f"Bearer {token1}"},
        )
        alert_id = create_resp.json()["id"]

        # token2(다른 사용자)가 삭제 시도
        resp = client.delete(
            f"/watchlist/alerts/{alert_id}",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert resp.status_code == 403

    def test_unauthenticated_delete_returns_401(self, client):
        """인증 없이 삭제 — 401"""
        resp = client.delete("/watchlist/alerts/1")
        assert resp.status_code == 401
