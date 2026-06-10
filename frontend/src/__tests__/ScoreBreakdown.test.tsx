// ScoreBreakdown 컴포넌트 테스트
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ScoreBreakdown } from '../components/ScoreBreakdown';
import type { ScoreBreakdown as ScoreBreakdownType } from '../types';

const baseFactors: ScoreBreakdownType['factors'] = [
  { factor: 'sentiment', weight: 0.40, factor_score: 0.75, contribution: 0.300 },
  { factor: 'volume',    weight: 0.20, factor_score: 0.60, contribution: 0.120 },
  { factor: 'momentum',  weight: 0.25, factor_score: 0.80, contribution: 0.200 },
  { factor: 'anomaly',   weight: 0.15, factor_score: 0.50, contribution: 0.075 },
];

describe('ScoreBreakdown', () => {
  it('팩터 기여도를 모두 렌더링한다', () => {
    const breakdown: ScoreBreakdownType = { factors: baseFactors };
    render(<ScoreBreakdown breakdown={breakdown} />);

    expect(screen.getByText('감성(40%)')).toBeInTheDocument();
    expect(screen.getByText('거래량(20%)')).toBeInTheDocument();
    expect(screen.getByText('모멘텀(25%)')).toBeInTheDocument();
    expect(screen.getByText('이상거래(15%)')).toBeInTheDocument();
  });

  it('팩터 기여도 값을 소수점 3자리로 표시한다', () => {
    const breakdown: ScoreBreakdownType = { factors: baseFactors };
    render(<ScoreBreakdown breakdown={breakdown} />);

    expect(screen.getByText('0.300')).toBeInTheDocument();
    expect(screen.getByText('0.120')).toBeInTheDocument();
    expect(screen.getByText('0.200')).toBeInTheDocument();
    expect(screen.getByText('0.075')).toBeInTheDocument();
  });

  it('피드백 델타가 양수이면 피드백 조정 행과 + 접두사를 표시한다', () => {
    const breakdown: ScoreBreakdownType = { factors: baseFactors, feedback_delta: 0.05 };
    render(<ScoreBreakdown breakdown={breakdown} />);

    expect(screen.getByText('피드백 조정')).toBeInTheDocument();
    expect(screen.getByText('+0.050')).toBeInTheDocument();
  });

  it('피드백 델타가 음수이면 피드백 조정 행과 음수 값을 표시한다', () => {
    const breakdown: ScoreBreakdownType = { factors: baseFactors, feedback_delta: -0.03 };
    render(<ScoreBreakdown breakdown={breakdown} />);

    expect(screen.getByText('피드백 조정')).toBeInTheDocument();
    expect(screen.getByText('-0.030')).toBeInTheDocument();
  });

  it('피드백 델타가 0이면 피드백 조정 행을 렌더링하지 않는다', () => {
    const breakdown: ScoreBreakdownType = { factors: baseFactors, feedback_delta: 0 };
    render(<ScoreBreakdown breakdown={breakdown} />);

    expect(screen.queryByText('피드백 조정')).not.toBeInTheDocument();
  });

  it('피드백 델타가 null이면 피드백 조정 행을 렌더링하지 않는다', () => {
    const breakdown: ScoreBreakdownType = { factors: baseFactors, feedback_delta: null };
    render(<ScoreBreakdown breakdown={breakdown} />);

    expect(screen.queryByText('피드백 조정')).not.toBeInTheDocument();
  });

  it('피드백 델타가 undefined이면 피드백 조정 행을 렌더링하지 않는다', () => {
    const breakdown: ScoreBreakdownType = { factors: baseFactors };
    render(<ScoreBreakdown breakdown={breakdown} />);

    expect(screen.queryByText('피드백 조정')).not.toBeInTheDocument();
  });
});
