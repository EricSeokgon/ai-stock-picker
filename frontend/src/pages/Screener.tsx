// 종목 스크리너 페이지 (SPEC-STOCK-018)
// - PER/PBR/ROE/시가총액/배당수익률/52주 위치 필터
// - 프리셋 저장/불러오기 (최대 5개, 로그인 필요)
// - 필터 없이 전체 종목 조회 가능

import { useEffect, useState } from 'react';
import { useAuth } from '../auth/AuthContext';
import {
  runScreener,
  listPresets,
  createPreset,
  deletePreset,
  type FilterRange,
  type ScreenerCriteria,
  type ScreenerResult,
  type ScreenerPreset,
} from '../api/screener';

// ── 필터 입력 컴포넌트 ───────────────────────────────────────────────────────

interface FilterInputProps {
  label: string;
  value: FilterRange;
  onChange: (v: FilterRange) => void;
  step?: number;
}

function FilterInput({ label, value, onChange, step = 0.1 }: FilterInputProps) {
  return (
    <div style={{ marginBottom: '12px' }}>
      <label style={{ display: 'block', marginBottom: '4px', fontWeight: 500 }}>{label}</label>
      <div style={{ display: 'flex', gap: '8px' }}>
        <input
          type="number"
          placeholder="최솟값"
          step={step}
          value={value.min ?? ''}
          onChange={(e) =>
            onChange({ ...value, min: e.target.value === '' ? null : Number(e.target.value) })
          }
          style={{ width: '100px', padding: '4px 8px', border: '1px solid #ddd', borderRadius: '4px' }}
          data-testid={`filter-${label}-min`}
        />
        <span style={{ alignSelf: 'center' }}>~</span>
        <input
          type="number"
          placeholder="최댓값"
          step={step}
          value={value.max ?? ''}
          onChange={(e) =>
            onChange({ ...value, max: e.target.value === '' ? null : Number(e.target.value) })
          }
          style={{ width: '100px', padding: '4px 8px', border: '1px solid #ddd', borderRadius: '4px' }}
          data-testid={`filter-${label}-max`}
        />
      </div>
    </div>
  );
}

// ── 기본 필터 상태 ────────────────────────────────────────────────────────────

const emptyRange = (): FilterRange => ({ min: null, max: null });

interface FilterState {
  per: FilterRange;
  pbr: FilterRange;
  roe: FilterRange;
  market_cap: FilterRange;
  dividend_yield: FilterRange;
  week52_position: FilterRange;
}

function emptyFilters(): FilterState {
  return {
    per: emptyRange(),
    pbr: emptyRange(),
    roe: emptyRange(),
    market_cap: emptyRange(),
    dividend_yield: emptyRange(),
    week52_position: emptyRange(),
  };
}

function filterStateToApi(state: FilterState): ScreenerCriteria {
  const toRange = (r: FilterRange) =>
    r.min == null && r.max == null ? undefined : r;
  return {
    per: toRange(state.per),
    pbr: toRange(state.pbr),
    roe: toRange(state.roe),
    market_cap: toRange(state.market_cap),
    dividend_yield: toRange(state.dividend_yield),
    week52_position: toRange(state.week52_position),
  };
}

// ── 유틸: 시가총액 포매팅 ────────────────────────────────────────────────────

function fmtMarketCap(v: number | null): string {
  if (v == null) return '-';
  if (v >= 1_000_000_000_000) return `${(v / 1_000_000_000_000).toFixed(1)}조`;
  if (v >= 100_000_000) return `${(v / 100_000_000).toFixed(0)}억`;
  return `${v.toLocaleString()}원`;
}

function fmtNum(v: number | null, digits = 1): string {
  return v == null ? '-' : v.toFixed(digits);
}

// ── 메인 컴포넌트 ─────────────────────────────────────────────────────────────

export default function Screener() {
  const { isAuthenticated, token } = useAuth();
  const [filters, setFilters] = useState<FilterState>(emptyFilters());
  const [results, setResults] = useState<ScreenerResult[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 프리셋
  const [presets, setPresets] = useState<ScreenerPreset[]>([]);
  const [presetName, setPresetName] = useState('');
  const [presetLoading, setPresetLoading] = useState(false);
  const [presetError, setPresetError] = useState<string | null>(null);

  // 정렬
  const [sortBy, setSortBy] = useState<string>('per');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');

  // 마운트 시 프리셋 로드 (인증 시)
  useEffect(() => {
    if (isAuthenticated && token) {
      void loadPresets();
    }
  }, [isAuthenticated, token]);

  async function loadPresets() {
    if (!token) return;
    try {
      const list = await listPresets(token);
      setPresets(list);
    } catch (_e) {
      // 프리셋 로드 실패는 무음 처리
    }
  }

  // 스크리너 실행
  async function handleRun() {
    setLoading(true);
    setError(null);
    try {
      const criteria = filterStateToApi(filters);
      const resp = await runScreener({ filters: criteria, sort_by: sortBy, sort_order: sortOrder, limit: 200 });
      setResults(resp.results);
      setTotal(resp.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : '스크리너 실행 오류');
    } finally {
      setLoading(false);
    }
  }

  // 필터 초기화
  function handleReset() {
    setFilters(emptyFilters());
  }

  // 프리셋 저장
  async function handleSavePreset() {
    if (!token || !presetName.trim()) return;
    setPresetLoading(true);
    setPresetError(null);
    try {
      await createPreset(token, { name: presetName.trim(), criteria: filterStateToApi(filters) });
      setPresetName('');
      await loadPresets();
    } catch (e) {
      setPresetError(e instanceof Error ? e.message : '프리셋 저장 오류');
    } finally {
      setPresetLoading(false);
    }
  }

  // 프리셋 불러오기
  function handleLoadPreset(preset: ScreenerPreset) {
    const c = preset.criteria;
    setFilters({
      per: c.per ?? emptyRange(),
      pbr: c.pbr ?? emptyRange(),
      roe: c.roe ?? emptyRange(),
      market_cap: c.market_cap ?? emptyRange(),
      dividend_yield: c.dividend_yield ?? emptyRange(),
      week52_position: c.week52_position ?? emptyRange(),
    });
  }

  // 프리셋 삭제
  async function handleDeletePreset(presetId: number) {
    if (!token) return;
    try {
      await deletePreset(token, presetId);
      await loadPresets();
    } catch (e) {
      setPresetError(e instanceof Error ? e.message : '프리셋 삭제 오류');
    }
  }

  // 정렬 토글
  function handleSort(col: string) {
    if (sortBy === col) {
      setSortOrder((o) => (o === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortBy(col);
      setSortOrder('asc');
    }
  }

  const sortedResults = [...results].sort((a, b) => {
    const av = (a as unknown as Record<string, unknown>)[sortBy] as number | null;
    const bv = (b as unknown as Record<string, unknown>)[sortBy] as number | null;
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    return sortOrder === 'asc' ? av - bv : bv - av;
  });

  const SortHeader = ({ col, label }: { col: string; label: string }) => (
    <th
      onClick={() => handleSort(col)}
      style={{ cursor: 'pointer', padding: '8px', borderBottom: '2px solid #ddd', whiteSpace: 'nowrap' }}
    >
      {label}{sortBy === col ? (sortOrder === 'asc' ? ' ▲' : ' ▼') : ''}
    </th>
  );

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '24px 16px' }} data-testid="screener-page">
      <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '20px' }}>종목 스크리너</h1>

      <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
        {/* 필터 패널 */}
        <div style={{ minWidth: '260px', background: '#f9f9f9', padding: '16px', borderRadius: '8px', border: '1px solid #e0e0e0' }}>
          <h2 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '16px' }}>필터 조건</h2>

          <FilterInput label="PER" value={filters.per} onChange={(v) => setFilters({ ...filters, per: v })} />
          <FilterInput label="PBR" value={filters.pbr} onChange={(v) => setFilters({ ...filters, pbr: v })} />
          <FilterInput label="ROE (%)" value={filters.roe} onChange={(v) => setFilters({ ...filters, roe: v })} />
          <FilterInput
            label="시가총액 (억원 단위)"
            value={{
              min: filters.market_cap.min != null ? filters.market_cap.min / 1e8 : null,
              max: filters.market_cap.max != null ? filters.market_cap.max / 1e8 : null,
            }}
            onChange={(v) =>
              setFilters({
                ...filters,
                market_cap: {
                  min: v.min != null ? v.min * 1e8 : null,
                  max: v.max != null ? v.max * 1e8 : null,
                },
              })
            }
            step={100}
          />
          <FilterInput label="배당수익률 (%)" value={filters.dividend_yield} onChange={(v) => setFilters({ ...filters, dividend_yield: v })} />
          <FilterInput label="52주 위치 (%)" value={filters.week52_position} onChange={(v) => setFilters({ ...filters, week52_position: v })} step={1} />

          <div style={{ display: 'flex', gap: '8px', marginTop: '16px' }}>
            <button
              onClick={() => void handleRun()}
              disabled={loading}
              style={{ flex: 1, padding: '8px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer' }}
              data-testid="run-screener-btn"
            >
              {loading ? '조회 중...' : '스크리너 실행'}
            </button>
            <button
              onClick={handleReset}
              style={{ padding: '8px 12px', background: '#f3f4f6', border: '1px solid #ddd', borderRadius: '6px', cursor: 'pointer' }}
            >
              초기화
            </button>
          </div>

          {error && (
            <p style={{ color: '#dc2626', marginTop: '8px', fontSize: '0.875rem' }} data-testid="screener-error">{error}</p>
          )}

          {/* 프리셋 */}
          {isAuthenticated && (
            <div style={{ marginTop: '20px', borderTop: '1px solid #e0e0e0', paddingTop: '16px' }}>
              <h3 style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: '8px' }}>프리셋 저장</h3>
              <div style={{ display: 'flex', gap: '4px' }}>
                <input
                  type="text"
                  value={presetName}
                  onChange={(e) => setPresetName(e.target.value)}
                  placeholder="프리셋 이름"
                  maxLength={100}
                  style={{ flex: 1, padding: '4px 8px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '0.875rem' }}
                  data-testid="preset-name-input"
                />
                <button
                  onClick={() => void handleSavePreset()}
                  disabled={presetLoading || !presetName.trim()}
                  style={{ padding: '4px 8px', background: '#16a34a', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '0.875rem' }}
                  data-testid="save-preset-btn"
                >
                  저장
                </button>
              </div>
              {presetError && (
                <p style={{ color: '#dc2626', marginTop: '4px', fontSize: '0.75rem' }}>{presetError}</p>
              )}

              {presets.length > 0 && (
                <div style={{ marginTop: '12px' }}>
                  <h3 style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: '8px' }}>저장된 프리셋</h3>
                  {presets.map((p) => (
                    <div
                      key={p.id}
                      style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0', borderBottom: '1px solid #f0f0f0' }}
                    >
                      <button
                        onClick={() => handleLoadPreset(p)}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#2563eb', fontSize: '0.875rem', padding: 0 }}
                        data-testid={`load-preset-${p.id}`}
                      >
                        {p.name}
                      </button>
                      <button
                        onClick={() => void handleDeletePreset(p.id)}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#dc2626', fontSize: '0.75rem' }}
                        aria-label={`프리셋 ${p.name} 삭제`}
                      >
                        삭제
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* 결과 테이블 */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ marginBottom: '8px', color: '#6b7280', fontSize: '0.875rem' }} data-testid="result-count">
            {total > 0 ? `총 ${total}개 종목` : results.length === 0 && !loading ? '조건을 설정하고 스크리너를 실행하세요.' : ''}
          </div>

          {sortedResults.length > 0 && (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }} data-testid="screener-table">
                <thead style={{ background: '#f3f4f6' }}>
                  <tr>
                    <th style={{ padding: '8px', borderBottom: '2px solid #ddd', textAlign: 'left' }}>종목코드</th>
                    <th style={{ padding: '8px', borderBottom: '2px solid #ddd', textAlign: 'left' }}>종목명</th>
                    <th style={{ padding: '8px', borderBottom: '2px solid #ddd', textAlign: 'left' }}>섹터</th>
                    <SortHeader col="current_price" label="현재가" />
                    <SortHeader col="per" label="PER" />
                    <SortHeader col="pbr" label="PBR" />
                    <SortHeader col="roe" label="ROE(%)" />
                    <SortHeader col="market_cap" label="시가총액" />
                    <SortHeader col="dividend_yield" label="배당(%)" />
                    <SortHeader col="week52_position" label="52주(%)" />
                  </tr>
                </thead>
                <tbody>
                  {sortedResults.map((r) => (
                    <tr
                      key={r.krx_code}
                      style={{ borderBottom: '1px solid #f0f0f0' }}
                      data-testid={`row-${r.krx_code}`}
                    >
                      <td style={{ padding: '8px' }}>{r.krx_code}</td>
                      <td style={{ padding: '8px' }}>
                        {r.name ?? '-'}
                        {r.in_watchlist && <span title="관심 목록" style={{ marginLeft: '4px', color: '#f59e0b' }}>★</span>}
                        {r.in_recommendations && <span title="추천 종목" style={{ marginLeft: '4px', color: '#10b981' }}>R</span>}
                      </td>
                      <td style={{ padding: '8px', color: '#6b7280' }}>{r.sector ?? '-'}</td>
                      <td style={{ padding: '8px', textAlign: 'right' }}>
                        {r.current_price != null ? `${r.current_price.toLocaleString()}원` : '-'}
                      </td>
                      <td style={{ padding: '8px', textAlign: 'right' }}>{fmtNum(r.per)}</td>
                      <td style={{ padding: '8px', textAlign: 'right' }}>{fmtNum(r.pbr, 2)}</td>
                      <td style={{ padding: '8px', textAlign: 'right' }}>{fmtNum(r.roe)}</td>
                      <td style={{ padding: '8px', textAlign: 'right' }}>{fmtMarketCap(r.market_cap)}</td>
                      <td style={{ padding: '8px', textAlign: 'right' }}>{fmtNum(r.dividend_yield)}</td>
                      <td style={{ padding: '8px', textAlign: 'right' }}>{fmtNum(r.week52_position, 1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
