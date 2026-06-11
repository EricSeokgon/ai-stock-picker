import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// 피드백 버튼 컴포넌트 — 좋아요/싫어요 + 카운트 표시
import { useEffect, useState } from 'react';
import { fetchFeedbackSummary, submitFeedback } from '../api/recommendations';
export function FeedbackButtons({ krxCode }) {
    const [upCount, setUpCount] = useState(0);
    const [downCount, setDownCount] = useState(0);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState(null);
    useEffect(() => {
        let cancelled = false;
        setLoading(true);
        setError(null);
        fetchFeedbackSummary(krxCode)
            .then((data) => {
            if (cancelled)
                return;
            setUpCount(data.up);
            setDownCount(data.down);
        })
            .catch(() => {
            if (!cancelled)
                setError('피드백 정보를 불러올 수 없습니다');
        })
            .finally(() => {
            if (!cancelled)
                setLoading(false);
        });
        return () => { cancelled = true; };
    }, [krxCode]);
    async function handleVote(vote) {
        if (submitting)
            return;
        setSubmitting(true);
        setError(null);
        try {
            const data = await submitFeedback(krxCode, vote);
            setUpCount(data.up);
            setDownCount(data.down);
        }
        catch {
            setError('피드백 제출 중 오류가 발생했습니다');
        }
        finally {
            setSubmitting(false);
        }
    }
    const isDisabled = loading || submitting;
    const btnStyle = (active) => ({
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.3rem',
        padding: '0.35rem 0.75rem',
        border: `1px solid ${active ? '#1976d2' : '#ddd'}`,
        borderRadius: '20px',
        background: active ? '#e3f2fd' : '#fafafa',
        cursor: isDisabled ? 'not-allowed' : 'pointer',
        opacity: isDisabled ? 0.6 : 1,
        fontSize: '0.85rem',
        fontWeight: 600,
        color: '#333',
        transition: 'background 0.15s',
    });
    return (_jsxs("div", { children: [_jsxs("div", { style: { display: 'flex', gap: '0.5rem', alignItems: 'center' }, children: [_jsxs("button", { "aria-label": `좋아요 ${upCount}개`, disabled: isDisabled, onClick: () => { void handleVote('up'); }, style: btnStyle(false), children: [_jsx("span", { "aria-hidden": "true", children: "\uD83D\uDC4D" }), _jsx("span", { children: upCount })] }), _jsxs("button", { "aria-label": `싫어요 ${downCount}개`, disabled: isDisabled, onClick: () => { void handleVote('down'); }, style: btnStyle(false), children: [_jsx("span", { "aria-hidden": "true", children: "\uD83D\uDC4E" }), _jsx("span", { children: downCount })] })] }), error && (_jsx("p", { role: "alert", style: { margin: '0.4rem 0 0', fontSize: '0.8rem', color: '#c62828' }, children: error }))] }));
}
