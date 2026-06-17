// 배당 포트폴리오 분석 API 래퍼 (SPEC-STOCK-019)
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
function authHeaders(token) {
    return {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
    };
}
/** 포트폴리오 배당 분석 조회 */
export async function getPortfolioDividends(token, portfolioId) {
    const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/dividends`, {
        headers: authHeaders(token),
    });
    if (!res.ok)
        throw new Error(`배당 분석 조회 실패: ${res.status}`);
    return res.json();
}
