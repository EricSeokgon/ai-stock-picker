// 포트폴리오 관리 페이지
import { useCallback, useEffect, useState } from 'react';
import { useAuth } from '../auth/AuthContext';
import {
  apiListPortfolios,
  apiCreatePortfolio,
  apiListHoldings,
  apiAddHolding,
  apiGetPerformance,
  apiOptimizePortfolio,
  type Portfolio,
  type Holding,
  type PortfolioPerformance,
  type OptimizeResult,
  type Market,
  type Currency,
} from '../api/portfolio';
// SPEC-STOCK-039: 시장 상태 폴링 훅 & 배지 컴포넌트
import { useMarketPolling } from '../hooks/useMarketPolling';
import { MarketStatusBadge } from '../components/MarketStatusBadge';
import PortfolioScoreCard from '../components/PortfolioScoreCard';
import RebalancingTable from '../components/RebalancingTable';
import NewStockSuggestions from '../components/NewStockSuggestions';
import RiskAnalysisPanel from '../components/RiskAnalysisPanel';
// @MX:NOTE: [AUTO] BacktestPanel — SPEC-STOCK-029 백테스팅 패널 통합
import BacktestPanel from '../components/BacktestPanel';
// @MX:NOTE: [AUTO] PerformanceSummaryPanel — SPEC-STOCK-030 기간별 성과 요약 패널
import PerformanceSummaryPanel from '../components/PerformanceSummaryPanel';
// @MX:NOTE: [AUTO] PortfolioAlertPanel — SPEC-STOCK-031 포트폴리오 알림 설정 패널
import PortfolioAlertPanel from '../components/PortfolioAlertPanel';
// SPEC-STOCK-033: 배당 수익률 분석 강화 컴포넌트
import DividendSummaryPanel from '../components/DividendSummaryPanel';
import DividendCalendarView from '../components/DividendCalendarView';
import DRIPSimulator from '../components/DRIPSimulator';
import BenchmarkComparisonPanel from '../components/BenchmarkComparisonPanel';
import BenchmarkChartView from '../components/BenchmarkChartView';
import PortfolioReportPanel from '../components/PortfolioReportPanel';
// @MX:NOTE: [AUTO] AICommentaryPanel — SPEC-STOCK-040 AI 포트폴리오 코멘터리 패널
import AICommentaryPanel from '../components/AICommentaryPanel';
// @MX:NOTE: [AUTO] PortfolioGoalPanel — SPEC-STOCK-041 포트폴리오 목표 관리 패널
import PortfolioGoalPanel from '../components/PortfolioGoalPanel';
// @MX:NOTE: [AUTO] HoldingsSyncPanel — SPEC-STOCK-050 거래 기반 홀딩스 동기화 패널
import HoldingsSyncPanel from '../components/HoldingsSyncPanel';
import { getPortfolioDividends, type PortfolioDividends } from '../api/dividends';
import { LivePriceBadge } from '../components/LivePriceBadge';
import { PerformanceDonutChart } from '../components/PerformanceDonutChart';
import {
  fetchRebalanceAdvice,
  fetchRiskProfile,
  fetchMarketBriefing,
  type RebalanceAdvice,
  type RiskProfileAdvice,
  type MarketBriefingAdvice,
} from '../api/advice';

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

// 배당 분석 섹션 컴포넌트 (SPEC-STOCK-019)
function DividendsSection({ portfolioId, token }: { portfolioId: number; token: string }) {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<PortfolioDividends | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showCalendar, setShowCalendar] = useState(false);

  async function handleFetch() {
    setLoading(true);
    setError(null);
    try {
      const result = await getPortfolioDividends(token, portfolioId);
      setData(result);
    } catch {
      setError('배당 데이터를 가져오지 못했습니다. 잠시 후 다시 시도하세요.');
    } finally {
      setLoading(false);
    }
  }

  const sectionStyle: React.CSSProperties = {
    marginTop: '1rem',
    padding: '0.75rem',
    border: '1px solid #e8f5e9',
    borderRadius: '4px',
    background: '#f9fff9',
  };

  const MONTHS = ['1월','2월','3월','4월','5월','6월','7월','8월','9월','10월','11월','12월'];

  return (
    <div style={sectionStyle}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem', flexWrap: 'wrap' }}>
        <strong style={{ fontSize: '0.875rem' }}>배당 분석</strong>
        <button
          onClick={() => void handleFetch()}
          disabled={loading}
          style={{
            padding: '0.3rem 0.7rem', background: '#2e7d32', color: '#fff',
            border: 'none', borderRadius: '4px', cursor: loading ? 'default' : 'pointer',
            fontSize: '0.8rem', opacity: loading ? 0.7 : 1,
          }}
        >
          {loading ? '조회 중...' : '배당 분석 조회'}
        </button>
        {data && (
          <button
            onClick={() => setShowCalendar((v) => !v)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '0.8rem', color: '#666' }}
          >
            {showCalendar ? '▲ 캘린더 닫기' : '▼ 배당 캘린더 보기'}
          </button>
        )}
      </div>

      {error && (
        <p style={{ color: '#c62828', fontSize: '0.8rem', margin: '0.25rem 0' }}>{error}</p>
      )}

      {data && (
        <>
          {/* 요약 카드 */}
          <div style={{ display: 'flex', gap: '1.5rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
            <div>
              <span style={{ fontSize: '0.75rem', color: '#555' }}>연간 배당 수입</span><br />
              <strong style={{ fontSize: '0.95rem', color: '#2e7d32' }}>
                ₩{Math.round(data.total_annual_income).toLocaleString()}
              </strong>
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', color: '#555' }}>가중 평균 배당수익률</span><br />
              <strong style={{ fontSize: '0.95rem' }}>
                {data.weighted_avg_yield > 0 ? `${data.weighted_avg_yield.toFixed(2)}%` : '-'}
              </strong>
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', color: '#555' }}>배당 확인 종목</span><br />
              <strong>{data.coverage_count} / {data.total_holdings}</strong>
            </div>
          </div>

          {/* 종목별 배당 테이블 */}
          {data.holdings.length > 0 && (
            <div style={{ overflowX: 'auto', marginBottom: '0.75rem' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', minWidth: '400px' }}>
                <thead>
                  <tr style={{ background: '#e8f5e9' }}>
                    <th style={{ padding: '0.35rem 0.5rem', textAlign: 'left' }}>종목</th>
                    <th style={{ padding: '0.35rem 0.5rem', textAlign: 'right' }}>DPS(원)</th>
                    <th style={{ padding: '0.35rem 0.5rem', textAlign: 'right' }}>배당수익률</th>
                    <th style={{ padding: '0.35rem 0.5rem', textAlign: 'right' }}>연간 수입</th>
                    <th style={{ padding: '0.35rem 0.5rem', textAlign: 'center' }}>지급월</th>
                  </tr>
                </thead>
                <tbody>
                  {data.holdings.map((h) => (
                    <tr key={h.krx_code} style={{ borderBottom: '1px solid #eee' }}>
                      <td style={{ padding: '0.35rem 0.5rem' }}>
                        <span style={{ fontWeight: 600 }}>{h.krx_code}</span>
                        {h.name && <span style={{ color: '#666', marginLeft: '0.3rem', fontSize: '0.75rem' }}>{h.name}</span>}
                      </td>
                      <td style={{ padding: '0.35rem 0.5rem', textAlign: 'right' }}>
                        {h.dps != null ? h.dps.toLocaleString() : <span style={{ color: '#aaa' }}>-</span>}
                      </td>
                      <td style={{ padding: '0.35rem 0.5rem', textAlign: 'right' }}>
                        {h.dividend_yield != null ? `${h.dividend_yield.toFixed(2)}%` : <span style={{ color: '#aaa' }}>-</span>}
                      </td>
                      <td style={{ padding: '0.35rem 0.5rem', textAlign: 'right', color: '#2e7d32' }}>
                        {h.annual_income > 0 ? `₩${Math.round(h.annual_income).toLocaleString()}` : <span style={{ color: '#aaa' }}>-</span>}
                      </td>
                      <td style={{ padding: '0.35rem 0.5rem', textAlign: 'center' }}>
                        {h.ex_dividend_month != null ? `${h.ex_dividend_month}월` : <span style={{ color: '#aaa' }}>-</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* 12개월 배당 캘린더 그리드 */}
          {showCalendar && (
            <div>
              <h5 style={{ margin: '0 0 0.5rem', fontSize: '0.8rem', color: '#555' }}>배당 캘린더 (지급월 기준)</h5>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.4rem' }}>
                {Array.from({ length: 12 }, (_, i) => i + 1).map((month) => {
                  const entry = data.calendar.find((c) => c.month === month);
                  const hasDiv = entry != null && entry.holdings.length > 0;
                  return (
                    <div
                      key={month}
                      style={{
                        padding: '0.4rem',
                        border: `1px solid ${hasDiv ? '#81c784' : '#e0e0e0'}`,
                        borderRadius: '4px',
                        background: hasDiv ? '#f1f8e9' : '#fafafa',
                        fontSize: '0.75rem',
                      }}
                    >
                      <div style={{ fontWeight: 600, color: hasDiv ? '#2e7d32' : '#999', marginBottom: '0.2rem' }}>
                        {MONTHS[month - 1]}
                      </div>
                      {hasDiv ? (
                        <>
                          <div style={{ color: '#555' }}>{entry.holdings.join(', ')}</div>
                          <div style={{ color: '#2e7d32', marginTop: '0.15rem' }}>
                            ₩{Math.round(entry.total_income).toLocaleString()}
                          </div>
                        </>
                      ) : (
                        <div style={{ color: '#bbb' }}>-</div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </>
      )}
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

// AI 최적화 분석 섹션 (SPEC-STOCK-026)
function OptimizeSection({ portfolioId, token }: { portfolioId: number; token: string }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<OptimizeResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleOptimize(refresh = false) {
    setLoading(true);
    setError(null);
    try {
      const data = await apiOptimizePortfolio(token, portfolioId, refresh);
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'AI 최적화 분석 실패');
    } finally {
      setLoading(false);
    }
  }

  const sectionStyle: React.CSSProperties = {
    marginTop: '1rem',
    padding: '0.75rem',
    border: '1px solid #ede9fe',
    borderRadius: '4px',
    background: '#faf5ff',
  };

  return (
    <div style={sectionStyle}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem' }}>
        <strong style={{ fontSize: '0.875rem' }}>AI 최적화 분석</strong>
        <button
          onClick={() => void handleOptimize(false)}
          disabled={loading}
          style={{
            padding: '0.3rem 0.7rem', background: '#7c3aed', color: '#fff',
            border: 'none', borderRadius: '4px', cursor: loading ? 'default' : 'pointer',
            fontSize: '0.8rem', opacity: loading ? 0.7 : 1,
          }}
        >
          {loading ? '분석 중...' : '최적화 분석 실행'}
        </button>
        {result && (
          <button
            onClick={() => void handleOptimize(true)}
            disabled={loading}
            style={{
              padding: '0.3rem 0.7rem', background: 'none', border: '1px solid #7c3aed',
              color: '#7c3aed', borderRadius: '4px', cursor: loading ? 'default' : 'pointer',
              fontSize: '0.8rem', opacity: loading ? 0.7 : 1,
            }}
          >
            새로 분석
          </button>
        )}
      </div>

      {error && (
        <p style={{ color: '#c62828', fontSize: '0.8rem', margin: '0.25rem 0' }}>{error}</p>
      )}

      {result && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {/* 점수 카드 */}
          <PortfolioScoreCard score={result.score} breakdown={result.score_breakdown} />

          {/* 리밸런싱 테이블 */}
          <div>
            <p style={{ margin: '0 0 8px', fontWeight: 600, fontSize: '13px', color: '#374151' }}>
              리밸런싱 제안
            </p>
            <RebalancingTable items={result.target_weights} />
          </div>

          {/* 신규 종목 추천 */}
          {result.new_stocks.length > 0 && (
            <div>
              <p style={{ margin: '0 0 8px', fontWeight: 600, fontSize: '13px', color: '#374151' }}>
                신규 종목 추천
              </p>
              <NewStockSuggestions stocks={result.new_stocks} />
            </div>
          )}

          {/* 종합 요약 */}
          {result.summary && (
            <p style={{ fontSize: '0.8rem', color: '#4b5563', lineHeight: 1.6, margin: 0 }}>
              {result.summary}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// AI 투자 조언 섹션 — 리밸런싱·리스크·브리핑 (SPEC-STOCK-014)
// @MX:NOTE: [AUTO] 3종 조언을 탭으로 전환하는 단일 섹션 컴포넌트
function AdviceSection({ token }: { token: string }) {
  type Tab = 'rebalance' | 'risk' | 'briefing';
  const [tab, setTab] = useState<Tab>('rebalance');
  const [rebalance, setRebalance] = useState<RebalanceAdvice | null>(null);
  const [risk, setRisk] = useState<RiskProfileAdvice | null>(null);
  const [briefing, setBriefing] = useState<MarketBriefingAdvice | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleFetch() {
    setLoading(true);
    setError(null);
    try {
      if (tab === 'rebalance') {
        const data = await fetchRebalanceAdvice(token);
        setRebalance(data);
      } else if (tab === 'risk') {
        const data = await fetchRiskProfile(token);
        setRisk(data);
      } else {
        const data = await fetchMarketBriefing(token);
        setBriefing(data);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'AI 조언 요청 실패');
    } finally {
      setLoading(false);
    }
  }

  const tabLabel: Record<Tab, string> = {
    rebalance: '리밸런싱',
    risk: '리스크',
    briefing: '시장 브리핑',
  };

  const sectionStyle: React.CSSProperties = {
    marginTop: '1rem',
    padding: '0.75rem',
    border: '1px solid #e8f5e9',
    borderRadius: '4px',
    background: '#f9fbe7',
  };

  const tabBtnStyle = (active: boolean): React.CSSProperties => ({
    padding: '0.3rem 0.7rem',
    border: `1px solid ${active ? '#388e3c' : '#ccc'}`,
    background: active ? '#388e3c' : '#fff',
    color: active ? '#fff' : '#333',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '0.8rem',
  });

  return (
    <div style={sectionStyle}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
        <strong style={{ fontSize: '0.875rem' }}>AI 투자 조언</strong>
        {(['rebalance', 'risk', 'briefing'] as Tab[]).map((t) => (
          <button key={t} style={tabBtnStyle(tab === t)} onClick={() => setTab(t)}>
            {tabLabel[t]}
          </button>
        ))}
        <button
          onClick={() => void handleFetch()}
          disabled={loading}
          style={{
            padding: '0.3rem 0.7rem', background: '#1976d2', color: '#fff',
            border: 'none', borderRadius: '4px', cursor: loading ? 'default' : 'pointer',
            fontSize: '0.8rem', opacity: loading ? 0.7 : 1, marginLeft: 'auto',
          }}
        >
          {loading ? '요청 중...' : '조언 받기'}
        </button>
      </div>

      {error && (
        <p style={{ color: '#c62828', fontSize: '0.8rem', margin: '0 0 0.5rem' }}>{error}</p>
      )}

      {/* 리밸런싱 결과 */}
      {tab === 'rebalance' && rebalance && (
        <div style={{ fontSize: '0.875rem' }}>
          {rebalance.message && <p style={{ color: '#666' }}>{rebalance.message}</p>}
          {rebalance.error && <p style={{ color: '#c62828' }}>{rebalance.error}</p>}
          {rebalance.actions && rebalance.actions.length > 0 && (
            <ul style={{ margin: '0 0 0.5rem 1rem', padding: 0 }}>
              {rebalance.actions.map((action, i) => (
                <li key={i} style={{ marginBottom: '0.3rem' }}>
                  <strong>{action.krx_code}</strong>
                  {' — '}
                  <span style={{
                    color: action.action === 'buy_more' ? '#388e3c'
                      : action.action === 'reduce' ? '#c62828' : '#666'
                  }}>
                    {action.action === 'buy_more' ? '매수 추가' : action.action === 'reduce' ? '비중 축소' : '유지'}
                  </span>
                  {': '}{action.reason}
                </li>
              ))}
            </ul>
          )}
          {rebalance.disclaimer && (
            <p style={{ fontSize: '0.75rem', color: '#888', margin: 0 }}>{rebalance.disclaimer}</p>
          )}
        </div>
      )}

      {/* 리스크 프로파일 결과 */}
      {tab === 'risk' && risk && (
        <div style={{ fontSize: '0.875rem' }}>
          {risk.message && <p style={{ color: '#666' }}>{risk.message}</p>}
          {risk.error && <p style={{ color: '#c62828' }}>{risk.error}</p>}
          {risk.risk_score !== undefined && risk.risk_score !== null && (
            <div style={{ marginBottom: '0.5rem' }}>
              <strong>리스크 점수: </strong>
              <span style={{
                fontWeight: 'bold',
                color: risk.risk_score >= 70 ? '#c62828' : risk.risk_score >= 40 ? '#f57c00' : '#388e3c',
              }}>
                {risk.risk_score}/100
              </span>
            </div>
          )}
          {risk.explanation && (
            <p style={{ margin: '0 0 0.5rem', lineHeight: 1.5 }}>{risk.explanation}</p>
          )}
          {risk.disclaimer && (
            <p style={{ fontSize: '0.75rem', color: '#888', margin: 0 }}>{risk.disclaimer}</p>
          )}
        </div>
      )}

      {/* 시장 브리핑 결과 */}
      {tab === 'briefing' && briefing && (
        <div style={{ fontSize: '0.875rem' }}>
          {briefing.message && <p style={{ color: '#666' }}>{briefing.message}</p>}
          {briefing.error && <p style={{ color: '#c62828' }}>{briefing.error}</p>}
          {briefing.briefing && (
            <p style={{ margin: '0 0 0.5rem', lineHeight: 1.5, whiteSpace: 'pre-line' }}>{briefing.briefing}</p>
          )}
          {briefing.disclaimer && (
            <p style={{ fontSize: '0.75rem', color: '#888', margin: 0 }}>{briefing.disclaimer}</p>
          )}
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

  // 종목 추가 폼 상태 (SPEC-STOCK-028: market/currency 추가)
  const [krxCode, setKrxCode] = useState('');
  const [quantity, setQuantity] = useState('');
  const [avgBuyPrice, setAvgBuyPrice] = useState('');
  const [market, setMarket] = useState<Market>('KRX');
  const [addErr, setAddErr] = useState<string | null>(null);
  const [addLoading, setAddLoading] = useState(false);

  // market 변경 시 currency 자동 설정
  const currency: Currency = market === 'KRX' ? 'KRW' : 'USD';

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

  // SPEC-STOCK-039: KRX 시장 상태 기반 자동 폴링 (REST 방식, 60초 간격)
  const onPoll = useCallback(async () => {
    try {
      const p = await apiGetPerformance(token, portfolioId);
      setPerformance(p);
    } catch {
      // 폴링 오류는 무시 (다음 주기에 재시도)
    }
  }, [token, portfolioId]);

  const { isPolling, isPaused, isMarketOpen, lastUpdated, toggle } = useMarketPolling({
    portfolioId,
    interval: 60,
    onPoll,
  });

  async function handleAddHolding(e: React.FormEvent) {
    e.preventDefault();
    setAddErr(null);
    setAddLoading(true);
    try {
      await apiAddHolding(token, portfolioId, krxCode, Number(quantity), Number(avgBuyPrice), market, currency);
      setKrxCode('');
      setQuantity('');
      setAvgBuyPrice('');
      setMarket('KRX');
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
      {/* SPEC-STOCK-039: 시장 상태 배지 + 폴링 토글 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem' }}>
        {isMarketOpen !== null && (
          <MarketStatusBadge isOpen={isMarketOpen} lastUpdated={lastUpdated} />
        )}
        <button
          onClick={toggle}
          style={{
            fontSize: '0.75rem',
            padding: '3px 8px',
            borderRadius: '4px',
            border: '1px solid #ccc',
            cursor: 'pointer',
            background: isPolling ? '#e3f2fd' : '#fafafa',
            color: isPolling ? '#1565c0' : '#666',
          }}
        >
          {isPolling ? (isPaused ? '일시 중지' : '폴링 중') : '폴링 시작'}
        </button>
      </div>
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
            <strong>₩{performance.total_current.toLocaleString()}</strong>
          </div>
          <div style={{ minWidth: '80px' }}>
            <span style={{ fontSize: '0.75rem', color: '#666' }}>수익률</span><br />
            <strong style={{ color: returnColor(performance.total_return_pct) }}>
              {formatPct(performance.total_return_pct)}
            </strong>
          </div>
          <div style={{ minWidth: '80px' }}>
            <span style={{ fontSize: '0.75rem', color: '#666' }}>종목 수</span><br />
            <strong>{performance.holdings.length}</strong>
          </div>
          <style>{`
            @media (max-width: 767px) {
              .portfolio-summary-cards { flex-direction: column !important; gap: 0.75rem !important; }
            }
          `}</style>
        </div>
      )}

      {/* 성과 분석 대시보드 패널 (SPEC-STOCK-017) */}
      {performance && performance.holdings.length > 0 && (
        <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
          {/* 도넛 차트 */}
          <div style={{ minWidth: '200px' }}>
            <PerformanceDonutChart summary={performance.classification_summary} />
          </div>

          {/* 분류별 목록 */}
          <div style={{ flex: '1', minWidth: '180px' }}>
            <h5 style={{ margin: '0 0 0.5rem', fontSize: '0.8rem', color: '#555' }}>성과 분류</h5>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              {(['high', 'normal', 'low'] as const).map((cls) => {
                const clsLabels = { high: '고수익 (≥+5%)', normal: '보통 (-5%~+5%)', low: '저수익 (≤-5%)' };
                const clsColors = { high: '#2e7d32', normal: '#1565c0', low: '#c62828' };
                const group = performance.classification_summary[cls];
                return (
                  <div key={cls} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem' }}>
                    <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: clsColors[cls], flexShrink: 0 }} />
                    <span style={{ color: '#555' }}>{clsLabels[cls]}</span>
                    <span style={{ marginLeft: 'auto', fontWeight: 600 }}>{group.count}종목</span>
                    <span style={{ color: '#888' }}>({group.invested_pct.toFixed(1)}%)</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* 섹터별 집계 */}
          <div style={{ flex: '1', minWidth: '200px' }}>
            <h5 style={{ margin: '0 0 0.5rem', fontSize: '0.8rem', color: '#555' }}>섹터별 성과</h5>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              {performance.sector_performance.map((sp) => (
                <div key={sp.sector} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', borderBottom: '1px solid #eee', paddingBottom: '0.15rem' }}>
                  <span style={{ color: '#555' }}>{sp.sector}</span>
                  <span>
                    <span style={{ color: '#888', marginRight: '0.5rem' }}>{sp.holding_count}종목</span>
                    <span style={{ fontWeight: 600, color: sp.return_pct >= 0 ? '#2e7d32' : '#c62828' }}>
                      {sp.return_pct >= 0 ? '+' : ''}{sp.return_pct.toFixed(2)}%
                    </span>
                  </span>
                </div>
              ))}
            </div>
          </div>
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
              {holdings.map((h) => {
                // SPEC-STOCK-028: USD 종목의 성과 데이터 매칭 (환율 환산값 표시용)
                const perf = performance?.holdings.find((p) => p.krx_code === h.krx_code);
                const isUsd = h.currency === 'USD';
                return (
                  <tr key={h.id} style={{ borderBottom: '1px solid #eee' }}>
                    <td style={cellStyle}>
                      {h.krx_code}
                      {h.market && h.market !== 'KRX' ? (
                        <span style={{
                          marginLeft: '0.3rem',
                          padding: '0.1rem 0.3rem',
                          background: '#fff3e0',
                          borderRadius: '3px',
                          fontSize: '0.7rem',
                          color: '#e65100',
                          fontWeight: 600,
                        }}>
                          {h.market}
                        </span>
                      ) : null}
                    </td>
                    <td style={cellStyle}>{h.quantity.toLocaleString()}</td>
                    <td style={cellStyle}>
                      {isUsd ? '$' : '₩'}{h.avg_buy_price.toLocaleString()}
                    </td>
                    <td style={cellStyle}>
                      <LivePriceBadge krxCode={h.krx_code} />
                      {/* SPEC-STOCK-028: USD 종목 KRW 환산값 표시 */}
                      {isUsd && perf?.current_value_krw != null && (
                        <span style={{ display: 'block', fontSize: '0.7rem', color: '#888', marginTop: '0.1rem' }}>
                          ≈₩{Math.round(perf.current_value_krw).toLocaleString()}
                          {perf.fx_rate_used != null && (
                            <span style={{ marginLeft: '0.25rem' }}>(@{perf.fx_rate_used.toFixed(0)})</span>
                          )}
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
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
          {/* SPEC-STOCK-028: 시장 선택 드롭다운 */}
          <select
            value={market}
            onChange={(e) => setMarket(e.target.value as Market)}
            style={{ flex: '0 0 100px', padding: '0.35rem 0.5rem', border: '1px solid #ccc', borderRadius: '4px', fontSize: '0.875rem' }}
          >
            <option value="KRX">KRX (국내)</option>
            <option value="NYSE">NYSE (미국)</option>
            <option value="NASDAQ">NASDAQ (미국)</option>
          </select>
          <input
            placeholder={market === 'KRX' ? '종목코드 (예: 005930)' : '티커 (예: AAPL)'}
            value={krxCode}
            onChange={(e) => setKrxCode(e.target.value)}
            required
            style={{ flex: '1 1 100px', padding: '0.35rem 0.5rem', border: '1px solid #ccc', borderRadius: '4px', fontSize: '0.875rem' }}
          />
          <input placeholder="수량" type="number" min="1" value={quantity} onChange={(e) => setQuantity(e.target.value)} required
            style={{ flex: '1 1 80px', padding: '0.35rem 0.5rem', border: '1px solid #ccc', borderRadius: '4px', fontSize: '0.875rem' }} />
          <input
            placeholder={currency === 'USD' ? '평균단가 (USD)' : '평균단가 (원)'}
            type="number"
            min="1"
            value={avgBuyPrice}
            onChange={(e) => setAvgBuyPrice(e.target.value)}
            required
            style={{ flex: '1 1 100px', padding: '0.35rem 0.5rem', border: '1px solid #ccc', borderRadius: '4px', fontSize: '0.875rem' }}
          />
          <button type="submit" disabled={addLoading}
            style={{ padding: '0.35rem 0.75rem', background: '#388e3c', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '0.875rem' }}>
            {addLoading ? '추가 중...' : '추가'}
          </button>
        </form>
      </div>

      {/* 거래 기반 홀딩스 동기화 (SPEC-STOCK-050) */}
      <HoldingsSyncPanel portfolioId={portfolioId} onSynced={() => void load()} />

      {/* 배당 분석 섹션 (SPEC-STOCK-019) */}
      <DividendsSection portfolioId={portfolioId} token={token} />

      {/* AI 분석 섹션 (REQ-FE-005) */}
      <AiAnalysisSection portfolioId={portfolioId} token={token} />

      {/* AI 최적화 분석 섹션 (SPEC-STOCK-026) */}
      <OptimizeSection portfolioId={portfolioId} token={token} />

      {/* 기간별 성과 요약 (SPEC-STOCK-030) */}
      <PerformanceSummaryPanel token={token} portfolioId={portfolioId} />

      {/* 포트폴리오 리스크 분석 (SPEC-STOCK-027) */}
      <RiskAnalysisPanel portfolioId={portfolioId} />

      {/* 포트폴리오 백테스팅 (SPEC-STOCK-029) */}
      <BacktestPanel token={token} portfolioId={portfolioId} />

      {/* 포트폴리오 알림 설정 (SPEC-STOCK-031) */}
      <PortfolioAlertPanel portfolioId={portfolioId} />

      {/* 배당 수익률 분석 (SPEC-STOCK-033) */}
      <DividendSummaryPanel token={token} portfolioId={portfolioId} />
      <DividendCalendarView token={token} portfolioId={portfolioId} />
      <DRIPSimulator token={token} portfolioId={portfolioId} />

      {/* 벤치마크 비교 (SPEC-STOCK-034) */}
      <BenchmarkComparisonPanel token={token} portfolioId={portfolioId} />
      <BenchmarkChartView token={token} portfolioId={portfolioId} />

      {/* 포트폴리오 목표 관리 (SPEC-STOCK-041) */}
      <PortfolioGoalPanel portfolioId={portfolioId} />

      {/* AI 포트폴리오 코멘터리 (SPEC-STOCK-040) */}
      <AICommentaryPanel portfolioId={portfolioId} />

      {/* AI 투자 조언 섹션 (SPEC-STOCK-014) */}
      <AdviceSection token={token} />
    </div>
  );
}

// ── SPEC-STOCK-049: 거래 내역 탭 컴포넌트 ─────────────────────────────────────
// @MX:NOTE: [AUTO] TransactionTab — 매수/매도 수동 기록·거래 목록·실현손익 UI
// @MX:SPEC: SPEC-STOCK-049 REQ-TXN-001~013

import {
  addTransaction,
  listTransactions,
  getRealizedPnl,
  type TransactionItem,
  type TransactionListResponse,
  type RealizedPnlResponse,
} from '../api/portfolio';

/** 거래 내역 탭 Props */
interface TransactionTabProps {
  portfolioId: number;
}

/** 거래 내역 & 실현손익 탭 컴포넌트 (SPEC-STOCK-049) */
export function TransactionTab({ portfolioId }: TransactionTabProps) {
  const { token } = useAuth();

  // 거래 목록 상태
  const [txns, setTxns] = useState<TransactionItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // 실현손익 상태
  const [pnlData, setPnlData] = useState<RealizedPnlResponse>({
    items: [],
    total_realized_pnl: '0',
  });

  // 폼 상태
  const [krxCode, setKrxCode] = useState('');
  const [txnType, setTxnType] = useState<'BUY' | 'SELL'>('BUY');
  const [quantity, setQuantity] = useState('');
  const [price, setPrice] = useState('');
  const [txnDate, setTxnDate] = useState(new Date().toISOString().slice(0, 10));
  const [note, setNote] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 거래 목록 & 실현손익 로드
  const loadData = useCallback(async () => {
    if (!token) return;
    try {
      const [txnRes, pnlRes] = await Promise.all([
        listTransactions(token, portfolioId, { page, page_size: pageSize }),
        getRealizedPnl(token, portfolioId),
      ]);
      setTxns(txnRes.transactions);
      setTotal(txnRes.total);
      setPnlData(pnlRes);
    } catch (e) {
      // 데이터 로드 오류 — 무시하고 빈 상태 유지
    }
  }, [token, portfolioId, page]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // 거래 추가 제출
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      await addTransaction(token, portfolioId, {
        krx_code: krxCode,
        txn_type: txnType,
        quantity: parseInt(quantity, 10),
        price: parseFloat(price),
        txn_date: txnDate,
        note: note || null,
      });
      setKrxCode('');
      setQuantity('');
      setPrice('');
      setNote('');
      await loadData();
    } catch (e) {
      setError('거래 추가에 실패했습니다');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div data-testid="transaction-tab">
      {/* 거래 추가 폼 */}
      <form onSubmit={handleSubmit} style={{ marginBottom: 16 }}>
        <h4>거래 추가</h4>
        {error && <p style={{ color: 'red' }}>{error}</p>}
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <input
            data-testid="txn-krx-code-input"
            type="text"
            placeholder="종목코드 (예: 005930)"
            value={krxCode}
            onChange={(e) => setKrxCode(e.target.value)}
            required
          />
          <select
            data-testid="txn-type-select"
            value={txnType}
            onChange={(e) => setTxnType(e.target.value as 'BUY' | 'SELL')}
          >
            <option value="BUY">매수</option>
            <option value="SELL">매도</option>
          </select>
          <input
            data-testid="txn-quantity-input"
            type="number"
            placeholder="수량"
            min={1}
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            required
          />
          <input
            data-testid="txn-price-input"
            type="number"
            placeholder="가격"
            min={0.01}
            step="0.01"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            required
          />
          <input
            data-testid="txn-date-input"
            type="date"
            value={txnDate}
            onChange={(e) => setTxnDate(e.target.value)}
            required
          />
          <input
            data-testid="txn-note-input"
            type="text"
            placeholder="메모 (선택)"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
          <button data-testid="txn-submit-btn" type="submit" disabled={submitting}>
            {submitting ? '추가 중...' : '거래 추가'}
          </button>
        </div>
      </form>

      {/* 실현손익 요약 */}
      <div data-testid="pnl-section" style={{ marginBottom: 16 }}>
        <h4>실현손익 (이동평균 원가법)</h4>
        <p>
          총 실현손익:{' '}
          <strong data-testid="pnl-total">{pnlData.total_realized_pnl}</strong>
        </p>
        {pnlData.items.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>종목코드</th>
                <th>실현손익</th>
              </tr>
            </thead>
            <tbody>
              {pnlData.items.map((item) => (
                <tr key={item.krx_code} data-testid={`pnl-row-${item.krx_code}`}>
                  <td>{item.krx_code}</td>
                  <td>{item.realized_pnl}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* 거래 목록 */}
      <div data-testid="txn-list">
        <h4>거래 내역 ({total}건)</h4>
        {txns.length === 0 ? (
          <p>거래 내역이 없습니다.</p>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th>날짜</th>
                <th>종목</th>
                <th>유형</th>
                <th>수량</th>
                <th>가격</th>
                <th>메모</th>
              </tr>
            </thead>
            <tbody>
              {txns.map((txn) => (
                <tr key={txn.id} data-testid={`txn-row-${txn.id}`}>
                  <td>{txn.txn_date}</td>
                  <td>{txn.krx_code}</td>
                  <td style={{ color: txn.txn_type === 'BUY' ? '#2563eb' : '#dc2626' }}>
                    {txn.txn_type}
                  </td>
                  <td>{txn.quantity}</td>
                  <td>{txn.price}</td>
                  <td>{txn.note ?? '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {/* 페이지네이션 */}
        {total > pageSize && (
          <div style={{ marginTop: 8 }}>
            <button
              data-testid="txn-prev-btn"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              이전
            </button>
            <span style={{ margin: '0 8px' }}>
              {page} / {Math.ceil(total / pageSize)}
            </span>
            <button
              data-testid="txn-next-btn"
              disabled={page >= Math.ceil(total / pageSize)}
              onClick={() => setPage((p) => p + 1)}
            >
              다음
            </button>
          </div>
        )}
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
