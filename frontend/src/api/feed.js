// 피드 및 공유 포트폴리오 공개 API (SPEC-STOCK-042)
// SPEC-STOCK-046: 댓글 API 추가 (getComments, addComment, deleteComment)
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
// @MX:ANCHOR: [AUTO] 피드 조회 API — Feed 페이지에서 호출
// @MX:REASON: 공개 엔드포인트로 여러 컴포넌트에서 참조될 수 있는 외부 시스템 연동 지점
// @MX:SPEC: SPEC-STOCK-042, SPEC-STOCK-045
export async function getFeed(sort, page, size, q) {
    const params = new URLSearchParams({ sort, page: String(page), size: String(size) });
    // q 비어있으면 파라미터 생략 (REQ-FEED-005)
    if (q && q.trim())
        params.set('q', q.trim());
    const res = await fetch(`${API_BASE}/feed?${params.toString()}`);
    if (!res.ok)
        throw new Error(`피드 조회 실패: ${res.status}`);
    return res.json();
}
// 공개 포트폴리오 조회 (인증 불필요)
export async function getSharedPortfolio(shareToken) {
    const res = await fetch(`${API_BASE}/shared/${shareToken}`);
    if (res.status === 404)
        throw new Error('공유된 포트폴리오를 찾을 수 없습니다.');
    if (!res.ok)
        throw new Error(`포트폴리오 조회 실패: ${res.status}`);
    return res.json();
}
// 공개 포트폴리오 좋아요 취소 (인증 필요, DELETE → 204)
export async function unlikeSharedPortfolio(shareToken, token) {
    const res = await fetch(`${API_BASE}/shared/${shareToken}/like`, {
        method: 'DELETE',
        headers: {
            Authorization: `Bearer ${token}`,
        },
    });
    if (res.status === 401)
        throw new Error('로그인이 필요합니다.');
    if (res.status === 403)
        throw new Error('자신의 포트폴리오에는 좋아요 취소할 수 없습니다.');
    if (res.status === 404)
        throw new Error('공유된 포트폴리오를 찾을 수 없습니다.');
    if (res.status !== 204)
        throw new Error(`좋아요 취소 실패: ${res.status}`);
}
// 공개 포트폴리오 좋아요 (인증 필요)
export async function likeSharedPortfolio(shareToken, token) {
    const res = await fetch(`${API_BASE}/shared/${shareToken}/like`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
        },
    });
    if (res.status === 401)
        throw new Error('로그인이 필요합니다.');
    if (res.status === 403)
        throw new Error('자신의 포트폴리오에는 좋아요할 수 없습니다.');
    if (res.status === 404)
        throw new Error('공유된 포트폴리오를 찾을 수 없습니다.');
    if (!res.ok)
        throw new Error(`좋아요 처리 실패: ${res.status}`);
    return res.json();
}
// ── SPEC-STOCK-046: 댓글 API ─────────────────────────────────────────────────
// SPEC-STOCK-048: 대댓글 지원 (parent_comment_id, replies)
// 공유 포트폴리오 댓글 목록 조회 (인증 불필요)
export async function getComments(shareToken, page = 1, size = 20) {
    const params = new URLSearchParams({ page: String(page), size: String(size) });
    const res = await fetch(`${API_BASE}/shared/${shareToken}/comments?${params.toString()}`);
    if (res.status === 404)
        throw new Error('공유된 포트폴리오를 찾을 수 없습니다.');
    if (!res.ok)
        throw new Error(`댓글 목록 조회 실패: ${res.status}`);
    return res.json();
}
// 공유 포트폴리오 댓글/대댓글 작성 (인증 필요, SPEC-STOCK-048 REQ-REPLY-001)
export async function addComment(shareToken, content, token, parentCommentId) {
    // 대댓글인 경우 parent_comment_id 포함 (SPEC-STOCK-048 REQ-REPLY-001)
    const body = { content };
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
    if (res.status === 401)
        throw new Error('로그인이 필요합니다.');
    if (res.status === 404)
        throw new Error('공유된 포트폴리오를 찾을 수 없습니다.');
    if (res.status === 422)
        throw new Error('댓글 내용이 유효하지 않습니다.');
    if (!res.ok)
        throw new Error(`댓글 작성 실패: ${res.status}`);
    return res.json();
}
// 공유 포트폴리오 댓글 삭제 (인증 필요)
export async function deleteComment(shareToken, commentId, token) {
    const res = await fetch(`${API_BASE}/shared/${shareToken}/comments/${commentId}`, {
        method: 'DELETE',
        headers: {
            Authorization: `Bearer ${token}`,
        },
    });
    if (res.status === 401)
        throw new Error('로그인이 필요합니다.');
    if (res.status === 403)
        throw new Error('삭제 권한이 없습니다.');
    if (res.status === 404)
        throw new Error('댓글을 찾을 수 없습니다.');
    if (res.status !== 204)
        throw new Error(`댓글 삭제 실패: ${res.status}`);
}
