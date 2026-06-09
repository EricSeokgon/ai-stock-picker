# 백테스트 라우터 통합 테스트 — TestClient + 공유 인메모리 SQLite
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from stock_picker.db.models import BacktestDailyResult, BacktestRun, User


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
    BacktestRun.__table__.create(bind=engine, checkfirst=True)
    BacktestDailyResult.__table__.create(bind=engine, checkfirst=True)

    app = _build_app(engine)
    with TestClient(app) as c:
        yield c

    BacktestDailyResult.__table__.drop(bind=engine, checkfirst=True)
    BacktestRun.__table__.drop(bind=engine, checkfirst=True)
    User.__table__.drop(bind=engine, checkfirst=True)


def _register_and_login(client, username="testuser", email="test@example.com", password="pass1234"):
    """회원가입 + 로그인 후 Bearer 토큰 반환"""
    client.post("/auth/register", json={
        "username": username,
        "email": email,
        "password": password,
    })
    resp = client.post("/auth/login", json={"username": username, "password": password})
    return resp.json()["access_token"]


class TestStartBacktest:
    """POST /backtest/run 테스트"""

    def test_submits_backtest_and_returns_run_id(self, client):
        """백테스트 작업 제출 → 202 + run_id 반환"""
        token = _register_and_login(client)
        resp = client.post(
            "/backtest/run",
            json={
                "strategy": "momentum",
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 202
        body = resp.json()
        assert "id" in body
        assert body["strategy"] == "momentum"
        assert body["status"] == "pending"

    def test_invalid_strategy_returns_422(self, client):
        """유효하지 않은 전략 → 422"""
        token = _register_and_login(client)
        resp = client.post(
            "/backtest/run",
            json={
                "strategy": "invalid_strategy",
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    def test_end_before_start_returns_422(self, client):
        """종료일이 시작일보다 이전 → 422"""
        token = _register_and_login(client)
        resp = client.post(
            "/backtest/run",
            json={
                "strategy": "volume",
                "start_date": "2023-12-31",
                "end_date": "2023-01-01",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    def test_requires_authentication(self, client):
        """인증 없이 제출 시 401"""
        resp = client.post(
            "/backtest/run",
            json={
                "strategy": "momentum",
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
            },
        )
        assert resp.status_code == 401


class TestListRuns:
    """GET /backtest/runs 테스트"""

    def test_returns_user_runs(self, client):
        """사용자의 백테스트 실행 목록 반환"""
        token = _register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}

        client.post("/backtest/run", json={
            "strategy": "momentum", "start_date": "2023-01-01", "end_date": "2023-06-30",
        }, headers=headers)
        client.post("/backtest/run", json={
            "strategy": "volume", "start_date": "2023-07-01", "end_date": "2023-12-31",
        }, headers=headers)

        resp = client.get("/backtest/runs", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 2

    def test_returns_empty_list_when_no_runs(self, client):
        """실행 기록 없을 때 빈 목록 반환"""
        token = _register_and_login(client)
        resp = client.get("/backtest/runs", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_only_own_runs_visible(self, client):
        """다른 사용자의 실행 기록은 보이지 않음"""
        token1 = _register_and_login(client, "user1", "u1@test.com")
        token2 = _register_and_login(client, "user2", "u2@test.com")

        client.post("/backtest/run", json={
            "strategy": "momentum", "start_date": "2023-01-01", "end_date": "2023-12-31",
        }, headers={"Authorization": f"Bearer {token1}"})

        resp = client.get("/backtest/runs", headers={"Authorization": f"Bearer {token2}"})
        assert resp.status_code == 200
        assert resp.json() == []


class TestGetRun:
    """GET /backtest/runs/{run_id} 테스트"""

    def test_returns_run_status(self, client):
        """실행 상태 조회"""
        token = _register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = client.post("/backtest/run", json={
            "strategy": "momentum", "start_date": "2023-01-01", "end_date": "2023-12-31",
        }, headers=headers)
        run_id = create_resp.json()["id"]

        resp = client.get(f"/backtest/runs/{run_id}", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == run_id
        assert body["status"] in ("pending", "running", "done", "error")

    def test_returns_404_for_nonexistent_run(self, client):
        """존재하지 않는 실행 ID 조회 시 404"""
        token = _register_and_login(client)
        resp = client.get("/backtest/runs/9999", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 404

    def test_cannot_access_other_users_run(self, client):
        """다른 사용자의 실행 기록 접근 불가"""
        token1 = _register_and_login(client, "user1", "u1@test.com")
        token2 = _register_and_login(client, "user2", "u2@test.com")

        create_resp = client.post("/backtest/run", json={
            "strategy": "momentum", "start_date": "2023-01-01", "end_date": "2023-12-31",
        }, headers={"Authorization": f"Bearer {token1}"})
        run_id = create_resp.json()["id"]

        resp = client.get(f"/backtest/runs/{run_id}", headers={"Authorization": f"Bearer {token2}"})
        assert resp.status_code == 404


class TestGetResults:
    """GET /backtest/runs/{run_id}/results 테스트"""

    def test_returns_empty_results_for_pending_run(self, client):
        """pending 상태의 실행은 빈 결과 반환"""
        token = _register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = client.post("/backtest/run", json={
            "strategy": "volume", "start_date": "2023-01-01", "end_date": "2023-12-31",
        }, headers=headers)
        run_id = create_resp.json()["id"]

        resp = client.get(f"/backtest/runs/{run_id}/results", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["items"] == []
        assert body["page"] == 1

    def test_pagination_params(self, client):
        """페이지네이션 파라미터 검증"""
        token = _register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = client.post("/backtest/run", json={
            "strategy": "momentum", "start_date": "2023-01-01", "end_date": "2023-12-31",
        }, headers=headers)
        run_id = create_resp.json()["id"]

        resp = client.get(
            f"/backtest/runs/{run_id}/results?page=2&page_size=10",
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["page"] == 2
        assert body["page_size"] == 10

    def test_returns_404_for_nonexistent_run(self, client):
        """존재하지 않는 실행 ID의 결과 조회 시 404"""
        token = _register_and_login(client)
        resp = client.get(
            "/backtest/runs/9999/results",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404
