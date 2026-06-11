// 이메일 알림 구독 API 래퍼 (Bearer 토큰 필요)

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

function authHeaders(token: string): Record<string, string> {
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };
}

export interface EmailSubscription {
  id: number;
  email: string;
  is_active: boolean;
  created_at: string;
}

// @MX:ANCHOR: [AUTO] 이메일 구독 API 진입점 — Settings 페이지에서 사용
// @MX:REASON: 구독/해지가 Settings 페이지와 테스트에서 공유됨

// 이메일 구독 등록
export async function subscribeEmail(
  token: string,
  email: string,
): Promise<EmailSubscription> {
  const res = await fetch(`${API_BASE}/notifications/email`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ email }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(err.detail ?? `구독 실패: ${res.status}`);
  }
  return res.json() as Promise<EmailSubscription>;
}

// 이메일 구독 해지
export async function unsubscribeEmail(token: string): Promise<{ message: string }> {
  const res = await fetch(`${API_BASE}/notifications/email`, {
    method: 'DELETE',
    headers: authHeaders(token),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(err.detail ?? `구독 해지 실패: ${res.status}`);
  }
  return res.json() as Promise<{ message: string }>;
}

// ── 인박스 알림 API (SPEC-STOCK-013) ──────────────────────────────────────────

// @MX:ANCHOR: [AUTO] 인박스 알림 API 진입점 — NavBar 뱃지 + Notifications 페이지에서 공유
// @MX:REASON: fetchUnreadCount(NavBar), fetchNotifications(NotificationsPage), markAsRead/markAllRead (양쪽) 등 3개 이상

export interface Notification {
  id: number;
  type: string;
  krx_code: string;
  title: string;
  body: string | null;
  is_read: boolean;
  ref_date: string | null;
  related_alert_id: number | null;
  created_at: string;
  read_at: string | null;
}

export async function fetchNotifications(
  token: string,
  unread_only = false,
  limit = 50,
): Promise<Notification[]> {
  const params = new URLSearchParams({ unread_only: String(unread_only), limit: String(limit) });
  const res = await fetch(`${API_BASE}/notifications/?${params}`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`알림 조회 실패: ${res.status}`);
  return res.json() as Promise<Notification[]>;
}

export async function fetchUnreadCount(token: string): Promise<number> {
  const res = await fetch(`${API_BASE}/notifications/unread-count`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`미읽음 수 조회 실패: ${res.status}`);
  const data = (await res.json()) as { count: number };
  return data.count;
}

export async function markNotificationRead(
  token: string,
  id: number,
): Promise<Notification> {
  const res = await fetch(`${API_BASE}/notifications/${id}/read`, {
    method: 'PATCH',
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`읽음 처리 실패: ${res.status}`);
  return res.json() as Promise<Notification>;
}

export async function markAllNotificationsRead(
  token: string,
): Promise<{ updated: number }> {
  const res = await fetch(`${API_BASE}/notifications/read-all`, {
    method: 'PATCH',
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`전체 읽음 실패: ${res.status}`);
  return res.json() as Promise<{ updated: number }>;
}
