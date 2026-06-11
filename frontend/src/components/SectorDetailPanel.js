import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// 섹터 상세 패널 — 선택된 섹터의 트렌드 차트와 구성 종목 표시
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { fetchSectorDetail } from '../api/sectors';
// trade_date를 MM/DD 형식으로 변환
function formatDate(dateStr) {
    const parts = dateStr.split('-');
    if (parts.length >= 3) {
        return `${parts[1]}/${parts[2]}`;
    }
    return dateStr;
}
function TrendChart({ trends }) {
    if (trends.length === 0) {
        return (_jsx("p", { style: { color: '#888', fontSize: '0.875rem', textAlign: 'center', padding: '1.5rem 0' }, "data-testid": "no-trend-data", children: "\uD2B8\uB80C\uB4DC \uB370\uC774\uD130 \uC5C6\uC74C" }));
    }
    const chartData = trends.map((t) => ({
        date: formatDate(t.trade_date),
        trend_score: t.trend_score,
    }));
    return (_jsx(ResponsiveContainer, { width: "100%", height: 180, children: _jsxs(LineChart, { data: chartData, margin: { top: 8, right: 12, left: -20, bottom: 0 }, children: [_jsx(CartesianGrid, { strokeDasharray: "3 3", stroke: "#f0f0f0" }), _jsx(XAxis, { dataKey: "date", tick: { fontSize: 11 } }), _jsx(YAxis, { domain: [-1, 1], tick: { fontSize: 11 } }), _jsx(Tooltip, { formatter: (value) => [value.toFixed(3), '트렌드 점수'], labelFormatter: (label) => `날짜: ${label}` }), _jsx(Line, { type: "monotone", dataKey: "trend_score", stroke: "#1976d2", strokeWidth: 2, dot: false, activeDot: { r: 4 } })] }) }));
}
function StockList({ stocks, totalStocks }) {
    const navigate = useNavigate();
    return (_jsxs("div", { children: [_jsxs("p", { style: { fontSize: '0.8rem', color: '#888', marginBottom: '0.5rem' }, children: ["\uCD1D ", totalStocks, "\uAC1C \uC885\uBAA9"] }), stocks.length === 0 ? (_jsx("p", { style: { color: '#aaa', fontSize: '0.875rem' }, children: "\uC885\uBAA9 \uB370\uC774\uD130 \uC5C6\uC74C" })) : (_jsx("ul", { style: { padding: 0, margin: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.4rem' }, children: stocks.map((stock) => (_jsx("li", { children: _jsxs("button", { onClick: () => void navigate(`/stocks/${stock.krx_code}`), style: {
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            width: '100%',
                            padding: '0.4rem 0.6rem',
                            border: '1px solid #e0e0e0',
                            borderRadius: '4px',
                            backgroundColor: '#fafafa',
                            cursor: 'pointer',
                            fontSize: '0.875rem',
                            textAlign: 'left',
                        }, "aria-label": `${stock.krx_code} 종목 상세 보기`, children: [_jsx("span", { style: { fontWeight: 600, color: '#1976d2' }, children: stock.krx_code }), _jsxs("span", { style: { color: '#888', fontSize: '0.8rem' }, children: ["\uC5B8\uAE09 ", stock.mention_count, "\uD68C"] })] }) }, stock.krx_code))) }))] }));
}
// @MX:ANCHOR: [AUTO] 섹터 상세 패널 — Sectors 페이지에서 단독 렌더링
// @MX:REASON: 섹터 선택 시 이 컴포넌트만 사용되므로 API 호출과 UI 책임이 집중됨
export function SectorDetailPanel({ sector, onClose }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    useEffect(() => {
        let cancelled = false;
        async function load() {
            setLoading(true);
            setError(null);
            try {
                const result = await fetchSectorDetail(sector, 7);
                if (!cancelled)
                    setData(result);
            }
            catch (err) {
                if (!cancelled)
                    setError(err instanceof Error ? err.message : '상세 정보를 불러오는 중 오류가 발생했습니다.');
            }
            finally {
                if (!cancelled)
                    setLoading(false);
            }
        }
        void load();
        return () => { cancelled = true; };
    }, [sector]);
    return (_jsxs("div", { style: {
            border: '1px solid #e0e0e0',
            borderRadius: '8px',
            padding: '1.25rem',
            backgroundColor: '#fff',
            boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
        }, "aria-label": `${sector} 섹터 상세`, children: [_jsxs("div", { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }, children: [_jsxs("h3", { style: { margin: 0, fontSize: '1rem', fontWeight: 700, color: '#212121' }, children: [sector, " \uC139\uD130 \uC0C1\uC138"] }), _jsx("button", { onClick: onClose, "aria-label": "\uB2EB\uAE30", style: {
                            background: 'none',
                            border: 'none',
                            cursor: 'pointer',
                            fontSize: '1.25rem',
                            color: '#888',
                            lineHeight: 1,
                            padding: '0.2rem',
                        }, children: "\u2715" })] }), loading && (_jsx("div", { role: "status", "aria-live": "polite", style: { textAlign: 'center', padding: '2rem', color: '#888' }, children: "\uBD88\uB7EC\uC624\uB294 \uC911..." })), !loading && error && (_jsxs("div", { role: "alert", style: { color: '#c62828', fontSize: '0.875rem' }, children: ["\uC624\uB958: ", error] })), !loading && !error && data && (_jsxs("div", { children: [_jsxs("div", { style: { marginBottom: '1rem' }, children: [_jsx("h4", { style: { fontSize: '0.875rem', color: '#555', margin: '0 0 0.5rem 0' }, children: "\uD2B8\uB80C\uB4DC \uC810\uC218 \uCD94\uC774 (\uCD5C\uADFC 7\uC77C)" }), _jsx(TrendChart, { trends: data.trends })] }), _jsxs("div", { children: [_jsx("h4", { style: { fontSize: '0.875rem', color: '#555', margin: '0 0 0.5rem 0' }, children: "\uAD6C\uC131 \uC885\uBAA9" }), _jsx(StockList, { stocks: data.stocks, totalStocks: data.total_stocks })] })] }))] }));
}
