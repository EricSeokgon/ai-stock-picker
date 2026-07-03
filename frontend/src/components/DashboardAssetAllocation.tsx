// 자산유형별 배분 파이 차트 컴포넌트 (SPEC-STOCK-038)
import React from 'react';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface AssetTypeItem {
  asset_type: string;
  value_krw: number;
  weight_pct: number;
}

interface DashboardAssetAllocationProps {
  assets: AssetTypeItem[];
  loading: boolean;
}

// 자산유형별 색상 — 국내: 파랑, 해외: 주황
const COLORS: Record<string, string> = {
  국내: '#3b82f6',
  해외: '#f97316',
};
const FALLBACK_COLORS = ['#8b5cf6', '#ec4899', '#14b8a6'];

export default function DashboardAssetAllocation({ assets, loading }: DashboardAssetAllocationProps) {
  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '200px' }}>
        <span style={{ color: '#6b7280' }}>로딩 중...</span>
      </div>
    );
  }

  if (assets.length === 0) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '200px' }}>
        <span style={{ color: '#9ca3af' }}>자산 배분 데이터가 없습니다.</span>
      </div>
    );
  }

  const pieData = assets.map((a) => ({
    name: a.asset_type,
    value: a.value_krw,
    weight_pct: a.weight_pct,
  }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie
          data={pieData}
          cx="50%"
          cy="50%"
          outerRadius={80}
          dataKey="value"
          label={({ name, weight_pct }: { name: string; weight_pct: number }) =>
            `${name} ${weight_pct.toFixed(1)}%`
          }
        >
          {pieData.map((entry, index) => (
            <Cell
              key={`cell-${index}`}
              fill={COLORS[entry.name] ?? FALLBACK_COLORS[index % FALLBACK_COLORS.length]}
            />
          ))}
        </Pie>
        <Tooltip
          formatter={(value: number) => [`${value.toLocaleString()}원`, '평가액']}
        />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}
