// 일반 알림 설정 API 클라이언트 — 목표가·급등락 알림 CRUD (SPEC-STOCK-020)

// @MX:ANCHOR: [AUTO] /alerts API 진입점 — Alerts 페이지와 테스트에서 공유
// @MX:REASON: Alerts.tsx(페이지), Alerts.test.tsx, 향후 AlertBadge 등 3개 이상 소비자

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

function authHeaders(token: string): Record<string, string> {
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };
}

export type AlertType = 'target_price' | 'surge_drop' | 'ex_dividend';
export type AlertDirection = 'above' | 'below' | 'either';

export interface Alert {
  id: number;
  user_id: number;
  krx_code: string;
  stock_name: string | null;
  alert_type: AlertType;
  condition_value: number;
  condition_direction: AlertDirection | null;
  is_active: boolean;
  is_triggered: boolean;
  triggered_at: string | null;
  triggered_message: string | null;
  created_at: string;
}

export interface AlertCreatePayload {
  krx_code: string;
  stock_name?: string | null;
  alert_type: AlertType;
  condition_value: number;
  condition_direction?: AlertDirection | null;
}

export interface AlertUpdatePayload {
  stock_name?: string | null;
  condition_value?: number;
  condition_direction?: AlertDirection | null;
  is_active?: boolean;
}

/** 사용자 알림 설정 목록 조회. */
export async function fetchAlerts(token: string): Promise<Alert[]> {
  const res = await fetch(`${API_BASE}/alerts/`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`알림 목록 조회 실패: ${res.status}`);
  return res.json() as Promise<Alert[]>;
}

/** 신규 알림 설정 등록. */
export async function createAlert(token: string, data: AlertCreatePayload): Promise<Alert> {
  const res = await fetch(`${API_BASE}/alerts/`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(err.detail ?? `알림 생성 실패: ${res.status}`);
  }
  return res.json() as Promise<Alert>;
}

/** 알림 설정 수정 (부분 업데이트). */
export async function updateAlert(
  token: string,
  alertId: number,
  data: AlertUpdatePayload,
): Promise<Alert> {
  const res = await fetch(`${API_BASE}/alerts/${alertId}`, {
    method: 'PUT',
    headers: authHeaders(token),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(err.detail ?? `알림 수정 실패: ${res.status}`);
  }
  return res.json() as Promise<Alert>;
}

/** 알림 설정 삭제. */
export async function deleteAlert(token: string, alertId: number): Promise<void> {
  const res = await fetch(`${API_BASE}/alerts/${alertId}`, {
    method: 'DELETE',
    headers: authHeaders(token),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(err.detail ?? `알림 삭제 실패: ${res.status}`);
  }
}

/** 알림 활성/비활성 토글. */
export async function toggleAlert(token: string, alertId: number, isActive: boolean): Promise<Alert> {
  return updateAlert(token, alertId, { is_active: isActive });
}
