# 포트폴리오 라우터 — CRUD + 성과 조회 엔드포인트
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from stock_picker.auth.dependencies import get_current_user, get_db_session
from stock_picker.db.models import Portfolio, PortfolioHolding, User
from stock_picker.portfolio import service
from stock_picker.portfolio.schemas import (
    HoldingCreate,
    HoldingResponse,
    PortfolioCreate,
    PortfolioPerformance,
    PortfolioResponse,
)

from stock_picker.portfolio.ai_analysis import analyze_portfolio

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


@router.post("", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
def create_portfolio(
    body: PortfolioCreate,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Portfolio:
    """포트폴리오 생성"""
    return service.create_portfolio(db, user_id=current_user.id, name=body.name)


@router.get("", response_model=list[PortfolioResponse])
def list_portfolios(
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[Portfolio]:
    """사용자의 포트폴리오 목록 조회"""
    return service.list_portfolios(db, user_id=current_user.id)


@router.post(
    "/{portfolio_id}/holdings",
    response_model=HoldingResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_holding(
    portfolio_id: int,
    body: HoldingCreate,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> PortfolioHolding:
    """포트폴리오에 보유 종목 추가"""
    # 소유권 확인
    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
        .first()
    )
    if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="포트폴리오를 찾을 수 없습니다",
        )

    return service.add_holding(
        db,
        portfolio_id=portfolio_id,
        krx_code=body.krx_code,
        quantity=body.quantity,
        avg_buy_price=body.avg_buy_price,
    )


@router.delete(
    "/{portfolio_id}/holdings/{holding_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_holding(
    portfolio_id: int,
    holding_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """보유 종목 삭제"""
    # 소유권 확인 (portfolio → user 체인)
    holding = (
        db.query(PortfolioHolding)
        .join(Portfolio)
        .filter(
            PortfolioHolding.id == holding_id,
            PortfolioHolding.portfolio_id == portfolio_id,
            Portfolio.user_id == current_user.id,
        )
        .first()
    )
    if holding is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="보유 종목을 찾을 수 없습니다",
        )
    service.remove_holding(db, holding_id=holding_id)


@router.post("/{portfolio_id}/ai-analysis")
def ai_analysis(
    portfolio_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """포트폴리오 AI 분석 — Claude API로 분산투자/리스크/개선 제안 제공"""
    return analyze_portfolio(portfolio_id=portfolio_id, user_id=current_user.id, db=db)


@router.get("/{portfolio_id}/performance", response_model=PortfolioPerformance)
def get_performance(
    portfolio_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> PortfolioPerformance:
    """포트폴리오 성과 계산 — 현재가 기반"""
    # 소유권 확인
    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
        .first()
    )
    if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="포트폴리오를 찾을 수 없습니다",
        )

    result = service.calculate_performance(db, portfolio_id=portfolio_id, user_id=current_user.id)
    return PortfolioPerformance(**result)
