// 종목 스크리너 페이지 테스트 (SPEC-STOCK-018)
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

// AuthContext mock
vi.mock('../auth/AuthContext', () => ({
  AuthProvider: ({ children }: { children: unknown }) => children,
  useAuth: () => ({
    user: null,
    token: null,
    isAuthenticated: false,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  }),
}));

// 스크리너 API mock
vi.mock('../api/screener', () => ({
  runScreener: vi.fn(),
  listPresets: vi.fn(),
  createPreset: vi.fn(),
  deletePreset: vi.fn(),
}));

import Screener from '../pages/Screener';
import { runScreener, listPresets } from '../api/screener';

const mockRunScreener = vi.mocked(runScreener);
const mockListPresets = vi.mocked(listPresets);

function renderScreener() {
  return render(
    <MemoryRouter>
      <Screener />
    </MemoryRouter>,
  );
}

describe('Screener 페이지', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRunScreener.mockResolvedValue({
      snapshot_date: '2026-06-15',
      total: 2,
      results: [
        {
          krx_code: '005930',
          name: '삼성전자',
          sector: '전기전자',
          current_price: 71000,
          change_pct: -0.84,
          per: 9.2,
          pbr: 1.1,
          roe: 12.5,
          market_cap: 423_000_000_000_000,
          dividend_yield: 3.1,
          week52_position: 55.0,
          in_watchlist: false,
          in_recommendations: true,
        },
        {
          krx_code: '000660',
          name: 'SK하이닉스',
          sector: '전기전자',
          current_price: 192000,
          change_pct: 1.2,
          per: 5.8,
          pbr: 2.3,
          roe: 35.0,
          market_cap: 139_000_000_000_000,
          dividend_yield: 0.5,
          week52_position: 70.0,
          in_watchlist: false,
          in_recommendations: false,
        },
      ],
    });
    mockListPresets.mockResolvedValue([]);
  });

  it('스크리너 페이지가 렌더링된다', () => {
    renderScreener();
    expect(screen.getByTestId('screener-page')).toBeTruthy();
    expect(screen.getByText('종목 스크리너')).toBeTruthy();
  });

  it('스크리너 실행 버튼이 존재한다', () => {
    renderScreener();
    expect(screen.getByTestId('run-screener-btn')).toBeTruthy();
  });

  it('스크리너 실행 시 결과 테이블이 렌더링된다', async () => {
    renderScreener();
    const btn = screen.getByTestId('run-screener-btn');
    fireEvent.click(btn);

    await waitFor(() => {
      expect(screen.getByTestId('screener-table')).toBeTruthy();
    });

    expect(screen.getByTestId('row-005930')).toBeTruthy();
    expect(screen.getByTestId('row-000660')).toBeTruthy();
  });

  it('결과 건수가 표시된다', async () => {
    renderScreener();
    fireEvent.click(screen.getByTestId('run-screener-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('result-count').textContent).toContain('2');
    });
  });

  it('runScreener API가 호출된다', async () => {
    renderScreener();
    fireEvent.click(screen.getByTestId('run-screener-btn'));

    await waitFor(() => {
      expect(mockRunScreener).toHaveBeenCalledTimes(1);
    });
  });

  it('API 오류 시 에러 메시지가 표시된다', async () => {
    mockRunScreener.mockRejectedValueOnce(new Error('서버 오류'));
    renderScreener();
    fireEvent.click(screen.getByTestId('run-screener-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('screener-error')).toBeTruthy();
    });
  });

  it('미인증 상태에서는 프리셋 UI가 표시되지 않는다', () => {
    renderScreener();
    expect(screen.queryByTestId('preset-name-input')).toBeNull();
  });
});
