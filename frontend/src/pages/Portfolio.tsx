// 포트폴리오 관리 페이지
import { useEffect, useState } from 'react';
import { useAuth } from '../auth/AuthContext';
import {
  apiListPortfolios,
  apiCreatePortfolio,
  apiListHoldings,
  apiAddHolding,
  apiGetPerformance,
  type Portfolio,
  type Holding,
  type PortfolioPerformance,
} from '../api/portfolio';
import { LivePriceBadge } from '../components/LivePriceBadge';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

// 색상 유틸리티
function returnColor(pct: number | null): string {
  if (pct === null) return '#666';
  return pct >= 0 ? '#2e7d32' : '#c62828';
}

function formatPct(pct: number | null): string {
  if (pct === null) return '-';
  return `${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%`;
}

// 포트폴리오 생성 모달
function CreatePortfolioModal({
  onClose,
  onCreate,
}: {
  onClose: () => void;
  onCreate: (name: string, description?: string) => Promise<void>;
}) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await onCreate(name, description || undefined);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : '생성 실패');
    } finally {
      setLoading(false);
    }
  }

  const overlayStyle: React.CSSProperties = {
    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
    display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100,
  };
  const boxStyle: React.CSSProperties = {
    background: '#fff', padding: '1.5rem', borderRadius: '8px',
    width: '360px', boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
  };

  return (
    <div style={overlayStyle} role="dialog" aria-modal="true" aria-label="포트폴리오 생성">
      <div style={boxStyle}>
        <h3 style={{ marginTop: 0 }}>새 포트폴리오 생성</h3>
        {error && <p style={{ color: '#c62828', fontSize: '0.875rem' }}>{error}</p>}
        <form onSubmit={(e) => void handleSubmit(e)}>
          <div style={{ marginBottom: '0.75rem' }}>
            <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.875rem' }}>이름 *</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              style={{ width: '100%', padding: '0.4rem 0.5rem', border: '1px solid #ccc', borderRadius: '4px', boxSizing: 'border-box' }}
            />
          </div>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.875rem' }}>설명 (선택)</label>
            <input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              style={{ width: '100%', padding: '0.4rem 0.5rem', border: '1px solid #ccc', borderRadius: '4px', boxSizing: 'border-box' }}
            />
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
            <button type="button" onClick={onClose} style={{ padding: '0.4rem 0.9rem', border: '1px solid #ccc', borderRadius: '4px', cursor: 'pointer' }}>
              취소
            </button>
            <button type="submit" disabled={loading} style={{ padding: '0.4rem 0.9rem', background: '#1976d2', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
              {loading ? '생성 중...' : '생성'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// AI 분석 결과 타입
interface AiAnalysisResult {
  diversification: string;
  risk: string;
  suggestions: string[];
}

// AI 분석 섹션 컴포넌트 (REQ-FE-005)
function AiAnalysisSection({ portfolioId, token }: { portfolioId: number; token: string }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AiAnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

  async function handleRunAnalysis() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/ai-analysis`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`AI 분석 실패: ${res.status}`);
      const data = await res.json() as AiAnalysisResult;
      setResult(data);
      setExpanded(true);
    } catch {
      setError('AI 분석을 일시적으로 사용할 수 없습니다.');
    } finally {
      setLoading(false);
    }
  }

  const sectionStyle: React.CSSProperties = {
    marginTop: '1rem',
    padding: '0.75rem',
    border: '1px solid #e3f2fd',
    borderRadius: '4px',
    background: '#fafcff',
  };

  return (
    <div style={sectionStyle}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
        <strong style={{ fontSize: '0.875rem' }}>AI 분석</strong>
        <button
          onClick={() => void handleRunAnalysis()}
          disabled={loading}
          style={{
            padding: '0.3rem 0.7rem', background: '#1976d2', color: '#fff',
            border: 'none', borderRadius: '4px', cursor: loading ? 'default' : 'pointer',
            fontSize: '0.8rem', opacity: loading ? 0.7 : 1,
          }}
        >
          {loading ? '분석 중...' : 'AI 분석 실행'}
        </button>
        {result && (
          <button
            onClick={() => setExpanded((v) => !v)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '0.8rem', color: '#666' }}
          >
            {expanded ? '▲ 접기' : '▼ 펼치기'}
          </button>
        )}
      </div>

      {error && (
        <p style={{ color: '#c62828', fontSize: '0.8rem', margin: '0.25rem 0' }}>{error}</p>
      )}

      {result && expanded && (
        <div style={{ fontSize: '0.875rem' }}>
          <div style={{ marginBottom: '0.5rem' }}>
            <strong>분산도:</strong> <span>{result.diversification}</span>
          </div>
          <div style={{ marginBottom: '0.5rem' }}>
            <strong>리스크:</strong> <span>{result.risk}</span>
          </div>
          {result.suggestions && result.suggestions.length > 0 && (
            <div style={{ marginBottom: '0.5rem' }}>
              <strong>개선 제안:</strong>
              <ul style={{ margin: '0.25rem 0 0 1rem', padding: 0 }}>
                {result.suggestions.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </div>
          )}
          <p style={{ fontSize: '0.75rem', color: '#888', marginTop: '0.5rem', marginBottom: 0 }}>
            본 분석은 AI가 생성한 참고 정보입니다. 실제 투자 결정은 본인 책임하에 이루어져야 합니다.
          </p>
        </div>
      )}
    </div>
  );
}

// 포트폴리오 상세 패널 (보유 종목 + 성과)
function PortfolioDetail({ portfolioId, token }: { portfolioId: number; token: string }) {
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [performance, setPerformance] = useState<PortfolioPerformance | null>(null);
  const [loadErr, setLoadErr] = useState<string | null>(null);

  // 종목 추가 폼 상태
  const [krxCode, setKrxCode] = useState('');
  const [quantity, setQuantity] = useState('');
  const [avgBuyPrice, setAvgBuyPrice] = useState('');
  const [addErr, setAddErr] = useState<string | null>(null);
  const [addLoading, setAddLoading] = useState(false);

  async function load() {
    try {
      const [h, p] = await Promise.all([
        apiListHoldings(token, portfolioId),
        apiGetPerformance(token, portfolioId),
      ]);
      setHoldings(h);
      setPerformance(p);
    } catch (err) {
      setLoadErr(err instanceof Error ? err.message : '조회 실패');
    }
  }

  useEffect(() => { void load(); }, [portfolioId, token]);

  async function handleAddHolding(e: React.FormEvent) {
    e.preventDefault();
    setAddErr(null);
    setAddLoading(true);
    try {
      await apiAddHolding(token, portfolioId, krxCode, Number(quantity), Number(avgBuyPrice));
      setKrxCode('');
      setQuantity('');
      setAvgBuyPrice('');
      await load();
    } catch (err) {
      setAddErr(err instanceof Error ? err.message : '추가 실패');
    } finally {
      setAddLoading(false);
    }
  }

  const cellStyle: React.CSSProperties = { padding: '0.4rem 0.6rem', fontSize: '0.875rem' };

  if (loadErr) return <p style={{ color: '#c62828', fontSize: '0.875rem' }}>오류: {loadErr}</p>;

  return (
    <div style={{ padding: '1rem', background: '#f8f9fa', borderRadius: '4px', marginTop: '0.5rem' }}>
      {/* 성과 요약 카드 — 모바일에서 세로 스택 */}
      {performance && (
        <div
          className="portfolio-summary-cards"
          style={{ display: 'flex', gap: '1.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}
        >
          <div style={{ minWidth: '80px' }}>
            <span style={{ fontSize: '0.75rem', color: '#666' }}>총 투자금</span><br />
            <strong>₩{performance.total_invested.toLocaleString()}</strong>
          </div>
          <div style={{ minWidth: '80px' }}>
            <span style={{ fontSize: '0.75rem', color: '#666' }}>현재 평가금</span><br />
            <strong>{performance.current_value !== null ? `₩${performance.current_value.toLocaleString()}` : '-'}</strong>
          </div>
          <div style={{ minWidth: '80px' }}>
            <span style={{ fontSize: '0.75rem', color: '#666' }}>수익률</span><br />
            <strong style={{ color: returnColor(performance.total_return_pct) }}>
              {formatPct(performance.total_return_pct)}
            </strong>
          </div>
          <div style={{ minWidth: '80px' }}>
            <span style={{ fontSize: '0.75rem', color: '#666' }}>종목 수</span><br />
            <strong>{performance.holdings_count}</strong>
          </div>
          <style>{`
            @media (max-width: 767px) {
              .portfolio-summary-cards { flex-direction: column !important; gap: 0.75rem !important; }
            }
          `}</style>
        </div>
      )}

      {/* 보유 종목 테이블 — 모바일에서 overflow-x: auto로 가로 스크롤 */}
      {holdings.length > 0 ? (
        <div style={{ overflowX: 'auto', marginBottom: '1rem', WebkitOverflowScrolling: 'touch' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem', minWidth: '360px' }}>
            <thead>
              <tr style={{ background: '#e3f2fd' }}>
                <th style={cellStyle}>종목코드</th>
                <th style={cellStyle}>수량</th>
                <th style={cellStyle}>평균단가</th>
                <th style={cellStyle}>현재 시세</th>
              </tr>
            </thead>
            <tbody>
              {holdings.map((h) => (
                <tr key={h.id} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={cellStyle}>{h.krx_code}</td>
                  <td style={cellStyle}>{h.quantity.toLocaleString()}</td>
                  <td style={cellStyle}>₩{h.avg_buy_price.toLocaleString()}</td>
                  <td style={cellStyle}><LivePriceBadge krxCode={h.krx_code} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p style={{ fontSize: '0.875rem', color: '#666', marginBottom: '1rem' }}>보유 종목이 없습니다.</p>
      )}

      {/* 종목 추가 폼 */}
      <div>
        <h4 style={{ margin: '0 0 0.5rem', fontSize: '0.875rem' }}>종목 추가</h4>
        {addErr && <p style={{ color: '#c62828', fontSize: '0.8rem', margin: '0 0 0.5rem' }}>{addErr}</p>}
        <form onSubmit={(e) => void handleAddHolding(e)} style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <input placeholder="KRX 코드 (예: 005930)" value={krxCode} onChange={(e) => setKrxCode(e.target.value)} required
            style={{ flex: '1 1 100px', padding: '0.35rem 0.5rem', border: '1px solid #ccc', borderRadius: '4px', fontSize: '0.875rem' }} />
          <input placeholder="수량" type="number" min="1" value={quantity} onChange={(e) => setQuantity(e.target.value)} required
            style={{ flex: '1 1 80px', padding: '0.35rem 0.5rem', border: '1px solid #ccc', borderRadius: '4px', fontSize: '0.875rem' }} />
          <input placeholder="평균단가 (원)" type="number" min="1" value={avgBuyPrice} onChange={(e) => setAvgBuyPrice(e.target.value)} required
            style={{ flex: '1 1 100px', padding: '0.35rem 0.5rem', border: '1px solid #ccc', borderRadius: '4px', fontSize: '0.875rem' }} />
          <button type="submit" disabled={addLoading}
            style={{ padding: '0.35rem 0.75rem', background: '#388e3c', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '0.875rem' }}>
            {addLoading ? '추가 중...' : '추가'}
          </button>
        </form>
      </div>

      {/* AI 분석 섹션 (REQ-FE-005) */}
      <AiAnalysisSection portfolioId={portfolioId} token={token} />
    </div>
  );
}

export default function Portfolio() {
  const { token } = useAuth();
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  async function loadPortfolios() {
    if (!token) return;
    try {
      const list = await apiListPortfolios(token);
      setPortfolios(list);
    } catch (err) {
      setError(err instanceof Error ? err.message : '조회 실패');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void loadPortfolios(); }, [token]);

  async function handleCreate(name: string, description?: string) {
    if (!token) return;
    await apiCreatePortfolio(token, name, description);
    await loadPortfolios();
    setShowModal(false);
  }

  if (!token) return <p>로그인이 필요합니다.</p>;

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
        <h2 style={{ margin: 0, color: '#0d47a1' }}>내 포트폴리오</h2>
        <button
          onClick={() => setShowModal(true)}
          style={{ padding: '0.4rem 0.9rem', background: '#1976d2', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
        >
          + 새 포트폴리오
        </button>
      </div>

      {loading && <p style={{ color: '#666' }}>불러오는 중...</p>}
      {error && <p style={{ color: '#c62828' }}>오류: {error}</p>}

      {!loading && portfolios.length === 0 && (
        <p style={{ color: '#666' }}>아직 포트폴리오가 없습니다. 새 포트폴리오를 만들어 보세요.</p>
      )}

      {portfolios.map((p) => (
        <div key={p.id} style={{ border: '1px solid #ddd', borderRadius: '6px', marginBottom: '1rem', overflow: 'hidden' }}>
          <div
            style={{
              padding: '0.75rem 1rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              cursor: 'pointer', background: expandedId === p.id ? '#e3f2fd' : '#fff',
            }}
            onClick={() => setExpandedId(expandedId === p.id ? null : p.id)}
            role="button"
            aria-expanded={expandedId === p.id}
          >
            <div>
              <strong>{p.name}</strong>
              {p.description && <span style={{ marginLeft: '0.5rem', fontSize: '0.875rem', color: '#666' }}>{p.description}</span>}
            </div>
            <span style={{ fontSize: '0.8rem', color: '#666' }}>{expandedId === p.id ? '▲' : '▼'}</span>
          </div>

          {expandedId === p.id && <PortfolioDetail portfolioId={p.id} token={token} />}
        </div>
      ))}

      {showModal && (
        <CreatePortfolioModal
          onClose={() => setShowModal(false)}
          onCreate={handleCreate}
        />
      )}
    </div>
  );
}
