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
