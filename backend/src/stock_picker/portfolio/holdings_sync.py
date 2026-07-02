"""
SPEC-STOCK-050: 거래 기반 홀딩스 동기화 서비스

원장(portfolio_transactions)을 단일 진실 공급원으로 사용해
portfolio_holdings를 재계산·동기화한다.

핵심 규칙:
- 명시적 동기화만: add_transaction/delete_transaction 호출 시 자동 트리거 없음
- 이동평균 원가법으로 avg_buy_price 계산
- SELL > BUY 누적이면 SyncConflictError 발생, 홀딩 불변
- 수동 홀딩 보존: 원장에 거래 없는 종목의 기존 홀딩은 건드리지 않음
- float 금지, Decimal 사용
"""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from fastapi import HTTPException
from sqlalchemy.orm import Session

from stock_picker.db.models import PortfolioHolding, PortfolioTransaction
from stock_picker.portfolio.schemas import (
    SyncApplyResponse,
    SyncHoldingItem,
    SyncPreviewItem,
    SyncPreviewResponse,
)
from stock_picker.portfolio.transactions import _verify_portfolio_owner

if TYPE_CHECKING:
    pass


# @MX:NOTE: [AUTO] SyncConflictError — SELL 누적 > BUY 누적 시 발생하는 도메인 예외
# @MX:SPEC: SPEC-STOCK-050 REQ-SYNC-007
class SyncConflictError(Exception):
    """SELL 누적 수량이 BUY 누적 수량을 초과할 때 발생"""

    def __init__(self, krx_code: str, position: int, sell_qty: int) -> None:
        self.krx_code = krx_code
        self.position = position
        self.sell_qty = sell_qty
        super().__init__(
            f"{krx_code}: 포지션({position})보다 매도 수량({sell_qty})이 많습니다"
        )


# @MX:ANCHOR: [AUTO] _compute_ledger_state — 이동평균 원가법 계산 핵심 함수
# @MX:REASON: preview_sync, apply_sync 양쪽에서 호출하는 단일 계산 로직
# @MX:SPEC: SPEC-STOCK-050 REQ-SYNC-003·REQ-SYNC-007
def _compute_ledger_state(
    transactions: list[PortfolioTransaction],
) -> dict[str, dict]:
    """거래 목록에서 이동평균 원가법으로 원장 상태를 계산한다.

    반환값 예시:
        {
            "005930": {"quantity": 15, "avg_buy_price": Decimal("1500.00")},
        }

    SyncConflictError: SELL 수량이 현재 포지션을 초과하면 발생
    """
    state: dict[str, dict] = {}

    for txn in transactions:
        code = txn.krx_code
        if code not in state:
            state[code] = {"quantity": 0, "cost": Decimal("0")}

        qty = Decimal(str(txn.quantity))
        price = Decimal(str(txn.price))

        if txn.txn_type == "BUY":
            state[code]["cost"] += price * qty
            state[code]["quantity"] += txn.quantity
        elif txn.txn_type == "SELL":
            current_pos = state[code]["quantity"]
            if current_pos < txn.quantity:
                raise SyncConflictError(
                    krx_code=code,
                    position=current_pos,
                    sell_qty=txn.quantity,
                )
            if current_pos > 0:
                avg = state[code]["cost"] / Decimal(str(current_pos))
                state[code]["cost"] -= avg * qty
            state[code]["quantity"] -= txn.quantity

    # 이동평균 단가 계산 후 정리
    result: dict[str, dict] = {}
    for code, s in state.items():
        qty = s["quantity"]
        if qty > 0:
            avg = (s["cost"] / Decimal(str(qty))).quantize(Decimal("0.01"))
            result[code] = {"quantity": qty, "avg_buy_price": avg}
        # qty == 0 : 포지션 소진, 결과에 포함하지 않음

    return result


def _compute_preview(
    existing_holdings: list[PortfolioHolding],
    derived_state: dict[str, dict],
) -> list[SyncPreviewItem]:
    """현재 홀딩 목록과 원장 파생 상태를 비교해 변경 항목을 반환한다.

    수동 홀딩 보존 규칙:
      - 원장에 거래가 있는 종목만 upsert/unchanged/delete 판단
      - 원장에 거래가 없는 종목의 기존 홀딩은 결과에 포함하지 않음
        (즉, delete 대상으로 표시하지 않음)
    """
    existing: dict[str, PortfolioHolding] = {h.krx_code: h for h in existing_holdings}
    items: list[SyncPreviewItem] = []

    # 원장에 거래가 있는 종목만 처리
    for code, derived in derived_state.items():
        current = existing.get(code)
        if current is None:
            # 신규 홀딩 필요
            items.append(
                SyncPreviewItem(
                    krx_code=code,
                    action="upsert",
                    current_qty=0,
                    derived_qty=derived["quantity"],
                    current_avg=None,
                    derived_avg=derived["avg_buy_price"],
                )
            )
        else:
            current_avg = Decimal(str(current.avg_buy_price)).quantize(Decimal("0.01"))
            derived_avg = derived["avg_buy_price"]
            if current.quantity == derived["quantity"] and current_avg == derived_avg:
                items.append(
                    SyncPreviewItem(
                        krx_code=code,
                        action="unchanged",
                        current_qty=current.quantity,
                        derived_qty=derived["quantity"],
                        current_avg=current_avg,
                        derived_avg=derived_avg,
                    )
                )
            else:
                items.append(
                    SyncPreviewItem(
                        krx_code=code,
                        action="upsert",
                        current_qty=current.quantity,
                        derived_qty=derived["quantity"],
                        current_avg=current_avg,
                        derived_avg=derived_avg,
                    )
                )

    return items


# @MX:ANCHOR: [AUTO] preview_sync — 홀딩스 동기화 프리뷰 공개 API
# @MX:REASON: router.py 엔드포인트 GET /{id}/holdings/sync/preview에서 호출
# @MX:SPEC: SPEC-STOCK-050 REQ-SYNC-004·REQ-SYNC-005
def preview_sync(
    db: Session,
    portfolio_id: int,
    user_id: int,
) -> SyncPreviewResponse:
    """거래 원장 기반 홀딩스 동기화 변경 사항을 미리 보여준다 (DB 변경 없음).

    Raises:
        HTTPException(403): 포트폴리오 소유자가 아닌 경우
        HTTPException(409): SELL > BUY 누적으로 포지션 음수가 되는 경우
    """
    # 소유권 검증 (SPEC-049와 동일한 규약 재사용)
    _verify_portfolio_owner(db, portfolio_id, user_id)

    # 거래 조회: txn_date ASC, id ASC 순서로 재현
    transactions = (
        db.query(PortfolioTransaction)
        .filter(PortfolioTransaction.portfolio_id == portfolio_id)
        .order_by(PortfolioTransaction.txn_date.asc(), PortfolioTransaction.id.asc())
        .all()
    )

    # 원장 상태 계산
    try:
        derived_state = _compute_ledger_state(transactions)
    except SyncConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    # 현재 홀딩 조회
    existing_holdings = (
        db.query(PortfolioHolding)
        .filter(PortfolioHolding.portfolio_id == portfolio_id)
        .all()
    )

    items = _compute_preview(existing_holdings, derived_state)
    return SyncPreviewResponse(items=items)


# @MX:ANCHOR: [AUTO] apply_sync — 홀딩스 동기화 적용 공개 API
# @MX:REASON: router.py 엔드포인트 POST /{id}/holdings/sync에서 호출
# @MX:SPEC: SPEC-STOCK-050 REQ-SYNC-008·REQ-SYNC-009·REQ-SYNC-010
def apply_sync(
    db: Session,
    portfolio_id: int,
    user_id: int,
) -> SyncApplyResponse:
    """거래 원장 기반 홀딩스 동기화를 적용한다.

    - upsert: 원장 기반 수량/단가로 홀딩 생성 또는 갱신
    - 수동 홀딩 보존: 원장에 거래 없는 종목은 건드리지 않음
    - SyncConflictError 발생 시 트랜잭션 롤백, 홀딩 불변

    Raises:
        HTTPException(403): 포트폴리오 소유자가 아닌 경우
        HTTPException(409): SELL > BUY 누적으로 포지션 음수가 되는 경우
    """
    # 소유권 검증
    _verify_portfolio_owner(db, portfolio_id, user_id)

    # 거래 조회
    transactions = (
        db.query(PortfolioTransaction)
        .filter(PortfolioTransaction.portfolio_id == portfolio_id)
        .order_by(PortfolioTransaction.txn_date.asc(), PortfolioTransaction.id.asc())
        .all()
    )

    # 원장 상태 계산 — 불일치 감지 시 전체 거부
    try:
        derived_state = _compute_ledger_state(transactions)
    except SyncConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    # 현재 홀딩 조회
    existing_holdings = (
        db.query(PortfolioHolding)
        .filter(PortfolioHolding.portfolio_id == portfolio_id)
        .all()
    )
    existing: dict[str, PortfolioHolding] = {h.krx_code: h for h in existing_holdings}

    synced_count = 0
    result_holdings: list[SyncHoldingItem] = []

    # 원장 기반 종목만 upsert (수동 홀딩은 건드리지 않음)
    for code, derived in derived_state.items():
        qty = derived["quantity"]
        avg = derived["avg_buy_price"]
        holding = existing.get(code)

        if holding is None:
            # 신규 홀딩 생성
            new_holding = PortfolioHolding(
                portfolio_id=portfolio_id,
                krx_code=code,
                quantity=qty,
                avg_buy_price=avg,
                market="KRX",
                currency="KRW",
            )
            db.add(new_holding)
            synced_count += 1
        else:
            current_avg = Decimal(str(holding.avg_buy_price)).quantize(Decimal("0.01"))
            if holding.quantity != qty or current_avg != avg:
                holding.quantity = qty
                holding.avg_buy_price = avg
                synced_count += 1

        result_holdings.append(
            SyncHoldingItem(krx_code=code, quantity=qty, avg_buy_price=avg)
        )

    db.commit()

    return SyncApplyResponse(synced=synced_count, holdings=result_holdings)
