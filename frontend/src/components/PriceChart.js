import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// 주가 차트 — Recharts LineChart로 종가 N일 이력 표시
import { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { fetchStockPrices } from '../api/stocks';
// 날짜 포맷: YYYY-MM-DD → MM/DD
function formatDate(dateStr) {
    const parts = dateStr.split('-');
    if (parts.length >= 3)
        return `${parts[1]}/${parts[2]}`;
    return dateStr;
}
// 가격 포맷: 숫자 → 원화 문자열
function formatPrice(val) {
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return `${num.toLocaleString('ko-KR')}원`;
}
// @MX:ANCHOR: [AUTO] PriceChart — StockDetail, StockDetailPage에서 참조
// @MX:REASON: 차트 실패가 부모 컴포넌트 렌더링에 영향을 주면 안 됨; 독립적 오류 처리 필요
export function PriceChart({ krxCode, days = 30 }) {
    const [prices, setPrices] = useState([]);
    const [available, setAvailable] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);
    useEffect(() => {
        let cancelled = false;
        setLoading(true);
        setError(false);
        fetchStockPrices(krxCode, days)
            .then((data) => {
            if (cancelled)
                return;
            setAvailable(data.available);
            setPrices(data.prices);
        })
            .catch(() => {
            if (!cancelled)
                setError(true);
        })
            .finally(() => {
            if (!cancelled)
                setLoading(false);
        });
        return () => { cancelled = true; };
    }, [krxCode, days]);
    const fallback = (msg) => (_jsx("div", { style: {
            padding: '1.5rem',
            textAlign: 'center',
            color: '#888',
            fontSize: '0.85rem',
            backgroundColor: '#fafafa',
            borderRadius: '6px',
            border: '1px dashed #ddd',
        }, children: msg }));
    if (loading) {
        return (_jsxs("div", { role: "status", "aria-label": "\uCC28\uD2B8 \uB85C\uB529 \uC911", style: {
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '180px',
                gap: '0.5rem',
                color: '#888',
                fontSize: '0.85rem',
            }, children: [_jsx("span", { style: {
                        width: '16px',
                        height: '16px',
                        border: '2px solid #ddd',
                        borderTop: '2px solid #1976d2',
                        borderRadius: '50%',
                        animation: 'spin 0.7s linear infinite',
                        display: 'inline-block',
                    } }), _jsx("span", { children: "\uCC28\uD2B8 \uBD88\uB7EC\uC624\uB294 \uC911..." }), _jsx("style", { children: `@keyframes spin { to { transform: rotate(360deg); } }` })] }));
    }
    if (error || available === false || prices.length === 0) {
        return fallback('차트 데이터를 불러올 수 없습니다');
    }
    return (_jsxs("div", { children: [_jsxs("p", { style: { margin: '0 0 0.5rem', fontSize: '0.8rem', fontWeight: 600, color: '#333' }, children: ["\uC8FC\uAC00 (", days, "\uC77C)"] }), _jsx(ResponsiveContainer, { width: "100%", height: 180, children: _jsxs(LineChart, { data: prices, margin: { top: 4, right: 8, left: 8, bottom: 4 }, children: [_jsx(CartesianGrid, { strokeDasharray: "3 3", stroke: "#f0f0f0" }), _jsx(XAxis, { dataKey: "date", tickFormatter: formatDate, tick: { fontSize: 10, fill: '#888' }, interval: "preserveStartEnd" }), _jsx(YAxis, { tickFormatter: (v) => v.toLocaleString('ko-KR'), tick: { fontSize: 10, fill: '#888' }, width: 64 }), _jsx(Tooltip, { formatter: (val) => [formatPrice(val), '종가'], labelFormatter: (label) => `날짜: ${label}` }), _jsx(Line, { type: "monotone", dataKey: "close", stroke: "#1976d2", strokeWidth: 2, dot: false, activeDot: { r: 4 } })] }) })] }));
}
