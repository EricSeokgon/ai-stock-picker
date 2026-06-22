# 포트폴리오 관련 Pydantic v2 스키마 (SPEC-STOCK-017·028 확장)
from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

# SPEC-STOCK-027 — 리스크 분석 스키마는 파일 하단에 추가됨
# SPEC-STOCK-028 — 해외 자산(NYSE/NASDAQ) 지원 필드 추가

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


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
    """보유 종목 추가 요청 (SPEC-STOCK-028: 해외 자산 필드 추가)"""

    krx_code: str
    quantity: int
    avg_buy_price: Decimal
    # SPEC-STOCK-028 — 거래소 및 통화 (기본값: KRX/KRW)
    market: Literal["KRX", "NYSE", "NASDAQ"] = "KRX"
    currency: Literal["KRW", "USD"] = "KRW"

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

    @model_validator(mode="after")
    def market_currency_consistent(self) -> "HoldingCreate":
        """market-currency 정합성: KRX=KRW, NYSE/NASDAQ=USD."""
        if self.market == "KRX" and self.currency != "KRW":
            raise ValueError("KRX 종목은 KRW 통화만 지원합니다")
        if self.market in ("NYSE", "NASDAQ") and self.currency != "USD":
            raise ValueError("NYSE/NASDAQ 종목은 USD 통화만 지원합니다")
        return self


class HoldingResponse(BaseModel):
    """보유 종목 응답 (SPEC-STOCK-028: market/currency 필드 추가)"""

    id: int
    portfolio_id: int
    krx_code: str
    quantity: int
    avg_buy_price: Decimal
    added_at: datetime
    # SPEC-STOCK-028 — 거래소 및 통화 정보
    market: str = "KRX"
    currency: str = "KRW"

    model_config = ConfigDict(from_attributes=True)


class HoldingPerformance(BaseModel):
    """보유 종목 성과 데이터 (SPEC-STOCK-017·028 확장: market, currency, fx_rate_used 추가)"""

    krx_code: str
    quantity: int
    avg_buy_price: float
    current_price: float
    return_pct: float
    # SPEC-STOCK-017 신규 필드
    classification: Literal["high", "normal", "low"] = "normal"
    sector: str = "기타"
    price_unavailable: bool = False
    # SPEC-STOCK-028 신규 필드
    market: str = "KRX"
    currency: str = "KRW"
    fx_rate_used: Optional[float] = None  # USD/KRW 환율 (KRX 종목은 None)


class ClassificationGroup(BaseModel):
    """성과 분류별 집계 (count + 투자 비중)"""

    count: int = 0
    invested: float = 0.0
    invested_pct: float = 0.0


class ClassificationSummary(BaseModel):
    """포트폴리오 전체 성과 분류 요약"""

    high: ClassificationGroup = ClassificationGroup()
    normal: ClassificationGroup = ClassificationGroup()
    low: ClassificationGroup = ClassificationGroup()


class SectorPerformance(BaseModel):
    """섹터별 성과 집계"""

    sector: str
    holding_count: int
    invested: float
    return_pct: float


class PortfolioPerformance(BaseModel):
    """포트폴리오 성과 응답 (SPEC-STOCK-017 확장: classification_summary, sector_performance 추가)"""

    holdings: list[HoldingPerformance]
    total_invested: float
    total_current: float
    total_return_pct: float
    # SPEC-STOCK-017 신규 필드
    classification_summary: ClassificationSummary = ClassificationSummary()
    sector_performance: list[SectorPerformance] = []


# ── SPEC-STOCK-019 배당 포트폴리오 분석 스키마 ────────────────────────────────


class HoldingDividend(BaseModel):
    """보유 종목별 배당 데이터 (SPEC-STOCK-019 REQ-DIV-001~004)"""

    krx_code: str
    name: str | None = None
    quantity: int
    # 배당 지표 (FDR 베스트에포트 — 없으면 None)
    dps: float | None = None  # 주당 배당금(원), 직전 회계연도
    dividend_yield: float | None = None  # 배당수익률(%)
    ex_dividend_month: int | None = None  # 배당기준일에서 파생한 지급 예상 월(1~12)
    annual_income: float = 0.0  # quantity × dps (dps 없으면 0.0)
    yoy_dps_change_pct: float | None = None  # 전년 대비 DPS 증감률(%), 다년 미확보 시 None
    dividend_available: bool = False  # dps 또는 yield 중 하나라도 있으면 True


class DividendCalendarMonth(BaseModel):
    """월별 배당 캘린더 항목 (SPEC-STOCK-019 REQ-DIV-020)"""

    month: int  # 1~12
    holdings: list[str]  # 해당 월 지급 예상 종목 코드 목록
    total_income: float  # 해당 월 예상 배당 수익 합계


class PortfolioDividends(BaseModel):
    """포트폴리오 배당 분석 응답 (SPEC-STOCK-019 REQ-DIV-010~013·020~023)

    # @MX:ANCHOR: [AUTO] 배당 분석 API 응답 스키마
    # @MX:REASON: router, dividend service, 프론트 API 래퍼에서 3곳 이상 참조
    """

    holdings: list[HoldingDividend]
    total_annual_income: float  # 모든 보유의 annual_income 합계
    weighted_avg_yield: float  # 투자금 가중 평균 배당수익률(%)
    calendar: list[DividendCalendarMonth]  # 지급월 확인된 종목만 포함
    coverage_count: int  # dividend_available=True 인 보유 수
    total_holdings: int  # 전체 보유 수


# ── SPEC-STOCK-026 포트폴리오 AI 최적화 스키마 ────────────────────────────────


class TargetWeightItem(BaseModel):
    """리밸런싱 목표 비중 항목 (SPEC-STOCK-026 REQ-OPT-001)"""

    krx_code: str
    current_pct: float  # 현재 비중(%)
    target_pct: float  # 목표 비중(%)
    action: Literal["buy", "sell", "hold"]  # 2% 임계값 기반 서버 재계산
    delta_shares: int  # 조정 주수 (음수=매도)


class NewStockItem(BaseModel):
    """추가 추천 종목 항목 (SPEC-STOCK-026 REQ-OPT-002)"""

    krx_code: str
    name: str
    sector: str
    reason: str  # 추천 이유 (Claude 생성)


class ScoreBreakdown(BaseModel):
    """포트폴리오 점수 세부 항목 (SPEC-STOCK-026 REQ-OPT-003)"""

    diversification: int  # 분산도 점수 (0-100)
    risk_balance: int  # 위험 균형 점수 (0-100)
    momentum: int  # 모멘텀 점수 (0-100)


class OptimizeResult(BaseModel):
    """포트폴리오 AI 최적화 분석 응답 (SPEC-STOCK-026)

    # @MX:ANCHOR: [AUTO] 포트폴리오 최적화 API 응답 스키마
    # @MX:REASON: router, service, 프론트 API 래퍼, 테스트에서 3곳 이상 참조
    """

    score: int  # 0-100, ScoreBreakdown 평균
    score_breakdown: ScoreBreakdown  # 세부 점수
    target_weights: list[TargetWeightItem]  # 리밸런싱 목표 비중 목록
    new_stocks: list[NewStockItem]  # 추가 추천 종목 (최대 5개, 비보유)
    summary: str  # 3-4 한국어 문장 + 면책 문구


# ── SPEC-STOCK-027 포트폴리오 리스크 분석 스키마 ─────────────────────────────


class HoldingVolatility(BaseModel):
    """보유 종목별 변동성 데이터 (SPEC-STOCK-027 REQ-RISK-001)"""

    krx_code: str
    name: str
    annualized_volatility_pct: float  # 연환산 변동성(%), std × √252 × 100
    price_data_days: int  # 실제 사용된 거래일 수


class RiskAnalysisResult(BaseModel):
    """포트폴리오 리스크 분석 응답 (SPEC-STOCK-027)

    # @MX:ANCHOR: [AUTO] 리스크 분석 API 응답 스키마
    # @MX:REASON: router, risk_analysis service, 프론트 API 래퍼, 테스트에서 3곳 이상 참조
    """

    correlation_matrix: dict[str, dict[str, float]]  # Pearson 상관계수 행렬
    holdings_volatility: list[HoldingVolatility]  # 종목별 연환산 변동성
    portfolio_volatility_pct: float  # 포트폴리오 전체 변동성(%)
    diversification_benefit_pct: float  # 분산 효과(%), max(0, ...)
    period_days: int  # 조회 기간(거래일)
    calculated_at: datetime  # 계산 시각
