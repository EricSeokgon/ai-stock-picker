// 뉴스 피드 컴포넌트
import type { NewsItem } from '../types';

interface NewsFeedProps {
  news: NewsItem[];
}

// 감성 배지 색상
function getSentimentStyle(sentiment: string | null): { backgroundColor: string; color: string; label: string } {
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
function formatDate(iso: string): string {
  try {
    const date = new Date(iso);
    return date.toLocaleString('ko-KR', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

function NewsCard({ item }: { item: NewsItem }) {
  const sentiment = getSentimentStyle(item.sentiment);

  return (
    <li
      style={{
        listStyle: 'none',
        border: '1px solid #ddd',
        borderRadius: '8px',
        padding: '1rem 1.25rem',
        backgroundColor: '#fff',
        boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem', marginBottom: '0.5rem' }}>
        {/* 감성 배지 */}
        <span
          style={{
            display: 'inline-block',
            padding: '2px 8px',
            borderRadius: '12px',
            fontSize: '0.75rem',
            fontWeight: 600,
            backgroundColor: sentiment.backgroundColor,
            color: sentiment.color,
            flexShrink: 0,
          }}
          aria-label={`감성: ${sentiment.label}`}
        >
          {sentiment.label}
        </span>

        {/* 제목 링크 */}
        <a
          href={item.url}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            fontWeight: 600,
            fontSize: '0.95rem',
            color: '#1565c0',
            textDecoration: 'none',
            lineHeight: 1.4,
          }}
        >
          {item.title}
        </a>
      </div>

      {/* 요약 */}
      {item.summary && (
        <p
          style={{
            margin: '0 0 0.5rem 0',
            fontSize: '0.875rem',
            color: '#555',
            lineHeight: 1.6,
          }}
        >
          {item.summary}
        </p>
      )}

      {/* 출처와 시간 */}
      <div style={{ display: 'flex', gap: '1rem', fontSize: '0.75rem', color: '#888' }}>
        <span>{item.source}</span>
        <time dateTime={item.published_at}>{formatDate(item.published_at)}</time>
      </div>
    </li>
  );
}

export function NewsFeed({ news }: NewsFeedProps) {
  return (
    <section aria-labelledby="news-heading">
      <h2
        id="news-heading"
        style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '1rem', color: '#212121' }}
      >
        최신 뉴스
      </h2>
      {news.length === 0 ? (
        <p style={{ color: '#888', fontSize: '0.875rem' }}>표시할 뉴스가 없습니다.</p>
      ) : (
        <ul
          style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', padding: 0, margin: 0 }}
          aria-label="뉴스 목록"
        >
          {news.map((item, idx) => (
            <NewsCard key={`${item.url}-${idx}`} item={item} />
          ))}
        </ul>
      )}
    </section>
  );
}
