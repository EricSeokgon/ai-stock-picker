import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// action 유형별 배경색
function actionStyle(action) {
    switch (action) {
        case 'buy':
            return { color: '#16a34a', fontWeight: 600 };
        case 'sell':
            return { color: '#dc2626', fontWeight: 600 };
        case 'hold':
        default:
            return { color: '#6b7280', fontWeight: 600 };
    }
}
function actionLabel(action) {
    switch (action) {
        case 'buy': return '매수';
        case 'sell': return '매도';
        case 'hold': return '유지';
    }
}
export default function RebalancingTable({ items }) {
    if (items.length === 0) {
        return (_jsx("p", { style: { color: '#9ca3af', textAlign: 'center', padding: '16px' }, children: "\uB9AC\uBC38\uB7F0\uC2F1 \uB300\uC0C1 \uC885\uBAA9\uC774 \uC5C6\uC2B5\uB2C8\uB2E4." }));
    }
    return (_jsx("div", { style: { overflowX: 'auto' }, children: _jsxs("table", { style: {
                width: '100%',
                borderCollapse: 'collapse',
                fontSize: '14px',
            }, children: [_jsx("thead", { children: _jsx("tr", { style: { background: '#f9fafb', borderBottom: '1px solid #e5e7eb' }, children: ['종목코드', '현재비중', '목표비중', '조정', '수량변화'].map((h) => (_jsx("th", { style: {
                                padding: '10px 12px',
                                textAlign: 'left',
                                fontWeight: 600,
                                color: '#374151',
                                whiteSpace: 'nowrap',
                            }, children: h }, h))) }) }), _jsx("tbody", { children: items.map((item) => (_jsxs("tr", { style: { borderBottom: '1px solid #f3f4f6' }, children: [_jsx("td", { style: { padding: '10px 12px', fontFamily: 'monospace', color: '#111827' }, children: item.krx_code }), _jsxs("td", { style: { padding: '10px 12px', color: '#6b7280' }, children: [item.current_pct.toFixed(1), "%"] }), _jsxs("td", { style: { padding: '10px 12px', fontWeight: 600, color: '#111827' }, children: [item.target_pct.toFixed(1), "%"] }), _jsx("td", { style: { padding: '10px 12px', ...actionStyle(item.action) }, children: actionLabel(item.action) }), _jsxs("td", { style: {
                                    padding: '10px 12px',
                                    color: item.delta_shares > 0 ? '#16a34a' : item.delta_shares < 0 ? '#dc2626' : '#6b7280',
                                    fontWeight: 600,
                                }, children: [item.delta_shares > 0 ? `+${item.delta_shares}` : item.delta_shares, "\uC8FC"] })] }, item.krx_code))) })] }) }));
}
