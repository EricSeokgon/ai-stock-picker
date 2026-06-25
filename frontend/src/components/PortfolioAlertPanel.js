// 포트폴리오 알림 패널 (SPEC-STOCK-031)
// 목표 수익률 및 MDD 임계값 알림 설정 CRUD UI
// 인라인 스타일 사용 — 기존 Portfolio.tsx 스타일 패턴 준수
import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useState } from 'react';
import { useAuth } from '../auth/AuthContext';
import { apiCreatePortfolioAlert, apiDeletePortfolioAlert, apiListPortfolioAlerts, apiUpdatePortfolioAlert, } from '../api/portfolio';
// @MX:ANCHOR: [AUTO] PortfolioAlertPanel — 포트폴리오 알림 UI 공개 컴포넌트
// @MX:REASON: Portfolio.tsx에서 렌더링되며, 알림 CRUD API와 연동되는 외부 공개 컴포넌트
const ALERT_TYPE_LABELS = {
    portfolio_target_return: '목표 수익률 달성',
    portfolio_mdd_breach: 'MDD 임계값 초과',
    portfolio_value_below: '포트폴리오 평가액 이하',
    holding_return: '개별 종목 수익률 임계',
};
const ALERT_TYPE_HINTS = {
    portfolio_target_return: '수익률이 이 값(%) 이상이면 알림 발송',
    portfolio_mdd_breach: 'MDD가 이 값(%) 이하면 알림 발송 (음수 입력, 예: -15)',
    portfolio_value_below: '포트폴리오 평가액(원)이 이 값 이하이면 알림 발송 (SPEC-036)',
    holding_return: '개별 종목 수익률(%)이 임계값 이상/이하이면 알림 발송 (SPEC-036)',
};
export default function PortfolioAlertPanel({ portfolioId }) {
    const { token } = useAuth();
    const [alerts, setAlerts] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [alertType, setAlertType] = useState('portfolio_target_return');
    const [conditionValue, setConditionValue] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [formError, setFormError] = useState(null);
    const loadAlerts = async () => {
        if (!token)
            return;
        setLoading(true);
        setError(null);
        try {
            const data = await apiListPortfolioAlerts(token, portfolioId);
            setAlerts(data);
        }
        catch (e) {
            setError(e instanceof Error ? e.message : '알림 목록 조회 실패');
        }
        finally {
            setLoading(false);
        }
    };
    useEffect(() => {
        loadAlerts();
    }, [portfolioId, token]);
    const handleCreate = async () => {
        if (!token)
            return;
        const value = parseFloat(conditionValue);
        if (isNaN(value)) {
            setFormError('유효한 숫자를 입력하세요');
            return;
        }
        setSubmitting(true);
        setFormError(null);
        try {
            await apiCreatePortfolioAlert(token, portfolioId, { alert_type: alertType, condition_value: value });
            setConditionValue('');
            await loadAlerts();
        }
        catch (e) {
            setFormError(e instanceof Error ? e.message : '알림 생성 실패');
        }
        finally {
            setSubmitting(false);
        }
    };
    const handleToggleActive = async (alert) => {
        if (!token)
            return;
        try {
            await apiUpdatePortfolioAlert(token, portfolioId, alert.id, { is_active: !alert.is_active });
            await loadAlerts();
        }
        catch (e) {
            setError(e instanceof Error ? e.message : '알림 수정 실패');
        }
    };
    const handleDelete = async (alertId) => {
        if (!token || !window.confirm('이 알림을 삭제하시겠습니까?'))
            return;
        try {
            await apiDeletePortfolioAlert(token, portfolioId, alertId);
            await loadAlerts();
        }
        catch (e) {
            setError(e instanceof Error ? e.message : '알림 삭제 실패');
        }
    };
    return (_jsxs("div", { style: { background: '#fff', borderRadius: 8, padding: 20, marginTop: 16 }, children: [
        _jsx("h3", { style: { fontSize: 16, fontWeight: 700, marginBottom: 12, color: '#1a1a2e' }, children: "포트폴리오 알림 설정" }),
        _jsxs("div", { style: { display: 'flex', gap: 8, alignItems: 'flex-end', flexWrap: 'wrap', marginBottom: 16 }, children: [
            _jsxs("div", { children: [
                _jsx("label", { style: { display: 'block', fontSize: 12, color: '#666', marginBottom: 4 }, children: "알림 유형" }),
                _jsx("select", { value: alertType, onChange: (e) => setAlertType(e.target.value), style: { padding: '6px 10px', border: '1px solid #ddd', borderRadius: 6, fontSize: 14 }, children: Object.keys(ALERT_TYPE_LABELS).map((t) => (_jsx("option", { value: t, children: ALERT_TYPE_LABELS[t] }, t))) })
            ] }),
            _jsxs("div", { children: [
                _jsxs("label", { style: { display: 'block', fontSize: 12, color: '#666', marginBottom: 4 }, children: ["조건값 (%) — ", ALERT_TYPE_HINTS[alertType]] }),
                _jsx("input", { type: "number", step: "0.1", value: conditionValue, onChange: (e) => setConditionValue(e.target.value), placeholder: alertType === 'portfolio_mdd_breach' ? '-15.0' : '10.0', style: { padding: '6px 10px', border: '1px solid #ddd', borderRadius: 6, fontSize: 14, width: 100 } })
            ] }),
            _jsx("button", { onClick: handleCreate, disabled: submitting || !conditionValue, style: { padding: '7px 16px', background: submitting ? '#ccc' : '#4f46e5', color: '#fff', border: 'none', borderRadius: 6, cursor: submitting ? 'not-allowed' : 'pointer', fontSize: 14 }, children: submitting ? '저장 중...' : '알림 추가' })
        ] }),
        formError && _jsx("div", { style: { color: '#e53e3e', fontSize: 13, marginBottom: 8 }, children: formError }),
        loading ? (_jsx("div", { style: { color: '#888', fontSize: 14 }, children: "불러오는 중..." })) : error ? (_jsx("div", { style: { color: '#e53e3e', fontSize: 14 }, children: error })) : alerts.length === 0 ? (_jsx("div", { style: { color: '#aaa', fontSize: 14 }, children: "등록된 알림이 없습니다." })) : (_jsxs("table", { style: { width: '100%', borderCollapse: 'collapse', fontSize: 14 }, children: [
            _jsx("thead", { children: _jsxs("tr", { style: { background: '#f8f9fa', textAlign: 'left' }, children: [
                _jsx("th", { style: { padding: '8px 10px', borderBottom: '1px solid #eee' }, children: "유형" }),
                _jsx("th", { style: { padding: '8px 10px', borderBottom: '1px solid #eee' }, children: "조건값" }),
                _jsx("th", { style: { padding: '8px 10px', borderBottom: '1px solid #eee' }, children: "상태" }),
                _jsx("th", { style: { padding: '8px 10px', borderBottom: '1px solid #eee' }, children: "발화" }),
                _jsx("th", { style: { padding: '8px 10px', borderBottom: '1px solid #eee' }, children: "관리" })
            ] }) }),
            _jsx("tbody", { children: alerts.map((alert) => (_jsxs("tr", { style: { borderBottom: '1px solid #f0f0f0' }, children: [
                _jsx("td", { style: { padding: '8px 10px' }, children: ALERT_TYPE_LABELS[alert.alert_type] ?? alert.alert_type }),
                _jsxs("td", { style: { padding: '8px 10px' }, children: [alert.condition_value.toFixed(2), "%"] }),
                _jsx("td", { style: { padding: '8px 10px' }, children: _jsx("button", { onClick: () => handleToggleActive(alert), style: { padding: '3px 10px', background: alert.is_active ? '#48bb78' : '#e2e8f0', color: alert.is_active ? '#fff' : '#555', border: 'none', borderRadius: 12, cursor: 'pointer', fontSize: 12 }, children: alert.is_active ? '활성' : '비활성' }) }),
                _jsx("td", { style: { padding: '8px 10px', color: alert.is_triggered ? '#e53e3e' : '#aaa' }, children: alert.is_triggered ? _jsx("span", { title: alert.triggered_message ?? '', children: "발화됨" }) : '대기' }),
                _jsx("td", { style: { padding: '8px 10px' }, children: _jsx("button", { onClick: () => handleDelete(alert.id), style: { padding: '3px 10px', background: '#fee2e2', color: '#e53e3e', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 12 }, children: "삭제" }) })
            ] }, alert.id))) })
        ] }),
        alerts.filter((a) => a.is_triggered && a.triggered_message).length > 0 && (_jsxs("div", { style: { marginTop: 12 }, children: [
            _jsx("strong", { style: { fontSize: 13, color: '#e53e3e' }, children: "발화된 알림" }),
            alerts.filter((a) => a.is_triggered && a.triggered_message).map((a) => (_jsx("div", { style: { background: '#fff5f5', border: '1px solid #fed7d7', borderRadius: 6, padding: '8px 12px', marginTop: 6, fontSize: 13, color: '#c53030' }, children: a.triggered_message }, a.id)))
        ] }))
    ] }));
}
