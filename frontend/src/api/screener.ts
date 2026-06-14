// 스크리너 API 래퍼 (SPEC-STOCK-018)

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

// ── 타입 정의 ─────────────────────────────────────────────────────────────────

export interface FilterRange {
  min?: number | null;
  max?: number | null;
}

export interface ScreenerCriteria {
  per?: FilterRange | null;
  pbr?: FilterRange | null;
  roe?: FilterRange | null;
  market_cap?: FilterRange | null;
  dividend_yield?: FilterRange | null;
  week52_position?: FilterRange | null;
}

export interface ScreenerRequest {
  filters?: ScreenerCriteria;
  sort_by?: string | null;
  sort_order?: 'asc' | 'desc';
  limit?: number;
}

export interface ScreenerResult {
  krx_code: string;
  name: string | null;
  sector: string | null;
  current_price: number | null;
  change_pct: number | null;
  per: number | null;
  pbr: number | null;
  roe: number | null;
  market_cap: number | null;
  dividend_yield: number | null;
  week52_position: number | null;
  in_watchlist: boolean;
  in_recommendations: boolean;
}

export interface ScreenerResponse {
  snapshot_date: string | null;
  total: number;
  results: ScreenerResult[];
}

export interface ScreenerPresetCreate {
  name: string;
  criteria: ScreenerCriteria;
}

export interface ScreenerPreset {
  id: number;
  user_id: number;
  name: string;
  criteria: ScreenerCriteria;
  created_at: string | null;
}

// ── API 함수 ──────────────────────────────────────────────────────────────────

// @MX:ANCHOR: [AUTO] 스크리너 실행 API — Screener 페이지에서 핵심 호출 진입점
// @MX:REASON: Screener 페이지, 프리셋 로드, 테스트에서 3곳 이상 사용
export async function runScreener(req: ScreenerRequest = {}): Promise<ScreenerResponse> {
  const res = await fetch(`${API_BASE}/screener/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(err.detail ?? `스크리너 실행 실패: ${res.status}`);
  }
  return res.json() as Promise<ScreenerResponse>;
}

function authHeaders(token: string): Record<string, string> {
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };
}

// 프리셋 목록 조회
export async function listPresets(token: string): Promise<ScreenerPreset[]> {
  const res = await fetch(`${API_BASE}/screener/presets`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`프리셋 조회 실패: ${res.status}`);
  return res.json() as Promise<ScreenerPreset[]>;
}

// 프리셋 저장
export async function createPreset(
  token: string,
  data: ScreenerPresetCreate,
): Promise<ScreenerPreset> {
  const res = await fetch(`${API_BASE}/screener/presets`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(err.detail ?? `프리셋 저장 실패: ${res.status}`);
  }
  return res.json() as Promise<ScreenerPreset>;
}

// 프리셋 삭제
export async function deletePreset(token: string, presetId: number): Promise<void> {
  const res = await fetch(`${API_BASE}/screener/presets/${presetId}`, {
    method: 'DELETE',
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`프리셋 삭제 실패: ${res.status}`);
}
