// FeedbackButtons 컴포넌트 테스트
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FeedbackButtons } from '../components/FeedbackButtons';
import type { FeedbackSummaryResponse } from '../api/recommendations';

vi.mock('../api/recommendations', () => ({
  fetchFeedbackSummary: vi.fn(),
  submitFeedback: vi.fn(),
  getRecommendationHistory: vi.fn(),
}));

import { fetchFeedbackSummary, submitFeedback } from '../api/recommendations';

const mockSummary: FeedbackSummaryResponse = {
  krx_code: '005930',
  up: 12,
  down: 3,
};

describe('FeedbackButtons', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('좋아요/싫어요 카운트를 렌더링한다', async () => {
    (fetchFeedbackSummary as ReturnType<typeof vi.fn>).mockResolvedValue(mockSummary);

    render(<FeedbackButtons krxCode="005930" />);

    await waitFor(() => {
      expect(screen.getByLabelText(/좋아요 12개/)).toBeInTheDocument();
      expect(screen.getByLabelText(/싫어요 3개/)).toBeInTheDocument();
    });
  });

  it('좋아요 클릭 시 submitFeedback("up")을 호출한다', async () => {
    (fetchFeedbackSummary as ReturnType<typeof vi.fn>).mockResolvedValue(mockSummary);
    (submitFeedback as ReturnType<typeof vi.fn>).mockResolvedValue({ krx_code: '005930', up: 13, down: 3 });

    render(<FeedbackButtons krxCode="005930" />);

    await waitFor(() => {
      expect(screen.getByLabelText(/좋아요/)).not.toBeDisabled();
    });

    await userEvent.click(screen.getByLabelText(/좋아요/));
    expect(submitFeedback).toHaveBeenCalledWith('005930', 'up');
  });

  it('제출 중 버튼이 비활성화된다', async () => {
    (fetchFeedbackSummary as ReturnType<typeof vi.fn>).mockResolvedValue(mockSummary);
    // submitFeedback을 pending 상태로 유지
    (submitFeedback as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}));

    render(<FeedbackButtons krxCode="005930" />);

    await waitFor(() => {
      expect(screen.getByLabelText(/좋아요/)).not.toBeDisabled();
    });

    // 클릭 후 즉시 disabled 상태 확인
    await userEvent.click(screen.getByLabelText(/좋아요/));
    expect(screen.getByLabelText(/좋아요/)).toBeDisabled();
    expect(screen.getByLabelText(/싫어요/)).toBeDisabled();
  });

  it('제출 후 카운트가 갱신된다', async () => {
    (fetchFeedbackSummary as ReturnType<typeof vi.fn>).mockResolvedValue(mockSummary);
    (submitFeedback as ReturnType<typeof vi.fn>).mockResolvedValue({
      krx_code: '005930',
      up: 13,
      down: 3,
    });

    render(<FeedbackButtons krxCode="005930" />);

    await waitFor(() => {
      expect(screen.getByLabelText(/좋아요 12개/)).toBeInTheDocument();
    });

    await userEvent.click(screen.getByLabelText(/좋아요/));

    await waitFor(() => {
      expect(screen.getByLabelText(/좋아요 13개/)).toBeInTheDocument();
    });
  });

  it('API 실패 시 오류 메시지를 버튼 영역에만 표시한다', async () => {
    (fetchFeedbackSummary as ReturnType<typeof vi.fn>).mockResolvedValue(mockSummary);
    (submitFeedback as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('서버 오류'));

    render(<FeedbackButtons krxCode="005930" />);

    await waitFor(() => {
      expect(screen.getByLabelText(/좋아요/)).not.toBeDisabled();
    });

    await userEvent.click(screen.getByLabelText(/좋아요/));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByRole('alert')).toHaveTextContent('피드백 제출 중 오류가 발생했습니다');
    });
  });
});
