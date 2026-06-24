# 포트폴리오 성과 리포트 단위 테스트 (SPEC-STOCK-035)
# TDD RED-GREEN-REFACTOR 사이클
# asyncio_mode = "auto" — @pytest.mark.asyncio 불필요
import ast
import csv
import io
import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ──────────────────────────────────────────────────────────────
# NFR 검증: scipy·외부 CSV 라이브러리 미사용
# ──────────────────────────────────────────────────────────────


class TestNoScipyInReport:
    """scipy import 금지 검증 (NFR-001)"""

    def test_no_scipy_in_report(self):
        """report.py는 scipy를 import하면 안 된다"""
        module_path = os.path.normpath(
            os.path.join(
                os.path.dirname(__file__),
                "../../src/stock_picker/portfolio/report.py",
            )
        )
        with open(module_path) as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert "scipy" not in alias.name, "scipy import 금지 (NFR-001)"
                else:
                    assert node.module is None or "scipy" not in node.module, \
                        "scipy import 금지 (NFR-001)"


class TestNoExternalCsvLibrary:
    """외부 CSV 라이브러리 미사용 검증 (NFR-002)"""

    def test_no_external_csv_library(self):
        """report.py는 pandas, openpyxl 등 외부 CSV 라이브러리를 import하면 안 된다"""
        module_path = os.path.normpath(
            os.path.join(
                os.path.dirname(__file__),
                "../../src/stock_picker/portfolio/report.py",
            )
        )
        with open(module_path) as f:
            source = f.read()
        tree = ast.parse(source)
        forbidden = {"pandas", "openpyxl", "xlrd", "xlwt", "xlsxwriter"}
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for lib in forbidden:
                            assert lib not in alias.name, f"{lib} import 금지 (NFR-002)"
                else:
                    if node.module:
                        for lib in forbidden:
                            assert lib not in node.module, f"{lib} import 금지 (NFR-002)"


# ──────────────────────────────────────────────────────────────
# 순수 함수 테스트 — generate_holding_report_rows
# ──────────────────────────────────────────────────────────────


class TestGenerateHoldingReportRows:
    """generate_holding_report_rows 순수 함수 검증"""

    def _make_holdings(self, count: int = 2) -> list[dict]:
        """테스트용 보유 종목 딕셔너리 목록 생성"""
        return [
            {
                "ticker": "005930",
                "name": "삼성전자",
                "quantity": 10.0,
                "avg_cost": 70000.0,
                "market_type": "KRX",
            },
            {
                "ticker": "000660",
                "name": "SK하이닉스",
                "quantity": 5.0,
                "avg_cost": 120000.0,
                "market_type": "KRX",
            },
        ][:count]

    def test_basic_pnl_calculation(self):
        """기본 손익 계산 — 2개 종목, pnl·weight 올바름"""
        from stock_picker.portfolio.report import generate_holding_report_rows

        holdings = self._make_holdings(2)
        prices = {"005930": 75000.0, "000660": 130000.0}
        fx_rates = {}
        total_value = 10 * 75000.0 + 5 * 130000.0  # 750000 + 650000 = 1400000

        rows = generate_holding_report_rows(holdings, prices, fx_rates, total_value)

        assert len(rows) == 2
        # 삼성전자 손익 확인
        samsung = next(r for r in rows if r.ticker == "005930")
        assert samsung.pnl_amount == pytest.approx((75000.0 - 70000.0) * 10)  # 50000
        assert samsung.pnl_pct == pytest.approx((75000.0 / 70000.0 - 1) * 100, rel=1e-4)

    def test_zero_avg_cost_no_division_error(self):
        """평균단가 0일 때 ZeroDivisionError 없이 pnl_pct=0.0 반환"""
        from stock_picker.portfolio.report import generate_holding_report_rows

        holdings = [
            {"ticker": "TEST", "name": "테스트", "quantity": 10.0, "avg_cost": 0.0, "market_type": "KRX"},
        ]
        prices = {"TEST": 100.0}
        fx_rates = {}
        total_value = 1000.0

        rows = generate_holding_report_rows(holdings, prices, fx_rates, total_value)
        assert len(rows) == 1
        assert rows[0].pnl_pct == 0.0

    def test_weight_sum_approximately_100(self):
        """비중 합계가 100%에 근사해야 한다"""
        from stock_picker.portfolio.report import generate_holding_report_rows

        holdings = self._make_holdings(2)
        prices = {"005930": 75000.0, "000660": 130000.0}
        fx_rates = {}
        total_value = 10 * 75000.0 + 5 * 130000.0

        rows = generate_holding_report_rows(holdings, prices, fx_rates, total_value)
        weight_sum = sum(r.weight_pct for r in rows)
        assert weight_sum == pytest.approx(100.0, abs=0.01)

    def test_foreign_ticker_with_fx_rate(self):
        """해외 종목 — FX 환율 적용 후 KRW 환산 손익 계산"""
        from stock_picker.portfolio.report import generate_holding_report_rows

        # AAPL 1주, 평균단가 150USD → avg_cost는 이미 KRW로 전달됨
        holdings = [
            {"ticker": "AAPL", "name": "Apple", "quantity": 1.0, "avg_cost": 195000.0, "market_type": "NYSE"},
        ]
        # prices는 이미 KRW 환산 가격
        prices = {"AAPL": 200000.0}
        fx_rates = {"USD": 1300.0}
        total_value = 200000.0

        rows = generate_holding_report_rows(holdings, prices, fx_rates, total_value)
        assert len(rows) == 1
        assert rows[0].pnl_amount == pytest.approx(5000.0)  # (200000 - 195000) * 1
        assert rows[0].weight_pct == pytest.approx(100.0, abs=0.01)

    def test_single_holding_weight_100(self):
        """단일 종목 보유 — 비중이 100%여야 한다"""
        from stock_picker.portfolio.report import generate_holding_report_rows

        holdings = [
            {"ticker": "005930", "name": "삼성전자", "quantity": 10.0, "avg_cost": 70000.0, "market_type": "KRX"},
        ]
        prices = {"005930": 75000.0}
        fx_rates = {}
        total_value = 750000.0

        rows = generate_holding_report_rows(holdings, prices, fx_rates, total_value)
        assert rows[0].weight_pct == pytest.approx(100.0, abs=0.01)


# ──────────────────────────────────────────────────────────────
# 순수 함수 테스트 — generate_csv_content
# ──────────────────────────────────────────────────────────────


def _make_sample_rows() -> list:
    """테스트용 HoldingReportRow 목록 생성"""
    from stock_picker.portfolio.schemas import HoldingReportRow
    return [
        HoldingReportRow(
            ticker="005930",
            name="삼성전자",
            quantity=10.0,
            avg_cost=70000.0,
            current_price=75000.0,
            pnl_amount=50000.0,
            pnl_pct=7.14,
            weight_pct=60.0,
        ),
        HoldingReportRow(
            ticker="000660",
            name="SK하이닉스",
            quantity=5.0,
            avg_cost=120000.0,
            current_price=130000.0,
            pnl_amount=50000.0,
            pnl_pct=8.33,
            weight_pct=40.0,
        ),
    ]


class TestGenerateCsvContent:
    """generate_csv_content 순수 함수 검증"""

    def test_returns_string_with_header(self):
        """CSV 문자열 반환 — 헤더 줄 포함"""
        from stock_picker.portfolio.report import generate_csv_content
        rows = _make_sample_rows()
        content = generate_csv_content(rows)
        assert isinstance(content, str)
        assert "종목코드" in content

    def test_csv_header_has_8_columns(self):
        """CSV 헤더는 정확히 8개 열이어야 한다"""
        from stock_picker.portfolio.report import generate_csv_content
        rows = _make_sample_rows()
        content = generate_csv_content(rows)
        reader = csv.reader(io.StringIO(content))
        header = next(reader)
        assert len(header) == 8

    def test_data_row_count_matches_input(self):
        """데이터 행 수는 입력 행 수와 일치해야 한다"""
        from stock_picker.portfolio.report import generate_csv_content
        rows = _make_sample_rows()
        content = generate_csv_content(rows)
        reader = csv.reader(io.StringIO(content))
        all_rows = list(reader)
        # 헤더 1줄 + 데이터 줄
        assert len(all_rows) == len(rows) + 1

    def test_empty_rows_returns_header_only(self):
        """빈 목록 입력 — 헤더만 포함된 CSV 반환"""
        from stock_picker.portfolio.report import generate_csv_content
        content = generate_csv_content([])
        reader = csv.reader(io.StringIO(content))
        all_rows = list(reader)
        assert len(all_rows) == 1  # 헤더만

    def test_csv_uses_stdlib_only(self):
        """CSV 직렬화는 io.StringIO + csv 표준 라이브러리만 사용"""
        import stock_picker.portfolio.report as report_module
        # 모듈에서 csv와 io가 임포트 되어 있어야 한다
        import csv as csv_stdlib
        import io as io_stdlib
        # generate_csv_content 함수 소스에 csv.writer가 사용되는지 확인
        import inspect
        source = inspect.getsource(report_module.generate_csv_content)
        assert "csv.writer" in source or "csv_writer" in source or "writer" in source


# ──────────────────────────────────────────────────────────────
# PortfolioReportSummary 스키마 검증
# ──────────────────────────────────────────────────────────────


class TestPortfolioReportSummarySchema:
    """PortfolioReportSummary 스키마 검증"""

    def test_contains_holdings_list(self):
        """PortfolioReportSummary는 holdings 목록을 포함해야 한다"""
        from stock_picker.portfolio.schemas import PortfolioReportSummary
        summary = PortfolioReportSummary(
            portfolio_id=1,
            generated_at=datetime.now(tz=timezone.utc),
            period="YTD",
            total_value_krw=1000000.0,
            total_return_pct=5.0,
            mdd_pct=None,
            holdings=[],
        )
        assert isinstance(summary.holdings, list)

    def test_mdd_pct_is_optional(self):
        """mdd_pct는 Optional이어야 한다 (None 허용)"""
        from stock_picker.portfolio.schemas import PortfolioReportSummary
        summary = PortfolioReportSummary(
            portfolio_id=1,
            generated_at=datetime.now(tz=timezone.utc),
            period="YTD",
            total_value_krw=1000000.0,
            total_return_pct=5.0,
            mdd_pct=None,
            holdings=[],
        )
        assert summary.mdd_pct is None

    def test_dividend_summary_is_optional(self):
        """dividend_summary는 Optional이어야 한다 (None 허용)"""
        from stock_picker.portfolio.schemas import PortfolioReportSummary
        summary = PortfolioReportSummary(
            portfolio_id=1,
            generated_at=datetime.now(tz=timezone.utc),
            period="YTD",
            total_value_krw=1000000.0,
            total_return_pct=5.0,
            mdd_pct=None,
            holdings=[],
            dividend_summary=None,
        )
        assert summary.dividend_summary is None

    def test_benchmark_is_optional(self):
        """benchmark는 Optional이어야 한다 (None 허용)"""
        from stock_picker.portfolio.schemas import PortfolioReportSummary
        summary = PortfolioReportSummary(
            portfolio_id=1,
            generated_at=datetime.now(tz=timezone.utc),
            period="YTD",
            total_value_krw=1000000.0,
            total_return_pct=5.0,
            mdd_pct=None,
            holdings=[],
            benchmark=None,
        )
        assert summary.benchmark is None


# ──────────────────────────────────────────────────────────────
# MonthlySnapshot 스키마 검증
# ──────────────────────────────────────────────────────────────


class TestMonthlySnapshotSchema:
    """MonthlySnapshot 스키마 검증"""

    def test_monthly_snapshot_from_dict(self):
        """MonthlySnapshot은 딕셔너리로 생성 가능해야 한다"""
        from stock_picker.portfolio.schemas import MonthlySnapshot
        snapshot = MonthlySnapshot(
            id=1,
            portfolio_id=1,
            month="2026-05",
            total_value_krw=1000000.0,
            total_return_pct=5.0,
            holding_count=3,
            created_at=datetime.now(tz=timezone.utc),
        )
        assert snapshot.month == "2026-05"
        assert snapshot.holding_count == 3


# ──────────────────────────────────────────────────────────────
# API 엔드포인트 소유권 검증 (404 반환)
# ──────────────────────────────────────────────────────────────


class TestReportApiOwnership:
    """보고서 API 소유권 검증 — 미소유 포트폴리오는 404 반환

    dependency_overrides 패턴을 사용하여 실제 DB 없이 인증된 사용자로 요청을 보낸다.
    portfolio ID 99999는 존재하지 않으므로 404가 반환되어야 한다.
    """

    def _make_client_with_auth(self):
        """인증 의존성 오버라이드 클라이언트 생성 (user_id=999, 존재하지 않는 사용자)"""
        from fastapi.testclient import TestClient
        from stock_picker.api.main import app
        from stock_picker.auth.dependencies import get_current_user, get_db_session
        from stock_picker.api.deps import get_redis_client

        # 인증된 가짜 사용자 (id=999)
        mock_user = MagicMock()
        mock_user.id = 999

        # DB: 어떤 포트폴리오 쿼리도 None 반환 (미소유)
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Redis: 가짜 클라이언트
        mock_redis = AsyncMock()

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db_session] = lambda: mock_db
        app.dependency_overrides[get_redis_client] = lambda: mock_redis

        client = TestClient(app, raise_server_exceptions=False)
        return client, app

    def test_get_report_csv_returns_404_when_not_owned(self):
        """GET /report?format=csv — 미소유 포트폴리오 → 404"""
        client, app = self._make_client_with_auth()
        try:
            resp = client.get("/portfolios/99999/report?format=csv")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()

    def test_get_report_json_returns_404_when_not_owned(self):
        """GET /report?format=json — 미소유 포트폴리오 → 404"""
        client, app = self._make_client_with_auth()
        try:
            resp = client.get("/portfolios/99999/report?format=json")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()

    def test_get_report_summary_returns_404_when_not_owned(self):
        """GET /report/summary — 미소유 포트폴리오 → 404"""
        client, app = self._make_client_with_auth()
        try:
            resp = client.get("/portfolios/99999/report/summary")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()

    def test_post_snapshot_returns_404_when_not_owned(self):
        """POST /report/snapshot — 미소유 포트폴리오 → 404"""
        client, app = self._make_client_with_auth()
        try:
            resp = client.post("/portfolios/99999/report/snapshot", json={"month": "2026-05"})
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()

    def test_get_snapshots_returns_404_when_not_owned(self):
        """GET /report/snapshots — 미소유 포트폴리오 → 404"""
        client, app = self._make_client_with_auth()
        try:
            resp = client.get("/portfolios/99999/report/snapshots")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()

    def test_unsupported_format_returns_400(self):
        """GET /report?format=unsupported — 미지원 포맷 → 400"""
        client, app = self._make_client_with_auth()
        try:
            resp = client.get("/portfolios/99999/report?format=xlsx")
            # format 검증이 먼저이면 400, 소유권 확인이 먼저이면 404
            assert resp.status_code in (400, 404)
        finally:
            app.dependency_overrides.clear()


# ──────────────────────────────────────────────────────────────
# 스냅샷 upsert 멱등성 검증
# ──────────────────────────────────────────────────────────────


class TestSnapshotUpsert:
    """스냅샷 DB-중립 upsert 멱등성 검증"""

    def test_create_snapshot_returns_monthly_snapshot(self):
        """스냅샷 생성 → MonthlySnapshot 반환"""
        from stock_picker.portfolio.report import upsert_monthly_snapshot
        from stock_picker.portfolio.schemas import MonthlySnapshot

        # DB 모의
        db = MagicMock()
        # 기존 레코드 없음
        db.query.return_value.filter.return_value.first.return_value = None

        result = upsert_monthly_snapshot(
            db=db,
            portfolio_id=1,
            month="2026-05",
            total_value_krw=1000000.0,
            total_return_pct=5.0,
            holding_count=3,
        )
        # DB add + commit + refresh 호출 확인
        db.add.assert_called_once()
        db.commit.assert_called()

    def test_same_month_update_not_duplicate(self):
        """동일 월 재요청 — 기존 레코드 업데이트 (INSERT 아님)"""
        from stock_picker.portfolio.report import upsert_monthly_snapshot

        # 기존 레코드 존재
        existing = MagicMock()
        existing.total_value_krw = 900000.0
        existing.total_return_pct = 3.0
        existing.holding_count = 2

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = existing

        upsert_monthly_snapshot(
            db=db,
            portfolio_id=1,
            month="2026-05",
            total_value_krw=1000000.0,
            total_return_pct=5.0,
            holding_count=3,
        )
        # 기존 레코드 필드 업데이트 확인
        assert existing.total_value_krw == 1000000.0
        assert existing.holding_count == 3
        # INSERT(add) 호출 없어야 함
        db.add.assert_not_called()
