import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
// 종목 상세 정보 모달 컴포넌트
import { useEffect, useState } from 'react';
import { fetchRecommendationDetail } from '../api/client';
import { PriceChart } from './PriceChart';
import { FeedbackButtons } from './FeedbackButtons';
import { ScoreBreakdown } from './ScoreBreakdown';
// 감성 레이블 및 색상 맵
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
function NewsItem({ item }) {
    return (_jsxs("li", { style: {
            padding: '0.5rem 0',
            borderBottom: '1px solid #f0f0f0',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.25rem',
        }, children: [_jsxs("div", { style: { display: 'flex', alignItems: 'flex-start', gap: '0.5rem' }, children: [_jsx(SentimentBadge, { sentiment: item.sentiment }), _jsx("span", { style: { fontSize: '0.875rem', color: '#333', lineHeight: 1.4 }, children: item.title })] }), item.summary && (_jsx("p", { style: { margin: 0, fontSize: '0.8rem', color: '#666', paddingLeft: '2.5rem' }, children: item.summary }))] }));
}
function ScoreRow({ label, score }) {
    const pct = Math.min(100, Math.max(0, Math.round(score * 100)));
    const color = score >= 0 ? '#2e7d32' : '#c62828';
    return (_jsxs("div", { style: { display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }, children: [_jsx("span", { style: { fontSize: '0.75rem', color: '#666', width: '72px', flexShrink: 0 }, children: label }), _jsx("div", { style: {
                    flex: 1,
                    height: '6px',
                    backgroundColor: '#e0e0e0',
                    borderRadius: '3px',
                    overflow: 'hidden',
                }, children: _jsx("div", { style: { height: '100%', width: `${pct}%`, backgroundColor: color, borderRadius: '3px' } }) }), _jsx("span", { style: { fontSize: '0.75rem', color, width: '42px', textAlign: 'right', flexShrink: 0 }, children: score.toFixed(3) })] }));
}
// @MX:ANCHOR: [AUTO] StockDetail - 종목 상세 모달 공개 컴포넌트
// @MX:REASON: App.tsx, 테스트에서 직접 참조. 내부에서 API 호출 수행
export function StockDetail({ krxCode, onClose }) {
    const [detail, setDetail] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    useEffect(() => {
        let cancelled = false;
        async function loadDetail() {
            try {
                setLoading(true);
                setError(null);
                const data = await fetchRecommendationDetail(krxCode);
                if (!cancelled)
                    setDetail(data);
            }
            catch (err) {
                if (!cancelled) {
                    setError(err instanceof Error ? err.message : '상세 정보를 불러올 수 없습니다.');
                }
            }
            finally {
                if (!cancelled)
                    setLoading(false);
            }
        }
        void loadDetail();
        return () => { cancelled = true; };
    }, [krxCode]);
    // 오버레이 클릭 시 모달 닫기
    const handleOverlayClick = (e) => {
        if (e.target === e.currentTarget)
            onClose();
    };
    return (
    // 모달 오버레이
    _jsx("div", { role: "dialog", "aria-modal": "true", "aria-label": `${krxCode} 종목 상세`, onClick: handleOverlayClick, style: {
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0,0,0,0.45)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '1rem',
        }, children: _jsxs("div", { style: {
                background: '#fff',
                borderRadius: '12px',
                boxShadow: '0 8px 32px rgba(0,0,0,0.18)',
                width: '100%',
                maxWidth: '560px',
                maxHeight: '80vh',
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
            }, children: [_jsxs("div", { style: {
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '1rem 1.25rem',
                        borderBottom: '1px solid #eee',
                    }, children: [_jsx("h3", { style: { margin: 0, fontSize: '1.1rem', fontWeight: 700, color: '#0d47a1' }, children: loading ? '종목 상세' : (detail?.krx_code ?? krxCode) }), _jsx("button", { onClick: onClose, "aria-label": "\uB2EB\uAE30", style: {
                                background: 'none',
                                border: 'none',
                                fontSize: '1.25rem',
                                cursor: 'pointer',
                                color: '#555',
                                padding: '0.25rem 0.5rem',
                                borderRadius: '4px',
                            }, children: "\u2715" })] }), _jsxs("div", { style: { overflow: 'auto', padding: '1rem 1.25rem', flex: 1 }, children: [loading && (_jsx("p", { style: { textAlign: 'center', color: '#888', padding: '2rem 0' }, children: "\uBD88\uB7EC\uC624\uB294 \uC911..." })), error && (_jsxs("p", { style: { color: '#c62828', padding: '1rem 0' }, children: ["\uC624\uB958: ", error] })), detail && !loading && (_jsxs(_Fragment, { children: [_jsxs("p", { style: { margin: '0 0 0.75rem', fontSize: '0.8rem', color: '#888' }, children: ["\uAE30\uC900\uC77C: ", detail.trade_date] }), _jsxs("div", { style: { marginBottom: '1rem' }, children: [_jsxs("p", { style: { margin: '0 0 0.5rem', fontSize: '0.85rem', fontWeight: 600, color: '#333' }, children: ["\uC810\uC218 \uBD84\uC11D (\uC885\uD569: ", (detail.total_score * 100).toFixed(1), "\uC810)"] }), _jsx(ScoreRow, { label: "\uAC10\uC131", score: detail.sentiment_score }), _jsx(ScoreRow, { label: "\uAC70\uB798\uB7C9", score: detail.volume_score }), _jsx(ScoreRow, { label: "\uBAA8\uBA58\uD140", score: detail.momentum_score }), _jsx(ScoreRow, { label: "\uC774\uC0C1\uAC10\uC9C0", score: detail.anomaly_score })] }), detail.score_breakdown && (_jsxs("div", { style: { marginTop: '1rem', marginBottom: '1rem' }, children: [_jsx("h4", { style: { fontSize: '0.875rem', color: '#555', marginBottom: '0.5rem', margin: '0 0 0.5rem' }, children: "\uC2A4\uCF54\uC5B4 \uBD84\uD574" }), _jsx(ScoreBreakdown, { breakdown: detail.score_breakdown })] })), _jsx("div", { style: { marginBottom: '1rem' }, children: _jsx(PriceChart, { krxCode: krxCode }) }), _jsxs("div", { style: { marginBottom: '1rem' }, children: [_jsx("p", { style: { margin: '0 0 0.4rem', fontSize: '0.85rem', fontWeight: 600, color: '#333' }, children: "\uC774 \uCD94\uCC9C\uC774 \uB3C4\uC6C0\uC774 \uB410\uB098\uC694?" }), _jsx(FeedbackButtons, { krxCode: krxCode })] }), _jsxs("div", { style: { marginBottom: '1rem' }, children: [_jsx("p", { style: { margin: '0 0 0.5rem', fontSize: '0.85rem', fontWeight: 600, color: '#333' }, children: "\uCD94\uCC9C \uC774\uC720" }), _jsx("p", { style: {
                                                margin: 0,
                                                fontSize: '0.875rem',
                                                color: '#444',
                                                lineHeight: 1.6,
                                                backgroundColor: '#f5f5f5',
                                                padding: '0.75rem',
                                                borderRadius: '6px',
                                            }, children: detail.reasoning })] }), detail.contributing_news.length > 0 && (_jsxs("div", { children: [_jsxs("p", { style: { margin: '0 0 0.5rem', fontSize: '0.85rem', fontWeight: 600, color: '#333' }, children: ["\uAE30\uC5EC \uB274\uC2A4 (", detail.contributing_news.length, "\uAC74)"] }), _jsx("ul", { style: { margin: 0, padding: 0, listStyle: 'none' }, children: detail.contributing_news.map((news, idx) => (_jsx(NewsItem, { item: news }, idx))) })] })), _jsx("p", { style: {
                                        marginTop: '1rem',
                                        fontSize: '0.75rem',
                                        color: '#999',
                                        fontStyle: 'italic',
                                    }, children: detail.disclaimer })] }))] })] }) }));
}
