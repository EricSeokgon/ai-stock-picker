// 포트폴리오 API 래퍼 (Bearer 토큰 필요)

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

// 포트폴리오 타입
export interface Portfolio {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
}

// 보유 종목 타입
export interface Holding {
  id: number;
  portfolio_id: number;
  krx_code: string;
  quantity: number;
  avg_buy_price: number;
  created_at: string;
}

// 성과 데이터 타입
export interface HoldingPerformance {
  krx_code: string;
  quantity: number;
  avg_buy_price: number;
  current_price: number | null;
  invested: number;
  current_value: number | null;
  return_pct: number | null;
}

export interface PortfolioPerformance {
  portfolio_id: number;
  holdings_count: number;
  total_invested: number;
  current_value: number | null;
  total_return: number | null;
  total_return_pct: number | null;
  holdings: HoldingPerformance[];
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

// 보유 종목 추가
export async function apiAddHolding(
  token: string,
  portfolioId: number,
  krx_code: string,
  quantity: number,
  avg_buy_price: number,
): Promise<Holding> {
  const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/holdings`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ krx_code, quantity, avg_buy_price }),
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
