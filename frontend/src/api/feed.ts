// 피드 및 공유 포트폴리오 공개 API (SPEC-STOCK-042)
// SPEC-STOCK-046: 댓글 API 추가 (getComments, addComment, deleteComment)

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

// ── SPEC-STOCK-046: 댓글 API ─────────────────────────────────────────────────
// SPEC-STOCK-048: 대댓글 지원 (parent_comment_id, replies)

// 댓글/대댓글 항목 타입 (SPEC-STOCK-048 REQ-REPLY-005)
export interface CommentItem {
  id: number;
  user_id: number;
  username: string;
  content: string;
  // 부모 댓글 ID (null이면 최상위 댓글, SPEC-STOCK-048 REQ-REPLY-001)
  parent_comment_id: number | null;
  // 대댓글 목록 (최상위 댓글에만 존재, 단일 레벨, SPEC-STOCK-048 REQ-REPLY-005)
  replies: CommentItem[];
  created_at: string;
}

// 댓글 목록 응답 타입 (total은 최상위 댓글만 카운트, SPEC-STOCK-048 REQ-REPLY-008)
export interface CommentListResponse {
  items: CommentItem[];
  total: number;
  page: number;
  size: number;
}

// 공유 포트폴리오 댓글 목록 조회 (인증 불필요)
export async function getComments(
  shareToken: string,
  page: number = 1,
  size: number = 20,
): Promise<CommentListResponse> {
  const params = new URLSearchParams({ page: String(page), size: String(size) });
  const res = await fetch(`${API_BASE}/shared/${shareToken}/comments?${params.toString()}`);
  if (res.status === 404) throw new Error('공유된 포트폴리오를 찾을 수 없습니다.');
  if (!res.ok) throw new Error(`댓글 목록 조회 실패: ${res.status}`);
  return res.json() as Promise<CommentListResponse>;
}

// 공유 포트폴리오 댓글/대댓글 작성 (인증 필요, SPEC-STOCK-048 REQ-REPLY-001)
export async function addComment(
  shareToken: string,
  content: string,
  token: string,
  parentCommentId?: number,
): Promise<CommentItem> {
  // 대댓글인 경우 parent_comment_id 포함 (SPEC-STOCK-048 REQ-REPLY-001)
  const body: Record<string, unknown> = { content };
  if (parentCommentId !== undefined) {
    body['parent_comment_id'] = parentCommentId;
  }
  const res = await fetch(`${API_BASE}/shared/${shareToken}/comments`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  });
  if (res.status === 401) throw new Error('로그인이 필요합니다.');
  if (res.status === 404) throw new Error('공유된 포트폴리오를 찾을 수 없습니다.');
  if (res.status === 422) throw new Error('댓글 내용이 유효하지 않습니다.');
  if (!res.ok) throw new Error(`댓글 작성 실패: ${res.status}`);
  return res.json() as Promise<CommentItem>;
}

// 공유 포트폴리오 댓글 삭제 (인증 필요)
export async function deleteComment(
  shareToken: string,
  commentId: number,
  token: string,
): Promise<void> {
  const res = await fetch(`${API_BASE}/shared/${shareToken}/comments/${commentId}`, {
    method: 'DELETE',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (res.status === 401) throw new Error('로그인이 필요합니다.');
  if (res.status === 403) throw new Error('삭제 권한이 없습니다.');
  if (res.status === 404) throw new Error('댓글을 찾을 수 없습니다.');
  if (res.status !== 204) throw new Error(`댓글 삭제 실패: ${res.status}`);
}
