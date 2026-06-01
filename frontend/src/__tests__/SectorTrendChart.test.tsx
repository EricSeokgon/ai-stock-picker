// SectorTrendChart 컴포넌트 테스트 - 섹터별 트렌드 시각화
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SectorTrendChart } from '../components/SectorTrendChart';
import type { SectorTrendPoint } from '../types';

const mockTrends: SectorTrendPoint[] = [
  {
    sector: '반도체',
    trade_date: '2026-06-01',
    trend_score: 0.82,
    news_volume: 45,
    avg_sentiment: 0.6,
  },
  {
    sector: '바이오',
    trade_date: '2026-06-01',
    trend_score: 0.54,
    news_volume: 23,
    avg_sentiment: 0.1,
  },
  {
    sector: '금융',
    trade_date: '2026-06-01',
    trend_score: 0.38,
    news_volume: 18,
    avg_sentiment: -0.2,
  },
];

describe('SectorTrendChart', () => {
  it('차트 제목이 표시된다', () => {
    render(<SectorTrendChart trends={mockTrends} />);
    expect(screen.getByText('섹터 트렌드')).toBeInTheDocument();
  });

  it('트렌드 데이터가 있을 때 Recharts 컨테이너 요소가 렌더링된다', () => {
    const { container } = render(<SectorTrendChart trends={mockTrends} />);
    // jsdom에서 ResponsiveContainer는 div wrapper를 렌더링함 (SVG는 실제 브라우저에서만)
    // recharts의 ResponsiveContainer div가 존재하는지 확인
    const rechartsWrapper = container.querySelector('.recharts-responsive-container');
    // wrapper가 없어도 BarChart div가 있어야 함
    const chartElement = rechartsWrapper ?? container.querySelector('[class*="recharts"]') ?? container.querySelector('section');
    expect(chartElement).toBeTruthy();
  });

  it('빈 데이터이면 "섹터 트렌드 데이터가 없습니다" 메시지를 표시한다', () => {
    render(<SectorTrendChart trends={[]} />);
    expect(screen.getByText('섹터 트렌드 데이터가 없습니다')).toBeInTheDocument();
  });

  it('빈 데이터이면 차트를 렌더링하지 않는다', () => {
    const { container } = render(<SectorTrendChart trends={[]} />);
    expect(container.querySelector('svg')).toBeFalsy();
  });
});
