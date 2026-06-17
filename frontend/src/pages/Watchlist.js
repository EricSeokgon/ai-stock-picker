import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// 관심 목록 관리 페이지 (REQ-FE-003)
// - 관심 목록 종목 표시 + 멀티플렉스 LivePrice (SPEC-STOCK-016 M5)
// - 삭제 버튼(✕)
// - 목표가 알림 추가/삭제
// - 미인증 시 /login 리다이렉트
// - 빈 목록 안내 메시지
import { useEffect, useMemo, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { getWatchlist, removeFromWatchlist, getAlerts, createAlert, deleteAlert, } from '../api/watchlist';
import { useLivePrices } from '../hooks/useLivePrices';
const initialAlertForm = {
    krxCode: '',
    targetPrice: '',
    direction: 'above',
};
export default function Watchlist() {
    const { isAuthenticated, token } = useAuth();
    const [items, setItems] = useState([]);
    const [alerts, setAlerts] = useState([]);
    // 멀티플렉스 WS — items가 바뀔 때만 심볼 목록 재계산 (REQ-FE-010)
    const symbols = useMemo(() => items.map((i) => i.krx_code), [items]);
    const livePrices = useLivePrices(symbols);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    // 열린 알림 폼 — krxCode를 키로 사용, '' 이면 닫힘
    const [openAlertForm, setOpenAlertForm] = useState(null);
    const [alertForm, setAlertForm] = useState(initialAlertForm);
    const [alertSubmitting, setAlertSubmitting] = useState(false);
    // 미인증 시 로그인 페이지로 이동
    if (!isAuthenticated || !token) {
        return _jsx(Navigate, { to: "/login", replace: true });
    }
    async function loadData() {
        if (!token)
            return;
        setLoading(true);
        setError(null);
        try {
            const [watchlistData, alertsData] = await Promise.all([
                getWatchlist(token),
                getAlerts(token),
            ]);
            setItems(watchlistData);
            setAlerts(alertsData);
        }
        catch (err) {
            setError(err instanceof Error ? err.message : '데이터 조회 실패');
        }
        finally {
            setLoading(false);
        }
    }
    useEffect(() => {
        void loadData();
    }, [token]);
    async function handleRemove(krxCode) {
        if (!token)
            return;
        try {
            await removeFromWatchlist(token, krxCode);
            setItems((prev) => prev.filter((item) => item.krx_code !== krxCode));
        }
        catch (err) {
            setError(err instanceof Error ? err.message : '삭제 실패');
        }
    }
    function handleOpenAlertForm(krxCode) {
        setOpenAlertForm(krxCode);
        setAlertForm({ krxCode, targetPrice: '', direction: 'above' });
        setError(null);
    }
    function handleCloseAlertForm() {
        setOpenAlertForm(null);
        setAlertForm(initialAlertForm);
    }
    // @MX:WARN: [AUTO] 알림 생성 실패 시 UI 롤백 포함 — 낙관적 업데이트 없음
    // @MX:REASON: 서버 응답 전 상태 변경 시 일관성 깨질 수 있음
    async function handleAlertSubmit(e) {
        e.preventDefault();
        if (!token || !alertForm.targetPrice)
            return;
        const price = parseFloat(alertForm.targetPrice);
        if (isNaN(price) || price <= 0) {
            setError('유효한 목표가를 입력해주세요.');
            return;
        }
        setAlertSubmitting(true);
        setError(null);
        try {
            const created = await createAlert(token, {
                krx_code: alertForm.krxCode,
                target_price: price,
                direction: alertForm.direction,
            });
            setAlerts((prev) => [...prev, created]);
            handleCloseAlertForm();
        }
        catch (err) {
            setError(err instanceof Error ? err.message : '알림 추가 실패');
        }
        finally {
            setAlertSubmitting(false);
        }
    }
    async function handleDeleteAlert(alertId) {
        if (!token)
            return;
        const previous = alerts;
        setAlerts((prev) => prev.filter((a) => a.id !== alertId));
        try {
            await deleteAlert(token, alertId);
        }
        catch (err) {
            // 실패 시 UI 롤백
            setAlerts(previous);
            setError(err instanceof Error ? err.message : '알림 삭제 실패');
        }
    }
    const rowStyle = {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0.6rem 0.8rem',
        borderBottom: '1px solid #eee',
        gap: '0.75rem',
        flexWrap: 'wrap',
    };
    const btnStyle = {
        background: 'none',
        border: '1px solid #ddd',
        borderRadius: '4px',
        cursor: 'pointer',
        padding: '0.2rem 0.5rem',
        fontSize: '0.85rem',
        color: '#666',
    };
    const activeAlerts = alerts.filter((a) => a.is_active);
    return (_jsxs("div", { children: [_jsx("h2", { style: { color: '#0d47a1', marginBottom: '1.5rem' }, children: "\uAD00\uC2EC \uBAA9\uB85D" }), loading && _jsx("p", { style: { color: '#666' }, children: "\uBD88\uB7EC\uC624\uB294 \uC911..." }), error && (_jsxs("p", { role: "alert", style: { color: '#c62828', fontSize: '0.875rem' }, children: ["\uC624\uB958: ", error] })), !loading && items.length === 0 && (_jsx("p", { style: { color: '#666', fontSize: '0.9rem' }, children: "\uAD00\uC2EC \uBAA9\uB85D\uC774 \uC5C6\uC2B5\uB2C8\uB2E4. \uCD94\uCC9C \uC885\uBAA9\uC5D0\uC11C \uBCC4\uD45C\uB97C \uB20C\uB7EC \uCD94\uAC00\uD558\uC138\uC694." })), items.length > 0 && (_jsx("div", { style: { border: '1px solid #ddd', borderRadius: '6px', overflow: 'hidden', marginBottom: '2rem' }, children: items.map((item) => (_jsxs("div", { children: [_jsxs("div", { style: rowStyle, children: [_jsxs("div", { style: { display: 'flex', alignItems: 'center', gap: '0.75rem', flex: 1 }, children: [_jsx("span", { style: { fontWeight: 600, fontSize: '0.95rem' }, children: item.krx_code }), livePrices[item.krx_code] ? (_jsxs("span", { style: {
                                                fontSize: '0.85rem',
                                                color: (livePrices[item.krx_code].change_pct ?? 0) >= 0 ? '#c62828' : '#1565c0',
                                                fontWeight: 500,
                                            }, "aria-label": `${item.krx_code} 현재가`, children: [livePrices[item.krx_code].price.toLocaleString(), "\uC6D0", ' ', "(", livePrices[item.krx_code].change_pct >= 0 ? '+' : '', livePrices[item.krx_code].change_pct.toFixed(2), "%)"] })) : (_jsx("span", { style: { fontSize: '0.8rem', color: '#999' }, children: "\uB85C\uB529 \uC911..." }))] }), _jsxs("div", { style: { display: 'flex', gap: '0.5rem' }, children: [_jsx("button", { onClick: () => handleOpenAlertForm(item.krx_code), "aria-label": `${item.krx_code} 알림 추가`, style: { ...btnStyle, color: '#1976d2', borderColor: '#1976d2' }, children: "\uC54C\uB9BC \uCD94\uAC00" }), _jsx("button", { onClick: () => void handleRemove(item.krx_code), "aria-label": `${item.krx_code} 관심 목록에서 삭제`, style: btnStyle, children: "\u2715" })] })] }), openAlertForm === item.krx_code && (_jsxs("form", { onSubmit: (e) => void handleAlertSubmit(e), style: {
                                display: 'flex',
                                gap: '0.5rem',
                                padding: '0.5rem 0.8rem',
                                backgroundColor: '#f5f5f5',
                                alignItems: 'center',
                                flexWrap: 'wrap',
                            }, "aria-label": `${item.krx_code} 알림 추가 폼`, children: [_jsx("input", { type: "number", placeholder: "\uBAA9\uD45C\uAC00", value: alertForm.targetPrice, onChange: (e) => setAlertForm((prev) => ({ ...prev, targetPrice: e.target.value })), style: { flex: '1 1 100px', minWidth: '80px', padding: '0.25rem 0.5rem', border: '1px solid #ccc', borderRadius: '4px' }, "aria-label": "\uBAA9\uD45C\uAC00 \uC785\uB825", min: "0", step: "any", required: true }), _jsxs("select", { value: alertForm.direction, onChange: (e) => setAlertForm((prev) => ({
                                        ...prev,
                                        direction: e.target.value,
                                    })), style: { padding: '0.25rem 0.5rem', border: '1px solid #ccc', borderRadius: '4px' }, "aria-label": "\uBC29\uD5A5 \uC120\uD0DD", children: [_jsx("option", { value: "above", children: "\uC774\uC0C1" }), _jsx("option", { value: "below", children: "\uC774\uD558" })] }), _jsx("button", { type: "submit", disabled: alertSubmitting, style: { ...btnStyle, color: '#fff', background: '#1976d2', borderColor: '#1976d2' }, children: alertSubmitting ? '추가 중...' : '추가' }), _jsx("button", { type: "button", onClick: handleCloseAlertForm, style: btnStyle, children: "\uCDE8\uC18C" })] }))] }, item.id))) })), _jsxs("div", { children: [_jsx("h3", { style: { color: '#333', fontSize: '1rem', marginBottom: '0.75rem' }, children: "\uD65C\uC131 \uAC00\uACA9 \uC54C\uB9BC" }), activeAlerts.length === 0 ? (_jsx("p", { style: { color: '#999', fontSize: '0.875rem' }, children: "\uB4F1\uB85D\uB41C \uAC00\uACA9 \uC54C\uB9BC\uC774 \uC5C6\uC2B5\uB2C8\uB2E4." })) : (_jsx("div", { style: { border: '1px solid #ddd', borderRadius: '6px', overflow: 'hidden' }, children: activeAlerts.map((alert) => (_jsxs("div", { style: rowStyle, children: [_jsxs("span", { style: { fontSize: '0.9rem', flex: '1 1 auto', wordBreak: 'break-word' }, children: [_jsx("strong", { children: alert.krx_code }), ' ', alert.direction === 'above' ? '이상' : '이하', ' ', alert.target_price.toLocaleString(), "\uC6D0"] }), _jsx("button", { onClick: () => void handleDeleteAlert(alert.id), "aria-label": `${alert.krx_code} 알림 삭제`, style: btnStyle, children: "\uC0AD\uC81C" })] }, alert.id))) }))] })] }));
}
