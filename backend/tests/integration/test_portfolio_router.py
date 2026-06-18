# 포트폴리오 라우터 통합 테스트 — TestClient + 공유 인메모리 SQLite
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from stock_picker.db.models import Portfolio, PortfolioHolding, User


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
    # SQLite 호환 테이블만 생성 (ARRAY 타입 제외)
    User.__table__.create(bind=engine, checkfirst=True)
    Portfolio.__table__.create(bind=engine, checkfirst=True)
    PortfolioHolding.__table__.create(bind=engine, checkfirst=True)

    app = _build_app(engine)
    with TestClient(app) as c:
        yield c

    PortfolioHolding.__table__.drop(bind=engine, checkfirst=True)
    Portfolio.__table__.drop(bind=engine, checkfirst=True)
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


class TestCreatePortfolio:
    """POST /portfolios 테스트"""

    def test_creates_portfolio_for_authenticated_user(self, client):
        """인증된 사용자의 포트폴리오 생성"""
        token = _register_and_login(client)
        resp = client.post(
            "/portfolios",
            json={"name": "내 첫 포트폴리오"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "내 첫 포트폴리오"
        assert "id" in body
        assert "user_id" in body

    def test_requires_authentication(self, client):
        """인증 없이 포트폴리오 생성 시 401"""
        resp = client.post("/portfolios", json={"name": "무인증 포트폴리오"})
        assert resp.status_code == 401


class TestListPortfolios:
    """GET /portfolios 테스트"""

    def test_returns_user_portfolios(self, client):
        """사용자의 포트폴리오 목록 반환"""
        token = _register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}
        client.post("/portfolios", json={"name": "포트폴리오A"}, headers=headers)
        client.post("/portfolios", json={"name": "포트폴리오B"}, headers=headers)

        resp = client.get("/portfolios", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 2
        names = {p["name"] for p in body}
        assert names == {"포트폴리오A", "포트폴리오B"}

    def test_returns_empty_list_when_no_portfolios(self, client):
        """포트폴리오 없을 때 빈 목록 반환"""
        token = _register_and_login(client)
        resp = client.get("/portfolios", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json() == []


class TestAddHolding:
    """POST /portfolios/{id}/holdings 테스트"""

    def _create_portfolio(self, client, token) -> int:
        resp = client.post(
            "/portfolios",
            json={"name": "홀딩 테스트"},
            headers={"Authorization": f"Bearer {token}"},
        )
        return resp.json()["id"]

    def test_adds_holding_to_portfolio(self, client):
        """포트폴리오에 보유 종목 추가"""
        token = _register_and_login(client)
        portfolio_id = self._create_portfolio(client, token)

        resp = client.post(
            f"/portfolios/{portfolio_id}/holdings",
            json={"krx_code": "005930", "quantity": 10, "avg_buy_price": "70000.00"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["krx_code"] == "005930"
        assert body["quantity"] == 10

    def test_returns_404_for_wrong_portfolio(self, client):
        """존재하지 않는 포트폴리오에 종목 추가 시 404"""
        token = _register_and_login(client)
        resp = client.post(
            "/portfolios/9999/holdings",
            json={"krx_code": "005930", "quantity": 1, "avg_buy_price": "1000.00"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    def test_cannot_add_to_other_users_portfolio(self, client):
        """다른 사용자의 포트폴리오에 종목 추가 불가"""
        token1 = _register_and_login(client, "user1", "u1@test.com")
        token2 = _register_and_login(client, "user2", "u2@test.com")

        # user1의 포트폴리오 생성
        portfolio_id = self._create_portfolio(client, token1)

        # user2가 user1의 포트폴리오에 추가 시도
        resp = client.post(
            f"/portfolios/{portfolio_id}/holdings",
            json={"krx_code": "000660", "quantity": 5, "avg_buy_price": "100000.00"},
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert resp.status_code == 404


class TestRemoveHolding:
    """DELETE /portfolios/{id}/holdings/{holding_id} 테스트"""

    def _setup(self, client, token) -> tuple[int, int]:
        """포트폴리오 + 보유 종목 생성 후 ID 반환"""
        portfolio_resp = client.post(
            "/portfolios",
            json={"name": "삭제 테스트"},
            headers={"Authorization": f"Bearer {token}"},
        )
        portfolio_id = portfolio_resp.json()["id"]

        holding_resp = client.post(
            f"/portfolios/{portfolio_id}/holdings",
            json={"krx_code": "005380", "quantity": 3, "avg_buy_price": "200000.00"},
            headers={"Authorization": f"Bearer {token}"},
        )
        holding_id = holding_resp.json()["id"]
        return portfolio_id, holding_id

    def test_removes_holding(self, client):
        """보유 종목 삭제 → 204"""
        token = _register_and_login(client)
        portfolio_id, holding_id = self._setup(client, token)

        resp = client.delete(
            f"/portfolios/{portfolio_id}/holdings/{holding_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204

    def test_returns_404_for_nonexistent_holding(self, client):
        """존재하지 않는 보유 종목 삭제 시 404"""
        token = _register_and_login(client)
        portfolio_resp = client.post(
            "/portfolios",
            json={"name": "테스트"},
            headers={"Authorization": f"Bearer {token}"},
        )
        portfolio_id = portfolio_resp.json()["id"]

        resp = client.delete(
            f"/portfolios/{portfolio_id}/holdings/9999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


class TestGetPerformance:
    """GET /portfolios/{id}/performance 테스트"""

    def test_returns_performance_for_portfolio(self, client):
        """포트폴리오 성과 데이터 반환"""
        token = _register_and_login(client)
        portfolio_resp = client.post(
            "/portfolios",
            json={"name": "성과 테스트"},
            headers={"Authorization": f"Bearer {token}"},
        )
        portfolio_id = portfolio_resp.json()["id"]
        client.post(
            f"/portfolios/{portfolio_id}/holdings",
            json={"krx_code": "005930", "quantity": 10, "avg_buy_price": "70000.00"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # _get_current_price를 75000으로 mocking
        with patch("stock_picker.portfolio.service._get_current_price", return_value=75000.0):
            resp = client.get(
                f"/portfolios/{portfolio_id}/performance",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "holdings" in body
        assert "total_invested" in body
        assert "total_current" in body
        assert "total_return_pct" in body

    def test_returns_404_for_unknown_portfolio(self, client):
        """존재하지 않는 포트폴리오 성과 조회 시 404"""
        token = _register_and_login(client)
        resp = client.get(
            "/portfolios/9999/performance",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


# ──────────────────────────────────────────────────────────────
# SPEC-STOCK-027 리스크 분석 통합 테스트 (T3-1)
# ──────────────────────────────────────────────────────────────

def _make_mock_risk_result():
    """테스트용 결정론적 리스크 분석 결과"""
    from datetime import datetime

    from stock_picker.portfolio.schemas import HoldingVolatility, RiskAnalysisResult

    return RiskAnalysisResult(
        correlation_matrix={
            "005930": {"005930": 1.0, "000660": 0.45},
            "000660": {"005930": 0.45, "000660": 1.0},
        },
        holdings_volatility=[
            HoldingVolatility(
                krx_code="005930",
                name="삼성전자",
                annualized_volatility_pct=28.5,
                price_data_days=85,
            ),
            HoldingVolatility(
                krx_code="000660",
                name="SK하이닉스",
                annualized_volatility_pct=35.2,
                price_data_days=85,
            ),
        ],
        portfolio_volatility_pct=22.3,
        diversification_benefit_pct=8.7,
        period_days=90,
        calculated_at=datetime(2026, 6, 18, 0, 0, 0),
    )


class TestRiskAnalysis:
    """GET /portfolios/{id}/risk-analysis 통합 테스트 (SPEC-STOCK-027)"""

    def test_risk_analysis_success(self, client):
        """2개 이상 보유 종목으로 리스크 분석 성공 시 200과 필수 키 반환"""
        token = _register_and_login(client)
        portfolio_resp = client.post(
            "/portfolios",
            json={"name": "리스크 분석 테스트"},
            headers={"Authorization": f"Bearer {token}"},
        )
        portfolio_id = portfolio_resp.json()["id"]

        # 2개 보유 종목 추가
        for krx_code, price in [("005930", "70000.00"), ("000660", "120000.00")]:
            client.post(
                f"/portfolios/{portfolio_id}/holdings",
                json={"krx_code": krx_code, "quantity": 10, "avg_buy_price": price},
                headers={"Authorization": f"Bearer {token}"},
            )

        mock_result = _make_mock_risk_result()

        with patch(
            "stock_picker.portfolio.router.calculate_risk_analysis",
            return_value=mock_result,
        ):
            resp = client.get(
                f"/portfolios/{portfolio_id}/risk-analysis?period=90",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "correlation_matrix" in body
        assert "holdings_volatility" in body
        assert "portfolio_volatility_pct" in body
        assert "diversification_benefit_pct" in body
        assert "period_days" in body
        assert "calculated_at" in body
        assert body["period_days"] == 90

    def test_risk_analysis_invalid_period_422(self, client):
        """허용되지 않은 period 값(45)은 422를 반환해야 한다"""
        token = _register_and_login(client)
        portfolio_resp = client.post(
            "/portfolios",
            json={"name": "422 테스트"},
            headers={"Authorization": f"Bearer {token}"},
        )
        portfolio_id = portfolio_resp.json()["id"]

        resp = client.get(
            f"/portfolios/{portfolio_id}/risk-analysis?period=45",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    def test_risk_analysis_fewer_than_two_holdings_400(self, client):
        """보유 종목 1개(FDR 실패 포함)는 400을 반환해야 한다"""
        from fastapi import HTTPException

        token = _register_and_login(client)
        portfolio_resp = client.post(
            "/portfolios",
            json={"name": "400 테스트"},
            headers={"Authorization": f"Bearer {token}"},
        )
        portfolio_id = portfolio_resp.json()["id"]

        # 1개만 추가
        client.post(
            f"/portfolios/{portfolio_id}/holdings",
            json={"krx_code": "005930", "quantity": 5, "avg_buy_price": "70000.00"},
            headers={"Authorization": f"Bearer {token}"},
        )

        with patch(
            "stock_picker.portfolio.router.calculate_risk_analysis",
            side_effect=HTTPException(status_code=400, detail="유효 보유 종목 부족"),
        ):
            resp = client.get(
                f"/portfolios/{portfolio_id}/risk-analysis",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 400
