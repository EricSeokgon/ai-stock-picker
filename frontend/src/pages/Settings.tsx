// 설정 페이지 — 이메일 알림 구독 관리
// - 구독 상태 표시
// - 이메일 입력 + 구독 버튼
// - 구독 중이면 이메일 + 해지 버튼
// - 미인증 시 /login 리다이렉트

import { useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import {
  subscribeEmail,
  unsubscribeEmail,
  type EmailSubscription,
} from '../api/notifications';

export default function Settings() {
  const { isAuthenticated, token } = useAuth();
  const [subscription, setSubscription] = useState<EmailSubscription | null>(null);
  const [emailInput, setEmailInput] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // 미인증 시 로그인 페이지로 이동
  if (!isAuthenticated || !token) {
    return <Navigate to="/login" replace />;
  }

  // @MX:WARN: [AUTO] 422 에러는 특정 메시지로 처리 — 서버 응답 파싱 필요
  // @MX:REASON: 이메일 유효성 에러(422)와 일반 에러를 구분해야 함
  async function handleSubscribe(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    setError(null);
    setSubmitting(true);
    try {
      const result = await subscribeEmail(token, emailInput);
      setSubscription(result);
      setEmailInput('');
    } catch (err) {
      const msg = err instanceof Error ? err.message : '요청 실패. 다시 시도해주세요.';
      if (msg.includes('422') || msg.toLowerCase().includes('invalid') || msg.toLowerCase().includes('email')) {
        setError('유효한 이메일 주소를 입력해주세요.');
      } else {
        setError('요청 실패. 다시 시도해주세요.');
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function handleUnsubscribe() {
    if (!token) return;
    setError(null);
    setSubmitting(true);
    try {
      await unsubscribeEmail(token);
      setSubscription(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : '요청 실패. 다시 시도해주세요.');
    } finally {
      setSubmitting(false);
    }
  }

  const inputStyle: React.CSSProperties = {
    padding: '0.4rem 0.6rem',
    border: '1px solid #ccc',
    borderRadius: '4px',
    fontSize: '0.9rem',
    width: '240px',
  };

  const btnStyle: React.CSSProperties = {
    padding: '0.4rem 0.8rem',
    border: '1px solid #1976d2',
    borderRadius: '4px',
    background: '#1976d2',
    color: '#fff',
    cursor: 'pointer',
    fontSize: '0.9rem',
  };

  const outlineBtnStyle: React.CSSProperties = {
    ...btnStyle,
    background: '#fff',
    color: '#d32f2f',
    borderColor: '#d32f2f',
  };

  return (
    <div>
      <h2 style={{ color: '#0d47a1', marginBottom: '1.5rem' }}>설정</h2>

      <section aria-labelledby="email-section-title">
        <h3 id="email-section-title" style={{ fontSize: '1rem', marginBottom: '1rem', color: '#333' }}>
          이메일 알림 구독
        </h3>

        {error && (
          <p role="alert" style={{ color: '#c62828', fontSize: '0.875rem', marginBottom: '0.75rem' }}>
            {error}
          </p>
        )}

        {subscription ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.9rem', color: '#333' }}>
              구독 중: <strong>{subscription.email}</strong>
            </span>
            <button
              onClick={() => void handleUnsubscribe()}
              disabled={submitting}
              style={outlineBtnStyle}
              aria-label="이메일 구독 해지"
            >
              {submitting ? '처리 중...' : '구독 해지'}
            </button>
          </div>
        ) : (
          <form
            onSubmit={(e) => void handleSubscribe(e)}
            style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}
            aria-label="이메일 구독 폼"
          >
            <input
              type="email"
              value={emailInput}
              onChange={(e) => setEmailInput(e.target.value)}
              placeholder="이메일 주소 입력"
              style={inputStyle}
              aria-label="이메일 주소"
              required
            />
            <button
              type="submit"
              disabled={submitting}
              style={btnStyle}
            >
              {submitting ? '처리 중...' : '구독'}
            </button>
          </form>
        )}
      </section>
    </div>
  );
}
