// 공유 포트폴리오 댓글 기능 프론트엔드 테스트 (SPEC-STOCK-046)
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

// AuthContext mock
vi.mock('../auth/AuthContext', () => ({
  AuthProvider: ({ children }: { children: unknown }) => children,
  useAuth: vi.fn(),
}));

// feed API mock
vi.mock('../api/feed', () => ({
  getSharedPortfolio: vi.fn(),
  likeSharedPortfolio: vi.fn(),
  unlikeSharedPortfolio: vi.fn(),
  getComments: vi.fn(),
  addComment: vi.fn(),
  deleteComment: vi.fn(),
}));

import { useAuth } from '../auth/AuthContext';
import {
  getSharedPortfolio,
  getComments,
  addComment,
  deleteComment,
} from '../api/feed';
import SharedPortfolio from '../pages/SharedPortfolio';

// 공유 포트폴리오 응답 픽스처
const mockPortfolio = {
  portfolio_name: '테스트 포트폴리오',
  holdings: [{ ticker: 'AAPL', shares: 10, purchase_price: 150 }],
  total_return_rate: 12.5,
  goal_progress: null,
  view_count: 42,
  like_count: 7,
};

// 댓글 목록 응답 픽스처
const mockCommentListEmpty = { items: [], total: 0, page: 1, size: 20 };
const mockCommentList = {
  items: [
    {
      id: 1,
      user_id: 10,
      username: '홍길동',
      content: '좋은 포트폴리오네요!',
      created_at: '2026-01-15T10:00:00Z',
    },
    {
      id: 2,
      user_id: 11,
      username: '김철수',
      content: '저도 비슷한 구성입니다.',
      created_at: '2026-01-15T11:00:00Z',
    },
  ],
  total: 2,
  page: 1,
  size: 20,
};

// 생성된 댓글 픽스처
const mockNewComment = {
  id: 3,
  user_id: 99,
  username: '테스터',
  content: '새로운 댓글입니다.',
  created_at: '2026-01-15T12:00:00Z',
};

// 컴포넌트 렌더 헬퍼
function renderSharedPortfolio(token: string | null = null) {
  (useAuth as ReturnType<typeof vi.fn>).mockReturnValue({
    user: token ? { id: 99, username: '테스터' } : null,
    token,
    isAuthenticated: !!token,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  });
  return render(
    <MemoryRouter initialEntries={['/shared/test-token']}>
      <Routes>
        <Route path="/shared/:shareToken" element={<SharedPortfolio />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('SharedPortfolio 댓글 섹션 (SPEC-STOCK-046)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (getSharedPortfolio as ReturnType<typeof vi.fn>).mockResolvedValue(mockPortfolio);
  });

  // TC-01: 댓글이 없을 때 빈 상태 메시지 표시
  it('댓글이 없으면 빈 상태 메시지를 표시한다', async () => {
    (getComments as ReturnType<typeof vi.fn>).mockResolvedValue(mockCommentListEmpty);
    renderSharedPortfolio();

    await waitFor(() => {
      expect(screen.getByTestId('no-comments')).toBeTruthy();
    });
    expect(screen.getByTestId('comment-count').textContent).toContain('0');
  });

  // TC-02: 댓글 목록이 정상 렌더링된다
  it('댓글 목록을 가져와서 렌더링한다', async () => {
    (getComments as ReturnType<typeof vi.fn>).mockResolvedValue(mockCommentList);
    renderSharedPortfolio();

    await waitFor(() => {
      expect(screen.getByTestId('comment-list')).toBeTruthy();
    });
    expect(screen.getByTestId('comment-item-1')).toBeTruthy();
    expect(screen.getByTestId('comment-item-2')).toBeTruthy();
    expect(screen.getByText('좋은 포트폴리오네요!')).toBeTruthy();
    expect(screen.getByTestId('comment-count').textContent).toContain('2');
  });

  // TC-03: 로그인 상태에서 댓글 작성 폼 표시 및 작성 성공
  it('로그인 상태에서 댓글을 작성하면 목록에 추가된다', async () => {
    const user = userEvent.setup();
    (getComments as ReturnType<typeof vi.fn>).mockResolvedValue(mockCommentListEmpty);
    (addComment as ReturnType<typeof vi.fn>).mockResolvedValue(mockNewComment);
    renderSharedPortfolio('valid-token');

    // 댓글 입력창 대기
    const input = await screen.findByTestId('comment-input');
    await user.type(input, '새로운 댓글입니다.');

    const submitBtn = screen.getByTestId('comment-submit-btn');
    await user.click(submitBtn);

    await waitFor(() => {
      expect(addComment).toHaveBeenCalledWith('test-token', '새로운 댓글입니다.', 'valid-token');
    });
    // 작성 후 목록에 새 댓글이 추가됨
    await waitFor(() => {
      expect(screen.getByText('새로운 댓글입니다.')).toBeTruthy();
    });
  });

  // TC-04: 비로그인 상태에서는 댓글 작성 폼이 없고 안내 메시지 표시
  it('비로그인 상태에서는 로그인 안내 메시지를 표시한다', async () => {
    (getComments as ReturnType<typeof vi.fn>).mockResolvedValue(mockCommentListEmpty);
    renderSharedPortfolio(null);

    await waitFor(() => {
      expect(screen.queryByTestId('comment-input')).toBeNull();
    });
    expect(screen.getByText(/로그인이 필요합니다/)).toBeTruthy();
  });

  // TC-05: 로그인 상태에서 댓글 삭제 버튼 표시 및 삭제 동작
  it('로그인 상태에서 댓글 삭제 버튼을 클릭하면 댓글이 제거된다', async () => {
    const user = userEvent.setup();
    (getComments as ReturnType<typeof vi.fn>).mockResolvedValue(mockCommentList);
    (deleteComment as ReturnType<typeof vi.fn>).mockResolvedValue(undefined);
    renderSharedPortfolio('valid-token');

    // 댓글 목록 렌더링 대기
    await waitFor(() => {
      expect(screen.getByTestId('comment-item-1')).toBeTruthy();
    });

    const deleteBtn = screen.getByTestId('comment-delete-btn-1');
    await user.click(deleteBtn);

    await waitFor(() => {
      expect(deleteComment).toHaveBeenCalledWith('test-token', 1, 'valid-token');
    });
    // 삭제 후 해당 댓글 제거됨
    await waitFor(() => {
      expect(screen.queryByTestId('comment-item-1')).toBeNull();
    });
  });

  // TC-06: 댓글 API 오류 시 에러 메시지 표시
  it('댓글 API 오류 시 에러 메시지를 표시한다', async () => {
    (getComments as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error('댓글을 불러올 수 없습니다.'),
    );
    renderSharedPortfolio();

    await waitFor(() => {
      expect(screen.getByTestId('comment-error')).toBeTruthy();
    });
    expect(screen.getByText('댓글을 불러올 수 없습니다.')).toBeTruthy();
  });
});
