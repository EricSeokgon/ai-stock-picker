// 배당 포트폴리오 분석 API 래퍼 (SPEC-STOCK-019)

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

// @MX:ANCHOR: [AUTO] 배당 분석 API 응답 타입 — router, Portfolio.tsx에서 3곳 이상 참조
// @MX:REASON: dividends.ts, Portfolio.tsx, Dividends.test.tsx에서 공유 타입

/** 보유 종목별 배당 데이터 */
export interface HoldingDividend {
  krx_code: string;
  name: string | null;
  quantity: number;
  dps: number | null;              // 주당 배당금(원)
  dividend_yield: number | null;   // 배당수익률(%)
  ex_dividend_month: number | null; // 지급 예상 월(1~12)
  annual_income: number;           // 연간 배당 수입(원)
  yoy_dps_change_pct: number | null; // 전년 대비 DPS 증감률(%)
  dividend_available: boolean;
}

/** 월별 배당 캘린더 */
export interface DividendCalendarMonth {
  month: number;
  holdings: string[];     // 해당 월 지급 예상 종목 코드 목록
  total_income: number;   // 해당 월 예상 배당 수입 합계
}

/** 포트폴리오 배당 분석 전체 응답 */
export interface PortfolioDividends {
  holdings: HoldingDividend[];
  total_annual_income: number;    // 전체 연간 배당 수입(원)
  weighted_avg_yield: number;     // 투자금 가중 평균 배당수익률(%)
  calendar: DividendCalendarMonth[];
  coverage_count: number;         // 배당 데이터 확인된 보유 수
  total_holdings: number;
}

function authHeaders(token: string): Record<string, string> {
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };
}

/** 포트폴리오 배당 분석 조회 */
export async function getPortfolioDividends(
  token: string,
  portfolioId: number,
): Promise<PortfolioDividends> {
  const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/dividends`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`배당 분석 조회 실패: ${res.status}`);
  return res.json() as Promise<PortfolioDividends>;
}
