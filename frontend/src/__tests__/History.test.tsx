// History 페이지 테스트
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import History from '../pages/History';
import * as recommendationsApi from '../api/recommendations';
import type { RecommendationHistoryResponse } from '../api/recommendations';

// getRecommendationHistory 모킹
vi.mock('../api/recommendations', () => ({
  getRecommendationHistory: vi.fn(),
}));

const mockHistoryData: RecommendationHistoryResponse = {
  days: 7,
  groups: [
    {
      date: '2026-06-09',
      recommendations: [
        {
          rank: 1,
          krx_code: '005930',
          total_score: 0.85,
          sentiment_score: 0.9,
          volume_score: 0.8,
          momentum_score: 0.85,
          anomaly_score: 0.7,
          reasoning: '반도체 섹터 상승 기대감',
        },
        {
          rank: 2,
          krx_code: '000660',
          total_score: 0.72,
          sentiment_score: 0.75,
          volume_score: 0.7,
          momentum_score: 0.68,
          anomaly_score: 0.65,
          reasoning: '외국인 매수세 유입',
        },
      ],
    },
    {
      date: '2026-06-08',
      recommendations: [
        {
          rank: 1,
          krx_code: '035420',
          total_score: 0.78,
          sentiment_score: 0.8,
          volume_score: 0.75,
          momentum_score: 0.77,
          anomaly_score: 0.72,
          reasoning: '플랫폼 광고 수익 회복',
        },
      ],
    },
  ],
};

function renderHistory() {
  return render(
    <MemoryRouter>
      <History />
    </MemoryRouter>,
  );
}

describe('History 페이지', () => {
  beforeEach(() => {
    vi.mocked(recommendationsApi.getRecommendationHistory).mockResolvedValue(mockHistoryData);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('초기 로딩 상태를 렌더링한다', () => {
    // 프라미스를 해소하지 않은 채로 렌더
    vi.mocked(recommendationsApi.getRecommendationHistory).mockReturnValue(new Promise(() => {}));
    renderHistory();
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByText('히스토리를 불러오는 중...')).toBeInTheDocument();
  });

  it('날짜별로 그룹화된 추천 목록을 렌더링한다', async () => {
    renderHistory();
    await waitFor(() => {
      expect(screen.getByText('2026-06-09')).toBeInTheDocument();
      expect(screen.getByText('2026-06-08')).toBeInTheDocument();
    });
    // krx_code는 span 안에 렌더링되므로 getAllByText 사용
    expect(screen.getAllByText('005930').length).toBeGreaterThan(0);
    expect(screen.getAllByText('000660').length).toBeGreaterThan(0);
    expect(screen.getAllByText('035420').length).toBeGreaterThan(0);
  });

  it('면책 고지 문구를 표시한다', async () => {
    renderHistory();
    await waitFor(() => {
      expect(
        screen.getByText(/본 히스토리는 투자 권유가 아닌 정보 제공 목적입니다/),
      ).toBeInTheDocument();
    });
  });

  it('그룹이 없을 때 빈 상태 메시지를 표시한다', async () => {
    vi.mocked(recommendationsApi.getRecommendationHistory).mockResolvedValue({
      days: 7,
      groups: [],
    });
    renderHistory();
    await waitFor(() => {
      expect(screen.getByText('히스토리 데이터가 없습니다.')).toBeInTheDocument();
    });
  });

  it('기간 탭 클릭 시 days 파라미터를 변경한다', async () => {
    renderHistory();
    // 초기 로드 완료 대기
    await waitFor(() => {
      expect(screen.getByText('2026-06-09')).toBeInTheDocument();
    });

    // "14일" 탭 클릭
    const tab14 = screen.getByRole('tab', { name: '14일' });
    fireEvent.click(tab14);

    await waitFor(() => {
      expect(recommendationsApi.getRecommendationHistory).toHaveBeenCalledWith(14);
    });
    expect(tab14).toHaveAttribute('aria-selected', 'true');
  });

  it('7일 탭이 기본 선택 상태이다', async () => {
    renderHistory();
    const tab7 = screen.getByRole('tab', { name: '7일' });
    expect(tab7).toHaveAttribute('aria-selected', 'true');
  });

  it('API 오류 시 에러 메시지를 표시한다', async () => {
    vi.mocked(recommendationsApi.getRecommendationHistory).mockRejectedValue(
      new Error('API 오류: 500'),
    );
    renderHistory();
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText(/API 오류: 500/)).toBeInTheDocument();
    });
  });

  it('추천 종목 점수를 백분율로 표시한다', async () => {
    renderHistory();
    await waitFor(() => {
      // 0.85 → 85.0점
      expect(screen.getByText('85.0점')).toBeInTheDocument();
    });
  });
});
