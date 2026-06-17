// AI 투자 조언 API 래퍼 — SPEC-STOCK-014 M6
// Bearer 토큰 인증 필요
// @MX:ANCHOR: [AUTO] AI 투자 조언 API 진입점 — AdviceHistory, Portfolio 페이지에서 사용
// @MX:REASON: rebalance/risk-profile/market-briefing/history/feedback 5개 엔드포인트 노출
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
function authHeaders(token) {
    return {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
    };
}
// ─────────────────────────────────────────────────────────────────
// API 함수
// ─────────────────────────────────────────────────────────────────
/** 리밸런싱 제안 요청 (REQ-RB-001) */
export async function fetchRebalanceAdvice(token) {
    const res = await fetch(`${API_BASE}/advice/rebalance`, {
        method: 'POST',
        headers: authHeaders(token),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `리밸런싱 조언 요청 실패: ${res.status}`);
    }
    return res.json();
}
/** 리스크 프로파일 분석 요청 (REQ-RM-001) */
export async function fetchRiskProfile(token) {
    const res = await fetch(`${API_BASE}/advice/risk-profile`, {
        method: 'POST',
        headers: authHeaders(token),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `리스크 프로파일 요청 실패: ${res.status}`);
    }
    return res.json();
}
/** 시장 브리핑 조회 (REQ-MB-001) */
export async function fetchMarketBriefing(token) {
    const res = await fetch(`${API_BASE}/advice/market-briefing`, {
        method: 'GET',
        headers: authHeaders(token),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `시장 브리핑 요청 실패: ${res.status}`);
    }
    return res.json();
}
/** AI 조언 이력 조회 (REQ-AIV-004) */
export async function fetchAdviceHistory(token) {
    const res = await fetch(`${API_BASE}/advice/history`, {
        method: 'GET',
        headers: authHeaders(token),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `조언 이력 조회 실패: ${res.status}`);
    }
    return res.json();
}
/** 조언 피드백 제출 (REQ-FB-001) */
export async function submitAdviceFeedback(token, adviceId, feedback) {
    const res = await fetch(`${API_BASE}/advice/${adviceId}/feedback`, {
        method: 'POST',
        headers: authHeaders(token),
        body: JSON.stringify({ feedback }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `피드백 제출 실패: ${res.status}`);
    }
    return res.json();
}
