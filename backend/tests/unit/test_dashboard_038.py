# 시장 시각화 대시보드 단위 테스트 (SPEC-STOCK-038)
# TDD RED-GREEN-REFACTOR 사이클
# asyncio_mode = "auto" — @pytest.mark.asyncio 불필요
from datetime import date, timedelta
from unittest.mock import MagicMock, patch



# ──────────────────────────────────────────────────────────────
# TestFilterSnapshotsByRange — 기간별 스냅샷 필터 순수 함수 (5개 테스트)
# ──────────────────────────────────────────────────────────────


class TestFilterSnapshotsByRange:
    """기간별 스냅샷 필터 순수 함수 테스트 (REQ-DASH-FILTER)"""

    def test_returns_only_snapshots_within_range(self):
        """범위 내 스냅샷만 반환해야 한다"""
        from stock_picker.portfolio.dashboard import filter_snapshots_by_range

        today = date.today()
        snapshots = [
            {"date": today - timedelta(days=40), "total_value_krw": 1000.0},
            {"date": today - timedelta(days=20), "total_value_krw": 2000.0},
            {"date": today - timedelta(days=5), "total_value_krw": 3000.0},
        ]
        result = filter_snapshots_by_range(snapshots, days=30)

        assert len(result) == 2
        assert result[0]["total_value_krw"] == 2000.0
        assert result[1]["total_value_krw"] == 3000.0

    def test_results_sorted_ascending_by_date(self):
        """날짜 오름차순으로 정렬되어야 한다"""
        from stock_picker.portfolio.dashboard import filter_snapshots_by_range

        today = date.today()
        snapshots = [
            {"date": today - timedelta(days=5), "total_value_krw": 3000.0},
            {"date": today - timedelta(days=15), "total_value_krw": 2000.0},
            {"date": today - timedelta(days=25), "total_value_krw": 1000.0},
        ]
        result = filter_snapshots_by_range(snapshots, days=30)

        assert result[0]["total_value_krw"] == 1000.0
        assert result[1]["total_value_krw"] == 2000.0
        assert result[2]["total_value_krw"] == 3000.0

    def test_empty_snapshots_returns_empty_list(self):
        """빈 스냅샷 입력 시 빈 배열을 반환해야 한다"""
        from stock_picker.portfolio.dashboard import filter_snapshots_by_range

        result = filter_snapshots_by_range([], days=30)

        assert result == []

    def test_excludes_snapshots_outside_range(self):
        """범위 외 스냅샷을 제외해야 한다"""
        from stock_picker.portfolio.dashboard import filter_snapshots_by_range

        today = date.today()
        snapshots = [
            {"date": today - timedelta(days=100), "total_value_krw": 500.0},
            {"date": today - timedelta(days=200), "total_value_krw": 400.0},
        ]
        result = filter_snapshots_by_range(snapshots, days=30)

        assert result == []

    def test_boundary_value_exactly_days_ago(self):
        """정확히 days일 전 스냅샷은 포함되어야 한다 (경계값)"""
        from stock_picker.portfolio.dashboard import filter_snapshots_by_range

        today = date.today()
        snapshots = [
            {"date": today - timedelta(days=30), "total_value_krw": 1500.0},
            {"date": today - timedelta(days=31), "total_value_krw": 1000.0},
        ]
        result = filter_snapshots_by_range(snapshots, days=30)

        # 정확히 30일 전은 포함, 31일 전은 제외
        assert len(result) == 1
        assert result[0]["total_value_krw"] == 1500.0


# ──────────────────────────────────────────────────────────────
# TestAggregateBySector — 섹터별 집계 순수 함수 (5개 테스트)
# ──────────────────────────────────────────────────────────────


class TestAggregateBySector:
    """섹터별 집계 순수 함수 테스트 (REQ-DASH-SECTOR)"""

    def test_aggregates_value_by_sector(self):
        """섹터별 평가액을 집계해야 한다"""
        from stock_picker.portfolio.dashboard import aggregate_by_sector

        holdings = [
            {"sector": "반도체", "current_value": 1000.0, "cost": 800.0},
            {"sector": "IT서비스", "current_value": 500.0, "cost": 400.0},
        ]
        result = aggregate_by_sector(holdings)

        sector_map = {r["sector"]: r for r in result}
        assert sector_map["반도체"]["value_krw"] == 1000.0
        assert sector_map["IT서비스"]["value_krw"] == 500.0

    def test_none_sector_becomes_기타해외(self):
        """섹터가 None이면 '기타/해외'로 분류되어야 한다"""
        from stock_picker.portfolio.dashboard import aggregate_by_sector

        holdings = [
            {"sector": None, "current_value": 2000.0, "cost": 1500.0},
        ]
        result = aggregate_by_sector(holdings)

        assert len(result) == 1
        assert result[0]["sector"] == "기타/해외"

    def test_return_pct_calculation_accuracy(self):
        """수익률(%) 계산이 정확해야 한다"""
        from stock_picker.portfolio.dashboard import aggregate_by_sector

        holdings = [
            {"sector": "반도체", "current_value": 1200.0, "cost": 1000.0},
        ]
        result = aggregate_by_sector(holdings)

        # 수익률 = (1200 - 1000) / 1000 * 100 = 20.0
        assert abs(result[0]["return_pct"] - 20.0) < 0.01

    def test_empty_holdings_returns_empty_list(self):
        """빈 holdings 입력 시 빈 배열을 반환해야 한다"""
        from stock_picker.portfolio.dashboard import aggregate_by_sector

        result = aggregate_by_sector([])

        assert result == []

    def test_multiple_holdings_same_sector_summed(self):
        """동일 섹터의 여러 종목은 합산되어야 한다"""
        from stock_picker.portfolio.dashboard import aggregate_by_sector

        holdings = [
            {"sector": "반도체", "current_value": 600.0, "cost": 500.0},
            {"sector": "반도체", "current_value": 400.0, "cost": 300.0},
        ]
        result = aggregate_by_sector(holdings)

        sector_map = {r["sector"]: r for r in result}
        # 합산 평가액 = 600 + 400 = 1000
        assert sector_map["반도체"]["value_krw"] == 1000.0
        # 합산 수익률 = (1000 - 800) / 800 * 100 = 25.0
        assert abs(sector_map["반도체"]["return_pct"] - 25.0) < 0.01


# ──────────────────────────────────────────────────────────────
# TestAggregateByAssetType — 자산유형 배분 순수 함수 (5개 테스트)
# ──────────────────────────────────────────────────────────────


class TestAggregateByAssetType:
    """자산유형 배분 순수 함수 테스트 (REQ-DASH-ASSET)"""

    def test_krx_classified_as_국내(self):
        """KRX 시장 종목은 '국내'로 분류되어야 한다"""
        from stock_picker.portfolio.dashboard import aggregate_by_asset_type

        holdings = [
            {"market": "KRX", "current_value": 1000.0},
        ]
        result = aggregate_by_asset_type(holdings)

        assert len(result) == 1
        assert result[0]["asset_type"] == "국내"

    def test_nyse_classified_as_해외(self):
        """NYSE 시장 종목은 '해외'로 분류되어야 한다"""
        from stock_picker.portfolio.dashboard import aggregate_by_asset_type

        holdings = [
            {"market": "NYSE", "current_value": 2000.0},
        ]
        result = aggregate_by_asset_type(holdings)

        assert len(result) == 1
        assert result[0]["asset_type"] == "해외"

    def test_nasdaq_classified_as_해외(self):
        """NASDAQ 시장 종목은 '해외'로 분류되어야 한다"""
        from stock_picker.portfolio.dashboard import aggregate_by_asset_type

        holdings = [
            {"market": "NASDAQ", "current_value": 1500.0},
        ]
        result = aggregate_by_asset_type(holdings)

        assert len(result) == 1
        assert result[0]["asset_type"] == "해외"

    def test_weight_pct_sums_to_100(self):
        """비중(%) 합계는 100이어야 한다"""
        from stock_picker.portfolio.dashboard import aggregate_by_asset_type

        holdings = [
            {"market": "KRX", "current_value": 3000.0},
            {"market": "NYSE", "current_value": 1000.0},
            {"market": "NASDAQ", "current_value": 1000.0},
        ]
        result = aggregate_by_asset_type(holdings)

        total_weight = sum(r["weight_pct"] for r in result)
        assert abs(total_weight - 100.0) < 0.01

    def test_empty_holdings_returns_empty_list(self):
        """빈 holdings 입력 시 빈 배열을 반환해야 한다"""
        from stock_picker.portfolio.dashboard import aggregate_by_asset_type

        result = aggregate_by_asset_type([])

        assert result == []

    def test_single_asset_type_weight_is_100(self):
        """단일 자산유형인 경우 비중은 100%이어야 한다"""
        from stock_picker.portfolio.dashboard import aggregate_by_asset_type

        holdings = [
            {"market": "KRX", "current_value": 5000.0},
        ]
        result = aggregate_by_asset_type(holdings)

        assert len(result) == 1
        assert abs(result[0]["weight_pct"] - 100.0) < 0.01


# ──────────────────────────────────────────────────────────────
# TestDashboardOwnership — 소유권 검증 (3개 테스트)
# ──────────────────────────────────────────────────────────────


class TestDashboardOwnership:
    """대시보드 엔드포인트 소유권 검증 테스트 (REQ-DASH-OWN)"""

    def _make_mock_db(self):
        """모의 DB 세션 생성"""
        return MagicMock()

    def _make_mock_user(self, user_id: int = 99):
        """모의 사용자 생성"""
        user = MagicMock()
        user.id = user_id
        return user

    def test_value_series_returns_404_when_not_owner(self):
        """미소유 포트폴리오에 대한 value-series 요청은 404를 반환해야 한다"""
        from fastapi.testclient import TestClient
        from stock_picker.api.main import create_app
        from stock_picker.auth.dependencies import get_current_user, get_db_session
        from stock_picker.portfolio import service

        app = create_app()
        mock_user = self._make_mock_user(user_id=99)

        with patch.object(service, "get_portfolio_with_holdings", return_value=None):
            app.dependency_overrides[get_current_user] = lambda: mock_user
            app.dependency_overrides[get_db_session] = lambda: self._make_mock_db()
            client = TestClient(app)
            try:
                response = client.get("/portfolios/999/dashboard/value-series?days=30")
                assert response.status_code == 404
            finally:
                app.dependency_overrides.clear()

    def test_sector_summary_returns_404_when_not_owner(self):
        """미소유 포트폴리오에 대한 sector-summary 요청은 404를 반환해야 한다"""
        from fastapi.testclient import TestClient
        from stock_picker.api.main import create_app
        from stock_picker.auth.dependencies import get_current_user, get_db_session
        from stock_picker.portfolio import service

        app = create_app()
        mock_user = self._make_mock_user(user_id=99)

        with patch.object(service, "get_portfolio_with_holdings", return_value=None):
            app.dependency_overrides[get_current_user] = lambda: mock_user
            app.dependency_overrides[get_db_session] = lambda: self._make_mock_db()
            client = TestClient(app)
            try:
                response = client.get("/portfolios/999/dashboard/sector-summary")
                assert response.status_code == 404
            finally:
                app.dependency_overrides.clear()

    def test_asset_allocation_returns_404_when_not_owner(self):
        """미소유 포트폴리오에 대한 asset-allocation 요청은 404를 반환해야 한다"""
        from fastapi.testclient import TestClient
        from stock_picker.api.main import create_app
        from stock_picker.auth.dependencies import get_current_user, get_db_session
        from stock_picker.portfolio import service

        app = create_app()
        mock_user = self._make_mock_user(user_id=99)

        with patch.object(service, "get_portfolio_with_holdings", return_value=None):
            app.dependency_overrides[get_current_user] = lambda: mock_user
            app.dependency_overrides[get_db_session] = lambda: self._make_mock_db()
            client = TestClient(app)
            try:
                response = client.get("/portfolios/999/dashboard/asset-allocation")
                assert response.status_code == 404
            finally:
                app.dependency_overrides.clear()


# ──────────────────────────────────────────────────────────────
# TestDashboardValidation — 입력 검증 (3개 테스트)
# ──────────────────────────────────────────────────────────────


class TestDashboardValidation:
    """대시보드 엔드포인트 입력 검증 테스트 (REQ-DASH-VALID)"""

    def _make_mock_db(self):
        return MagicMock()

    def _make_mock_user(self, user_id: int = 1):
        user = MagicMock()
        user.id = user_id
        return user

    def test_days_45_not_allowed_returns_422(self):
        """허용되지 않는 days=45 입력 시 422를 반환해야 한다"""
        from fastapi.testclient import TestClient
        from stock_picker.api.main import create_app
        from stock_picker.auth.dependencies import get_current_user, get_db_session

        app = create_app()
        mock_user = self._make_mock_user()

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db_session] = lambda: self._make_mock_db()
        client = TestClient(app)
        try:
            response = client.get("/portfolios/1/dashboard/value-series?days=45")
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    def test_days_30_allowed_returns_200_or_404(self):
        """허용되는 days=30 입력 시 200 또는 404를 반환해야 한다 (검증 통과)"""
        from fastapi.testclient import TestClient
        from stock_picker.api.main import create_app
        from stock_picker.auth.dependencies import get_current_user, get_db_session
        from stock_picker.portfolio import service

        app = create_app()
        mock_user = self._make_mock_user()

        with patch.object(service, "get_portfolio_with_holdings", return_value=None):
            app.dependency_overrides[get_current_user] = lambda: mock_user
            app.dependency_overrides[get_db_session] = lambda: self._make_mock_db()
            client = TestClient(app)
            try:
                response = client.get("/portfolios/1/dashboard/value-series?days=30")
                # 검증은 통과했으나 포트폴리오가 없으므로 404
                assert response.status_code in (200, 404)
            finally:
                app.dependency_overrides.clear()

    def test_days_0_not_allowed_returns_422(self):
        """허용되지 않는 days=0 입력 시 422를 반환해야 한다"""
        from fastapi.testclient import TestClient
        from stock_picker.api.main import create_app
        from stock_picker.auth.dependencies import get_current_user, get_db_session

        app = create_app()
        mock_user = self._make_mock_user()

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db_session] = lambda: self._make_mock_db()
        client = TestClient(app)
        try:
            response = client.get("/portfolios/1/dashboard/value-series?days=0")
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()
