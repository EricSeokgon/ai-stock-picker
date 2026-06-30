// 피드 및 공유 포트폴리오 공개 API (SPEC-STOCK-042)
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
