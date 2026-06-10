// RecommendationList 컴포넌트 테스트
import { describe, it, expect, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RecommendationList } from '../components/RecommendationList';
import type { RecommendationItem } from '../types';

const mockItems: RecommendationItem[] = [
  {
    rank: 1,
    krx_code: '005930',
    total_score: 0.85,
    sentiment_score: 0.7,
    volume_score: 0.6,
    momentum_score: 0.8,
    anomaly_score: 0.5,
    reasoning: '삼성전자 강한 매수 신호 감지',
  },
  {
    rank: 2,
    krx_code: '000660',
    total_score: 0.72,
    sentiment_score: -0.2,
    volume_score: 0.5,
    momentum_score: 0.6,
    anomaly_score: 0.3,
    reasoning: 'SK하이닉스 반도체 수요 회복 기대',
  },
  {
    rank: 3,
    krx_code: '035420',
    total_score: 0.65,
    sentiment_score: 0.4,
    volume_score: 0.3,
    momentum_score: 0.5,
    anomaly_score: 0.2,
    reasoning: 'NAVER 플랫폼 성장 지속',
  },
];

describe('RecommendationList', () => {
  it('3개의 항목을 렌더링한다', () => {
    render(<RecommendationList recommendations={mockItems} />);
    // 각 KRX 코드가 화면에 표시되어야 함
    expect(screen.getByText('005930')).toBeInTheDocument();
    expect(screen.getByText('000660')).toBeInTheDocument();
    expect(screen.getByText('035420')).toBeInTheDocument();
  });

  it('순위가 올바른 순서로 표시된다', () => {
    render(<RecommendationList recommendations={mockItems} />);
    const list = screen.getByRole('list', { name: '주식 추천 목록' });
    const items = within(list).getAllByRole('listitem');
    // 첫 번째 항목에 순위 1 배지가 있어야 함
    expect(within(items[0]).getByLabelText('순위 1위')).toBeInTheDocument();
    expect(within(items[1]).getByLabelText('순위 2위')).toBeInTheDocument();
    expect(within(items[2]).getByLabelText('순위 3위')).toBeInTheDocument();
  });

  it('추천 이유(reasoning) 텍스트를 표시한다', () => {
    render(<RecommendationList recommendations={mockItems} />);
    expect(screen.getByText('삼성전자 강한 매수 신호 감지')).toBeInTheDocument();
    expect(screen.getByText('SK하이닉스 반도체 수요 회복 기대')).toBeInTheDocument();
    expect(screen.getByText('NAVER 플랫폼 성장 지속')).toBeInTheDocument();
  });

  it('섹션 제목을 표시한다', () => {
    render(<RecommendationList recommendations={mockItems} />);
    expect(screen.getByText('오늘의 주식 추천')).toBeInTheDocument();
  });

  it('onSelect prop이 있을 때 항목 클릭 시 해당 krx_code로 호출된다', async () => {
    const onSelect = vi.fn();
    render(<RecommendationList recommendations={mockItems} onSelect={onSelect} />);
    const list = screen.getByRole('list', { name: '주식 추천 목록' });
    const items = within(list).getAllByRole('listitem');
    // 첫 번째 항목(005930) 클릭
    await userEvent.click(items[0]);
    expect(onSelect).toHaveBeenCalledWith('005930');
  });

  it('두 번째 항목 클릭 시 해당 krx_code(000660)로 onSelect가 호출된다', async () => {
    const onSelect = vi.fn();
    render(<RecommendationList recommendations={mockItems} onSelect={onSelect} />);
    const list = screen.getByRole('list', { name: '주식 추천 목록' });
    const items = within(list).getAllByRole('listitem');
    await userEvent.click(items[1]);
    expect(onSelect).toHaveBeenCalledWith('000660');
  });

  it('feedback_score가 0이 아닌 경우 피드백 반영 배지를 표시한다', () => {
    const itemsWithFeedback: RecommendationItem[] = [
      {
        ...mockItems[0],
        base_score: 0.80,
        feedback_score: 0.05,
      },
    ];
    render(<RecommendationList recommendations={itemsWithFeedback} />);
    expect(screen.getByText(/피드백 반영/)).toBeInTheDocument();
  });

  it('feedback_score가 0이면 피드백 반영 배지를 표시하지 않는다', () => {
    const itemsNoFeedback: RecommendationItem[] = [
      {
        ...mockItems[0],
        base_score: 0.80,
        feedback_score: 0,
      },
    ];
    render(<RecommendationList recommendations={itemsNoFeedback} />);
    expect(screen.queryByText(/피드백 반영/)).not.toBeInTheDocument();
  });

  it('base_score/feedback_score가 없는 경우 피드백 배지 없이 정상 렌더링된다', () => {
    // mockItems에는 base_score/feedback_score 필드 없음
    render(<RecommendationList recommendations={mockItems} />);
    expect(screen.queryByText(/피드백 반영/)).not.toBeInTheDocument();
    // 기존 KRX 코드들은 여전히 표시됨
    expect(screen.getByText('005930')).toBeInTheDocument();
  });
});
