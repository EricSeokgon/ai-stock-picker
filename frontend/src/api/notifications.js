// 이메일 알림 구독 API 래퍼 (Bearer 토큰 필요)
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
function authHeaders(token) {
    return {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
    };
}
// @MX:ANCHOR: [AUTO] 이메일 구독 API 진입점 — Settings 페이지에서 사용
// @MX:REASON: 구독/해지가 Settings 페이지와 테스트에서 공유됨
// 이메일 구독 등록
export async function subscribeEmail(token, email) {
    const res = await fetch(`${API_BASE}/notifications/email`, {
        method: 'POST',
        headers: authHeaders(token),
        body: JSON.stringify({ email }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `구독 실패: ${res.status}`);
    }
    return res.json();
}
// 이메일 구독 해지
export async function unsubscribeEmail(token) {
    const res = await fetch(`${API_BASE}/notifications/email`, {
        method: 'DELETE',
        headers: authHeaders(token),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `구독 해지 실패: ${res.status}`);
    }
    return res.json();
}
export async function fetchNotifications(token, unread_only = false, limit = 50) {
    const params = new URLSearchParams({ unread_only: String(unread_only), limit: String(limit) });
    const res = await fetch(`${API_BASE}/notifications/?${params}`, {
        headers: authHeaders(token),
    });
    if (!res.ok)
        throw new Error(`알림 조회 실패: ${res.status}`);
    return res.json();
}
export async function fetchUnreadCount(token) {
    const res = await fetch(`${API_BASE}/notifications/unread-count`, {
        headers: authHeaders(token),
    });
    if (!res.ok)
        throw new Error(`미읽음 수 조회 실패: ${res.status}`);
    const data = (await res.json());
    return data.count;
}
export async function markNotificationRead(token, id) {
    const res = await fetch(`${API_BASE}/notifications/${id}/read`, {
        method: 'PATCH',
        headers: authHeaders(token),
    });
    if (!res.ok)
        throw new Error(`읽음 처리 실패: ${res.status}`);
    return res.json();
}
export async function markAllNotificationsRead(token) {
    const res = await fetch(`${API_BASE}/notifications/read-all`, {
        method: 'PATCH',
        headers: authHeaders(token),
    });
    if (!res.ok)
        throw new Error(`전체 읽음 실패: ${res.status}`);
    return res.json();
}
// @MX:ANCHOR: [AUTO] 알림 채널 설정 API 진입점 — Settings 페이지와 테스트에서 공유
// @MX:REASON: getNotificationPreferences, updateNotificationPreferences 두 함수가 Settings에서 함께 호출됨
// 알림 채널 설정 조회
export async function getNotificationPreferences(token) {
    const res = await fetch(`${API_BASE}/notifications/preferences`, {
        headers: authHeaders(token),
    });
    if (!res.ok)
        throw new Error(`채널 설정 조회 실패: ${res.status}`);
    return res.json();
}
// 알림 채널 설정 저장
export async function updateNotificationPreferences(token, items) {
    const res = await fetch(`${API_BASE}/notifications/preferences`, {
        method: 'PUT',
        headers: authHeaders(token),
        body: JSON.stringify(items),
    });
    if (!res.ok)
        throw new Error(`채널 설정 저장 실패: ${res.status}`);
    return res.json();
}
