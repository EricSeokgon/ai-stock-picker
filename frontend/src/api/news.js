const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
/**
 * 시장 전체 감성 집계 조회 (REQ-NEWS-SENT-001)
 * 24시간 기준 분석 기사 avg_score/label/counts 반환
 */
export async function fetchMarketSentiment() {
    const res = await fetch(`${API_BASE}/news/market-sentiment`);
    if (!res.ok)
        throw new Error(`API 오류: ${res.status}`);
    return res.json();
}
/**
 * 종목별 뉴스 조회 (REQ-NEWS-FEED-002)
 * krx_code가 있으면 해당 종목 뉴스, 없으면 전체 뉴스
 */
export async function fetchNewsByStock(krxCode, limit = 10) {
    const res = await fetch(`${API_BASE}/news?krx_code=${krxCode}&limit=${limit}`);
    if (!res.ok)
        throw new Error(`API 오류: ${res.status}`);
    return res.json();
}
/**
 * 수동 뉴스 수집·분석 트리거 (REQ-NEWS-FETCH-001)
 */
export async function triggerNewsFetch() {
    const res = await fetch(`${API_BASE}/news/fetch`, { method: 'POST' });
    if (!res.ok)
        throw new Error(`API 오류: ${res.status}`);
    return res.json();
}
