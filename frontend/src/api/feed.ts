// 피드 및 공유 포트폴리오 공개 API (SPEC-STOCK-042)

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

// 피드 항목 타입
export interface FeedItem {
  share_token: string;
  portfolio_name: string;
  total_return_rate: number;
  view_count: number;
  like_count: number;
  shared_at: string;
}

// 피드 응답 타입
export interface FeedResponse {
  items: FeedItem[];
  page: number;
  size: number;
  total: number;
}

// 공개 포트폴리오 보유 종목 타입
export interface SharedHolding {
  ticker: string;
  shares: number;
  purchase_price: number;
}

// 공개 포트폴리오 응답 타입
export interface SharePublicResponse {
  portfolio_name: string;
  holdings: SharedHolding[];
  total_return_rate: number;
  goal_progress: number | null;
  view_count: number;
  like_count: number;
}

// 좋아요 응답 타입
export interface LikeResponse {
  like_count: number;
  liked: boolean;
}

// @MX:ANCHOR: [AUTO] 피드 조회 API — Feed 페이지에서 호출
// @MX:REASON: 공개 엔드포인트로 여러 컴포넌트에서 참조될 수 있는 외부 시스템 연동 지점
// @MX:SPEC: SPEC-STOCK-042, SPEC-STOCK-045
export async function getFeed(
  sort: 'likes' | 'recent' | 'trending',
  page: number,
  size: number,
  q?: string,
): Promise<FeedResponse> {
  const params = new URLSearchParams({ sort, page: String(page), size: String(size) });
  // q 비어있으면 파라미터 생략 (REQ-FEED-005)
  if (q && q.trim()) params.set('q', q.trim());
  const res = await fetch(`${API_BASE}/feed?${params.toString()}`);
  if (!res.ok) throw new Error(`피드 조회 실패: ${res.status}`);
  return res.json() as Promise<FeedResponse>;
}

// 공개 포트폴리오 조회 (인증 불필요)
export async function getSharedPortfolio(shareToken: string): Promise<SharePublicResponse> {
  const res = await fetch(`${API_BASE}/shared/${shareToken}`);
  if (res.status === 404) throw new Error('공유된 포트폴리오를 찾을 수 없습니다.');
  if (!res.ok) throw new Error(`포트폴리오 조회 실패: ${res.status}`);
  return res.json() as Promise<SharePublicResponse>;
}

// 공개 포트폴리오 좋아요 취소 (인증 필요, DELETE → 204)
export async function unlikeSharedPortfolio(shareToken: string, token: string): Promise<void> {
  const res = await fetch(`${API_BASE}/shared/${shareToken}/like`, {
    method: 'DELETE',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (res.status === 401) throw new Error('로그인이 필요합니다.');
  if (res.status === 403) throw new Error('자신의 포트폴리오에는 좋아요 취소할 수 없습니다.');
  if (res.status === 404) throw new Error('공유된 포트폴리오를 찾을 수 없습니다.');
  if (res.status !== 204) throw new Error(`좋아요 취소 실패: ${res.status}`);
}

// 공개 포트폴리오 좋아요 (인증 필요)
export async function likeSharedPortfolio(
  shareToken: string,
  token: string,
): Promise<LikeResponse> {
  const res = await fetch(`${API_BASE}/shared/${shareToken}/like`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
  });
  if (res.status === 401) throw new Error('로그인이 필요합니다.');
  if (res.status === 403) throw new Error('자신의 포트폴리오에는 좋아요할 수 없습니다.');
  if (res.status === 404) throw new Error('공유된 포트폴리오를 찾을 수 없습니다.');
  if (!res.ok) throw new Error(`좋아요 처리 실패: ${res.status}`);
  return res.json() as Promise<LikeResponse>;
}
