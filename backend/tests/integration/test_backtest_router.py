# 백테스트 라우터 통합 테스트 — TestClient + 공유 인메모리 SQLite

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
        """백테스트 작업 제출 → 202 + {run_id, message} 반환"""
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
        assert "run_id" in body
        assert "message" in body
        assert isinstance(body["run_id"], int)

    def test_submits_with_universe_size_and_top_n(self, client):
        """universe_size, top_n 파라미터 포함 제출 → 202"""
        token = _register_and_login(client)
        resp = client.post(
            "/backtest/run",
            json={
                "strategy": "volume",
                "start_date": "2023-01-01",
                "end_date": "2023-06-30",
                "universe_size": 15,
                "top_n": 3,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 202
        body = resp.json()
        assert "run_id" in body

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

    def test_universe_size_less_than_1_returns_422(self, client):
        """universe_size < 1 → 422"""
        token = _register_and_login(client)
        resp = client.post(
            "/backtest/run",
            json={
                "strategy": "momentum",
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
                "universe_size": 0,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    def test_top_n_less_than_1_returns_422(self, client):
        """top_n < 1 → 422"""
        token = _register_and_login(client)
        resp = client.post(
            "/backtest/run",
            json={
                "strategy": "momentum",
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
                "top_n": 0,
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

    def test_run_list_includes_universe_and_top_n(self, client):
        """목록에 universe_size, top_n 포함"""
        token = _register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}
        client.post("/backtest/run", json={
            "strategy": "momentum", "start_date": "2023-01-01", "end_date": "2023-12-31",
            "universe_size": 10, "top_n": 3,
        }, headers=headers)

        resp = client.get("/backtest/runs", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body[0]["universe_size"] == 10
        assert body[0]["top_n"] == 3


class TestGetRun:
    """GET /backtest/runs/{run_id} 테스트"""

    def test_returns_run_status(self, client):
        """실행 상태 조회"""
        token = _register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = client.post("/backtest/run", json={
            "strategy": "momentum", "start_date": "2023-01-01", "end_date": "2023-12-31",
        }, headers=headers)
        run_id = create_resp.json()["run_id"]

        resp = client.get(f"/backtest/runs/{run_id}", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == run_id
        assert body["status"] in ("pending", "running", "done", "failed")

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
        run_id = create_resp.json()["run_id"]

        resp = client.get(f"/backtest/runs/{run_id}", headers={"Authorization": f"Bearer {token2}"})
        assert resp.status_code == 404


class TestGetResults:
    """GET /backtest/runs/{run_id}/results 테스트"""

    def test_returns_empty_list_for_pending_run(self, client):
        """pending 상태의 실행은 빈 배열 반환"""
        token = _register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = client.post("/backtest/run", json={
            "strategy": "volume", "start_date": "2023-01-01", "end_date": "2023-12-31",
        }, headers=headers)
        run_id = create_resp.json()["run_id"]

        resp = client.get(f"/backtest/runs/{run_id}/results", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body == []

    def test_results_flat_array_structure(self, client):
        """결과가 flat array 구조 (list)인지 확인 — 타인 소유 run은 404"""
        token1 = _register_and_login(client, "flat_user1", "flat1@test.com")
        token2 = _register_and_login(client, "flat_user2", "flat2@test.com")

        # user1이 run 생성
        create_resp = client.post("/backtest/run", json={
            "strategy": "momentum", "start_date": "2023-01-01", "end_date": "2023-12-31",
        }, headers={"Authorization": f"Bearer {token1}"})
        run_id = create_resp.json()["run_id"]

        # user1은 자신의 run 결과 조회 가능 (빈 배열)
        resp = client.get(
            f"/backtest/runs/{run_id}/results",
            headers={"Authorization": f"Bearer {token1}"},
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

        # user2는 user1의 run 접근 불가
        resp2 = client.get(
            f"/backtest/runs/{run_id}/results",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert resp2.status_code == 404

    def test_returns_404_for_nonexistent_run(self, client):
        """존재하지 않는 실행 ID의 결과 조회 시 404"""
        token = _register_and_login(client)
        resp = client.get(
            "/backtest/runs/9999/results",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404
