// StockSearchBar 컴포넌트 테스트
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { StockSearchBar } from '../components/StockSearchBar';
import type { StockSearchResponse } from '../api/stocks';

vi.mock('../api/stocks', () => ({
  searchStocks: vi.fn(),
}));

import { searchStocks } from '../api/stocks';

const mockResults: StockSearchResponse = {
  query: '삼성',
  results: [
    { krx_code: '005930', name: '삼성전자', in_recommendations: true },
    { krx_code: '005935', name: '삼성전자우', in_recommendations: false },
  ],
  total: 2,
};

// 테스트 전략: fake timer로 debounce skip 후 real timer로 전환하여 waitFor 동작 보장
function setupFakeTimers() {
  vi.useFakeTimers();
}

function flushDebounceAndSwitch() {
  vi.advanceTimersByTime(400);
  vi.useRealTimers();
}

describe('StockSearchBar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('검색 입력 필드를 렌더링한다', () => {
    render(<StockSearchBar onSelect={vi.fn()} />);
    expect(screen.getByRole('searchbox', { name: /종목 검색 입력/ })).toBeInTheDocument();
  });

  it('입력 시 debounce 후 API를 호출한다', async () => {
    setupFakeTimers();
    (searchStocks as ReturnType<typeof vi.fn>).mockResolvedValue(mockResults);

    render(<StockSearchBar onSelect={vi.fn()} />);
    const input = screen.getByRole('searchbox');

    fireEvent.change(input, { target: { value: '삼성' } });

    // debounce 전: 아직 호출 안 됨
    expect(searchStocks).not.toHaveBeenCalled();

    flushDebounceAndSwitch();

    await waitFor(() => {
      expect(searchStocks).toHaveBeenCalledWith('삼성');
    });
  });

  it('결과에 "추천" 배지를 표시한다 (in_recommendations=true)', async () => {
    setupFakeTimers();
    (searchStocks as ReturnType<typeof vi.fn>).mockResolvedValue(mockResults);

    render(<StockSearchBar onSelect={vi.fn()} />);
    const input = screen.getByRole('searchbox');

    fireEvent.change(input, { target: { value: '삼성' } });
    flushDebounceAndSwitch();

    await waitFor(() => {
      expect(screen.getByText('추천')).toBeInTheDocument();
    });

    expect(screen.getByText('삼성전자')).toBeInTheDocument();
    expect(screen.getByText('005930')).toBeInTheDocument();
  });

  it('결과가 없을 때 "검색 결과가 없습니다"를 표시한다', async () => {
    setupFakeTimers();
    (searchStocks as ReturnType<typeof vi.fn>).mockResolvedValue({
      query: '없는종목',
      results: [],
      total: 0,
    });

    render(<StockSearchBar onSelect={vi.fn()} />);
    const input = screen.getByRole('searchbox');

    fireEvent.change(input, { target: { value: '없는종목' } });
    flushDebounceAndSwitch();

    await waitFor(() => {
      expect(screen.getByText('검색 결과가 없습니다')).toBeInTheDocument();
    });
  });

  it('결과 클릭 시 onSelect(krxCode)가 호출된다', async () => {
    setupFakeTimers();
    (searchStocks as ReturnType<typeof vi.fn>).mockResolvedValue(mockResults);
    const onSelect = vi.fn();

    render(<StockSearchBar onSelect={onSelect} />);
    const input = screen.getByRole('searchbox');

    fireEvent.change(input, { target: { value: '삼성' } });
    flushDebounceAndSwitch();

    await waitFor(() => {
      expect(screen.getByText('삼성전자')).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText('삼성전자'));
    expect(onSelect).toHaveBeenCalledWith('005930');
  });

  it('API 실패 시 오류 메시지를 표시한다', async () => {
    setupFakeTimers();
    (searchStocks as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('네트워크 오류'));

    render(<StockSearchBar onSelect={vi.fn()} />);
    const input = screen.getByRole('searchbox');

    fireEvent.change(input, { target: { value: '삼성' } });
    flushDebounceAndSwitch();

    await waitFor(() => {
      expect(screen.getByText('검색 중 오류가 발생했습니다')).toBeInTheDocument();
    });
  });
});
