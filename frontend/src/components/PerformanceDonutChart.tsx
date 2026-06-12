// 성과 분류 도넛 차트 컴포넌트 (SPEC-STOCK-017 REQ-CHART-001)
// recharts PieChart/Pie 사용, innerRadius 설정으로 도넛 형태

import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import type { ClassificationSummary } from '../api/portfolio';

interface PerformanceDonutChartProps {
  summary: ClassificationSummary;
}

// 분류별 색상 및 레이블
const CLS_COLORS: Record<string, string> = {
  high: '#2e7d32',
  normal: '#1565c0',
  low: '#c62828',
};

const CLS_LABELS: Record<string, string> = {
  high: '고수익',
  normal: '보통',
  low: '저수익',
};

// @MX:NOTE: [AUTO] PerformanceDonutChart — SPEC-STOCK-017 REQ-CHART-001
// @MX:SPEC: SPEC-STOCK-017
export function PerformanceDonutChart({ summary }: PerformanceDonutChartProps) {
  const data = (['high', 'normal', 'low'] as const)
    .map((cls) => ({
      name: CLS_LABELS[cls],
      value: summary[cls].count,
      investedPct: summary[cls].invested_pct,
    }))
    .filter((d) => d.value > 0);

  // 모든 종목이 0이면 플레이스홀더 표시
  if (data.length === 0) {
    return (
      <div style={{ width: '100%', height: 160, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#aaa', fontSize: '0.8rem' }}>
        성과 데이터 없음
      </div>
    );
  }

  return (
    <div>
      <h5 style={{ margin: '0 0 0.25rem', fontSize: '0.8rem', color: '#555' }}>성과 분류 비중</h5>
      <ResponsiveContainer width="100%" height={160}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={40}
            outerRadius={65}
            paddingAngle={2}
            dataKey="value"
            labelLine={false}
          >
            {data.map((entry) => {
              // CLS_COLORS에 없는 key에 대한 fallback
              const originalCls = Object.keys(CLS_LABELS).find(
                (k) => CLS_LABELS[k] === entry.name
              ) ?? '';
              return (
                <Cell
                  key={`cell-${entry.name}`}
                  fill={CLS_COLORS[originalCls] ?? '#999'}
                />
              );
            })}
          </Pie>
          <Tooltip
            formatter={(value: number, name: string, props: { payload?: { investedPct?: number } }) =>
              [`${value}종목 (${props.payload?.investedPct?.toFixed(1) ?? 0}%)`, name]
            }
          />
          <Legend iconSize={10} iconType="circle" wrapperStyle={{ fontSize: '0.75rem' }} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
