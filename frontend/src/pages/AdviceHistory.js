import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// AI 투자 조언 이력 페이지 — SPEC-STOCK-014 M6
import { useEffect, useState } from 'react';
import { fetchAdviceHistory, submitAdviceFeedback, } from '../api/advice';
const ADVICE_TYPE_LABEL = {
    rebalance: '리밸런싱 제안',
    risk_profile: '리스크 프로파일',
    market_briefing: '시장 브리핑',
};
const FEEDBACK_LABEL = {
    helpful: '도움됨',
    not_helpful: '도움 안됨',
    neutral: '보통',
};
// @MX:NOTE: [AUTO] feedback 버튼 상태 변경 후 즉시 UI 반영 (낙관적 업데이트 패턴)
const AdviceHistory = ({ token }) => {
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [feedbackPending, setFeedbackPending] = useState(null);
    useEffect(() => {
        if (!token)
            return;
        setLoading(true);
        fetchAdviceHistory(token)
            .then(setHistory)
            .catch((e) => setError(e.message))
            .finally(() => setLoading(false));
    }, [token]);
    const handleFeedback = async (adviceId, feedback) => {
        if (!token || feedbackPending !== null)
            return;
        setFeedbackPending(adviceId);
        try {
            await submitAdviceFeedback(token, adviceId, feedback);
            // 낙관적 업데이트: 로컬 상태 즉시 반영
            setHistory((prev) => prev.map((item) => item.id === adviceId ? { ...item, feedback } : item));
        }
        catch (e) {
            setError(e instanceof Error ? e.message : '피드백 제출 실패');
        }
        finally {
            setFeedbackPending(null);
        }
    };
    if (!token) {
        return (_jsx("div", { className: "container mx-auto p-4", children: _jsx("p", { className: "text-gray-500", children: "\uB85C\uADF8\uC778\uC774 \uD544\uC694\uD569\uB2C8\uB2E4." }) }));
    }
    if (loading) {
        return (_jsx("div", { className: "container mx-auto p-4", children: _jsx("p", { className: "text-gray-500", children: "AI \uC870\uC5B8 \uC774\uB825\uC744 \uBD88\uB7EC\uC624\uB294 \uC911..." }) }));
    }
    return (_jsxs("div", { className: "container mx-auto p-4", children: [_jsx("h1", { className: "text-2xl font-bold mb-6", children: "AI \uD22C\uC790 \uC870\uC5B8 \uC774\uB825" }), error && (_jsx("div", { className: "bg-red-50 border border-red-200 rounded p-3 mb-4 text-red-700", children: error })), history.length === 0 ? (_jsxs("div", { className: "text-center py-12 text-gray-400", children: [_jsx("p", { children: "\uC544\uC9C1 \uC0DD\uC131\uB41C AI \uC870\uC5B8\uC774 \uC5C6\uC2B5\uB2C8\uB2E4." }), _jsx("p", { className: "text-sm mt-2", children: "\uD3EC\uD2B8\uD3F4\uB9AC\uC624 \uD398\uC774\uC9C0\uC5D0\uC11C AI \uC870\uC5B8\uC744 \uC694\uCCAD\uD574 \uBCF4\uC138\uC694." })] })) : (_jsx("div", { className: "space-y-4", children: history.map((item) => (_jsxs("div", { className: "bg-white border border-gray-200 rounded-lg p-4 shadow-sm", children: [_jsxs("div", { className: "flex items-center justify-between mb-2", children: [_jsx("span", { className: "inline-block bg-blue-100 text-blue-800 text-xs font-medium px-2 py-1 rounded", children: ADVICE_TYPE_LABEL[item.advice_type] ?? item.advice_type }), _jsx("span", { className: "text-xs text-gray-400", children: item.ref_date })] }), _jsx("h3", { className: "font-semibold text-gray-800 mb-1", children: item.title }), item.body && (_jsx("p", { className: "text-sm text-gray-600 mb-2 line-clamp-3", children: item.body })), item.risk_score !== null && item.risk_score !== undefined && (_jsxs("div", { className: "flex items-center gap-2 mb-2", children: [_jsx("span", { className: "text-xs text-gray-500", children: "\uB9AC\uC2A4\uD06C \uC810\uC218:" }), _jsxs("span", { className: `font-bold text-sm ${item.risk_score >= 70
                                        ? 'text-red-600'
                                        : item.risk_score >= 40
                                            ? 'text-yellow-600'
                                            : 'text-green-600'}`, children: [item.risk_score, "/100"] })] })), _jsxs("div", { className: "flex items-center gap-2 mt-3 pt-3 border-t border-gray-100", children: [_jsx("span", { className: "text-xs text-gray-400", children: "\uB3C4\uC6C0\uC774 \uB418\uC5C8\uB098\uC694?" }), ['helpful', 'neutral', 'not_helpful'].map((fb) => (_jsx("button", { disabled: feedbackPending === item.id, onClick: () => handleFeedback(item.id, fb), className: `text-xs px-2 py-1 rounded border transition-colors ${item.feedback === fb
                                        ? 'bg-blue-600 text-white border-blue-600'
                                        : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'} disabled:opacity-50`, children: FEEDBACK_LABEL[fb] }, fb)))] }), _jsx("p", { className: "text-xs text-gray-300 mt-2", children: new Date(item.created_at).toLocaleString('ko-KR') })] }, item.id))) }))] }));
};
export default AdviceHistory;
