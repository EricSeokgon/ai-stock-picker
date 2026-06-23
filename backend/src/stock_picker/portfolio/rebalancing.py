# @MX:NOTE: [AUTO] SPEC-STOCK-032 포트폴리오 리밸런싱 자동화 모듈
# @MX:SPEC: SPEC-STOCK-032
# scipy 사용 금지 (NFR-001) — numpy + math만 허용
# 이 모듈은 순수 함수로 구성되어 DB 의존성이 없음
from __future__ import annotations

import json
import logging
import math
from typing import Any

from stock_picker.portfolio.schemas import (
    RebalancingOrder,
    RebalancingOrderPlan,
)

# 서비스 함수 — 순환 임포트 방지를 위해 지연 임포트 후 모듈 참조로 패치 가능하도록 노출
# 실제 함수는 calculate_rebalancing_plan 내부에서 지연 임포트
def get_portfolio_with_holdings(db: Any, portfolio_id: int, user_id: int) -> Any:
    """포트폴리오 소유권 확인 래퍼 — 테스트 패치용 프록시"""
    from stock_picker.portfolio.service import get_portfolio_with_holdings as _impl
    return _impl(db, portfolio_id, user_id)


async def get_portfolio_performance(
    portfolio_id: int,
    user_id: int,
    db: Any,
    redis: Any,
) -> Any:
    """포트폴리오 성과 조회 래퍼 — 테스트 패치용 프록시"""
    from stock_picker.portfolio.service import calculate_performance as _impl
    return await _impl(db=db, portfolio_id=portfolio_id, user_id=user_id, redis=redis)


async def optimize_portfolio(
    portfolio_id: int,
    user_id: int,
    db: Any,
    redis: Any,
) -> Any:
    """AI 최적화 래퍼 — 테스트 패치용 프록시"""
    from stock_picker.portfolio.service import optimize_portfolio as _impl
    return await _impl(portfolio_id=portfolio_id, user_id=user_id, db=db, redis=redis)

logger = logging.getLogger(__name__)


# @MX:ANCHOR: [AUTO] calculate_rebalancing_orders — 리밸런싱 핵심 순수 함수
# @MX:REASON: 라우터, 서비스, 테스트 등 3곳 이상 참조되는 공개 API 경계
# @MX:SPEC: SPEC-STOCK-032 REQ-RBA-001~006
# @MX:WARN: [AUTO] float 연산 정밀도 주의 — 수량 계산 시 floor/ceil 처리 필수
# @MX:REASON: 부동소수점 오차로 수량이 의도와 다르게 계산될 수 있음 (예: 2.9999 → 2주)
def calculate_rebalancing_orders(
    holdings: list[dict[str, Any]],
    target_weights: dict[str, float],
    budget: float,
    commission_rate_domestic: float = 0.00015,
    commission_rate_foreign: float = 0.0025,
) -> list[RebalancingOrder]:
    """보유 종목과 목표 비중을 입력받아 리밸런싱 주문 목록을 반환한다.

    Args:
        holdings: 보유 종목 리스트. 각 항목은 다음 키를 포함한다.
            - krx_code (str): 종목 코드
            - stock_name (str): 종목명
            - quantity (int): 보유 수량
            - current_price_krw (float): 현재가 (KRW 환산)
            - market (str): "KRX" | "NYSE" | "NASDAQ"
            - price_unavailable (bool): 현재가 미수신 여부
        target_weights: {krx_code: target_pct} 형태의 목표 비중 (0~100 범위)
        budget: 매수에 사용 가능한 예산 (KRW)
        commission_rate_domestic: 국내 KRX 수수료율 (기본 0.015%)
        commission_rate_foreign: 해외 NYSE/NASDAQ 수수료율 (기본 0.25%)

    Returns:
        매수→매도→홀드 순으로 정렬된 RebalancingOrder 리스트 (RBA-004)
    """
    # 현재 총 평가액 계산 (현재가 미수신 종목은 0으로 처리)
    total_value = sum(
        h["current_price_krw"] * h["quantity"]
        for h in holdings
        if not h.get("price_unavailable", False)
    )
    # total_value가 0이면 budget을 기준 총액으로 사용 (신규 투자 케이스)
    if total_value <= 0:
        total_value = budget

    # 현재 보유 가치 맵 {krx_code: current_value_krw}
    current_value_map: dict[str, float] = {
        h["krx_code"]: h["current_price_krw"] * h["quantity"]
        for h in holdings
    }

    # 현재 비중 계산 {krx_code: current_pct}
    current_weight_map: dict[str, float] = {}
    for h in holdings:
        code = h["krx_code"]
        val = current_value_map.get(code, 0.0)
        current_weight_map[code] = (val / total_value * 100) if total_value > 0 else 0.0

    # 각 종목의 목표 금액과 현재 금액의 차이(delta_value) 계산
    # delta_value > 0: 매수, delta_value < 0: 매도, ≈0: 홀드
    holding_map = {h["krx_code"]: h for h in holdings}

    # 예산 추적 — 누적 매수 금액이 budget을 초과하면 해당 종목은 홀드
    remaining_budget = budget

    raw_orders: list[dict[str, Any]] = []

    # 매수 우선순위를 위해 delta_value 내림차순 정렬 후 처리
    codes = list(target_weights.keys())
    codes_sorted = sorted(
        codes,
        key=lambda c: (
            target_weights.get(c, 0.0) / 100 * total_value
            - current_value_map.get(c, 0.0)
        ),
        reverse=True,  # delta 큰 순(가장 많이 사야 할 종목 먼저)
    )

    for code in codes_sorted:
        h = holding_map.get(code)
        if h is None:
            logger.warning("holdings에 없는 종목 코드 무시: %s", code)
            continue

        price = h["current_price_krw"]
        quantity_held = h["quantity"]
        market = h.get("market", "KRX")
        price_unavailable = h.get("price_unavailable", False)
        stock_name = h.get("stock_name", code)

        target_pct = target_weights.get(code, 0.0)
        current_pct = current_weight_map.get(code, 0.0)

        # 현재가 미수신 종목은 항상 홀드 (NFR-004)
        if price_unavailable or price <= 0:
            raw_orders.append({
                "krx_code": code,
                "stock_name": stock_name,
                "action": "hold",
                "quantity": 0,
                "estimated_price": price,
                "estimated_amount": 0.0,
                "estimated_commission": 0.0,
                "current_weight": current_pct,
                "target_weight": target_pct,
                "expected_weight_after": current_pct,
            })
            continue

        # 목표 금액과 현재 금액 계산
        target_value = target_pct / 100 * total_value
        current_value = current_value_map.get(code, 0.0)
        delta_value = target_value - current_value

        # 수수료율 결정 (RBA-003)
        commission_rate = (
            commission_rate_foreign if market in ("NYSE", "NASDAQ")
            else commission_rate_domestic
        )

        if delta_value > 0:
            # 매수: 정수 수량(floor), 예산 제약 적용 (RBA-001, RBA-002)
            max_buyable_by_budget = remaining_budget / price if price > 0 else 0
            ideal_quantity = delta_value / price
            buy_quantity = int(math.floor(min(ideal_quantity, max_buyable_by_budget)))

            if buy_quantity <= 0:
                # 예산 소진 → 홀드로 전환 (RBA-002)
                raw_orders.append({
                    "krx_code": code,
                    "stock_name": stock_name,
                    "action": "hold",
                    "quantity": 0,
                    "estimated_price": price,
                    "estimated_amount": 0.0,
                    "estimated_commission": 0.0,
                    "current_weight": current_pct,
                    "target_weight": target_pct,
                    "expected_weight_after": current_pct,
                })
                continue

            buy_amount = buy_quantity * price
            commission = buy_amount * commission_rate
            remaining_budget -= buy_amount

            # 매수 후 예상 비중 계산
            new_value = current_value + buy_amount
            expected_weight = (new_value / total_value * 100) if total_value > 0 else 0.0

            raw_orders.append({
                "krx_code": code,
                "stock_name": stock_name,
                "action": "buy",
                "quantity": buy_quantity,
                "estimated_price": price,
                "estimated_amount": buy_amount,
                "estimated_commission": commission,
                "current_weight": current_pct,
                "target_weight": target_pct,
                "expected_weight_after": round(expected_weight, 2),
            })

        elif delta_value < 0:
            # 매도: 정수 수량(ceil), 보유 수량 초과 불가 (RBA-001)
            sell_value = abs(delta_value)
            ideal_sell_quantity = sell_value / price
            sell_quantity = min(
                int(math.ceil(ideal_sell_quantity)),
                quantity_held,
            )

            if sell_quantity <= 0:
                # 매도 수량 0이면 홀드
                raw_orders.append({
                    "krx_code": code,
                    "stock_name": stock_name,
                    "action": "hold",
                    "quantity": 0,
                    "estimated_price": price,
                    "estimated_amount": 0.0,
                    "estimated_commission": 0.0,
                    "current_weight": current_pct,
                    "target_weight": target_pct,
                    "expected_weight_after": current_pct,
                })
                continue

            sell_amount = sell_quantity * price
            commission = sell_amount * commission_rate

            # 매도 후 예상 비중
            new_value = current_value - sell_amount
            expected_weight = (new_value / total_value * 100) if total_value > 0 else 0.0

            raw_orders.append({
                "krx_code": code,
                "stock_name": stock_name,
                "action": "sell",
                "quantity": sell_quantity,
                "estimated_price": price,
                "estimated_amount": sell_amount,
                "estimated_commission": commission,
                "current_weight": current_pct,
                "target_weight": target_pct,
                "expected_weight_after": max(0.0, round(expected_weight, 2)),
            })

        else:
            # 홀드: 비중이 정확히 일치
            raw_orders.append({
                "krx_code": code,
                "stock_name": stock_name,
                "action": "hold",
                "quantity": 0,
                "estimated_price": price,
                "estimated_amount": 0.0,
                "estimated_commission": 0.0,
                "current_weight": current_pct,
                "target_weight": target_pct,
                "expected_weight_after": current_pct,
            })

    # 정렬: 매수 → 매도 → 홀드 (RBA-004)
    action_priority = {"buy": 0, "sell": 1, "hold": 2}
    raw_orders.sort(key=lambda o: action_priority[o["action"]])

    return [RebalancingOrder(**o) for o in raw_orders]


async def calculate_rebalancing_plan(
    portfolio_id: int,
    user_id: int,
    db: Any,
    redis: Any,
    budget: float | None = None,
    commission_rate_domestic: float = 0.00015,
    commission_rate_foreign: float = 0.0025,
    dry_run: bool = True,
) -> RebalancingOrderPlan:
    """포트폴리오 리밸런싱 계획을 계산하고 선택적으로 DB에 저장한다 (RBA-005).

    Args:
        portfolio_id: 포트폴리오 ID
        user_id: 요청 사용자 ID (소유권 검증용)
        db: SQLAlchemy 세션
        redis: Redis 클라이언트
        budget: 매수 예산 (None이면 총 평가액 사용)
        commission_rate_domestic: 국내 수수료율
        commission_rate_foreign: 해외 수수료율
        dry_run: True이면 계획만 반환, False이면 DB 저장 포함

    Returns:
        RebalancingOrderPlan

    Raises:
        HTTPException 404: 포트폴리오 미존재 또는 소유권 불일치
    """
    from fastapi import HTTPException, status

    # 소유권 확인 (NFR-005: 404 반환)
    portfolio = get_portfolio_with_holdings(db, portfolio_id, user_id)
    if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="포트폴리오를 찾을 수 없습니다",
        )

    # 현재가 및 포트폴리오 성과 데이터 조회
    performance = await get_portfolio_performance(
        portfolio_id=portfolio_id,
        user_id=user_id,
        db=db,
        redis=redis,
    )
    holdings_data = performance.get("holdings", [])

    if not holdings_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="보유 종목이 없어 리밸런싱 계획을 생성할 수 없습니다",
        )

    # 총 평가액 계산 (예산 기본값)
    total_value = sum(
        h.get("current_value", 0.0)
        for h in holdings_data
        if not h.get("price_unavailable", False)
    )
    effective_budget = budget if budget is not None else total_value

    # AI 최적화로 목표 비중 획득
    optimize_result = await optimize_portfolio(
        portfolio_id=portfolio_id,
        user_id=user_id,
        db=db,
        redis=redis,
    )

    # target_weights 추출 {krx_code: target_pct}
    if hasattr(optimize_result, "target_weights"):
        target_weights = {
            tw.krx_code: tw.target_pct
            for tw in optimize_result.target_weights
        }
    else:
        target_weights = {}

    # holdings_data를 calculate_rebalancing_orders 입력 형식으로 변환
    holdings_for_calc = []
    for h in holdings_data:
        holdings_for_calc.append({
            "krx_code": h["krx_code"],
            "stock_name": h.get("stock_name", h["krx_code"]),
            "quantity": h.get("quantity", 0),
            "current_price_krw": h.get("current_price", 0.0),
            "market": h.get("market", "KRX"),
            "price_unavailable": h.get("price_unavailable", False),
        })

    # 순수 함수로 주문 계획 계산
    orders = calculate_rebalancing_orders(
        holdings=holdings_for_calc,
        target_weights=target_weights,
        budget=effective_budget,
        commission_rate_domestic=commission_rate_domestic,
        commission_rate_foreign=commission_rate_foreign,
    )

    total_buy_amount = sum(o.estimated_amount for o in orders if o.action == "buy")
    total_sell_amount = sum(o.estimated_amount for o in orders if o.action == "sell")
    total_commission = sum(o.estimated_commission for o in orders)

    plan = RebalancingOrderPlan(
        portfolio_id=portfolio_id,
        budget=effective_budget,
        total_buy_amount=total_buy_amount,
        total_sell_amount=total_sell_amount,
        total_commission=total_commission,
        orders=orders,
    )

    # dry_run=False이면 DB에 저장 (RBA-005)
    if not dry_run:
        from stock_picker.db.models import RebalancingPlan

        orders_json = json.dumps(
            [o.model_dump() for o in orders],
            ensure_ascii=False,
            default=str,
        )
        db_plan = RebalancingPlan(
            portfolio_id=portfolio_id,
            user_id=user_id,
            budget=effective_budget,
            total_buy_amount=total_buy_amount,
            total_sell_amount=total_sell_amount,
            total_commission=total_commission,
            orders_json=orders_json,
        )
        db.add(db_plan)
        db.commit()
        db.refresh(db_plan)
        plan.created_at = db_plan.created_at

    return plan
