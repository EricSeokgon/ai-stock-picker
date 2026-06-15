// SPEC-STOCK-021: MarketSentimentWidget 컴포넌트 테스트
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MarketSentimentWidget } from '../components/MarketSentimentWidget';
import type { MarketSentimentResponse } from '../types';

// fetchMarketSentiment mock
vi.mock('../api/news', () => ({
  fetchMarketSentiment: vi.fn(),
  fetchNewsByStock: vi.fn(),
  triggerNewsFetch: vi.fn(),
}));

import { fetchMarketSentiment } from '../api/news';

const mockFetch = fetchMarketSentiment as ReturnType<typeof vi.fn>;

beforeEach(() => {
  vi.clearAllMocks();
});

describe('MarketSentimentWidget', () => {
  it('로딩 중 상태를 표시한다', async () => {
    // 리졸브 안 되는 Promise로 로딩 유지
    mockFetch.mockReturnValue(new Promise(() => {}));
    render(<MarketSentimentWidget />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('긍정 데이터 로드 시 라벨과 건수를 표시한다', async () => {
    const data: MarketSentimentResponse = {
      avg_score: 0.45,
      label: '긍정',
      positive: 8,
      negative: 1,
      neutral: 1,
      total: 10,
      as_of: '2026-06-15T10:00:00Z',
    };
    mockFetch.mockResolvedValue(data);

    render(<MarketSentimentWidget />);

    await waitFor(() => {
      expect(screen.getByText('긍정')).toBeInTheDocument();
    });

    expect(screen.getByText(/긍정 8건/)).toBeInTheDocument();
    expect(screen.getByText(/부정 1건/)).toBeInTheDocument();
    expect(screen.getByText(/총 10건/)).toBeInTheDocument();
    expect(screen.getByText(/0\.45/)).toBeInTheDocument();
  });

  it('total 0이면 데이터 없음 메시지를 표시한다', async () => {
    const data: MarketSentimentResponse = {
      avg_score: null,
      label: null,
      positive: 0,
      negative: 0,
      neutral: 0,
      total: 0,
      as_of: '2026-06-15T10:00:00Z',
    };
    mockFetch.mockResolvedValue(data);

    render(<MarketSentimentWidget />);

    await waitFor(() => {
      expect(screen.getByText(/분석된 뉴스 데이터가 없습니다/)).toBeInTheDocument();
    });
  });

  it('API 오류 시 에러 메시지를 표시한다', async () => {
    mockFetch.mockRejectedValue(new Error('네트워크 오류'));

    render(<MarketSentimentWidget />);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
    expect(screen.getByText(/네트워크 오류/)).toBeInTheDocument();
  });

  it('region role이 있어 접근성을 만족한다', async () => {
    const data: MarketSentimentResponse = {
      avg_score: 0.2,
      label: '긍정',
      positive: 5,
      negative: 2,
      neutral: 3,
      total: 10,
      as_of: '2026-06-15T10:00:00Z',
    };
    mockFetch.mockResolvedValue(data);

    render(<MarketSentimentWidget />);

    await waitFor(() => {
      expect(screen.getByRole('region', { name: '시장 감성 위젯' })).toBeInTheDocument();
    });
  });

  it('부정 데이터 시 부정 라벨을 표시한다', async () => {
    const data: MarketSentimentResponse = {
      avg_score: -0.4,
      label: '부정',
      positive: 1,
      negative: 7,
      neutral: 2,
      total: 10,
      as_of: '2026-06-15T10:00:00Z',
    };
    mockFetch.mockResolvedValue(data);

    render(<MarketSentimentWidget />);

    await waitFor(() => {
      expect(screen.getByText('부정')).toBeInTheDocument();
    });
    expect(screen.getByText(/부정 7건/)).toBeInTheDocument();
  });
});
