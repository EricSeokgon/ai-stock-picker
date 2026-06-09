// WatchlistStar 컴포넌트 테스트
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { WatchlistStar } from '../components/WatchlistStar';

// useAuth 모킹
const mockUseAuth = vi.fn();

vi.mock('../auth/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

// useNavigate 모킹
const mockNavigate = vi.fn();

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('WatchlistStar', () => {
  beforeEach(() => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true });
    mockNavigate.mockReset();
  });

  it('isWatchlisted=true 이면 ★을 표시한다', () => {
    render(
      <MemoryRouter>
        <WatchlistStar krxCode="005930" isWatchlisted={true} onToggle={vi.fn()} />
      </MemoryRouter>
    );
    expect(screen.getByText('★')).toBeDefined();
  });

  it('isWatchlisted=false 이면 ☆을 표시한다', () => {
    render(
      <MemoryRouter>
        <WatchlistStar krxCode="005930" isWatchlisted={false} onToggle={vi.fn()} />
      </MemoryRouter>
    );
    expect(screen.getByText('☆')).toBeDefined();
  });

  it('클릭 시 onToggle을 호출한다 (인증 상태)', () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true });
    const onToggle = vi.fn();

    render(
      <MemoryRouter>
        <WatchlistStar krxCode="005930" isWatchlisted={false} onToggle={onToggle} />
      </MemoryRouter>
    );

    fireEvent.click(screen.getByRole('button'));
    expect(onToggle).toHaveBeenCalledOnce();
  });

  it('미인증 상태에서 클릭 시 /login으로 이동한다', () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false });
    const onToggle = vi.fn();

    render(
      <MemoryRouter>
        <WatchlistStar krxCode="005930" isWatchlisted={false} onToggle={onToggle} />
      </MemoryRouter>
    );

    fireEvent.click(screen.getByRole('button'));
    expect(mockNavigate).toHaveBeenCalledWith('/login');
    expect(onToggle).not.toHaveBeenCalled();
  });
});
