import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// 감성 배지 색상
function getSentimentStyle(sentiment) {
    switch (sentiment) {
        case 'positive':
            return { backgroundColor: '#e8f5e9', color: '#2e7d32', label: '긍정' };
        case 'negative':
            return { backgroundColor: '#ffebee', color: '#c62828', label: '부정' };
        default:
            return { backgroundColor: '#f5f5f5', color: '#616161', label: '중립' };
    }
}
// ISO 날짜를 읽기 쉬운 형식으로 변환
function formatDate(iso) {
    try {
        const date = new Date(iso);
        return date.toLocaleString('ko-KR', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    }
    catch {
        return iso;
    }
}
function NewsCard({ item }) {
    const sentiment = getSentimentStyle(item.sentiment);
    return (_jsxs("li", { style: {
            listStyle: 'none',
            border: '1px solid #ddd',
            borderRadius: '8px',
            padding: '1rem 1.25rem',
            backgroundColor: '#fff',
            boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
        }, children: [_jsxs("div", { style: { display: 'flex', alignItems: 'flex-start', gap: '0.75rem', marginBottom: '0.5rem' }, children: [_jsx("span", { style: {
                            display: 'inline-block',
                            padding: '2px 8px',
                            borderRadius: '12px',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            backgroundColor: sentiment.backgroundColor,
                            color: sentiment.color,
                            flexShrink: 0,
                        }, "aria-label": `감성: ${sentiment.label}`, children: sentiment.label }), _jsx("a", { href: item.url, target: "_blank", rel: "noopener noreferrer", style: {
                            fontWeight: 600,
                            fontSize: '0.95rem',
                            color: '#1565c0',
                            textDecoration: 'none',
                            lineHeight: 1.4,
                        }, children: item.title })] }), item.summary && (_jsx("p", { style: {
                    margin: '0 0 0.5rem 0',
                    fontSize: '0.875rem',
                    color: '#555',
                    lineHeight: 1.6,
                }, children: item.summary })), _jsxs("div", { style: { display: 'flex', gap: '1rem', fontSize: '0.75rem', color: '#888' }, children: [_jsx("span", { children: item.source }), _jsx("time", { dateTime: item.published_at, children: formatDate(item.published_at) })] })] }));
}
export function NewsFeed({ news }) {
    return (_jsxs("section", { "aria-labelledby": "news-heading", children: [_jsx("h2", { id: "news-heading", style: { fontSize: '1.25rem', fontWeight: 700, marginBottom: '1rem', color: '#212121' }, children: "\uCD5C\uC2E0 \uB274\uC2A4" }), news.length === 0 ? (_jsx("p", { style: { color: '#888', fontSize: '0.875rem' }, children: "\uD45C\uC2DC\uD560 \uB274\uC2A4\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4." })) : (_jsx("ul", { style: { display: 'flex', flexDirection: 'column', gap: '0.75rem', padding: 0, margin: 0 }, "aria-label": "\uB274\uC2A4 \uBAA9\uB85D", children: news.map((item, idx) => (_jsx(NewsCard, { item: item }, `${item.url}-${idx}`))) }))] }));
}
