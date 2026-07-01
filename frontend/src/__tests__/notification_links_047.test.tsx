// 알림 딥링크 프론트엔드 테스트 (SPEC-STOCK-047)
// T-047-008 ~ T-047-010 (프론트엔드 3개)
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

// AuthContext mock
vi.mock('../auth/AuthContext', () => ({
  AuthProvider: ({ children }: { children: unknown }) => children,
  useAuth: vi.fn(),
}));

// notifications API mock
vi.mock('../api/notifications', () => ({
  fetchNotifications: vi.fn(),
  markNotificationRead: vi.fn(),
  markAllNotificationsRead: vi.fn(),
}));

import { useAuth } from '../auth/AuthContext';
import {
  fetchNotifications,
  markNotificationRead,
} from '../api/notifications';

// useNavigate mock — MemoryRouter 내부에서 실제 navigate 사용
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

import NotificationsPage from '../pages/Notifications';

// 알림 픽스처 헬퍼
function makeNotification(overrides: Partial<{
  id: number;
  type: string;
  krx_code: string;
  title: string;
  body: string | null;
  is_read: boolean;
  link: string | null;
  ref_date: string | null;
  related_alert_id: number | null;
  created_at: string;
  read_at: string | null;
}> = {}) {
  return {
    id: 1,
    type: 'portfolio_like',
    krx_code: 'P7',
    title: '누군가 포트폴리오를 좋아합니다',
    body: null,
    is_read: false,
    link: null,
    ref_date: null,
    related_alert_id: null,
    created_at: '2026-07-01T10:00:00Z',
    read_at: null,
    ...overrides,
  };
}

function renderNotifications() {
  (useAuth as ReturnType<typeof vi.fn>).mockReturnValue({
    token: 'test-token',
    user: { id: 1, username: 'tester' },
    isAuthenticated: true,
  });
  return render(
    <MemoryRouter>
      <NotificationsPage />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockNavigate.mockReset();
});

// ─────────────────────────────────────────────────────────────────────────────
// T-047-008: link 있는 알림 → data-testid="notification-link-{id}" 렌더
// ─────────────────────────────────────────────────────────────────────────────

describe('알림 딥링크 렌더링 (AC-047-008)', () => {
  it('link 있는 알림에 notification-link-{id} testid 렌더', async () => {
    (fetchNotifications as ReturnType<typeof vi.fn>).mockResolvedValue([
      makeNotification({ id: 42, link: '/shared/abc123' }),
    ]);

    renderNotifications();

    await waitFor(() => {
      expect(screen.getByTestId('notification-link-42')).toBeDefined();
    });
  });

  it('link 없는 알림에 notification-link-{id} testid 미노출 (AC-047-009)', async () => {
    (fetchNotifications as ReturnType<typeof vi.fn>).mockResolvedValue([
      makeNotification({ id: 99, link: null }),
    ]);

    renderNotifications();

    await waitFor(() => {
      // 로딩 완료 확인 (알림 제목이 보여야 함)
      expect(screen.getByText('누군가 포트폴리오를 좋아합니다')).toBeDefined();
    });
    expect(screen.queryByTestId('notification-link-99')).toBeNull();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// T-047-009: link 있는 알림 클릭 → navigate(link) 호출
// ─────────────────────────────────────────────────────────────────────────────

describe('알림 딥링크 클릭 이동 (AC-047-008)', () => {
  it('link 있는 알림 클릭 → navigate(/shared/abc123) 호출', async () => {
    (fetchNotifications as ReturnType<typeof vi.fn>).mockResolvedValue([
      makeNotification({ id: 42, link: '/shared/abc123', is_read: true }),
    ]);
    (markNotificationRead as ReturnType<typeof vi.fn>).mockResolvedValue(
      makeNotification({ id: 42, link: '/shared/abc123', is_read: true }),
    );

    renderNotifications();

    const linkEl = await screen.findByTestId('notification-link-42');
    await userEvent.click(linkEl);

    expect(mockNavigate).toHaveBeenCalledWith('/shared/abc123');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// T-047-010: 미읽음 link 알림 클릭 → markNotificationRead 호출
// ─────────────────────────────────────────────────────────────────────────────

describe('알림 딥링크 클릭 시 읽음 처리 (AC-047-010)', () => {
  it('미읽음 link 알림 클릭 → markNotificationRead(id) 호출', async () => {
    (fetchNotifications as ReturnType<typeof vi.fn>).mockResolvedValue([
      makeNotification({ id: 42, link: '/shared/abc123', is_read: false }),
    ]);
    (markNotificationRead as ReturnType<typeof vi.fn>).mockResolvedValue(
      makeNotification({ id: 42, link: '/shared/abc123', is_read: true }),
    );

    renderNotifications();

    const linkEl = await screen.findByTestId('notification-link-42');
    await userEvent.click(linkEl);

    expect(markNotificationRead).toHaveBeenCalledWith('test-token', 42);
  });
});
