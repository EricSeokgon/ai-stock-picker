// 인증 API 래퍼

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

// 인증 토큰 응답 타입
export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
}

// 사용자 정보 타입
export interface UserInfo {
  id: number;
  email: string;
  username: string;
  created_at: string;
}

// 회원가입 요청
export async function apiRegister(email: string, username: string, password: string): Promise<AuthTokenResponse> {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, username, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(err.detail ?? `회원가입 실패: ${res.status}`);
  }
  return res.json() as Promise<AuthTokenResponse>;
}

// 로그인 요청
export async function apiLogin(email: string, password: string): Promise<AuthTokenResponse> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(err.detail ?? `로그인 실패: ${res.status}`);
  }
  return res.json() as Promise<AuthTokenResponse>;
}

// 현재 사용자 정보 조회 (Bearer 토큰 필요)
export async function apiGetMe(token: string): Promise<UserInfo> {
  const res = await fetch(`${API_BASE}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`인증 확인 실패: ${res.status}`);
  return res.json() as Promise<UserInfo>;
}
