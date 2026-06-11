import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
function EtfItem({ item, onSelect, }) {
    const isClickable = Boolean(onSelect);
    return (_jsxs("li", { onClick: () => onSelect?.(item.krx_code), style: {
            listStyle: 'none',
            padding: '0.75rem 1rem',
            border: '1px solid #ddd',
            borderRadius: '8px',
            backgroundColor: '#fff',
            cursor: isClickable ? 'pointer' : 'default',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.25rem',
            transition: 'box-shadow 0.15s',
        }, onMouseEnter: (e) => {
            if (isClickable)
                e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.12)';
        }, onMouseLeave: (e) => {
            e.currentTarget.style.boxShadow = 'none';
        }, children: [_jsxs("div", { style: { display: 'flex', alignItems: 'center', gap: '0.75rem' }, children: [_jsx("span", { "aria-label": `순위 ${item.rank}위`, style: {
                            display: 'inline-flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            width: '28px',
                            height: '28px',
                            borderRadius: '50%',
                            backgroundColor: '#1565c0',
                            color: '#fff',
                            fontWeight: 700,
                            fontSize: '0.8rem',
                            flexShrink: 0,
                        }, children: item.rank }), _jsx("span", { style: {
                            fontWeight: 700,
                            fontSize: '1rem',
                            color: '#212121',
                            letterSpacing: '0.04em',
                        }, children: item.krx_code }), _jsxs("span", { style: {
                            marginLeft: 'auto',
                            fontSize: '0.8rem',
                            fontWeight: 600,
                            color: '#1565c0',
                        }, children: [(item.total_score * 100).toFixed(1), "\uC810"] })] }), _jsx("p", { style: {
                    margin: 0,
                    fontSize: '0.8rem',
                    color: '#555',
                    lineHeight: 1.5,
                    paddingLeft: '2.5rem',
                }, children: item.reasoning })] }));
}
// @MX:ANCHOR: [AUTO] EtfRecommendationList - ETF 추천 목록 공개 컴포넌트
// @MX:REASON: App.tsx에서 직접 참조하는 외부 노출 컴포넌트
export function EtfRecommendationList({ etfItems, onSelect }) {
    return (_jsxs("section", { "aria-labelledby": "etf-heading", children: [_jsx("h2", { id: "etf-heading", style: {
                    fontSize: '1.25rem',
                    fontWeight: 700,
                    marginBottom: '1rem',
                    color: '#212121',
                }, children: "ETF \uCD94\uCC9C" }), etfItems.length === 0 ? (_jsx("p", { style: { color: '#999', textAlign: 'center', padding: '1rem 0' }, children: "ETF \uCD94\uCC9C\uC774 \uC5C6\uC2B5\uB2C8\uB2E4" })) : (_jsx("ul", { style: { display: 'flex', flexDirection: 'column', gap: '0.5rem', padding: 0, margin: 0 }, "aria-label": "ETF \uCD94\uCC9C \uBAA9\uB85D", children: etfItems.map((item) => (_jsx(EtfItem, { item: item, onSelect: onSelect }, item.krx_code))) }))] }));
}
