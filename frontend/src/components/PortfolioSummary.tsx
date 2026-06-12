// 포트폴리오 요약 위젯 — 대시보드에서 사용
import { useEffect, useState } from 'react';
import { useAuth } from '../auth/AuthContext';
import { apiListPortfolios, apiGetPerformance, type Portfolio, type PortfolioPerformance } from '../api/portfolio';

export function PortfolioSummary() {
  const { token, isAuthenticated } = useAuth();
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [performance, setPerformance] = useState<PortfolioPerformance | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isAuthenticated || !token) return;
    setLoading(true);

    apiListPortfolios(token)
      .then(async (list) => {
        if (list.length === 0) return;
        const latest = list[list.length - 1];
        setPortfolio(latest);
        const perf = await apiGetPerformance(token, latest.id);
        setPerformance(perf);
      })
      .catch(() => { /* 조용히 실패 — 위젯은 보조 정보 */ })
      .finally(() => setLoading(false));
  }, [isAuthenticated, token]);

  const containerStyle: React.CSSProperties = {
    padding: '1rem',
    border: '1px solid #ddd',
    borderRadius: '6px',
    background: '#fff',
    fontSize: '0.875rem',
  };

  if (!isAuthenticated) {
    return (
      <div style={containerStyle}>
        <p style={{ margin: 0, color: '#666' }}>로그인이 필요합니다</p>
      </div>
    );
  }

  if (loading) {
    return <div style={containerStyle}><p style={{ margin: 0, color: '#666' }}>포트폴리오 로딩 중...</p></div>;
  }

  if (!portfolio || !performance) {
    return <div style={containerStyle}><p style={{ margin: 0, color: '#666' }}>포트폴리오 없음</p></div>;
  }

  const pct = performance.total_return_pct;
  const pctColor = pct === null ? '#666' : pct >= 0 ? '#2e7d32' : '#c62828';
  const pctText = pct === null ? '-' : `${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%`;

  return (
    <div style={containerStyle}>
      <div style={{ fontWeight: 700, marginBottom: '0.4rem', color: '#0d47a1' }}>{portfolio.name}</div>
      <div style={{ display: 'flex', gap: '1rem' }}>
        <div>
          <span style={{ color: '#666' }}>수익률 </span>
          <strong style={{ color: pctColor }}>{pctText}</strong>
        </div>
        <div>
          <span style={{ color: '#666' }}>종목 수 </span>
          <strong>{performance.holdings.length}</strong>
        </div>
      </div>
    </div>
  );
}
