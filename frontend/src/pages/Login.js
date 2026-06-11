import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// 로그인 / 회원가입 페이지 — 탭 전환 방식
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
// 인라인 스타일 상수
const containerStyle = {
    maxWidth: '400px',
    margin: '4rem auto',
    padding: '2rem',
    border: '1px solid #ddd',
    borderRadius: '8px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
};
const tabButtonStyle = (active) => ({
    flex: 1,
    padding: '0.6rem',
    border: 'none',
    borderBottom: active ? '2px solid #1976d2' : '2px solid transparent',
    background: 'transparent',
    fontWeight: active ? 700 : 400,
    color: active ? '#1976d2' : '#666',
    cursor: 'pointer',
    fontSize: '1rem',
});
const inputStyle = {
    width: '100%',
    padding: '0.5rem 0.75rem',
    border: '1px solid #ccc',
    borderRadius: '4px',
    fontSize: '0.95rem',
    boxSizing: 'border-box',
};
const labelStyle = {
    display: 'block',
    marginBottom: '0.25rem',
    fontSize: '0.875rem',
    color: '#333',
};
const fieldStyle = { marginBottom: '1rem' };
const submitButtonStyle = {
    width: '100%',
    padding: '0.6rem',
    background: '#1976d2',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    fontSize: '1rem',
    cursor: 'pointer',
};
const errorStyle = {
    padding: '0.6rem',
    background: '#ffebee',
    border: '1px solid #ef9a9a',
    borderRadius: '4px',
    color: '#c62828',
    marginBottom: '1rem',
    fontSize: '0.875rem',
};
export default function Login() {
    const [tab, setTab] = useState('login');
    const [email, setEmail] = useState('');
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(false);
    const { login, register } = useAuth();
    const navigate = useNavigate();
    async function handleSubmit(e) {
        e.preventDefault();
        setError(null);
        setLoading(true);
        try {
            if (tab === 'login') {
                await login(email, password);
            }
            else {
                await register(email, username, password);
            }
            void navigate('/');
        }
        catch (err) {
            setError(err instanceof Error ? err.message : '오류가 발생했습니다');
        }
        finally {
            setLoading(false);
        }
    }
    function handleTabChange(next) {
        setTab(next);
        setError(null);
        setEmail('');
        setUsername('');
        setPassword('');
    }
    return (_jsxs("div", { style: containerStyle, children: [_jsx("h2", { style: { textAlign: 'center', marginBottom: '1.5rem', color: '#0d47a1' }, children: "\uD55C\uAD6D \uC8FC\uC2DD \uCD94\uCC9C \uC11C\uBE44\uC2A4" }), _jsxs("div", { style: { display: 'flex', marginBottom: '1.5rem' }, children: [_jsx("button", { style: tabButtonStyle(tab === 'login'), onClick: () => handleTabChange('login'), children: "\uB85C\uADF8\uC778" }), _jsx("button", { style: tabButtonStyle(tab === 'register'), onClick: () => handleTabChange('register'), children: "\uD68C\uC6D0\uAC00\uC785" })] }), error && _jsx("div", { role: "alert", style: errorStyle, children: error }), _jsxs("form", { onSubmit: (e) => void handleSubmit(e), children: [_jsxs("div", { style: fieldStyle, children: [_jsx("label", { htmlFor: "email", style: labelStyle, children: "\uC774\uBA54\uC77C" }), _jsx("input", { id: "email", type: "email", value: email, onChange: (e) => setEmail(e.target.value), required: true, style: inputStyle, autoComplete: "email" })] }), tab === 'register' && (_jsxs("div", { style: fieldStyle, children: [_jsx("label", { htmlFor: "username", style: labelStyle, children: "\uC0AC\uC6A9\uC790\uBA85" }), _jsx("input", { id: "username", type: "text", value: username, onChange: (e) => setUsername(e.target.value), required: true, style: inputStyle, autoComplete: "username" })] })), _jsxs("div", { style: fieldStyle, children: [_jsx("label", { htmlFor: "password", style: labelStyle, children: "\uBE44\uBC00\uBC88\uD638" }), _jsx("input", { id: "password", type: "password", value: password, onChange: (e) => setPassword(e.target.value), required: true, style: inputStyle, autoComplete: tab === 'login' ? 'current-password' : 'new-password' })] }), _jsx("button", { type: "submit", disabled: loading, style: { ...submitButtonStyle, opacity: loading ? 0.7 : 1 }, children: loading ? '처리 중...' : tab === 'login' ? '로그인' : '회원가입' })] })] }));
}
