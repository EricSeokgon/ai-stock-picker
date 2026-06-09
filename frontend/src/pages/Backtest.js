import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// 백테스트 페이지 — 전략 실행 및 결과 시각화
import { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { useAuth } from '../auth/AuthContext';
import { apiRunBacktest, apiListBacktestRuns, apiGetBacktestResults, } from '../api/backtest';
// 상태 배지 색상
function statusColor(status) {
    switch (status) {
        case 'done': return '#2e7d32';
        case 'running': return '#f57c00';
        case 'pending': return '#1565c0';
        case 'failed': return '#c62828';
    }
}
function statusLabel(status) {
    switch (status) {
        case 'done': return '완료';
        case 'running': return '실행 중';
        case 'pending': return '대기';
        case 'failed': return '실패';
    }
}
function fmtPct(v) {
    if (v === null)
        return '-';
    return `${(v * 100).toFixed(2)}%`;
}
function fmtNum(v, digits = 3) {
    if (v === null)
        return '-';
    return v.toFixed(digits);
}
// 백테스트 상세 패널 (지표 + 차트)
function BacktestDetail({ run, token }) {
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    useEffect(() => {
        if (run.status !== 'done') {
            setLoading(false);
            return;
        }
        apiGetBacktestResults(token, run.id)
            .then(setResults)
            .catch((err) => setError(err instanceof Error ? err.message : '결과 조회 실패'))
            .finally(() => setLoading(false));
    }, [run.id, run.status, token]);
    const panelStyle = {
        padding: '1rem', background: '#f8f9fa', borderTop: '1px solid #ddd',
    };
    const metricRowStyle = {
        display: 'flex', gap: '1.5rem', flexWrap: 'wrap', marginBottom: '1rem',
    };
    const metricStyle = { fontSize: '0.875rem' };
    return (_jsxs("div", { style: panelStyle, children: [_jsxs("div", { style: metricRowStyle, children: [_jsxs("div", { style: metricStyle, children: [_jsx("span", { style: { color: '#666' }, children: "CAGR " }), _jsx("strong", { children: fmtPct(run.cagr) })] }), _jsxs("div", { style: metricStyle, children: [_jsx("span", { style: { color: '#666' }, children: "\uCD5C\uB300 \uB099\uD3ED " }), _jsx("strong", { children: fmtPct(run.max_drawdown) })] }), _jsxs("div", { style: metricStyle, children: [_jsx("span", { style: { color: '#666' }, children: "\uC0E4\uD504 \uBE44\uC728 " }), _jsx("strong", { children: fmtNum(run.sharpe_ratio) })] }), _jsxs("div", { style: metricStyle, children: [_jsx("span", { style: { color: '#666' }, children: "\uCD1D \uC218\uC775\uB960 " }), _jsx("strong", { children: fmtPct(run.total_return) })] })] }), run.status !== 'done' ? (_jsx("p", { style: { color: '#666', fontSize: '0.875rem' }, children: "\uC2E4\uD589\uC774 \uC644\uB8CC\uB41C \uD6C4 \uCC28\uD2B8\uAC00 \uD45C\uC2DC\uB429\uB2C8\uB2E4." })) : loading ? (_jsx("p", { style: { color: '#666', fontSize: '0.875rem' }, children: "\uACB0\uACFC \uB85C\uB529 \uC911..." })) : error ? (_jsx("p", { style: { color: '#c62828', fontSize: '0.875rem' }, children: error })) : results.length === 0 ? (_jsx("p", { style: { color: '#666', fontSize: '0.875rem' }, children: "\uACB0\uACFC \uB370\uC774\uD130\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4." })) : (_jsx("div", { style: { width: '100%', height: 280 }, children: _jsx(ResponsiveContainer, { children: _jsxs(LineChart, { data: results, margin: { top: 4, right: 16, bottom: 0, left: 0 }, children: [_jsx(CartesianGrid, { strokeDasharray: "3 3" }), _jsx(XAxis, { dataKey: "date", tick: { fontSize: 11 }, tickCount: 6 }), _jsx(YAxis, { tick: { fontSize: 11 }, tickFormatter: (v) => v.toFixed(0) }), _jsx(Tooltip, { formatter: (v) => v.toFixed(2) }), _jsx(Legend, {}), _jsx(Line, { type: "monotone", dataKey: "portfolio_value", stroke: "#1976d2", dot: false, name: "\uC804\uB7B5 \uD3EC\uD2B8\uD3F4\uB9AC\uC624" }), _jsx(Line, { type: "monotone", dataKey: "benchmark_value", stroke: "#f57c00", dot: false, name: "\uBCA4\uCE58\uB9C8\uD06C" })] }) }) }))] }));
}
export default function Backtest() {
    const { token } = useAuth();
    const [runs, setRuns] = useState([]);
    const [loadingList, setLoadingList] = useState(true);
    const [listError, setListError] = useState(null);
    const [expandedId, setExpandedId] = useState(null);
    // 실행 폼 상태
    const [strategy, setStrategy] = useState('momentum');
    const [startDate, setStartDate] = useState('2023-01-01');
    const [endDate, setEndDate] = useState('2024-01-01');
    const [universeSize, setUniverseSize] = useState('100');
    const [topN, setTopN] = useState('10');
    const [submitting, setSubmitting] = useState(false);
    const [submitError, setSubmitError] = useState(null);
    async function loadRuns() {
        if (!token)
            return;
        try {
            const list = await apiListBacktestRuns(token);
            setRuns(list);
        }
        catch (err) {
            setListError(err instanceof Error ? err.message : '목록 조회 실패');
        }
        finally {
            setLoadingList(false);
        }
    }
    useEffect(() => { void loadRuns(); }, [token]);
    async function handleSubmit(e) {
        e.preventDefault();
        if (!token)
            return;
        setSubmitting(true);
        setSubmitError(null);
        try {
            await apiRunBacktest(token, {
                strategy,
                start_date: startDate,
                end_date: endDate,
                universe_size: Number(universeSize),
                top_n: Number(topN),
            });
            await loadRuns();
        }
        catch (err) {
            setSubmitError(err instanceof Error ? err.message : '실행 실패');
        }
        finally {
            setSubmitting(false);
        }
    }
    if (!token)
        return _jsx("p", { children: "\uB85C\uADF8\uC778\uC774 \uD544\uC694\uD569\uB2C8\uB2E4." });
    const inputStyle = {
        padding: '0.35rem 0.5rem', border: '1px solid #ccc', borderRadius: '4px',
        fontSize: '0.875rem',
    };
    const labelStyle = { fontSize: '0.875rem', color: '#333' };
    return (_jsxs("div", { children: [_jsx("h2", { style: { color: '#0d47a1', marginBottom: '1.5rem' }, children: "\uBC31\uD14C\uC2A4\uD2B8" }), _jsxs("div", { style: { border: '1px solid #ddd', borderRadius: '6px', padding: '1rem', marginBottom: '2rem', background: '#fff' }, children: [_jsx("h3", { style: { margin: '0 0 1rem', fontSize: '1rem' }, children: "\uC0C8 \uBC31\uD14C\uC2A4\uD2B8 \uC2E4\uD589" }), submitError && _jsx("p", { style: { color: '#c62828', fontSize: '0.875rem' }, children: submitError }), _jsxs("form", { onSubmit: (e) => void handleSubmit(e), style: { display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'flex-end' }, children: [_jsx("div", { children: _jsxs("label", { style: labelStyle, children: ["\uC804\uB7B5", _jsx("br", {}), _jsxs("select", { value: strategy, onChange: (e) => setStrategy(e.target.value), style: inputStyle, children: [_jsx("option", { value: "momentum", children: "\uBAA8\uBA58\uD140" }), _jsx("option", { value: "volume", children: "\uAC70\uB798\uB7C9" })] })] }) }), _jsx("div", { children: _jsxs("label", { style: labelStyle, children: ["\uC2DC\uC791\uC77C", _jsx("br", {}), _jsx("input", { type: "date", value: startDate, onChange: (e) => setStartDate(e.target.value), required: true, style: inputStyle })] }) }), _jsx("div", { children: _jsxs("label", { style: labelStyle, children: ["\uC885\uB8CC\uC77C", _jsx("br", {}), _jsx("input", { type: "date", value: endDate, onChange: (e) => setEndDate(e.target.value), required: true, style: inputStyle })] }) }), _jsx("div", { children: _jsxs("label", { style: labelStyle, children: ["\uC720\uB2C8\uBC84\uC2A4 \uD06C\uAE30", _jsx("br", {}), _jsx("input", { type: "number", min: "1", value: universeSize, onChange: (e) => setUniverseSize(e.target.value), style: { ...inputStyle, width: '80px' } })] }) }), _jsx("div", { children: _jsxs("label", { style: labelStyle, children: ["\uC0C1\uC704 N\uC885\uBAA9", _jsx("br", {}), _jsx("input", { type: "number", min: "1", value: topN, onChange: (e) => setTopN(e.target.value), style: { ...inputStyle, width: '70px' } })] }) }), _jsx("button", { type: "submit", disabled: submitting, style: { padding: '0.4rem 1rem', background: '#1976d2', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '0.875rem' }, children: submitting ? '실행 중...' : '실행' })] })] }), _jsx("h3", { style: { fontSize: '1rem', marginBottom: '0.75rem' }, children: "\uC2E4\uD589 \uC774\uB825" }), loadingList && _jsx("p", { style: { color: '#666' }, children: "\uBD88\uB7EC\uC624\uB294 \uC911..." }), listError && _jsxs("p", { style: { color: '#c62828' }, children: ["\uC624\uB958: ", listError] }), !loadingList && runs.length === 0 && _jsx("p", { style: { color: '#666' }, children: "\uC544\uC9C1 \uC2E4\uD589\uB41C \uBC31\uD14C\uC2A4\uD2B8\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4." }), runs.map((run) => (_jsxs("div", { style: { border: '1px solid #ddd', borderRadius: '6px', marginBottom: '0.75rem', overflow: 'hidden' }, children: [_jsxs("div", { style: {
                            padding: '0.75rem 1rem', display: 'flex', alignItems: 'center',
                            justifyContent: 'space-between', cursor: 'pointer',
                            background: expandedId === run.id ? '#e3f2fd' : '#fff',
                        }, onClick: () => setExpandedId(expandedId === run.id ? null : run.id), role: "button", "aria-expanded": expandedId === run.id, children: [_jsxs("div", { style: { display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }, children: [_jsxs("span", { style: { fontWeight: 600 }, children: ["#", run.id, " \u2014 ", run.strategy === 'momentum' ? '모멘텀' : '거래량'] }), _jsxs("span", { style: { fontSize: '0.8rem', color: '#666' }, children: [run.start_date, " ~ ", run.end_date] }), _jsx("span", { style: {
                                            padding: '0.15rem 0.5rem', borderRadius: '12px', fontSize: '0.75rem',
                                            background: statusColor(run.status) + '20', color: statusColor(run.status), fontWeight: 600,
                                        }, children: statusLabel(run.status) })] }), _jsx("span", { style: { fontSize: '0.8rem', color: '#666' }, children: expandedId === run.id ? '▲' : '▼' })] }), expandedId === run.id && _jsx(BacktestDetail, { run: run, token: token })] }, run.id)))] }));
}
