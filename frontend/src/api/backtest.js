// 백테스트 API 래퍼 (Bearer 토큰 필요)
// @MX:ANCHOR: [AUTO] 백테스트 API 진입점 — Backtest.tsx, backtest.test.ts에서 직접 참조
// @MX:REASON: 이 파일의 타입·함수는 3개 이상 컴포넌트가 직접 import하는 공개 계약
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
function authHeaders(token) {
    return {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
    };
}
// 백테스트 실행 요청 (POST /backtest/run → HTTP 202)
export async function runBacktest(token, req) {
    const res = await fetch(`${API_BASE}/backtest/run`, {
        method: 'POST',
        headers: authHeaders(token),
        body: JSON.stringify(req),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `백테스트 실행 실패: ${res.status}`);
    }
    return res.json();
}
// 하위 호환 별칭
export const apiRunBacktest = runBacktest;
// 백테스트 실행 목록 조회
export async function getBacktestRuns(token) {
    const res = await fetch(`${API_BASE}/backtest/runs`, {
        headers: authHeaders(token),
    });
    if (!res.ok)
        throw new Error(`백테스트 목록 조회 실패: ${res.status}`);
    return res.json();
}
export const apiListBacktestRuns = getBacktestRuns;
// 특정 백테스트 실행 상세 조회
export async function getBacktestRun(token, runId) {
    const res = await fetch(`${API_BASE}/backtest/runs/${runId}`, {
        headers: authHeaders(token),
    });
    if (!res.ok)
        throw new Error(`백테스트 조회 실패: ${res.status}`);
    return res.json();
}
export const apiGetBacktestRun = getBacktestRun;
// 백테스트 일별 결과 조회
export async function getBacktestResults(token, runId) {
    const res = await fetch(`${API_BASE}/backtest/runs/${runId}/results`, {
        headers: authHeaders(token),
    });
    if (!res.ok)
        throw new Error(`백테스트 결과 조회 실패: ${res.status}`);
    return res.json();
}
export const apiGetBacktestResults = getBacktestResults;
