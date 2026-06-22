# 포트폴리오 백테스팅 라우터 통합 테스트 (SPEC-STOCK-029)
# TestClient + 인메모리 SQLite + FDR/Redis 모킹
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
    client.post("/auth/register", json={"username": username, "email": email, "password": password})
    resp = client.post("/auth/login", json={"username": username, "password": password})
    return resp.json()["access_token"]


def _create_portfolio(client, token, name="테스트 포트폴리오") -> int:
    """포트폴리오 생성 후 ID 반환"""
    resp = client.post(
        "/portfolios",
        json={"name": name},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _add_holding(client, token, portfolio_id: int, krx_code: str, market: str = "KRX", currency: str = "KRW"):
    """보유 종목 추가"""
    resp = client.post(
        f"/portfolios/{portfolio_id}/holdings",
        json={
            "krx_code": krx_code,
            "quantity": 10,
            "avg_buy_price": 10000.0,
            "market": market,
            "currency": currency,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201


# 모킹용 가격 데이터
_MOCK_PRICES_A = [
    {"date": "2024-01-02", "close": 100.0},
    {"date": "2024-01-03", "close": 105.0},
    {"date": "2024-01-04", "close": 103.0},
    {"date": "2024-01-05", "close": 108.0},
]

_MOCK_PRICES_B = [
    {"date": "2024-01-02", "close": 50.0},
    {"date": "2024-01-03", "close": 52.0},
    {"date": "2024-01-04", "close": 51.0},
    {"date": "2024-01-05", "close": 53.0},
]


class TestBacktestPortfolio:
    """POST /portfolios/{id}/backtest 통합 테스트"""

    def test_happy_path_returns_200_with_backtest_result(self, client):
        """유효한 요청 → 200 및 BacktestResult 반환 (AC-1)"""
        token = _register_and_login(client)
        portfolio_id = _create_portfolio(client, token)
        _add_holding(client, token, portfolio_id, "005930")

        with patch(
            "stock_picker.portfolio.backtest._fetch_price_series_sync",
            return_value=_MOCK_PRICES_A,
        ):
            resp = client.post(
                f"/portfolios/{portfolio_id}/backtest",
                json={"start_date": "2024-01-01", "end_date": "2024-03-31"},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "daily" in body
        assert "mdd" in body
        assert "sharpe_ratio" in body
        assert "total_return" in body
        assert "period_days" in body
        assert "excluded_tickers" in body
        assert "used_tickers" in body
        assert "disclaimer" in body

    def test_date_inversion_returns_422(self, client):
        """종료일 < 시작일 → 422 (AC-2)"""
        token = _register_and_login(client)
        portfolio_id = _create_portfolio(client, token)

        resp = client.post(
            f"/portfolios/{portfolio_id}/backtest",
            json={"start_date": "2024-06-30", "end_date": "2024-01-01"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    def test_start_equals_end_returns_422(self, client):
        """시작일 == 종료일 → 422 (AC-2)"""
        token = _register_and_login(client)
        portfolio_id = _create_portfolio(client, token)

        resp = client.post(
            f"/portfolios/{portfolio_id}/backtest",
            json={"start_date": "2024-01-01", "end_date": "2024-01-01"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    def test_portfolio_not_found_returns_404(self, client):
        """존재하지 않는 포트폴리오 → 404 (AC-11)"""
        token = _register_and_login(client)

        with patch(
            "stock_picker.portfolio.backtest._fetch_price_series_sync",
            return_value=_MOCK_PRICES_A,
        ):
            resp = client.post(
                "/portfolios/99999/backtest",
                json={"start_date": "2024-01-01", "end_date": "2024-03-31"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 404

    def test_unauthorized_returns_401(self, client):
        """인증 없이 요청 → 401"""
        resp = client.post(
            "/portfolios/1/backtest",
            json={"start_date": "2024-01-01", "end_date": "2024-03-31"},
        )
        assert resp.status_code == 401

    def test_empty_portfolio_returns_400(self, client):
        """보유 종목 없는 포트폴리오 → 400 (REQ-PBT-021)"""
        token = _register_and_login(client)
        portfolio_id = _create_portfolio(client, token)
        # 종목 추가 없이 바로 백테스팅

        resp = client.post(
            f"/portfolios/{portfolio_id}/backtest",
            json={"start_date": "2024-01-01", "end_date": "2024-03-31"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400

    def test_single_ticker_result_matches_price_ratio(self, client):
        """단일 종목 백테스트 — 총 수익률 = 종가 비율 - 1 (AC-3)"""
        token = _register_and_login(client)
        portfolio_id = _create_portfolio(client, token)
        _add_holding(client, token, portfolio_id, "005930")

        prices = [
            {"date": "2024-01-02", "close": 100.0},
            {"date": "2024-01-03", "close": 120.0},
        ]

        with patch(
            "stock_picker.portfolio.backtest._fetch_price_series_sync",
            return_value=prices,
        ):
            resp = client.post(
                f"/portfolios/{portfolio_id}/backtest",
                json={"start_date": "2024-01-01", "end_date": "2024-01-31"},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        body = resp.json()
        # 총 수익률 = 120/100 - 1 = 0.2
        assert abs(body["total_return"] - 0.2) < 1e-4

    def test_all_tickers_fail_returns_422(self, client):
        """전 종목 FDR 실패 → 422 (REQ-PBT-022)"""
        token = _register_and_login(client)
        portfolio_id = _create_portfolio(client, token)
        _add_holding(client, token, portfolio_id, "INVALID1")

        with patch(
            "stock_picker.portfolio.backtest._fetch_price_series_sync",
            return_value=[],
        ):
            resp = client.post(
                f"/portfolios/{portfolio_id}/backtest",
                json={"start_date": "2024-01-01", "end_date": "2024-03-31"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 422

    def test_mdd_is_non_positive(self, client):
        """MDD는 항상 0 이하 (AC-9)"""
        token = _register_and_login(client)
        portfolio_id = _create_portfolio(client, token)
        _add_holding(client, token, portfolio_id, "005930")

        with patch(
            "stock_picker.portfolio.backtest._fetch_price_series_sync",
            return_value=_MOCK_PRICES_A,
        ):
            resp = client.post(
                f"/portfolios/{portfolio_id}/backtest",
                json={"start_date": "2024-01-01", "end_date": "2024-03-31"},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        assert resp.json()["mdd"] <= 0.0

    def test_disclaimer_contains_investment_warning(self, client):
        """응답에 투자 면책 문구 포함 (REQ-PBT-NFR-003)"""
        token = _register_and_login(client)
        portfolio_id = _create_portfolio(client, token)
        _add_holding(client, token, portfolio_id, "005930")

        with patch(
            "stock_picker.portfolio.backtest._fetch_price_series_sync",
            return_value=_MOCK_PRICES_A,
        ):
            resp = client.post(
                f"/portfolios/{portfolio_id}/backtest",
                json={"start_date": "2024-01-01", "end_date": "2024-03-31"},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        disclaimer = resp.json()["disclaimer"]
        assert "투자 권유가 아니며 정보 제공 목적" in disclaimer

    def test_cross_user_isolation(self, client):
        """타사용자의 포트폴리오 접근 → 404 (보안)"""
        token_a = _register_and_login(client, "userA", "a@test.com")
        token_b = _register_and_login(client, "userB", "b@test.com")

        # userA의 포트폴리오 생성
        portfolio_id = _create_portfolio(client, token_a)
        _add_holding(client, token_a, portfolio_id, "005930")

        # userB가 userA의 포트폴리오에 백테스팅 시도
        with patch(
            "stock_picker.portfolio.backtest._fetch_price_series_sync",
            return_value=_MOCK_PRICES_A,
        ):
            resp = client.post(
                f"/portfolios/{portfolio_id}/backtest",
                json={"start_date": "2024-01-01", "end_date": "2024-03-31"},
                headers={"Authorization": f"Bearer {token_b}"},
            )

        assert resp.status_code == 404
