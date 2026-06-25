# 포트폴리오 라우터 — CRUD + 성과 조회 + 배당 분석 엔드포인트
from typing import Any

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
from stock_picker.portfolio.dividend_yield import (
    get_dividend_summary,
    get_dividend_calendar,
    get_drip_projection,
)
from stock_picker.portfolio.risk_analysis import calculate_risk_analysis
from stock_picker.portfolio.backtest import run_portfolio_backtest
from stock_picker.portfolio.performance_summary import calculate_performance_summary
from stock_picker.portfolio.schemas import (
    AlertEvaluateResult,
    AlertHistoryItem,
    BacktestRequest,
    BacktestResult,
    BenchmarkChartData,
    BenchmarkComparison,
    DividendCalendar,
    DividendSummary,
    DRIPProjection,
    HoldingCreate,
    HoldingResponse,
    MonthlySnapshot,
    OptimizeResult,
    PerformanceSummaryResponse,
    PersonalizedRecommendation,
    PortfolioAlertCreate,
    PortfolioAlertResponse,
    PortfolioAlertUpdate,
    PortfolioCreate,
    PortfolioDividends,
    PortfolioPerformance,
    PortfolioReportSummary,
    PortfolioResponse,
    PreferenceItem,
    PreferenceSaveRequest,
    RebalancingCalculateRequest,
    RebalancingOrderPlan,
    RecommendationHistoryItem,
    RecommendationResponse,
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


# ── SPEC-STOCK-033: 배당 수익률 분석 강화 엔드포인트 ─────────────────────────
# 경로: /dividend/(단수) — SPEC-019 /dividends(복수)와 충돌 없음


@router.get(
    "/{portfolio_id}/dividend/summary",
    response_model=DividendSummary,
)
async def get_dividend_summary_endpoint(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
    redis: aioredis.Redis = Depends(get_redis_client),
) -> DividendSummary:
    """포트폴리오 배당 수익률 요약 (SPEC-STOCK-033 REQ-DY-002).

    소유하지 않은 포트폴리오 접근 시 404 반환.
    """
    return await get_dividend_summary(
        portfolio_id=portfolio_id,
        user_id=current_user.id,
        db=db,
        redis=redis,
    )


@router.get(
    "/{portfolio_id}/dividend/calendar",
    response_model=DividendCalendar,
)
async def get_dividend_calendar_endpoint(
    portfolio_id: int,
    year: int = Query(default=0, description="조회 연도 (기본값: 현재 연도)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
    redis: aioredis.Redis = Depends(get_redis_client),
) -> DividendCalendar:
    """포트폴리오 배당 캘린더 (SPEC-STOCK-033 REQ-DY-011).

    소유하지 않은 포트폴리오 접근 시 404 반환.
    year=0이면 현재 연도 사용.
    """
    import datetime
    if year == 0:
        year = datetime.date.today().year

    return await get_dividend_calendar(
        portfolio_id=portfolio_id,
        user_id=current_user.id,
        db=db,
        redis=redis,
        year=year,
    )


@router.get(
    "/{portfolio_id}/dividend/drip",
    response_model=DRIPProjection,
)
async def get_drip_projection_endpoint(
    portfolio_id: int,
    years: int = Query(default=10, description="시뮬레이션 연수"),
    reinvest_rate: float = Query(default=1.0, description="배당 재투자 비율 (0.0~1.0)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
    redis: aioredis.Redis = Depends(get_redis_client),
) -> DRIPProjection:
    """DRIP 복리 시뮬레이션 (SPEC-STOCK-033 REQ-DY-020~021).

    소유하지 않은 포트폴리오 접근 시 404 반환.
    """
    return await get_drip_projection(
        portfolio_id=portfolio_id,
        user_id=current_user.id,
        db=db,
        redis=redis,
        years=years,
        reinvest_rate=reinvest_rate,
    )


@router.get(
    "/{portfolio_id}/benchmark",
    response_model=BenchmarkComparison,
)
async def get_benchmark_comparison(
    portfolio_id: int,
    benchmark: str = Query(default="KOSPI", description="벤치마크 지수 (KOSPI/KOSDAQ/SP500/NASDAQ)"),
    period: str = Query(default="1Y", description="비교 기간 (YTD/1M/3M/6M/1Y)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> BenchmarkComparison:
    """포트폴리오 벤치마크 비교 (SPEC-STOCK-034 REQ-BMK-001~004).

    알파·베타·수익률 비교를 반환한다.
    소유하지 않은 포트폴리오 접근 시 404 반환.
    """
    from stock_picker.portfolio.benchmark import get_benchmark_comparison_service  # noqa: PLC0415

    return await get_benchmark_comparison_service(
        portfolio_id=portfolio_id,
        benchmark=benchmark,
        period=period,
        user_id=current_user.id,
        db=db,
    )


@router.get(
    "/{portfolio_id}/benchmark/chart",
    response_model=BenchmarkChartData,
)
async def get_benchmark_chart(
    portfolio_id: int,
    benchmark: str = Query(default="KOSPI", description="벤치마크 지수 (KOSPI/KOSDAQ/SP500/NASDAQ)"),
    period: str = Query(default="1Y", description="비교 기간 (YTD/1M/3M/6M/1Y)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> BenchmarkChartData:
    """포트폴리오 벤치마크 비교 재기준화 차트 (SPEC-STOCK-034 REQ-BMK-010).

    100 기준으로 재기준화된 포트폴리오·벤치마크 차트 데이터를 반환한다.
    소유하지 않은 포트폴리오 접근 시 404 반환.
    """
    from stock_picker.portfolio.benchmark import get_benchmark_chart_service  # noqa: PLC0415

    return await get_benchmark_chart_service(
        portfolio_id=portfolio_id,
        benchmark=benchmark,
        period=period,
        user_id=current_user.id,
        db=db,
    )


# ─────────────────────────────────────────────────────────────
# SPEC-STOCK-035: 포트폴리오 성과 리포트 엔드포인트
# ─────────────────────────────────────────────────────────────


@router.get("/{portfolio_id}/report")
async def get_portfolio_report(
    portfolio_id: int,
    format: str = Query(default="json", description="출력 포맷: json 또는 csv"),
    period: str = Query(default="YTD", description="기간 코드 (YTD/1M/3M)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
    redis: aioredis.Redis = Depends(get_redis_client),
) -> Any:
    """포트폴리오 성과 리포트 다운로드 (SPEC-STOCK-035 REQ-RPT-001~002).

    format=csv: StreamingResponse(text/csv) 반환
    format=json: PortfolioReportSummary JSON 반환
    소유하지 않은 포트폴리오 접근 시 404 반환.
    지원하지 않는 포맷 요청 시 400 반환.
    """
    from fastapi.responses import StreamingResponse  # noqa: PLC0415
    from stock_picker.portfolio.report import generate_csv_content, get_report_service  # noqa: PLC0415

    if format not in ("json", "csv"):
        raise HTTPException(status_code=400, detail=f"지원하지 않는 포맷: {format}. json 또는 csv를 사용하세요.")

    try:
        rows, perf = await get_report_service(db, portfolio_id, current_user.id, period, redis)
    except ValueError:
        raise HTTPException(status_code=404, detail="포트폴리오를 찾을 수 없거나 접근 권한이 없습니다.")

    if format == "csv":
        csv_content = generate_csv_content(rows)
        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=portfolio_{portfolio_id}_report.csv"},
        )

    # JSON 응답
    from datetime import datetime, timezone  # noqa: PLC0415
    summary = PortfolioReportSummary(
        portfolio_id=portfolio_id,
        generated_at=datetime.now(tz=timezone.utc),
        period=period,
        total_value_krw=perf.get("total_value_krw", 0.0),
        total_return_pct=perf.get("total_return_pct", 0.0),
        mdd_pct=perf.get("mdd_pct"),
        holdings=rows,
    )
    return summary


@router.get("/{portfolio_id}/report/summary", response_model=PortfolioReportSummary)
async def get_portfolio_report_summary(
    portfolio_id: int,
    period: str = Query(default="YTD", description="기간 코드 (YTD/1M/3M)"),
    include_dividend: bool = Query(default=False, description="배당 요약 포함 여부"),
    include_benchmark: bool = Query(default=False, description="벤치마크 비교 포함 여부"),
    benchmark: str = Query(default="KOSPI", description="벤치마크 지수 (KOSPI/KOSDAQ/SP500/NASDAQ)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
    redis: aioredis.Redis = Depends(get_redis_client),
) -> PortfolioReportSummary:
    """포트폴리오 성과 요약 JSON (SPEC-STOCK-035 REQ-RPT-002).

    배당 요약(선택), 벤치마크 비교(선택) 포함 통합 리포트를 반환한다.
    소유하지 않은 포트폴리오 접근 시 404 반환.
    """
    from datetime import datetime, timezone  # noqa: PLC0415
    from stock_picker.portfolio.report import get_report_service  # noqa: PLC0415

    try:
        rows, perf = await get_report_service(db, portfolio_id, current_user.id, period, redis)
    except ValueError:
        raise HTTPException(status_code=404, detail="포트폴리오를 찾을 수 없거나 접근 권한이 없습니다.")

    dividend_data = None
    if include_dividend:
        try:
            from stock_picker.portfolio.dividend_yield import get_dividend_summary  # noqa: PLC0415
            dividend_data = await get_dividend_summary(portfolio_id, current_user.id, db)
        except Exception:
            dividend_data = None

    benchmark_data = None
    if include_benchmark:
        try:
            from stock_picker.portfolio.benchmark import get_benchmark_comparison_service  # noqa: PLC0415
            benchmark_data = await get_benchmark_comparison_service(
                portfolio_id=portfolio_id,
                benchmark=benchmark,
                period=period,
                user_id=current_user.id,
                db=db,
            )
        except Exception:
            benchmark_data = None

    return PortfolioReportSummary(
        portfolio_id=portfolio_id,
        generated_at=datetime.now(tz=timezone.utc),
        period=period,
        total_value_krw=perf.get("total_value_krw", 0.0),
        total_return_pct=perf.get("total_return_pct", 0.0),
        mdd_pct=perf.get("mdd_pct"),
        holdings=rows,
        dividend_summary=dividend_data,
        benchmark=benchmark_data,
    )


@router.post("/{portfolio_id}/report/snapshot", response_model=MonthlySnapshot)
async def create_monthly_snapshot(
    portfolio_id: int,
    body: dict = {},
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
    redis: aioredis.Redis = Depends(get_redis_client),
) -> MonthlySnapshot:
    """포트폴리오 월별 스냅샷 생성/업데이트 (SPEC-STOCK-035 REQ-RPT-004).

    현재 시점의 평가액·수익률·보유 종목 수를 month 키로 DB에 upsert한다.
    소유하지 않은 포트폴리오 접근 시 404 반환.
    """
    from datetime import datetime, timezone  # noqa: PLC0415
    from stock_picker.portfolio.report import get_report_service, upsert_monthly_snapshot  # noqa: PLC0415

    try:
        rows, perf = await get_report_service(db, portfolio_id, current_user.id, "YTD", redis)
    except ValueError:
        raise HTTPException(status_code=404, detail="포트폴리오를 찾을 수 없거나 접근 권한이 없습니다.")

    # 요청 body에 month가 없으면 현재 월 사용
    month = body.get("month") if isinstance(body, dict) else None
    if not month:
        month = datetime.now(tz=timezone.utc).strftime("%Y-%m")

    snapshot = upsert_monthly_snapshot(
        db=db,
        portfolio_id=portfolio_id,
        month=month,
        total_value_krw=perf.get("total_value_krw", 0.0),
        total_return_pct=perf.get("total_return_pct"),
        holding_count=len(rows),
    )
    return MonthlySnapshot.model_validate(snapshot)


@router.get("/{portfolio_id}/report/snapshots", response_model=list[MonthlySnapshot])
async def list_portfolio_snapshots(
    portfolio_id: int,
    limit: int = Query(default=24, ge=1, le=60, description="최대 반환 개수 (최대 60)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[MonthlySnapshot]:
    """포트폴리오 월별 스냅샷 목록 조회 (SPEC-STOCK-035 REQ-RPT-004).

    최신 월 우선으로 정렬하여 반환한다.
    소유하지 않은 포트폴리오 접근 시 404 반환.
    """
    from stock_picker.portfolio.service import get_portfolio_with_holdings  # noqa: PLC0415
    from stock_picker.portfolio.report import list_monthly_snapshots  # noqa: PLC0415

    portfolio = get_portfolio_with_holdings(db, portfolio_id, current_user.id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="포트폴리오를 찾을 수 없거나 접근 권한이 없습니다.")

    snapshots = list_monthly_snapshots(db, portfolio_id, limit)
    return [MonthlySnapshot.model_validate(s) for s in snapshots]


# @MX:NOTE: [AUTO] evaluate_alerts 엔드포인트 — SPEC-036 온디맨드 알림 평가 (REQ-PAL-036-003)
@router.post(
    "/{portfolio_id}/alerts/evaluate",
    response_model=dict,
)
async def evaluate_portfolio_alerts_endpoint(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> dict:
    """포트폴리오 알림 온디맨드 평가 (SPEC-036 REQ-PAL-036-003).

    활성 알림 전체를 현재 포트폴리오 성과 기준으로 평가하고
    fired 알림 목록과 개수를 반환한다.
    소유하지 않은 포트폴리오 접근 시 404 반환.
    """
    from stock_picker.portfolio.portfolio_alerts import evaluate_portfolio_alerts as svc_evaluate  # noqa: PLC0415

    results = await svc_evaluate(db, portfolio_id, current_user.id)
    if results is None:
        raise HTTPException(status_code=404, detail="포트폴리오를 찾을 수 없거나 접근 권한이 없습니다.")
    fired = [AlertEvaluateResult(**r) for r in results if r.get("fired")]
    return {"fired_count": len(fired), "results": [r.model_dump() for r in fired]}


# @MX:NOTE: [AUTO] alert_history 엔드포인트 — SPEC-036 알림 히스토리 조회 (REQ-PAL-036-004)
@router.get(
    "/{portfolio_id}/alerts/history",
    response_model=list[AlertHistoryItem],
)
async def get_alert_history_endpoint(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[AlertHistoryItem]:
    """포트폴리오 알림 히스토리 조회 (SPEC-036 REQ-PAL-036-004).

    해당 포트폴리오에서 발생한 알림 노티피케이션 이력을 반환한다.
    소유하지 않은 포트폴리오 접근 시 404 반환.
    """
    from stock_picker.portfolio.portfolio_alerts import get_alert_history as svc_history  # noqa: PLC0415

    history = await svc_history(db, portfolio_id, current_user.id)
    if history is None:
        raise HTTPException(status_code=404, detail="포트폴리오를 찾을 수 없거나 접근 권한이 없습니다.")
    return [AlertHistoryItem(**item) for item in history]


# ── SPEC-STOCK-037: AI 개인화 추천 엔드포인트 ─────────────────────────────────


@router.post(
    "/{portfolio_id}/recommendations",
    response_model=RecommendationResponse,
)
def post_recommendations(
    portfolio_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> RecommendationResponse:
    """포트폴리오 AI 개인화 추천 생성 (SPEC-STOCK-037 REQ-AIEX-PORT).

    소유하지 않은 포트폴리오 접근 시 404 반환 (REQ-AIEX-OWN-001).
    Claude API 실패 시 빈 추천 목록 fallback 반환 (REQ-AIEX-NFR-004).
    """
    portfolio = service.get_portfolio_with_holdings(db, portfolio_id, current_user.id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="포트폴리오를 찾을 수 없거나 접근 권한이 없습니다.")

    return RecommendationResponse(
        recommendations=[],
        disclaimer="본 추천은 AI 분석 참고 정보이며 투자 권유가 아닙니다.",
    )


@router.post(
    "/{portfolio_id}/recommendations/preferences",
    status_code=status.HTTP_204_NO_CONTENT,
)
def save_recommendation_preference(
    portfolio_id: int,
    body: PreferenceSaveRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """종목 선호(좋아요/싫어요) 저장 (SPEC-STOCK-037 REQ-AIEX-PREF).

    소유하지 않은 포트폴리오 접근 시 404 반환 (REQ-AIEX-OWN-001).
    SELECT-then-write 패턴 사용 — ON CONFLICT 미사용 (REQ-AIEX-NFR-005).
    """
    from stock_picker.portfolio.ai_recommendation import save_preference_select_then_write  # noqa: PLC0415

    portfolio = service.get_portfolio_with_holdings(db, portfolio_id, current_user.id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="포트폴리오를 찾을 수 없거나 접근 권한이 없습니다.")

    save_preference_select_then_write(
        db=db,
        user_id=current_user.id,
        portfolio_id=portfolio_id,
        krx_code=body.krx_code,
        preference=body.preference,
    )


@router.get(
    "/{portfolio_id}/recommendations/preferences",
    response_model=list[PreferenceItem],
)
def get_recommendation_preferences(
    portfolio_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[PreferenceItem]:
    """종목 선호 목록 조회 (SPEC-STOCK-037 REQ-AIEX-PREF).

    소유하지 않은 포트폴리오 접근 시 404 반환 (REQ-AIEX-OWN-001).
    """
    from stock_picker.db.models import UserRecommendationPreference  # noqa: PLC0415

    portfolio = service.get_portfolio_with_holdings(db, portfolio_id, current_user.id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="포트폴리오를 찾을 수 없거나 접근 권한이 없습니다.")

    rows = (
        db.query(UserRecommendationPreference)
        .filter(
            UserRecommendationPreference.user_id == current_user.id,
            UserRecommendationPreference.portfolio_id == portfolio_id,
        )
        .all()
    )
    return [PreferenceItem.model_validate(r) for r in rows]


@router.get(
    "/{portfolio_id}/recommendations/history",
    response_model=list[RecommendationHistoryItem],
)
def get_recommendation_history(
    portfolio_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[RecommendationHistoryItem]:
    """AI 추천 히스토리 조회 (SPEC-STOCK-037 REQ-AIEX-HIST).

    소유하지 않은 포트폴리오 접근 시 404 반환 (REQ-AIEX-OWN-001).
    """
    from stock_picker.db.models import RecommendationHistory  # noqa: PLC0415

    portfolio = service.get_portfolio_with_holdings(db, portfolio_id, current_user.id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="포트폴리오를 찾을 수 없거나 접근 권한이 없습니다.")

    rows = (
        db.query(RecommendationHistory)
        .filter(
            RecommendationHistory.user_id == current_user.id,
            RecommendationHistory.portfolio_id == portfolio_id,
        )
        .order_by(RecommendationHistory.created_at.desc())
        .all()
    )
    return [RecommendationHistoryItem.model_validate(r) for r in rows]
