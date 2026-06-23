# 포트폴리오 라우터 — CRUD + 성과 조회 + 배당 분석 엔드포인트
import redis.asyncio as aioredis
import sqlalchemy.exc
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from stock_picker.api.deps import get_redis_client
from stock_picker.auth.dependencies import get_current_user, get_db_session
from stock_picker.db.models import Portfolio, PortfolioHolding, User
from stock_picker.portfolio import service
from stock_picker.portfolio.ai_analysis import analyze_portfolio
from stock_picker.portfolio.dividends import calculate_portfolio_dividends
from stock_picker.portfolio.risk_analysis import calculate_risk_analysis
from stock_picker.portfolio.backtest import run_portfolio_backtest
from stock_picker.portfolio.performance_summary import calculate_performance_summary
from stock_picker.portfolio.schemas import (
    BacktestRequest,
    BacktestResult,
    HoldingCreate,
    HoldingResponse,
    OptimizeResult,
    PerformanceSummaryResponse,
    PortfolioCreate,
    PortfolioDividends,
    PortfolioPerformance,
    PortfolioResponse,
    RiskAnalysisResult,
)

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

    try:
        return service.add_holding(
            db,
            portfolio_id=portfolio_id,
            krx_code=body.krx_code,
            quantity=body.quantity,
            avg_buy_price=body.avg_buy_price,
            market=body.market,
            currency=body.currency,
        )
    except sqlalchemy.exc.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 동일 시장에 동일 종목이 존재합니다",
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
async def ai_analysis(
    portfolio_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """포트폴리오 AI 분석 — Claude API로 분산투자/리스크/개선 제안 제공"""
    return await analyze_portfolio(portfolio_id=portfolio_id, user_id=current_user.id, db=db)


# @MX:NOTE: [AUTO] SPEC-STOCK-026 — POST /portfolios/{id}/optimize, Redis 캐시 TTL=3600s
@router.post("/{portfolio_id}/optimize", response_model=OptimizeResult)
async def optimize_portfolio(
    portfolio_id: int,
    refresh: bool = False,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    redis: aioredis.Redis = Depends(get_redis_client),
) -> OptimizeResult:
    """포트폴리오 AI 최적화 분석 — 리밸런싱 제안 + 신규 종목 추천 (SPEC-STOCK-026)"""
    result = await service.optimize_portfolio(
        portfolio_id=portfolio_id,
        user_id=current_user.id,
        db=db,
        redis=redis,
        refresh=refresh,
    )
    if isinstance(result, dict) and "message" in result:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result["message"],
        )
    return result


# @MX:NOTE: [AUTO] SPEC-STOCK-027 — GET /portfolios/{id}/risk-analysis, Redis 캐시 TTL=3600s
@router.get("/{portfolio_id}/risk-analysis", response_model=RiskAnalysisResult)
async def get_risk_analysis(
    portfolio_id: int,
    period: int = Query(default=90, description="분석 기간(거래일). 허용값: 30, 60, 90, 180, 252"),
    refresh: bool = Query(default=False, description="캐시 무시하고 재계산"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
    redis: aioredis.Redis = Depends(get_redis_client),
) -> RiskAnalysisResult:
    """포트폴리오 리스크 분석 — 상관관계·변동성·분산 효과 (SPEC-STOCK-027)"""
    allowed_periods = {30, 60, 90, 180, 252}
    if period not in allowed_periods:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"period는 {sorted(allowed_periods)} 중 하나여야 합니다",
        )
    return await calculate_risk_analysis(
        portfolio_id=portfolio_id,
        user_id=current_user.id,
        db=db,
        redis=redis,
        period=period,
        refresh=refresh,
    )


@router.get("/{portfolio_id}/performance", response_model=PortfolioPerformance)
async def get_performance(
    portfolio_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    redis: aioredis.Redis = Depends(get_redis_client),
) -> PortfolioPerformance:
    """포트폴리오 성과 계산 — KRX + 해외 자산 현재가 기반 (SPEC-STOCK-028)"""
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

    result = await service.calculate_performance(
        db, portfolio_id=portfolio_id, user_id=current_user.id, redis=redis
    )
    return PortfolioPerformance(**result)


@router.post("/{portfolio_id}/backtest", response_model=BacktestResult)
async def backtest_portfolio(
    portfolio_id: int,
    body: BacktestRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    redis: aioredis.Redis = Depends(get_redis_client),
) -> BacktestResult:
    """포트폴리오 buy-and-hold 백테스팅 — FDR 가격 시계열 기반 수익률 시뮬레이션 (SPEC-STOCK-029)"""
    return await run_portfolio_backtest(
        portfolio_id=portfolio_id,
        user_id=current_user.id,
        db=db,
        redis=redis,
        start_date=body.start_date,
        end_date=body.end_date,
    )


@router.get("/{portfolio_id}/dividends", response_model=PortfolioDividends)
async def get_portfolio_dividends(
    portfolio_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    redis: aioredis.Redis = Depends(get_redis_client),
) -> PortfolioDividends:
    """포트폴리오 배당 분석 — FDR 베스트에포트 + Redis 캐시 (SPEC-STOCK-019)"""
    result = await calculate_portfolio_dividends(
        portfolio_id=portfolio_id,
        user_id=current_user.id,
        db=db,
        redis=redis,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="포트폴리오를 찾을 수 없습니다",
        )
    return result


@router.get("/{portfolio_id}/performance-summary", response_model=PerformanceSummaryResponse)
async def get_performance_summary(
    portfolio_id: int,
    refresh: bool = Query(default=False, description="캐시를 무시하고 재계산"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
    redis: aioredis.Redis = Depends(get_redis_client),
) -> PerformanceSummaryResponse:
    """기간별 성과 요약 — YTD/1M/3M/6M/1Y 수익률 및 MDD (SPEC-STOCK-030)"""
    return await calculate_performance_summary(
        portfolio_id=portfolio_id,
        user_id=current_user.id,
        db=db,
        redis=redis,
        refresh=refresh,
    )
