// @MX:ANCHOR: [AUTO] 추천 히스토리 API 공개 진입점 — History 페이지에서 직접 호출
// @MX:REASON: fan_in >= 3 예상 (History 컴포넌트, 테스트, 잠재적 대시보드 위젯)
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
export async function getRecommendationHistory(days) {
    const res = await fetch(`${API_BASE}/recommendations/history?days=${days}`);
    if (!res.ok)
        throw new Error(`API 오류: ${res.status}`);
    return res.json();
}
export async function fetchFeedbackSummary(krxCode) {
    const res = await fetch(`${API_BASE}/recommendations/${krxCode}/feedback`);
    if (!res.ok)
        throw new Error(`API 오류: ${res.status}`);
    return res.json();
}
export async function submitFeedback(krxCode, vote) {
    const res = await fetch(`${API_BASE}/recommendations/${krxCode}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ vote }),
    });
    if (!res.ok)
        throw new Error(`API 오류: ${res.status}`);
    return res.json();
}
