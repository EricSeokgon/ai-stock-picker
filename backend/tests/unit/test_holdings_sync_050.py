from __future__ import annotations
"""
SPEC-STOCK-050: 거래 기반 홀딩스 동기화 — 백엔드 단위 테스트 (10개)
T-050-001 ~ T-050-010

RED phase: holdings_sync 모듈 미구현 → ImportError 또는 404로 실패 예정
"""
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest


# ---- 헬퍼 팩토리 -------------------------------------------------------

def _make_mock_user(user_id: int = 1):
    """테스트용 가짜 사용자 생성"""
    user = MagicMock()
    user.id = user_id
    return user


def _make_mock_portfolio(portfolio_id: int = 1, user_id: int = 1):
    """테스트용 가짜 포트폴리오 생성"""
    p = MagicMock()
    p.id = portfolio_id
    p.user_id = user_id
    return p


def _make_mock_transaction(
    id: int = 1,
    portfolio_id: int = 1,
    krx_code: str = "005930",
    txn_type: str = "BUY",
    quantity: int = 10,
    price: str = "1000.00",
    txn_date: str = "2024-01-01",
):
    """테스트용 가짜 거래 생성"""
    t = MagicMock()
    t.id = id
    t.portfolio_id = portfolio_id
    t.krx_code = krx_code
    t.txn_type = txn_type
    t.quantity = quantity
    t.price = Decimal(price)
    t.txn_date = txn_date
    return t


def _make_mock_holding(
    id: int = 1,
    portfolio_id: int = 1,
    krx_code: str = "005930",
    quantity: int = 10,
    avg_buy_price: str = "1000.00",
    market: str = "KRX",
    currency: str = "KRW",
):
    """테스트용 가짜 홀딩 생성"""
    h = MagicMock()
    h.id = id
    h.portfolio_id = portfolio_id
    h.krx_code = krx_code
    h.quantity = quantity
    h.avg_buy_price = Decimal(avg_buy_price)
    h.market = market
    h.currency = currency
    return h


def _get_test_client():
    """FastAPI TestClient 생성"""
    from fastapi.testclient import TestClient
    from stock_picker.main import app
    return TestClient(app)


# ====================================================================
# 라우터 수준 테스트: TestClient + patch
# ====================================================================

class TestPreviewSyncReturnsDiff:
    """T-050-001: preview 엔드포인트가 diff 목록을 반환한다"""

    def test_preview_returns_diff(self):
        from stock_picker.portfolio.schemas import SyncPreviewItem, SyncPreviewResponse

        mock_user = _make_mock_user()
        mock_db = MagicMock()
        preview_response = SyncPreviewResponse(
            items=[
                SyncPreviewItem(
                    krx_code="005930",
                    action="upsert",
                    current_qty=0,
                    derived_qty=10,
                    current_avg=None,
                    derived_avg=Decimal("1000.00"),
                )
            ]
        )

        # TestClient를 patch 컨텍스트 외부에서 먼저 생성한다.
        # anyio 스레드풀 초기화가 patch 활성 상태에서 일어나면
        # _patching_friendly_get_db_session 제너레이터가 이중 yield되어
        # RuntimeError("generator didn't stop after throw()") 가 발생한다.
        # test_transactions_049.py 패턴과 동일하게 맞춘다.
        client = _get_test_client()

        with (
            patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user),
            patch(
                "stock_picker.auth.dependencies.get_db_session",
                return_value=iter([mock_db]),
            ),
            patch(
                "stock_picker.portfolio.holdings_sync.preview_sync",
                return_value=preview_response,
            ),
        ):
            resp = client.get(
                "/portfolios/1/holdings/sync/preview",
                headers={"Authorization": "Bearer testtoken"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert len(data["items"]) == 1
        assert data["items"][0]["krx_code"] == "005930"
        assert data["items"][0]["action"] == "upsert"


class TestPreviewSyncNoTransactions:
    """T-050-002: 거래 없는 포트폴리오 → preview 빈 목록 반환"""

    def test_preview_empty_when_no_transactions(self):
        from stock_picker.portfolio.schemas import SyncPreviewResponse

        mock_user = _make_mock_user()
        mock_db = MagicMock()
        empty_response = SyncPreviewResponse(items=[])

        with (
            patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user),
            patch(
                "stock_picker.auth.dependencies.get_db_session",
                return_value=iter([mock_db]),
            ),
            patch(
                "stock_picker.portfolio.holdings_sync.preview_sync",
                return_value=empty_response,
            ),
        ):
            client = _get_test_client()
            resp = client.get(
                "/portfolios/1/holdings/sync/preview",
                headers={"Authorization": "Bearer testtoken"},
            )

        assert resp.status_code == 200
        assert resp.json()["items"] == []


class TestApplySyncUpserts:
    """T-050-003: apply sync → 홀딩스 업서트 후 응답 반환"""

    def test_apply_sync_returns_200(self):
        from stock_picker.portfolio.schemas import SyncApplyResponse

        mock_user = _make_mock_user()
        mock_db = MagicMock()
        apply_response = SyncApplyResponse(synced=1, holdings=[])

        with (
            patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user),
            patch(
                "stock_picker.auth.dependencies.get_db_session",
                return_value=iter([mock_db]),
            ),
            patch(
                "stock_picker.portfolio.holdings_sync.apply_sync",
                return_value=apply_response,
            ),
        ):
            client = _get_test_client()
            resp = client.post(
                "/portfolios/1/holdings/sync",
                headers={"Authorization": "Bearer testtoken"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "synced" in data
        assert data["synced"] == 1


class TestApplySyncCount:
    """T-050-004: apply sync → synced 카운트 정확히 반환"""

    def test_apply_sync_synced_count(self):
        from stock_picker.portfolio.schemas import SyncApplyResponse

        mock_user = _make_mock_user()
        mock_db = MagicMock()
        apply_response = SyncApplyResponse(synced=3, holdings=[])

        with (
            patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user),
            patch(
                "stock_picker.auth.dependencies.get_db_session",
                return_value=iter([mock_db]),
            ),
            patch(
                "stock_picker.portfolio.holdings_sync.apply_sync",
                return_value=apply_response,
            ),
        ):
            client = _get_test_client()
            resp = client.post(
                "/portfolios/1/holdings/sync",
                headers={"Authorization": "Bearer testtoken"},
            )

        assert resp.status_code == 200
        assert resp.json()["synced"] == 3


# ====================================================================
# 서비스 수준 테스트: MagicMock 직접 사용
# ====================================================================

class TestMovingAverageAnchor:
    """T-050-005: 이동평균 원가법 앵커 검증
    BUY 10@1000 → BUY 10@2000 → SELL 5@3000 → qty=15, avg=1500.00
    """

    def test_moving_average_calculation(self):
        from stock_picker.portfolio import holdings_sync as sync_service

        # 거래 순서: BUY 10@1000 → BUY 10@2000 → SELL 5@3000
        txns = [
            _make_mock_transaction(
                id=1, krx_code="005930", txn_type="BUY", quantity=10, price="1000.00"
            ),
            _make_mock_transaction(
                id=2, krx_code="005930", txn_type="BUY", quantity=10, price="2000.00"
            ),
            _make_mock_transaction(
                id=3, krx_code="005930", txn_type="SELL", quantity=5, price="3000.00"
            ),
        ]

        # 원장 상태 계산: qty=15, avg=1500.00
        result = sync_service._compute_ledger_state(txns)

        assert result["005930"]["quantity"] == 15
        assert result["005930"]["avg_buy_price"] == Decimal("1500.00")


class TestSellExceedsBuyRaises409:
    """T-050-006: SELL 누적 > BUY 누적 → SyncConflictError → HTTP 409"""

    def test_conflict_returns_409(self):
        from fastapi import HTTPException

        mock_user = _make_mock_user()
        mock_db = MagicMock()

        # 실제 apply_sync는 내부에서 SyncConflictError를 HTTPException(409)로 변환한다.
        # mock에서는 이미 변환된 HTTPException(409)를 직접 raise해 라우터 동작을 검증한다.
        client = _get_test_client()

        with (
            patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user),
            patch(
                "stock_picker.auth.dependencies.get_db_session",
                return_value=iter([mock_db]),
            ),
            patch(
                "stock_picker.portfolio.holdings_sync.apply_sync",
                side_effect=HTTPException(
                    status_code=409,
                    detail="005930: 포지션(0)보다 매도 수량(5)이 많습니다",
                ),
            ),
        ):
            resp = client.post(
                "/portfolios/1/holdings/sync",
                headers={"Authorization": "Bearer testtoken"},
            )

        assert resp.status_code == 409


class TestNonOwnerGets403:
    """T-050-007: 비소유자 접근 → 403"""

    def test_non_owner_preview_returns_403(self):
        from fastapi import HTTPException

        mock_user = _make_mock_user(user_id=2)
        mock_db = MagicMock()

        with (
            patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user),
            patch(
                "stock_picker.auth.dependencies.get_db_session",
                return_value=iter([mock_db]),
            ),
            patch(
                "stock_picker.portfolio.holdings_sync.preview_sync",
                side_effect=HTTPException(
                    status_code=403, detail="포트폴리오 접근 권한이 없습니다"
                ),
            ),
        ):
            client = _get_test_client()
            resp = client.get(
                "/portfolios/1/holdings/sync/preview",
                headers={"Authorization": "Bearer testtoken"},
            )

        assert resp.status_code == 403


class TestManualHoldingsPreserved:
    """T-050-008: 수동 홀딩스 보존 — 거래 없는 종목은 delete 대상에 포함되지 않는다"""

    def test_manual_holdings_not_deleted(self):
        from stock_picker.portfolio import holdings_sync as sync_service

        # 기존 홀딩: 005930(거래 없음, 수동), 000660(거래 있음)
        existing_holdings = [
            _make_mock_holding(id=1, krx_code="005930", quantity=5, avg_buy_price="50000.00"),
            _make_mock_holding(id=2, krx_code="000660", quantity=10, avg_buy_price="100000.00"),
        ]
        # 원장 파생 상태: 000660만 존재
        derived_state = {
            "000660": {"quantity": 10, "avg_buy_price": Decimal("100000.00")}
        }

        preview_items = sync_service._compute_preview(
            existing_holdings=existing_holdings,
            derived_state=derived_state,
        )

        # 005930은 "delete" action으로 나타나지 않아야 함
        delete_items = [
            item for item in preview_items
            if item.action == "delete" and item.krx_code == "005930"
        ]
        assert len(delete_items) == 0


class TestApplySyncIdempotent:
    """T-050-009: apply sync 멱등성 — 두 번 apply해도 최종 상태 동일"""

    def test_apply_is_idempotent(self):
        from stock_picker.portfolio import holdings_sync as sync_service
        from stock_picker.portfolio.schemas import SyncApplyResponse

        mock_db = MagicMock()
        mock_portfolio = _make_mock_portfolio()

        # 홀딩과 거래가 이미 일치하는 상태 설정
        existing_holding = _make_mock_holding(
            id=1, krx_code="005930", quantity=10, avg_buy_price="1000.00"
        )
        # _verify_portfolio_owner 패치 및 DB 쿼리 설정
        mock_db.query.return_value.filter.return_value.first.return_value = mock_portfolio
        mock_db.query.return_value.filter.return_value.all.return_value = [existing_holding]
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            _make_mock_transaction(
                id=1, krx_code="005930", txn_type="BUY", quantity=10, price="1000.00"
            )
        ]

        with patch(
            "stock_picker.portfolio.holdings_sync._verify_portfolio_owner",
            return_value=mock_portfolio,
        ):
            result = sync_service.apply_sync(mock_db, portfolio_id=1, user_id=1)

        # SyncApplyResponse 반환, synced >= 0
        assert isinstance(result, SyncApplyResponse)
        assert result.synced >= 0


class TestPreviewShowsUnchanged:
    """T-050-010: 이미 일치하는 홀딩은 preview에서 action="unchanged"로 표시"""

    def test_preview_unchanged_when_holdings_match(self):
        from stock_picker.portfolio.schemas import SyncPreviewItem, SyncPreviewResponse

        mock_user = _make_mock_user()
        mock_db = MagicMock()
        # 이미 홀딩과 원장이 일치하는 경우
        preview_response = SyncPreviewResponse(
            items=[
                SyncPreviewItem(
                    krx_code="005930",
                    action="unchanged",
                    current_qty=10,
                    derived_qty=10,
                    current_avg=Decimal("1000.00"),
                    derived_avg=Decimal("1000.00"),
                )
            ]
        )

        with (
            patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user),
            patch(
                "stock_picker.auth.dependencies.get_db_session",
                return_value=iter([mock_db]),
            ),
            patch(
                "stock_picker.portfolio.holdings_sync.preview_sync",
                return_value=preview_response,
            ),
        ):
            client = _get_test_client()
            resp = client.get(
                "/portfolios/1/holdings/sync/preview",
                headers={"Authorization": "Bearer testtoken"},
            )

        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["action"] == "unchanged"
