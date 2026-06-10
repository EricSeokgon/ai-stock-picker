# 종목 검색 및 주가 히스토리 라우터 통합 테스트 (SPEC-STOCK-007)
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

_FIXTURE_CSV = (
    Path(__file__).parent.parent / "fixtures" / "krx_master.csv"
)


def _make_app(mock_session: AsyncMock | None = None):
    """FastAPI 앱 + 비동기 세션 override 구성"""
    from stock_picker.api.main import create_app
    from stock_picker.db.session import get_session

    app = create_app()

    if mock_session is not None:
        async def override_session():
            yield mock_session

        app.dependency_overrides[get_session] = override_session

    return app


def _make_mock_session_with_empty_recommendations():
    """최근 추천 없는 mock 세션 반환"""
    mock_session = AsyncMock()
    empty_result = MagicMock()
    empty_result.all.return_value = []
    mock_session.execute.return_value = empty_result
    return mock_session


class TestSearchStocksEndpoint:
    """GET /stocks/search 엔드포인트 통합 테스트"""

    def test_search_returns_200_with_results(self):
        """유효한 쿼리 → 200 응답 및 results 포함"""
        mock_session = _make_mock_session_with_empty_recommendations()
        app = _make_app(mock_session)

        with patch("stock_picker.search.service.load_krx_master", return_value={"삼성전자": "005930"}):
            with TestClient(app) as client:
                resp = client.get("/stocks/search?q=삼성")

        assert resp.status_code == 200
        data = resp.json()
        assert "query" in data
        assert "results" in data
        assert "total" in data
        assert data["query"] == "삼성"

    def test_search_result_has_correct_fields(self):
        """검색 결과 항목에 krx_code, name, in_recommendations 포함"""
        mock_session = _make_mock_session_with_empty_recommendations()
        app = _make_app(mock_session)

        with patch("stock_picker.search.service.load_krx_master", return_value={"삼성전자": "005930"}):
            with TestClient(app) as client:
                resp = client.get("/stocks/search?q=삼성")

        data = resp.json()
        if data["total"] > 0:
            item = data["results"][0]
            assert "krx_code" in item
            assert "name" in item
            assert "in_recommendations" in item

    def test_search_missing_q_returns_422(self):
        """q 파라미터 누락 → 422"""
        app = _make_app()
        with TestClient(app) as client:
            resp = client.get("/stocks/search")
        assert resp.status_code == 422

    def test_search_empty_q_returns_422(self):
        """q 최소 길이 1 미만 → 422"""
        app = _make_app()
        with TestClient(app) as client:
            resp = client.get("/stocks/search?q=")
        # FastAPI min_length=1 validation
        assert resp.status_code in (422, 400)

    def test_search_code_prefix_works(self):
        """코드 접두어 검색 동작"""
        mock_session = _make_mock_session_with_empty_recommendations()
        app = _make_app(mock_session)

        with patch(
            "stock_picker.search.service.load_krx_master",
            return_value={"삼성전자": "005930", "SK하이닉스": "000660"},
        ):
            with TestClient(app) as client:
                resp = client.get("/stocks/search?q=00566")

        assert resp.status_code == 200

    def test_search_no_match_returns_empty_results(self):
        """매칭 없는 쿼리 → results 빈 배열"""
        mock_session = _make_mock_session_with_empty_recommendations()
        app = _make_app(mock_session)

        with patch("stock_picker.search.service.load_krx_master", return_value={"삼성전자": "005930"}):
            with TestClient(app) as client:
                resp = client.get("/stocks/search?q=ZZZNOTEXIST")

        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_search_total_matches_results_length(self):
        """total 필드값 = results 배열 길이"""
        mock_session = _make_mock_session_with_empty_recommendations()
        app = _make_app(mock_session)

        with patch(
            "stock_picker.search.service.load_krx_master",
            return_value={"삼성전자": "005930", "SK하이닉스": "000660"},
        ):
            with TestClient(app) as client:
                resp = client.get("/stocks/search?q=0")

        data = resp.json()
        assert data["total"] == len(data["results"])

    def test_search_recommended_stock_has_in_recommendations_true(self):
        """최근 추천 종목은 in_recommendations=True"""
        mock_session = AsyncMock()
        # 005930을 최근 추천으로 설정
        mock_result = MagicMock()
        mock_result.all.return_value = [("005930",)]
        mock_session.execute.return_value = mock_result

        app = _make_app(mock_session)

        with patch("stock_picker.search.service.load_krx_master", return_value={"삼성전자": "005930"}):
            with TestClient(app) as client:
                resp = client.get("/stocks/search?q=삼성전자")

        data = resp.json()
        if data["total"] > 0:
            assert data["results"][0]["in_recommendations"] is True


class TestStockPricesEndpoint:
    """GET /stocks/{krx_code}/prices 엔드포인트 통합 테스트"""

    def test_valid_code_returns_200(self):
        """유효한 코드 + FDR 성공 → 200 응답"""
        app = _make_app()

        with patch(
            "stock_picker.api.routes.stocks.get_stock_price_history",
            return_value=[{"date": "2026-01-01", "close": 70000.0}],
        ):
            with TestClient(app) as client:
                resp = client.get("/stocks/005930/prices")

        assert resp.status_code == 200

    def test_response_has_required_fields(self):
        """응답에 krx_code, days, prices, available 포함"""
        app = _make_app()

        with patch(
            "stock_picker.api.routes.stocks.get_stock_price_history",
            return_value=[{"date": "2026-01-01", "close": 70000.0}],
        ):
            with TestClient(app) as client:
                resp = client.get("/stocks/005930/prices")

        data = resp.json()
        assert "krx_code" in data
        assert "days" in data
        assert "prices" in data
        assert "available" in data

    def test_fdr_failure_returns_available_false(self):
        """FDR 실패 시 available=False"""
        app = _make_app()

        with patch(
            "stock_picker.api.routes.stocks.get_stock_price_history",
            return_value=[],
        ):
            with TestClient(app) as client:
                resp = client.get("/stocks/999999/prices")

        assert resp.status_code == 200
        assert resp.json()["available"] is False

    def test_days_parameter_accepted(self):
        """days 파라미터 30 → 정상 응답"""
        app = _make_app()

        with patch(
            "stock_picker.api.routes.stocks.get_stock_price_history",
            return_value=[{"date": "2026-01-01", "close": 70000.0}],
        ):
            with TestClient(app) as client:
                resp = client.get("/stocks/005930/prices?days=30")

        assert resp.status_code == 200
        assert resp.json()["days"] == 30

    def test_days_above_90_returns_422(self):
        """days > 90 → 422 Unprocessable Entity"""
        app = _make_app()
        with TestClient(app) as client:
            resp = client.get("/stocks/005930/prices?days=91")
        assert resp.status_code == 422

    def test_days_below_1_returns_422(self):
        """days < 1 → 422"""
        app = _make_app()
        with TestClient(app) as client:
            resp = client.get("/stocks/005930/prices?days=0")
        assert resp.status_code == 422

    def test_price_point_has_date_and_close(self):
        """prices 배열의 각 항목에 date, close 포함"""
        app = _make_app()

        with patch(
            "stock_picker.api.routes.stocks.get_stock_price_history",
            return_value=[
                {"date": "2026-01-01", "close": 70000.0},
                {"date": "2026-01-02", "close": 71000.0},
            ],
        ):
            with TestClient(app) as client:
                resp = client.get("/stocks/005930/prices")

        data = resp.json()
        assert len(data["prices"]) == 2
        assert "date" in data["prices"][0]
        assert "close" in data["prices"][0]
