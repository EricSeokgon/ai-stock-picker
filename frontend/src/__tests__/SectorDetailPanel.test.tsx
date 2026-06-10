// SectorDetailPanel 컴포넌트 테스트
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { SectorDetailPanel } from '../components/SectorDetailPanel';
import * as sectorsApi from '../api/sectors';
import type { SectorDetailResponse } from '../api/sectors';

vi.mock('../api/sectors', () => ({
  fetchSectorRanking: vi.fn(),
  fetchSectorDetail: vi.fn(),
}));

const mockDetailData: SectorDetailResponse = {
  sector: 'IT',
  days: 7,
  trends: [
    { sector: 'IT', trade_date: '2024-01-15', trend_score: 0.62, news_volume: 42, avg_sentiment: 0.35 },
    { sector: 'IT', trade_date: '2024-01-14', trend_score: 0.55, news_volume: 38, avg_sentiment: 0.28 },
  ],
  stocks: [
    { krx_code: '005930', mention_count: 15 },
    { krx_code: '000660', mention_count: 8 },
  ],
  total_stocks: 2,
};

const mockDetailNoTrends: SectorDetailResponse = {
  sector: 'IT',
  days: 7,
  trends: [],
  stocks: [],
  total_stocks: 0,
};

function renderPanel(sector = 'IT', onClose = vi.fn()) {
  return render(
    <MemoryRouter>
      <SectorDetailPanel sector={sector} onClose={onClose} />
    </MemoryRouter>,
  );
}

describe('SectorDetailPanel 컴포넌트', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('섹터 이름을 타이틀에 표시한다', async () => {
    vi.mocked(sectorsApi.fetchSectorDetail).mockResolvedValue(mockDetailData);
    renderPanel('IT');
    await waitFor(() => {
      expect(screen.getByText('IT 섹터 상세')).toBeInTheDocument();
    });
  });

  it('트렌드 데이터가 없으면 "트렌드 데이터 없음" 메시지를 표시한다', async () => {
    vi.mocked(sectorsApi.fetchSectorDetail).mockResolvedValue(mockDetailNoTrends);
    renderPanel();
    await waitFor(() => {
      expect(screen.getByTestId('no-trend-data')).toBeInTheDocument();
    });
  });

  it('종목 목록이 표시된다', async () => {
    vi.mocked(sectorsApi.fetchSectorDetail).mockResolvedValue(mockDetailData);
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('005930')).toBeInTheDocument();
      expect(screen.getByText('000660')).toBeInTheDocument();
    });
  });

  it('닫기 버튼 클릭 시 onClose 가 호출된다', async () => {
    vi.mocked(sectorsApi.fetchSectorDetail).mockResolvedValue(mockDetailData);
    const onClose = vi.fn();
    renderPanel('IT', onClose);

    await waitFor(() => {
      expect(screen.getByText('IT 섹터 상세')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: '닫기' }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('총 종목 수가 표시된다', async () => {
    vi.mocked(sectorsApi.fetchSectorDetail).mockResolvedValue(mockDetailData);
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('총 2개 종목')).toBeInTheDocument();
    });
  });
});
