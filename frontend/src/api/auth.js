// 인증 API 래퍼
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
// 회원가입 요청
export async function apiRegister(email, username, password) {
    const res = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, username, password }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `회원가입 실패: ${res.status}`);
    }
    return res.json();
}
// 로그인 요청
export async function apiLogin(email, password) {
    const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `로그인 실패: ${res.status}`);
    }
    return res.json();
}
// 현재 사용자 정보 조회 (Bearer 토큰 필요)
export async function apiGetMe(token) {
    const res = await fetch(`${API_BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok)
        throw new Error(`인증 확인 실패: ${res.status}`);
    return res.json();
}
