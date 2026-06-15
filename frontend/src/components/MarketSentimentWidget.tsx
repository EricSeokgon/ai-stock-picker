// SPEC-STOCK-021: AI 시장 템포 위젯
// REQ-NEWS-SENT-002: 시장 전체 감성 시각화 (avg_score, label, positive/negative/neutral 비율)
import { useEffect, useState } from 'react';
import type { MarketSentimentResponse } from '../types';
import { fetchMarketSentiment } from '../api/news';

// 5단계 라벨 배지 스타일
function getLabelStyle(label: string | null): { backgroundColor: string; color: string } {
  switch (label) {
    case '매우긍정':
      return { backgroundColor: '#1b5e20', color: '#fff' };
    case '긍정':
      return { backgroundColor: '#e8f5e9', color: '#2e7d32' };
    case '중립':
      return { backgroundColor: '#f5f5f5', color: '#616161' };
    case '부정':
      return { backgroundColor: '#fff3e0', color: '#e65100' };
    case '매우부정':
      return { backgroundColor: '#ffebee', color: '#c62828' };
    default:
      return { backgroundColor: '#f5f5f5', color: '#9e9e9e' };
  }
}

export function MarketSentimentWidget() {
  const [data, setData] = useState<MarketSentimentResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMarketSentiment()
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div
        role="status"
        aria-label="시장 감성 로딩 중"
        style={{ padding: '16px', color: '#9e9e9e' }}
      >
        시장 감성 분석 중...
      </div>
    );
  }

  if (error) {
    return (
      <div role="alert" style={{ padding: '16px', color: '#c62828' }}>
        시장 감성 데이터 로드 실패: {error}
      </div>
    );
  }

  if (!data || data.total === 0) {
    return (
      <div
        role="region"
        aria-label="시장 감성 위젯"
        style={{ padding: '16px', color: '#9e9e9e' }}
      >
        분석된 뉴스 데이터가 없습니다.
      </div>
    );
  }

  const labelStyle = getLabelStyle(data.label);
  const totalSafe = data.total > 0 ? data.total : 1;
  const positiveRatio = Math.round((data.positive / totalSafe) * 100);
  const negativeRatio = Math.round((data.negative / totalSafe) * 100);
  const neutralRatio = 100 - positiveRatio - negativeRatio;

  return (
    <div
      role="region"
      aria-label="시장 감성 위젯"
      style={{
        padding: '16px',
        border: '1px solid #e0e0e0',
        borderRadius: '8px',
        background: '#fff',
      }}
    >
      <h3 style={{ margin: '0 0 12px', fontSize: '14px', color: '#424242' }}>
        AI 시장 템포 (최근 24시간)
      </h3>

      {/* 라벨 배지 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
        <span
          aria-label={`시장 감성 라벨: ${data.label ?? '데이터 없음'}`}
          style={{
            ...labelStyle,
            padding: '4px 10px',
            borderRadius: '12px',
            fontSize: '13px',
            fontWeight: 600,
          }}
        >
          {data.label ?? '데이터 없음'}
        </span>
        {data.avg_score !== null && (
          <span style={{ fontSize: '12px', color: '#757575' }}>
            평균 점수 {data.avg_score.toFixed(2)}
          </span>
        )}
      </div>

      {/* 비율 바 */}
      <div style={{ marginBottom: '8px' }}>
        <div
          role="img"
          aria-label={`긍정 ${positiveRatio}%, 부정 ${negativeRatio}%, 중립 ${neutralRatio}%`}
          style={{ display: 'flex', height: '8px', borderRadius: '4px', overflow: 'hidden' }}
        >
          <div style={{ width: `${positiveRatio}%`, backgroundColor: '#2e7d32' }} />
          <div style={{ width: `${neutralRatio}%`, backgroundColor: '#bdbdbd' }} />
          <div style={{ width: `${negativeRatio}%`, backgroundColor: '#c62828' }} />
        </div>
      </div>

      {/* 건수 */}
      <div style={{ display: 'flex', gap: '12px', fontSize: '12px', color: '#616161' }}>
        <span>긍정 {data.positive}건</span>
        <span>중립 {data.neutral}건</span>
        <span>부정 {data.negative}건</span>
        <span style={{ marginLeft: 'auto' }}>총 {data.total}건</span>
      </div>
    </div>
  );
}

export default MarketSentimentWidget;
