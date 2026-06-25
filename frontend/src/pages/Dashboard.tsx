// 시장 시각화 대시보드 페이지 (SPEC-STOCK-038)
// 4개 차트 — 가치 시계열, 섹터 히트맵, 자산 배분, 벤치마크 비교
import React, { useState, useEffect, useCallback } from 'react';
import DashboardValueChart from '../components/DashboardValueChart';
import DashboardSectorHeatmap from '../components/DashboardSectorHeatmap';
import DashboardAssetAllocation from '../components/DashboardAssetAllocation';
import DashboardBenchmarkChart from '../components/DashboardBenchmarkChart';
import {
  fetchValueSeries,
  fetchSectorSummary,
  fetchAssetAllocation,
  ALLOWED_DAYS,
  type AllowedDays,
  type ValueDataPoint,
  type SectorItem,
  type AssetTypeItem,
} from '../api/dashboard';

interface DashboardProps {
  portfolioId: number;
  token: string;
  // 벤치마크 데이터 — 기존 benchmark API에서 가져옴 (선택)
  benchmarkData?: any[];
  benchmarkLoading?: boolean;
}

const PERIOD_LABELS: Record<AllowedDays, string> = {
  7: '7일',
  30: '30일',
  90: '90일',
  365: '1년',
};

export default function Dashboard({
  portfolioId,
  token,
  benchmarkData = [],
  benchmarkLoading = false,
}: DashboardProps) {
  const [period, setPeriod] = useState<AllowedDays>(30);

  // 가치 시계열 상태
  const [valueData, setValueData] = useState<ValueDataPoint[]>([]);
  const [valueLoading, setValueLoading] = useState(false);

  // 섹터 상태
  const [sectors, setSectors] = useState<SectorItem[]>([]);
  const [sectorLoading, setSectorLoading] = useState(false);

  // 자산 배분 상태
  const [assets, setAssets] = useState<AssetTypeItem[]>([]);
  const [assetLoading, setAssetLoading] = useState(false);

  // 가치 시계열 + 섹터 + 자산 배분 조회
  const loadDashboardData = useCallback(async () => {
    if (!portfolioId || !token) return;

    setValueLoading(true);
    setSectorLoading(true);
    setAssetLoading(true);

    // 3개 API 병렬 호출
    const [valueResult, sectorResult, assetResult] = await Promise.allSettled([
      fetchValueSeries(portfolioId, period, token),
      fetchSectorSummary(portfolioId, token),
      fetchAssetAllocation(portfolioId, token),
    ]);

    setValueLoading(false);
    setSectorLoading(false);
    setAssetLoading(false);

    if (valueResult.status === 'fulfilled') {
      setValueData(valueResult.value.data);
    }
    if (sectorResult.status === 'fulfilled') {
      setSectors(sectorResult.value.sectors);
    }
    if (assetResult.status === 'fulfilled') {
      setAssets(assetResult.value.assets);
    }
  }, [portfolioId, token, period]);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <h2 style={{ fontSize: '22px', fontWeight: 700, marginBottom: '16px', color: '#111827' }}>
        시장 시각화 대시보드
      </h2>

      {/* 기간 선택 탭 */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '24px' }}>
        {ALLOWED_DAYS.map((d) => (
          <button
            key={d}
            onClick={() => setPeriod(d)}
            style={{
              padding: '6px 16px',
              borderRadius: '20px',
              border: 'none',
              cursor: 'pointer',
              fontWeight: period === d ? 700 : 400,
              background: period === d ? '#3b82f6' : '#f3f4f6',
              color: period === d ? '#fff' : '#374151',
              fontSize: '14px',
              transition: 'all 0.15s',
            }}
          >
            {PERIOD_LABELS[d]}
          </button>
        ))}
      </div>

      {/* 2×2 차트 그리드 */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: '20px',
        }}
      >
        {/* 가치 시계열 */}
        <div style={cardStyle}>
          <h3 style={cardTitleStyle}>포트폴리오 가치 추이</h3>
          <DashboardValueChart data={valueData} loading={valueLoading} />
        </div>

        {/* 섹터 히트맵 */}
        <div style={cardStyle}>
          <h3 style={cardTitleStyle}>섹터별 평가액</h3>
          <DashboardSectorHeatmap sectors={sectors} loading={sectorLoading} />
        </div>

        {/* 자산 배분 */}
        <div style={cardStyle}>
          <h3 style={cardTitleStyle}>자산유형 배분</h3>
          <DashboardAssetAllocation assets={assets} loading={assetLoading} />
        </div>

        {/* 벤치마크 비교 */}
        <div style={cardStyle}>
          <h3 style={cardTitleStyle}>벤치마크 비교</h3>
          <DashboardBenchmarkChart data={benchmarkData} loading={benchmarkLoading} />
        </div>
      </div>
    </div>
  );
}

const cardStyle: React.CSSProperties = {
  background: '#fff',
  border: '1px solid #e5e7eb',
  borderRadius: '12px',
  padding: '20px',
  boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
};

const cardTitleStyle: React.CSSProperties = {
  fontSize: '15px',
  fontWeight: 600,
  color: '#374151',
  marginBottom: '12px',
};
