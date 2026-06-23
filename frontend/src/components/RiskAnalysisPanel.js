import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
// 포트폴리오 리스크 분석 패널 (SPEC-STOCK-027)
// 인라인 스타일 사용 — 기존 Portfolio.tsx 및 PortfolioScoreCard.tsx 스타일 패턴 준수
import { useEffect, useState } from 'react';
import { useAuth } from '../auth/AuthContext';
import { apiGetRiskAnalysis } from '../api/portfolio';
// @MX:ANCHOR: [AUTO] RiskAnalysisPanel — 리스크 분석 UI 공개 컴포넌트
// @MX:REASON: Portfolio.tsx에서 호출되는 외부 공개 컴포넌트 (fan_in >= 1, 추후 확장 예상)
const PERIOD_OPTIONS = [30, 60, 90, 180, 252];
// 상관계수(-1~1)를 RGB 색상으로 변환
function corrToRgb(corr) {
    const c = Math.max(-1, Math.min(1, corr));
    if (c < 0) {
        const r = Math.round(255 + c * 255);
        const g = Math.round(255 + c * 255);
        return `rgb(${r}, ${g}, 255)`;
    }
    if (c > 0) {
        const b = Math.round(255 - c * 255);
        const g = Math.round(255 - c * 255);
        return `rgb(255, ${g}, ${b})`;
    }
    return 'rgb(255, 255, 255)';
}
// 셀 텍스트 색상: |corr| >= 0.6이면 흰색, 아니면 검정
function corrTextColor(corr) {
    return Math.abs(corr) >= 0.6 ? '#fff' : '#111';
}
function CorrelationHeatmap({ matrix }) {
    const tickers = Object.keys(matrix);
    if (tickers.length === 0)
        return null;
    const cellStyle = {
        width: '60px',
        height: '40px',
        textAlign: 'center',
        fontSize: '0.75rem',
        border: '1px solid #e5e7eb',
        padding: '0 2px',
        lineHeight: '40px',
        overflow: 'hidden',
        whiteSpace: 'nowrap',
    };
    const headerCellStyle = {
        ...cellStyle,
        background: '#f3f4f6',
        fontWeight: 600,
        fontSize: '0.7rem',
        color: '#374151',
    };
    return (_jsx("div", { style: { overflowX: 'auto' }, children: _jsxs("table", { style: { borderCollapse: 'collapse', tableLayout: 'fixed' }, children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { style: { ...headerCellStyle, width: '64px' } }), tickers.map((t) => (_jsx("th", { style: headerCellStyle, children: t }, t)))] }) }), _jsx("tbody", { children: tickers.map((row) => (_jsxs("tr", { children: [_jsx("th", { style: headerCellStyle, children: row }), tickers.map((col) => {
                                const corr = matrix[row]?.[col] ?? 0;
                                const isDiag = row === col;
                                return (_jsx("td", { style: {
                                        ...cellStyle,
                                        background: corrToRgb(corr),
                                        color: corrTextColor(corr),
                                        fontWeight: isDiag ? 700 : 400,
                                    }, children: corr.toFixed(2) }, col));
                            })] }, row))) })] }) }));
}
function VolatilityTable({ holdings, portfolioVolatility, diversificationBenefit }) {
    const sorted = [...holdings].sort((a, b) => b.annualized_volatility_pct - a.annualized_volatility_pct);
    const thStyle = {
        textAlign: 'left',
        padding: '0.4rem 0.5rem',
        fontSize: '0.75rem',
        color: '#6b7280',
        borderBottom: '1px solid #e5e7eb',
        fontWeight: 600,
    };
    const tdStyle = {
        padding: '0.4rem 0.5rem',
        fontSize: '0.8rem',
        color: '#111',
        borderBottom: '1px solid #f3f4f6',
    };
    return (_jsxs("div", { children: [_jsxs("table", { style: { width: '100%', borderCollapse: 'collapse' }, children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { style: thStyle, children: "\uC885\uBAA9\uCF54\uB4DC" }), _jsx("th", { style: thStyle, children: "\uC885\uBAA9\uBA85" }), _jsx("th", { style: { ...thStyle, textAlign: 'right' }, children: "\uC5F0\uD658\uC0B0 \uBCC0\uB3D9\uC131(%)" }), _jsx("th", { style: { ...thStyle, textAlign: 'right' }, children: "\uAC00\uACA9 \uB370\uC774\uD130(\uC77C)" })] }) }), _jsx("tbody", { children: sorted.map((h) => (_jsxs("tr", { children: [_jsx("td", { style: tdStyle, children: h.krx_code }), _jsx("td", { style: tdStyle, children: h.name }), _jsxs("td", { style: { ...tdStyle, textAlign: 'right', fontWeight: 500 }, children: [h.annualized_volatility_pct.toFixed(2), "%"] }), _jsxs("td", { style: { ...tdStyle, textAlign: 'right' }, children: [h.price_data_days, "\uC77C"] })] }, h.krx_code))) })] }), _jsxs("div", { style: {
                    marginTop: '0.5rem',
                    padding: '0.4rem 0.5rem',
                    background: '#f3f4f6',
                    borderRadius: '4px',
                    fontSize: '0.8rem',
                    color: '#374151',
                    display: 'flex',
                    gap: '1.5rem',
                }, children: [_jsxs("span", { children: ["\uD3EC\uD2B8\uD3F4\uB9AC\uC624 \uBCC0\uB3D9\uC131: ", _jsxs("strong", { children: [portfolioVolatility.toFixed(2), "%"] })] }), _jsxs("span", { children: ["\uBD84\uC0B0 \uD6A8\uACFC: ", _jsxs("strong", { children: [diversificationBenefit.toFixed(2), "%"] })] })] })] }));
}
// @MX:WARN: [AUTO] 복수 useEffect + 비동기 fetch — period 변경 시 경쟁 상태 가능성
// @MX:REASON: period 변경 → fetch 재호출 시 이전 요청이 더 늦게 도착할 수 있음; cleanup 미구현
export default function RiskAnalysisPanel({ portfolioId }) {
    const { token } = useAuth();
    const [period, setPeriod] = useState(90);
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    useEffect(() => {
        if (!token)
            return;
        let cancelled = false;
        setLoading(true);
        setError(null);
        apiGetRiskAnalysis(token, portfolioId, period, false)
            .then((result) => {
            if (!cancelled)
                setData(result);
        })
            .catch((e) => {
            if (!cancelled)
                setError(e instanceof Error ? e.message : '리스크 분석 조회 실패');
        })
            .finally(() => {
            if (!cancelled)
                setLoading(false);
        });
        return () => { cancelled = true; };
    }, [token, portfolioId, period]);
    const sectionStyle = {
        marginTop: '1rem',
        padding: '0.75rem',
        border: '1px solid #fce7f3',
        borderRadius: '4px',
        background: '#fff7f9',
    };
    const periodBtnStyle = (active) => ({
        padding: '0.2rem 0.6rem',
        border: '1px solid #e5e7eb',
        borderRadius: '4px',
        cursor: 'pointer',
        fontSize: '0.75rem',
        background: active ? '#be185d' : '#fff',
        color: active ? '#fff' : '#374151',
        fontWeight: active ? 600 : 400,
    });
    return (_jsxs("div", { style: sectionStyle, children: [_jsxs("div", { style: { display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem', flexWrap: 'wrap' }, children: [_jsx("strong", { style: { fontSize: '0.875rem' }, children: "\uB9AC\uC2A4\uD06C \uBD84\uC11D" }), _jsx("div", { style: { display: 'flex', gap: '0.3rem', flexWrap: 'wrap' }, children: PERIOD_OPTIONS.map((p) => (_jsxs("button", { onClick: () => setPeriod(p), style: periodBtnStyle(period === p), "aria-pressed": period === p, "aria-label": `${p}일 기간 선택`, children: [p, "\uC77C"] }, p))) })] }), loading && (_jsx("div", { style: { padding: '1.5rem 0', textAlign: 'center', color: '#9ca3af', fontSize: '0.875rem' }, children: "\uBD84\uC11D \uC911..." })), error && !loading && (_jsxs("div", { style: { padding: '1rem', background: '#fef2f2', borderRadius: '4px', color: '#dc2626', fontSize: '0.85rem' }, children: [error, _jsx("button", { onClick: () => setPeriod((p) => p), style: { marginLeft: '0.75rem', padding: '0.2rem 0.5rem', fontSize: '0.75rem', cursor: 'pointer' }, "aria-label": "\uB2E4\uC2DC \uC2DC\uB3C4", children: "\uB2E4\uC2DC \uC2DC\uB3C4" })] })), data && !loading && !error && (_jsxs(_Fragment, { children: [_jsxs("div", { style: { marginBottom: '1rem' }, children: [_jsx("p", { style: { fontSize: '0.8rem', fontWeight: 600, color: '#374151', marginBottom: '0.4rem' }, children: "\uC0C1\uAD00\uACC4\uC218 \uB9E4\uD2B8\uB9AD\uC2A4" }), _jsx(CorrelationHeatmap, { matrix: data.correlation_matrix })] }), _jsxs("div", { children: [_jsx("p", { style: { fontSize: '0.8rem', fontWeight: 600, color: '#374151', marginBottom: '0.4rem' }, children: "\uBCF4\uC720 \uC885\uBAA9\uBCC4 \uBCC0\uB3D9\uC131" }), _jsx(VolatilityTable, { holdings: data.holdings_volatility, portfolioVolatility: data.portfolio_volatility_pct, diversificationBenefit: data.diversification_benefit_pct })] })] }))] }));
}
