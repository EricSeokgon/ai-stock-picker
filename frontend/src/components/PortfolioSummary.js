import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// 포트폴리오 요약 위젯 — 대시보드에서 사용
import { useEffect, useState } from 'react';
import { useAuth } from '../auth/AuthContext';
import { apiListPortfolios, apiGetPerformance } from '../api/portfolio';
export function PortfolioSummary() {
    const { token, isAuthenticated } = useAuth();
    const [portfolio, setPortfolio] = useState(null);
    const [performance, setPerformance] = useState(null);
    const [loading, setLoading] = useState(false);
    useEffect(() => {
        if (!isAuthenticated || !token)
            return;
        setLoading(true);
        apiListPortfolios(token)
            .then(async (list) => {
            if (list.length === 0)
                return;
            const latest = list[list.length - 1];
            setPortfolio(latest);
            const perf = await apiGetPerformance(token, latest.id);
            setPerformance(perf);
        })
            .catch(() => { })
            .finally(() => setLoading(false));
    }, [isAuthenticated, token]);
    const containerStyle = {
        padding: '1rem',
        border: '1px solid #ddd',
        borderRadius: '6px',
        background: '#fff',
        fontSize: '0.875rem',
    };
    if (!isAuthenticated) {
        return (_jsx("div", { style: containerStyle, children: _jsx("p", { style: { margin: 0, color: '#666' }, children: "\uB85C\uADF8\uC778\uC774 \uD544\uC694\uD569\uB2C8\uB2E4" }) }));
    }
    if (loading) {
        return _jsx("div", { style: containerStyle, children: _jsx("p", { style: { margin: 0, color: '#666' }, children: "\uD3EC\uD2B8\uD3F4\uB9AC\uC624 \uB85C\uB529 \uC911..." }) });
    }
    if (!portfolio || !performance) {
        return _jsx("div", { style: containerStyle, children: _jsx("p", { style: { margin: 0, color: '#666' }, children: "\uD3EC\uD2B8\uD3F4\uB9AC\uC624 \uC5C6\uC74C" }) });
    }
    const pct = performance.total_return_pct;
    const pctColor = pct === null ? '#666' : pct >= 0 ? '#2e7d32' : '#c62828';
    const pctText = pct === null ? '-' : `${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%`;
    return (_jsxs("div", { style: containerStyle, children: [_jsx("div", { style: { fontWeight: 700, marginBottom: '0.4rem', color: '#0d47a1' }, children: portfolio.name }), _jsxs("div", { style: { display: 'flex', gap: '1rem' }, children: [_jsxs("div", { children: [_jsx("span", { style: { color: '#666' }, children: "\uC218\uC775\uB960 " }), _jsx("strong", { style: { color: pctColor }, children: pctText })] }), _jsxs("div", { children: [_jsx("span", { style: { color: '#666' }, children: "\uC885\uBAA9 \uC218 " }), _jsx("strong", { children: performance.holdings.length })] })] })] }));
}
