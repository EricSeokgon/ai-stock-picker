// 대시보드 API 호출 모듈 (SPEC-STOCK-038)
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

// 허용 기간 상수 (서버와 동일하게 유지)
export const ALLOWED_DAYS = [7, 30, 90, 365] as const;
export type AllowedDays = typeof ALLOWED_DAYS[number];

export interface ValueDataPoint {
  date: string;
  total_value_krw: number;
}

export interface ValueSeriesResponse {
  data: ValueDataPoint[];
  period_days: number;
}

export interface SectorItem {
  sector: string;
  value_krw: number;
  return_pct: number;
}

export interface SectorResponse {
  sectors: SectorItem[];
}

export interface AssetTypeItem {
  asset_type: string;
  value_krw: number;
  weight_pct: number;
}

export interface AssetAllocationResponse {
  assets: AssetTypeItem[];
}

// 포트폴리오 가치 시계열 조회
export async function fetchValueSeries(
  portfolioId: number,
  days: AllowedDays = 30,
  token: string,
): Promise<ValueSeriesResponse> {
  const res = await fetch(
    `${BASE_URL}/portfolios/${portfolioId}/dashboard/value-series?days=${days}`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
  if (!res.ok) throw new Error(`value-series 조회 실패: ${res.status}`);
  return res.json();
}

// 섹터별 요약 조회
export async function fetchSectorSummary(
  portfolioId: number,
  token: string,
): Promise<SectorResponse> {
  const res = await fetch(
    `${BASE_URL}/portfolios/${portfolioId}/dashboard/sector-summary`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
  if (!res.ok) throw new Error(`sector-summary 조회 실패: ${res.status}`);
  return res.json();
}

// 자산유형별 배분 조회
export async function fetchAssetAllocation(
  portfolioId: number,
  token: string,
): Promise<AssetAllocationResponse> {
  const res = await fetch(
    `${BASE_URL}/portfolios/${portfolioId}/dashboard/asset-allocation`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
  if (!res.ok) throw new Error(`asset-allocation 조회 실패: ${res.status}`);
  return res.json();
}
