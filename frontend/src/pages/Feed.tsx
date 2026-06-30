// 공개 포트폴리오 피드 페이지 (SPEC-STOCK-042, 인증 불필요)
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getFeed, type FeedItem } from '../api/feed';

// 수익률 색상 유틸리티
function rateColor(rate: number): string {
  return rate >= 0 ? '#2e7d32' : '#c62828';
}

function formatRate(rate: number): string {
  return `${rate >= 0 ? '+' : ''}${rate.toFixed(2)}%`;
}

// @MX:NOTE: [AUTO] Feed 페이지 — 공개 포트폴리오 피드, 좋아요순/최신순 정렬 (SPEC-STOCK-042)
export default function Feed() {
  const navigate = useNavigate();
  const [items, setItems] = useState<FeedItem[]>([]);
  const [sort, setSort] = useState<'likes' | 'recent'>('likes');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : '피드 조회에 실패했습니다.');
      })
      .finally(() => setLoading(false));
  }, [sort, page]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  const sortBtnStyle = (active: boolean): React.CSSProperties => ({
    padding: '0.35rem 0.8rem',
    border: `1px solid ${active ? '#1976d2' : '#ccc'}`,
    background: active ? '#1976d2' : '#fff',
    color: active ? '#fff' : '#333',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '0.875rem',
    fontWeight: active ? 600 : 400,
  });

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '0.5rem' }}>
        <h2 style={{ margin: 0, color: '#0d47a1' }}>포트폴리오 피드</h2>
        {/* 정렬 토글 */}
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button style={sortBtnStyle(sort === 'likes')} onClick={() => setSort('likes')}>
            좋아요순
          </button>
          <button style={sortBtnStyle(sort === 'recent')} onClick={() => setSort('recent')}>
            최신순
          </button>
        </div>
      </div>

      {error && (
        <div
          role="alert"
          style={{
            padding: '0.75rem 1rem',
            background: '#ffebee',
            border: '1px solid #ef9a9a',
            borderRadius: '4px',
            color: '#c62828',
            marginBottom: '1rem',
          }}
        >
          {error}
        </div>
      )}

      {loading && (
        <div role="status" aria-live="polite" style={{ textAlign: 'center', padding: '2rem', color: '#666' }}>
          로딩 중...
        </div>
      )}

      {!loading && items.length === 0 && !error && (
        <p style={{ color: '#666', textAlign: 'center', padding: '2rem' }}>
          공유된 포트폴리오가 없습니다.
        </p>
      )}

      {/* 피드 카드 목록 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
        {items.map((item) => (
          <div
            key={item.share_token}
            onClick={() => void navigate(`/shared/${item.share_token}`)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') void navigate(`/shared/${item.share_token}`); }}
            style={{
              padding: '1rem',
              border: '1px solid #e0e0e0',
              borderRadius: '8px',
              background: '#fff',
              cursor: 'pointer',
              transition: 'box-shadow 0.15s',
            }}
            onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.boxShadow = '0 2px 8px rgba(0,0,0,0.12)'; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.boxShadow = 'none'; }}
          >
            {/* 포트폴리오 이름 */}
            <div style={{ fontWeight: 700, fontSize: '1rem', marginBottom: '0.5rem', color: '#0d47a1' }}>
              {item.portfolio_name}
            </div>

            {/* 수익률 */}
            <div style={{ fontSize: '1.25rem', fontWeight: 700, color: rateColor(item.total_return_rate), marginBottom: '0.5rem' }}>
              {formatRate(item.total_return_rate)}
            </div>

            {/* 조회수 · 좋아요 */}
            <div style={{ display: 'flex', gap: '1rem', fontSize: '0.8rem', color: '#666' }}>
              <span>조회 {item.view_count.toLocaleString()}</span>
              <span>좋아요 {item.like_count.toLocaleString()}</span>
            </div>

            {/* 공유 일시 */}
            <div style={{ fontSize: '0.75rem', color: '#aaa', marginTop: '0.5rem' }}>
              {new Date(item.shared_at).toLocaleDateString('ko-KR')}
            </div>
          </div>
        ))}
      </div>

      {/* 페이지네이션 */}
      {totalPages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1 || loading}
            style={{
              padding: '0.35rem 0.75rem',
              border: '1px solid #ccc',
              borderRadius: '4px',
              cursor: page === 1 ? 'default' : 'pointer',
              background: '#fff',
              opacity: page === 1 ? 0.5 : 1,
            }}
          >
            이전
          </button>
          {Array.from({ length: Math.min(totalPages, 10) }, (_, i) => i + 1).map((p) => (
            <button
              key={p}
              onClick={() => setPage(p)}
              style={{
                padding: '0.35rem 0.65rem',
                border: `1px solid ${p === page ? '#1976d2' : '#ccc'}`,
                borderRadius: '4px',
                cursor: 'pointer',
                background: p === page ? '#1976d2' : '#fff',
                color: p === page ? '#fff' : '#333',
                fontWeight: p === page ? 700 : 400,
              }}
            >
              {p}
            </button>
          ))}
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages || loading}
            style={{
              padding: '0.35rem 0.75rem',
              border: '1px solid #ccc',
              borderRadius: '4px',
              cursor: page === totalPages ? 'default' : 'pointer',
              background: '#fff',
              opacity: page === totalPages ? 0.5 : 1,
            }}
          >
            다음
          </button>
        </div>
      )}
    </div>
  );
}
