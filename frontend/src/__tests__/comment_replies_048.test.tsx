// SPEC-STOCK-048: 댓글 대댓글 프론트엔드 테스트
// 테스트 실행: cd frontend && npx vitest run src/__tests__/comment_replies_048.test.tsx
/**
 * SPEC-STOCK-048 프론트엔드 TDD 단위 테스트 (3개)
 * F-048-001 ~ F-048-003
 * 커버리지 대상: CommentItem replies 렌더링, addComment parentCommentId, 답글 버튼 UI
 */
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

// 대댓글 포함 댓글 목록 픽스처
const mockCommentWithReplies = {
  items: [
    {
      id: 1,
      user_id: 10,
      username: '홍길동',
      content: '최상위 댓글입니다',
      parent_comment_id: null,
      replies: [
        {
          id: 2,
          user_id: 11,
          username: '이순신',
          content: '이 댓글의 대댓글입니다',
          parent_comment_id: 1,
          replies: [],
          created_at: '2026-07-01T11:00:00Z',
        },
      ],
      created_at: '2026-07-01T10:00:00Z',
    },
  ],
  total: 1,
  page: 1,
  size: 20,
};

// 컴포넌트 렌더 헬퍼
function renderSharedPortfolio(token: string | null = null) {
  (useAuth as ReturnType<typeof vi.fn>).mockReturnValue({
    user: token ? { id: 99, username: '테스터' } : null,
    token,
    isAuthenticated: !!token,
  });
  return render(
    <MemoryRouter initialEntries={['/shared/test-token']}>
      <Routes>
        <Route path="/shared/:shareToken" element={<SharedPortfolio />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  (getSharedPortfolio as ReturnType<typeof vi.fn>).mockResolvedValue(mockPortfolio);
});

describe('SPEC-STOCK-048: 대댓글 프론트엔드 테스트', () => {

  // ─── F-048-001: 대댓글 replies 렌더링 ─────────────────────────────────────

  it('F-048-001: 댓글 목록에 대댓글(replies)이 중첩 렌더링된다', async () => {
    // GIVEN: 최상위 댓글 1개 + 대댓글 1개 응답
    (getComments as ReturnType<typeof vi.fn>).mockResolvedValue(mockCommentWithReplies);

    renderSharedPortfolio(null); // 비로그인

    // THEN: 최상위 댓글 렌더링
    await waitFor(() => {
      expect(screen.getByTestId('comment-item-1')).toBeDefined();
    });

    // THEN: 대댓글 replies 목록 렌더링
    expect(screen.getByTestId('replies-list-1')).toBeDefined();
    // 대댓글 항목 렌더링
    expect(screen.getByTestId('reply-item-2')).toBeDefined();
    // 대댓글 내용 표시
    expect(screen.getByText('이 댓글의 대댓글입니다')).toBeDefined();
  });

  // ─── F-048-002: 답글 버튼 표시 및 클릭 시 입력창 활성화 ───────────────────

  it('F-048-002: 로그인 시 답글 버튼이 표시되고 클릭하면 답글 입력창이 나타난다', async () => {
    // GIVEN: 최상위 댓글 1개 (대댓글 없음)
    (getComments as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [
        {
          id: 1,
          user_id: 10,
          username: '홍길동',
          content: '최상위 댓글',
          parent_comment_id: null,
          replies: [],
          created_at: '2026-07-01T10:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      size: 20,
    });

    renderSharedPortfolio('test-jwt-token'); // 로그인 상태

    // THEN: 댓글 렌더링 대기
    await waitFor(() => {
      expect(screen.getByTestId('comment-item-1')).toBeDefined();
    });

    // THEN: 답글 버튼 표시
    const replyBtn = screen.getByTestId('reply-btn-1');
    expect(replyBtn).toBeDefined();

    // WHEN: 답글 버튼 클릭
    const user = userEvent.setup();
    await user.click(replyBtn);

    // THEN: 답글 입력창 표시
    await waitFor(() => {
      expect(screen.getByTestId('reply-input-area-1')).toBeDefined();
    });
    expect(screen.getByTestId('reply-input-1')).toBeDefined();
    expect(screen.getByTestId('reply-submit-btn-1')).toBeDefined();
  });

  // ─── F-048-003: 답글 작성 시 addComment에 parentCommentId 전달 ────────────

  it('F-048-003: 답글 게시 시 addComment가 parentCommentId와 함께 호출된다', async () => {
    // GIVEN: 최상위 댓글 1개
    (getComments as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [
        {
          id: 1,
          user_id: 10,
          username: '홍길동',
          content: '최상위 댓글',
          parent_comment_id: null,
          replies: [],
          created_at: '2026-07-01T10:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      size: 20,
    });

    // addComment mock: 대댓글 생성 성공
    (addComment as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: 2,
      user_id: 99,
      username: '테스터',
      content: '대댓글입니다',
      parent_comment_id: 1,
      replies: [],
      created_at: '2026-07-01T11:00:00Z',
    });

    renderSharedPortfolio('test-jwt-token');

    await waitFor(() => {
      expect(screen.getByTestId('comment-item-1')).toBeDefined();
    });

    // WHEN: 답글 버튼 클릭 → 입력 → 게시
    const user = userEvent.setup();
    await user.click(screen.getByTestId('reply-btn-1'));

    await waitFor(() => {
      expect(screen.getByTestId('reply-input-1')).toBeDefined();
    });

    await user.type(screen.getByTestId('reply-input-1'), '대댓글입니다');
    await user.click(screen.getByTestId('reply-submit-btn-1'));

    // THEN: addComment가 parentCommentId=1 포함해서 호출됨
    await waitFor(() => {
      expect(addComment).toHaveBeenCalledWith(
        'test-token',
        '대댓글입니다',
        'test-jwt-token',
        1, // parentCommentId
      );
    });
  });
});
