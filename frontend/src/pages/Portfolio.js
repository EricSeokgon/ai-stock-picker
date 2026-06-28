import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
// 포트폴리오 관리 페이지
import { useEffect, useState } from 'react';
import { useAuth } from '../auth/AuthContext';
import { apiListPortfolios, apiCreatePortfolio, apiListHoldings, apiAddHolding, apiGetPerformance, apiOptimizePortfolio, } from '../api/portfolio';
import PortfolioScoreCard from '../components/PortfolioScoreCard';
import RebalancingTable from '../components/RebalancingTable';
import NewStockSuggestions from '../components/NewStockSuggestions';
import RiskAnalysisPanel from '../components/RiskAnalysisPanel';
import BacktestPanel from '../components/BacktestPanel';
// @MX:NOTE: [AUTO] PortfolioAlertPanel — SPEC-STOCK-031 포트폴리오 알림 설정 패널
import PortfolioAlertPanel from '../components/PortfolioAlertPanel';
// SPEC-STOCK-033: 배당 수익률 분석 강화 컴포넌트
import DividendSummaryPanel from '../components/DividendSummaryPanel';
import DividendCalendarView from '../components/DividendCalendarView';
import DRIPSimulator from '../components/DRIPSimulator';
import BenchmarkComparisonPanel from '../components/BenchmarkComparisonPanel';
import BenchmarkChartView from '../components/BenchmarkChartView';
import PortfolioReportPanel from '../components/PortfolioReportPanel';
import AICommentaryPanel from '../components/AICommentaryPanel';
import { getPortfolioDividends } from '../api/dividends';
import { LivePriceBadge } from '../components/LivePriceBadge';
import { PerformanceDonutChart } from '../components/PerformanceDonutChart';
import { fetchRebalanceAdvice, fetchRiskProfile, fetchMarketBriefing, } from '../api/advice';
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
// 색상 유틸리티
function returnColor(pct) {
    if (pct === null)
        return '#666';
    return pct >= 0 ? '#2e7d32' : '#c62828';
}
function formatPct(pct) {
    if (pct === null)
        return '-';
    return `${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%`;
}
// 포트폴리오 생성 모달
function CreatePortfolioModal({ onClose, onCreate, }) {
    const [name, setName] = useState('');
    const [description, setDescription] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    async function handleSubmit(e) {
        e.preventDefault();
        setLoading(true);
        setError(null);
        try {
            await onCreate(name, description || undefined);
            onClose();
        }
        catch (err) {
            setError(err instanceof Error ? err.message : '생성 실패');
        }
        finally {
            setLoading(false);
        }
    }
    const overlayStyle = {
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100,
    };
    const boxStyle = {
        background: '#fff', padding: '1.5rem', borderRadius: '8px',
        width: '360px', boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
    };
    return (_jsx("div", { style: overlayStyle, role: "dialog", "aria-modal": "true", "aria-label": "\uD3EC\uD2B8\uD3F4\uB9AC\uC624 \uC0DD\uC131", children: _jsxs("div", { style: boxStyle, children: [_jsx("h3", { style: { marginTop: 0 }, children: "\uC0C8 \uD3EC\uD2B8\uD3F4\uB9AC\uC624 \uC0DD\uC131" }), error && _jsx("p", { style: { color: '#c62828', fontSize: '0.875rem' }, children: error }), _jsxs("form", { onSubmit: (e) => void handleSubmit(e), children: [_jsxs("div", { style: { marginBottom: '0.75rem' }, children: [_jsx("label", { style: { display: 'block', marginBottom: '0.25rem', fontSize: '0.875rem' }, children: "\uC774\uB984 *" }), _jsx("input", { value: name, onChange: (e) => setName(e.target.value), required: true, style: { width: '100%', padding: '0.4rem 0.5rem', border: '1px solid #ccc', borderRadius: '4px', boxSizing: 'border-box' } })] }), _jsxs("div", { style: { marginBottom: '1rem' }, children: [_jsx("label", { style: { display: 'block', marginBottom: '0.25rem', fontSize: '0.875rem' }, children: "\uC124\uBA85 (\uC120\uD0DD)" }), _jsx("input", { value: description, onChange: (e) => setDescription(e.target.value), style: { width: '100%', padding: '0.4rem 0.5rem', border: '1px solid #ccc', borderRadius: '4px', boxSizing: 'border-box' } })] }), _jsxs("div", { style: { display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }, children: [_jsx("button", { type: "button", onClick: onClose, style: { padding: '0.4rem 0.9rem', border: '1px solid #ccc', borderRadius: '4px', cursor: 'pointer' }, children: "\uCDE8\uC18C" }), _jsx("button", { type: "submit", disabled: loading, style: { padding: '0.4rem 0.9rem', background: '#1976d2', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }, children: loading ? '생성 중...' : '생성' })] })] })] }) }));
}
// 배당 분석 섹션 컴포넌트 (SPEC-STOCK-019)
function DividendsSection({ portfolioId, token }) {
    const [loading, setLoading] = useState(false);
    const [data, setData] = useState(null);
    const [error, setError] = useState(null);
    const [showCalendar, setShowCalendar] = useState(false);
    async function handleFetch() {
        setLoading(true);
        setError(null);
        try {
            const result = await getPortfolioDividends(token, portfolioId);
            setData(result);
        }
        catch {
            setError('배당 데이터를 가져오지 못했습니다. 잠시 후 다시 시도하세요.');
        }
        finally {
            setLoading(false);
        }
    }
    const sectionStyle = {
        marginTop: '1rem',
        padding: '0.75rem',
        border: '1px solid #e8f5e9',
        borderRadius: '4px',
        background: '#f9fff9',
    };
    const MONTHS = ['1월', '2월', '3월', '4월', '5월', '6월', '7월', '8월', '9월', '10월', '11월', '12월'];
    return (_jsxs("div", { style: sectionStyle, children: [_jsxs("div", { style: { display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem', flexWrap: 'wrap' }, children: [_jsx("strong", { style: { fontSize: '0.875rem' }, children: "\uBC30\uB2F9 \uBD84\uC11D" }), _jsx("button", { onClick: () => void handleFetch(), disabled: loading, style: {
                            padding: '0.3rem 0.7rem', background: '#2e7d32', color: '#fff',
                            border: 'none', borderRadius: '4px', cursor: loading ? 'default' : 'pointer',
                            fontSize: '0.8rem', opacity: loading ? 0.7 : 1,
                        }, children: loading ? '조회 중...' : '배당 분석 조회' }), data && (_jsx("button", { onClick: () => setShowCalendar((v) => !v), style: { background: 'none', border: 'none', cursor: 'pointer', fontSize: '0.8rem', color: '#666' }, children: showCalendar ? '▲ 캘린더 닫기' : '▼ 배당 캘린더 보기' }))] }), error && (_jsx("p", { style: { color: '#c62828', fontSize: '0.8rem', margin: '0.25rem 0' }, children: error })), data && (_jsxs(_Fragment, { children: [_jsxs("div", { style: { display: 'flex', gap: '1.5rem', marginBottom: '0.75rem', flexWrap: 'wrap' }, children: [_jsxs("div", { children: [_jsx("span", { style: { fontSize: '0.75rem', color: '#555' }, children: "\uC5F0\uAC04 \uBC30\uB2F9 \uC218\uC785" }), _jsx("br", {}), _jsxs("strong", { style: { fontSize: '0.95rem', color: '#2e7d32' }, children: ["\u20A9", Math.round(data.total_annual_income).toLocaleString()] })] }), _jsxs("div", { children: [_jsx("span", { style: { fontSize: '0.75rem', color: '#555' }, children: "\uAC00\uC911 \uD3C9\uADE0 \uBC30\uB2F9\uC218\uC775\uB960" }), _jsx("br", {}), _jsx("strong", { style: { fontSize: '0.95rem' }, children: data.weighted_avg_yield > 0 ? `${data.weighted_avg_yield.toFixed(2)}%` : '-' })] }), _jsxs("div", { children: [_jsx("span", { style: { fontSize: '0.75rem', color: '#555' }, children: "\uBC30\uB2F9 \uD655\uC778 \uC885\uBAA9" }), _jsx("br", {}), _jsxs("strong", { children: [data.coverage_count, " / ", data.total_holdings] })] })] }), data.holdings.length > 0 && (_jsx("div", { style: { overflowX: 'auto', marginBottom: '0.75rem' }, children: _jsxs("table", { style: { width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', minWidth: '400px' }, children: [_jsx("thead", { children: _jsxs("tr", { style: { background: '#e8f5e9' }, children: [_jsx("th", { style: { padding: '0.35rem 0.5rem', textAlign: 'left' }, children: "\uC885\uBAA9" }), _jsx("th", { style: { padding: '0.35rem 0.5rem', textAlign: 'right' }, children: "DPS(\uC6D0)" }), _jsx("th", { style: { padding: '0.35rem 0.5rem', textAlign: 'right' }, children: "\uBC30\uB2F9\uC218\uC775\uB960" }), _jsx("th", { style: { padding: '0.35rem 0.5rem', textAlign: 'right' }, children: "\uC5F0\uAC04 \uC218\uC785" }), _jsx("th", { style: { padding: '0.35rem 0.5rem', textAlign: 'center' }, children: "\uC9C0\uAE09\uC6D4" })] }) }), _jsx("tbody", { children: data.holdings.map((h) => (_jsxs("tr", { style: { borderBottom: '1px solid #eee' }, children: [_jsxs("td", { style: { padding: '0.35rem 0.5rem' }, children: [_jsx("span", { style: { fontWeight: 600 }, children: h.krx_code }), h.name && _jsx("span", { style: { color: '#666', marginLeft: '0.3rem', fontSize: '0.75rem' }, children: h.name })] }), _jsx("td", { style: { padding: '0.35rem 0.5rem', textAlign: 'right' }, children: h.dps != null ? h.dps.toLocaleString() : _jsx("span", { style: { color: '#aaa' }, children: "-" }) }), _jsx("td", { style: { padding: '0.35rem 0.5rem', textAlign: 'right' }, children: h.dividend_yield != null ? `${h.dividend_yield.toFixed(2)}%` : _jsx("span", { style: { color: '#aaa' }, children: "-" }) }), _jsx("td", { style: { padding: '0.35rem 0.5rem', textAlign: 'right', color: '#2e7d32' }, children: h.annual_income > 0 ? `₩${Math.round(h.annual_income).toLocaleString()}` : _jsx("span", { style: { color: '#aaa' }, children: "-" }) }), _jsx("td", { style: { padding: '0.35rem 0.5rem', textAlign: 'center' }, children: h.ex_dividend_month != null ? `${h.ex_dividend_month}월` : _jsx("span", { style: { color: '#aaa' }, children: "-" }) })] }, h.krx_code))) })] }) })), showCalendar && (_jsxs("div", { children: [_jsx("h5", { style: { margin: '0 0 0.5rem', fontSize: '0.8rem', color: '#555' }, children: "\uBC30\uB2F9 \uCE98\uB9B0\uB354 (\uC9C0\uAE09\uC6D4 \uAE30\uC900)" }), _jsx("div", { style: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.4rem' }, children: Array.from({ length: 12 }, (_, i) => i + 1).map((month) => {
                                    const entry = data.calendar.find((c) => c.month === month);
                                    const hasDiv = entry != null && entry.holdings.length > 0;
                                    return (_jsxs("div", { style: {
                                            padding: '0.4rem',
                                            border: `1px solid ${hasDiv ? '#81c784' : '#e0e0e0'}`,
                                            borderRadius: '4px',
                                            background: hasDiv ? '#f1f8e9' : '#fafafa',
                                            fontSize: '0.75rem',
                                        }, children: [_jsx("div", { style: { fontWeight: 600, color: hasDiv ? '#2e7d32' : '#999', marginBottom: '0.2rem' }, children: MONTHS[month - 1] }), hasDiv ? (_jsxs(_Fragment, { children: [_jsx("div", { style: { color: '#555' }, children: entry.holdings.join(', ') }), _jsxs("div", { style: { color: '#2e7d32', marginTop: '0.15rem' }, children: ["\u20A9", Math.round(entry.total_income).toLocaleString()] })] })) : (_jsx("div", { style: { color: '#bbb' }, children: "-" }))] }, month));
                                }) })] }))] }))] }));
}
// AI 분석 섹션 컴포넌트 (REQ-FE-005)
function AiAnalysisSection({ portfolioId, token }) {
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);
    const [expanded, setExpanded] = useState(false);
    async function handleRunAnalysis() {
        setLoading(true);
        setError(null);
        setResult(null);
        try {
            const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/ai-analysis`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${token}` },
            });
            if (!res.ok)
                throw new Error(`AI 분석 실패: ${res.status}`);
            const data = await res.json();
            setResult(data);
            setExpanded(true);
        }
        catch {
            setError('AI 분석을 일시적으로 사용할 수 없습니다.');
        }
        finally {
            setLoading(false);
        }
    }
    const sectionStyle = {
        marginTop: '1rem',
        padding: '0.75rem',
        border: '1px solid #e3f2fd',
        borderRadius: '4px',
        background: '#fafcff',
    };
    return (_jsxs("div", { style: sectionStyle, children: [_jsxs("div", { style: { display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }, children: [_jsx("strong", { style: { fontSize: '0.875rem' }, children: "AI \uBD84\uC11D" }), _jsx("button", { onClick: () => void handleRunAnalysis(), disabled: loading, style: {
                            padding: '0.3rem 0.7rem', background: '#1976d2', color: '#fff',
                            border: 'none', borderRadius: '4px', cursor: loading ? 'default' : 'pointer',
                            fontSize: '0.8rem', opacity: loading ? 0.7 : 1,
                        }, children: loading ? '분석 중...' : 'AI 분석 실행' }), result && (_jsx("button", { onClick: () => setExpanded((v) => !v), style: { background: 'none', border: 'none', cursor: 'pointer', fontSize: '0.8rem', color: '#666' }, children: expanded ? '▲ 접기' : '▼ 펼치기' }))] }), error && (_jsx("p", { style: { color: '#c62828', fontSize: '0.8rem', margin: '0.25rem 0' }, children: error })), result && expanded && (_jsxs("div", { style: { fontSize: '0.875rem' }, children: [_jsxs("div", { style: { marginBottom: '0.5rem' }, children: [_jsx("strong", { children: "\uBD84\uC0B0\uB3C4:" }), " ", _jsx("span", { children: result.diversification })] }), _jsxs("div", { style: { marginBottom: '0.5rem' }, children: [_jsx("strong", { children: "\uB9AC\uC2A4\uD06C:" }), " ", _jsx("span", { children: result.risk })] }), result.suggestions && result.suggestions.length > 0 && (_jsxs("div", { style: { marginBottom: '0.5rem' }, children: [_jsx("strong", { children: "\uAC1C\uC120 \uC81C\uC548:" }), _jsx("ul", { style: { margin: '0.25rem 0 0 1rem', padding: 0 }, children: result.suggestions.map((s, i) => (_jsx("li", { children: s }, i))) })] })), _jsx("p", { style: { fontSize: '0.75rem', color: '#888', marginTop: '0.5rem', marginBottom: 0 }, children: "\uBCF8 \uBD84\uC11D\uC740 AI\uAC00 \uC0DD\uC131\uD55C \uCC38\uACE0 \uC815\uBCF4\uC785\uB2C8\uB2E4. \uC2E4\uC81C \uD22C\uC790 \uACB0\uC815\uC740 \uBCF8\uC778 \uCC45\uC784\uD558\uC5D0 \uC774\uB8E8\uC5B4\uC838\uC57C \uD569\uB2C8\uB2E4." })] }))] }));
}
// AI 최적화 분석 섹션 (SPEC-STOCK-026)
function OptimizeSection({ portfolioId, token }) {
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);
    async function handleOptimize(refresh = false) {
        setLoading(true);
        setError(null);
        try {
            const data = await apiOptimizePortfolio(token, portfolioId, refresh);
            setResult(data);
        }
        catch (e) {
            setError(e instanceof Error ? e.message : 'AI 최적화 분석 실패');
        }
        finally {
            setLoading(false);
        }
    }
    const sectionStyle = {
        marginTop: '1rem',
        padding: '0.75rem',
        border: '1px solid #ede9fe',
        borderRadius: '4px',
        background: '#faf5ff',
    };
    return (_jsxs("div", { style: sectionStyle, children: [_jsxs("div", { style: { display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem' }, children: [_jsx("strong", { style: { fontSize: '0.875rem' }, children: "AI \uCD5C\uC801\uD654 \uBD84\uC11D" }), _jsx("button", { onClick: () => void handleOptimize(false), disabled: loading, style: {
                            padding: '0.3rem 0.7rem', background: '#7c3aed', color: '#fff',
                            border: 'none', borderRadius: '4px', cursor: loading ? 'default' : 'pointer',
                            fontSize: '0.8rem', opacity: loading ? 0.7 : 1,
                        }, children: loading ? '분석 중...' : '최적화 분석 실행' }), result && (_jsx("button", { onClick: () => void handleOptimize(true), disabled: loading, style: {
                            padding: '0.3rem 0.7rem', background: 'none', border: '1px solid #7c3aed',
                            color: '#7c3aed', borderRadius: '4px', cursor: loading ? 'default' : 'pointer',
                            fontSize: '0.8rem', opacity: loading ? 0.7 : 1,
                        }, children: "\uC0C8\uB85C \uBD84\uC11D" }))] }), error && (_jsx("p", { style: { color: '#c62828', fontSize: '0.8rem', margin: '0.25rem 0' }, children: error })), result && (_jsxs("div", { style: { display: 'flex', flexDirection: 'column', gap: '1rem' }, children: [_jsx(PortfolioScoreCard, { score: result.score, breakdown: result.score_breakdown }), _jsxs("div", { children: [_jsx("p", { style: { margin: '0 0 8px', fontWeight: 600, fontSize: '13px', color: '#374151' }, children: "\uB9AC\uBC38\uB7F0\uC2F1 \uC81C\uC548" }), _jsx(RebalancingTable, { items: result.target_weights })] }), result.new_stocks.length > 0 && (_jsxs("div", { children: [_jsx("p", { style: { margin: '0 0 8px', fontWeight: 600, fontSize: '13px', color: '#374151' }, children: "\uC2E0\uADDC \uC885\uBAA9 \uCD94\uCC9C" }), _jsx(NewStockSuggestions, { stocks: result.new_stocks })] })), result.summary && (_jsx("p", { style: { fontSize: '0.8rem', color: '#4b5563', lineHeight: 1.6, margin: 0 }, children: result.summary }))] }))] }));
}
// AI 투자 조언 섹션 — 리밸런싱·리스크·브리핑 (SPEC-STOCK-014)
// @MX:NOTE: [AUTO] 3종 조언을 탭으로 전환하는 단일 섹션 컴포넌트
function AdviceSection({ token }) {
    const [tab, setTab] = useState('rebalance');
    const [rebalance, setRebalance] = useState(null);
    const [risk, setRisk] = useState(null);
    const [briefing, setBriefing] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    async function handleFetch() {
        setLoading(true);
        setError(null);
        try {
            if (tab === 'rebalance') {
                const data = await fetchRebalanceAdvice(token);
                setRebalance(data);
            }
            else if (tab === 'risk') {
                const data = await fetchRiskProfile(token);
                setRisk(data);
            }
            else {
                const data = await fetchMarketBriefing(token);
                setBriefing(data);
            }
        }
        catch (e) {
            setError(e instanceof Error ? e.message : 'AI 조언 요청 실패');
        }
        finally {
            setLoading(false);
        }
    }
    const tabLabel = {
        rebalance: '리밸런싱',
        risk: '리스크',
        briefing: '시장 브리핑',
    };
    const sectionStyle = {
        marginTop: '1rem',
        padding: '0.75rem',
        border: '1px solid #e8f5e9',
        borderRadius: '4px',
        background: '#f9fbe7',
    };
    const tabBtnStyle = (active) => ({
        padding: '0.3rem 0.7rem',
        border: `1px solid ${active ? '#388e3c' : '#ccc'}`,
        background: active ? '#388e3c' : '#fff',
        color: active ? '#fff' : '#333',
        borderRadius: '4px',
        cursor: 'pointer',
        fontSize: '0.8rem',
    });
    return (_jsxs("div", { style: sectionStyle, children: [_jsxs("div", { style: { display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem', flexWrap: 'wrap' }, children: [_jsx("strong", { style: { fontSize: '0.875rem' }, children: "AI \uD22C\uC790 \uC870\uC5B8" }), ['rebalance', 'risk', 'briefing'].map((t) => (_jsx("button", { style: tabBtnStyle(tab === t), onClick: () => setTab(t), children: tabLabel[t] }, t))), _jsx("button", { onClick: () => void handleFetch(), disabled: loading, style: {
                            padding: '0.3rem 0.7rem', background: '#1976d2', color: '#fff',
                            border: 'none', borderRadius: '4px', cursor: loading ? 'default' : 'pointer',
                            fontSize: '0.8rem', opacity: loading ? 0.7 : 1, marginLeft: 'auto',
                        }, children: loading ? '요청 중...' : '조언 받기' })] }), error && (_jsx("p", { style: { color: '#c62828', fontSize: '0.8rem', margin: '0 0 0.5rem' }, children: error })), tab === 'rebalance' && rebalance && (_jsxs("div", { style: { fontSize: '0.875rem' }, children: [rebalance.message && _jsx("p", { style: { color: '#666' }, children: rebalance.message }), rebalance.error && _jsx("p", { style: { color: '#c62828' }, children: rebalance.error }), rebalance.actions && rebalance.actions.length > 0 && (_jsx("ul", { style: { margin: '0 0 0.5rem 1rem', padding: 0 }, children: rebalance.actions.map((action, i) => (_jsxs("li", { style: { marginBottom: '0.3rem' }, children: [_jsx("strong", { children: action.krx_code }), ' — ', _jsx("span", { style: {
                                        color: action.action === 'buy_more' ? '#388e3c'
                                            : action.action === 'reduce' ? '#c62828' : '#666'
                                    }, children: action.action === 'buy_more' ? '매수 추가' : action.action === 'reduce' ? '비중 축소' : '유지' }), ': ', action.reason] }, i))) })), rebalance.disclaimer && (_jsx("p", { style: { fontSize: '0.75rem', color: '#888', margin: 0 }, children: rebalance.disclaimer }))] })), tab === 'risk' && risk && (_jsxs("div", { style: { fontSize: '0.875rem' }, children: [risk.message && _jsx("p", { style: { color: '#666' }, children: risk.message }), risk.error && _jsx("p", { style: { color: '#c62828' }, children: risk.error }), risk.risk_score !== undefined && risk.risk_score !== null && (_jsxs("div", { style: { marginBottom: '0.5rem' }, children: [_jsx("strong", { children: "\uB9AC\uC2A4\uD06C \uC810\uC218: " }), _jsxs("span", { style: {
                                    fontWeight: 'bold',
                                    color: risk.risk_score >= 70 ? '#c62828' : risk.risk_score >= 40 ? '#f57c00' : '#388e3c',
                                }, children: [risk.risk_score, "/100"] })] })), risk.explanation && (_jsx("p", { style: { margin: '0 0 0.5rem', lineHeight: 1.5 }, children: risk.explanation })), risk.disclaimer && (_jsx("p", { style: { fontSize: '0.75rem', color: '#888', margin: 0 }, children: risk.disclaimer }))] })), tab === 'briefing' && briefing && (_jsxs("div", { style: { fontSize: '0.875rem' }, children: [briefing.message && _jsx("p", { style: { color: '#666' }, children: briefing.message }), briefing.error && _jsx("p", { style: { color: '#c62828' }, children: briefing.error }), briefing.briefing && (_jsx("p", { style: { margin: '0 0 0.5rem', lineHeight: 1.5, whiteSpace: 'pre-line' }, children: briefing.briefing })), briefing.disclaimer && (_jsx("p", { style: { fontSize: '0.75rem', color: '#888', margin: 0 }, children: briefing.disclaimer }))] }))] }));
}
// 포트폴리오 상세 패널 (보유 종목 + 성과)
function PortfolioDetail({ portfolioId, token }) {
    const [holdings, setHoldings] = useState([]);
    const [performance, setPerformance] = useState(null);
    const [loadErr, setLoadErr] = useState(null);
    // 종목 추가 폼 상태 (SPEC-STOCK-028: market/currency 추가)
    const [krxCode, setKrxCode] = useState('');
    const [quantity, setQuantity] = useState('');
    const [avgBuyPrice, setAvgBuyPrice] = useState('');
    const [market, setMarket] = useState('KRX');
    const [addErr, setAddErr] = useState(null);
    const [addLoading, setAddLoading] = useState(false);
    // market 변경 시 currency 자동 설정
    const currency = market === 'KRX' ? 'KRW' : 'USD';
    async function load() {
        try {
            const [h, p] = await Promise.all([
                apiListHoldings(token, portfolioId),
                apiGetPerformance(token, portfolioId),
            ]);
            setHoldings(h);
            setPerformance(p);
        }
        catch (err) {
            setLoadErr(err instanceof Error ? err.message : '조회 실패');
        }
    }
    useEffect(() => { void load(); }, [portfolioId, token]);
    async function handleAddHolding(e) {
        e.preventDefault();
        setAddErr(null);
        setAddLoading(true);
        try {
            await apiAddHolding(token, portfolioId, krxCode, Number(quantity), Number(avgBuyPrice), market, currency);
            setKrxCode('');
            setQuantity('');
            setAvgBuyPrice('');
            setMarket('KRX');
            await load();
        }
        catch (err) {
            setAddErr(err instanceof Error ? err.message : '추가 실패');
        }
        finally {
            setAddLoading(false);
        }
    }
    const cellStyle = { padding: '0.4rem 0.6rem', fontSize: '0.875rem' };
    if (loadErr)
        return _jsxs("p", { style: { color: '#c62828', fontSize: '0.875rem' }, children: ["\uC624\uB958: ", loadErr] });
    return (_jsxs("div", { style: { padding: '1rem', background: '#f8f9fa', borderRadius: '4px', marginTop: '0.5rem' }, children: [performance && (_jsxs("div", { className: "portfolio-summary-cards", style: { display: 'flex', gap: '1.5rem', marginBottom: '1rem', flexWrap: 'wrap' }, children: [_jsxs("div", { style: { minWidth: '80px' }, children: [_jsx("span", { style: { fontSize: '0.75rem', color: '#666' }, children: "\uCD1D \uD22C\uC790\uAE08" }), _jsx("br", {}), _jsxs("strong", { children: ["\u20A9", performance.total_invested.toLocaleString()] })] }), _jsxs("div", { style: { minWidth: '80px' }, children: [_jsx("span", { style: { fontSize: '0.75rem', color: '#666' }, children: "\uD604\uC7AC \uD3C9\uAC00\uAE08" }), _jsx("br", {}), _jsxs("strong", { children: ["\u20A9", performance.total_current.toLocaleString()] })] }), _jsxs("div", { style: { minWidth: '80px' }, children: [_jsx("span", { style: { fontSize: '0.75rem', color: '#666' }, children: "\uC218\uC775\uB960" }), _jsx("br", {}), _jsx("strong", { style: { color: returnColor(performance.total_return_pct) }, children: formatPct(performance.total_return_pct) })] }), _jsxs("div", { style: { minWidth: '80px' }, children: [_jsx("span", { style: { fontSize: '0.75rem', color: '#666' }, children: "\uC885\uBAA9 \uC218" }), _jsx("br", {}), _jsx("strong", { children: performance.holdings.length })] }), _jsx("style", { children: `
            @media (max-width: 767px) {
              .portfolio-summary-cards { flex-direction: column !important; gap: 0.75rem !important; }
            }
          ` })] })), performance && performance.holdings.length > 0 && (_jsxs("div", { style: { display: 'flex', gap: '1rem', marginBottom: '1rem', flexWrap: 'wrap' }, children: [_jsx("div", { style: { minWidth: '200px' }, children: _jsx(PerformanceDonutChart, { summary: performance.classification_summary }) }), _jsxs("div", { style: { flex: '1', minWidth: '180px' }, children: [_jsx("h5", { style: { margin: '0 0 0.5rem', fontSize: '0.8rem', color: '#555' }, children: "\uC131\uACFC \uBD84\uB958" }), _jsx("div", { style: { display: 'flex', flexDirection: 'column', gap: '0.25rem' }, children: ['high', 'normal', 'low'].map((cls) => {
                                    const clsLabels = { high: '고수익 (≥+5%)', normal: '보통 (-5%~+5%)', low: '저수익 (≤-5%)' };
                                    const clsColors = { high: '#2e7d32', normal: '#1565c0', low: '#c62828' };
                                    const group = performance.classification_summary[cls];
                                    return (_jsxs("div", { style: { display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem' }, children: [_jsx("span", { style: { width: '10px', height: '10px', borderRadius: '50%', background: clsColors[cls], flexShrink: 0 } }), _jsx("span", { style: { color: '#555' }, children: clsLabels[cls] }), _jsxs("span", { style: { marginLeft: 'auto', fontWeight: 600 }, children: [group.count, "\uC885\uBAA9"] }), _jsxs("span", { style: { color: '#888' }, children: ["(", group.invested_pct.toFixed(1), "%)"] })] }, cls));
                                }) })] }), _jsxs("div", { style: { flex: '1', minWidth: '200px' }, children: [_jsx("h5", { style: { margin: '0 0 0.5rem', fontSize: '0.8rem', color: '#555' }, children: "\uC139\uD130\uBCC4 \uC131\uACFC" }), _jsx("div", { style: { display: 'flex', flexDirection: 'column', gap: '0.25rem' }, children: performance.sector_performance.map((sp) => (_jsxs("div", { style: { display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', borderBottom: '1px solid #eee', paddingBottom: '0.15rem' }, children: [_jsx("span", { style: { color: '#555' }, children: sp.sector }), _jsxs("span", { children: [_jsxs("span", { style: { color: '#888', marginRight: '0.5rem' }, children: [sp.holding_count, "\uC885\uBAA9"] }), _jsxs("span", { style: { fontWeight: 600, color: sp.return_pct >= 0 ? '#2e7d32' : '#c62828' }, children: [sp.return_pct >= 0 ? '+' : '', sp.return_pct.toFixed(2), "%"] })] })] }, sp.sector))) })] })] })), holdings.length > 0 ? (_jsx("div", { style: { overflowX: 'auto', marginBottom: '1rem', WebkitOverflowScrolling: 'touch' }, children: _jsxs("table", { style: { width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem', minWidth: '360px' }, children: [_jsx("thead", { children: _jsxs("tr", { style: { background: '#e3f2fd' }, children: [_jsx("th", { style: cellStyle, children: "\uC885\uBAA9\uCF54\uB4DC" }), _jsx("th", { style: cellStyle, children: "\uC218\uB7C9" }), _jsx("th", { style: cellStyle, children: "\uD3C9\uADE0\uB2E8\uAC00" }), _jsx("th", { style: cellStyle, children: "\uD604\uC7AC \uC2DC\uC138" })] }) }), _jsx("tbody", { children: holdings.map((h) => (_jsxs("tr", { style: { borderBottom: '1px solid #eee' }, children: [_jsxs("td", { style: cellStyle, children: [h.krx_code, h.market && h.market !== 'KRX' && (_jsx("span", { style: {
                                                    marginLeft: '0.3rem',
                                                    padding: '0.1rem 0.3rem',
                                                    background: '#e3f2fd',
                                                    borderRadius: '3px',
                                                    fontSize: '0.7rem',
                                                    color: '#1565c0',
                                                    fontWeight: 600,
                                                }, children: h.market }))] }), _jsx("td", { style: cellStyle, children: h.quantity.toLocaleString() }), _jsxs("td", { style: cellStyle, children: [h.currency === 'USD' ? '$' : '₩', h.avg_buy_price.toLocaleString()] }), _jsx("td", { style: cellStyle, children: _jsx(LivePriceBadge, { krxCode: h.krx_code }) })] }, h.id))) })] }) })) : (_jsx("p", { style: { fontSize: '0.875rem', color: '#666', marginBottom: '1rem' }, children: "\uBCF4\uC720 \uC885\uBAA9\uC774 \uC5C6\uC2B5\uB2C8\uB2E4." })), _jsxs("div", { children: [_jsx("h4", { style: { margin: '0 0 0.5rem', fontSize: '0.875rem' }, children: "\uC885\uBAA9 \uCD94\uAC00" }), addErr && _jsx("p", { style: { color: '#c62828', fontSize: '0.8rem', margin: '0 0 0.5rem' }, children: addErr }), _jsxs("form", { onSubmit: (e) => void handleAddHolding(e), style: { display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }, children: [_jsxs("select", { value: market, onChange: (e) => setMarket(e.target.value), style: { flex: '0 0 100px', padding: '0.35rem 0.5rem', border: '1px solid #ccc', borderRadius: '4px', fontSize: '0.875rem' }, children: [_jsx("option", { value: "KRX", children: "KRX (\uAD6D\uB0B4)" }), _jsx("option", { value: "NYSE", children: "NYSE (\uBBF8\uAD6D)" }), _jsx("option", { value: "NASDAQ", children: "NASDAQ (\uBBF8\uAD6D)" })] }), _jsx("input", { placeholder: market === 'KRX' ? '종목코드 (예: 005930)' : '티커 (예: AAPL)', value: krxCode, onChange: (e) => setKrxCode(e.target.value), required: true, style: { flex: '1 1 100px', padding: '0.35rem 0.5rem', border: '1px solid #ccc', borderRadius: '4px', fontSize: '0.875rem' } }), _jsx("input", { placeholder: "\uC218\uB7C9", type: "number", min: "1", value: quantity, onChange: (e) => setQuantity(e.target.value), required: true, style: { flex: '1 1 80px', padding: '0.35rem 0.5rem', border: '1px solid #ccc', borderRadius: '4px', fontSize: '0.875rem' } }), _jsx("input", { placeholder: currency === 'USD' ? '평균단가 (USD)' : '평균단가 (원)', type: "number", min: "1", value: avgBuyPrice, onChange: (e) => setAvgBuyPrice(e.target.value), required: true, style: { flex: '1 1 100px', padding: '0.35rem 0.5rem', border: '1px solid #ccc', borderRadius: '4px', fontSize: '0.875rem' } }), _jsx("button", { type: "submit", disabled: addLoading, style: { padding: '0.35rem 0.75rem', background: '#388e3c', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '0.875rem' }, children: addLoading ? '추가 중...' : '추가' })] })] }), _jsx(DividendsSection, { portfolioId: portfolioId, token: token }), _jsx(AiAnalysisSection, { portfolioId: portfolioId, token: token }), _jsx(OptimizeSection, { portfolioId: portfolioId, token: token }), _jsx(RiskAnalysisPanel, { portfolioId: portfolioId }), _jsx(BacktestPanel, { token: token, portfolioId: portfolioId }), _jsx(PortfolioAlertPanel, { portfolioId: portfolioId }), _jsx(DividendSummaryPanel, { token: token, portfolioId: portfolioId }), _jsx(DividendCalendarView, { token: token, portfolioId: portfolioId }), _jsx(DRIPSimulator, { token: token, portfolioId: portfolioId }), _jsx(BenchmarkComparisonPanel, { token: token, portfolioId: portfolioId }), _jsx(BenchmarkChartView, { token: token, portfolioId: portfolioId }), _jsx(AICommentaryPanel, { portfolioId: portfolioId }), _jsx(AdviceSection, { token: token })] }));
}
export default function Portfolio() {
    const { token } = useAuth();
    const [portfolios, setPortfolios] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showModal, setShowModal] = useState(false);
    const [expandedId, setExpandedId] = useState(null);
    async function loadPortfolios() {
        if (!token)
            return;
        try {
            const list = await apiListPortfolios(token);
            setPortfolios(list);
        }
        catch (err) {
            setError(err instanceof Error ? err.message : '조회 실패');
        }
        finally {
            setLoading(false);
        }
    }
    useEffect(() => { void loadPortfolios(); }, [token]);
    async function handleCreate(name, description) {
        if (!token)
            return;
        await apiCreatePortfolio(token, name, description);
        await loadPortfolios();
        setShowModal(false);
    }
    if (!token)
        return _jsx("p", { children: "\uB85C\uADF8\uC778\uC774 \uD544\uC694\uD569\uB2C8\uB2E4." });
    return (_jsxs("div", { children: [_jsxs("div", { style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }, children: [_jsx("h2", { style: { margin: 0, color: '#0d47a1' }, children: "\uB0B4 \uD3EC\uD2B8\uD3F4\uB9AC\uC624" }), _jsx("button", { onClick: () => setShowModal(true), style: { padding: '0.4rem 0.9rem', background: '#1976d2', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }, children: "+ \uC0C8 \uD3EC\uD2B8\uD3F4\uB9AC\uC624" })] }), loading && _jsx("p", { style: { color: '#666' }, children: "\uBD88\uB7EC\uC624\uB294 \uC911..." }), error && _jsxs("p", { style: { color: '#c62828' }, children: ["\uC624\uB958: ", error] }), !loading && portfolios.length === 0 && (_jsx("p", { style: { color: '#666' }, children: "\uC544\uC9C1 \uD3EC\uD2B8\uD3F4\uB9AC\uC624\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4. \uC0C8 \uD3EC\uD2B8\uD3F4\uB9AC\uC624\uB97C \uB9CC\uB4E4\uC5B4 \uBCF4\uC138\uC694." })), portfolios.map((p) => (_jsxs("div", { style: { border: '1px solid #ddd', borderRadius: '6px', marginBottom: '1rem', overflow: 'hidden' }, children: [_jsxs("div", { style: {
                            padding: '0.75rem 1rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                            cursor: 'pointer', background: expandedId === p.id ? '#e3f2fd' : '#fff',
                        }, onClick: () => setExpandedId(expandedId === p.id ? null : p.id), role: "button", "aria-expanded": expandedId === p.id, children: [_jsxs("div", { children: [_jsx("strong", { children: p.name }), p.description && _jsx("span", { style: { marginLeft: '0.5rem', fontSize: '0.875rem', color: '#666' }, children: p.description })] }), _jsx("span", { style: { fontSize: '0.8rem', color: '#666' }, children: expandedId === p.id ? '▲' : '▼' })] }), expandedId === p.id && _jsx(PortfolioDetail, { portfolioId: p.id, token: token })] }, p.id))), showModal && (_jsx(CreatePortfolioModal, { onClose: () => setShowModal(false), onCreate: handleCreate }))] }));
}
