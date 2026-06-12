// SPEC-STOCK-017 PerformanceDonutChart 렌더링 테스트
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { PerformanceDonutChart } from '../components/PerformanceDonutChart';
import type { ClassificationSummary } from '../api/portfolio';

function makeSummary(overrides: Partial<ClassificationSummary> = {}): ClassificationSummary {
  return {
    high: { count: 0, invested: 0, invested_pct: 0 },
    normal: { count: 0, invested: 0, invested_pct: 0 },
    low: { count: 0, invested: 0, invested_pct: 0 },
    ...overrides,
  };
}

describe('PerformanceDonutChart', () => {
  it('데이터가 없으면 "성과 데이터 없음" 텍스트를 표시한다', () => {
    render(<PerformanceDonutChart summary={makeSummary()} />);
    expect(screen.getByText('성과 데이터 없음')).toBeDefined();
  });

  it('데이터가 있으면 제목 "성과 분류 비중"을 표시한다', () => {
    const summary = makeSummary({
      high: { count: 2, invested: 1400000, invested_pct: 70 },
      normal: { count: 1, invested: 600000, invested_pct: 30 },
    });
    render(<PerformanceDonutChart summary={summary} />);
    expect(screen.getByText('성과 분류 비중')).toBeDefined();
  });

  it('count=0인 그룹은 차트 데이터에서 제외된다', () => {
    // low count=0 → "저수익" 레이블이 없어야 함
    const summary = makeSummary({
      high: { count: 1, invested: 700000, invested_pct: 100 },
    });
    const { queryByText } = render(<PerformanceDonutChart summary={summary} />);
    // recharts Legend에서 "저수익" 텍스트가 없어야 함
    expect(queryByText('저수익')).toBeNull();
  });
});
