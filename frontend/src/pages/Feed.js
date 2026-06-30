import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// 공개 포트폴리오 피드 페이지 (SPEC-STOCK-042, 인증 불필요)
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getFeed } from '../api/feed';
// 수익률 색상 유틸리티
function rateColor(rate) {
    return rate >= 0 ? '#2e7d32' : '#c62828';
}
function formatRate(rate) {
    return `${rate >= 0 ? '+' : ''}${rate.toFixed(2)}%`;
}
// @MX:NOTE: [AUTO] Feed 페이지 — 공개 포트폴리오 피드, 좋아요순/최신순 정렬 (SPEC-STOCK-042)
export default function Feed() {
    const navigate = useNavigate();
    const [items, setItems] = useState([]);
    const [sort, setSort] = useState('likes');
    const [page, setPage] = useState(1);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const PAGE_SIZE = 20;
    // 정렬 변경 시 1페이지로 리셋
    useEffect(() => {
        setPage(1);
        setItems([]);
    }, [sort]);
    // 페이지 또는 정렬 변경 시 데이터 조회
    useEffect(() => {
        setLoading(true);
        setError(null);
        getFeed(sort, page, PAGE_SIZE)
            .then((data) => {
            setItems(data.items);
            setTotal(data.total);
        })
            .catch((e) => {
            setError(e instanceof Error ? e.message : '피드 조회에 실패했습니다.');
        })
            .finally(() => setLoading(false));
    }, [sort, page]);
    const totalPages = Math.ceil(total / PAGE_SIZE);
    const sortBtnStyle = (active) => ({
        padding: '0.35rem 0.8rem',
        border: `1px solid ${active ? '#1976d2' : '#ccc'}`,
        background: active ? '#1976d2' : '#fff',
        color: active ? '#fff' : '#333',
        borderRadius: '4px',
        cursor: 'pointer',
        fontSize: '0.875rem',
        fontWeight: active ? 600 : 400,
    });
    return (_jsxs("div", { children: [_jsxs("div", { style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '0.5rem' }, children: [_jsx("h2", { style: { margin: 0, color: '#0d47a1' }, children: "\uD3EC\uD2B8\uD3F4\uB9AC\uC624 \uD53C\uB4DC" }), _jsxs("div", { style: { display: 'flex', gap: '0.5rem' }, children: [_jsx("button", { style: sortBtnStyle(sort === 'likes'), onClick: () => setSort('likes'), children: "\uC88B\uC544\uC694\uC21C" }), _jsx("button", { style: sortBtnStyle(sort === 'recent'), onClick: () => setSort('recent'), children: "\uCD5C\uC2E0\uC21C" })] })] }), error && (_jsx("div", { role: "alert", style: {
                    padding: '0.75rem 1rem',
                    background: '#ffebee',
                    border: '1px solid #ef9a9a',
                    borderRadius: '4px',
                    color: '#c62828',
                    marginBottom: '1rem',
                }, children: error })), loading && (_jsx("div", { role: "status", "aria-live": "polite", style: { textAlign: 'center', padding: '2rem', color: '#666' }, children: "\uB85C\uB529 \uC911..." })), !loading && items.length === 0 && !error && (_jsx("p", { style: { color: '#666', textAlign: 'center', padding: '2rem' }, children: "\uACF5\uC720\uB41C \uD3EC\uD2B8\uD3F4\uB9AC\uC624\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4." })), _jsx("div", { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }, children: items.map((item) => (_jsxs("div", { onClick: () => void navigate(`/shared/${item.share_token}`), role: "button", tabIndex: 0, onKeyDown: (e) => { if (e.key === 'Enter' || e.key === ' ')
                        void navigate(`/shared/${item.share_token}`); }, style: {
                        padding: '1rem',
                        border: '1px solid #e0e0e0',
                        borderRadius: '8px',
                        background: '#fff',
                        cursor: 'pointer',
                        transition: 'box-shadow 0.15s',
                    }, onMouseEnter: (e) => { e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.12)'; }, onMouseLeave: (e) => { e.currentTarget.style.boxShadow = 'none'; }, children: [_jsx("div", { style: { fontWeight: 700, fontSize: '1rem', marginBottom: '0.5rem', color: '#0d47a1' }, children: item.portfolio_name }), _jsx("div", { style: { fontSize: '1.25rem', fontWeight: 700, color: rateColor(item.total_return_rate), marginBottom: '0.5rem' }, children: formatRate(item.total_return_rate) }), _jsxs("div", { style: { display: 'flex', gap: '1rem', fontSize: '0.8rem', color: '#666' }, children: [_jsxs("span", { children: ["\uC870\uD68C ", item.view_count.toLocaleString()] }), _jsxs("span", { children: ["\uC88B\uC544\uC694 ", item.like_count.toLocaleString()] })] }), _jsx("div", { style: { fontSize: '0.75rem', color: '#aaa', marginTop: '0.5rem' }, children: new Date(item.shared_at).toLocaleDateString('ko-KR') })] }, item.share_token))) }), totalPages > 1 && (_jsxs("div", { style: { display: 'flex', justifyContent: 'center', gap: '0.5rem', flexWrap: 'wrap' }, children: [_jsx("button", { onClick: () => setPage((p) => Math.max(1, p - 1)), disabled: page === 1 || loading, style: {
                            padding: '0.35rem 0.75rem',
                            border: '1px solid #ccc',
                            borderRadius: '4px',
                            cursor: page === 1 ? 'default' : 'pointer',
                            background: '#fff',
                            opacity: page === 1 ? 0.5 : 1,
                        }, children: "\uC774\uC804" }), Array.from({ length: Math.min(totalPages, 10) }, (_, i) => i + 1).map((p) => (_jsx("button", { onClick: () => setPage(p), style: {
                            padding: '0.35rem 0.65rem',
                            border: `1px solid ${p === page ? '#1976d2' : '#ccc'}`,
                            borderRadius: '4px',
                            cursor: 'pointer',
                            background: p === page ? '#1976d2' : '#fff',
                            color: p === page ? '#fff' : '#333',
                            fontWeight: p === page ? 700 : 400,
                        }, children: p }, p))), _jsx("button", { onClick: () => setPage((p) => Math.min(totalPages, p + 1)), disabled: page === totalPages || loading, style: {
                            padding: '0.35rem 0.75rem',
                            border: '1px solid #ccc',
                            borderRadius: '4px',
                            cursor: page === totalPages ? 'default' : 'pointer',
                            background: '#fff',
                            opacity: page === totalPages ? 0.5 : 1,
                        }, children: "\uB2E4\uC74C" })] }))] }));
}
