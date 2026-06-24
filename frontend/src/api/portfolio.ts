// 포트폴리오 API 래퍼 (Bearer 토큰 필요)

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

// 포트폴리오 타입
export interface Portfolio {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
}

// 보유 종목 타입 (SPEC-STOCK-028: market/currency 필드 추가)
export type Market = 'KRX' | 'NYSE' | 'NASDAQ';
export type Currency = 'KRW' | 'USD';

export interface Holding {
  id: number;
  portfolio_id: number;
  krx_code: string;
  quantity: number;
  avg_buy_price: number;
  created_at: string;
  market?: Market;
  currency?: Currency;
}

// 보유 종목 추가 요청 타입
export interface HoldingCreate {
  krx_code: string;
  quantity: number;
  avg_buy_price: number;
  market?: Market;
  currency?: Currency;
}

// 성과 데이터 타입 (SPEC-STOCK-017: 백엔드 응답과 정합화 + 신규 필드 추가)
export interface HoldingPerformance {
  krx_code: string;
  quantity: number;
  avg_buy_price: number;
  current_price: number;
  return_pct: number;
  // SPEC-STOCK-017 신규 필드
  classification: 'high' | 'normal' | 'low';
  sector: string;
  price_unavailable: boolean;
  // SPEC-STOCK-028: 해외 자산 필드
  market?: Market;
  currency?: Currency;
  fx_rate_used?: number | null;
  current_value_krw?: number | null;
}

export interface ClassificationGroup {
  count: number;
  invested: number;
  invested_pct: number;
}

export interface ClassificationSummary {
  high: ClassificationGroup;
  normal: ClassificationGroup;
  low: ClassificationGroup;
}

export interface SectorPerformance {
  sector: string;
  holding_count: number;
  invested: number;
  return_pct: number;
}

export interface PortfolioPerformance {
  holdings: HoldingPerformance[];
  total_invested: number;
  total_current: number;
  total_return_pct: number;
  // SPEC-STOCK-017 신규 필드
  classification_summary: ClassificationSummary;
  sector_performance: SectorPerformance[];
}

// @MX:ANCHOR: [AUTO] 포트폴리오 API 공통 헤더 생성 — Portfolio/Backtest/AuthContext에서 호출
// @MX:REASON: Bearer 토큰 헤더 패턴이 3개 모듈에서 공유됨
function authHeaders(token: string): Record<string, string> {
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };
}

// 포트폴리오 목록 조회
export async function apiListPortfolios(token: string): Promise<Portfolio[]> {
  const res = await fetch(`${API_BASE}/portfolios`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`포트폴리오 조회 실패: ${res.status}`);
  return res.json() as Promise<Portfolio[]>;
}

// 포트폴리오 생성
export async function apiCreatePortfolio(token: string, name: string, description?: string): Promise<Portfolio> {
  const res = await fetch(`${API_BASE}/portfolios`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ name, description }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(err.detail ?? `포트폴리오 생성 실패: ${res.status}`);
  }
  return res.json() as Promise<Portfolio>;
}

// 보유 종목 조회
export async function apiListHoldings(token: string, portfolioId: number): Promise<Holding[]> {
  const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/holdings`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`보유 종목 조회 실패: ${res.status}`);
  return res.json() as Promise<Holding[]>;
}

// 보유 종목 추가 (SPEC-STOCK-028: market/currency 파라미터 추가, 기본값으로 역방향 호환)
export async function apiAddHolding(
  token: string,
  portfolioId: number,
  krx_code: string,
  quantity: number,
  avg_buy_price: number,
  market: Market = 'KRX',
  currency: Currency = 'KRW',
): Promise<Holding> {
  const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/holdings`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ krx_code, quantity, avg_buy_price, market, currency }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(err.detail ?? `종목 추가 실패: ${res.status}`);
  }
  return res.json() as Promise<Holding>;
}

// 포트폴리오 성과 조회
export async function apiGetPerformance(token: string, portfolioId: number): Promise<PortfolioPerformance> {
  const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/performance`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`성과 조회 실패: ${res.status}`);
  return res.json() as Promise<PortfolioPerformance>;
}

// ── SPEC-STOCK-026 포트폴리오 AI 최적화 타입 및 API ─────────────────────────

export interface TargetWeightItem {
  krx_code: string;
  current_pct: number;
  target_pct: number;
  action: 'buy' | 'sell' | 'hold';
  delta_shares: number;
}

export interface NewStockItem {
  krx_code: string;
  name: string;
  sector: string;
  reason: string;
}

export interface ScoreBreakdown {
  diversification: number;
  risk_balance: number;
  momentum: number;
}

export interface OptimizeResult {
  score: number;
  score_breakdown: ScoreBreakdown;
  target_weights: TargetWeightItem[];
  new_stocks: NewStockItem[];
  summary: string;
}

// 포트폴리오 AI 최적화 분석 호출 (SPEC-STOCK-026)
export async function apiOptimizePortfolio(
  token: string,
  portfolioId: number,
  refresh = false,
): Promise<OptimizeResult> {
  const url = `${API_BASE}/portfolios/${portfolioId}/optimize${refresh ? '?refresh=true' : ''}`;
  const res = await fetch(url, {
    method: 'POST',
    headers: authHeaders(token),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(err.detail ?? `최적화 분석 실패: ${res.status}`);
  }
  return res.json() as Promise<OptimizeResult>;
}

// ── SPEC-STOCK-027 포트폴리오 리스크 분석 타입 및 API ────────────────────────

export interface HoldingVolatility {
  krx_code: string;
  name: string;
  annualized_volatility_pct: number;
  price_data_days: number;
}

export interface RiskAnalysisResult {
  correlation_matrix: Record<string, Record<string, number>>;
  holdings_volatility: HoldingVolatility[];
  portfolio_volatility_pct: number;
  diversification_benefit_pct: number;
  period_days: number;
  calculated_at: string;
}

// @MX:ANCHOR: [AUTO] 리스크 분석 API 공개 엔드포인트 — RiskAnalysisPanel에서 호출
// @MX:REASON: 외부 시스템(백엔드 /portfolios/{id}/risk-analysis) 연동 지점으로 fan_in >= 3 예상
export async function apiGetRiskAnalysis(
  token: string,
  portfolioId: number,
  period: number = 90,
  refresh: boolean = false,
): Promise<RiskAnalysisResult> {
  const params = new URLSearchParams({ period: String(period) });
  if (refresh) params.set('refresh', 'true');
  const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/risk-analysis?${params.toString()}`, {
    headers: authHeaders(token),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(err.detail ?? `리스크 분석 조회 실패: ${res.status}`);
  }
  return res.json() as Promise<RiskAnalysisResult>;
}

// ── SPEC-STOCK-029 포트폴리오 백테스팅 타입 및 API ───────────────────────────

// 일별 백테스트 결과
export interface DailyReturn {
  date: string;              // "YYYY-MM-DD"
  portfolio_value: number;   // 1.0 기준 정규화 포트폴리오 가치
  daily_return: number;      // 일별 수익률
  cumulative_return: number; // 누적 수익률 (첫날=0)
}

// 백테스팅 결과
export interface BacktestResult {
  daily: DailyReturn[];
  mdd: number;              // 최대 낙폭 (≤0)
  sharpe_ratio: number;     // 연환산 샤프 비율 (무위험수익률 0.035)
  total_return: number;     // 총 수익률
  period_days: number;      // 거래일 수
  excluded_tickers: string[]; // FDR 조회 실패로 제외된 종목
  used_tickers: string[];   // 실제 계산에 사용된 종목
  disclaimer: string;       // 면책 문구 (REQ-PBT-NFR-003)
}

// ─── SPEC-STOCK-030: 기간별 성과 요약 타입 ──────────────────────────────────

export type PeriodCode = 'ytd' | '1m' | '3m' | '6m' | '1y';

export interface PeriodPerformance {
  period: PeriodCode;
  display_label: string;
  start_date: string | null;
  end_date: string | null;
  trading_days: number;
  has_data: boolean;
  total_return_pct: number | null;
  annualized_return_pct: number | null;
  mdd_pct: number | null;
}

export interface PerformanceSummaryResponse {
  portfolio_id: number;
  periods: PeriodPerformance[];
  calculated_at: string;
  disclaimer: string;
}

// @MX:ANCHOR: [AUTO] 기간별 성과 요약 API 엔드포인트 (SPEC-STOCK-030)
// @MX:REASON: [AUTO] PerformanceSummaryPanel, Portfolio 페이지, 테스트에서 3곳 이상 참조
export async function apiGetPerformanceSummary(
  token: string,
  portfolioId: number,
  refresh = false,
): Promise<PerformanceSummaryResponse> {
  const url = new URL(`${API_BASE}/portfolios/${portfolioId}/performance-summary`);
  if (refresh) url.searchParams.set('refresh', 'true');
  const res = await fetch(url.toString(), { headers: authHeaders(token) });
  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(err.detail ?? `성과 요약 조회 실패: ${res.status}`);
  }
  return res.json() as Promise<PerformanceSummaryResponse>;
}

// ── SPEC-STOCK-031: 포트폴리오 알림 타입 및 API 함수 ─────────────────────────

export type AlertType = 'portfolio_target_return' | 'portfolio_mdd_breach';

export interface PortfolioAlert {
  id: number;
  user_id: number;
  portfolio_id: number;
  alert_type: AlertType;
  condition_value: number;
  is_active: boolean;
  is_triggered: boolean;
  triggered_at: string | null;
  triggered_message: string | null;
  created_at: string;
}

export interface PortfolioAlertCreate {
  alert_type: AlertType;
  condition_value: number;
}

export interface PortfolioAlertUpdate {
  condition_value?: number;
  is_active?: boolean;
}

// @MX:NOTE: [AUTO] 포트폴리오 알림 목록 조회 (SPEC-STOCK-031 REQ-PAL-001)
export async function apiListPortfolioAlerts(
  token: string,
  portfolioId: number,
): Promise<PortfolioAlert[]> {
  const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/alerts`, {
    headers: authHeaders(token),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(err.detail ?? `알림 목록 조회 실패: ${res.status}`);
  }
  return res.json() as Promise<PortfolioAlert[]>;
}

// @MX:NOTE: [AUTO] 포트폴리오 알림 생성 (SPEC-STOCK-031 REQ-PAL-001)
export async function apiCreatePortfolioAlert(
  token: string,
  portfolioId: number,
  data: PortfolioAlertCreate,
): Promise<PortfolioAlert> {
  const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/alerts`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(err.detail ?? `알림 생성 실패: ${res.status}`);
  }
  return res.json() as Promise<PortfolioAlert>;
}

// @MX:NOTE: [AUTO] 포트폴리오 알림 수정 (SPEC-STOCK-031 REQ-PAL-001)
export async function apiUpdatePortfolioAlert(
  token: string,
  portfolioId: number,
  alertId: number,
  data: PortfolioAlertUpdate,
): Promise<PortfolioAlert> {
  const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/alerts/${alertId}`, {
    method: 'PATCH',
    headers: authHeaders(token),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(err.detail ?? `알림 수정 실패: ${res.status}`);
  }
  return res.json() as Promise<PortfolioAlert>;
}

// @MX:NOTE: [AUTO] 포트폴리오 알림 삭제 (SPEC-STOCK-031 REQ-PAL-001)
export async function apiDeletePortfolioAlert(
  token: string,
  portfolioId: number,
  alertId: number,
): Promise<void> {
  const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/alerts/${alertId}`, {
    method: 'DELETE',
    headers: authHeaders(token),
  });
  if (!res.ok && res.status !== 204) {
    const err = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(err.detail ?? `알림 삭제 실패: ${res.status}`);
  }
}

// @MX:ANCHOR: [AUTO] 백테스팅 API 공개 엔드포인트 — BacktestPanel에서 호출
// @MX:REASON: 외부 시스템(백엔드 /portfolios/{id}/backtest) 연동 지점으로 fan_in >= 3 예상
export async function runPortfolioBacktest(
  token: string,
  portfolioId: number,
  startDate: string,
  endDate: string,
): Promise<BacktestResult> {
  const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/backtest`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ start_date: startDate, end_date: endDate }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(err.detail ?? `백테스팅 실패: ${res.status}`);
  }
  return res.json() as Promise<BacktestResult>;
}

// ── SPEC-STOCK-033: 배당 수익률 분석 강화 타입 및 API ─────────────────────

export interface DividendHolding {
  krx_code: string;
  stock_name: string;
  shares: number;
  annual_dps: number;
  dividend_yield_pct: number;
  estimated_annual_dividend: number;
}

export interface DividendSummary {
  portfolio_id: number;
  total_portfolio_value: number;
  total_annual_dividend: number;
  portfolio_dividend_yield_pct: number;
  holdings: DividendHolding[];
}

export interface DividendEvent {
  krx_code: string;
  stock_name: string;
  ex_dividend_date: string;
  payment_date: string | null;
  dps: number;
  shares: number;
  estimated_total: number;
}

export interface DividendCalendar {
  portfolio_id: number;
  year: number;
  months: Record<number, DividendEvent[]>;
}

export interface DRIPYearData {
  year: number;
  portfolio_value: number;
  annual_dividend: number;
  cumulative_return_pct: number;
}

export interface DRIPProjection {
  portfolio_id: number;
  initial_value: number;
  dividend_yield_pct: number;
  reinvest_rate: number;
  years: DRIPYearData[];
  disclaimer: string;
}

// @MX:ANCHOR: [AUTO] 배당 수익률 요약 API — DividendSummaryPanel에서 호출
// @MX:REASON: 백엔드 /portfolios/{id}/dividend/summary 연동, fan_in >= 3 예상
export async function apiGetDividendSummary(
  token: string,
  portfolioId: number,
): Promise<DividendSummary> {
  const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/dividend/summary`, {
    headers: authHeaders(token),
  });
  if (!res.ok)
    throw new Error(`배당 수익률 요약 조회 실패: ${res.status}`);
  return res.json() as Promise<DividendSummary>;
}

// 배당 캘린더 조회 (연도 파라미터 선택 — 기본값: 현재 연도)
export async function apiGetDividendCalendar(
  token: string,
  portfolioId: number,
  year: number | null = null,
): Promise<DividendCalendar> {
  const params = year ? `?year=${year}` : '';
  const res = await fetch(
    `${API_BASE}/portfolios/${portfolioId}/dividend/calendar${params}`,
    { headers: authHeaders(token) }
  );
  if (!res.ok)
    throw new Error(`배당 캘린더 조회 실패: ${res.status}`);
  return res.json() as Promise<DividendCalendar>;
}

// @MX:ANCHOR: [AUTO] DRIP 시뮬레이션 API — DRIPSimulator에서 호출
// @MX:REASON: 백엔드 /portfolios/{id}/dividend/drip 연동, fan_in >= 3 예상
export async function apiGetDRIPProjection(
  token: string,
  portfolioId: number,
  years = 10,
  reinvestRate = 1.0,
): Promise<DRIPProjection> {
  const res = await fetch(
    `${API_BASE}/portfolios/${portfolioId}/dividend/drip?years=${years}&reinvest_rate=${reinvestRate}`,
    { headers: authHeaders(token) }
  );
  if (!res.ok)
    throw new Error(`DRIP 시뮬레이션 조회 실패: ${res.status}`);
  return res.json() as Promise<DRIPProjection>;
}

// ─── SPEC-STOCK-034: 벤치마크 비교 타입 ────────────────────────────────────

// 벤치마크 비교 응답 타입
export interface BenchmarkComparison {
  portfolio_id: number;
  benchmark: string;
  period: string;
  portfolio_return_pct: number;
  benchmark_return_pct: number | null;
  excess_return_pct: number | null;
  alpha: number | null;
  beta: number | null;
  calculated_at: string;
}

// 벤치마크 차트 포인트 타입
export interface BenchmarkChartPoint {
  date: string;
  portfolio_index: number;
  benchmark_index: number | null;
}

// 벤치마크 차트 데이터 타입
export interface BenchmarkChartData {
  portfolio_id: number;
  benchmark: string;
  period: string;
  chart: BenchmarkChartPoint[];
}

// 벤치마크 비교 조회 (SPEC-STOCK-034 REQ-BMK-001~004)
export async function apiGetBenchmarkComparison(
  token: string,
  portfolioId: number,
  benchmark = 'KOSPI',
  period = '1Y',
): Promise<BenchmarkComparison> {
  const res = await fetch(
    `${API_BASE}/portfolios/${portfolioId}/benchmark?benchmark=${benchmark}&period=${period}`,
    { headers: authHeaders(token) }
  );
  if (!res.ok)
    throw new Error(`벤치마크 비교 조회 실패: ${res.status}`);
  return res.json() as Promise<BenchmarkComparison>;
}

// 벤치마크 비교 재기준화 차트 조회 (SPEC-STOCK-034 REQ-BMK-010)
export async function apiGetBenchmarkChart(
  token: string,
  portfolioId: number,
  benchmark = 'KOSPI',
  period = '1Y',
): Promise<BenchmarkChartData> {
  const res = await fetch(
    `${API_BASE}/portfolios/${portfolioId}/benchmark/chart?benchmark=${benchmark}&period=${period}`,
    { headers: authHeaders(token) }
  );
  if (!res.ok)
    throw new Error(`벤치마크 차트 조회 실패: ${res.status}`);
  return res.json() as Promise<BenchmarkChartData>;
}
