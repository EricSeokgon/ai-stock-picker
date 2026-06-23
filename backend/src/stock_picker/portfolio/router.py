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
    PortfolioAlertCreate,
    PortfolioAlertResponse,
    PortfolioAlertUpdate,
    PortfolioCreate,
    PortfolioDividends,
    PortfolioPerformance,
    PortfolioResponse,
    RebalancingCalculateRequest,
    RebalancingOrderPlan,
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


# ── SPEC-STOCK-031: 포트폴리오 알림 CRUD 엔드포인트 ─────────────────────────
# 동기 Session 패턴 유지 (router.py 전체 관행), 내부 서비스는 async
# 소유권 불일치 시 HTTP 404 반환 (get_portfolio_with_holdings 관행 일치, NFR-005)


@router.post(
    "/{portfolio_id}/alerts",
    response_model=PortfolioAlertResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_portfolio_alert(
    portfolio_id: int,
    body: PortfolioAlertCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> PortfolioAlertResponse:
    """포트폴리오 알림 생성 (SPEC-STOCK-031 REQ-PAL-001).

    - 소유권 불일치: 404
    - (user_id, portfolio_id, alert_type) 중복: 409
    """
    from sqlalchemy.exc import IntegrityError

    from stock_picker.db.session import AsyncSessionLocal
    from stock_picker.portfolio.portfolio_alerts import create_portfolio_alert as svc_create

    try:
        async with AsyncSessionLocal() as async_session:
            alert = await svc_create(
                session=async_session,
                user_id=current_user.id,
                portfolio_id=portfolio_id,
                alert_type=body.alert_type,
                condition_value=body.condition_value,
            )
            if alert is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="포트폴리오를 찾을 수 없습니다",
                )
            await async_session.commit()
            return PortfolioAlertResponse.model_validate(alert)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="동일한 알림 유형이 이미 존재합니다",
        )


@router.get("/{portfolio_id}/alerts", response_model=list[PortfolioAlertResponse])
async def list_portfolio_alerts(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[PortfolioAlertResponse]:
    """포트폴리오 알림 목록 조회 (SPEC-STOCK-031 REQ-PAL-001)."""
    from stock_picker.db.session import AsyncSessionLocal
    from stock_picker.portfolio.portfolio_alerts import list_portfolio_alerts as svc_list

    async with AsyncSessionLocal() as async_session:
        alerts = await svc_list(
            session=async_session,
            user_id=current_user.id,
            portfolio_id=portfolio_id,
        )
    if alerts is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="포트폴리오를 찾을 수 없습니다",
        )
    return [PortfolioAlertResponse.model_validate(a) for a in alerts]


@router.patch(
    "/{portfolio_id}/alerts/{alert_id}",
    response_model=PortfolioAlertResponse,
)
async def update_portfolio_alert(
    portfolio_id: int,
    alert_id: int,
    body: PortfolioAlertUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> PortfolioAlertResponse:
    """포트폴리오 알림 수정 (SPEC-STOCK-031 REQ-PAL-001)."""
    from stock_picker.db.session import AsyncSessionLocal
    from stock_picker.portfolio.portfolio_alerts import update_portfolio_alert as svc_update

    async with AsyncSessionLocal() as async_session:
        alert = await svc_update(
            session=async_session,
            user_id=current_user.id,
            portfolio_id=portfolio_id,
            alert_id=alert_id,
            condition_value=body.condition_value,
            is_active=body.is_active,
        )
        if alert is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="알림을 찾을 수 없습니다",
            )
        await async_session.commit()
        return PortfolioAlertResponse.model_validate(alert)


@router.delete(
    "/{portfolio_id}/alerts/{alert_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_portfolio_alert(
    portfolio_id: int,
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> None:
    """포트폴리오 알림 삭제 (SPEC-STOCK-031 REQ-PAL-001)."""
    from stock_picker.db.session import AsyncSessionLocal
    from stock_picker.portfolio.portfolio_alerts import delete_portfolio_alert as svc_delete

    async with AsyncSessionLocal() as async_session:
        deleted = await svc_delete(
            session=async_session,
            user_id=current_user.id,
            portfolio_id=portfolio_id,
            alert_id=alert_id,
        )
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="알림을 찾을 수 없습니다",
            )
        await async_session.commit()


# ─────────────────────────────────────────────────────────────────────────────
# SPEC-STOCK-032: 포트폴리오 리밸런싱 자동화 엔드포인트
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/{portfolio_id}/rebalance/calculate",
    response_model=RebalancingOrderPlan,
    status_code=status.HTTP_200_OK,
)
async def calculate_rebalancing(
    portfolio_id: int,
    body: RebalancingCalculateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
    redis: aioredis.Redis = Depends(get_redis_client),
) -> RebalancingOrderPlan:
    """포트폴리오 리밸런싱 계획을 계산한다 (SPEC-STOCK-032 RBA-001~005).

    dry_run=True이면 계획만 반환하고 DB에 저장하지 않는다.
    dry_run=False이면 계획을 DB에 저장한다.
    소유하지 않은 포트폴리오에 접근하면 404를 반환한다 (NFR-005).
    """
    from stock_picker.portfolio.rebalancing import calculate_rebalancing_plan

    return await calculate_rebalancing_plan(
        portfolio_id=portfolio_id,
        user_id=current_user.id,
        db=db,
        redis=redis,
        budget=body.budget,
        commission_rate_domestic=body.commission_rate_domestic,
        commission_rate_foreign=body.commission_rate_foreign,
        dry_run=body.dry_run,
    )


@router.get(
    "/{portfolio_id}/rebalance/orders",
    response_model=list[RebalancingOrderPlan],
    status_code=status.HTTP_200_OK,
)
def list_rebalancing_orders(
    portfolio_id: int,
    limit: int = Query(default=5, description="최대 조회 건수"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[RebalancingOrderPlan]:
    """저장된 리밸런싱 계획 목록을 최신순으로 반환한다 (SPEC-STOCK-032 RBA-005).

    소유하지 않은 포트폴리오에 접근하면 404를 반환한다 (NFR-005).
    """
    import json

    from stock_picker.db.models import Portfolio, RebalancingPlan
    from stock_picker.portfolio.schemas import RebalancingOrder

    # 소유권 확인 (NFR-005)
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

    plans = (
        db.query(RebalancingPlan)
        .filter(RebalancingPlan.portfolio_id == portfolio_id)
        .order_by(RebalancingPlan.created_at.desc())
        .limit(limit)
        .all()
    )

    result = []
    for p in plans:
        orders_data = json.loads(p.orders_json)
        orders = [RebalancingOrder(**o) for o in orders_data]
        result.append(
            RebalancingOrderPlan(
                portfolio_id=p.portfolio_id,
                budget=p.budget,
                total_buy_amount=p.total_buy_amount,
                total_sell_amount=p.total_sell_amount,
                total_commission=p.total_commission,
                orders=orders,
                created_at=p.created_at,
            )
        )
    return result
