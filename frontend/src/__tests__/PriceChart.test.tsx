// PriceChart 컴포넌트 테스트
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { PriceChart } from '../components/PriceChart';
import type { StockPricesResponse } from '../api/stocks';

vi.mock('../api/stocks', () => ({
  fetchStockPrices: vi.fn(),
  searchStocks: vi.fn(),
}));

// Recharts ResizeObserver 관련 경고 억제
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

import { fetchStockPrices } from '../api/stocks';

const mockPricesAvailable: StockPricesResponse = {
  krx_code: '005930',
  days: 30,
  prices: [
    { date: '2026-05-01', close: 70000 },
    { date: '2026-05-02', close: 71000 },
    { date: '2026-05-05', close: 72000 },
  ],
  available: true,
};

describe('PriceChart', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('가격 데이터가 있으면 차트 레이블을 렌더링한다', async () => {
    (fetchStockPrices as ReturnType<typeof vi.fn>).mockResolvedValue(mockPricesAvailable);

    render(<PriceChart krxCode="005930" />);

    await waitFor(() => {
      expect(screen.getByText(/주가/)).toBeInTheDocument();
    });
  });

  it('available=false 시 폴백 메시지를 표시한다', async () => {
    (fetchStockPrices as ReturnType<typeof vi.fn>).mockResolvedValue({
      ...mockPricesAvailable,
      available: false,
      prices: [],
    });

    render(<PriceChart krxCode="005930" />);

    await waitFor(() => {
      expect(screen.getByText('차트 데이터를 불러올 수 없습니다')).toBeInTheDocument();
    });
  });

  it('prices=[] 시 폴백 메시지를 표시한다', async () => {
    (fetchStockPrices as ReturnType<typeof vi.fn>).mockResolvedValue({
      ...mockPricesAvailable,
      available: true,
      prices: [],
    });

    render(<PriceChart krxCode="005930" />);

    await waitFor(() => {
      expect(screen.getByText('차트 데이터를 불러올 수 없습니다')).toBeInTheDocument();
    });
  });

  it('로딩 중에 로딩 상태를 표시한다', () => {
    (fetchStockPrices as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}));

    render(<PriceChart krxCode="005930" />);

    expect(screen.getByRole('status', { name: /차트 로딩/ })).toBeInTheDocument();
  });

  it('API 실패 시 폴백 메시지를 표시한다', async () => {
    (fetchStockPrices as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('오류'));

    render(<PriceChart krxCode="005930" />);

    await waitFor(() => {
      expect(screen.getByText('차트 데이터를 불러올 수 없습니다')).toBeInTheDocument();
    });
  });
});
