// StockDetailPage 테스트 — /stocks/:krxCode 라우트
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import StockDetailPage from '../pages/StockDetailPage';
import type { RecommendationDetail } from '../types';

vi.mock('../api/client', () => ({
  fetchRecommendationDetail: vi.fn(),
}));
vi.mock('../api/stocks', () => ({
  fetchStockPrices: vi.fn(),
  searchStocks: vi.fn(),
}));
vi.mock('../api/recommendations', () => ({
  fetchFeedbackSummary: vi.fn(),
  submitFeedback: vi.fn(),
  getRecommendationHistory: vi.fn(),
}));

import { fetchRecommendationDetail } from '../api/client';
import { fetchStockPrices } from '../api/stocks';
import { fetchFeedbackSummary } from '../api/recommendations';

// Recharts ResizeObserver 경고 억제
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

const mockDetail: RecommendationDetail = {
  krx_code: '005930',
  trade_date: '2026-06-01',
  total_score: 0.85,
  sentiment_score: 0.7,
  volume_score: 0.6,
  momentum_score: 0.8,
  anomaly_score: 0.5,
  reasoning: '삼성전자는 강한 매수 신호',
  contributing_news: [],
  disclaimer: '투자 참고용',
};

function renderPage(krxCode: string) {
  return render(
    <MemoryRouter initialEntries={[`/stocks/${krxCode}`]}>
      <Routes>
        <Route path="/stocks/:krxCode" element={<StockDetailPage />} />
        <Route path="/" element={<div>홈 페이지</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('StockDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (fetchStockPrices as ReturnType<typeof vi.fn>).mockResolvedValue({
      krx_code: '005930',
      days: 30,
      prices: [],
      available: false,
    });
    (fetchFeedbackSummary as ReturnType<typeof vi.fn>).mockResolvedValue({
      krx_code: '005930',
      up: 0,
      down: 0,
    });
  });

  it('krxCode 라우트 파라미터로 페이지를 렌더링한다', async () => {
    (fetchRecommendationDetail as ReturnType<typeof vi.fn>).mockResolvedValue(mockDetail);

    renderPage('005930');

    await waitFor(() => {
      expect(screen.getByText('005930')).toBeInTheDocument();
    });
  });

  it('면책 조항 텍스트를 표시한다', () => {
    (fetchRecommendationDetail as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}));

    renderPage('005930');

    expect(screen.getByText('본 정보는 투자 권유가 아닌 참고 목적입니다')).toBeInTheDocument();
  });

  it('PriceChart 컴포넌트가 포함된다 (차트 로딩 or 폴백 텍스트)', async () => {
    (fetchRecommendationDetail as ReturnType<typeof vi.fn>).mockResolvedValue(mockDetail);

    renderPage('005930');

    // PriceChart가 렌더링되면 로딩 or 폴백 메시지 중 하나가 나타남
    await waitFor(() => {
      const chartMsg =
        screen.queryByRole('status', { name: /차트 로딩/ }) ??
        screen.queryByText('차트 데이터를 불러올 수 없습니다');
      expect(chartMsg).not.toBeNull();
    });
  });

  it('FeedbackButtons 컴포넌트가 포함된다 (좋아요/싫어요 버튼)', async () => {
    (fetchRecommendationDetail as ReturnType<typeof vi.fn>).mockResolvedValue(mockDetail);

    renderPage('005930');

    await waitFor(() => {
      // FeedbackButtons가 로드되면 좋아요 버튼이 나타남
      expect(screen.getByLabelText(/좋아요/)).toBeInTheDocument();
    });
  });
});
