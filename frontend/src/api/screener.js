// 스크리너 API 래퍼 (SPEC-STOCK-018)
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
// ── API 함수 ──────────────────────────────────────────────────────────────────
// @MX:ANCHOR: [AUTO] 스크리너 실행 API — Screener 페이지에서 핵심 호출 진입점
// @MX:REASON: Screener 페이지, 프리셋 로드, 테스트에서 3곳 이상 사용
export async function runScreener(req = {}) {
    const res = await fetch(`${API_BASE}/screener/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `스크리너 실행 실패: ${res.status}`);
    }
    return res.json();
}
function authHeaders(token) {
    return {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
    };
}
// 프리셋 목록 조회
export async function listPresets(token) {
    const res = await fetch(`${API_BASE}/screener/presets`, {
        headers: authHeaders(token),
    });
    if (!res.ok)
        throw new Error(`프리셋 조회 실패: ${res.status}`);
    return res.json();
}
// 프리셋 저장
export async function createPreset(token, data) {
    const res = await fetch(`${API_BASE}/screener/presets`, {
        method: 'POST',
        headers: authHeaders(token),
        body: JSON.stringify(data),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `프리셋 저장 실패: ${res.status}`);
    }
    return res.json();
}
// 프리셋 삭제
export async function deletePreset(token, presetId) {
    const res = await fetch(`${API_BASE}/screener/presets/${presetId}`, {
        method: 'DELETE',
        headers: authHeaders(token),
    });
    if (!res.ok)
        throw new Error(`프리셋 삭제 실패: ${res.status}`);
}
