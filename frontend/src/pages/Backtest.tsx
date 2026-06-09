// 백테스트 페이지 — 전략 실행 및 결과 시각화
import { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { useAuth } from '../auth/AuthContext';
import {
  apiRunBacktest,
  apiListBacktestRuns,
  apiGetBacktestResults,
  type BacktestRun,
  type BacktestDailyResult,
  type BacktestStrategy,
} from '../api/backtest';

// 상태 배지 색상
function statusColor(status: BacktestRun['status']): string {
  switch (status) {
    case 'done': return '#2e7d32';
    case 'running': return '#f57c00';
    case 'pending': return '#1565c0';
    case 'failed': return '#c62828';
  }
}

function statusLabel(status: BacktestRun['status']): string {
  switch (status) {
    case 'done': return '완료';
    case 'running': return '실행 중';
    case 'pending': return '대기';
    case 'failed': return '실패';
  }
}

function fmtPct(v: number | null): string {
  if (v === null) return '-';
  return `${(v * 100).toFixed(2)}%`;
}

function fmtNum(v: number | null, digits = 3): string {
  if (v === null) return '-';
  return v.toFixed(digits);
}

// 백테스트 상세 패널 (지표 + 차트)
function BacktestDetail({ run, token }: { run: BacktestRun; token: string }) {
  const [results, setResults] = useState<BacktestDailyResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (run.status !== 'done') { setLoading(false); return; }
    apiGetBacktestResults(token, run.id)
      .then(setResults)
      .catch((err) => setError(err instanceof Error ? err.message : '결과 조회 실패'))
      .finally(() => setLoading(false));
  }, [run.id, run.status, token]);

  const panelStyle: React.CSSProperties = {
    padding: '1rem', background: '#f8f9fa', borderTop: '1px solid #ddd',
  };

  const metricRowStyle: React.CSSProperties = {
    display: 'flex', gap: '1.5rem', flexWrap: 'wrap', marginBottom: '1rem',
  };

  const metricStyle: React.CSSProperties = { fontSize: '0.875rem' };

  return (
    <div style={panelStyle}>
      {/* 핵심 지표 */}
      <div style={metricRowStyle}>
        <div style={metricStyle}><span style={{ color: '#666' }}>CAGR </span><strong>{fmtPct(run.cagr)}</strong></div>
        <div style={metricStyle}><span style={{ color: '#666' }}>최대 낙폭 </span><strong>{fmtPct(run.max_drawdown)}</strong></div>
        <div style={metricStyle}><span style={{ color: '#666' }}>샤프 비율 </span><strong>{fmtNum(run.sharpe_ratio)}</strong></div>
        <div style={metricStyle}><span style={{ color: '#666' }}>총 수익률 </span><strong>{fmtPct(run.total_return)}</strong></div>
      </div>

      {/* 차트 */}
      {run.status !== 'done' ? (
        <p style={{ color: '#666', fontSize: '0.875rem' }}>실행이 완료된 후 차트가 표시됩니다.</p>
      ) : loading ? (
        <p style={{ color: '#666', fontSize: '0.875rem' }}>결과 로딩 중...</p>
      ) : error ? (
        <p style={{ color: '#c62828', fontSize: '0.875rem' }}>{error}</p>
      ) : results.length === 0 ? (
        <p style={{ color: '#666', fontSize: '0.875rem' }}>결과 데이터가 없습니다.</p>
      ) : (
        <div style={{ width: '100%', height: 280 }}>
          <ResponsiveContainer>
            <LineChart data={results} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} tickCount={6} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => v.toFixed(0)} />
              <Tooltip formatter={(v: number) => v.toFixed(2)} />
              <Legend />
              <Line
                type="monotone"
                dataKey="portfolio_value"
                stroke="#1976d2"
                dot={false}
                name="전략 포트폴리오"
              />
              <Line
                type="monotone"
                dataKey="benchmark_value"
                stroke="#f57c00"
                dot={false}
                name="벤치마크"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

export default function Backtest() {
  const { token } = useAuth();
  const [runs, setRuns] = useState<BacktestRun[]>([]);
  const [loadingList, setLoadingList] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  // 실행 폼 상태
  const [strategy, setStrategy] = useState<BacktestStrategy>('momentum');
  const [startDate, setStartDate] = useState('2023-01-01');
  const [endDate, setEndDate] = useState('2024-01-01');
  const [universeSize, setUniverseSize] = useState('100');
  const [topN, setTopN] = useState('10');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  async function loadRuns() {
    if (!token) return;
    try {
      const list = await apiListBacktestRuns(token);
      setRuns(list);
    } catch (err) {
      setListError(err instanceof Error ? err.message : '목록 조회 실패');
    } finally {
      setLoadingList(false);
    }
  }

  useEffect(() => { void loadRuns(); }, [token]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      await apiRunBacktest(token, {
        strategy,
        start_date: startDate,
        end_date: endDate,
        universe_size: Number(universeSize),
        top_n: Number(topN),
      });
      await loadRuns();
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : '실행 실패');
    } finally {
      setSubmitting(false);
    }
  }

  if (!token) return <p>로그인이 필요합니다.</p>;

  const inputStyle: React.CSSProperties = {
    padding: '0.35rem 0.5rem', border: '1px solid #ccc', borderRadius: '4px',
    fontSize: '0.875rem',
  };

  const labelStyle: React.CSSProperties = { fontSize: '0.875rem', color: '#333' };

  return (
    <div>
      <h2 style={{ color: '#0d47a1', marginBottom: '1.5rem' }}>백테스트</h2>

      {/* 실행 폼 */}
      <div style={{ border: '1px solid #ddd', borderRadius: '6px', padding: '1rem', marginBottom: '2rem', background: '#fff' }}>
        <h3 style={{ margin: '0 0 1rem', fontSize: '1rem' }}>새 백테스트 실행</h3>
        {submitError && <p style={{ color: '#c62828', fontSize: '0.875rem' }}>{submitError}</p>}
        <form onSubmit={(e) => void handleSubmit(e)} style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'flex-end' }}>
          <div>
            <label style={labelStyle}>전략<br />
              <select value={strategy} onChange={(e) => setStrategy(e.target.value as BacktestStrategy)} style={inputStyle}>
                <option value="momentum">모멘텀</option>
                <option value="volume">거래량</option>
              </select>
            </label>
          </div>
          <div>
            <label style={labelStyle}>시작일<br />
              <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} required style={inputStyle} />
            </label>
          </div>
          <div>
            <label style={labelStyle}>종료일<br />
              <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} required style={inputStyle} />
            </label>
          </div>
          <div>
            <label style={labelStyle}>유니버스 크기<br />
              <input type="number" min="1" value={universeSize} onChange={(e) => setUniverseSize(e.target.value)} style={{ ...inputStyle, width: '80px' }} />
            </label>
          </div>
          <div>
            <label style={labelStyle}>상위 N종목<br />
              <input type="number" min="1" value={topN} onChange={(e) => setTopN(e.target.value)} style={{ ...inputStyle, width: '70px' }} />
            </label>
          </div>
          <button type="submit" disabled={submitting}
            style={{ padding: '0.4rem 1rem', background: '#1976d2', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '0.875rem' }}>
            {submitting ? '실행 중...' : '실행'}
          </button>
        </form>
      </div>

      {/* 실행 목록 */}
      <h3 style={{ fontSize: '1rem', marginBottom: '0.75rem' }}>실행 이력</h3>
      {loadingList && <p style={{ color: '#666' }}>불러오는 중...</p>}
      {listError && <p style={{ color: '#c62828' }}>오류: {listError}</p>}
      {!loadingList && runs.length === 0 && <p style={{ color: '#666' }}>아직 실행된 백테스트가 없습니다.</p>}

      {runs.map((run) => (
        <div key={run.id} style={{ border: '1px solid #ddd', borderRadius: '6px', marginBottom: '0.75rem', overflow: 'hidden' }}>
          <div
            style={{
              padding: '0.75rem 1rem', display: 'flex', alignItems: 'center',
              justifyContent: 'space-between', cursor: 'pointer',
              background: expandedId === run.id ? '#e3f2fd' : '#fff',
            }}
            onClick={() => setExpandedId(expandedId === run.id ? null : run.id)}
            role="button"
            aria-expanded={expandedId === run.id}
          >
            <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
              <span style={{ fontWeight: 600 }}>#{run.id} — {run.strategy === 'momentum' ? '모멘텀' : '거래량'}</span>
              <span style={{ fontSize: '0.8rem', color: '#666' }}>{run.start_date} ~ {run.end_date}</span>
              <span style={{
                padding: '0.15rem 0.5rem', borderRadius: '12px', fontSize: '0.75rem',
                background: statusColor(run.status) + '20', color: statusColor(run.status), fontWeight: 600,
              }}>
                {statusLabel(run.status)}
              </span>
            </div>
            <span style={{ fontSize: '0.8rem', color: '#666' }}>{expandedId === run.id ? '▲' : '▼'}</span>
          </div>
          {expandedId === run.id && <BacktestDetail run={run} token={token} />}
        </div>
      ))}
    </div>
  );
}
