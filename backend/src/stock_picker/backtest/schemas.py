# 백테스트 관련 Pydantic v2 스키마
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator


class BacktestRunRequest(BaseModel):
    """백테스트 실행 요청"""
    strategy: str
    start_date: date
    end_date: date
    universe_size: int | None = None
    top_n: int | None = None

    @field_validator("strategy")
    @classmethod
    def strategy_valid(cls, v: str) -> str:
        allowed = {"momentum", "volume"}
        if v not in allowed:
            raise ValueError(f"전략은 {allowed} 중 하나여야 합니다")
        return v

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v: date, info: object) -> date:
        # info.data는 이미 검증된 필드들을 포함
        data = getattr(info, "data", {})
        start_date = data.get("start_date")
        if start_date and v <= start_date:
            raise ValueError("종료일은 시작일보다 이후여야 합니다")
        return v

    @field_validator("universe_size")
    @classmethod
    def universe_size_positive(cls, v: int | None) -> int | None:
        if v is not None and v < 1:
            raise ValueError("universe_size는 1 이상이어야 합니다")
        return v

    @field_validator("top_n")
    @classmethod
    def top_n_positive(cls, v: int | None) -> int | None:
        if v is not None and v < 1:
            raise ValueError("top_n은 1 이상이어야 합니다")
        return v


class BacktestStartResponse(BaseModel):
    """백테스트 시작 응답 — run_id 즉시 반환"""
    run_id: int
    message: str


class BacktestRunResponse(BaseModel):
    """백테스트 실행 응답"""
    id: int
    user_id: int
    strategy: str
    start_date: date
    end_date: date
    status: str
    created_at: datetime
    completed_at: datetime | None = None
    universe_size: int | None = None
    top_n: int | None = None

    model_config = ConfigDict(from_attributes=True)


class BacktestRunDetail(BacktestRunResponse):
    """백테스트 상세 응답 — 성과 지표 포함"""
    cagr: float | None = None
    max_drawdown: float | None = None
    sharpe_ratio: float | None = None
    total_return: float | None = None
    win_rate: float | None = None
    total_trades: int = 0


class DailyResultTimeSeries(BaseModel):
    """일별 포트폴리오 가치 시계열"""
    date: str
    portfolio_value: float
    benchmark_value: float | None = None
    daily_return: float


class DailyResultResponse(BaseModel):
    """일별 결과 응답"""
    id: int
    run_id: int
    trade_date: date
    krx_code: str
    signal: str
    price: Decimal
    return_pct: Decimal | None = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedDailyResults(BaseModel):
    """페이지네이션된 일별 결과"""
    items: list[DailyResultResponse]
    total: int
    page: int
    page_size: int
