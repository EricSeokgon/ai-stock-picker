// 관심 목록 관리 페이지 (REQ-FE-003)
// - 관심 목록 종목 표시 + LivePriceBadge
// - 삭제 버튼(✕)
// - 미인증 시 /login 리다이렉트
// - 빈 목록 안내 메시지

import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { getWatchlist, removeFromWatchlist, type WatchlistItem } from '../api/watchlist';
import { LivePriceBadge } from '../components/LivePriceBadge';

export default function Watchlist() {
  const { isAuthenticated, token } = useAuth();
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 미인증 시 로그인 페이지로 이동
  if (!isAuthenticated || !token) {
    return <Navigate to="/login" replace />;
  }

  async function loadWatchlist() {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getWatchlist(token);
      setItems(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '관심 목록 조회 실패');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadWatchlist();
  }, [token]);

  async function handleRemove(krxCode: string) {
    if (!token) return;
    try {
      await removeFromWatchlist(token, krxCode);
      setItems((prev) => prev.filter((item) => item.krx_code !== krxCode));
    } catch (err) {
      setError(err instanceof Error ? err.message : '삭제 실패');
    }
  }

  const rowStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0.6rem 0.8rem',
    borderBottom: '1px solid #eee',
    gap: '1rem',
  };

  return (
    <div>
      <h2 style={{ color: '#0d47a1', marginBottom: '1.5rem' }}>관심 목록</h2>

      {loading && <p style={{ color: '#666' }}>불러오는 중...</p>}

      {error && (
        <p style={{ color: '#c62828', fontSize: '0.875rem' }}>오류: {error}</p>
      )}

      {!loading && items.length === 0 && (
        <p style={{ color: '#666', fontSize: '0.9rem' }}>
          관심 목록이 없습니다. 추천 종목에서 별표를 눌러 추가하세요.
        </p>
      )}

      {items.length > 0 && (
        <div style={{ border: '1px solid #ddd', borderRadius: '6px', overflow: 'hidden' }}>
          {items.map((item) => (
            <div key={item.id} style={rowStyle}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flex: 1 }}>
                <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>{item.krx_code}</span>
                <LivePriceBadge krxCode={item.krx_code} />
              </div>
              <button
                onClick={() => void handleRemove(item.krx_code)}
                aria-label={`${item.krx_code} 관심 목록에서 삭제`}
                style={{
                  background: 'none',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  padding: '0.2rem 0.5rem',
                  fontSize: '0.85rem',
                  color: '#666',
                }}
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
