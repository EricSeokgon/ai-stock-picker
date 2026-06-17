import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// 종목 스크리너 페이지 (SPEC-STOCK-018)
// - PER/PBR/ROE/시가총액/배당수익률/52주 위치 필터
// - 프리셋 저장/불러오기 (최대 5개, 로그인 필요)
// - 필터 없이 전체 종목 조회 가능
import { useEffect, useState } from 'react';
import { useAuth } from '../auth/AuthContext';
import { runScreener, listPresets, createPreset, deletePreset, } from '../api/screener';
function FilterInput({ label, value, onChange, step = 0.1 }) {
    return (_jsxs("div", { style: { marginBottom: '12px' }, children: [_jsx("label", { style: { display: 'block', marginBottom: '4px', fontWeight: 500 }, children: label }), _jsxs("div", { style: { display: 'flex', gap: '8px' }, children: [_jsx("input", { type: "number", placeholder: "\uCD5C\uC19F\uAC12", step: step, value: value.min ?? '', onChange: (e) => onChange({ ...value, min: e.target.value === '' ? null : Number(e.target.value) }), style: { width: '100px', padding: '4px 8px', border: '1px solid #ddd', borderRadius: '4px' }, "data-testid": `filter-${label}-min` }), _jsx("span", { style: { alignSelf: 'center' }, children: "~" }), _jsx("input", { type: "number", placeholder: "\uCD5C\uB313\uAC12", step: step, value: value.max ?? '', onChange: (e) => onChange({ ...value, max: e.target.value === '' ? null : Number(e.target.value) }), style: { width: '100px', padding: '4px 8px', border: '1px solid #ddd', borderRadius: '4px' }, "data-testid": `filter-${label}-max` })] })] }));
}
// ── 기본 필터 상태 ────────────────────────────────────────────────────────────
const emptyRange = () => ({ min: null, max: null });
function emptyFilters() {
    return {
        per: emptyRange(),
        pbr: emptyRange(),
        roe: emptyRange(),
        market_cap: emptyRange(),
        dividend_yield: emptyRange(),
        week52_position: emptyRange(),
    };
}
function filterStateToApi(state) {
    const toRange = (r) => r.min == null && r.max == null ? undefined : r;
    return {
        per: toRange(state.per),
        pbr: toRange(state.pbr),
        roe: toRange(state.roe),
        market_cap: toRange(state.market_cap),
        dividend_yield: toRange(state.dividend_yield),
        week52_position: toRange(state.week52_position),
    };
}
// ── 유틸: 시가총액 포매팅 ────────────────────────────────────────────────────
function fmtMarketCap(v) {
    if (v == null)
        return '-';
    if (v >= 1000000000000)
        return `${(v / 1000000000000).toFixed(1)}조`;
    if (v >= 100000000)
        return `${(v / 100000000).toFixed(0)}억`;
    return `${v.toLocaleString()}원`;
}
function fmtNum(v, digits = 1) {
    return v == null ? '-' : v.toFixed(digits);
}
// ── 메인 컴포넌트 ─────────────────────────────────────────────────────────────
export default function Screener() {
    const { isAuthenticated, token } = useAuth();
    const [filters, setFilters] = useState(emptyFilters());
    const [results, setResults] = useState([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    // 프리셋
    const [presets, setPresets] = useState([]);
    const [presetName, setPresetName] = useState('');
    const [presetLoading, setPresetLoading] = useState(false);
    const [presetError, setPresetError] = useState(null);
    // 정렬
    const [sortBy, setSortBy] = useState('per');
    const [sortOrder, setSortOrder] = useState('asc');
    // 마운트 시 프리셋 로드 (인증 시)
    useEffect(() => {
        if (isAuthenticated && token) {
            void loadPresets();
        }
    }, [isAuthenticated, token]);
    async function loadPresets() {
        if (!token)
            return;
        try {
            const list = await listPresets(token);
            setPresets(list);
        }
        catch (_e) {
            // 프리셋 로드 실패는 무음 처리
        }
    }
    // 스크리너 실행
    async function handleRun() {
        setLoading(true);
        setError(null);
        try {
            const criteria = filterStateToApi(filters);
            const resp = await runScreener({ filters: criteria, sort_by: sortBy, sort_order: sortOrder, limit: 200 });
            setResults(resp.results);
            setTotal(resp.total);
        }
        catch (e) {
            setError(e instanceof Error ? e.message : '스크리너 실행 오류');
        }
        finally {
            setLoading(false);
        }
    }
    // 필터 초기화
    function handleReset() {
        setFilters(emptyFilters());
    }
    // 프리셋 저장
    async function handleSavePreset() {
        if (!token || !presetName.trim())
            return;
        setPresetLoading(true);
        setPresetError(null);
        try {
            await createPreset(token, { name: presetName.trim(), criteria: filterStateToApi(filters) });
            setPresetName('');
            await loadPresets();
        }
        catch (e) {
            setPresetError(e instanceof Error ? e.message : '프리셋 저장 오류');
        }
        finally {
            setPresetLoading(false);
        }
    }
    // 프리셋 불러오기
    function handleLoadPreset(preset) {
        const c = preset.criteria;
        setFilters({
            per: c.per ?? emptyRange(),
            pbr: c.pbr ?? emptyRange(),
            roe: c.roe ?? emptyRange(),
            market_cap: c.market_cap ?? emptyRange(),
            dividend_yield: c.dividend_yield ?? emptyRange(),
            week52_position: c.week52_position ?? emptyRange(),
        });
    }
    // 프리셋 삭제
    async function handleDeletePreset(presetId) {
        if (!token)
            return;
        try {
            await deletePreset(token, presetId);
            await loadPresets();
        }
        catch (e) {
            setPresetError(e instanceof Error ? e.message : '프리셋 삭제 오류');
        }
    }
    // 정렬 토글
    function handleSort(col) {
        if (sortBy === col) {
            setSortOrder((o) => (o === 'asc' ? 'desc' : 'asc'));
        }
        else {
            setSortBy(col);
            setSortOrder('asc');
        }
    }
    const sortedResults = [...results].sort((a, b) => {
        const av = a[sortBy];
        const bv = b[sortBy];
        if (av == null && bv == null)
            return 0;
        if (av == null)
            return 1;
        if (bv == null)
            return -1;
        return sortOrder === 'asc' ? av - bv : bv - av;
    });
    const SortHeader = ({ col, label }) => (_jsxs("th", { onClick: () => handleSort(col), style: { cursor: 'pointer', padding: '8px', borderBottom: '2px solid #ddd', whiteSpace: 'nowrap' }, children: [label, sortBy === col ? (sortOrder === 'asc' ? ' ▲' : ' ▼') : ''] }));
    return (_jsxs("div", { style: { maxWidth: '1200px', margin: '0 auto', padding: '24px 16px' }, "data-testid": "screener-page", children: [_jsx("h1", { style: { fontSize: '1.5rem', fontWeight: 700, marginBottom: '20px' }, children: "\uC885\uBAA9 \uC2A4\uD06C\uB9AC\uB108" }), _jsxs("div", { style: { display: 'flex', gap: '24px', flexWrap: 'wrap' }, children: [_jsxs("div", { style: { minWidth: '260px', background: '#f9f9f9', padding: '16px', borderRadius: '8px', border: '1px solid #e0e0e0' }, children: [_jsx("h2", { style: { fontSize: '1rem', fontWeight: 600, marginBottom: '16px' }, children: "\uD544\uD130 \uC870\uAC74" }), _jsx(FilterInput, { label: "PER", value: filters.per, onChange: (v) => setFilters({ ...filters, per: v }) }), _jsx(FilterInput, { label: "PBR", value: filters.pbr, onChange: (v) => setFilters({ ...filters, pbr: v }) }), _jsx(FilterInput, { label: "ROE (%)", value: filters.roe, onChange: (v) => setFilters({ ...filters, roe: v }) }), _jsx(FilterInput, { label: "\uC2DC\uAC00\uCD1D\uC561 (\uC5B5\uC6D0 \uB2E8\uC704)", value: {
                                    min: filters.market_cap.min != null ? filters.market_cap.min / 1e8 : null,
                                    max: filters.market_cap.max != null ? filters.market_cap.max / 1e8 : null,
                                }, onChange: (v) => setFilters({
                                    ...filters,
                                    market_cap: {
                                        min: v.min != null ? v.min * 1e8 : null,
                                        max: v.max != null ? v.max * 1e8 : null,
                                    },
                                }), step: 100 }), _jsx(FilterInput, { label: "\uBC30\uB2F9\uC218\uC775\uB960 (%)", value: filters.dividend_yield, onChange: (v) => setFilters({ ...filters, dividend_yield: v }) }), _jsx(FilterInput, { label: "52\uC8FC \uC704\uCE58 (%)", value: filters.week52_position, onChange: (v) => setFilters({ ...filters, week52_position: v }), step: 1 }), _jsxs("div", { style: { display: 'flex', gap: '8px', marginTop: '16px' }, children: [_jsx("button", { onClick: () => void handleRun(), disabled: loading, style: { flex: 1, padding: '8px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer' }, "data-testid": "run-screener-btn", children: loading ? '조회 중...' : '스크리너 실행' }), _jsx("button", { onClick: handleReset, style: { padding: '8px 12px', background: '#f3f4f6', border: '1px solid #ddd', borderRadius: '6px', cursor: 'pointer' }, children: "\uCD08\uAE30\uD654" })] }), error && (_jsx("p", { style: { color: '#dc2626', marginTop: '8px', fontSize: '0.875rem' }, "data-testid": "screener-error", children: error })), isAuthenticated && (_jsxs("div", { style: { marginTop: '20px', borderTop: '1px solid #e0e0e0', paddingTop: '16px' }, children: [_jsx("h3", { style: { fontSize: '0.875rem', fontWeight: 600, marginBottom: '8px' }, children: "\uD504\uB9AC\uC14B \uC800\uC7A5" }), _jsxs("div", { style: { display: 'flex', gap: '4px' }, children: [_jsx("input", { type: "text", value: presetName, onChange: (e) => setPresetName(e.target.value), placeholder: "\uD504\uB9AC\uC14B \uC774\uB984", maxLength: 100, style: { flex: 1, padding: '4px 8px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '0.875rem' }, "data-testid": "preset-name-input" }), _jsx("button", { onClick: () => void handleSavePreset(), disabled: presetLoading || !presetName.trim(), style: { padding: '4px 8px', background: '#16a34a', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '0.875rem' }, "data-testid": "save-preset-btn", children: "\uC800\uC7A5" })] }), presetError && (_jsx("p", { style: { color: '#dc2626', marginTop: '4px', fontSize: '0.75rem' }, children: presetError })), presets.length > 0 && (_jsxs("div", { style: { marginTop: '12px' }, children: [_jsx("h3", { style: { fontSize: '0.875rem', fontWeight: 600, marginBottom: '8px' }, children: "\uC800\uC7A5\uB41C \uD504\uB9AC\uC14B" }), presets.map((p) => (_jsxs("div", { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0', borderBottom: '1px solid #f0f0f0' }, children: [_jsx("button", { onClick: () => handleLoadPreset(p), style: { background: 'none', border: 'none', cursor: 'pointer', color: '#2563eb', fontSize: '0.875rem', padding: 0 }, "data-testid": `load-preset-${p.id}`, children: p.name }), _jsx("button", { onClick: () => void handleDeletePreset(p.id), style: { background: 'none', border: 'none', cursor: 'pointer', color: '#dc2626', fontSize: '0.75rem' }, "aria-label": `프리셋 ${p.name} 삭제`, children: "\uC0AD\uC81C" })] }, p.id)))] }))] }))] }), _jsxs("div", { style: { flex: 1, minWidth: 0 }, children: [_jsx("div", { style: { marginBottom: '8px', color: '#6b7280', fontSize: '0.875rem' }, "data-testid": "result-count", children: total > 0 ? `총 ${total}개 종목` : results.length === 0 && !loading ? '조건을 설정하고 스크리너를 실행하세요.' : '' }), sortedResults.length > 0 && (_jsx("div", { style: { overflowX: 'auto' }, children: _jsxs("table", { style: { width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }, "data-testid": "screener-table", children: [_jsx("thead", { style: { background: '#f3f4f6' }, children: _jsxs("tr", { children: [_jsx("th", { style: { padding: '8px', borderBottom: '2px solid #ddd', textAlign: 'left' }, children: "\uC885\uBAA9\uCF54\uB4DC" }), _jsx("th", { style: { padding: '8px', borderBottom: '2px solid #ddd', textAlign: 'left' }, children: "\uC885\uBAA9\uBA85" }), _jsx("th", { style: { padding: '8px', borderBottom: '2px solid #ddd', textAlign: 'left' }, children: "\uC139\uD130" }), _jsx(SortHeader, { col: "current_price", label: "\uD604\uC7AC\uAC00" }), _jsx(SortHeader, { col: "per", label: "PER" }), _jsx(SortHeader, { col: "pbr", label: "PBR" }), _jsx(SortHeader, { col: "roe", label: "ROE(%)" }), _jsx(SortHeader, { col: "market_cap", label: "\uC2DC\uAC00\uCD1D\uC561" }), _jsx(SortHeader, { col: "dividend_yield", label: "\uBC30\uB2F9(%)" }), _jsx(SortHeader, { col: "week52_position", label: "52\uC8FC(%)" })] }) }), _jsx("tbody", { children: sortedResults.map((r) => (_jsxs("tr", { style: { borderBottom: '1px solid #f0f0f0' }, "data-testid": `row-${r.krx_code}`, children: [_jsx("td", { style: { padding: '8px' }, children: r.krx_code }), _jsxs("td", { style: { padding: '8px' }, children: [r.name ?? '-', r.in_watchlist && _jsx("span", { title: "\uAD00\uC2EC \uBAA9\uB85D", style: { marginLeft: '4px', color: '#f59e0b' }, children: "\u2605" }), r.in_recommendations && _jsx("span", { title: "\uCD94\uCC9C \uC885\uBAA9", style: { marginLeft: '4px', color: '#10b981' }, children: "R" })] }), _jsx("td", { style: { padding: '8px', color: '#6b7280' }, children: r.sector ?? '-' }), _jsx("td", { style: { padding: '8px', textAlign: 'right' }, children: r.current_price != null ? `${r.current_price.toLocaleString()}원` : '-' }), _jsx("td", { style: { padding: '8px', textAlign: 'right' }, children: fmtNum(r.per) }), _jsx("td", { style: { padding: '8px', textAlign: 'right' }, children: fmtNum(r.pbr, 2) }), _jsx("td", { style: { padding: '8px', textAlign: 'right' }, children: fmtNum(r.roe) }), _jsx("td", { style: { padding: '8px', textAlign: 'right' }, children: fmtMarketCap(r.market_cap) }), _jsx("td", { style: { padding: '8px', textAlign: 'right' }, children: fmtNum(r.dividend_yield) }), _jsx("td", { style: { padding: '8px', textAlign: 'right' }, children: fmtNum(r.week52_position, 1) })] }, r.krx_code))) })] }) }))] })] })] }));
}
