// SPEC-STOCK-045: 피드 디스커버리 강화 프론트엔드 테스트
// 실행: cd frontend && npx vitest run src/__tests__/feed_discovery_045.test.tsx
/**
 * T-045-009: 검색 제출 → q 파라미터로 getFeed 호출
 * T-045-010: 트렌딩 버튼 클릭 → sort=trending 으로 getFeed 호출
 * T-045-011: 트렌딩 결과가 서버 반환 순서대로 렌더링
 * T-045-012: 검색어 비우고 제출 → q 없이 getFeed 호출
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import Feed from '../pages/Feed';

// ─────────────────────────────────────────────────────────────────────────────
// getFeed 모킹
// ─────────────────────────────────────────────────────────────────────────────

vi.mock('../api/feed', () => ({
  getFeed: vi.fn(),
}));

import { getFeed } from '../api/feed';
const mockGetFeed = getFeed as ReturnType<typeof vi.fn>;

const EMPTY_RESPONSE = {
  items: [],
  page: 1,
  size: 20,
  total: 0,
};

function renderFeed() {
  return render(
    <MemoryRouter>
      <Feed />
    </MemoryRouter>,
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 테스트 스위트
// ─────────────────────────────────────────────────────────────────────────────

describe('피드 디스커버리 강화 (SPEC-STOCK-045)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetFeed.mockResolvedValue(EMPTY_RESPONSE);
  });

  it('T-045-009: 검색어 제출 시 q 파라미터로 getFeed 호출', async () => {
    const user = userEvent.setup();
    renderFeed();

    // 초기 로드 완료 대기
    await waitFor(() => expect(mockGetFeed).toHaveBeenCalled());

    // 이전 호출 제거 후 새 반환값 설정
    vi.clearAllMocks();
    mockGetFeed.mockResolvedValue(EMPTY_RESPONSE);

    // 검색어 입력
    const searchInput = screen.getByRole('textbox');
    await user.type(searchInput, '배당');

    // 검색 제출 (버튼 또는 Enter)
    const searchBtn = screen.getByRole('button', { name: /검색/ });
    await user.click(searchBtn);

    await waitFor(() => {
      expect(mockGetFeed).toHaveBeenCalledWith(
        expect.any(String),  // sort
        1,                   // page reset
        expect.any(Number),  // size
        '배당',              // q
      );
    });
  });

  it('T-045-010: 트렌딩 버튼 클릭 시 sort=trending 으로 getFeed 호출', async () => {
    const user = userEvent.setup();
    renderFeed();

    // 초기 로드 완료 대기
    await waitFor(() => expect(mockGetFeed).toHaveBeenCalled());

    vi.clearAllMocks();
    mockGetFeed.mockResolvedValue(EMPTY_RESPONSE);

    // 트렌딩 버튼 클릭
    await user.click(screen.getByRole('button', { name: /트렌딩/ }));

    await waitFor(() => {
      expect(mockGetFeed).toHaveBeenCalledWith(
        'trending',
        1,
        expect.any(Number),
        undefined,
      );
    });
  });

  it('T-045-011: 트렌딩 결과가 서버 반환 순서대로 렌더링', async () => {
    const orderedItems = [
      {
        share_token: 'tok_top',
        portfolio_name: '화제의 ETF',
        view_count: 100,
        like_count: 5,
        shared_at: '2026-06-30T00:00:00Z',
        total_return_rate: 12.5,
      },
      {
        share_token: 'tok_mid',
        portfolio_name: '일반 성장주',
        view_count: 10,
        like_count: 1,
        shared_at: '2026-06-29T00:00:00Z',
        total_return_rate: 3.0,
      },
    ];

    mockGetFeed.mockResolvedValue({
      items: orderedItems,
      page: 1,
      size: 20,
      total: 2,
    });

    renderFeed();

    await waitFor(() => {
      expect(screen.getByText('화제의 ETF')).toBeInTheDocument();
      expect(screen.getByText('일반 성장주')).toBeInTheDocument();
    });

    // 서버 반환 순서: 화제의 ETF 가 일반 성장주 보다 앞에 위치해야 함
    const allItems = screen.getAllByText(/ETF|성장주/);
    expect(allItems[0].textContent).toContain('ETF');
    expect(allItems[1].textContent).toContain('성장주');
  });

  it('T-045-012: 검색어 비우고 제출 → q 없이 getFeed 호출', async () => {
    const user = userEvent.setup();
    renderFeed();

    await waitFor(() => expect(mockGetFeed).toHaveBeenCalled());

    // 검색어 입력 후 제출
    const input = screen.getByRole('textbox');
    await user.type(input, '배당');
    await user.click(screen.getByRole('button', { name: /검색/ }));

    vi.clearAllMocks();
    mockGetFeed.mockResolvedValue(EMPTY_RESPONSE);

    // 검색어 지우고 다시 제출
    await user.clear(input);
    await user.click(screen.getByRole('button', { name: /검색/ }));

    await waitFor(() => {
      const calls = mockGetFeed.mock.calls;
      expect(calls.length).toBeGreaterThan(0);
      const lastCall = calls[calls.length - 1];
      // q 인자가 undefined 이거나 빈 문자열이어야 함
      expect(lastCall[3] == null || lastCall[3] === '').toBe(true);
    });
  });
});
