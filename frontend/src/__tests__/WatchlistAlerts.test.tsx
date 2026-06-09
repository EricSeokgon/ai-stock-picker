// WatchlistAlerts — Watchlist 페이지의 목표가 알림 기능 테스트
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import Watchlist from '../pages/Watchlist';
import type { WatchlistItem, WatchlistAlert } from '../api/watchlist';

// useAuth 모킹
const mockUseAuth = vi.fn();
vi.mock('../auth/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

// watchlist API 모킹
const mockGetWatchlist = vi.fn<[], Promise<WatchlistItem[]>>();
const mockGetAlerts = vi.fn<[], Promise<WatchlistAlert[]>>();
const mockCreateAlert = vi.fn<[string, unknown], Promise<WatchlistAlert>>();
const mockDeleteAlert = vi.fn<[string, number], Promise<void>>();
vi.mock('../api/watchlist', () => ({
  getWatchlist: () => mockGetWatchlist(),
  removeFromWatchlist: vi.fn(),
  getAlerts: () => mockGetAlerts(),
  createAlert: (...args: [string, unknown]) => mockCreateAlert(...args),
  deleteAlert: (...args: [string, number]) => mockDeleteAlert(...args),
}));

// LivePriceBadge 모킹
vi.mock('../components/LivePriceBadge', () => ({
  LivePriceBadge: ({ krxCode }: { krxCode: string }) => (
    <span data-testid={`live-price-${krxCode}`}>시세</span>
  ),
}));

// Navigate 모킹
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return {
    ...actual,
    Navigate: ({ to }: { to: string }) => <div data-testid="navigate-mock">Redirect to {to}</div>,
  };
});

const sampleItems: WatchlistItem[] = [
  { id: 1, krx_code: '005930', created_at: '2026-01-01' },
];

const sampleAlerts: WatchlistAlert[] = [
  {
    id: 10,
    krx_code: '005930',
    target_price: 80000,
    direction: 'above',
    is_active: true,
    triggered_at: null,
  },
];

function renderWatchlist() {
  return render(
    <MemoryRouter>
      <Watchlist />
    </MemoryRouter>,
  );
}

describe('WatchlistAlerts — 목표가 알림', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      token: 'test-token',
    });
    mockGetWatchlist.mockResolvedValue(sampleItems);
    mockGetAlerts.mockResolvedValue(sampleAlerts);
  });

  it('미인증 시 /login으로 리다이렉트', () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, token: null });
    renderWatchlist();
    expect(screen.getByTestId('navigate-mock')).toHaveTextContent('Redirect to /login');
  });

  it('활성 알림 목록이 렌더됨', async () => {
    renderWatchlist();

    await waitFor(() => {
      expect(screen.getByText(/80,000원/)).toBeInTheDocument();
    });
    // 알림 섹션 내 방향 텍스트 확인
    expect(screen.getAllByText(/이상/).length).toBeGreaterThan(0);
    // 알림 섹션에 "005930 이상 80,000원" 텍스트가 있는 요소 확인
    expect(screen.getByRole('button', { name: /005930 알림 삭제/i })).toBeInTheDocument();
  });

  it('알림 추가 폼 제출 시 createAlert 호출 및 목록 갱신', async () => {
    const user = userEvent.setup();
    const newAlert: WatchlistAlert = {
      id: 20,
      krx_code: '005930',
      target_price: 70000,
      direction: 'below',
      is_active: true,
      triggered_at: null,
    };
    mockCreateAlert.mockResolvedValue(newAlert);

    renderWatchlist();

    // 관심목록 종목이 로드될 때까지 대기
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /005930 알림 추가/i })).toBeInTheDocument();
    });

    // 알림 추가 버튼 클릭
    await user.click(screen.getByRole('button', { name: /005930 알림 추가/i }));

    // 폼 입력
    const priceInput = screen.getByRole('spinbutton', { name: /목표가 입력/i });
    await user.clear(priceInput);
    await user.type(priceInput, '70000');

    const dirSelect = screen.getByRole('combobox', { name: /방향 선택/i });
    await user.selectOptions(dirSelect, 'below');

    await user.click(screen.getByRole('button', { name: /^추가$/i }));

    await waitFor(() => {
      expect(mockCreateAlert).toHaveBeenCalledWith('test-token', {
        krx_code: '005930',
        target_price: 70000,
        direction: 'below',
      });
    });

    // 새로운 알림이 목록에 표시됨
    await waitFor(() => {
      expect(screen.getByText(/70,000원/)).toBeInTheDocument();
    });
  });

  it('알림 삭제 버튼 클릭 시 목록에서 제거됨', async () => {
    const user = userEvent.setup();
    mockDeleteAlert.mockResolvedValue(undefined);

    renderWatchlist();

    await waitFor(() => {
      expect(screen.getByText(/80,000원/)).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /005930 알림 삭제/i }));

    await waitFor(() => {
      expect(screen.queryByText(/80,000원/)).not.toBeInTheDocument();
    });
    expect(mockDeleteAlert).toHaveBeenCalledWith('test-token', 10);
  });

  it('알림 생성 실패 시 에러 메시지 표시', async () => {
    const user = userEvent.setup();
    mockCreateAlert.mockRejectedValue(new Error('서버 오류'));

    renderWatchlist();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /005930 알림 추가/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /005930 알림 추가/i }));

    const priceInput = screen.getByRole('spinbutton', { name: /목표가 입력/i });
    await user.type(priceInput, '50000');
    await user.click(screen.getByRole('button', { name: /^추가$/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('서버 오류');
    });
  });
});
