# SPEC-STOCK-049: 포트폴리오 거래 내역 & 실현손익 단위 테스트
# 테스트 실행: backend/.venv/bin/pytest backend/tests/unit/test_transactions_049.py -v
"""
SPEC-STOCK-049 TDD 단위 테스트
커버리지 대상: add_transaction, list_transactions, get_realized_pnl 서비스 함수 및 라우터 엔드포인트
T-049-001 ~ T-049-009 (백엔드 9개)
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# 공통 헬퍼 팩토리
# ─────────────────────────────────────────────────────────────────────────────


def _make_mock_user(user_id: int = 1, username: str = "testuser"):
    """User 모의 객체 생성"""
    from stock_picker.db.models import User

    u = MagicMock(spec=User)
    u.id = user_id
    u.username = username
    u.email = f"{username}@example.com"
    return u


def _make_mock_portfolio(portfolio_id: int = 1, owner_id: int = 1):
    """Portfolio 모의 객체 생성"""
    from stock_picker.db.models import Portfolio

    p = MagicMock(spec=Portfolio)
    p.id = portfolio_id
    p.user_id = owner_id
    p.name = f"포트폴리오 {portfolio_id}"
    return p


def _make_mock_transaction(
    txn_id: int = 1,
    portfolio_id: int = 1,
    krx_code: str = "005930",
    txn_type: str = "BUY",
    quantity: int = 10,
    price: Decimal = Decimal("1000.00"),
    txn_date: date | None = None,
    note: str | None = None,
):
    """PortfolioTransaction 모의 객체 생성"""
    from stock_picker.db.models import PortfolioTransaction  # noqa: F401

    t = MagicMock()
    t.id = txn_id
    t.portfolio_id = portfolio_id
    t.krx_code = krx_code
    t.txn_type = txn_type
    t.quantity = quantity
    t.price = price
    t.txn_date = txn_date or date(2026, 1, 1)
    t.note = note
    t.created_at = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    return t


# ─────────────────────────────────────────────────────────────────────────────
# T-049-001: 매수 거래 기록 → side=BUY·수량·가격 저장 확인 (AC-049-001)
# ─────────────────────────────────────────────────────────────────────────────


class TestAddBuyTransaction:
    """POST /portfolios/{id}/transactions — BUY 거래 정상 저장"""

    def test_add_buy_transaction(self):
        """T-049-001: BUY 거래 추가 → DB 저장 확인"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app

        client = TestClient(app)
        mock_user = _make_mock_user(user_id=1)
        mock_txn = _make_mock_transaction(
            txn_id=1,
            portfolio_id=1,
            krx_code="005930",
            txn_type="BUY",
            quantity=10,
            price=Decimal("50000.00"),
            txn_date=date(2026, 1, 2),
        )
        # 서비스 반환값: TransactionItem 직렬화 가능한 dict
        expected = {
            "id": 1,
            "portfolio_id": 1,
            "krx_code": "005930",
            "txn_type": "BUY",
            "quantity": 10,
            "price": "50000.00",
            "txn_date": "2026-01-02",
            "note": None,
            "created_at": "2026-01-01T00:00:00Z",
        }

        with (
            patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user),
            patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()),
            patch("stock_picker.portfolio.transactions.add_transaction", return_value=expected),
        ):
            response = client.post(
                "/portfolios/1/transactions",
                json={
                    "krx_code": "005930",
                    "txn_type": "BUY",
                    "quantity": 10,
                    "price": "50000.00",
                    "txn_date": "2026-01-02",
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert data["txn_type"] == "BUY"
        assert data["quantity"] == 10
        assert data["krx_code"] == "005930"


# ─────────────────────────────────────────────────────────────────────────────
# T-049-002: 매도 거래 기록 (AC-049-002)
# ─────────────────────────────────────────────────────────────────────────────


class TestAddSellTransaction:
    """POST /portfolios/{id}/transactions — SELL 거래 정상 저장"""

    def test_add_sell_transaction(self):
        """T-049-002: SELL 거래 추가 → DB 저장 확인"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app

        client = TestClient(app)
        mock_user = _make_mock_user(user_id=1)
        expected = {
            "id": 2,
            "portfolio_id": 1,
            "krx_code": "005930",
            "txn_type": "SELL",
            "quantity": 5,
            "price": "60000.00",
            "txn_date": "2026-01-03",
            "note": None,
            "created_at": "2026-01-01T00:00:00Z",
        }

        with (
            patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user),
            patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()),
            patch("stock_picker.portfolio.transactions.add_transaction", return_value=expected),
        ):
            response = client.post(
                "/portfolios/1/transactions",
                json={
                    "krx_code": "005930",
                    "txn_type": "SELL",
                    "quantity": 5,
                    "price": "60000.00",
                    "txn_date": "2026-01-03",
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert data["txn_type"] == "SELL"
        assert data["quantity"] == 5


# ─────────────────────────────────────────────────────────────────────────────
# T-049-003: 타인 포트폴리오 거래 → 403 (AC-049-005)
# ─────────────────────────────────────────────────────────────────────────────


class TestAddTransactionUnauthorized:
    """POST /portfolios/{id}/transactions — 소유권 없는 경우 403"""

    def test_add_transaction_unauthorized(self):
        """T-049-003: 타인 포트폴리오 → 403 거부"""
        from fastapi import HTTPException
        from fastapi.testclient import TestClient
        from stock_picker.main import app

        client = TestClient(app)
        mock_user = _make_mock_user(user_id=99)

        with (
            patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user),
            patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()),
            patch(
                "stock_picker.portfolio.transactions.add_transaction",
                side_effect=HTTPException(status_code=403, detail="Forbidden"),
            ),
        ):
            response = client.post(
                "/portfolios/1/transactions",
                json={
                    "krx_code": "005930",
                    "txn_type": "BUY",
                    "quantity": 10,
                    "price": "50000.00",
                    "txn_date": "2026-01-02",
                },
            )

        assert response.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# T-049-004: 잘못된 txn_type → 422 (AC-049-004)
# ─────────────────────────────────────────────────────────────────────────────


class TestAddTransactionInvalidType:
    """POST /portfolios/{id}/transactions — txn_type 유효성 검증"""

    def test_add_transaction_invalid_type(self):
        """T-049-004: txn_type 'HOLD' → 422 Unprocessable Entity"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app

        client = TestClient(app)
        mock_user = _make_mock_user(user_id=1)

        with (
            patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user),
            patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()),
        ):
            response = client.post(
                "/portfolios/1/transactions",
                json={
                    "krx_code": "005930",
                    "txn_type": "HOLD",  # 유효하지 않은 타입
                    "quantity": 10,
                    "price": "50000.00",
                    "txn_date": "2026-01-02",
                },
            )

        assert response.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# T-049-005: 거래 목록 페이지네이션 (AC-049-007)
# ─────────────────────────────────────────────────────────────────────────────


class TestListTransactionsPagination:
    """GET /portfolios/{id}/transactions — 페이지네이션 동작"""

    def test_list_transactions_pagination(self):
        """T-049-005: page/page_size 파라미터로 페이지네이션, total 반환"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app

        client = TestClient(app)
        mock_user = _make_mock_user(user_id=1)

        # 총 5개 거래, page_size=2 요청 → total=5 반환
        expected_list = {
            "transactions": [
                {
                    "id": 3,
                    "portfolio_id": 1,
                    "krx_code": "005930",
                    "txn_type": "BUY",
                    "quantity": 5,
                    "price": "55000.00",
                    "txn_date": "2026-01-03",
                    "note": None,
                    "created_at": "2026-01-01T00:00:00Z",
                },
            ],
            "total": 5,
            "page": 2,
            "page_size": 1,
        }

        with (
            patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user),
            patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()),
            patch("stock_picker.portfolio.transactions.list_transactions", return_value=expected_list),
        ):
            response = client.get("/portfolios/1/transactions?page=2&page_size=1")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert data["page"] == 2
        assert data["page_size"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# T-049-006: krx_code 필터 (AC-049-006)
# ─────────────────────────────────────────────────────────────────────────────


class TestListTransactionsFilterByKrxCode:
    """GET /portfolios/{id}/transactions?krx_code=... — 종목 코드 필터"""

    def test_list_transactions_filter_by_krx_code(self):
        """T-049-006: krx_code 필터 → 해당 종목 거래만 반환"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app

        client = TestClient(app)
        mock_user = _make_mock_user(user_id=1)

        expected_list = {
            "transactions": [
                {
                    "id": 1,
                    "portfolio_id": 1,
                    "krx_code": "035720",
                    "txn_type": "BUY",
                    "quantity": 3,
                    "price": "80000.00",
                    "txn_date": "2026-01-01",
                    "note": None,
                    "created_at": "2026-01-01T00:00:00Z",
                },
            ],
            "total": 1,
            "page": 1,
            "page_size": 20,
        }

        with (
            patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user),
            patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()),
            patch("stock_picker.portfolio.transactions.list_transactions", return_value=expected_list),
        ):
            response = client.get("/portfolios/1/transactions?krx_code=035720")

        assert response.status_code == 200
        data = response.json()
        assert len(data["transactions"]) == 1
        assert data["transactions"][0]["krx_code"] == "035720"


# ─────────────────────────────────────────────────────────────────────────────
# T-049-007: 이동평균 실현손익 계산 (AC-049-009)
# 앵커: BUY 10@1000·BUY 10@2000·SELL 5@3000 → realized=7500
# ─────────────────────────────────────────────────────────────────────────────


class TestRealizedPnlMovingAverage:
    """GET /portfolios/{id}/transactions/pnl — 이동평균 원가법 실현손익"""

    def test_realized_pnl_moving_average(self):
        """T-049-007: BUY 10@1000, BUY 10@2000, SELL 5@3000 → realized=7500"""
        from stock_picker.portfolio.transactions import get_realized_pnl

        # 순수 서비스 레이어 테스트
        mock_db = MagicMock()

        # BUY 10@1000, BUY 10@2000, SELL 5@3000 거래 모킹
        mock_txns = [
            MagicMock(krx_code="005930", txn_type="BUY", quantity=10, price=Decimal("1000.00"), txn_date=date(2026, 1, 1)),
            MagicMock(krx_code="005930", txn_type="BUY", quantity=10, price=Decimal("2000.00"), txn_date=date(2026, 1, 2)),
            MagicMock(krx_code="005930", txn_type="SELL", quantity=5, price=Decimal("3000.00"), txn_date=date(2026, 1, 3)),
        ]

        # 포트폴리오 소유권 확인 모킹
        mock_portfolio = _make_mock_portfolio(portfolio_id=1, owner_id=1)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_portfolio

        # 거래 목록 조회 모킹
        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = mock_txns
        mock_db.query.side_effect = [
            MagicMock(filter=MagicMock(return_value=MagicMock(first=MagicMock(return_value=mock_portfolio)))),
            mock_query,
        ]

        result = get_realized_pnl(db=mock_db, portfolio_id=1, user_id=1)

        # 이동평균 원가법: BUY 10@1000 → avg=1000, BUY 10@2000 → avg=1500
        # SELL 5@3000 → realized = 5*(3000-1500) = 7500
        assert result["total_realized_pnl"] == Decimal("7500.00")
        assert len(result["items"]) == 1
        assert result["items"][0]["krx_code"] == "005930"
        assert result["items"][0]["realized_pnl"] == Decimal("7500.00")


# ─────────────────────────────────────────────────────────────────────────────
# T-049-008: 매도 없으면 realized=0 (AC-049-011)
# ─────────────────────────────────────────────────────────────────────────────


class TestRealizedPnlNoSell:
    """get_realized_pnl — 매도 없으면 realized=0"""

    def test_realized_pnl_no_sell(self):
        """T-049-008: 매수만 있는 종목 → realized=0"""
        from stock_picker.portfolio.transactions import get_realized_pnl

        mock_db = MagicMock()
        mock_portfolio = _make_mock_portfolio(portfolio_id=1, owner_id=1)

        # BUY만 있는 거래
        mock_txns = [
            MagicMock(krx_code="005930", txn_type="BUY", quantity=10, price=Decimal("1000.00"), txn_date=date(2026, 1, 1)),
            MagicMock(krx_code="005930", txn_type="BUY", quantity=5, price=Decimal("1200.00"), txn_date=date(2026, 1, 2)),
        ]

        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = mock_txns
        mock_db.query.side_effect = [
            MagicMock(filter=MagicMock(return_value=MagicMock(first=MagicMock(return_value=mock_portfolio)))),
            mock_query,
        ]

        result = get_realized_pnl(db=mock_db, portfolio_id=1, user_id=1)

        assert result["total_realized_pnl"] == Decimal("0")
        # 매도 없으면 items 비어있거나 realized_pnl=0
        for item in result["items"]:
            assert item["realized_pnl"] == Decimal("0")


# ─────────────────────────────────────────────────────────────────────────────
# T-049-009: 종목별 분리 계산 (AC-049-010)
# ─────────────────────────────────────────────────────────────────────────────


class TestRealizedPnlPerStock:
    """get_realized_pnl — 다종목 종목별 분리 계산"""

    def test_realized_pnl_per_stock(self):
        """T-049-009: 종목별 realized 계산, total=합계"""
        from stock_picker.portfolio.transactions import get_realized_pnl

        mock_db = MagicMock()
        mock_portfolio = _make_mock_portfolio(portfolio_id=1, owner_id=1)

        # 005930: BUY 10@1000, SELL 10@2000 → realized = 10*(2000-1000) = 10000
        # 035720: BUY 5@800, SELL 5@1600 → realized = 5*(1600-800) = 4000
        mock_txns = [
            MagicMock(krx_code="005930", txn_type="BUY", quantity=10, price=Decimal("1000.00"), txn_date=date(2026, 1, 1)),
            MagicMock(krx_code="005930", txn_type="SELL", quantity=10, price=Decimal("2000.00"), txn_date=date(2026, 1, 2)),
            MagicMock(krx_code="035720", txn_type="BUY", quantity=5, price=Decimal("800.00"), txn_date=date(2026, 1, 1)),
            MagicMock(krx_code="035720", txn_type="SELL", quantity=5, price=Decimal("1600.00"), txn_date=date(2026, 1, 2)),
        ]

        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = mock_txns
        mock_db.query.side_effect = [
            MagicMock(filter=MagicMock(return_value=MagicMock(first=MagicMock(return_value=mock_portfolio)))),
            mock_query,
        ]

        result = get_realized_pnl(db=mock_db, portfolio_id=1, user_id=1)

        assert result["total_realized_pnl"] == Decimal("14000.00")
        items_by_code = {item["krx_code"]: item for item in result["items"]}
        assert items_by_code["005930"]["realized_pnl"] == Decimal("10000.00")
        assert items_by_code["035720"]["realized_pnl"] == Decimal("4000.00")
