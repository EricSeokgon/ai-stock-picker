// 포트폴리오 가치 시계열 차트 컴포넌트 (SPEC-STOCK-038)
import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

interface ValueDataPoint {
  date: string;
  total_value_krw: number;
}

interface DashboardValueChartProps {
  data: ValueDataPoint[];
  loading: boolean;
}

export default function DashboardValueChart({ data, loading }: DashboardValueChartProps) {
  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '200px' }}>
        <span style={{ color: '#6b7280' }}>로딩 중...</span>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '200px' }}>
        <span style={{ color: '#9ca3af' }}>표시할 가치 데이터가 없습니다.</span>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 11, fill: '#6b7280' }}
          tickFormatter={(v: string) => v.slice(5)} // "YYYY-MM-DD" → "MM-DD"
        />
        <YAxis
          tick={{ fontSize: 11, fill: '#6b7280' }}
          tickFormatter={(v: number) => `${(v / 10000).toFixed(0)}만`}
        />
        <Tooltip
          formatter={(value: number) =>
            [`${value.toLocaleString()}원`, '포트폴리오 가치']
          }
        />
        <Line
          type="monotone"
          dataKey="total_value_krw"
          stroke="#3b82f6"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
