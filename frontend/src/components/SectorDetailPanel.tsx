// 섹터 상세 패널 — 선택된 섹터의 트렌드 차트와 구성 종목 표시
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { fetchSectorDetail } from '../api/sectors';
import type { SectorDetailResponse, SectorTrendPoint, SectorStockItem } from '../api/sectors';

interface SectorDetailPanelProps {
  sector: string;
  onClose: () => void;
}

// trade_date를 MM/DD 형식으로 변환
function formatDate(dateStr: string): string {
  const parts = dateStr.split('-');
  if (parts.length >= 3) {
    return `${parts[1]}/${parts[2]}`;
  }
  return dateStr;
}

interface TrendChartProps {
  trends: SectorTrendPoint[];
}

function TrendChart({ trends }: TrendChartProps) {
  if (trends.length === 0) {
    return (
      <p
        style={{ color: '#888', fontSize: '0.875rem', textAlign: 'center', padding: '1.5rem 0' }}
        data-testid="no-trend-data"
      >
        트렌드 데이터 없음
      </p>
    );
  }

  const chartData = trends.map((t) => ({
    date: formatDate(t.trade_date),
    trend_score: t.trend_score,
  }));

  return (
    <ResponsiveContainer width="100%" height={180}>
      <LineChart data={chartData} margin={{ top: 8, right: 12, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="date" tick={{ fontSize: 11 }} />
        <YAxis domain={[-1, 1]} tick={{ fontSize: 11 }} />
        <Tooltip
          formatter={(value: number) => [value.toFixed(3), '트렌드 점수']}
          labelFormatter={(label: string) => `날짜: ${label}`}
        />
        <Line
          type="monotone"
          dataKey="trend_score"
          stroke="#1976d2"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

interface StockListProps {
  stocks: SectorStockItem[];
  totalStocks: number;
}

function StockList({ stocks, totalStocks }: StockListProps) {
  const navigate = useNavigate();

  return (
    <div>
      <p style={{ fontSize: '0.8rem', color: '#888', marginBottom: '0.5rem' }}>
        총 {totalStocks}개 종목
      </p>
      {stocks.length === 0 ? (
        <p style={{ color: '#aaa', fontSize: '0.875rem' }}>종목 데이터 없음</p>
      ) : (
        <ul style={{ padding: 0, margin: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
          {stocks.map((stock) => (
            <li key={stock.krx_code}>
              <button
                onClick={() => void navigate(`/stocks/${stock.krx_code}`)}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  width: '100%',
                  padding: '0.4rem 0.6rem',
                  border: '1px solid #e0e0e0',
                  borderRadius: '4px',
                  backgroundColor: '#fafafa',
                  cursor: 'pointer',
                  fontSize: '0.875rem',
                  textAlign: 'left',
                }}
                aria-label={`${stock.krx_code} 종목 상세 보기`}
              >
                <span style={{ fontWeight: 600, color: '#1976d2' }}>{stock.krx_code}</span>
                <span style={{ color: '#888', fontSize: '0.8rem' }}>
                  언급 {stock.mention_count}회
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// @MX:ANCHOR: [AUTO] 섹터 상세 패널 — Sectors 페이지에서 단독 렌더링
// @MX:REASON: 섹터 선택 시 이 컴포넌트만 사용되므로 API 호출과 UI 책임이 집중됨
export function SectorDetailPanel({ sector, onClose }: SectorDetailPanelProps) {
  const [data, setData] = useState<SectorDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const result = await fetchSectorDetail(sector, 7);
        if (!cancelled) setData(result);
      } catch (err) {
        if (!cancelled)
          setError(err instanceof Error ? err.message : '상세 정보를 불러오는 중 오류가 발생했습니다.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();
    return () => { cancelled = true; };
  }, [sector]);

  return (
    <div
      style={{
        border: '1px solid #e0e0e0',
        borderRadius: '8px',
        padding: '1.25rem',
        backgroundColor: '#fff',
        boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
      }}
      aria-label={`${sector} 섹터 상세`}
    >
      {/* 패널 헤더 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: '#212121' }}>
          {sector} 섹터 상세
        </h3>
        <button
          onClick={onClose}
          aria-label="닫기"
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            fontSize: '1.25rem',
            color: '#888',
            lineHeight: 1,
            padding: '0.2rem',
          }}
        >
          ✕
        </button>
      </div>

      {/* 로딩 */}
      {loading && (
        <div role="status" aria-live="polite" style={{ textAlign: 'center', padding: '2rem', color: '#888' }}>
          불러오는 중...
        </div>
      )}

      {/* 오류 */}
      {!loading && error && (
        <div role="alert" style={{ color: '#c62828', fontSize: '0.875rem' }}>
          오류: {error}
        </div>
      )}

      {/* 데이터 */}
      {!loading && !error && data && (
        <div>
          {/* 트렌드 차트 */}
          <div style={{ marginBottom: '1rem' }}>
            <h4 style={{ fontSize: '0.875rem', color: '#555', margin: '0 0 0.5rem 0' }}>
              트렌드 점수 추이 (최근 7일)
            </h4>
            <TrendChart trends={data.trends} />
          </div>

          {/* 구성 종목 */}
          <div>
            <h4 style={{ fontSize: '0.875rem', color: '#555', margin: '0 0 0.5rem 0' }}>
              구성 종목
            </h4>
            <StockList stocks={data.stocks} totalStocks={data.total_stocks} />
          </div>
        </div>
      )}
    </div>
  );
}
