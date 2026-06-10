// 종목 검색 및 가격 이력 API 클라이언트

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

// @MX:ANCHOR: [AUTO] 종목 검색 API 공개 진입점
// @MX:REASON: StockSearchBar, 테스트, 잠재적 자동완성 컴포넌트에서 참조

export interface StockSearchItem {
  krx_code: string;
  name: string;
  in_recommendations: boolean;
}

export interface StockSearchResponse {
  query: string;
  results: StockSearchItem[];
  total: number;
}

export interface PricePoint {
  date: string;
  close: number;
}

export interface StockPricesResponse {
  krx_code: string;
  days: number;
  prices: PricePoint[];
  available: boolean;
}

export async function searchStocks(q: string): Promise<StockSearchResponse> {
  const params = new URLSearchParams({ q });
  const res = await fetch(`${API_BASE}/stocks/search?${params.toString()}`);
  if (!res.ok) throw new Error(`API 오류: ${res.status}`);
  return res.json() as Promise<StockSearchResponse>;
}

export async function fetchStockPrices(krxCode: string, days = 30): Promise<StockPricesResponse> {
  const params = new URLSearchParams({ days: String(days) });
  const res = await fetch(`${API_BASE}/stocks/${krxCode}/prices?${params.toString()}`);
  if (!res.ok) throw new Error(`API 오류: ${res.status}`);
  return res.json() as Promise<StockPricesResponse>;
}
