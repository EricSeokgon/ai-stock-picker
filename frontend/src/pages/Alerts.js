import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
// 알림 설정 페이지 — 목표가·급등락 알림 관리 (SPEC-STOCK-020 REQ-FE-001)
import { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { fetchAlerts, createAlert, deleteAlert, toggleAlert, } from '../api/alerts';
// ─── 타입 뱃지 ────────────────────────────────────────────────────────────────
function AlertTypeBadge({ alertType }) {
    const map = {
        target_price: { label: '목표가', cls: 'bg-blue-100 text-blue-800' },
        surge_drop: { label: '급등락', cls: 'bg-orange-100 text-orange-800' },
        ex_dividend: { label: '배당락', cls: 'bg-purple-100 text-purple-800' },
    };
    const { label, cls } = map[alertType] ?? { label: alertType, cls: 'bg-gray-100 text-gray-700' };
    return (_jsx("span", { className: `inline-block text-xs font-medium px-2 py-0.5 rounded ${cls}`, children: label }));
}
function CreateAlertForm({ onCreated, token }) {
    const [krxCode, setKrxCode] = useState('');
    const [stockName, setStockName] = useState('');
    const [alertType, setAlertType] = useState('target_price');
    const [conditionValue, setConditionValue] = useState('');
    const [direction, setDirection] = useState('above');
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState(null);
    const handleSubmit = async (e) => {
        e.preventDefault();
        const value = parseFloat(conditionValue);
        if (!krxCode || isNaN(value) || value <= 0) {
            setError('종목코드와 조건 값을 올바르게 입력하세요.');
            return;
        }
        setSubmitting(true);
        setError(null);
        try {
            const payload = {
                krx_code: krxCode.trim(),
                stock_name: stockName.trim() || null,
                alert_type: alertType,
                condition_value: value,
                condition_direction: alertType === 'surge_drop' ? direction : direction,
            };
            const created = await createAlert(token, payload);
            onCreated(created);
            setKrxCode('');
            setStockName('');
            setConditionValue('');
        }
        catch (e) {
            setError(e.message);
        }
        finally {
            setSubmitting(false);
        }
    };
    return (_jsxs("form", { onSubmit: handleSubmit, className: "bg-white rounded-lg shadow p-4 mb-6 space-y-3", children: [_jsx("h3", { className: "font-semibold text-gray-800", children: "\uC0C8 \uC54C\uB9BC \uC124\uC815" }), error && _jsx("p", { className: "text-sm text-red-600", children: error }), _jsxs("div", { className: "grid grid-cols-2 gap-3", children: [_jsxs("div", { children: [_jsx("label", { className: "block text-xs text-gray-600 mb-1", children: "\uC885\uBAA9\uCF54\uB4DC *" }), _jsx("input", { className: "w-full border rounded px-2 py-1 text-sm", placeholder: "005930", value: krxCode, onChange: (e) => setKrxCode(e.target.value), maxLength: 10 })] }), _jsxs("div", { children: [_jsx("label", { className: "block text-xs text-gray-600 mb-1", children: "\uC885\uBAA9\uBA85 (\uC120\uD0DD)" }), _jsx("input", { className: "w-full border rounded px-2 py-1 text-sm", placeholder: "\uC0BC\uC131\uC804\uC790", value: stockName, onChange: (e) => setStockName(e.target.value) })] })] }), _jsxs("div", { className: "grid grid-cols-2 gap-3", children: [_jsxs("div", { children: [_jsx("label", { className: "block text-xs text-gray-600 mb-1", children: "\uC54C\uB9BC \uC720\uD615 *" }), _jsxs("select", { className: "w-full border rounded px-2 py-1 text-sm", value: alertType, onChange: (e) => setAlertType(e.target.value), children: [_jsx("option", { value: "target_price", children: "\uBAA9\uD45C\uAC00 \uC54C\uB9BC" }), _jsx("option", { value: "surge_drop", children: "\uAE09\uB4F1\uB77D \uC54C\uB9BC" })] })] }), _jsxs("div", { children: [_jsx("label", { className: "block text-xs text-gray-600 mb-1", children: "\uBC29\uD5A5" }), _jsx("select", { className: "w-full border rounded px-2 py-1 text-sm", value: direction, onChange: (e) => setDirection(e.target.value), children: alertType === 'surge_drop' ? (_jsxs(_Fragment, { children: [_jsx("option", { value: "either", children: "\uAE09\uB4F1 \uB610\uB294 \uAE09\uB77D" }), _jsx("option", { value: "above", children: "\uAE09\uB4F1\uB9CC" }), _jsx("option", { value: "below", children: "\uAE09\uB77D\uB9CC" })] })) : (_jsxs(_Fragment, { children: [_jsx("option", { value: "above", children: "\uC774\uC0C1 (\uC0C1\uD5A5 \uB3CC\uD30C)" }), _jsx("option", { value: "below", children: "\uC774\uD558 (\uD558\uD5A5 \uB3CC\uD30C)" })] })) })] })] }), _jsxs("div", { children: [_jsx("label", { className: "block text-xs text-gray-600 mb-1", children: alertType === 'target_price' ? '목표가 (원) *' : '임계값 (%) *' }), _jsx("input", { type: "number", step: alertType === 'target_price' ? '100' : '0.1', min: "0.01", className: "w-full border rounded px-2 py-1 text-sm", placeholder: alertType === 'target_price' ? '70000' : '5.0', value: conditionValue, onChange: (e) => setConditionValue(e.target.value) })] }), _jsx("button", { type: "submit", disabled: submitting, className: "w-full bg-blue-600 text-white rounded py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50", children: submitting ? '등록 중...' : '알림 등록' })] }));
}
function AlertCard({ alert, onDelete, onToggle }) {
    const directionLabel = {
        above: '이상',
        below: '이하',
        either: '급등/락',
    };
    const valueLabel = alert.alert_type === 'target_price'
        ? `${alert.condition_value.toLocaleString()}원`
        : `${alert.condition_value}%`;
    return (_jsx("div", { className: `bg-white rounded-lg shadow p-4 border-l-4 ${alert.is_triggered ? 'border-green-400' : alert.is_active ? 'border-blue-400' : 'border-gray-300'}`, children: _jsxs("div", { className: "flex items-start justify-between", children: [_jsxs("div", { className: "space-y-1", children: [_jsxs("div", { className: "flex items-center gap-2", children: [_jsx("span", { className: "font-semibold text-gray-900", children: alert.stock_name ? `${alert.stock_name} (${alert.krx_code})` : alert.krx_code }), _jsx(AlertTypeBadge, { alertType: alert.alert_type }), alert.is_triggered && (_jsx("span", { className: "text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded", children: "\uBC1C\uB3D9\uB428" })), !alert.is_active && !alert.is_triggered && (_jsx("span", { className: "text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded", children: "\uBE44\uD65C\uC131" }))] }), _jsxs("p", { className: "text-sm text-gray-600", children: [valueLabel, " ", directionLabel[alert.condition_direction ?? 'above'] ?? '', " \uB3C4\uB2EC \uC2DC \uC54C\uB9BC"] }), alert.triggered_message && (_jsx("p", { className: "text-xs text-green-700 mt-1", children: alert.triggered_message }))] }), _jsxs("div", { className: "flex gap-2 ml-2", children: [!alert.is_triggered && (_jsx("button", { onClick: () => onToggle(alert.id, !alert.is_active), className: `text-xs px-2 py-1 rounded ${alert.is_active ? 'bg-gray-100 text-gray-700 hover:bg-gray-200' : 'bg-blue-100 text-blue-700 hover:bg-blue-200'}`, children: alert.is_active ? '비활성화' : '활성화' })), _jsx("button", { onClick: () => onDelete(alert.id), className: "text-xs px-2 py-1 rounded bg-red-100 text-red-700 hover:bg-red-200", children: "\uC0AD\uC81C" })] })] }) }));
}
// ─── 메인 페이지 ─────────────────────────────────────────────────────────────
export default function AlertsPage() {
    const { token } = useAuth();
    const [alerts, setAlerts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const loadAlerts = async () => {
        if (!token)
            return;
        try {
            setLoading(true);
            const data = await fetchAlerts(token);
            setAlerts(data);
        }
        catch (e) {
            setError(e.message);
        }
        finally {
            setLoading(false);
        }
    };
    useEffect(() => {
        void loadAlerts();
    }, [token]);
    const handleCreated = (alert) => {
        setAlerts((prev) => [alert, ...prev]);
    };
    const handleDelete = async (id) => {
        if (!token)
            return;
        try {
            await deleteAlert(token, id);
            setAlerts((prev) => prev.filter((a) => a.id !== id));
        }
        catch (e) {
            setError(e.message);
        }
    };
    const handleToggle = async (id, isActive) => {
        if (!token)
            return;
        try {
            const updated = await toggleAlert(token, id, isActive);
            setAlerts((prev) => prev.map((a) => (a.id === id ? updated : a)));
        }
        catch (e) {
            setError(e.message);
        }
    };
    const activeAlerts = alerts.filter((a) => a.is_active && !a.is_triggered);
    const triggeredAlerts = alerts.filter((a) => a.is_triggered);
    const inactiveAlerts = alerts.filter((a) => !a.is_active && !a.is_triggered);
    return (_jsxs("div", { className: "max-w-2xl mx-auto px-4 py-6", children: [_jsx("h2", { className: "text-xl font-bold text-gray-900 mb-4", children: "\uC54C\uB9BC \uC124\uC815" }), _jsx("p", { className: "text-sm text-gray-600 mb-6", children: "\uBAA9\uD45C\uAC00 \uB610\uB294 \uAE09\uB4F1\uB77D \uC870\uAC74 \uC124\uC815 \uC2DC \uBC1C\uB3D9 \uC54C\uB9BC\uC744 \uBC1B\uC2B5\uB2C8\uB2E4. \uBC1C\uB3D9\uB41C \uC54C\uB9BC\uC740 \uC778\uBC15\uC2A4(\uC54C\uB9BC \uBCA8)\uC5D0\uC11C \uD655\uC778\uD558\uC138\uC694." }), token && _jsx(CreateAlertForm, { onCreated: handleCreated, token: token }), error && (_jsx("div", { className: "bg-red-50 border border-red-200 rounded p-3 mb-4 text-sm text-red-700", children: error })), loading ? (_jsx("p", { className: "text-center text-gray-500 py-8", children: "\uBD88\uB7EC\uC624\uB294 \uC911..." })) : alerts.length === 0 ? (_jsx("p", { className: "text-center text-gray-400 py-8", children: "\uB4F1\uB85D\uB41C \uC54C\uB9BC\uC774 \uC5C6\uC2B5\uB2C8\uB2E4." })) : (_jsxs("div", { className: "space-y-6", children: [activeAlerts.length > 0 && (_jsxs("section", { children: [_jsxs("h3", { className: "text-sm font-semibold text-gray-700 mb-2", children: ["\uD65C\uC131 \uC54C\uB9BC (", activeAlerts.length, ")"] }), _jsx("div", { className: "space-y-3", children: activeAlerts.map((a) => (_jsx(AlertCard, { alert: a, onDelete: handleDelete, onToggle: handleToggle }, a.id))) })] })), triggeredAlerts.length > 0 && (_jsxs("section", { children: [_jsxs("h3", { className: "text-sm font-semibold text-gray-700 mb-2", children: ["\uBC1C\uB3D9\uB41C \uC54C\uB9BC (", triggeredAlerts.length, ")"] }), _jsx("div", { className: "space-y-3", children: triggeredAlerts.map((a) => (_jsx(AlertCard, { alert: a, onDelete: handleDelete, onToggle: handleToggle }, a.id))) })] })), inactiveAlerts.length > 0 && (_jsxs("section", { children: [_jsxs("h3", { className: "text-sm font-semibold text-gray-700 mb-2", children: ["\uBE44\uD65C\uC131 \uC54C\uB9BC (", inactiveAlerts.length, ")"] }), _jsx("div", { className: "space-y-3", children: inactiveAlerts.map((a) => (_jsx(AlertCard, { alert: a, onDelete: handleDelete, onToggle: handleToggle }, a.id))) })] }))] }))] }));
}
