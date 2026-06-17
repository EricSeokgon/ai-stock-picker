# 포트폴리오 서비스 레이어 — CRUD + 성과 계산 + AI 최적화 (SPEC-STOCK-017·026 확장)
import logging
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any

import redis.asyncio as aioredis
from sqlalchemy.orm import Session

from stock_picker.db.models import Portfolio, PortfolioHolding
from stock_picker.portfolio.utils import get_sector
from stock_picker.realtime.price_feed import get_current_price

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


def _classify(return_pct: float) -> str:
    """수익률 기반 성과 분류.

    # @MX:NOTE: [AUTO] REQ-PERF-003 분류 기준 — high: >=+5%, low: <=-5%, 나머지: normal
    """
    if return_pct >= 5.0:
        return "high"
    if return_pct <= -5.0:
        return "low"
    return "normal"


def calculate_performance(
    db: Session, portfolio_id: int, user_id: int
) -> dict[str, Any]:
    """포트폴리오 성과 계산 — Redis 캐시 현재가 기반 (SPEC-STOCK-017).

    # @MX:ANCHOR: [AUTO] calculate_performance — router, tests 3곳 이상에서 참조
    # @MX:REASON: [AUTO] 성과 API의 단일 계산 진입점 (SPEC-STOCK-017 REQ-PERF-001~009)

    Returns:
        {
            "holdings": [...],
            "total_invested": float,
            "total_current": float,
            "total_return_pct": float,
            "classification_summary": {"high": {...}, "normal": {...}, "low": {...}},
            "sector_performance": [...],
        }
    """
    _empty_summary = {
        "high": {"count": 0, "invested": 0.0, "invested_pct": 0.0},
        "normal": {"count": 0, "invested": 0.0, "invested_pct": 0.0},
        "low": {"count": 0, "invested": 0.0, "invested_pct": 0.0},
    }

    portfolio = get_portfolio_with_holdings(db, portfolio_id, user_id)
    if portfolio is None:
        return {
            "holdings": [],
            "total_invested": 0.0,
            "total_current": 0.0,
            "total_return_pct": 0.0,
            "classification_summary": _empty_summary,
            "sector_performance": [],
        }

    holdings_perf: list[dict[str, Any]] = []
    total_invested = 0.0
    total_current = 0.0
    # 섹터별 집계용 임시 구조
    sector_map: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"invested": 0.0, "current": 0.0, "count": 0}
    )

    for h in portfolio.holdings:
        buy_price = float(h.avg_buy_price)
        invested = buy_price * h.quantity

        # Redis 캐시 지원 현재가 조회 (get_current_price: dict | None)
        price_result = get_current_price(h.krx_code)
        price_unavailable = price_result is None

        if price_unavailable:
            # 현재가 미수신 시 매수가로 대체, 수익률 0
            current_price = buy_price
            current_val = invested
            return_pct = 0.0
            logger.warning("현재가 조회 실패 — krx_code=%s, 매수가로 대체", h.krx_code)
        else:
            current_price = float(price_result["price"])  # type: ignore[index]
            current_val = current_price * h.quantity
            # 매입가 0 → 0 나눗셈 방지
            return_pct = (
                ((current_price - buy_price) / buy_price * 100) if buy_price > 0 else 0.0
            )

        classification = _classify(return_pct)
        sector = get_sector(h.krx_code)

        holdings_perf.append({
            "krx_code": h.krx_code,
            "quantity": h.quantity,
            "avg_buy_price": buy_price,
            "current_price": current_price,
            "return_pct": round(return_pct, 2),
            "classification": classification,
            "sector": sector,
            "price_unavailable": price_unavailable,
        })

        total_invested += invested
        total_current += current_val

        # 섹터 집계
        sector_map[sector]["invested"] += invested
        sector_map[sector]["current"] += current_val
        sector_map[sector]["count"] += 1

    total_return_pct = (
        ((total_current - total_invested) / total_invested * 100)
        if total_invested > 0
        else 0.0
    )

    # classification_summary 계산
    summary: dict[str, dict[str, Any]] = {
        "high": {"count": 0, "invested": 0.0, "invested_pct": 0.0},
        "normal": {"count": 0, "invested": 0.0, "invested_pct": 0.0},
        "low": {"count": 0, "invested": 0.0, "invested_pct": 0.0},
    }
    for hp in holdings_perf:
        cls = hp["classification"]
        invested_val = hp["avg_buy_price"] * hp["quantity"]
        summary[cls]["count"] += 1
        summary[cls]["invested"] += invested_val

    if total_invested > 0:
        for cls in summary:
            summary[cls]["invested_pct"] = round(
                summary[cls]["invested"] / total_invested * 100, 2
            )

    # sector_performance 계산 (투자금 내림차순 정렬)
    sector_perf = []
    for sector_name, data in sector_map.items():
        s_invested = data["invested"]
        s_current = data["current"]
        s_return_pct = (
            ((s_current - s_invested) / s_invested * 100) if s_invested > 0 else 0.0
        )
        sector_perf.append({
            "sector": sector_name,
            "holding_count": data["count"],
            "invested": round(s_invested, 2),
            "return_pct": round(s_return_pct, 2),
        })
    sector_perf.sort(key=lambda x: x["invested"], reverse=True)

    return {
        "holdings": holdings_perf,
        "total_invested": round(total_invested, 2),
        "total_current": round(total_current, 2),
        "total_return_pct": round(total_return_pct, 2),
        "classification_summary": summary,
        "sector_performance": sector_perf,
    }


# @MX:ANCHOR: [AUTO] 포트폴리오 AI 최적화 단일 진입점
# @MX:REASON: router.py 및 테스트에서 호출
async def optimize_portfolio(
    portfolio_id: int,
    user_id: int,
    db: Session,
    redis: aioredis.Redis,
    refresh: bool = False,
) -> Any:
    """포트폴리오 AI 최적화 분석 (SPEC-STOCK-026 REQ-OPT-001~005).

    1. 포트폴리오 소유권 확인 (403)
    2. Redis 캐시 확인 (key: portfolio_optimize:{portfolio_id}:{today})
    3. 보유 종목 없으면 메시지 반환
    4. Claude AI로 최적화 분석
    5. action 서버 재계산 (2% 임계값), score 계산
    6. 결과 Redis 캐싱 (TTL=3600s)

    Returns:
        OptimizeResult 또는 {"message": str}
    """
    from stock_picker.portfolio.ai_analysis import optimize_portfolio_with_claude
    from stock_picker.portfolio.schemas import (
        NewStockItem,
        OptimizeResult,
        ScoreBreakdown,
        TargetWeightItem,
    )

    # 포트폴리오 소유권 확인
    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
        .first()
    )
    if portfolio is None:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="포트폴리오에 접근할 수 없습니다",
        )

    # Redis 캐시 확인
    today = date.today().isoformat()
    cache_key = f"portfolio_optimize:{portfolio_id}:{today}"

    if not refresh:
        cached = await redis.get(cache_key)
        if cached:
            return OptimizeResult.model_validate_json(cached)

    # 보유 종목 조회
    holdings = (
        db.query(PortfolioHolding)
        .filter(PortfolioHolding.portfolio_id == portfolio_id)
        .all()
    )

    if not holdings:
        return {"message": "분석할 보유 종목이 없습니다."}

    # 현재 비중 계산
    total_value = sum(float(h.avg_buy_price) * h.quantity for h in holdings)
    holdings_data = []
    portfolio_codes = [h.krx_code for h in holdings]

    for h in holdings:
        invested = float(h.avg_buy_price) * h.quantity
        weight_pct = round((invested / total_value * 100), 2) if total_value > 0 else 0.0
        holdings_data.append({
            "krx_code": h.krx_code,
            "quantity": h.quantity,
            "avg_buy_price": float(h.avg_buy_price),
            "invested_amount": round(invested, 2),
            "weight_pct": weight_pct,
            "sector": get_sector(h.krx_code),
        })

    # Claude AI 최적화 분석 호출
    raw = await optimize_portfolio_with_claude(holdings_data, portfolio_codes, db)

    # score_breakdown 파싱
    bd = raw.get("score_breakdown", {})
    diversification = int(bd.get("diversification", 50))
    risk_balance = int(bd.get("risk_balance", 50))
    momentum = int(bd.get("momentum", 50))
    # 범위 클램핑
    diversification = max(0, min(100, diversification))
    risk_balance = max(0, min(100, risk_balance))
    momentum = max(0, min(100, momentum))
    score = int(round((diversification + risk_balance + momentum) / 3))

    # target_weights — action 서버 재계산 (2% 임계값)
    current_pct_map = {item["krx_code"]: item["weight_pct"] for item in holdings_data}
    target_weight_items = []
    for tw in raw.get("target_weights", []):
        krx_code = tw["krx_code"]
        current_pct = float(tw.get("current_pct", current_pct_map.get(krx_code, 0.0)))
        target_pct = float(tw["target_pct"])
        delta_pct = target_pct - current_pct

        if delta_pct > 2.0:
            action = "buy"
        elif delta_pct < -2.0:
            action = "sell"
        else:
            action = "hold"

        # delta_shares: 단순 비중 차이 기반 (avg_buy_price 사용)
        holding_map = {h.krx_code: h for h in holdings}
        h = holding_map.get(krx_code)
        if h and float(h.avg_buy_price) > 0 and total_value > 0:
            delta_value = (delta_pct / 100) * total_value
            delta_shares = int(delta_value / float(h.avg_buy_price))
        else:
            delta_shares = 0

        target_weight_items.append(TargetWeightItem(
            krx_code=krx_code,
            current_pct=current_pct,
            target_pct=target_pct,
            action=action,
            delta_shares=delta_shares,
        ))

    # new_stocks — 포트폴리오 보유 종목 제외, 최대 5개
    new_stock_items = []
    for ns in raw.get("new_stocks", [])[:5]:
        if ns["krx_code"] not in portfolio_codes:
            new_stock_items.append(NewStockItem(
                krx_code=ns["krx_code"],
                name=ns.get("name", ""),
                sector=ns.get("sector", "기타"),
                reason=ns.get("reason", ""),
            ))

    result = OptimizeResult(
        score=score,
        score_breakdown=ScoreBreakdown(
            diversification=diversification,
            risk_balance=risk_balance,
            momentum=momentum,
        ),
        target_weights=target_weight_items,
        new_stocks=new_stock_items,
        summary=raw.get("summary", ""),
    )

    # Redis 캐싱 (TTL=3600s)
    await redis.setex(cache_key, 3600, result.model_dump_json())

    return result
