// 포트폴리오 공유 패널 (SPEC-STOCK-042)
import { useEffect, useState } from 'react';
import { useAuth } from '../auth/AuthContext';
import {
  apiCreateShare,
  apiDeleteShare,
  apiGetShare,
  getShareStats,
  type ShareResponse,
  type ShareViewStatItem,
} from '../api/portfolio';

interface SharePanelProps {
  portfolioId: number;
}

// @MX:NOTE: [AUTO] SharePanel — 포트폴리오 공유 링크 생성/삭제/복사 UI (SPEC-STOCK-042)
export default function SharePanel({ portfolioId }: SharePanelProps) {
  const { token } = useAuth();
  const [shareData, setShareData] = useState<ShareResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [stats, setStats] = useState<ShareViewStatItem[]>([]);
  const [statsError, setStatsError] = useState<string | null>(null);

  // 마운트 시 현재 공유 상태 조회
  useEffect(() => {
    if (!token) return;
    setLoading(true);
    apiGetShare(token, portfolioId)
      .then(setShareData)
      .catch(() => setShareData(null))
      .finally(() => setLoading(false));
  }, [token, portfolioId]);

  // 공유 데이터 존재 시 7일 조회 통계 조회
  useEffect(() => {
    if (!token || !shareData) return;
    setStatsError(null);
    getShareStats(token, portfolioId)
      .then((res) => setStats(res.stats))
      .catch(() => setStatsError('통계 조회 실패'));
  }, [token, portfolioId, shareData]);

  // 공유 링크 생성
  async function handleCreate() {
    if (!token) return;
    setActionLoading(true);
    setError(null);
    try {
      const data = await apiCreateShare(token, portfolioId);
      setShareData(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : '공유 링크 생성 실패');
    } finally {
      setActionLoading(false);
    }
  }

  // 공유 비활성화
  async function handleDelete() {
    if (!token) return;
    setActionLoading(true);
    setError(null);
    try {
      await apiDeleteShare(token, portfolioId);
      setShareData(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : '공유 비활성화 실패');
    } finally {
      setActionLoading(false);
    }
  }

  // 클립보드 복사
  function handleCopy() {
    if (!shareData) return;
    const fullUrl = `${window.location.origin}${shareData.share_url}`;
    navigator.clipboard.writeText(fullUrl).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }).catch(() => {
      setError('클립보드 복사에 실패했습니다.');
    });
  }

  const sectionStyle: React.CSSProperties = {
    marginTop: '1rem',
    padding: '0.75rem',
    border: '1px solid #e3f2fd',
    borderRadius: '4px',
    background: '#f0f7ff',
  };

  const btnStyle = (color: string): React.CSSProperties => ({
    padding: '0.3rem 0.7rem',
    background: color,
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    cursor: actionLoading ? 'default' : 'pointer',
    fontSize: '0.8rem',
    opacity: actionLoading ? 0.7 : 1,
  });

  return (
    <div style={sectionStyle}>
      <strong style={{ fontSize: '0.875rem' }}>포트폴리오 공유</strong>

      {loading && (
        <p style={{ fontSize: '0.8rem', color: '#666', margin: '0.5rem 0' }}>로딩 중...</p>
      )}

      {error && (
        <p style={{ color: '#c62828', fontSize: '0.8rem', margin: '0.5rem 0' }}>{error}</p>
      )}

      {!loading && !shareData && (
        <div style={{ marginTop: '0.5rem' }}>
          <p style={{ fontSize: '0.8rem', color: '#555', margin: '0 0 0.5rem' }}>
            공유 링크가 없습니다. 링크를 생성하면 누구나 이 포트폴리오를 볼 수 있습니다.
          </p>
          <button
            onClick={() => void handleCreate()}
            disabled={actionLoading}
            style={btnStyle('#1976d2')}
          >
            {actionLoading ? '생성 중...' : '공유 링크 생성'}
          </button>
        </div>
      )}

      {!loading && shareData && (
        <div style={{ marginTop: '0.5rem' }}>
          {/* 공유 통계 (누적) */}
          <div style={{ display: 'flex', gap: '1rem', marginBottom: '0.5rem', fontSize: '0.8rem', color: '#555' }}>
            <span>조회수: <strong>{shareData.view_count}</strong></span>
            <span>좋아요: <strong>{shareData.like_count}</strong></span>
          </div>

          {/* 7일 일별 조회 통계 */}
          {statsError && (
            <p data-testid="stats-error" style={{ color: '#c62828', fontSize: '0.75rem', margin: '0.25rem 0' }}>
              {statsError}
            </p>
          )}
          {stats.length > 0 && (
            <div style={{ marginBottom: '0.5rem' }}>
              <p style={{ fontSize: '0.75rem', color: '#555', margin: '0 0 0.25rem' }}>일별 조회수 (최근 7일)</p>
              {stats.map((s) => (
                <div
                  key={s.date}
                  data-testid="stat-item"
                  style={{ display: 'flex', gap: '0.5rem', fontSize: '0.75rem', color: '#555' }}
                >
                  <span>{s.date}</span>
                  <span>{s.view_count}</span>
                </div>
              ))}
            </div>
          )}

          {/* 링크 표시 */}
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap', marginBottom: '0.5rem' }}>
            <input
              readOnly
              value={`${window.location.origin}${shareData.share_url}`}
              style={{
                flex: '1 1 200px',
                padding: '0.3rem 0.5rem',
                border: '1px solid #ccc',
                borderRadius: '4px',
                fontSize: '0.8rem',
                background: '#fff',
              }}
              onClick={(e) => (e.target as HTMLInputElement).select()}
            />
            <button onClick={handleCopy} style={btnStyle('#388e3c')}>
              {copied ? '복사됨!' : '링크 복사'}
            </button>
          </div>

          {/* 공유 비활성화 */}
          <button
            onClick={() => void handleDelete()}
            disabled={actionLoading}
            style={{
              ...btnStyle('#c62828'),
              background: 'none',
              color: '#c62828',
              border: '1px solid #c62828',
            }}
          >
            {actionLoading ? '처리 중...' : '공유 비활성화'}
          </button>
        </div>
      )}
    </div>
  );
}
