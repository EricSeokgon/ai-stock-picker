# 백테스트 관련 Pydantic v2 스키마
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator


class BacktestRunRequest(BaseModel):
    """백테스트 실행 요청"""
    strategy: str
    start_date: date
    end_date: date

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

    model_config = ConfigDict(from_attributes=True)


class BacktestRunDetail(BacktestRunResponse):
    """백테스트 상세 응답 — 성과 지표 포함"""
    cagr: float | None = None
    max_drawdown: float | None = None
    sharpe_ratio: float | None = None
    total_trades: int = 0


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
