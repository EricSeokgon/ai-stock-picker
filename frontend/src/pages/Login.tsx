// 로그인 / 회원가입 페이지 — 탭 전환 방식
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

type Tab = 'login' | 'register';

// 인라인 스타일 상수
const containerStyle: React.CSSProperties = {
  maxWidth: '400px',
  margin: '4rem auto',
  padding: '2rem',
  border: '1px solid #ddd',
  borderRadius: '8px',
  boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
};

const tabButtonStyle = (active: boolean): React.CSSProperties => ({
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

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '0.5rem 0.75rem',
  border: '1px solid #ccc',
  borderRadius: '4px',
  fontSize: '0.95rem',
  boxSizing: 'border-box',
};

const labelStyle: React.CSSProperties = {
  display: 'block',
  marginBottom: '0.25rem',
  fontSize: '0.875rem',
  color: '#333',
};

const fieldStyle: React.CSSProperties = { marginBottom: '1rem' };

const submitButtonStyle: React.CSSProperties = {
  width: '100%',
  padding: '0.6rem',
  background: '#1976d2',
  color: '#fff',
  border: 'none',
  borderRadius: '4px',
  fontSize: '1rem',
  cursor: 'pointer',
};

const errorStyle: React.CSSProperties = {
  padding: '0.6rem',
  background: '#ffebee',
  border: '1px solid #ef9a9a',
  borderRadius: '4px',
  color: '#c62828',
  marginBottom: '1rem',
  fontSize: '0.875rem',
};

export default function Login() {
  const [tab, setTab] = useState<Tab>('login');
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const { login, register } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (tab === 'login') {
        await login(email, password);
      } else {
        await register(email, username, password);
      }
      void navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : '오류가 발생했습니다');
    } finally {
      setLoading(false);
    }
  }

  function handleTabChange(next: Tab) {
    setTab(next);
    setError(null);
    setEmail('');
    setUsername('');
    setPassword('');
  }

  return (
    <div style={containerStyle}>
      <h2 style={{ textAlign: 'center', marginBottom: '1.5rem', color: '#0d47a1' }}>
        한국 주식 추천 서비스
      </h2>

      {/* 탭 헤더 */}
      <div style={{ display: 'flex', marginBottom: '1.5rem' }}>
        <button style={tabButtonStyle(tab === 'login')} onClick={() => handleTabChange('login')}>
          로그인
        </button>
        <button style={tabButtonStyle(tab === 'register')} onClick={() => handleTabChange('register')}>
          회원가입
        </button>
      </div>

      {/* 오류 메시지 */}
      {error && <div role="alert" style={errorStyle}>{error}</div>}

      {/* 폼 */}
      <form onSubmit={(e) => void handleSubmit(e)}>
        <div style={fieldStyle}>
          <label htmlFor="email" style={labelStyle}>이메일</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            style={inputStyle}
            autoComplete="email"
          />
        </div>

        {tab === 'register' && (
          <div style={fieldStyle}>
            <label htmlFor="username" style={labelStyle}>사용자명</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              style={inputStyle}
              autoComplete="username"
            />
          </div>
        )}

        <div style={fieldStyle}>
          <label htmlFor="password" style={labelStyle}>비밀번호</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            style={inputStyle}
            autoComplete={tab === 'login' ? 'current-password' : 'new-password'}
          />
        </div>

        <button type="submit" disabled={loading} style={{ ...submitButtonStyle, opacity: loading ? 0.7 : 1 }}>
          {loading ? '처리 중...' : tab === 'login' ? '로그인' : '회원가입'}
        </button>
      </form>
    </div>
  );
}
