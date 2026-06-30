import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// 공유 포트폴리오 공개 보기 페이지 (SPEC-STOCK-042, 인증 불필요)
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getSharedPortfolio, likeSharedPortfolio, unlikeSharedPortfolio } from '../api/feed';
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
    const [liked, setLiked] = useState(false);
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
    // 좋아요/취소 토글 처리 (session-local: 초기값 false, 서버 응답 확인 후 상태 변경)
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
            if (liked) {
                await unlikeSharedPortfolio(shareToken, token);
                setLiked(false);
                setLikeCount((c) => c - 1);
            } else {
                const res = await likeSharedPortfolio(shareToken, token);
                setLiked(true);
                setLikeCount(res.like_count);
            }
        }
        catch (e) {
            setLikeError(e instanceof Error ? e.message : '좋아요 처리에 실패했습니다.');
        }
        finally {
            setLikeLoading(false);
        }
    }
    if (loading) {
        return (_jsx("div", { role: "status", "aria-live": "polite", style: { textAlign: 'center', padding: '3rem', color: '#666' }, children: "로딩 중..." }));
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
    return (_jsxs("div", { children: [_jsxs("div", { style: { marginBottom: '1.5rem' }, children: [_jsx("h2", { style: { margin: '0 0 0.5rem', color: '#0d47a1' }, children: data.portfolio_name }), _jsxs("div", { style: { display: 'flex', gap: '2rem', flexWrap: 'wrap', alignItems: 'center' }, children: [_jsxs("div", { children: [_jsx("span", { style: { fontSize: '0.75rem', color: '#666' }, children: "총 수익률" }), _jsx("div", { style: { fontSize: '1.5rem', fontWeight: 700, color: rateColor(data.total_return_rate) }, children: formatRate(data.total_return_rate) })] }), data.goal_progress !== null && (_jsxs("div", { children: [_jsx("span", { style: { fontSize: '0.75rem', color: '#666' }, children: "목표 달성률" }), _jsxs("div", { style: { fontSize: '1.1rem', fontWeight: 600, color: data.goal_progress >= 100 ? '#2e7d32' : '#1565c0' }, children: [data.goal_progress.toFixed(1), "%"] })] })), _jsxs("div", { children: [_jsx("span", { style: { fontSize: '0.75rem', color: '#666' }, children: "조회수" }), _jsx("div", { style: { fontSize: '1rem', fontWeight: 600 }, children: data.view_count.toLocaleString() })] })] })] }), _jsxs("div", { style: { marginBottom: '1.5rem' }, children: [_jsx("button", { "data-testid": "like-btn", onClick: () => void handleLike(), disabled: likeLoading, style: {
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.4rem',
                            padding: '0.45rem 1rem',
                            background: liked ? '#e91e63' : '#fff',
                            border: '1px solid #e91e63',
                            color: liked ? '#fff' : '#e91e63',
                            borderRadius: '20px',
                            cursor: likeLoading ? 'default' : 'pointer',
                            fontSize: '0.875rem',
                            fontWeight: 600,
                            opacity: likeLoading ? 0.7 : 1,
                        }, children: liked ? '♥ 좋아요 취소' : '♡ 좋아요' }), _jsx("span", { "data-testid": "like-count", style: { marginLeft: '0.5rem', fontSize: '0.875rem', color: '#666' }, children: `${likeCount.toLocaleString()}개` }), likeError && (_jsx("span", { "data-testid": "like-error", style: { marginLeft: '0.75rem', fontSize: '0.8rem', color: '#c62828' }, children: likeError }))] }), _jsxs("div", { children: [_jsx("h3", { style: { margin: '0 0 0.75rem', fontSize: '1rem', color: '#333' }, children: "보유 종목" }), data.holdings.length === 0 ? (_jsx("p", { style: { color: '#666', fontSize: '0.875rem' }, children: "보유 종목 정보가 없습니다." })) : (_jsx("div", { style: { overflowX: 'auto' }, children: _jsxs("table", { style: { width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem', minWidth: '360px' }, children: [_jsx("thead", { children: _jsxs("tr", { style: { background: '#e3f2fd' }, children: [_jsx("th", { style: cellStyle, children: "티커" }), _jsx("th", { style: { ...cellStyle, textAlign: 'right' }, children: "보유 수량" }), _jsx("th", { style: { ...cellStyle, textAlign: 'right' }, children: "매수 단가" })] }) }), _jsx("tbody", { children: data.holdings.map((h) => (_jsxs("tr", { style: { borderBottom: '1px solid #eee' }, children: [_jsx("td", { style: { ...cellStyle, fontWeight: 600 }, children: h.ticker }), _jsx("td", { style: { ...cellStyle, textAlign: 'right' }, children: h.shares.toLocaleString() }), _jsx("td", { style: { ...cellStyle, textAlign: 'right' }, children: h.purchase_price.toLocaleString() })] }, h.ticker))) })] }) }))] }), _jsx("p", { style: { marginTop: '1.5rem', fontSize: '0.75rem', color: '#888' }, children: "이 정보는 참고용이며, 실제 투자 결정은 본인 책임하에 이루어져야 합니다." })] }));
}
