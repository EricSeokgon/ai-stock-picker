// 대시보드 API 호출 모듈 (SPEC-STOCK-038)
const BASE_URL = process.env.REACT_APP_API_URL ?? '';

// 허용 기간 상수 (서버와 동일하게 유지)
export const ALLOWED_DAYS = [7, 30, 90, 365];

// 포트폴리오 가치 시계열 조회
export async function fetchValueSeries(portfolioId, days = 30, token) {
  const res = await fetch(
    `${BASE_URL}/portfolios/${portfolioId}/dashboard/value-series?days=${days}`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
  if (!res.ok) throw new Error(`value-series 조회 실패: ${res.status}`);
  return res.json();
}

// 섹터별 요약 조회
export async function fetchSectorSummary(portfolioId, token) {
  const res = await fetch(
    `${BASE_URL}/portfolios/${portfolioId}/dashboard/sector-summary`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
  if (!res.ok) throw new Error(`sector-summary 조회 실패: ${res.status}`);
  return res.json();
}

// 자산유형별 배분 조회
export async function fetchAssetAllocation(portfolioId, token) {
  const res = await fetch(
    `${BASE_URL}/portfolios/${portfolioId}/dashboard/asset-allocation`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
  if (!res.ok) throw new Error(`asset-allocation 조회 실패: ${res.status}`);
  return res.json();
}
