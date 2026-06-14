# 스크리너 라우터 유닛 테스트 — TDD RED 단계
# REQ-SCR-API-001~005
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from stock_picker.screener.schemas import ScreenerResult


def _make_app_with_screener():
    """스크리너 라우터만 포함한 미니 FastAPI 앱"""
    from fastapi import FastAPI
    from stock_picker.screener.router import router as screener_router

    app = FastAPI()
    app.include_router(screener_router)
    return app


class TestRunScreenerEndpoint:
    """POST /screener/run 엔드포인트 (REQ-SCR-API-001)"""

    def test_run_screener_returns_200_with_results(self):
        """스크리너 실행 — 200 OK + 결과 목록"""
        mock_result = ScreenerResult(
            krx_code="005930",
            name="삼성전자",
            sector="전기전자",
            current_price=71000.0,
            change_pct=-0.84,
            per=9.2,
            pbr=1.1,
            roe=12.5,
            market_cap=423_000_000_000_000,
            dividend_yield=3.1,
            week52_position=55.0,
        )

        with patch("stock_picker.screener.router.run_screener") as mock_run, \
             patch("stock_picker.screener.router.get_db_session") as mock_db:
            mock_run.return_value = [mock_result]
            mock_db.return_value = MagicMock()

            app = _make_app_with_screener()

            # get_db_session 의존성 override
            from stock_picker.auth.dependencies import get_db_session
            app.dependency_overrides[get_db_session] = lambda: MagicMock()

            client = TestClient(app)
            resp = client.post(
                "/screener/run",
                json={"filters": {"per": {"max": 10.0}}},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "results" in data
            assert "total" in data

    def test_run_screener_min_greater_than_max_returns_422(self):
        """min > max 필터 → 422 Unprocessable Entity (REQ-SCR-006)"""
        app = _make_app_with_screener()
        from stock_picker.auth.dependencies import get_db_session
        app.dependency_overrides[get_db_session] = lambda: MagicMock()

        client = TestClient(app)
        resp = client.post(
            "/screener/run",
            json={"filters": {"per": {"min": 20.0, "max": 5.0}}},
        )
        assert resp.status_code == 422

    def test_run_screener_empty_filters_returns_all(self):
        """필터 없이 실행 — 전체 스냅샷 반환 (REQ-SCR-005)"""
        with patch("stock_picker.screener.router.run_screener") as mock_run, \
             patch("stock_picker.screener.router.get_db_session"):
            mock_run.return_value = []

            app = _make_app_with_screener()
            from stock_picker.auth.dependencies import get_db_session
            app.dependency_overrides[get_db_session] = lambda: MagicMock()

            client = TestClient(app)
            resp = client.post("/screener/run", json={})
            assert resp.status_code == 200


class TestPresetEndpoints:
    """프리셋 CRUD 엔드포인트 (REQ-SCR-API-002~005)"""

    def _make_authed_app(self, mock_user):
        """인증 의존성을 mock한 앱"""
        app = _make_app_with_screener()
        from stock_picker.auth.dependencies import get_current_user, get_db_session
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db_session] = lambda: MagicMock()
        return app

    def test_list_presets_requires_auth(self):
        """GET /screener/presets — 인증 없으면 401/403 (REQ-SCR-API-005)"""
        app = _make_app_with_screener()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/screener/presets")
        assert resp.status_code in (401, 403)

    def test_list_presets_returns_user_presets(self):
        """GET /screener/presets — 인증된 사용자 프리셋 반환 (REQ-SCR-API-002)"""
        mock_user = MagicMock()
        mock_user.id = 1

        with patch("stock_picker.screener.router.list_presets") as mock_list:
            mock_list.return_value = []

            app = self._make_authed_app(mock_user)
            client = TestClient(app)
            resp = client.get("/screener/presets")
            assert resp.status_code == 200
            assert isinstance(resp.json(), list)

    def test_create_preset_success(self):
        """POST /screener/presets — 프리셋 저장 성공 (REQ-SCR-API-003)"""
        from stock_picker.db.models import ScreenerPreset
        mock_user = MagicMock()
        mock_user.id = 1

        mock_preset = MagicMock(spec=ScreenerPreset)
        mock_preset.id = 1
        mock_preset.user_id = 1
        mock_preset.name = "가치투자"
        mock_preset.criteria = '{"per": {"max": 10}}'

        with patch("stock_picker.screener.router.create_preset") as mock_create:
            mock_create.return_value = mock_preset

            app = self._make_authed_app(mock_user)
            client = TestClient(app)
            resp = client.post(
                "/screener/presets",
                json={"name": "가치투자", "criteria": {}},
            )
            assert resp.status_code in (200, 201)

    def test_create_preset_exceeds_limit_returns_409(self):
        """5개 초과 시 409 (REQ-SCR-PRESET-002)"""
        mock_user = MagicMock()
        mock_user.id = 1

        with patch("stock_picker.screener.router.create_preset") as mock_create:
            mock_create.side_effect = HTTPException(status_code=409, detail="최대 5개")

            app = self._make_authed_app(mock_user)
            client = TestClient(app)
            resp = client.post(
                "/screener/presets",
                json={"name": "초과 필터", "criteria": {}},
            )
            assert resp.status_code == 409

    def test_delete_preset_success(self):
        """DELETE /screener/presets/{id} — 삭제 성공 204 (REQ-SCR-API-004)"""
        mock_user = MagicMock()
        mock_user.id = 1

        with patch("stock_picker.screener.router.delete_preset"):
            app = self._make_authed_app(mock_user)
            client = TestClient(app)
            resp = client.delete("/screener/presets/1")
            assert resp.status_code == 204

    def test_delete_preset_not_owner_returns_403(self):
        """타인 프리셋 삭제 → 403 (REQ-SCR-PRESET-005)"""
        mock_user = MagicMock()
        mock_user.id = 1

        with patch("stock_picker.screener.router.delete_preset") as mock_del:
            mock_del.side_effect = HTTPException(status_code=403, detail="권한 없음")

            app = self._make_authed_app(mock_user)
            client = TestClient(app)
            resp = client.delete("/screener/presets/99")
            assert resp.status_code == 403
