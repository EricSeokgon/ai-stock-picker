// NewsFeed 컴포넌트 테스트
import { describe, it, expect } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { NewsFeed } from '../components/NewsFeed';
import type { NewsItem } from '../types';

const mockNews: NewsItem[] = [
  {
    title: '코스피 급등, 반도체 섹터 주도',
    summary: '삼성전자와 SK하이닉스를 중심으로 반도체 섹터가 강세를 보였습니다.',
    sentiment: 'positive',
    source: '한국경제',
    url: 'https://example.com/news/1',
    published_at: '2026-06-01T08:30:00Z',
  },
  {
    title: '외국인 코스피 순매도 지속',
    summary: null,
    sentiment: 'negative',
    source: '매일경제',
    url: 'https://example.com/news/2',
    published_at: '2026-06-01T09:00:00Z',
  },
];

describe('NewsFeed', () => {
  it('2개의 뉴스 항목을 렌더링한다', () => {
    render(<NewsFeed news={mockNews} />);
    expect(screen.getByText('코스피 급등, 반도체 섹터 주도')).toBeInTheDocument();
    expect(screen.getByText('외국인 코스피 순매도 지속')).toBeInTheDocument();
  });

  it('감성 배지를 표시한다', () => {
    render(<NewsFeed news={mockNews} />);
    expect(screen.getByLabelText('감성: 긍정')).toBeInTheDocument();
    expect(screen.getByLabelText('감성: 부정')).toBeInTheDocument();
  });

  it('제목이 링크로 표시된다', () => {
    render(<NewsFeed news={mockNews} />);
    const link = screen.getByRole('link', { name: '코스피 급등, 반도체 섹터 주도' });
    expect(link).toHaveAttribute('href', 'https://example.com/news/1');
    expect(link).toHaveAttribute('target', '_blank');
  });

  it('섹션 제목을 표시한다', () => {
    render(<NewsFeed news={mockNews} />);
    expect(screen.getByText('최신 뉴스')).toBeInTheDocument();
  });

  it('summary가 null인 경우에도 크래시 없이 렌더링된다', () => {
    render(<NewsFeed news={[mockNews[1]]} />);
    expect(screen.getByText('외국인 코스피 순매도 지속')).toBeInTheDocument();
  });

  it('빈 뉴스 배열일 때 안내 메시지를 표시한다', () => {
    render(<NewsFeed news={[]} />);
    expect(screen.getByText('표시할 뉴스가 없습니다.')).toBeInTheDocument();
  });

  it('중립 감성 배지를 표시한다', () => {
    const neutralNews: NewsItem[] = [
      { ...mockNews[0], sentiment: 'neutral', url: 'https://example.com/3' },
    ];
    render(<NewsFeed news={neutralNews} />);
    expect(screen.getByLabelText('감성: 중립')).toBeInTheDocument();
  });
});
