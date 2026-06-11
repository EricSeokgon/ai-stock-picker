import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
export const DEFAULT_FILTERS = {
    sector: '',
    sort: 'score',
    minScore: 0,
};
const containerStyle = {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '0.75rem',
    alignItems: 'flex-end',
    padding: '0.75rem 1rem',
    backgroundColor: '#f5f7fa',
    border: '1px solid #e0e4eb',
    borderRadius: '8px',
    marginBottom: '1rem',
};
const fieldStyle = {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.25rem',
};
const labelStyle = {
    fontSize: '0.75rem',
    color: '#555',
    fontWeight: 600,
};
const selectStyle = {
    padding: '0.35rem 0.5rem',
    border: '1px solid #ccc',
    borderRadius: '4px',
    fontSize: '0.875rem',
    backgroundColor: '#fff',
    minWidth: '120px',
};
const numberInputStyle = {
    padding: '0.35rem 0.5rem',
    border: '1px solid #ccc',
    borderRadius: '4px',
    fontSize: '0.875rem',
    width: '80px',
};
const resetBtnStyle = {
    padding: '0.35rem 0.75rem',
    border: '1px solid #aaa',
    borderRadius: '4px',
    background: '#fff',
    cursor: 'pointer',
    fontSize: '0.8rem',
    color: '#444',
    alignSelf: 'flex-end',
};
const loadingStyle = {
    fontSize: '0.8rem',
    color: '#1976d2',
    alignSelf: 'center',
    fontStyle: 'italic',
};
// @MX:ANCHOR: [AUTO] RecommendationFilterBar — 필터 UI 공개 컴포넌트
// @MX:REASON: Dashboard, 테스트에서 직접 참조. FilterState + onFilterChange 계약 유지 필요
export function RecommendationFilterBar({ sectors, filters, onFilterChange, isLoading = false, }) {
    function handleSectorChange(e) {
        onFilterChange({ ...filters, sector: e.target.value });
    }
    function handleSortChange(e) {
        onFilterChange({ ...filters, sort: e.target.value });
    }
    function handleMinScoreChange(e) {
        const val = parseFloat(e.target.value);
        onFilterChange({ ...filters, minScore: isNaN(val) ? 0 : Math.min(1, Math.max(0, val)) });
    }
    function handleReset() {
        onFilterChange({ ...DEFAULT_FILTERS });
    }
    return (_jsxs("div", { style: containerStyle, role: "search", "aria-label": "\uCD94\uCC9C \uC885\uBAA9 \uD544\uD130", children: [_jsxs("div", { style: fieldStyle, children: [_jsx("label", { htmlFor: "filter-sector", style: labelStyle, children: "\uC139\uD130" }), _jsxs("select", { id: "filter-sector", value: filters.sector, onChange: handleSectorChange, style: selectStyle, "aria-label": "\uC139\uD130 \uC120\uD0DD", children: [_jsx("option", { value: "", children: "\uC804\uCCB4" }), sectors.map((s) => (_jsx("option", { value: s, children: s }, s)))] })] }), _jsxs("div", { style: fieldStyle, children: [_jsx("label", { htmlFor: "filter-sort", style: labelStyle, children: "\uC815\uB82C" }), _jsxs("select", { id: "filter-sort", value: filters.sort, onChange: handleSortChange, style: selectStyle, "aria-label": "\uC815\uB82C \uAE30\uC900 \uC120\uD0DD", children: [_jsx("option", { value: "score", children: "\uCD94\uCC9C\uC810\uC218" }), _jsx("option", { value: "sentiment", children: "\uAC10\uC131\uC810\uC218" }), _jsx("option", { value: "volume", children: "\uAC70\uB798\uB7C9\uC774\uC0C1" })] })] }), _jsxs("div", { style: fieldStyle, children: [_jsx("label", { htmlFor: "filter-min-score", style: labelStyle, children: "\uCD5C\uC18C \uC810\uC218" }), _jsx("input", { id: "filter-min-score", type: "number", min: 0, max: 1, step: 0.1, value: filters.minScore, onChange: handleMinScoreChange, style: numberInputStyle, "aria-label": "\uCD5C\uC18C \uC810\uC218 \uC785\uB825" })] }), isLoading && (_jsx("span", { style: loadingStyle, role: "status", "aria-live": "polite", children: "\uD544\uD130 \uC801\uC6A9 \uC911..." })), _jsx("button", { type: "button", onClick: handleReset, style: resetBtnStyle, "aria-label": "\uD544\uD130 \uCD08\uAE30\uD654", children: "\uD544\uD130 \uCD08\uAE30\uD654" })] }));
}
