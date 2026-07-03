# 포트폴리오 거래 원장 서비스 (SPEC-STOCK-049)
# 이동평균 원가법 실현손익 계산 포함
# 독립 원장 — PortfolioHolding 자동 갱신 없음
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from stock_picker.db.models import Portfolio, PortfolioTransaction

# @MX:ANCHOR: [AUTO] 거래 원장 서비스 공개 API — router.py에서 직접 호출
# @MX:REASON: add_transaction, list_transactions, get_realized_pnl 3개 함수가 router에서 참조


def _verify_portfolio_owner(db: Session, portfolio_id: int, user_id: int) -> Portfolio:
    """포트폴리오 소유권 확인 — 소유자 아니면 403 발생"""
    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
        .first()
    )
    if portfolio is None:
        raise HTTPException(status_code=403, detail="포트폴리오 접근 권한이 없습니다")
    return portfolio


def add_transaction(
    db: Session,
    portfolio_id: int,
    user_id: int,
    data: Any,
) -> dict:
    """거래 원장에 매수/매도 거래 추가 (SPEC-STOCK-049 REQ-TXN-001·002·003)

    # @MX:NOTE: [AUTO] SELL 검증 — 순보유 초과 시 400 반환 (REQ-TXN-003)
    """
    _verify_portfolio_owner(db, portfolio_id, user_id)

    # SELL 이면 순보유수량 검증 (REQ-TXN-003)
    if hasattr(data, "txn_type"):
        txn_type = data.txn_type
        krx_code = data.krx_code
        quantity = data.quantity
        price = data.price
        txn_date = data.txn_date
        note = getattr(data, "note", None)
    else:
        # dict 형태로도 지원
        txn_type = data["txn_type"]
        krx_code = data["krx_code"]
        quantity = data["quantity"]
        price = data["price"]
        txn_date = data["txn_date"]
        note = data.get("note")

    if txn_type == "SELL":
        # 누적 BUY - 누적 SELL = 순보유수량
        rows = (
            db.query(PortfolioTransaction)
            .filter(
                PortfolioTransaction.portfolio_id == portfolio_id,
                PortfolioTransaction.krx_code == krx_code,
            )
            .all()
        )
        net_qty = sum(
            r.quantity if r.txn_type == "BUY" else -r.quantity
            for r in rows
        )
        if quantity > net_qty:
            raise HTTPException(
                status_code=400,
                detail=f"순보유수량({net_qty})을 초과하는 매도 수량({quantity})은 허용되지 않습니다",
            )

    txn = PortfolioTransaction(
        portfolio_id=portfolio_id,
        krx_code=krx_code,
        txn_type=txn_type,
        quantity=quantity,
        price=price,
        txn_date=txn_date,
        note=note,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)

    return {
        "id": txn.id,
        "portfolio_id": txn.portfolio_id,
        "krx_code": txn.krx_code,
        "txn_type": txn.txn_type,
        "quantity": txn.quantity,
        "price": str(txn.price),
        "txn_date": str(txn.txn_date),
        "note": txn.note,
        "created_at": txn.created_at.isoformat() if txn.created_at else None,
    }


def list_transactions(
    db: Session,
    portfolio_id: int,
    user_id: int,
    krx_code: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """거래 목록 조회 — txn_date 최신순, 페이지네이션 (SPEC-STOCK-049 REQ-TXN-006·007)"""
    _verify_portfolio_owner(db, portfolio_id, user_id)

    q = db.query(PortfolioTransaction).filter(
        PortfolioTransaction.portfolio_id == portfolio_id
    )
    if krx_code:
        q = q.filter(PortfolioTransaction.krx_code == krx_code)

    total = q.count()
    rows = (
        q.order_by(
            PortfolioTransaction.txn_date.desc(),
            PortfolioTransaction.id.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [
        {
            "id": r.id,
            "portfolio_id": r.portfolio_id,
            "krx_code": r.krx_code,
            "txn_type": r.txn_type,
            "quantity": r.quantity,
            "price": str(r.price),
            "txn_date": str(r.txn_date),
            "note": r.note,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]

    return {
        "transactions": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def delete_transaction(
    db: Session,
    portfolio_id: int,
    transaction_id: int,
    user_id: int,
) -> None:
    """거래 삭제 (SPEC-STOCK-049 REQ-TXN-008)"""
    _verify_portfolio_owner(db, portfolio_id, user_id)

    txn = (
        db.query(PortfolioTransaction)
        .filter(
            PortfolioTransaction.id == transaction_id,
            PortfolioTransaction.portfolio_id == portfolio_id,
        )
        .first()
    )
    if txn is None:
        raise HTTPException(status_code=404, detail="거래를 찾을 수 없습니다")

    db.delete(txn)
    db.commit()


def get_realized_pnl(
    db: Session,
    portfolio_id: int,
    user_id: int,
    krx_code: str | None = None,
) -> dict:
    """이동평균 원가법 실현손익 계산 (SPEC-STOCK-049 REQ-TXN-009~013)

    # @MX:NOTE: [AUTO] 이동평균 원가법 — BUY 시 원가 갱신, SELL 시 realized 누적
    # 앵커: BUY 10@1000, BUY 10@2000, SELL 5@3000 → realized=7500 (AC-049-009)
    """
    _verify_portfolio_owner(db, portfolio_id, user_id)

    q = db.query(PortfolioTransaction).filter(
        PortfolioTransaction.portfolio_id == portfolio_id
    )
    if krx_code:
        q = q.filter(PortfolioTransaction.krx_code == krx_code)

    # traded_at ASC, id ASC 정렬 (결정적 순서 보장)
    rows = q.order_by(
        PortfolioTransaction.txn_date.asc(),
        PortfolioTransaction.id.asc(),
    ).all()

    # 종목별 이동평균 원가법 리플레이
    # 상태: position(수량), cost(총원가), realized(실현손익)
    per_ticker: dict[str, dict] = defaultdict(
        lambda: {"position": 0, "cost": Decimal("0"), "realized": Decimal("0")}
    )

    for row in rows:
        code = row.krx_code
        state = per_ticker[code]
        qty = Decimal(str(row.quantity))
        price = Decimal(str(row.price))

        if row.txn_type == "BUY":
            # BUY: cost += price*qty, position += qty
            state["cost"] += price * qty
            state["position"] += row.quantity
        elif row.txn_type == "SELL":
            if state["position"] > 0:
                # 이동평균 원가
                avg_cost = state["cost"] / Decimal(str(state["position"]))
                # 실현손익 += 매도대금 - 매도수량의 평균원가
                realized = (price - avg_cost) * qty
                state["realized"] += realized
                # 원가 차감 (position 감소만큼)
                state["cost"] -= avg_cost * qty
                state["position"] -= row.quantity

    # 응답 구성
    items = [
        {
            "krx_code": code,
            "realized_pnl": state["realized"].quantize(Decimal("0.01")),
            "total_sold_qty": 0,  # 세부 통계는 향후 확장 가능
        }
        for code, state in per_ticker.items()
    ]

    total = sum(item["realized_pnl"] for item in items)

    return {
        "items": items,
        "total_realized_pnl": total.quantize(Decimal("0.01")) if items else Decimal("0"),
    }
