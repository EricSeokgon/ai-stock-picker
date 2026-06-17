// 일반 알림 설정 API 클라이언트 — 목표가·급등락 알림 CRUD (SPEC-STOCK-020)
// @MX:ANCHOR: [AUTO] /alerts API 진입점 — Alerts 페이지와 테스트에서 공유
// @MX:REASON: Alerts.tsx(페이지), Alerts.test.tsx, 향후 AlertBadge 등 3개 이상 소비자
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
function authHeaders(token) {
    return {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
    };
}
/** 사용자 알림 설정 목록 조회. */
export async function fetchAlerts(token) {
    const res = await fetch(`${API_BASE}/alerts/`, {
        headers: authHeaders(token),
    });
    if (!res.ok)
        throw new Error(`알림 목록 조회 실패: ${res.status}`);
    return res.json();
}
/** 신규 알림 설정 등록. */
export async function createAlert(token, data) {
    const res = await fetch(`${API_BASE}/alerts/`, {
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
/** 알림 설정 수정 (부분 업데이트). */
export async function updateAlert(token, alertId, data) {
    const res = await fetch(`${API_BASE}/alerts/${alertId}`, {
        method: 'PUT',
        headers: authHeaders(token),
        body: JSON.stringify(data),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `알림 수정 실패: ${res.status}`);
    }
    return res.json();
}
/** 알림 설정 삭제. */
export async function deleteAlert(token, alertId) {
    const res = await fetch(`${API_BASE}/alerts/${alertId}`, {
        method: 'DELETE',
        headers: authHeaders(token),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `알림 삭제 실패: ${res.status}`);
    }
}
/** 알림 활성/비활성 토글. */
export async function toggleAlert(token, alertId, isActive) {
    return updateAlert(token, alertId, { is_active: isActive });
}
