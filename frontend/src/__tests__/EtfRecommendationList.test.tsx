// EtfRecommendationList 컴포넌트 테스트 - ETF 추천 목록
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { EtfRecommendationList } from '../components/EtfRecommendationList';
import type { RecommendationItem } from '../types';

// ETF 코드 패턴: KRX ETF는 6자리 숫자, 일반적으로 069500(KODEX 200) 등
const mockEtfItems: RecommendationItem[] = [
  {
    rank: 1,
    krx_code: '069500',
    total_score: 0.78,
    sentiment_score: 0.5,
    volume_score: 0.7,
    momentum_score: 0.6,
    anomaly_score: 0.4,
    reasoning: 'KODEX 200 ETF - 시장 전반적 상승 기대',
  },
  {
    rank: 2,
    krx_code: '102110',
    total_score: 0.65,
    sentiment_score: 0.4,
    volume_score: 0.5,
    momentum_score: 0.5,
    anomaly_score: 0.3,
    reasoning: 'TIGER 200 ETF - 안정적 포트폴리오 구성',
  },
];

describe('EtfRecommendationList', () => {
  it('ETF 목록 섹션 제목을 표시한다', () => {
    render(<EtfRecommendationList etfItems={mockEtfItems} />);
    expect(screen.getByText('ETF 추천')).toBeInTheDocument();
  });

  it('ETF 코드 목록을 렌더링한다', () => {
    render(<EtfRecommendationList etfItems={mockEtfItems} />);
    expect(screen.getByText('069500')).toBeInTheDocument();
    expect(screen.getByText('102110')).toBeInTheDocument();
  });

  it('추천 이유를 표시한다', () => {
    render(<EtfRecommendationList etfItems={mockEtfItems} />);
    expect(screen.getByText('KODEX 200 ETF - 시장 전반적 상승 기대')).toBeInTheDocument();
  });

  it('빈 목록이면 "ETF 추천이 없습니다" 메시지를 표시한다', () => {
    render(<EtfRecommendationList etfItems={[]} />);
    expect(screen.getByText('ETF 추천이 없습니다')).toBeInTheDocument();
  });

  it('onSelect prop이 있을 때 항목 클릭 시 호출된다', async () => {
    const { default: userEvent } = await import('@testing-library/user-event');
    const onSelect = vi.fn();
    render(<EtfRecommendationList etfItems={mockEtfItems} onSelect={onSelect} />);
    const item = screen.getByText('069500').closest('li') ?? screen.getByText('069500');
    await userEvent.click(item);
    expect(onSelect).toHaveBeenCalledWith('069500');
  });
});

// vi는 vitest 전역에서 사용 가능
import { vi } from 'vitest';
