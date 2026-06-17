// 포트폴리오 API 래퍼 (Bearer 토큰 필요)
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
// @MX:ANCHOR: [AUTO] 포트폴리오 API 공통 헤더 생성 — Portfolio/Backtest/AuthContext에서 호출
// @MX:REASON: Bearer 토큰 헤더 패턴이 3개 모듈에서 공유됨
function authHeaders(token) {
    return {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
    };
}
// 포트폴리오 목록 조회
export async function apiListPortfolios(token) {
    const res = await fetch(`${API_BASE}/portfolios`, {
        headers: authHeaders(token),
    });
    if (!res.ok)
        throw new Error(`포트폴리오 조회 실패: ${res.status}`);
    return res.json();
}
// 포트폴리오 생성
export async function apiCreatePortfolio(token, name, description) {
    const res = await fetch(`${API_BASE}/portfolios`, {
        method: 'POST',
        headers: authHeaders(token),
        body: JSON.stringify({ name, description }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `포트폴리오 생성 실패: ${res.status}`);
    }
    return res.json();
}
// 보유 종목 조회
export async function apiListHoldings(token, portfolioId) {
    const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/holdings`, {
        headers: authHeaders(token),
    });
    if (!res.ok)
        throw new Error(`보유 종목 조회 실패: ${res.status}`);
    return res.json();
}
// 보유 종목 추가
export async function apiAddHolding(token, portfolioId, krx_code, quantity, avg_buy_price) {
    const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/holdings`, {
        method: 'POST',
        headers: authHeaders(token),
        body: JSON.stringify({ krx_code, quantity, avg_buy_price }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `종목 추가 실패: ${res.status}`);
    }
    return res.json();
}
// 포트폴리오 성과 조회
export async function apiGetPerformance(token, portfolioId) {
    const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/performance`, {
        headers: authHeaders(token),
    });
    if (!res.ok)
        throw new Error(`성과 조회 실패: ${res.status}`);
    return res.json();
}
