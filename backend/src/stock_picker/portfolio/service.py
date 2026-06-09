# 포트폴리오 서비스 레이어 — CRUD + 성과 계산
import logging
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from stock_picker.db.models import Portfolio, PortfolioHolding

logger = logging.getLogger(__name__)


def create_portfolio(db: Session, user_id: int, name: str) -> Portfolio:
    """새 포트폴리오 생성.

    # @MX:ANCHOR: [AUTO] 포트폴리오 생성 서비스 함수
    # @MX:REASON: router.py, 테스트, 통합 레이어에서 3회 이상 참조
    """
    portfolio = Portfolio(user_id=user_id, name=name)
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return portfolio


def list_portfolios(db: Session, user_id: int) -> list[Portfolio]:
    """사용자의 포트폴리오 목록 조회"""
    return db.query(Portfolio).filter(Portfolio.user_id == user_id).all()


def get_portfolio_with_holdings(
    db: Session, portfolio_id: int, user_id: int
) -> Portfolio | None:
    """포트폴리오와 보유 종목 함께 조회 (소유권 확인 포함)"""
    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
        .first()
    )
    if portfolio is None:
        return None
    # holdings 명시적 로드 (lazy="noload"이므로 직접 쿼리)
    portfolio.holdings = (
        db.query(PortfolioHolding)
        .filter(PortfolioHolding.portfolio_id == portfolio_id)
        .all()
    )
    return portfolio


def add_holding(
    db: Session,
    portfolio_id: int,
    krx_code: str,
    quantity: int,
    avg_buy_price: Decimal,
) -> PortfolioHolding:
    """포트폴리오에 보유 종목 추가"""
    holding = PortfolioHolding(
        portfolio_id=portfolio_id,
        krx_code=krx_code,
        quantity=quantity,
        avg_buy_price=avg_buy_price,
    )
    db.add(holding)
    db.commit()
    db.refresh(holding)
    return holding


def remove_holding(db: Session, holding_id: int) -> None:
    """보유 종목 삭제"""
    holding = db.query(PortfolioHolding).filter(PortfolioHolding.id == holding_id).first()
    if holding is not None:
        db.delete(holding)
        db.commit()


def _get_current_price(krx_code: str) -> float:
    """FinanceDataReader로 현재가 조회.

    # @MX:WARN: [AUTO] 외부 API 호출 — 네트워크 오류 시 fallback 필요
    # @MX:REASON: FinanceDataReader는 동기 HTTP 호출이며 타임아웃 처리 없음

    실패 시 0.0 반환 (호출부에서 처리).
    """
    try:
        import FinanceDataReader as fdr
        df = fdr.DataReader(krx_code)
        if df is None or df.empty:
            logger.warning("가격 데이터 없음 — krx_code=%s", krx_code)
            return 0.0
        close_col = "Close" if "Close" in df.columns else df.columns[-1]
        return float(df[close_col].iloc[-1])
    except Exception:
        logger.exception("현재가 조회 실패 — krx_code=%s", krx_code)
        return 0.0


def calculate_performance(
    db: Session, portfolio_id: int, user_id: int
) -> dict[str, Any]:
    """포트폴리오 성과 계산 — 현재가 기반.

    Returns:
        {
            "holdings": [
                {
                    "krx_code": "005930",
                    "quantity": 10,
                    "avg_buy_price": 70000.0,
                    "current_price": 75000.0,
                    "return_pct": 7.14,
                }
            ],
            "total_invested": 700000.0,
            "total_current": 750000.0,
            "total_return_pct": 7.14,
        }
    """
    portfolio = get_portfolio_with_holdings(db, portfolio_id, user_id)
    if portfolio is None:
        return {
            "holdings": [],
            "total_invested": 0.0,
            "total_current": 0.0,
            "total_return_pct": 0.0,
        }

    holdings_perf = []
    total_invested = 0.0
    total_current = 0.0

    for h in portfolio.holdings:
        buy_price = float(h.avg_buy_price)
        current_price = _get_current_price(h.krx_code)
        invested = buy_price * h.quantity
        current_val = current_price * h.quantity

        # 현재가 조회 실패 시 매수가로 대체
        if current_price == 0.0:
            current_price = buy_price
            current_val = invested

        return_pct = ((current_price - buy_price) / buy_price * 100) if buy_price > 0 else 0.0

        holdings_perf.append({
            "krx_code": h.krx_code,
            "quantity": h.quantity,
            "avg_buy_price": buy_price,
            "current_price": current_price,
            "return_pct": round(return_pct, 2),
        })
        total_invested += invested
        total_current += current_val

    total_return_pct = (
        ((total_current - total_invested) / total_invested * 100)
        if total_invested > 0
        else 0.0
    )

    return {
        "holdings": holdings_perf,
        "total_invested": round(total_invested, 2),
        "total_current": round(total_current, 2),
        "total_return_pct": round(total_return_pct, 2),
    }
