import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
// 설정 페이지 — 이메일 알림 구독 관리 + 알림 채널 설정
// - 구독 상태 표시
// - 이메일 입력 + 구독 버튼
// - 구독 중이면 이메일 + 해지 버튼
// - 미인증 시 /login 리다이렉트
// - 알림 채널 설정: 알림 유형별 이메일/텔레그램 활성화 여부
import { useState, useEffect } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { subscribeEmail, unsubscribeEmail, getNotificationPreferences, updateNotificationPreferences, } from '../api/notifications';
// 알림 유형 메타데이터 — 백엔드 alert_type 값과 한국어 레이블 매핑
const ALERT_TYPES = [
    { key: 'target_price', label: '목표가 도달' },
    { key: 'surge_drop', label: '급등락' },
    { key: 'volume_spike', label: '거래량 급증' },
    { key: 'ex_dividend', label: '배당일' },
    { key: 'rec_new', label: '신규 추천 진입' },
    { key: 'rec_dropped', label: '추천 이탈' },
    { key: 'rec_score_change', label: '추천 점수 변화' },
];
export default function Settings() {
    const { isAuthenticated, token } = useAuth();
    const [subscription, setSubscription] = useState(null);
    const [emailInput, setEmailInput] = useState('');
    const [error, setError] = useState(null);
    const [submitting, setSubmitting] = useState(false);
    // 알림 채널 설정 상태
    const [preferences, setPreferences] = useState([]);
    const [prefLoading, setPrefLoading] = useState(true);
    const [prefSaving, setPrefSaving] = useState(false);
    const [prefMessage, setPrefMessage] = useState(null);
    // 미인증 시 로그인 페이지로 이동
    if (!isAuthenticated || !token) {
        return _jsx(Navigate, { to: "/login", replace: true });
    }
    // 알림 채널 설정 초기 로드 — 컴포넌트 마운트 시 서버에서 설정 조회
    // eslint-disable-next-line react-hooks/rules-of-hooks
    useEffect(() => {
        if (!token)
            return;
        void (async () => {
            try {
                const data = await getNotificationPreferences(token);
                // 서버 응답에 없는 알림 유형은 기본값(모두 비활성)으로 채움
                const merged = ALERT_TYPES.map((at) => {
                    const found = data.find((d) => d.alert_type === at.key);
                    return found ?? { alert_type: at.key, email_enabled: false, telegram_enabled: false };
                });
                setPreferences(merged);
            }
            catch {
                // 조회 실패 시 모든 항목을 기본값으로 초기화
                setPreferences(ALERT_TYPES.map((at) => ({ alert_type: at.key, email_enabled: false, telegram_enabled: false })));
            }
            finally {
                setPrefLoading(false);
            }
        })();
    }, [token]);
    // @MX:WARN: [AUTO] 422 에러는 특정 메시지로 처리 — 서버 응답 파싱 필요
    // @MX:REASON: 이메일 유효성 에러(422)와 일반 에러를 구분해야 함
    async function handleSubscribe(e) {
        e.preventDefault();
        if (!token)
            return;
        setError(null);
        setSubmitting(true);
        try {
            const result = await subscribeEmail(token, emailInput);
            setSubscription(result);
            setEmailInput('');
        }
        catch (err) {
            const msg = err instanceof Error ? err.message : '요청 실패. 다시 시도해주세요.';
            if (msg.includes('422') || msg.toLowerCase().includes('invalid') || msg.toLowerCase().includes('email')) {
                setError('유효한 이메일 주소를 입력해주세요.');
            }
            else {
                setError('요청 실패. 다시 시도해주세요.');
            }
        }
        finally {
            setSubmitting(false);
        }
    }
    async function handleUnsubscribe() {
        if (!token)
            return;
        setError(null);
        setSubmitting(true);
        try {
            await unsubscribeEmail(token);
            setSubscription(null);
        }
        catch (err) {
            setError(err instanceof Error ? err.message : '요청 실패. 다시 시도해주세요.');
        }
        finally {
            setSubmitting(false);
        }
    }
    // 알림 채널 체크박스 변경 핸들러 — 해당 행의 특정 채널 값을 토글
    function handlePrefChange(alertType, channel, value) {
        setPreferences((prev) => prev.map((p) => p.alert_type === alertType ? { ...p, [channel]: value } : p));
    }
    // 알림 채널 설정 저장 핸들러
    async function handleSavePreferences() {
        if (!token)
            return;
        setPrefSaving(true);
        setPrefMessage(null);
        try {
            const saved = await updateNotificationPreferences(token, preferences);
            // 저장 성공 시 서버 응답값으로 상태 동기화
            const merged = ALERT_TYPES.map((at) => {
                const found = saved.find((d) => d.alert_type === at.key);
                return found ?? { alert_type: at.key, email_enabled: false, telegram_enabled: false };
            });
            setPreferences(merged);
            setPrefMessage({ type: 'success', text: '알림 채널 설정이 저장되었습니다.' });
        }
        catch (err) {
            setPrefMessage({ type: 'error', text: err instanceof Error ? err.message : '저장에 실패했습니다.' });
        }
        finally {
            setPrefSaving(false);
        }
    }
    const inputStyle = {
        padding: '0.4rem 0.6rem',
        border: '1px solid #ccc',
        borderRadius: '4px',
        fontSize: '0.9rem',
        width: '240px',
    };
    const btnStyle = {
        padding: '0.4rem 0.8rem',
        border: '1px solid #1976d2',
        borderRadius: '4px',
        background: '#1976d2',
        color: '#fff',
        cursor: 'pointer',
        fontSize: '0.9rem',
    };
    const outlineBtnStyle = {
        ...btnStyle,
        background: '#fff',
        color: '#d32f2f',
        borderColor: '#d32f2f',
    };
    return (_jsxs("div", { children: [_jsx("h2", { style: { color: '#0d47a1', marginBottom: '1.5rem' }, children: "\uC124\uC815" }), _jsxs("section", { "aria-labelledby": "email-section-title", children: [_jsx("h3", { id: "email-section-title", style: { fontSize: '1rem', marginBottom: '1rem', color: '#333' }, children: "\uC774\uBA54\uC77C \uC54C\uB9BC \uAD6C\uB3C5" }), error && (_jsx("p", { role: "alert", style: { color: '#c62828', fontSize: '0.875rem', marginBottom: '0.75rem' }, children: error })), subscription ? (_jsxs("div", { style: { display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }, children: [_jsxs("span", { style: { fontSize: '0.9rem', color: '#333' }, children: ["\uAD6C\uB3C5 \uC911: ", _jsx("strong", { children: subscription.email })] }), _jsx("button", { onClick: () => void handleUnsubscribe(), disabled: submitting, style: outlineBtnStyle, "aria-label": "\uC774\uBA54\uC77C \uAD6C\uB3C5 \uD574\uC9C0", children: submitting ? '처리 중...' : '구독 해지' })] })) : (_jsxs("form", { onSubmit: (e) => void handleSubscribe(e), style: { display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }, "aria-label": "\uC774\uBA54\uC77C \uAD6C\uB3C5 \uD3FC", children: [_jsx("input", { type: "email", value: emailInput, onChange: (e) => setEmailInput(e.target.value), placeholder: "\uC774\uBA54\uC77C \uC8FC\uC18C \uC785\uB825", style: inputStyle, "aria-label": "\uC774\uBA54\uC77C \uC8FC\uC18C", required: true }), _jsx("button", { type: "submit", disabled: submitting, style: btnStyle, children: submitting ? '처리 중...' : '구독' })] }))] }), _jsxs("section", { "aria-labelledby": "pref-section-title", style: { marginTop: '2.5rem' }, children: [_jsx("h3", { id: "pref-section-title", style: { fontSize: '1rem', marginBottom: '1rem', color: '#333' }, children: "\uC54C\uB9BC \uCC44\uB110 \uC124\uC815" }), prefMessage && (_jsx("p", { role: "alert", style: {
                            color: prefMessage.type === 'success' ? '#2e7d32' : '#c62828',
                            fontSize: '0.875rem',
                            marginBottom: '0.75rem',
                        }, children: prefMessage.text })), prefLoading ? (_jsx("p", { style: { color: '#666', fontSize: '0.9rem' }, children: "\uBD88\uB7EC\uC624\uB294 \uC911..." })) : (_jsxs(_Fragment, { children: [_jsxs("table", { "aria-label": "\uC54C\uB9BC \uCC44\uB110 \uC124\uC815 \uD14C\uC774\uBE14", style: {
                                    borderCollapse: 'collapse',
                                    fontSize: '0.9rem',
                                    minWidth: '360px',
                                }, children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { style: {
                                                        textAlign: 'left',
                                                        padding: '0.5rem 1rem 0.5rem 0',
                                                        fontWeight: 600,
                                                        color: '#555',
                                                        borderBottom: '1px solid #ddd',
                                                    }, children: "\uC54C\uB9BC \uC720\uD615" }), _jsx("th", { style: {
                                                        padding: '0.5rem 1.5rem',
                                                        fontWeight: 600,
                                                        color: '#555',
                                                        borderBottom: '1px solid #ddd',
                                                    }, children: "\uC774\uBA54\uC77C" }), _jsx("th", { style: {
                                                        padding: '0.5rem 1.5rem',
                                                        fontWeight: 600,
                                                        color: '#555',
                                                        borderBottom: '1px solid #ddd',
                                                    }, children: "\uD154\uB808\uADF8\uB7A8" })] }) }), _jsx("tbody", { children: ALERT_TYPES.map((at) => {
                                            const pref = preferences.find((p) => p.alert_type === at.key);
                                            return (_jsxs("tr", { children: [_jsx("td", { style: { padding: '0.45rem 1rem 0.45rem 0', color: '#333' }, children: at.label }), _jsx("td", { style: { textAlign: 'center', padding: '0.45rem 1.5rem' }, children: _jsx("input", { type: "checkbox", checked: pref?.email_enabled ?? false, onChange: (e) => handlePrefChange(at.key, 'email_enabled', e.target.checked), "aria-label": `${at.label} 이메일 알림`, style: { cursor: 'pointer' } }) }), _jsx("td", { style: { textAlign: 'center', padding: '0.45rem 1.5rem' }, children: _jsx("input", { type: "checkbox", checked: pref?.telegram_enabled ?? false, onChange: (e) => handlePrefChange(at.key, 'telegram_enabled', e.target.checked), "aria-label": `${at.label} 텔레그램 알림`, style: { cursor: 'pointer' } }) })] }, at.key));
                                        }) })] }), _jsx("button", { onClick: () => void handleSavePreferences(), disabled: prefSaving, style: { ...btnStyle, marginTop: '1rem' }, "aria-label": "\uC54C\uB9BC \uCC44\uB110 \uC124\uC815 \uC800\uC7A5", children: prefSaving ? '저장 중...' : '저장' })] }))] })] }));
}
