import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
// 종목 상세 전체 페이지 뷰 — /stocks/:krxCode 라우트
import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { fetchRecommendationDetail } from '../api/client';
import { PriceChart } from '../components/PriceChart';
import { FeedbackButtons } from '../components/FeedbackButtons';
const DISCLAIMER = '본 정보는 투자 권유가 아닌 참고 목적입니다';
const SENTIMENT_MAP = {
    positive: { label: '긍정', color: '#1b5e20', bg: '#e8f5e9' },
    negative: { label: '부정', color: '#b71c1c', bg: '#ffebee' },
    neutral: { label: '중립', color: '#37474f', bg: '#eceff1' },
};
function SentimentBadge({ sentiment }) {
    const info = SENTIMENT_MAP[sentiment] ?? SENTIMENT_MAP['neutral'];
    return (_jsx("span", { style: {
            display: 'inline-block',
            padding: '1px 8px',
            borderRadius: '12px',
            fontSize: '0.75rem',
            fontWeight: 600,
            color: info.color,
            backgroundColor: info.bg,
            flexShrink: 0,
        }, children: info.label }));
}
function ScoreRow({ label, score }) {
    const pct = Math.min(100, Math.max(0, Math.round(score * 100)));
    const color = score >= 0 ? '#2e7d32' : '#c62828';
    return (_jsxs("div", { style: { display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }, children: [_jsx("span", { style: { fontSize: '0.75rem', color: '#666', width: '72px', flexShrink: 0 }, children: label }), _jsx("div", { style: { flex: 1, height: '6px', backgroundColor: '#e0e0e0', borderRadius: '3px', overflow: 'hidden' }, children: _jsx("div", { style: { height: '100%', width: `${pct}%`, backgroundColor: color, borderRadius: '3px' } }) }), _jsx("span", { style: { fontSize: '0.75rem', color, width: '42px', textAlign: 'right', flexShrink: 0 }, children: score.toFixed(3) })] }));
}
function NewsListItem({ item }) {
    return (_jsxs("li", { style: { padding: '0.5rem 0', borderBottom: '1px solid #f0f0f0', display: 'flex', flexDirection: 'column', gap: '0.25rem' }, children: [_jsxs("div", { style: { display: 'flex', alignItems: 'flex-start', gap: '0.5rem' }, children: [_jsx(SentimentBadge, { sentiment: item.sentiment }), _jsx("span", { style: { fontSize: '0.875rem', color: '#333', lineHeight: 1.4 }, children: item.title })] }), item.summary && (_jsx("p", { style: { margin: 0, fontSize: '0.8rem', color: '#666', paddingLeft: '2.5rem' }, children: item.summary }))] }));
}
// 전체 페이지용 인라인 종목 상세 컴포넌트
function InlineStockDetail({ krxCode }) {
    const [detail, setDetail] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    useEffect(() => {
        let cancelled = false;
        setLoading(true);
        setError(null);
        fetchRecommendationDetail(krxCode)
            .then((data) => { if (!cancelled)
            setDetail(data); })
            .catch((err) => {
            if (!cancelled)
                setError(err instanceof Error ? err.message : '상세 정보를 불러올 수 없습니다.');
        })
            .finally(() => { if (!cancelled)
            setLoading(false); });
        return () => { cancelled = true; };
    }, [krxCode]);
    return (_jsxs("div", { style: { padding: '1.25rem' }, children: [_jsx("h2", { style: { margin: '0 0 0.5rem', fontSize: '1.2rem', fontWeight: 700, color: '#0d47a1' }, children: loading ? krxCode : (detail?.krx_code ?? krxCode) }), loading && (_jsx("p", { style: { textAlign: 'center', color: '#888', padding: '2rem 0' }, children: "\uBD88\uB7EC\uC624\uB294 \uC911..." })), error && (_jsxs("p", { style: { color: '#c62828', padding: '1rem 0' }, children: ["\uC624\uB958: ", error] })), detail && !loading && (_jsxs(_Fragment, { children: [_jsxs("p", { style: { margin: '0 0 0.75rem', fontSize: '0.8rem', color: '#888' }, children: ["\uAE30\uC900\uC77C: ", detail.trade_date] }), _jsxs("div", { style: { marginBottom: '1rem' }, children: [_jsxs("p", { style: { margin: '0 0 0.5rem', fontSize: '0.85rem', fontWeight: 600, color: '#333' }, children: ["\uC810\uC218 \uBD84\uC11D (\uC885\uD569: ", (detail.total_score * 100).toFixed(1), "\uC810)"] }), _jsx(ScoreRow, { label: "\uAC10\uC131", score: detail.sentiment_score }), _jsx(ScoreRow, { label: "\uAC70\uB798\uB7C9", score: detail.volume_score }), _jsx(ScoreRow, { label: "\uBAA8\uBA58\uD140", score: detail.momentum_score }), _jsx(ScoreRow, { label: "\uC774\uC0C1\uAC10\uC9C0", score: detail.anomaly_score })] }), _jsx("div", { style: { marginBottom: '1rem' }, children: _jsx(PriceChart, { krxCode: krxCode }) }), _jsxs("div", { style: { marginBottom: '1rem' }, children: [_jsx("p", { style: { margin: '0 0 0.4rem', fontSize: '0.85rem', fontWeight: 600, color: '#333' }, children: "\uC774 \uCD94\uCC9C\uC774 \uB3C4\uC6C0\uC774 \uB410\uB098\uC694?" }), _jsx(FeedbackButtons, { krxCode: krxCode })] }), _jsxs("div", { style: { marginBottom: '1rem' }, children: [_jsx("p", { style: { margin: '0 0 0.5rem', fontSize: '0.85rem', fontWeight: 600, color: '#333' }, children: "\uCD94\uCC9C \uC774\uC720" }), _jsx("p", { style: { margin: 0, fontSize: '0.875rem', color: '#444', lineHeight: 1.6, backgroundColor: '#f5f5f5', padding: '0.75rem', borderRadius: '6px' }, children: detail.reasoning })] }), detail.contributing_news.length > 0 && (_jsxs("div", { children: [_jsxs("p", { style: { margin: '0 0 0.5rem', fontSize: '0.85rem', fontWeight: 600, color: '#333' }, children: ["\uAE30\uC5EC \uB274\uC2A4 (", detail.contributing_news.length, "\uAC74)"] }), _jsx("ul", { style: { margin: 0, padding: 0, listStyle: 'none' }, children: detail.contributing_news.map((news, idx) => (_jsx(NewsListItem, { item: news }, idx))) })] })), _jsx("p", { style: { marginTop: '1rem', fontSize: '0.75rem', color: '#999', fontStyle: 'italic' }, children: detail.disclaimer })] }))] }));
}
export default function StockDetailPage() {
    const { krxCode } = useParams();
    if (!krxCode) {
        return (_jsx("div", { style: { padding: '2rem', textAlign: 'center', color: '#c62828' }, children: "\uC885\uBAA9 \uCF54\uB4DC\uAC00 \uC62C\uBC14\uB974\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4." }));
    }
    return (_jsxs("div", { style: { maxWidth: '640px', margin: '0 auto', padding: '1rem 0' }, children: [_jsx("div", { style: { marginBottom: '1rem' }, children: _jsx(Link, { to: "/", style: { color: '#1976d2', textDecoration: 'none', fontSize: '0.875rem' }, children: "\u2190 \uD648\uC73C\uB85C" }) }), _jsx("div", { style: {
                    background: '#fff',
                    borderRadius: '12px',
                    boxShadow: '0 2px 12px rgba(0,0,0,0.1)',
                    overflow: 'hidden',
                }, children: _jsx(InlineStockDetail, { krxCode: krxCode }) }), _jsx("p", { style: {
                    marginTop: '1.5rem',
                    padding: '0.75rem 1rem',
                    backgroundColor: '#fffde7',
                    border: '1px solid #fff176',
                    borderRadius: '6px',
                    fontSize: '0.8rem',
                    color: '#795548',
                    fontStyle: 'italic',
                }, role: "note", children: DISCLAIMER })] }));
}
