import { jsx as _jsx } from "react/jsx-runtime";
// 인증 컨텍스트 — 로그인/회원가입/로그아웃 및 사용자 세션 관리
import { createContext, useContext, useEffect, useState } from 'react';
import { apiLogin, apiRegister, apiGetMe } from '../api/auth';
// 로컬스토리지 키
const TOKEN_KEY = 'stock_picker_token';
const AuthContext = createContext(null);
export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [token, setToken] = useState(null);
    // 마운트 시 저장된 토큰으로 세션 복원
    useEffect(() => {
        const saved = localStorage.getItem(TOKEN_KEY);
        if (!saved)
            return;
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
    async function login(email, password) {
        const res = await apiLogin(email, password);
        localStorage.setItem(TOKEN_KEY, res.access_token);
        const u = await apiGetMe(res.access_token);
        setToken(res.access_token);
        setUser(u);
    }
    async function register(email, username, password) {
        const res = await apiRegister(email, username, password);
        localStorage.setItem(TOKEN_KEY, res.access_token);
        const u = await apiGetMe(res.access_token);
        setToken(res.access_token);
        setUser(u);
    }
    function logout() {
        localStorage.removeItem(TOKEN_KEY);
        setToken(null);
        setUser(null);
    }
    return (_jsx(AuthContext.Provider, { value: { user, token, isAuthenticated: !!token, login, register, logout }, children: children }));
}
// @MX:ANCHOR: [AUTO] useAuth 훅 — 모든 인증 소비 컴포넌트의 진입점
// @MX:REASON: Login, Portfolio, Backtest, NavBar 4개 컴포넌트에서 사용
export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx)
        throw new Error('useAuth는 AuthProvider 내부에서만 사용 가능합니다');
    return ctx;
}
