import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// 점수에 따른 색상 반환 (0-40: 빨강, 41-70: 주황, 71-100: 초록)
function scoreColor(value) {
    if (value >= 71)
        return '#16a34a';
    if (value >= 41)
        return '#d97706';
    return '#dc2626';
}
function BreakdownBar({ label, value }) {
    const color = scoreColor(value);
    return (_jsxs("div", { style: { marginBottom: '8px' }, children: [_jsxs("div", { style: { display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }, children: [_jsx("span", { style: { fontSize: '13px', color: '#4b5563' }, children: label }), _jsx("span", { style: { fontSize: '13px', fontWeight: 600, color }, children: value })] }), _jsx("div", { style: {
                    height: '8px',
                    background: '#e5e7eb',
                    borderRadius: '4px',
                    overflow: 'hidden',
                }, children: _jsx("div", { style: {
                        height: '100%',
                        width: `${value}%`,
                        background: color,
                        borderRadius: '4px',
                        transition: 'width 0.4s ease',
                    } }) })] }));
}
export default function PortfolioScoreCard({ score, breakdown }) {
    const mainColor = scoreColor(score);
    return (_jsxs("div", { style: {
            border: '1px solid #e5e7eb',
            borderRadius: '12px',
            padding: '20px',
            background: '#fff',
            maxWidth: '400px',
        }, children: [_jsxs("div", { style: { display: 'flex', alignItems: 'center', gap: '20px', marginBottom: '20px' }, children: [_jsx("div", { style: {
                            width: '80px',
                            height: '80px',
                            borderRadius: '50%',
                            border: `6px solid ${mainColor}`,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            flexShrink: 0,
                        }, children: _jsx("span", { style: { fontSize: '22px', fontWeight: 700, color: mainColor }, children: score }) }), _jsxs("div", { children: [_jsx("p", { style: { margin: 0, fontWeight: 600, fontSize: '16px', color: '#111827' }, children: "\uD3EC\uD2B8\uD3F4\uB9AC\uC624 \uC885\uD569 \uC810\uC218" }), _jsx("p", { style: { margin: '4px 0 0', fontSize: '13px', color: '#6b7280' }, children: score >= 71 ? '우수' : score >= 41 ? '보통' : '개선 필요' })] })] }), _jsxs("div", { children: [_jsx(BreakdownBar, { label: "\uBD84\uC0B0\uB3C4", value: breakdown.diversification }), _jsx(BreakdownBar, { label: "\uC704\uD5D8 \uADE0\uD615", value: breakdown.risk_balance }), _jsx(BreakdownBar, { label: "\uBAA8\uBA58\uD140", value: breakdown.momentum })] })] }));
}
