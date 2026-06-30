import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// 공유 포트폴리오 공개 보기 페이지 (SPEC-STOCK-042, 인증 불필요)
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getSharedPortfolio, likeSharedPortfolio } from '../api/feed';
import { useAuth } from '../auth/AuthContext';
// 수익률 색상
function rateColor(rate) {
    return rate >= 0 ? '#2e7d32' : '#c62828';
}
function formatRate(rate) {
    return `${rate >= 0 ? '+' : ''}${rate.toFixed(2)}%`;
}
// @MX:NOTE: [AUTO] SharedPortfolio 페이지 — 공개 포트폴리오 상세 보기 및 좋아요 (SPEC-STOCK-042)
export default function SharedPortfolio() {
    const { shareToken } = useParams();
    const { token } = useAuth();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [likeCount, setLikeCount] = useState(0);
    const [likeLoading, setLikeLoading] = useState(false);
    const [likeError, setLikeError] = useState(null);
    // 공유 포트폴리오 데이터 조회
    useEffect(() => {
        if (!shareToken)
            return;
        setLoading(true);
        setError(null);
        getSharedPortfolio(shareToken)
            .then((res) => {
            setData(res);
            setLikeCount(res.like_count);
        })
            .catch((e) => {
            setError(e instanceof Error ? e.message : '포트폴리오를 불러올 수 없습니다.');
        })
            .finally(() => setLoading(false));
    }, [shareToken]);
    // 좋아요 처리
    async function handleLike() {
        if (!shareToken)
            return;
        if (!token) {
            setLikeError('로그인 후 좋아요를 누를 수 있습니다.');
            return;
        }
        setLikeLoading(true);
        setLikeError(null);
        try {
            const res = await likeSharedPortfolio(shareToken, token);
            setLikeCount(res.like_count);
        }
        catch (e) {
            setLikeError(e instanceof Error ? e.message : '좋아요 처리에 실패했습니다.');
        }
        finally {
            setLikeLoading(false);
        }
    }
    if (loading) {
        return (_jsx("div", { role: "status", "aria-live": "polite", style: { textAlign: 'center', padding: '3rem', color: '#666' }, children: "\uB85C\uB529 \uC911..." }));
    }
    if (error) {
        return (_jsx("div", { role: "alert", style: {
                padding: '1rem',
                background: '#ffebee',
                border: '1px solid #ef9a9a',
                borderRadius: '4px',
                color: '#c62828',
            }, children: error }));
    }
    if (!data)
        return null;
    const cellStyle = { padding: '0.4rem 0.6rem', fontSize: '0.875rem' };
    return (_jsxs("div", { children: [_jsxs("div", { style: { marginBottom: '1.5rem' }, children: [_jsx("h2", { style: { margin: '0 0 0.5rem', color: '#0d47a1' }, children: data.portfolio_name }), _jsxs("div", { style: { display: 'flex', gap: '2rem', flexWrap: 'wrap', alignItems: 'center' }, children: [_jsxs("div", { children: [_jsx("span", { style: { fontSize: '0.75rem', color: '#666' }, children: "\uCD1D \uC218\uC775\uB960" }), _jsx("div", { style: { fontSize: '1.5rem', fontWeight: 700, color: rateColor(data.total_return_rate) }, children: formatRate(data.total_return_rate) })] }), data.goal_progress !== null && (_jsxs("div", { children: [_jsx("span", { style: { fontSize: '0.75rem', color: '#666' }, children: "\uBAA9\uD45C \uB2EC\uC131\uB960" }), _jsxs("div", { style: { fontSize: '1.1rem', fontWeight: 600, color: data.goal_progress >= 100 ? '#2e7d32' : '#1565c0' }, children: [data.goal_progress.toFixed(1), "%"] })] })), _jsxs("div", { children: [_jsx("span", { style: { fontSize: '0.75rem', color: '#666' }, children: "\uC870\uD68C\uC218" }), _jsx("div", { style: { fontSize: '1rem', fontWeight: 600 }, children: data.view_count.toLocaleString() })] })] })] }), _jsxs("div", { style: { marginBottom: '1.5rem' }, children: [_jsxs("button", { onClick: () => void handleLike(), disabled: likeLoading, "aria-label": `좋아요 ${likeCount}개`, style: {
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.4rem',
                            padding: '0.45rem 1rem',
                            background: '#fff',
                            border: '1px solid #e91e63',
                            color: '#e91e63',
                            borderRadius: '20px',
                            cursor: likeLoading ? 'default' : 'pointer',
                            fontSize: '0.875rem',
                            fontWeight: 600,
                            opacity: likeLoading ? 0.7 : 1,
                        }, children: ["\u2665 \uC88B\uC544\uC694 ", likeCount.toLocaleString()] }), likeError && (_jsx("span", { style: { marginLeft: '0.75rem', fontSize: '0.8rem', color: '#c62828' }, children: likeError }))] }), _jsxs("div", { children: [_jsx("h3", { style: { margin: '0 0 0.75rem', fontSize: '1rem', color: '#333' }, children: "\uBCF4\uC720 \uC885\uBAA9" }), data.holdings.length === 0 ? (_jsx("p", { style: { color: '#666', fontSize: '0.875rem' }, children: "\uBCF4\uC720 \uC885\uBAA9 \uC815\uBCF4\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4." })) : (_jsx("div", { style: { overflowX: 'auto' }, children: _jsxs("table", { style: { width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem', minWidth: '360px' }, children: [_jsx("thead", { children: _jsxs("tr", { style: { background: '#e3f2fd' }, children: [_jsx("th", { style: cellStyle, children: "\uD2F0\uCEE4" }), _jsx("th", { style: { ...cellStyle, textAlign: 'right' }, children: "\uBCF4\uC720 \uC218\uB7C9" }), _jsx("th", { style: { ...cellStyle, textAlign: 'right' }, children: "\uB9E4\uC218 \uB2E8\uAC00" })] }) }), _jsx("tbody", { children: data.holdings.map((h) => (_jsxs("tr", { style: { borderBottom: '1px solid #eee' }, children: [_jsx("td", { style: { ...cellStyle, fontWeight: 600 }, children: h.ticker }), _jsx("td", { style: { ...cellStyle, textAlign: 'right' }, children: h.shares.toLocaleString() }), _jsx("td", { style: { ...cellStyle, textAlign: 'right' }, children: h.purchase_price.toLocaleString() })] }, h.ticker))) })] }) }))] }), _jsx("p", { style: { marginTop: '1.5rem', fontSize: '0.75rem', color: '#888' }, children: "\uC774 \uC815\uBCF4\uB294 \uCC38\uACE0\uC6A9\uC774\uBA70, \uC2E4\uC81C \uD22C\uC790 \uACB0\uC815\uC740 \uBCF8\uC778 \uCC45\uC784\uD558\uC5D0 \uC774\uB8E8\uC5B4\uC838\uC57C \uD569\uB2C8\uB2E4." })] }));
}
