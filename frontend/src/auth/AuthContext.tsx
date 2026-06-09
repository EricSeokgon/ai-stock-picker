// 인증 컨텍스트 — 로그인/회원가입/로그아웃 및 사용자 세션 관리
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { apiLogin, apiRegister, apiGetMe, type UserInfo } from '../api/auth';

// 로컬스토리지 키
const TOKEN_KEY = 'stock_picker_token';

// @MX:ANCHOR: [AUTO] AuthContext 공개 API — Login/Portfolio/Backtest 페이지에서 useAuth()로 호출
// @MX:REASON: 인증 상태 소비 지점이 3곳 이상(Login, Portfolio, Backtest, NavBar)
interface AuthContextValue {
  user: UserInfo | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [token, setToken] = useState<string | null>(null);

  // 마운트 시 저장된 토큰으로 세션 복원
  useEffect(() => {
    const saved = localStorage.getItem(TOKEN_KEY);
    if (!saved) return;

    // 토큰 유효성 확인
    apiGetMe(saved)
      .then((u) => {
        setToken(saved);
        setUser(u);
      })
      .catch(() => {
        // 401 등 오류 시 토큰 제거
        localStorage.removeItem(TOKEN_KEY);
      });
  }, []);

  async function login(email: string, password: string): Promise<void> {
    const res = await apiLogin(email, password);
    localStorage.setItem(TOKEN_KEY, res.access_token);
    const u = await apiGetMe(res.access_token);
    setToken(res.access_token);
    setUser(u);
  }

  async function register(email: string, username: string, password: string): Promise<void> {
    const res = await apiRegister(email, username, password);
    localStorage.setItem(TOKEN_KEY, res.access_token);
    const u = await apiGetMe(res.access_token);
    setToken(res.access_token);
    setUser(u);
  }

  function logout(): void {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, token, isAuthenticated: !!token, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

// @MX:ANCHOR: [AUTO] useAuth 훅 — 모든 인증 소비 컴포넌트의 진입점
// @MX:REASON: Login, Portfolio, Backtest, NavBar 4개 컴포넌트에서 사용
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth는 AuthProvider 내부에서만 사용 가능합니다');
  return ctx;
}
