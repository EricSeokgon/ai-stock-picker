// 섹터 트렌드 차트 컴포넌트 - Recharts BarChart 사용
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  CartesianGrid,
  Cell,
} from 'recharts';
import type { SectorTrendPoint } from '../types';

interface SectorTrendChartProps {
  trends: SectorTrendPoint[];
}

// 섹터별 최신 트렌드 점수만 추출 (동일 섹터 중 최신 날짜 기준)
function getLatestBysector(trends: SectorTrendPoint[]): SectorTrendPoint[] {
  const map = new Map<string, SectorTrendPoint>();
  for (const t of trends) {
    const existing = map.get(t.sector);
    if (!existing || t.trade_date > existing.trade_date) {
      map.set(t.sector, t);
    }
  }
  return Array.from(map.values()).sort((a, b) => b.trend_score - a.trend_score);
}

// trend_score 기반 막대 색상: 0.7 이상 초록, 0.4 이상 주황, 그 이하 빨강
function barColor(score: number): string {
  if (score >= 0.7) return '#2e7d32';
  if (score >= 0.4) return '#f57c00';
  return '#c62828';
}

// @MX:ANCHOR: [AUTO] SectorTrendChart - 섹터 트렌드 차트 공개 컴포넌트
// @MX:REASON: App.tsx, 테스트에서 직접 참조하는 외부 노출 컴포넌트
export function SectorTrendChart({ trends }: SectorTrendChartProps) {
  const chartData = getLatestBysector(trends);
  const isEmpty = chartData.length === 0;

  return (
    <section aria-labelledby="sector-trend-heading">
      <h2
        id="sector-trend-heading"
        style={{
          fontSize: '1.25rem',
          fontWeight: 700,
          marginBottom: '1rem',
          color: '#212121',
        }}
      >
        섹터 트렌드
      </h2>

      {isEmpty ? (
        // 빈 데이터 플레이스홀더
        <div
          style={{
            padding: '2rem',
            textAlign: 'center',
            color: '#999',
            backgroundColor: '#f9f9f9',
            borderRadius: '8px',
            border: '1px dashed #ddd',
          }}
        >
          섹터 트렌드 데이터가 없습니다
        </div>
      ) : (
        // Recharts 차트 컨테이너
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 40 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="sector"
              tick={{ fontSize: 12 }}
              angle={-30}
              textAnchor="end"
              interval={0}
            />
            <YAxis
              domain={[0, 1]}
              tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
              tick={{ fontSize: 11 }}
              width={44}
            />
            <Tooltip
              formatter={(value: number) => [`${(value * 100).toFixed(1)}%`, '트렌드 점수']}
              labelFormatter={(label: string) => `섹터: ${label}`}
            />
            <Legend
              verticalAlign="top"
              wrapperStyle={{ paddingBottom: '8px', fontSize: '12px' }}
            />
            <Bar dataKey="trend_score" name="트렌드 점수" radius={[4, 4, 0, 0]}>
              {chartData.map((entry) => (
                <Cell key={entry.sector} fill={barColor(entry.trend_score)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </section>
  );
}
