// 백테스트 API 래퍼 (Bearer 토큰 필요)
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
function authHeaders(token) {
    return {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
    };
}
// 백테스트 실행 요청
export async function apiRunBacktest(token, params) {
    const res = await fetch(`${API_BASE}/backtest/run`, {
        method: 'POST',
        headers: authHeaders(token),
        body: JSON.stringify(params),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `백테스트 실행 실패: ${res.status}`);
    }
    return res.json();
}
// 백테스트 실행 목록 조회
export async function apiListBacktestRuns(token) {
    const res = await fetch(`${API_BASE}/backtest/runs`, {
        headers: authHeaders(token),
    });
    if (!res.ok)
        throw new Error(`백테스트 목록 조회 실패: ${res.status}`);
    return res.json();
}
// 특정 백테스트 실행 상세 조회
export async function apiGetBacktestRun(token, runId) {
    const res = await fetch(`${API_BASE}/backtest/runs/${runId}`, {
        headers: authHeaders(token),
    });
    if (!res.ok)
        throw new Error(`백테스트 조회 실패: ${res.status}`);
    return res.json();
}
// 백테스트 일별 결과 조회
export async function apiGetBacktestResults(token, runId) {
    const res = await fetch(`${API_BASE}/backtest/runs/${runId}/results`, {
        headers: authHeaders(token),
    });
    if (!res.ok)
        throw new Error(`백테스트 결과 조회 실패: ${res.status}`);
    return res.json();
}
