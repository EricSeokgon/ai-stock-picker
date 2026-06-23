import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
export default function NewStockSuggestions({ stocks }) {
    if (stocks.length === 0) {
        return (_jsx("p", { style: { color: '#9ca3af', textAlign: 'center', padding: '16px' }, children: "\uCD94\uCC9C\uD560 \uC2E0\uADDC \uC885\uBAA9\uC774 \uC5C6\uC2B5\uB2C8\uB2E4." }));
    }
    return (_jsx("div", { style: { display: 'flex', flexDirection: 'column', gap: '10px' }, children: stocks.map((stock) => (_jsxs("div", { style: {
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                padding: '14px 16px',
                background: '#fff',
            }, children: [_jsxs("div", { style: { display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '6px' }, children: [_jsx("span", { style: {
                                fontFamily: 'monospace',
                                fontWeight: 700,
                                color: '#1d4ed8',
                                fontSize: '15px',
                            }, children: stock.krx_code }), _jsx("span", { style: { fontWeight: 600, color: '#111827', fontSize: '15px' }, children: stock.name }), _jsx("span", { style: {
                                background: '#f3f4f6',
                                borderRadius: '4px',
                                padding: '2px 8px',
                                fontSize: '12px',
                                color: '#6b7280',
                            }, children: stock.sector })] }), _jsx("p", { style: { margin: 0, fontSize: '13px', color: '#4b5563', lineHeight: 1.5 }, children: stock.reason })] }, stock.krx_code))) }));
}
