# 백테스트 라우터 — 비동기 작업 제출 및 결과 조회
import asyncio
import os
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from stock_picker.auth.dependencies import get_current_user, get_db_session
from stock_picker.backtest import metrics as m
from stock_picker.backtest.schemas import (
    BacktestRunDetail,
    BacktestRunRequest,
    BacktestRunResponse,
    DailyResultResponse,
    PaginatedDailyResults,
)
from stock_picker.db.models import BacktestDailyResult, BacktestRun, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.post("/run", response_model=BacktestRunResponse, status_code=status.HTTP_202_ACCEPTED)
def start_backtest(
    body: BacktestRunRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> BacktestRun:
    """백테스트 작업 제출 — run_id 즉시 반환, 비동기 실행.

    # @MX:WARN: [AUTO] 동기 라우터에서 asyncio.create_task 호출
    # @MX:REASON: TestClient 환경(동기)에서는 create_task가 작동하지 않을 수 있음
    """
    # 실행 레코드 생성
    run = BacktestRun(
        user_id=current_user.id,
        strategy=body.strategy,
        start_date=body.start_date,
        end_date=body.end_date,
        status="pending",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    # 비동기 작업 제출 (이벤트 루프가 실행 중인 경우만)
    db_url = os.getenv(
        "SYNC_DATABASE_URL",
        os.getenv("DATABASE_URL", "").replace("+asyncpg", ""),
    )
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            from stock_picker.backtest.runner import run_backtest
            asyncio.create_task(
                run_backtest(run.id, body.strategy, body.start_date, body.end_date, db_url)
            )
            logger.info("백테스트 작업 제출 — run_id=%d", run.id)
    except RuntimeError:
        # 이벤트 루프가 없는 경우 (테스트 환경)
        logger.warning("이벤트 루프 없음 — 백테스트 run_id=%d는 수동 실행 필요", run.id)

    return run


@router.get("/runs", response_model=list[BacktestRunResponse])
def list_runs(
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[BacktestRun]:
    """사용자의 백테스트 실행 목록 조회"""
    return (
        db.query(BacktestRun)
        .filter(BacktestRun.user_id == current_user.id)
        .order_by(BacktestRun.created_at.desc())
        .all()
    )


@router.get("/runs/{run_id}", response_model=BacktestRunDetail)
def get_run(
    run_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> BacktestRunDetail:
    """백테스트 실행 상태 + 성과 지표 조회"""
    run = (
        db.query(BacktestRun)
        .filter(BacktestRun.id == run_id, BacktestRun.user_id == current_user.id)
        .first()
    )
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="백테스트 실행을 찾을 수 없습니다",
        )

    detail = BacktestRunDetail.model_validate(run)

    # 완료된 경우 성과 지표 계산
    if run.status == "done":
        daily_results = (
            db.query(BacktestDailyResult)
            .filter(BacktestDailyResult.run_id == run_id)
            .order_by(BacktestDailyResult.trade_date)
            .all()
        )
        daily_returns = [
            float(r.return_pct) for r in daily_results if r.return_pct is not None
        ]
        cumulative = _build_cumulative(daily_returns)

        detail.total_trades = len(daily_results)
        if daily_returns:
            detail.cagr = m.calculate_cagr(daily_returns, run.start_date, run.end_date)
            detail.max_drawdown = m.calculate_max_drawdown(cumulative)
            detail.sharpe_ratio = m.calculate_sharpe_ratio(daily_returns)

    return detail


@router.get("/runs/{run_id}/results", response_model=PaginatedDailyResults)
def get_results(
    run_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> PaginatedDailyResults:
    """백테스트 일별 결과 페이지네이션 조회"""
    # 소유권 확인
    run = (
        db.query(BacktestRun)
        .filter(BacktestRun.id == run_id, BacktestRun.user_id == current_user.id)
        .first()
    )
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="백테스트 실행을 찾을 수 없습니다",
        )

    total = (
        db.query(BacktestDailyResult)
        .filter(BacktestDailyResult.run_id == run_id)
        .count()
    )
    items = (
        db.query(BacktestDailyResult)
        .filter(BacktestDailyResult.run_id == run_id)
        .order_by(BacktestDailyResult.trade_date)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PaginatedDailyResults(
        items=[DailyResultResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def _build_cumulative(daily_returns: list[float]) -> list[float]:
    """일별 수익률에서 누적 수익률 시계열 생성"""
    cumulative = [1.0]
    for r in daily_returns:
        cumulative.append(cumulative[-1] * (1.0 + r))
    return cumulative
