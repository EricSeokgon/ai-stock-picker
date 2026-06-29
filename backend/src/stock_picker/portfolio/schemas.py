# 포트폴리오 관련 Pydantic v2 스키마 (SPEC-STOCK-017·028 확장)
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Optional

# SPEC-STOCK-027 — 리스크 분석 스키마는 파일 하단에 추가됨
# SPEC-STOCK-028 — 해외 자산(NYSE/NASDAQ) 지원 필드 추가

from datetime import date

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


# ── SPEC-STOCK-029 포트폴리오 백테스팅 스키마 ─────────────────────────────────


class BacktestRequest(BaseModel):
    """백테스트 요청 스키마 (SPEC-STOCK-029 REQ-PBT-020)

    # @MX:NOTE: [AUTO] disclaimer 필드는 '투자 권유가 아니며 정보 제공 목적' 문구 포함 필수 (REQ-PBT-NFR-003)
    """

    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_dates(self) -> "BacktestRequest":
        """시작일 >= 종료일이면 ValueError 발생 (REQ-PBT-020)"""
        if self.start_date >= self.end_date:
            raise ValueError("end_date는 start_date보다 이후여야 합니다")
        return self


class DailyReturn(BaseModel):
    """일별 백테스트 결과 항목 (SPEC-STOCK-029 REQ-PBT-040)"""

    date: str  # "YYYY-MM-DD"
    portfolio_value: float  # 1.0 기준 정규화 포트폴리오 가치
    daily_return: float  # 일별 수익률
    cumulative_return: float  # 누적 수익률 (첫날=0)


class BacktestResult(BaseModel):
    """포트폴리오 백테스팅 응답 (SPEC-STOCK-029)

    # @MX:ANCHOR: [AUTO] 백테스팅 API 응답 스키마
    # @MX:REASON: router, backtest service, 프론트 API 래퍼, 테스트에서 3곳 이상 참조
    """

    daily: list[DailyReturn]  # 일별 결과
    mdd: float  # 최대 낙폭 (≤0)
    sharpe_ratio: float  # 연환산 샤프 비율 (무위험수익률 0.035)
    total_return: float  # 총 수익률
    period_days: int  # 거래일 수
    excluded_tickers: list[str]  # FDR 조회 실패로 제외된 종목
    used_tickers: list[str]  # 실제 계산에 사용된 종목


# ─── SPEC-STOCK-030: 기간별 성과 요약 스키마 ─────────────────────────────────────

class PeriodPerformance(BaseModel):
    """단일 기간(YTD/1M/3M/6M/1Y)의 성과 지표"""

    # @MX:ANCHOR: [AUTO] 기간별 성과 핵심 스키마
    # @MX:REASON: [AUTO] router, performance_summary, 프론트 API 래퍼에서 3곳 이상 참조
    # @MX:SPEC: SPEC-STOCK-030 REQ-PS-001

    period: Literal["ytd", "1m", "3m", "6m", "1y"]  # 기간 코드
    display_label: str  # 표시 레이블 (예: "YTD", "1개월")
    start_date: Optional[str] = None  # 기간 시작일 (YYYY-MM-DD)
    end_date: Optional[str] = None  # 기간 종료일 (YYYY-MM-DD)
    trading_days: int = 0  # 실제 거래일 수
    has_data: bool  # 데이터 존재 여부
    total_return_pct: Optional[float] = None  # 총 수익률 (%)
    annualized_return_pct: Optional[float] = None  # 연환산 수익률 (%)
    mdd_pct: Optional[float] = None  # 최대 낙폭 (%, ≤0)


class PerformanceSummaryResponse(BaseModel):
    """포트폴리오 기간별 성과 요약 응답"""

    portfolio_id: int  # 포트폴리오 ID
    periods: list[PeriodPerformance]  # 5개 기간 성과 목록
    calculated_at: str  # 계산 시각 (ISO 8601 UTC)
    disclaimer: str  # 면책 문구 (REQ-PBT-NFR-003)


# ── SPEC-STOCK-031: 포트폴리오 알림 스키마 ────────────────────────────────────


class PortfolioAlertCreate(BaseModel):
    """포트폴리오 알림 생성 요청 (REQ-PAL-001, SPEC-036 확장).

    # @MX:NOTE: [AUTO] alert_type: SPEC-036에서 portfolio_value_below, holding_return 2종 추가
    """

    alert_type: Literal[
        "portfolio_target_return",
        "portfolio_mdd_breach",
        "portfolio_value_below",
        "holding_return",
    ]
    condition_value: float
    # SPEC-036 신규 필드
    target_krx_code: Optional[str] = None       # holding_return 타입 전용
    condition_direction: Optional[str] = None   # "above" | "below" (holding_return 전용)

    @field_validator("condition_value")
    @classmethod
    def condition_value_valid(cls, v: float) -> float:
        """유효 범위 기본 검증."""
        return v


class PortfolioAlertUpdate(BaseModel):
    """포트폴리오 알림 수정 요청 (REQ-PAL-001)."""

    condition_value: Optional[float] = None
    is_active: Optional[bool] = None


class PortfolioAlertResponse(BaseModel):
    """포트폴리오 알림 응답."""

    id: int
    user_id: int
    portfolio_id: int
    alert_type: str
    condition_value: float
    is_active: bool
    is_triggered: bool
    triggered_at: Optional[datetime] = None
    triggered_message: Optional[str] = None
    created_at: datetime
    # SPEC-036 신규 필드
    target_krx_code: Optional[str] = None
    condition_direction: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ── SPEC-STOCK-036: 알림 평가·히스토리 스키마 ────────────────────────────────


class AlertEvaluateResult(BaseModel):
    """단일 알림 평가 결과 (SPEC-036 REQ-PAL-036-003)."""

    alert_id: int
    alert_type: str
    fired: bool
    message: str


class AlertHistoryItem(BaseModel):
    """알림 히스토리 항목 — notifications 테이블 기반 (SPEC-036 REQ-PAL-036-004)."""

    notification_id: int
    alert_type: str
    message: str
    triggered_at: datetime
    portfolio_id: int


# ─────────────────────────────────────────────────────────────
# SPEC-STOCK-032: 포트폴리오 리밸런싱 자동화 스키마
# ─────────────────────────────────────────────────────────────


class RebalancingOrder(BaseModel):
    """단일 종목 리밸런싱 주문 (RBA-006)."""

    krx_code: str
    stock_name: str
    action: Literal["buy", "sell", "hold"]
    quantity: int
    estimated_price: float
    estimated_amount: float
    estimated_commission: float
    current_weight: float
    target_weight: float
    expected_weight_after: float


class RebalancingOrderPlan(BaseModel):
    """리밸런싱 계획서 — 주문 목록 및 요약 (RBA-006)."""

    portfolio_id: int
    budget: float
    total_buy_amount: float
    total_sell_amount: float
    total_commission: float
    orders: list[RebalancingOrder]
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class RebalancingCalculateRequest(BaseModel):
    """리밸런싱 계산 요청 (RBA-002, RBA-005)."""

    # None이면 포트폴리오 총 평가액을 예산으로 사용
    budget: Optional[float] = None
    commission_rate_domestic: float = 0.00015   # KRX 국내 수수료 0.015%
    commission_rate_foreign: float = 0.0025     # NYSE/NASDAQ 해외 수수료 0.25%
    dry_run: bool = True                         # True: 계획만 반환, False: DB 저장


# ── SPEC-STOCK-033: 배당 수익률 분석 강화 스키마 ─────────────────────────────


# @MX:NOTE: [AUTO] DividendHolding — SPEC-033 전용, SPEC-019 HoldingDividend와 별개
# SPEC-019 HoldingDividend는 line ~153에 있으며 수정 금지 (quantity/dps 필드 체계 다름)
class DividendHolding(BaseModel):
    """보유 종목별 배당 데이터 — 수익률 분석 (SPEC-STOCK-033 REQ-DY-001)

    SPEC-019 HoldingDividend와 필드 구성이 상이하므로 별도 클래스명 사용.
    """

    krx_code: str
    stock_name: str
    shares: int
    annual_dps: float           # 주당 연간 배당금 (KRW)
    dividend_yield_pct: float   # annual_dps / current_price * 100
    estimated_annual_dividend: float  # shares * annual_dps


class DividendSummary(BaseModel):
    """포트폴리오 배당 수익률 요약 (SPEC-STOCK-033 REQ-DY-002)

    # @MX:ANCHOR: [AUTO] 배당 수익률 분석 API 응답 스키마
    # @MX:REASON: router, dividend_yield service, 프론트 API 래퍼에서 3곳 이상 참조
    """

    portfolio_id: int
    total_portfolio_value: float
    total_annual_dividend: float
    portfolio_dividend_yield_pct: float   # 가중 평균 배당수익률
    holdings: list[DividendHolding]


class DividendEvent(BaseModel):
    """단일 배당 이벤트 (SPEC-STOCK-033 REQ-DY-010)"""

    krx_code: str
    stock_name: str
    ex_dividend_date: date
    payment_date: Optional[date]
    dps: float
    shares: int
    estimated_total: float   # shares * dps


class DividendCalendar(BaseModel):
    """연도별 배당 캘린더 (SPEC-STOCK-033 REQ-DY-011)

    # @MX:ANCHOR: [AUTO] 배당 캘린더 API 응답 스키마
    # @MX:REASON: router, dividend_yield service, 프론트 API 래퍼에서 3곳 이상 참조
    """

    portfolio_id: int
    year: int
    months: dict[int, list[DividendEvent]]   # {월(1-12): [이벤트]}


class DRIPYearData(BaseModel):
    """DRIP 시뮬레이션 연도별 데이터 (SPEC-STOCK-033 REQ-DY-020)"""

    year: int
    portfolio_value: float
    annual_dividend: float
    cumulative_return_pct: float


class DRIPProjection(BaseModel):
    """DRIP 복리 시뮬레이션 결과 (SPEC-STOCK-033 REQ-DY-021)

    # @MX:ANCHOR: [AUTO] DRIP 시뮬레이션 API 응답 스키마
    # @MX:REASON: router, calculate_drip_projection, 프론트 API 래퍼에서 3곳 이상 참조
    """

    portfolio_id: int
    initial_value: float
    dividend_yield_pct: float
    reinvest_rate: float
    years: list[DRIPYearData]
    disclaimer: str   # "배당률 고정, 가격 성장 미반영 — 참고용 시뮬레이션입니다"


# ─────────────────────────────────────────────────────────────
# SPEC-STOCK-034: 포트폴리오 벤치마크 비교 스키마
# ─────────────────────────────────────────────────────────────


class BenchmarkPeriodReturn(BaseModel):
    """단일 기간 벤치마크 수익률 항목 (SPEC-STOCK-034 REQ-BMK-001)"""

    period: str
    portfolio_return_pct: float
    benchmark_return_pct: Optional[float]
    excess_return_pct: Optional[float]


class BenchmarkComparison(BaseModel):
    """포트폴리오 벤치마크 비교 응답 (SPEC-STOCK-034 REQ-BMK-001~004)

    # @MX:ANCHOR: [AUTO] 벤치마크 비교 API 응답 스키마
    # @MX:REASON: router, benchmark service, 프론트 API 래퍼에서 3곳 이상 참조
    # @MX:SPEC: SPEC-STOCK-034
    """

    portfolio_id: int
    benchmark: str           # "KOSPI", "KOSDAQ", "SP500", "NASDAQ"
    period: str              # "YTD", "1M", "3M", "6M", "1Y"
    portfolio_return_pct: float
    benchmark_return_pct: Optional[float] = None
    excess_return_pct: Optional[float] = None
    alpha: Optional[float] = None    # 연환산 초과수익률 (%)
    beta: Optional[float] = None     # None if < 20 data points
    calculated_at: datetime


class BenchmarkChartPoint(BaseModel):
    """벤치마크 차트 단일 데이터 포인트 (SPEC-STOCK-034 REQ-BMK-010)"""

    date: date
    portfolio_index: float         # 기간 시작 100 기준
    benchmark_index: Optional[float] = None


class BenchmarkChartData(BaseModel):
    """벤치마크 비교 차트 데이터 (SPEC-STOCK-034 REQ-BMK-010)

    # @MX:ANCHOR: [AUTO] 벤치마크 차트 API 응답 스키마
    # @MX:REASON: router, benchmark service, 프론트 API 래퍼에서 3곳 이상 참조
    # @MX:SPEC: SPEC-STOCK-034
    """

    portfolio_id: int
    benchmark: str
    period: str
    chart: list[BenchmarkChartPoint]


# ─────────────────────────────────────────────────────────────
# SPEC-STOCK-035: 포트폴리오 성과 리포트 스키마
# ─────────────────────────────────────────────────────────────


class HoldingReportRow(BaseModel):
    """보유 종목별 손익 행 (SPEC-STOCK-035 REQ-RPT-001)

    순수 함수 generate_holding_report_rows의 출력 단위.
    모든 금액은 KRW 기준으로 통일되어 전달된다.
    """

    ticker: str              # 종목코드 (KRX 코드 또는 해외 티커)
    name: str                # 종목명
    quantity: float          # 보유 수량
    avg_cost: float          # 평균 매수가 (KRW)
    current_price: float     # 현재가 (KRW)
    pnl_amount: float        # 평가 손익 (KRW) = (현재가 - 평균단가) × 수량
    pnl_pct: float           # 수익률 (%) = (현재가 / 평균단가 - 1) × 100
    weight_pct: float        # 포트폴리오 내 비중 (%) = 현재가 × 수량 / 총액 × 100


# @MX:ANCHOR: [AUTO] PortfolioReportSummary — 030·033·034 집계 응답 스키마 (fan_in >= 3)
# @MX:REASON: [AUTO] router(report 엔드포인트), report.py 서비스, 프론트 API 래퍼에서 3곳 이상 참조
# @MX:SPEC: SPEC-STOCK-035 REQ-RPT-002
class PortfolioReportSummary(BaseModel):
    """포트폴리오 성과 리포트 종합 요약 (SPEC-STOCK-035 REQ-RPT-002)

    030 성과 요약 + 033 배당 요약(선택) + 034 벤치마크(선택) + 보유 종목 손익행 통합.
    """

    portfolio_id: int
    generated_at: datetime
    period: str                        # "YTD", "1M", "3M", "custom:start~end" 등
    total_value_krw: float             # 포트폴리오 총 평가액 (KRW)
    total_return_pct: float            # 기간 수익률 (%)
    mdd_pct: Optional[float] = None   # 최대 낙폭 (%, ≤0), 데이터 부족 시 None
    holdings: list[HoldingReportRow]  # 보유 종목 손익 행 목록
    dividend_summary: Optional[Any] = None   # DividendSummary (SPEC-033), 미요청 시 None
    benchmark: Optional[Any] = None          # BenchmarkComparison (SPEC-034), 미요청 시 None


class MonthlySnapshot(BaseModel):
    """포트폴리오 월별 스냅샷 응답 (SPEC-STOCK-035 REQ-RPT-004)"""

    # @MX:NOTE: [AUTO] from_attributes=True — ORM 모델 PortfolioMonthlySnapshot에서 직접 변환
    id: int
    portfolio_id: int
    month: str                         # "YYYY-MM" 형식 (예: "2026-05")
    total_value_krw: float
    total_return_pct: Optional[float] = None  # 기간 비교 불가 시 None
    holding_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── SPEC-STOCK-037: AI 개인화 추천 스키마 ────────────────────────────────────────


class PersonalizedRecommendation(BaseModel):
    """개인화 추천 단건 항목 (SPEC-STOCK-037 REQ-AIEX-RAT).

    fit_score: Claude가 산출한 포트폴리오 적합도 점수 (0.0~1.0).
    reason: 추천 이유 텍스트.
    risk_factors: 투자 위험 요소 텍스트.
    """

    # @MX:ANCHOR: [AUTO] 개인화 추천 응답 핵심 스키마 — router·service·테스트에서 참조
    # @MX:REASON: ai_recommendation.py, personalized_rec_service.py, router.py 3곳 이상 사용
    # @MX:SPEC: SPEC-STOCK-037 REQ-AIEX-RAT

    krx_code: str
    name: Optional[str] = None
    sector: Optional[str] = None
    # 추천 이유 (REQ-AIEX-RAT)
    reason: Optional[str] = None
    # 투자 위험 요소 (REQ-AIEX-RAT)
    risk_factors: Optional[str] = None
    # rationale 별칭 — Claude 응답과의 호환성
    rationale: Optional[str] = None
    # Claude가 산출한 적합도 점수 (0.0 이상 1.0 이하)
    fit_score: float

    @field_validator("fit_score")
    @classmethod
    def validate_fit_score(cls, v: float) -> float:
        """fit_score는 0.0 이상 1.0 이하여야 합니다 (REQ-AIEX-RAT)."""
        if v < 0.0 or v > 1.0:
            raise ValueError("fit_score는 0.0 이상 1.0 이하여야 합니다")
        return v


class RecommendationResponse(BaseModel):
    """개인화 추천 응답 전체 (SPEC-STOCK-037 REQ-AIEX-PORT).

    disclaimer 필드는 투자 권고가 아님을 명시하는 고정 문구.
    """

    recommendations: list[PersonalizedRecommendation]
    # 투자 권유가 아님 명시 — 항상 포함 (REQ-AIEX-PORT)
    disclaimer: str = "본 추천은 AI 분석 참고 정보이며 투자 권유가 아닙니다."


class PreferenceSaveRequest(BaseModel):
    """종목 선호 저장 요청 (SPEC-STOCK-037 REQ-AIEX-PREF).

    preference는 "liked" 또는 "disliked"만 허용.
    """

    krx_code: str
    # 선호 값: "liked" 또는 "disliked"만 허용 (REQ-AIEX-APPLY)
    preference: str

    @field_validator("preference")
    @classmethod
    def validate_preference(cls, v: str) -> str:
        """preference는 'liked' 또는 'disliked'만 허용합니다."""
        if v not in ("liked", "disliked"):
            raise ValueError("preference는 'liked' 또는 'disliked'여야 합니다")
        return v


class PreferenceItem(BaseModel):
    """선호 항목 단건 응답 (SPEC-STOCK-037 REQ-AIEX-PREF)."""

    krx_code: str
    preference: str
    sector: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RecommendationHistoryItem(BaseModel):
    """추천 히스토리 단건 응답 (SPEC-STOCK-037 REQ-AIEX-HIST)."""

    id: int
    portfolio_id: int
    # JSON 직렬화된 추천 목록 (문자열로 반환)
    recommendations: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────
# SPEC-STOCK-038 — 대시보드 시각화 스키마
# ─────────────────────────────────────────────────────────────


class ValueDataPoint(BaseModel):
    """포트폴리오 가치 시계열 단일 데이터 포인트"""

    date: str
    total_value_krw: float


class ValueSeriesResponse(BaseModel):
    """포트폴리오 가치 시계열 응답 (REQ-DASH-VALUE)"""

    data: list[ValueDataPoint]
    period_days: int


class SectorItem(BaseModel):
    """섹터별 집계 단건"""

    sector: str
    value_krw: float
    return_pct: float


class SectorResponse(BaseModel):
    """섹터별 요약 응답 (REQ-DASH-SECTOR)"""

    sectors: list[SectorItem]


class AssetTypeItem(BaseModel):
    """자산유형별 배분 단건"""

    asset_type: str
    value_krw: float
    weight_pct: float


class AssetAllocationResponse(BaseModel):
    """자산유형별 배분 응답 (REQ-DASH-ASSET)"""

    assets: list[AssetTypeItem]


# ── SPEC-STOCK-039: 시장 상태 응답 스키마 ────────────────────────────────────


class MarketStatusResponse(BaseModel):
    """시장 상태 응답 (SPEC-STOCK-039 REQ-MS-001).

    is_open: KRX 정규장 개장 여부.
    message: '장 중' (개장) 또는 '장 마감' (폐장).
    """

    is_open: bool
    message: str


# ── SPEC-STOCK-040: AI 포트폴리오 코멘터리 스키마 ──────────────────────────────


class AICommentaryResponse(BaseModel):
    """AI 포트폴리오 코멘터리 응답 (SPEC-STOCK-040 REQ-CMT-001).

    # @MX:ANCHOR: [AUTO] AI 코멘터리 API 응답 스키마
    # @MX:REASON: router, 단위 테스트, 프론트 API 래퍼에서 3곳 이상 참조

    cached: True이면 인메모리 캐시에서 반환된 결과.
    generated_at: ISO 8601 UTC 형식 생성 시각.
    is_fallback: Claude API 실패·빈 보유 종목 등 대체 텍스트 반환 여부.
    """

    portfolio_id: int
    commentary: str
    cached: bool
    generated_at: str  # ISO 8601 형식
    is_fallback: bool = False


# ── SPEC-STOCK-041: 포트폴리오 목표 관리 스키마 ─────────────────────────────────


class GoalCreate(BaseModel):
    """포트폴리오 목표 생성 요청 (REQ-GOAL-001).

    target_amount 또는 target_return_rate 중 하나 이상 필수.
    deadline만 설정 → 422 (model_validator에서 검증).
    """

    target_amount: Optional[Decimal] = None
    target_return_rate: Optional[Decimal] = None
    deadline: Optional[date] = None

    @model_validator(mode="after")
    def at_least_one_target_must_be_positive(self) -> "GoalCreate":
        """target_amount 또는 target_return_rate 중 하나 이상 양수여야 한다 (REQ-GOAL-001)."""
        has_amount = self.target_amount is not None and self.target_amount > 0
        has_rate = self.target_return_rate is not None and self.target_return_rate > 0

        if not has_amount and not has_rate:
            raise ValueError(
                "target_amount 또는 target_return_rate 중 하나 이상을 양수로 설정해야 합니다"
            )

        # 0 또는 음수 검증 (None이 아니면서 양수가 아닌 경우)
        if self.target_amount is not None and self.target_amount <= 0:
            raise ValueError("target_amount는 0보다 커야 합니다")
        if self.target_return_rate is not None and self.target_return_rate <= 0:
            raise ValueError("target_return_rate는 0보다 커야 합니다")

        return self


class GoalResponse(BaseModel):
    """포트폴리오 목표 응답 (REQ-GOAL-001)."""

    id: int
    portfolio_id: int
    target_amount: Optional[Decimal] = None
    target_return_rate: Optional[Decimal] = None
    deadline: Optional[date] = None
    is_active: bool
    goal_reached_notified: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GoalWithProgressResponse(BaseModel):
    """포트폴리오 목표 + 달성률 응답 (REQ-GOAL-002)."""

    id: int
    portfolio_id: int
    target_amount: Optional[Decimal] = None
    target_return_rate: Optional[Decimal] = None
    deadline: Optional[date] = None
    is_active: bool
    goal_reached_notified: bool
    created_at: datetime
    # 달성률 (0.0 ~ 100.0+, 음수 불허)
    achievement_rate: float
    # 남은 일수: deadline 없으면 None, 과거 deadline이면 0
    days_remaining: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
