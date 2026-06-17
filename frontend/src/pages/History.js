import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// 추천 히스토리 페이지
import { useState, useEffect } from 'react';
import { getRecommendationHistory } from '../api/recommendations';
import { MarketSentimentWidget } from '../components/MarketSentimentWidget';
// 기간 선택 옵션
const PERIOD_OPTIONS = [
    { label: '7일', days: 7 },
    { label: '14일', days: 14 },
    { label: '30일', days: 30 },
];
// 점수를 백분율 표시로 변환
function formatScore(score) {
    return (score * 100).toFixed(1);
}
function RecommendationCard({ item }) {
    return (_jsxs("li", { style: {
            listStyle: 'none',
            border: '1px solid #e0e0e0',
            borderRadius: '8px',
            padding: '0.875rem 1rem',
            backgroundColor: '#fff',
            boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
        }, children: [_jsxs("div", { style: { display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.4rem' }, children: [_jsx("span", { style: {
                            display: 'inline-flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            width: '1.75rem',
                            height: '1.75rem',
                            borderRadius: '50%',
                            backgroundColor: '#1976d2',
                            color: '#fff',
                            fontSize: '0.75rem',
                            fontWeight: 700,
                            flexShrink: 0,
                        }, "aria-label": `순위 ${item.rank}`, children: item.rank }), _jsxs("div", { style: { flex: 1, minWidth: 0 }, children: [_jsx("span", { style: { fontWeight: 600, fontSize: '0.95rem', color: '#212121' }, children: item.name ?? item.krx_code }), _jsx("span", { style: { marginLeft: '0.5rem', fontSize: '0.8rem', color: '#888' }, children: item.krx_code })] }), _jsxs("span", { style: {
                            fontSize: '0.85rem',
                            fontWeight: 600,
                            color: '#1976d2',
                            flexShrink: 0,
                        }, "aria-label": `종합 점수 ${formatScore(item.total_score)}`, children: [formatScore(item.total_score), "\uC810"] })] }), item.reasoning && (_jsx("p", { style: {
                    margin: '0 0 0 2.5rem',
                    fontSize: '0.8rem',
                    color: '#666',
                    lineHeight: 1.5,
                }, children: item.reasoning }))] }));
}
function DailyGroup({ group }) {
    return (_jsxs("section", { "aria-labelledby": `date-${group.date}`, style: { marginBottom: '1.5rem' }, children: [_jsx("h3", { id: `date-${group.date}`, style: {
                    fontSize: '0.95rem',
                    fontWeight: 700,
                    color: '#424242',
                    margin: '0 0 0.75rem 0',
                    padding: '0.4rem 0.75rem',
                    backgroundColor: '#f5f5f5',
                    borderLeft: '3px solid #1976d2',
                    borderRadius: '0 4px 4px 0',
                }, children: group.date }), _jsx("ul", { style: { display: 'flex', flexDirection: 'column', gap: '0.5rem', padding: 0, margin: 0 }, children: group.recommendations.map((item) => (_jsx(RecommendationCard, { item: item }, `${group.date}-${item.krx_code}`))) })] }));
}
export default function History() {
    const [selectedDays, setSelectedDays] = useState(7);
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    useEffect(() => {
        let cancelled = false;
        async function loadHistory() {
            setLoading(true);
            setError(null);
            try {
                const result = await getRecommendationHistory(selectedDays);
                if (!cancelled) {
                    setData(result);
                }
            }
            catch (err) {
                if (!cancelled) {
                    setError(err instanceof Error ? err.message : '히스토리를 불러오는 중 오류가 발생했습니다.');
                }
            }
            finally {
                if (!cancelled) {
                    setLoading(false);
                }
            }
        }
        void loadHistory();
        return () => {
            cancelled = true;
        };
    }, [selectedDays]);
    return (_jsxs("div", { children: [_jsx("h1", { style: { fontSize: '1.5rem', fontWeight: 700, marginBottom: '1.25rem', color: '#212121' }, children: "\uCD94\uCC9C \uD788\uC2A4\uD1A0\uB9AC" }), _jsx("div", { style: { marginBottom: '1.5rem' }, children: _jsx(MarketSentimentWidget, {}) }), _jsx("div", { role: "tablist", "aria-label": "\uAE30\uAC04 \uC120\uD0DD", style: { display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }, children: PERIOD_OPTIONS.map((opt) => (_jsx("button", { role: "tab", "aria-selected": selectedDays === opt.days, onClick: () => setSelectedDays(opt.days), style: {
                        padding: '0.4rem 1rem',
                        border: '1px solid',
                        borderColor: selectedDays === opt.days ? '#1976d2' : '#ccc',
                        borderRadius: '20px',
                        backgroundColor: selectedDays === opt.days ? '#1976d2' : '#fff',
                        color: selectedDays === opt.days ? '#fff' : '#555',
                        fontWeight: selectedDays === opt.days ? 600 : 400,
                        cursor: 'pointer',
                        fontSize: '0.875rem',
                        transition: 'all 0.15s ease',
                    }, children: opt.label }, opt.days))) }), loading && (_jsx("div", { role: "status", "aria-live": "polite", style: { textAlign: 'center', padding: '3rem', color: '#888' }, children: _jsx("p", { children: "\uD788\uC2A4\uD1A0\uB9AC\uB97C \uBD88\uB7EC\uC624\uB294 \uC911..." }) })), !loading && error && (_jsxs("div", { role: "alert", style: {
                    padding: '1rem',
                    backgroundColor: '#ffebee',
                    border: '1px solid #ef9a9a',
                    borderRadius: '4px',
                    color: '#c62828',
                }, children: [_jsx("strong", { children: "\uC624\uB958:" }), " ", error] })), !loading && !error && data && data.groups.length === 0 && (_jsx("p", { style: { color: '#888', fontSize: '0.9rem', textAlign: 'center', padding: '2rem' }, children: "\uD788\uC2A4\uD1A0\uB9AC \uB370\uC774\uD130\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4." })), !loading && !error && data && data.groups.length > 0 && (_jsx("div", { children: data.groups.map((group) => (_jsx(DailyGroup, { group: group }, group.date))) })), _jsx("p", { style: {
                    marginTop: '2rem',
                    padding: '0.75rem 1rem',
                    backgroundColor: '#fff8e1',
                    borderLeft: '3px solid #ffc107',
                    borderRadius: '0 4px 4px 0',
                    fontSize: '0.8rem',
                    color: '#5f4000',
                    lineHeight: 1.6,
                }, children: "\uBCF8 \uD788\uC2A4\uD1A0\uB9AC\uB294 \uD22C\uC790 \uAD8C\uC720\uAC00 \uC544\uB2CC \uC815\uBCF4 \uC81C\uACF5 \uBAA9\uC801\uC785\uB2C8\uB2E4. \uACFC\uAC70 \uCD94\uCC9C \uC774\uB825\uC774 \uBBF8\uB798 \uC218\uC775\uC744 \uBCF4\uC7A5\uD558\uC9C0 \uC54A\uC73C\uBA70, \uD22C\uC790 \uACB0\uC815\uC740 \uBCF8\uC778 \uCC45\uC784\uD558\uC5D0 \uC774\uB8E8\uC5B4\uC838\uC57C \uD569\uB2C8\uB2E4." })] }));
}
