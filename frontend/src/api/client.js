// 프로덕션에서는 VITE_API_BASE_URL 환경변수 필수 설정
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
export async function fetchRecommendations() {
    const res = await fetch(`${API_BASE}/recommendations`);
    if (!res.ok)
        throw new Error(`API 오류: ${res.status}`);
    return res.json();
}
export async function fetchNews(limit = 20) {
    const res = await fetch(`${API_BASE}/news?limit=${limit}`);
    if (!res.ok)
        throw new Error(`API 오류: ${res.status}`);
    return res.json();
}
// 섹터 트렌드 데이터 조회 (기본 7일)
export async function fetchSectorTrends(days = 7) {
    const res = await fetch(`${API_BASE}/sectors/trends?days=${days}`);
    if (!res.ok)
        throw new Error(`API 오류: ${res.status}`);
    return res.json();
}
// 개별 종목 추천 상세 정보 조회
export async function fetchRecommendationDetail(krxCode) {
    const res = await fetch(`${API_BASE}/recommendations/${krxCode}`);
    if (!res.ok)
        throw new Error(`API 오류: ${res.status}`);
    return res.json();
}
