import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// 점수를 백분율 바로 시각화
function ScoreBar({ score, label }) {
    // 점수 범위: -1~1 또는 0~1 가정, 표시용으로 0~100% 변환
    const pct = Math.min(100, Math.max(0, Math.round(score * 100)));
    const color = score >= 0 ? '#2e7d32' : '#c62828';
    return (_jsxs("div", { style: { display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }, children: [_jsx("span", { style: { fontSize: '0.75rem', color: '#666', width: '80px', flexShrink: 0 }, children: label }), _jsx("div", { style: {
                    flex: 1,
                    height: '8px',
                    backgroundColor: '#e0e0e0',
                    borderRadius: '4px',
                    overflow: 'hidden',
                }, children: _jsx("div", { style: {
                        height: '100%',
                        width: `${pct}%`,
                        backgroundColor: color,
                        borderRadius: '4px',
                        transition: 'width 0.3s ease',
                    } }) }), _jsx("span", { style: { fontSize: '0.75rem', color, width: '45px', textAlign: 'right', flexShrink: 0 }, children: score.toFixed(3) })] }));
}
function RecommendationCard({ item, onSelect, }) {
    const sentimentColor = item.sentiment_score > 0 ? '#2e7d32' : item.sentiment_score < 0 ? '#c62828' : '#555';
    const isClickable = Boolean(onSelect);
    return (_jsxs("li", { onClick: () => onSelect?.(item.krx_code), style: {
            listStyle: 'none',
            border: '1px solid #ddd',
            borderRadius: '8px',
            padding: '1rem 1.25rem',
            backgroundColor: '#fff',
            boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
            cursor: isClickable ? 'pointer' : 'default',
            transition: 'box-shadow 0.15s',
        }, children: [_jsxs("div", { style: { display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '0.75rem' }, children: [_jsx("span", { style: {
                            display: 'inline-flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            width: '36px',
                            height: '36px',
                            borderRadius: '50%',
                            backgroundColor: item.rank <= 3 ? '#1976d2' : '#546e7a',
                            color: '#fff',
                            fontWeight: 700,
                            fontSize: '0.9rem',
                            flexShrink: 0,
                        }, "aria-label": `순위 ${item.rank}위`, children: item.rank }), _jsx("span", { style: {
                            fontWeight: 700,
                            fontSize: '1.1rem',
                            color: '#212121',
                            letterSpacing: '0.05em',
                        }, children: item.krx_code }), _jsxs("span", { style: {
                            marginLeft: 'auto',
                            fontSize: '0.875rem',
                            fontWeight: 600,
                            color: sentimentColor,
                        }, children: ["\uC885\uD569 ", (item.total_score * 100).toFixed(1), "\uC810"] })] }), _jsxs("div", { style: { marginBottom: '0.75rem' }, children: [_jsx(ScoreBar, { score: item.sentiment_score, label: "\uAC10\uC131" }), _jsx(ScoreBar, { score: item.volume_score, label: "\uAC70\uB798\uB7C9" }), _jsx(ScoreBar, { score: item.momentum_score, label: "\uBAA8\uBA58\uD140" }), _jsx(ScoreBar, { score: item.anomaly_score, label: "\uC774\uC0C1\uAC10\uC9C0" })] }), item.base_score != null && item.feedback_score != null && item.feedback_score !== 0 && (_jsx("div", { style: { marginBottom: '0.5rem' }, children: _jsxs("span", { style: {
                        display: 'inline-block',
                        padding: '2px 8px',
                        borderRadius: '12px',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        backgroundColor: item.feedback_score > 0 ? '#e8f5e9' : '#ffebee',
                        color: item.feedback_score > 0 ? '#2e7d32' : '#c62828',
                    }, children: ["\uD53C\uB4DC\uBC31 \uBC18\uC601 ", item.feedback_score > 0 ? '+' : '', item.feedback_score.toFixed(3)] }) })), _jsx("p", { style: {
                    margin: 0,
                    fontSize: '0.875rem',
                    color: '#444',
                    lineHeight: 1.6,
                    borderTop: '1px solid #f0f0f0',
                    paddingTop: '0.75rem',
                }, children: item.reasoning })] }));
}
// @MX:ANCHOR: [AUTO] RecommendationList - 주식 추천 목록 공개 컴포넌트
// @MX:REASON: App.tsx, Dashboard, 테스트에서 직접 참조. onSelect 콜백 추가로 modal 연계
export function RecommendationList({ recommendations, onSelect }) {
    return (_jsxs("section", { "aria-labelledby": "recommendation-heading", children: [_jsx("h2", { id: "recommendation-heading", style: { fontSize: '1.25rem', fontWeight: 700, marginBottom: '1rem', color: '#212121' }, children: "\uC624\uB298\uC758 \uC8FC\uC2DD \uCD94\uCC9C" }), _jsx("ul", { className: "recommendation-list", style: { display: 'flex', flexDirection: 'column', gap: '0.75rem', padding: 0, margin: 0 }, "aria-label": "\uC8FC\uC2DD \uCD94\uCC9C \uBAA9\uB85D", children: recommendations.map((item) => (_jsx(RecommendationCard, { item: item, onSelect: onSelect }, item.krx_code))) }), _jsx("style", { children: `
        @media (max-width: 767px) {
          .recommendation-list li {
            padding: 0.75rem 1rem !important;
          }
          .recommendation-list li > div:first-child {
            flex-wrap: wrap;
            gap: 0.5rem;
          }
        }
      ` })] }));
}
