// 섹터별 히트맵(바 차트) 컴포넌트 — 수익률에 따라 색상 표시 (SPEC-STOCK-038)
import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  ResponsiveContainer,
} from 'recharts';

// 수익률에 따른 색상 반환: 양수 → 초록, 음수 → 빨강
function getColor(returnPct) {
  if (returnPct > 0) return '#22c55e';
  if (returnPct < 0) return '#ef4444';
  return '#94a3b8';
}

export default function DashboardSectorHeatmap({ sectors, loading }) {
  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '200px' }}>
        <span style={{ color: '#6b7280' }}>로딩 중...</span>
      </div>
    );
  }

  if (sectors.length === 0) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '200px' }}>
        <span style={{ color: '#9ca3af' }}>섹터 데이터가 없습니다.</span>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={sectors} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
        <XAxis dataKey="sector" tick={{ fontSize: 11, fill: '#6b7280' }} />
        <YAxis
          tick={{ fontSize: 11, fill: '#6b7280' }}
          tickFormatter={(v) => `${(v / 10000).toFixed(0)}만`}
        />
        <Tooltip
          formatter={(value, name) => {
            if (name === 'value_krw') return [`${value.toLocaleString()}원`, '평가액'];
            return [value, name];
          }}
        />
        <Bar dataKey="value_krw">
          {sectors.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={getColor(entry.return_pct)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
