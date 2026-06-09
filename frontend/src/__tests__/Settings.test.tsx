// Settings 페이지 테스트
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import Settings from '../pages/Settings';
import type { EmailSubscription } from '../api/notifications';

// useAuth 모킹
const mockUseAuth = vi.fn();
vi.mock('../auth/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

// notifications API 모킹
const mockSubscribeEmail = vi.fn<[string, string], Promise<EmailSubscription>>();
const mockUnsubscribeEmail = vi.fn<[string], Promise<{ message: string }>>();
vi.mock('../api/notifications', () => ({
  subscribeEmail: (...args: [string, string]) => mockSubscribeEmail(...args),
  unsubscribeEmail: (...args: [string]) => mockUnsubscribeEmail(...args),
}));

// Navigate 모킹
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return {
    ...actual,
    Navigate: ({ to }: { to: string }) => <div data-testid="navigate-mock">Redirect to {to}</div>,
  };
});

function renderSettings() {
  return render(
    <MemoryRouter>
      <Settings />
    </MemoryRouter>,
  );
}

describe('Settings 페이지', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      token: 'test-token',
      user: { email: 'user@test.com' },
    });
  });

  it('미인증 시 /login으로 리다이렉트', () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, token: null });
    renderSettings();
    expect(screen.getByTestId('navigate-mock')).toHaveTextContent('Redirect to /login');
  });

  it('미구독 시 이메일 입력 폼이 렌더됨', () => {
    renderSettings();
    expect(screen.getByRole('textbox', { name: /이메일 주소/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /구독/i })).toBeInTheDocument();
  });

  it('구독 성공 시 구독 이메일과 해지 버튼 표시', async () => {
    const user = userEvent.setup();
    const subscription: EmailSubscription = {
      id: 1,
      email: 'test@example.com',
      is_active: true,
      created_at: '2026-01-01T00:00:00',
    };
    mockSubscribeEmail.mockResolvedValue(subscription);

    renderSettings();

    await user.type(screen.getByRole('textbox', { name: /이메일 주소/i }), 'test@example.com');
    await user.click(screen.getByRole('button', { name: /구독/i }));

    await waitFor(() => {
      expect(screen.getByText('test@example.com')).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: /구독 해지/i })).toBeInTheDocument();
  });

  it('구독 해지 성공 시 이메일 폼으로 전환', async () => {
    const user = userEvent.setup();
    const subscription: EmailSubscription = {
      id: 1,
      email: 'test@example.com',
      is_active: true,
      created_at: '2026-01-01T00:00:00',
    };
    mockSubscribeEmail.mockResolvedValue(subscription);
    mockUnsubscribeEmail.mockResolvedValue({ message: '구독 해지 완료' });

    renderSettings();

    // 먼저 구독
    await user.type(screen.getByRole('textbox', { name: /이메일 주소/i }), 'test@example.com');
    await user.click(screen.getByRole('button', { name: /구독/i }));
    await waitFor(() => expect(screen.getByRole('button', { name: /구독 해지/i })).toBeInTheDocument());

    // 해지
    await user.click(screen.getByRole('button', { name: /구독 해지/i }));
    await waitFor(() => {
      expect(screen.getByRole('textbox', { name: /이메일 주소/i })).toBeInTheDocument();
    });
    expect(screen.queryByRole('button', { name: /구독 해지/i })).not.toBeInTheDocument();
  });

  it('잘못된 이메일 입력 시 유효성 에러 메시지 표시 (422 시뮬레이션)', async () => {
    const user = userEvent.setup();
    // 서버가 422를 반환하는 경우를 시뮬레이션 (유효한 형식이지만 서버 거부)
    mockSubscribeEmail.mockRejectedValue(new Error('422'));

    renderSettings();

    // 유효한 이메일 형식으로 입력해야 HTML5 기본 유효성 검사 통과
    await user.type(screen.getByRole('textbox', { name: /이메일 주소/i }), 'bad@example.com');
    await user.click(screen.getByRole('button', { name: /구독/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('유효한 이메일 주소를 입력해주세요.');
    });
  });

  it('네트워크 오류 시 일반 에러 메시지 표시', async () => {
    const user = userEvent.setup();
    mockSubscribeEmail.mockRejectedValue(new Error('Network error'));

    renderSettings();

    await user.type(screen.getByRole('textbox', { name: /이메일 주소/i }), 'test@example.com');
    await user.click(screen.getByRole('button', { name: /구독/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('요청 실패. 다시 시도해주세요.');
    });
  });
});
