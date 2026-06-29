"""포트폴리오 목표 관리 서비스 (SPEC-STOCK-041).

# @MX:ANCHOR: [AUTO] create_goal / get_active_goal / delete_goal: 라우터·스케줄러·테스트에서 참조
# @MX:REASON: portfolio/router.py 엔드포인트, scheduler/jobs.py check_portfolio_goals에서 사용
# @MX:SPEC: SPEC-STOCK-041 REQ-GOAL-001~007

REQ-GOAL-001: POST 목표 생성 — target_amount 또는 target_return_rate 필수, 모두 양수.
REQ-GOAL-001a: 활성 목표 중복 → 409 Conflict.
REQ-GOAL-002: GET 활성 목표 + 달성률 계산.
REQ-GOAL-003: DELETE → 소프트 삭제 (is_active=False).
REQ-GOAL-004: 비소유자 접근 → 404.
REQ-GOAL-005: 활성 목표 없음 → None 반환 (라우터에서 204 처리).
REQ-GOAL-006: achievement_rate 계산 로직 (MIN, 클램프).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from stock_picker.db.models import Portfolio, PortfolioGoal


# ─────────────────────────────────────────────────────────────────────────────
# 순수 계산 함수
# ─────────────────────────────────────────────────────────────────────────────


def calculate_achievement_rate(
    current_value: float,
    current_return_rate: float,
    target_amount: Optional[Decimal],
    target_return_rate: Optional[Decimal],
) -> float:
    """포트폴리오 목표 달성률 계산 (REQ-GOAL-006).

    Args:
        current_value: 현재 포트폴리오 평가액 (KRW).
        current_return_rate: 현재 수익률 (%).
        target_amount: 목표 평가액 (없으면 None).
        target_return_rate: 목표 수익률 (없으면 None).

    Returns:
        달성률 (0.0 ~ 이론상 무제한, 음수 클램프해 0.0).
    """
    rates: list[float] = []

    if target_amount is not None:
        t_amount = float(target_amount)
        if t_amount <= 0:
            # division-by-zero 방어 (T-013b)
            rates.append(0.0)
        else:
            rates.append((current_value / t_amount) * 100.0)

    if target_return_rate is not None:
        t_rate = float(target_return_rate)
        if t_rate <= 0:
            # division-by-zero 방어
            rates.append(0.0)
        else:
            rates.append((current_return_rate / t_rate) * 100.0)

    if not rates:
        return 0.0

    # 둘 다 있으면 MIN (REQ-GOAL-006)
    raw = min(rates)

    # 음수 클램프 (T-015)
    return round(max(0.0, raw), 2)


def get_days_remaining(deadline: Optional[date]) -> Optional[int]:
    """deadline 기준 남은 일수 계산 (REQ-GOAL-002).

    Returns:
        None — deadline 없음.
        0 — deadline이 과거.
        양수 — 남은 일수.
    """
    if deadline is None:
        return None
    delta = (deadline - date.today()).days
    return max(0, delta)


# ─────────────────────────────────────────────────────────────────────────────
# 소유권 확인 헬퍼
# ─────────────────────────────────────────────────────────────────────────────


def _get_portfolio_or_404(db: Session, portfolio_id: int, user_id: int) -> Portfolio:
    """포트폴리오 소유권 확인 — 없거나 비소유자 → 404 (REQ-GOAL-004)."""
    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
        .first()
    )
    if portfolio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="포트폴리오를 찾을 수 없습니다")
    return portfolio


# ─────────────────────────────────────────────────────────────────────────────
# CRUD 서비스 함수
# ─────────────────────────────────────────────────────────────────────────────


def create_goal(
    db: Session,
    portfolio_id: int,
    user_id: int,
    target_amount: Optional[Decimal] = None,
    target_return_rate: Optional[Decimal] = None,
    deadline: Optional[date] = None,
) -> PortfolioGoal:
    """포트폴리오 목표 생성 (REQ-GOAL-001, REQ-GOAL-001a).

    Raises:
        HTTPException(404): 포트폴리오 없음 또는 비소유자.
        HTTPException(409): 이미 활성 목표 존재.
    """
    _get_portfolio_or_404(db, portfolio_id, user_id)

    # 활성 목표 중복 확인 (REQ-GOAL-001a)
    existing = (
        db.query(PortfolioGoal)
        .filter(PortfolioGoal.portfolio_id == portfolio_id, PortfolioGoal.is_active == True)  # noqa: E712
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 활성 목표가 존재합니다. 기존 목표를 삭제 후 새 목표를 설정하세요.",
        )

    goal = PortfolioGoal(
        portfolio_id=portfolio_id,
        target_amount=target_amount,
        target_return_rate=target_return_rate,
        deadline=deadline,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def get_active_goal(
    db: Session,
    portfolio_id: int,
    user_id: int,
) -> Optional[PortfolioGoal]:
    """활성 목표 조회 (REQ-GOAL-002, REQ-GOAL-005).

    Returns:
        PortfolioGoal — 활성 목표 있음.
        None — 활성 목표 없음 (라우터에서 204 반환).

    Raises:
        HTTPException(404): 포트폴리오 없음 또는 비소유자.
    """
    _get_portfolio_or_404(db, portfolio_id, user_id)

    return (
        db.query(PortfolioGoal)
        .filter(PortfolioGoal.portfolio_id == portfolio_id, PortfolioGoal.is_active == True)  # noqa: E712
        .first()
    )


def delete_goal(
    db: Session,
    portfolio_id: int,
    goal_id: int,
    user_id: int,
) -> bool:
    """목표 소프트 삭제 (REQ-GOAL-003).

    Returns:
        True — 삭제 성공.

    Raises:
        HTTPException(404): 포트폴리오 없음, 비소유자, 또는 목표 없음.
    """
    _get_portfolio_or_404(db, portfolio_id, user_id)

    goal = (
        db.query(PortfolioGoal)
        .filter(PortfolioGoal.id == goal_id, PortfolioGoal.portfolio_id == portfolio_id)
        .first()
    )
    if goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="목표를 찾을 수 없습니다")

    goal.is_active = False
    db.commit()
    return True
