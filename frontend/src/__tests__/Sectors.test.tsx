// Sectors 페이지 테스트
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Sectors from '../pages/Sectors';
import * as sectorsApi from '../api/sectors';
import type { SectorRankingResponse } from '../api/sectors';

// sectors API 모킹
vi.mock('../api/sectors', () => ({
  fetchSectorRanking: vi.fn(),
  fetchSectorDetail: vi.fn(),
}));

const mockRankingData: SectorRankingResponse = {
  sort: 'score',
  limit: 10,
  sectors: [
    {
      sector: 'IT',
      trade_date: '2024-01-15',
      news_volume: 42,
      avg_sentiment: 0.35,
      trend_score: 0.62,
    },
    {
      sector: '금융',
      trade_date: '2024-01-15',
      news_volume: 28,
      avg_sentiment: 0.12,
      trend_score: 0.31,
    },
  ],
  total: 2,
};

const emptyRankingData: SectorRankingResponse = {
  sort: 'score',
  limit: 10,
  sectors: [],
  total: 0,
};

function renderSectors() {
  return render(
    <MemoryRouter>
      <Sectors />
    </MemoryRouter>,
  );
}

describe('Sectors 페이지', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('초기 로딩 상태를 표시한다', () => {
    vi.mocked(sectorsApi.fetchSectorRanking).mockReturnValue(new Promise(() => {}));
    renderSectors();
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByText('섹터 데이터를 불러오는 중...')).toBeInTheDocument();
  });

  it('API가 빈 배열을 반환하면 빈 상태 메시지를 표시한다', async () => {
    vi.mocked(sectorsApi.fetchSectorRanking).mockResolvedValue(emptyRankingData);
    renderSectors();
    await waitFor(() => {
      expect(screen.getByText(/섹터 데이터를 준비 중입니다/)).toBeInTheDocument();
    });
  });

  it('섹터 데이터가 있으면 랭킹 테이블을 렌더링한다', async () => {
    vi.mocked(sectorsApi.fetchSectorRanking).mockResolvedValue(mockRankingData);
    renderSectors();
    await waitFor(() => {
      expect(screen.getByText('IT')).toBeInTheDocument();
      expect(screen.getByText('금융')).toBeInTheDocument();
    });
  });

  it('정렬 버튼이 세 개 표시된다', async () => {
    vi.mocked(sectorsApi.fetchSectorRanking).mockResolvedValue(mockRankingData);
    renderSectors();
    await waitFor(() => {
      expect(screen.getByText('트렌드 점수')).toBeInTheDocument();
      expect(screen.getByText('감성 점수')).toBeInTheDocument();
      expect(screen.getByText('뉴스 볼륨')).toBeInTheDocument();
    });
  });

  it('정렬 버튼 클릭 시 활성 상태(aria-pressed)가 변경된다', async () => {
    vi.mocked(sectorsApi.fetchSectorRanking).mockResolvedValue(mockRankingData);
    renderSectors();

    await waitFor(() => {
      expect(screen.getByRole('group', { name: '정렬 기준 선택' })).toBeInTheDocument();
    });

    // 정렬 컨트롤 그룹 내 버튼만 조회
    const sortGroup = screen.getByRole('group', { name: '정렬 기준 선택' });
    const sentimentBtn = sortGroup.querySelector('button[aria-pressed]') as HTMLElement;
    // 첫 번째(트렌드 점수)가 기본 활성, 두 번째(감성 점수) 클릭
    const buttons = sortGroup.querySelectorAll('button');
    const sentimentButton = buttons[1] as HTMLElement;
    expect(sentimentButton).toHaveAttribute('aria-pressed', 'false');
    fireEvent.click(sentimentButton);
    expect(sentimentButton).toHaveAttribute('aria-pressed', 'true');
    // sentimentBtn 참조 사용하지 않도록 처리
    expect(sentimentBtn).toBeTruthy();
  });

  it('행 클릭 시 섹터 상세 패널이 열린다', async () => {
    vi.mocked(sectorsApi.fetchSectorRanking).mockResolvedValue(mockRankingData);
    vi.mocked(sectorsApi.fetchSectorDetail).mockResolvedValue({
      sector: 'IT',
      days: 7,
      trends: [],
      stocks: [],
      total_stocks: 0,
    });
    renderSectors();

    await waitFor(() => {
      expect(screen.getByText('IT')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('IT'));

    await waitFor(() => {
      expect(screen.getByText('IT 섹터 상세')).toBeInTheDocument();
    });
  });

  it('API 오류 발생 시 오류 메시지를 표시한다', async () => {
    vi.mocked(sectorsApi.fetchSectorRanking).mockRejectedValue(new Error('네트워크 오류'));
    renderSectors();
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText(/섹터 데이터를 불러오는 중 오류가 발생했습니다/)).toBeInTheDocument();
    });
  });

  it('면책 조항 텍스트가 표시된다', async () => {
    vi.mocked(sectorsApi.fetchSectorRanking).mockResolvedValue(mockRankingData);
    renderSectors();
    await waitFor(() => {
      expect(screen.getByText(/본 섹터 분석은 투자 권유가 아닌 정보 제공 목적입니다/)).toBeInTheDocument();
    });
  });
});
