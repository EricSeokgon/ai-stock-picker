// AI 포트폴리오 코멘터리 패널 (SPEC-STOCK-040)
import { useEffect, useState } from 'react';
import { useAuth } from '../auth/AuthContext';

// @MX:NOTE: [AUTO] SPEC-STOCK-040 — AI 코멘터리 패널. GET /portfolios/{id}/ai-commentary 호출.

interface AICommentaryResponse {
  portfolio_id: number;
  commentary: string;
  cached: boolean;
  generated_at: string;
  is_fallback: boolean;
}

interface Props {
  portfolioId: number;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export default function AICommentaryPanel({ portfolioId }: Props) {
  const { token } = useAuth();
  const [data, setData] = useState<AICommentaryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    void loadCommentary();
  }, [portfolioId, token]);

  async function loadCommentary() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `${API_BASE}/portfolios/${portfolioId}/ai-commentary`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (!res.ok) throw new Error(`코멘터리 조회 실패: ${res.status}`);
      setData(await res.json() as AICommentaryResponse);
    } catch (e) {
      setError(e instanceof Error ? e.message : '오류가 발생했습니다');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: '1rem', marginTop: '1rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
        <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>AI 포트폴리오 코멘터리</h3>
        {data?.cached && (
          <span style={{ fontSize: '0.75rem', background: '#f3f4f6', padding: '2px 8px', borderRadius: 9999, color: '#6b7280' }}>
            캐시된 결과
          </span>
        )}
        {data?.is_fallback && (
          <span style={{ fontSize: '0.75rem', background: '#fef3c7', padding: '2px 8px', borderRadius: 9999, color: '#92400e' }}>
            대체 응답
          </span>
        )}
      </div>

      {loading && <p style={{ color: '#6b7280', margin: 0 }}>AI 코멘터리 생성 중...</p>}
      {error && <p style={{ color: '#ef4444', margin: 0 }}>{error}</p>}
      {data && !loading && (
        <>
          <p style={{ margin: 0, lineHeight: 1.7, whiteSpace: 'pre-wrap', fontSize: '0.9rem' }}>
            {data.commentary}
          </p>
          <p style={{ margin: '0.75rem 0 0', fontSize: '0.75rem', color: '#9ca3af' }}>
            분석 기준 시점: {new Date(data.generated_at).toLocaleString('ko-KR')}
          </p>
        </>
      )}
    </div>
  );
}
