// 관심 목록 API 래퍼 (Bearer 토큰 필요)
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
function authHeaders(token) {
    return {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
    };
}
// 관심 목록 전체 조회
// @MX:ANCHOR: [AUTO] 관심 목록 API 진입점 — Watchlist 페이지, WatchlistStar에서 사용
// @MX:REASON: 관심 목록 CRUD가 여러 컴포넌트에서 공유됨
export async function getWatchlist(token) {
    const res = await fetch(`${API_BASE}/watchlist`, {
        headers: authHeaders(token),
    });
    if (!res.ok)
        throw new Error(`관심 목록 조회 실패: ${res.status}`);
    return res.json();
}
// 관심 목록에 종목 추가
export async function addToWatchlist(token, krxCode) {
    const res = await fetch(`${API_BASE}/watchlist`, {
        method: 'POST',
        headers: authHeaders(token),
        body: JSON.stringify({ krx_code: krxCode }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `관심 목록 추가 실패: ${res.status}`);
    }
    return res.json();
}
// 관심 목록에서 종목 삭제
export async function removeFromWatchlist(token, krxCode) {
    const res = await fetch(`${API_BASE}/watchlist/${krxCode}`, {
        method: 'DELETE',
        headers: authHeaders(token),
    });
    if (!res.ok)
        throw new Error(`관심 목록 삭제 실패: ${res.status}`);
}
// @MX:ANCHOR: [AUTO] 목표가 알림 API 진입점 — Watchlist 페이지에서 사용
// @MX:REASON: 알림 CRUD가 Watchlist 페이지와 테스트에서 공유됨
// 활성 알림 목록 조회
export async function getAlerts(token) {
    const res = await fetch(`${API_BASE}/watchlist/alerts`, {
        headers: authHeaders(token),
    });
    if (!res.ok)
        throw new Error(`알림 목록 조회 실패: ${res.status}`);
    return res.json();
}
// 알림 생성
export async function createAlert(token, data) {
    const res = await fetch(`${API_BASE}/watchlist/alerts`, {
        method: 'POST',
        headers: authHeaders(token),
        body: JSON.stringify(data),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `알림 생성 실패: ${res.status}`);
    }
    return res.json();
}
// 알림 삭제
export async function deleteAlert(token, alertId) {
    const res = await fetch(`${API_BASE}/watchlist/alerts/${alertId}`, {
        method: 'DELETE',
        headers: authHeaders(token),
    });
    if (!res.ok)
        throw new Error(`알림 삭제 실패: ${res.status}`);
}
