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
