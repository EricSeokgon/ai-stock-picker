// 포트폴리오 리스크 분석 패널 (SPEC-STOCK-027)
// 인라인 스타일 사용 — 기존 Portfolio.tsx 및 PortfolioScoreCard.tsx 스타일 패턴 준수
import React, { useEffect, useState } from 'react';
import { useAuth } from '../auth/AuthContext';
import { apiGetRiskAnalysis, type RiskAnalysisResult, type HoldingVolatility } from '../api/portfolio';

// @MX:ANCHOR: [AUTO] RiskAnalysisPanel — 리스크 분석 UI 공개 컴포넌트
// @MX:REASON: Portfolio.tsx에서 호출되는 외부 공개 컴포넌트 (fan_in >= 1, 추후 확장 예상)

const PERIOD_OPTIONS = [30, 60, 90, 180, 252] as const;
type Period = typeof PERIOD_OPTIONS[number];

interface Props {
  portfolioId: number;
}

// 상관계수(-1~1)를 RGB 색상으로 변환
function corrToRgb(corr: number): string {
  const c = Math.max(-1, Math.min(1, corr));
  if (c < 0) {
    const r = Math.round(255 + c * 255);
    const g = Math.round(255 + c * 255);
    return `rgb(${r}, ${g}, 255)`;
  }
  if (c > 0) {
    const b = Math.round(255 - c * 255);
    const g = Math.round(255 - c * 255);
    return `rgb(255, ${g}, ${b})`;
  }
  return 'rgb(255, 255, 255)';
}

// 셀 텍스트 색상: |corr| >= 0.6이면 흰색, 아니면 검정
function corrTextColor(corr: number): string {
  return Math.abs(corr) >= 0.6 ? '#fff' : '#111';
}

interface CorrelationHeatmapProps {
  matrix: Record<string, Record<string, number>>;
}

function CorrelationHeatmap({ matrix }: CorrelationHeatmapProps) {
  const tickers = Object.keys(matrix);
  if (tickers.length === 0) return null;

  const cellStyle: React.CSSProperties = {
    width: '60px',
    height: '40px',
    textAlign: 'center',
    fontSize: '0.75rem',
    border: '1px solid #e5e7eb',
    padding: '0 2px',
    lineHeight: '40px',
    overflow: 'hidden',
    whiteSpace: 'nowrap',
  };

  const headerCellStyle: React.CSSProperties = {
    ...cellStyle,
    background: '#f3f4f6',
    fontWeight: 600,
    fontSize: '0.7rem',
    color: '#374151',
  };

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ borderCollapse: 'collapse', tableLayout: 'fixed' }}>
        <thead>
          <tr>
            <th style={{ ...headerCellStyle, width: '64px' }} />
            {tickers.map((t) => (
              <th key={t} style={headerCellStyle}>{t}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {tickers.map((row) => (
            <tr key={row}>
              <th style={headerCellStyle}>{row}</th>
              {tickers.map((col) => {
                const corr = matrix[row]?.[col] ?? 0;
                const isDiag = row === col;
                return (
                  <td
                    key={col}
                    style={{
                      ...cellStyle,
                      background: corrToRgb(corr),
                      color: corrTextColor(corr),
                      fontWeight: isDiag ? 700 : 400,
                    }}
                  >
                    {corr.toFixed(2)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface VolatilityTableProps {
  holdings: HoldingVolatility[];
  portfolioVolatility: number;
  diversificationBenefit: number;
}

function VolatilityTable({ holdings, portfolioVolatility, diversificationBenefit }: VolatilityTableProps) {
  const sorted = [...holdings].sort((a, b) => b.annualized_volatility_pct - a.annualized_volatility_pct);

  const thStyle: React.CSSProperties = {
    textAlign: 'left',
    padding: '0.4rem 0.5rem',
    fontSize: '0.75rem',
    color: '#6b7280',
    borderBottom: '1px solid #e5e7eb',
    fontWeight: 600,
  };
  const tdStyle: React.CSSProperties = {
    padding: '0.4rem 0.5rem',
    fontSize: '0.8rem',
    color: '#111',
    borderBottom: '1px solid #f3f4f6',
  };

  return (
    <div>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={thStyle}>종목코드</th>
            <th style={thStyle}>종목명</th>
            <th style={{ ...thStyle, textAlign: 'right' }}>연환산 변동성(%)</th>
            <th style={{ ...thStyle, textAlign: 'right' }}>가격 데이터(일)</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((h) => (
            <tr key={h.krx_code}>
              <td style={tdStyle}>{h.krx_code}</td>
              <td style={tdStyle}>{h.name}</td>
              <td style={{ ...tdStyle, textAlign: 'right', fontWeight: 500 }}>
                {h.annualized_volatility_pct.toFixed(2)}%
              </td>
              <td style={{ ...tdStyle, textAlign: 'right' }}>{h.price_data_days}일</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{
        marginTop: '0.5rem',
        padding: '0.4rem 0.5rem',
        background: '#f3f4f6',
        borderRadius: '4px',
        fontSize: '0.8rem',
        color: '#374151',
        display: 'flex',
        gap: '1.5rem',
      }}>
        <span>포트폴리오 변동성: <strong>{portfolioVolatility.toFixed(2)}%</strong></span>
        <span>분산 효과: <strong>{diversificationBenefit.toFixed(2)}%</strong></span>
      </div>
    </div>
  );
}

// @MX:WARN: [AUTO] 복수 useEffect + 비동기 fetch — period 변경 시 경쟁 상태 가능성
// @MX:REASON: period 변경 → fetch 재호출 시 이전 요청이 더 늦게 도착할 수 있음; cleanup 미구현
export default function RiskAnalysisPanel({ portfolioId }: Props) {
  const { token } = useAuth();
  const [period, setPeriod] = useState<Period>(90);
  const [data, setData] = useState<RiskAnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    apiGetRiskAnalysis(token, portfolioId, period, false)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : '리스크 분석 조회 실패');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [token, portfolioId, period]);

  const sectionStyle: React.CSSProperties = {
    marginTop: '1rem',
    padding: '0.75rem',
    border: '1px solid #fce7f3',
    borderRadius: '4px',
    background: '#fff7f9',
  };

  const periodBtnStyle = (active: boolean): React.CSSProperties => ({
    padding: '0.2rem 0.6rem',
    border: '1px solid #e5e7eb',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '0.75rem',
    background: active ? '#be185d' : '#fff',
    color: active ? '#fff' : '#374151',
    fontWeight: active ? 600 : 400,
  });

  return (
    <div style={sectionStyle}>
      {/* 헤더 + 기간 선택 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
        <strong style={{ fontSize: '0.875rem' }}>리스크 분석</strong>
        <div style={{ display: 'flex', gap: '0.3rem', flexWrap: 'wrap' }}>
          {PERIOD_OPTIONS.map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              style={periodBtnStyle(period === p)}
              aria-pressed={period === p}
              aria-label={`${p}일 기간 선택`}
            >
              {p}일
            </button>
          ))}
        </div>
      </div>

      {/* 로딩 상태 */}
      {loading && (
        <div style={{ padding: '1.5rem 0', textAlign: 'center', color: '#9ca3af', fontSize: '0.875rem' }}>
          분석 중...
        </div>
      )}

      {/* 에러 상태 */}
      {error && !loading && (
        <div style={{ padding: '1rem', background: '#fef2f2', borderRadius: '4px', color: '#dc2626', fontSize: '0.85rem' }}>
          {error}
          <button
            onClick={() => setPeriod((p) => p)}
            style={{ marginLeft: '0.75rem', padding: '0.2rem 0.5rem', fontSize: '0.75rem', cursor: 'pointer' }}
            aria-label="다시 시도"
          >
            다시 시도
          </button>
        </div>
      )}

      {/* 데이터 */}
      {data && !loading && !error && (
        <>
          {/* 상관계수 매트릭스 */}
          <div style={{ marginBottom: '1rem' }}>
            <p style={{ fontSize: '0.8rem', fontWeight: 600, color: '#374151', marginBottom: '0.4rem' }}>
              상관계수 매트릭스
            </p>
            <CorrelationHeatmap matrix={data.correlation_matrix} />
          </div>

          {/* 보유 종목별 변동성 */}
          <div>
            <p style={{ fontSize: '0.8rem', fontWeight: 600, color: '#374151', marginBottom: '0.4rem' }}>
              보유 종목별 변동성
            </p>
            <VolatilityTable
              holdings={data.holdings_volatility}
              portfolioVolatility={data.portfolio_volatility_pct}
              diversificationBenefit={data.diversification_benefit_pct}
            />
          </div>
        </>
      )}
    </div>
  );
}
