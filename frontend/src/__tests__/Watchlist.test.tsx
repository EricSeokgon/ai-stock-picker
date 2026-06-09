// Watchlist 페이지 테스트
import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import Watchlist from '../pages/Watchlist';
import type { WatchlistItem } from '../api/watchlist';

// useAuth 모킹
const mockUseAuth = vi.fn();
vi.mock('../auth/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

// getWatchlist, getAlerts 모킹
const mockGetWatchlist = vi.fn<[], Promise<WatchlistItem[]>>();
const mockGetAlerts = vi.fn<[], Promise<unknown[]>>();
vi.mock('../api/watchlist', () => ({
  getWatchlist: () => mockGetWatchlist(),
  removeFromWatchlist: vi.fn(),
  getAlerts: () => mockGetAlerts(),
  createAlert: vi.fn(),
  deleteAlert: vi.fn(),
}));

// LivePriceBadge 모킹 (WebSocket 방지)
vi.mock('../components/LivePriceBadge', () => ({
  LivePriceBadge: ({ krxCode }: { krxCode: string }) => (
    <span data-testid={`live-price-${krxCode}`}>시세 조회 중...</span>
  ),
}));

// Navigate 모킹
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return {
    ...actual,
    Navigate: ({ to }: { to: string }) => <div data-testid="navigate" data-to={to} />,
  };
});

describe('Watchlist', () => {
  beforeEach(() => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      token: 'test-token',
    });
    mockGetWatchlist.mockResolvedValue([]);
    mockGetAlerts.mockResolvedValue([]);
  });

  it('미인증 상태면 /login으로 리다이렉트한다', () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, token: null });

    render(
      <MemoryRouter>
        <Watchlist />
      </MemoryRouter>
    );

    const nav = screen.getByTestId('navigate');
    expect(nav.getAttribute('data-to')).toBe('/login');
  });

  it('관심 목록 종목을 표시한다', async () => {
    mockGetWatchlist.mockResolvedValue([
      { id: 1, krx_code: '005930', created_at: '2024-01-01' },
      { id: 2, krx_code: '000660', created_at: '2024-01-01' },
    ]);

    render(
      <MemoryRouter>
        <Watchlist />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('005930')).toBeDefined();
      expect(screen.getByText('000660')).toBeDefined();
    });
  });

  it('빈 관심 목록이면 안내 메시지를 표시한다', async () => {
    mockGetWatchlist.mockResolvedValue([]);

    render(
      <MemoryRouter>
        <Watchlist />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/관심 목록이 없습니다/)).toBeDefined();
    });
  });

  it('각 종목에 LivePriceBadge가 렌더링된다', async () => {
    mockGetWatchlist.mockResolvedValue([
      { id: 1, krx_code: '005930', created_at: '2024-01-01' },
    ]);

    render(
      <MemoryRouter>
        <Watchlist />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('live-price-005930')).toBeDefined();
    });
  });
});
