// 벤치마크 비교 차트 컴포넌트 (SPEC-STOCK-038)
// 기존 benchmark API 응답 구조를 재사용
import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

// 라인 색상 팔레트
const LINE_COLORS = ['#3b82f6', '#f97316', '#22c55e', '#a855f7', '#ef4444'];

export default function DashboardBenchmarkChart({ data, loading }) {
  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '200px' }}>
        <span style={{ color: '#6b7280' }}>로딩 중...</span>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '200px' }}>
        <span style={{ color: '#9ca3af' }}>벤치마크 데이터가 없습니다.</span>
      </div>
    );
  }

  // 첫 번째 항목의 키에서 라인 키 목록 추출 (date 제외)
  const lineKeys = Object.keys(data[0]).filter((k) => k !== 'date');

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 11, fill: '#6b7280' }}
          tickFormatter={(v) => (typeof v === 'string' ? v.slice(5) : v)}
        />
        <YAxis tick={{ fontSize: 11, fill: '#6b7280' }} />
        <Tooltip />
        <Legend />
        {lineKeys.map((key, index) => (
          <Line
            key={key}
            type="monotone"
            dataKey={key}
            stroke={LINE_COLORS[index % LINE_COLORS.length]}
            strokeWidth={2}
            dot={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
