// 섹터 분석 API 클라이언트
// @MX:ANCHOR: [AUTO] 섹터 랭킹 및 상세 조회 공개 진입점 — Sectors 페이지에서 직접 호출
// @MX:REASON: fan_in >= 3 (Sectors 페이지, SectorDetailPanel, 테스트)
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
export async function fetchSectorRanking(sort, limit) {
    const params = new URLSearchParams();
    if (sort)
        params.set('sort', sort);
    if (limit !== undefined)
        params.set('limit', String(limit));
    const query = params.toString();
    const url = `${API_BASE}/sectors/ranking${query ? `?${query}` : ''}`;
    const res = await fetch(url);
    if (!res.ok)
        throw new Error(`API 오류: ${res.status}`);
    return res.json();
}
export async function fetchSectorDetail(sector, days) {
    const params = new URLSearchParams();
    if (days !== undefined)
        params.set('days', String(days));
    const query = params.toString();
    const url = `${API_BASE}/sectors/${encodeURIComponent(sector)}/detail${query ? `?${query}` : ''}`;
    const res = await fetch(url);
    if (!res.ok)
        throw new Error(`API 오류: ${res.status}`);
    return res.json();
}
