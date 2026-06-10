// 주가 차트 — Recharts LineChart로 종가 N일 이력 표시
import { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { fetchStockPrices } from '../api/stocks';
import type { PricePoint } from '../api/stocks';

export interface PriceChartProps {
  krxCode: string;
  days?: number;
}

// 날짜 포맷: YYYY-MM-DD → MM/DD
function formatDate(dateStr: string): string {
  const parts = dateStr.split('-');
  if (parts.length >= 3) return `${parts[1]}/${parts[2]}`;
  return dateStr;
}

// 가격 포맷: 숫자 → 원화 문자열
function formatPrice(val: number | string): string {
  const num = typeof val === 'string' ? parseFloat(val) : val;
  return `${num.toLocaleString('ko-KR')}원`;
}

// @MX:ANCHOR: [AUTO] PriceChart — StockDetail, StockDetailPage에서 참조
// @MX:REASON: 차트 실패가 부모 컴포넌트 렌더링에 영향을 주면 안 됨; 독립적 오류 처리 필요

export function PriceChart({ krxCode, days = 30 }: PriceChartProps) {
  const [prices, setPrices] = useState<PricePoint[]>([]);
  const [available, setAvailable] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(false);

    fetchStockPrices(krxCode, days)
      .then((data) => {
        if (cancelled) return;
        setAvailable(data.available);
        setPrices(data.prices);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [krxCode, days]);

  const fallback = (msg: string) => (
    <div
      style={{
        padding: '1.5rem',
        textAlign: 'center',
        color: '#888',
        fontSize: '0.85rem',
        backgroundColor: '#fafafa',
        borderRadius: '6px',
        border: '1px dashed #ddd',
      }}
    >
      {msg}
    </div>
  );

  if (loading) {
    return (
      <div
        role="status"
        aria-label="차트 로딩 중"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '180px',
          gap: '0.5rem',
          color: '#888',
          fontSize: '0.85rem',
        }}
      >
        <span
          style={{
            width: '16px',
            height: '16px',
            border: '2px solid #ddd',
            borderTop: '2px solid #1976d2',
            borderRadius: '50%',
            animation: 'spin 0.7s linear infinite',
            display: 'inline-block',
          }}
        />
        <span>차트 불러오는 중...</span>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (error || available === false || prices.length === 0) {
    return fallback('차트 데이터를 불러올 수 없습니다');
  }

  return (
    <div>
      <p style={{ margin: '0 0 0.5rem', fontSize: '0.8rem', fontWeight: 600, color: '#333' }}>
        주가 ({days}일)
      </p>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart
          data={prices}
          margin={{ top: 4, right: 8, left: 8, bottom: 4 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="date"
            tickFormatter={formatDate}
            tick={{ fontSize: 10, fill: '#888' }}
            interval="preserveStartEnd"
          />
          <YAxis
            tickFormatter={(v: number) => v.toLocaleString('ko-KR')}
            tick={{ fontSize: 10, fill: '#888' }}
            width={64}
          />
          <Tooltip
            formatter={(val: number) => [formatPrice(val), '종가']}
            labelFormatter={(label: string) => `날짜: ${label}`}
          />
          <Line
            type="monotone"
            dataKey="close"
            stroke="#1976d2"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
