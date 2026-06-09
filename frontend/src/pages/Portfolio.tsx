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
      {/* 성과 요약 */}
      {performance && (
        <div style={{ display: 'flex', gap: '1.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
          <div><span style={{ fontSize: '0.75rem', color: '#666' }}>총 투자금</span><br />
            <strong>₩{performance.total_invested.toLocaleString()}</strong>
          </div>
          <div><span style={{ fontSize: '0.75rem', color: '#666' }}>현재 평가금</span><br />
            <strong>{performance.current_value !== null ? `₩${performance.current_value.toLocaleString()}` : '-'}</strong>
          </div>
          <div><span style={{ fontSize: '0.75rem', color: '#666' }}>수익률</span><br />
            <strong style={{ color: returnColor(performance.total_return_pct) }}>
              {formatPct(performance.total_return_pct)}
            </strong>
          </div>
          <div><span style={{ fontSize: '0.75rem', color: '#666' }}>종목 수</span><br />
            <strong>{performance.holdings_count}</strong>
          </div>
        </div>
      )}

      {/* 보유 종목 테이블 */}
      {holdings.length > 0 ? (
        <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '1rem', fontSize: '0.875rem' }}>
          <thead>
            <tr style={{ background: '#e3f2fd' }}>
              <th style={cellStyle}>종목코드</th>
              <th style={cellStyle}>수량</th>
              <th style={cellStyle}>평균단가</th>
            </tr>
          </thead>
          <tbody>
            {holdings.map((h) => (
              <tr key={h.id} style={{ borderBottom: '1px solid #eee' }}>
                <td style={cellStyle}>{h.krx_code}</td>
                <td style={cellStyle}>{h.quantity.toLocaleString()}</td>
                <td style={cellStyle}>₩{h.avg_buy_price.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
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
