import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// SPEC-STOCK-021: AI 시장 템포 위젯
// REQ-NEWS-SENT-002: 시장 전체 감성 시각화 (avg_score, label, positive/negative/neutral 비율)
import { useEffect, useState } from 'react';
import { fetchMarketSentiment } from '../api/news';
// 5단계 라벨 배지 스타일
function getLabelStyle(label) {
    switch (label) {
        case '매우긍정':
            return { backgroundColor: '#1b5e20', color: '#fff' };
        case '긍정':
            return { backgroundColor: '#e8f5e9', color: '#2e7d32' };
        case '중립':
            return { backgroundColor: '#f5f5f5', color: '#616161' };
        case '부정':
            return { backgroundColor: '#fff3e0', color: '#e65100' };
        case '매우부정':
            return { backgroundColor: '#ffebee', color: '#c62828' };
        default:
            return { backgroundColor: '#f5f5f5', color: '#9e9e9e' };
    }
}
export function MarketSentimentWidget() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    useEffect(() => {
        fetchMarketSentiment()
            .then(setData)
            .catch((e) => setError(e.message))
            .finally(() => setLoading(false));
    }, []);
    if (loading) {
        return (_jsx("div", { role: "status", "aria-label": "\uC2DC\uC7A5 \uAC10\uC131 \uB85C\uB529 \uC911", style: { padding: '16px', color: '#9e9e9e' }, children: "\uC2DC\uC7A5 \uAC10\uC131 \uBD84\uC11D \uC911..." }));
    }
    if (error) {
        return (_jsxs("div", { role: "alert", style: { padding: '16px', color: '#c62828' }, children: ["\uC2DC\uC7A5 \uAC10\uC131 \uB370\uC774\uD130 \uB85C\uB4DC \uC2E4\uD328: ", error] }));
    }
    if (!data || data.total === 0) {
        return (_jsx("div", { role: "region", "aria-label": "\uC2DC\uC7A5 \uAC10\uC131 \uC704\uC82F", style: { padding: '16px', color: '#9e9e9e' }, children: "\uBD84\uC11D\uB41C \uB274\uC2A4 \uB370\uC774\uD130\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4." }));
    }
    const labelStyle = getLabelStyle(data.label);
    const totalSafe = data.total > 0 ? data.total : 1;
    const positiveRatio = Math.round((data.positive / totalSafe) * 100);
    const negativeRatio = Math.round((data.negative / totalSafe) * 100);
    const neutralRatio = 100 - positiveRatio - negativeRatio;
    return (_jsxs("div", { role: "region", "aria-label": "\uC2DC\uC7A5 \uAC10\uC131 \uC704\uC82F", style: {
            padding: '16px',
            border: '1px solid #e0e0e0',
            borderRadius: '8px',
            background: '#fff',
        }, children: [_jsx("h3", { style: { margin: '0 0 12px', fontSize: '14px', color: '#424242' }, children: "AI \uC2DC\uC7A5 \uD15C\uD3EC (\uCD5C\uADFC 24\uC2DC\uAC04)" }), _jsxs("div", { style: { display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }, children: [_jsx("span", { "aria-label": `시장 감성 라벨: ${data.label ?? '데이터 없음'}`, style: {
                            ...labelStyle,
                            padding: '4px 10px',
                            borderRadius: '12px',
                            fontSize: '13px',
                            fontWeight: 600,
                        }, children: data.label ?? '데이터 없음' }), data.avg_score !== null && (_jsxs("span", { style: { fontSize: '12px', color: '#757575' }, children: ["\uD3C9\uADE0 \uC810\uC218 ", data.avg_score.toFixed(2)] }))] }), _jsx("div", { style: { marginBottom: '8px' }, children: _jsxs("div", { role: "img", "aria-label": `긍정 ${positiveRatio}%, 부정 ${negativeRatio}%, 중립 ${neutralRatio}%`, style: { display: 'flex', height: '8px', borderRadius: '4px', overflow: 'hidden' }, children: [_jsx("div", { style: { width: `${positiveRatio}%`, backgroundColor: '#2e7d32' } }), _jsx("div", { style: { width: `${neutralRatio}%`, backgroundColor: '#bdbdbd' } }), _jsx("div", { style: { width: `${negativeRatio}%`, backgroundColor: '#c62828' } })] }) }), _jsxs("div", { style: { display: 'flex', gap: '12px', fontSize: '12px', color: '#616161' }, children: [_jsxs("span", { children: ["\uAE0D\uC815 ", data.positive, "\uAC74"] }), _jsxs("span", { children: ["\uC911\uB9BD ", data.neutral, "\uAC74"] }), _jsxs("span", { children: ["\uBD80\uC815 ", data.negative, "\uAC74"] }), _jsxs("span", { style: { marginLeft: 'auto' }, children: ["\uCD1D ", data.total, "\uAC74"] })] })] }));
}
export default MarketSentimentWidget;
