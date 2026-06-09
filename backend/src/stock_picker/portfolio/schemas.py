# 포트폴리오 관련 Pydantic v2 스키마
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator


class PortfolioCreate(BaseModel):
    """포트폴리오 생성 요청"""
    name: str

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("포트폴리오 이름은 비어있을 수 없습니다")
        return v.strip()


class PortfolioResponse(BaseModel):
    """포트폴리오 응답"""
    id: int
    user_id: int
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HoldingCreate(BaseModel):
    """보유 종목 추가 요청"""
    krx_code: str
    quantity: int
    avg_buy_price: Decimal

    @field_validator("quantity")
    @classmethod
    def quantity_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("수량은 1 이상이어야 합니다")
        return v

    @field_validator("avg_buy_price")
    @classmethod
    def price_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("평균 매수가는 0보다 커야 합니다")
        return v

    @field_validator("krx_code")
    @classmethod
    def code_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("KRX 코드는 비어있을 수 없습니다")
        return v.strip()


class HoldingResponse(BaseModel):
    """보유 종목 응답"""
    id: int
    portfolio_id: int
    krx_code: str
    quantity: int
    avg_buy_price: Decimal
    added_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HoldingPerformance(BaseModel):
    """보유 종목 성과 데이터"""
    krx_code: str
    quantity: int
    avg_buy_price: float
    current_price: float
    return_pct: float


class PortfolioPerformance(BaseModel):
    """포트폴리오 성과 응답"""
    holdings: list[HoldingPerformance]
    total_invested: float
    total_current: float
    total_return_pct: float
