import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// 포트폴리오 관리 페이지
import { useEffect, useState } from 'react';
import { useAuth } from '../auth/AuthContext';
import { apiListPortfolios, apiCreatePortfolio, apiListHoldings, apiAddHolding, apiGetPerformance, } from '../api/portfolio';
import { LivePriceBadge } from '../components/LivePriceBadge';
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
// 포트폴리오 상세 패널 (보유 종목 + 성과)
function PortfolioDetail({ portfolioId, token }) {
    const [holdings, setHoldings] = useState([]);
    const [performance, setPerformance] = useState(null);
    const [loadErr, setLoadErr] = useState(null);
    // 종목 추가 폼 상태
    const [krxCode, setKrxCode] = useState('');
    const [quantity, setQuantity] = useState('');
    const [avgBuyPrice, setAvgBuyPrice] = useState('');
    const [addErr, setAddErr] = useState(null);
    const [addLoading, setAddLoading] = useState(false);
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
            await apiAddHolding(token, portfolioId, krxCode, Number(quantity), Number(avgBuyPrice));
            setKrxCode('');
            setQuantity('');
            setAvgBuyPrice('');
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
    return (_jsxs("div", { style: { padding: '1rem', background: '#f8f9fa', borderRadius: '4px', marginTop: '0.5rem' }, children: [performance && (_jsxs("div", { style: { display: 'flex', gap: '1.5rem', marginBottom: '1rem', flexWrap: 'wrap' }, children: [_jsxs("div", { children: [_jsx("span", { style: { fontSize: '0.75rem', color: '#666' }, children: "\uCD1D \uD22C\uC790\uAE08" }), _jsx("br", {}), _jsxs("strong", { children: ["\u20A9", performance.total_invested.toLocaleString()] })] }), _jsxs("div", { children: [_jsx("span", { style: { fontSize: '0.75rem', color: '#666' }, children: "\uD604\uC7AC \uD3C9\uAC00\uAE08" }), _jsx("br", {}), _jsx("strong", { children: performance.current_value !== null ? `₩${performance.current_value.toLocaleString()}` : '-' })] }), _jsxs("div", { children: [_jsx("span", { style: { fontSize: '0.75rem', color: '#666' }, children: "\uC218\uC775\uB960" }), _jsx("br", {}), _jsx("strong", { style: { color: returnColor(performance.total_return_pct) }, children: formatPct(performance.total_return_pct) })] }), _jsxs("div", { children: [_jsx("span", { style: { fontSize: '0.75rem', color: '#666' }, children: "\uC885\uBAA9 \uC218" }), _jsx("br", {}), _jsx("strong", { children: performance.holdings_count })] })] })), holdings.length > 0 ? (_jsxs("table", { style: { width: '100%', borderCollapse: 'collapse', marginBottom: '1rem', fontSize: '0.875rem' }, children: [_jsx("thead", { children: _jsxs("tr", { style: { background: '#e3f2fd' }, children: [_jsx("th", { style: cellStyle, children: "\uC885\uBAA9\uCF54\uB4DC" }), _jsx("th", { style: cellStyle, children: "\uC218\uB7C9" }), _jsx("th", { style: cellStyle, children: "\uD3C9\uADE0\uB2E8\uAC00" }), _jsx("th", { style: cellStyle, children: "\uD604\uC7AC \uC2DC\uC138" })] }) }), _jsx("tbody", { children: holdings.map((h) => (_jsxs("tr", { style: { borderBottom: '1px solid #eee' }, children: [_jsx("td", { style: cellStyle, children: h.krx_code }), _jsx("td", { style: cellStyle, children: h.quantity.toLocaleString() }), _jsxs("td", { style: cellStyle, children: ["\u20A9", h.avg_buy_price.toLocaleString()] }), _jsx("td", { style: cellStyle, children: _jsx(LivePriceBadge, { krxCode: h.krx_code }) })] }, h.id))) })] })) : (_jsx("p", { style: { fontSize: '0.875rem', color: '#666', marginBottom: '1rem' }, children: "\uBCF4\uC720 \uC885\uBAA9\uC774 \uC5C6\uC2B5\uB2C8\uB2E4." })), _jsxs("div", { children: [_jsx("h4", { style: { margin: '0 0 0.5rem', fontSize: '0.875rem' }, children: "\uC885\uBAA9 \uCD94\uAC00" }), addErr && _jsx("p", { style: { color: '#c62828', fontSize: '0.8rem', margin: '0 0 0.5rem' }, children: addErr }), _jsxs("form", { onSubmit: (e) => void handleAddHolding(e), style: { display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }, children: [_jsx("input", { placeholder: "KRX \uCF54\uB4DC (\uC608: 005930)", value: krxCode, onChange: (e) => setKrxCode(e.target.value), required: true, style: { flex: '1 1 100px', padding: '0.35rem 0.5rem', border: '1px solid #ccc', borderRadius: '4px', fontSize: '0.875rem' } }), _jsx("input", { placeholder: "\uC218\uB7C9", type: "number", min: "1", value: quantity, onChange: (e) => setQuantity(e.target.value), required: true, style: { flex: '1 1 80px', padding: '0.35rem 0.5rem', border: '1px solid #ccc', borderRadius: '4px', fontSize: '0.875rem' } }), _jsx("input", { placeholder: "\uD3C9\uADE0\uB2E8\uAC00 (\uC6D0)", type: "number", min: "1", value: avgBuyPrice, onChange: (e) => setAvgBuyPrice(e.target.value), required: true, style: { flex: '1 1 100px', padding: '0.35rem 0.5rem', border: '1px solid #ccc', borderRadius: '4px', fontSize: '0.875rem' } }), _jsx("button", { type: "submit", disabled: addLoading, style: { padding: '0.35rem 0.75rem', background: '#388e3c', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '0.875rem' }, children: addLoading ? '추가 중...' : '추가' })] })] }), _jsx(AiAnalysisSection, { portfolioId: portfolioId, token: token })] }));
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
