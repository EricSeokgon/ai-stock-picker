// 관심 목록 API 래퍼 (Bearer 토큰 필요)

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export interface WatchlistItem {
  id: number;
  krx_code: string;
  created_at: string;
}

function authHeaders(token: string): Record<string, string> {
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };
}

// 관심 목록 전체 조회
// @MX:ANCHOR: [AUTO] 관심 목록 API 진입점 — Watchlist 페이지, WatchlistStar에서 사용
// @MX:REASON: 관심 목록 CRUD가 여러 컴포넌트에서 공유됨
export async function getWatchlist(token: string): Promise<WatchlistItem[]> {
  const res = await fetch(`${API_BASE}/watchlist`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`관심 목록 조회 실패: ${res.status}`);
  return res.json() as Promise<WatchlistItem[]>;
}

// 관심 목록에 종목 추가
export async function addToWatchlist(token: string, krxCode: string): Promise<WatchlistItem> {
  const res = await fetch(`${API_BASE}/watchlist`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ krx_code: krxCode }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(err.detail ?? `관심 목록 추가 실패: ${res.status}`);
  }
  return res.json() as Promise<WatchlistItem>;
}

// 관심 목록에서 종목 삭제
export async function removeFromWatchlist(token: string, krxCode: string): Promise<void> {
  const res = await fetch(`${API_BASE}/watchlist/${krxCode}`, {
    method: 'DELETE',
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`관심 목록 삭제 실패: ${res.status}`);
}
