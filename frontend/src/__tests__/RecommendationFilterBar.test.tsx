// RecommendationFilterBar 컴포넌트 테스트
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RecommendationFilterBar, DEFAULT_FILTERS } from '../components/RecommendationFilterBar';
import type { FilterState } from '../components/RecommendationFilterBar';

const defaultFilters: FilterState = { ...DEFAULT_FILTERS };

describe('RecommendationFilterBar', () => {
  it('섹터 드롭다운에 "전체" 옵션과 전달된 섹터들이 표시된다', () => {
    render(
      <RecommendationFilterBar
        sectors={['IT', '금융', '바이오']}
        filters={defaultFilters}
        onFilterChange={vi.fn()}
      />,
    );
    const select = screen.getByRole('combobox', { name: /섹터 선택/i });
    expect(select).toBeDefined();
    expect(screen.getByText('전체')).toBeDefined();
    expect(screen.getByText('IT')).toBeDefined();
    expect(screen.getByText('금융')).toBeDefined();
    expect(screen.getByText('바이오')).toBeDefined();
  });

  it('섹터 선택 시 onFilterChange가 새 sector 값과 함께 호출된다', async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    render(
      <RecommendationFilterBar
        sectors={['IT', '금융']}
        filters={defaultFilters}
        onFilterChange={handleChange}
      />,
    );
    const select = screen.getByRole('combobox', { name: /섹터 선택/i });
    await user.selectOptions(select, 'IT');
    expect(handleChange).toHaveBeenCalledWith({ ...defaultFilters, sector: 'IT' });
  });

  it('정렬 선택 변경 시 onFilterChange가 새 sort 값과 함께 호출된다', async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    render(
      <RecommendationFilterBar
        sectors={[]}
        filters={defaultFilters}
        onFilterChange={handleChange}
      />,
    );
    const select = screen.getByRole('combobox', { name: /정렬 기준 선택/i });
    await user.selectOptions(select, 'sentiment');
    expect(handleChange).toHaveBeenCalledWith({ ...defaultFilters, sort: 'sentiment' });
  });

  it('필터 초기화 버튼 클릭 시 onFilterChange가 DEFAULT_FILTERS와 함께 호출된다', async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    const customFilters: FilterState = { sector: 'IT', sort: 'sentiment', minScore: 0.5 };
    render(
      <RecommendationFilterBar
        sectors={['IT']}
        filters={customFilters}
        onFilterChange={handleChange}
      />,
    );
    const resetBtn = screen.getByRole('button', { name: /필터 초기화/i });
    await user.click(resetBtn);
    expect(handleChange).toHaveBeenCalledWith({ ...DEFAULT_FILTERS });
  });

  it('isLoading=true일 때 "필터 적용 중..." 메시지가 표시된다', () => {
    render(
      <RecommendationFilterBar
        sectors={[]}
        filters={defaultFilters}
        onFilterChange={vi.fn()}
        isLoading={true}
      />,
    );
    expect(screen.getByText('필터 적용 중...')).toBeDefined();
  });

  it('isLoading=false일 때 "필터 적용 중..." 메시지가 없다', () => {
    render(
      <RecommendationFilterBar
        sectors={[]}
        filters={defaultFilters}
        onFilterChange={vi.fn()}
        isLoading={false}
      />,
    );
    expect(screen.queryByText('필터 적용 중...')).toBeNull();
  });

  it('최소 점수 변경 시 onFilterChange가 새 minScore와 함께 호출된다', async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    render(
      <RecommendationFilterBar
        sectors={[]}
        filters={defaultFilters}
        onFilterChange={handleChange}
      />,
    );
    const input = screen.getByRole('spinbutton', { name: /최소 점수/i });
    await user.clear(input);
    await user.type(input, '0.5');
    // 마지막 호출이 minScore: 0.5를 포함해야 함
    const lastCall = handleChange.mock.calls[handleChange.mock.calls.length - 1][0] as FilterState;
    expect(lastCall.minScore).toBeCloseTo(0.5);
  });
});
