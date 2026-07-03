// SPEC-STOCK-049: 거래 내역 프론트엔드 단위 테스트 (T-049-FE-001 ~ T-049-FE-003)
// 실행: cd frontend && npx vitest run src/__tests__/transactions_049.test.tsx
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

// API 모듈 모킹 (테스트 격리)
vi.mock('../api/portfolio', () => ({
  getPortfolio: vi.fn(),
  getHoldings: vi.fn(),
  addTransaction: vi.fn(),
  listTransactions: vi.fn(),
  getRealizedPnl: vi.fn(),
  // 기타 Portfolio.tsx에서 사용하는 API 함수
  apiListPortfolios: vi.fn(),
  apiCreatePortfolio: vi.fn(),
  apiListHoldings: vi.fn(),
  apiAddHolding: vi.fn(),
  apiGetPerformance: vi.fn(),
  apiOptimizePortfolio: vi.fn(),
}));

// Portfolio.tsx가 임포트하는 .js JSX 컴포넌트 모킹 (파일 확장자 이슈 우회)
const nullComponent = () => null;
vi.mock('../components/BacktestPanel', () => ({ default: nullComponent }));
vi.mock('../components/PerformanceSummaryPanel', () => ({ default: nullComponent }));
vi.mock('../components/PortfolioAlertPanel', () => ({ default: nullComponent }));
vi.mock('../components/NewStockSuggestions', () => ({ default: nullComponent }));
vi.mock('../components/RiskAnalysisPanel', () => ({ default: nullComponent }));
vi.mock('../components/PortfolioScoreCard', () => ({ default: nullComponent }));
vi.mock('../components/RebalancingTable', () => ({ default: nullComponent }));
vi.mock('../components/DividendSummaryPanel', () => ({ default: nullComponent }));
vi.mock('../components/DividendCalendarView', () => ({ default: nullComponent }));
vi.mock('../components/DRIPSimulator', () => ({ default: nullComponent }));
vi.mock('../components/BenchmarkComparisonPanel', () => ({ default: nullComponent }));
vi.mock('../components/BenchmarkChartView', () => ({ default: nullComponent }));
vi.mock('../components/PortfolioReportPanel', () => ({ default: nullComponent }));
vi.mock('../components/AICommentaryPanel', () => ({ default: nullComponent }));
vi.mock('../components/PortfolioGoalPanel', () => ({ default: nullComponent }));
vi.mock('../components/MarketStatusBadge', () => ({ MarketStatusBadge: nullComponent }));
vi.mock('../components/LivePriceBadge', () => ({ LivePriceBadge: nullComponent }));
vi.mock('../components/PerformanceDonutChart', () => ({ PerformanceDonutChart: nullComponent }));
vi.mock('../hooks/useMarketPolling', () => ({
  useMarketPolling: () => ({}),
}));

vi.mock('../auth/AuthContext', () => ({
  useAuth: vi.fn().mockReturnValue({
    token: 'mock-token-049',
    user: { id: 1, username: 'testuser' },
  }),
}));

// AuthContext 임포트
import { useAuth } from '../auth/AuthContext';
// API 함수 임포트
import {
  addTransaction,
  listTransactions,
  getRealizedPnl,
} from '../api/portfolio';


// ─────────────────────────────────────────────────────────────────────────────
// T-049-FE-001: 거래 추가 폼 — API 호출 확인
// ─────────────────────────────────────────────────────────────────────────────

describe('T-049-FE-001: 거래 추가 폼', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useAuth as ReturnType<typeof vi.fn>).mockReturnValue({
      token: 'mock-token-049',
      user: { id: 1, username: 'testuser' },
    });
  });

  it('BUY 폼 제출 시 addTransaction API 호출', async () => {
    (addTransaction as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: 1,
      portfolio_id: 1,
      krx_code: '005930',
      txn_type: 'BUY',
      quantity: 10,
      price: '50000.00',
      txn_date: '2026-01-01',
      note: null,
    });
    (listTransactions as ReturnType<typeof vi.fn>).mockResolvedValue({
      transactions: [],
      total: 0,
      page: 1,
      page_size: 20,
    });
    (getRealizedPnl as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [],
      total_realized_pnl: '0.00',
    });

    // TransactionTab 컴포넌트 임포트 (또는 Portfolio 전체)
    const { TransactionTab } = await import('../pages/Portfolio');

    render(
      <MemoryRouter initialEntries={['/portfolios/1']}>
        <TransactionTab portfolioId={1} />
      </MemoryRouter>
    );

    // 거래 추가 폼 대기
    await waitFor(() => {
      expect(screen.getByTestId('txn-krx-code-input')).toBeInTheDocument();
    });

    // 폼 입력
    fireEvent.change(screen.getByTestId('txn-krx-code-input'), {
      target: { value: '005930' },
    });
    fireEvent.change(screen.getByTestId('txn-quantity-input'), {
      target: { value: '10' },
    });
    fireEvent.change(screen.getByTestId('txn-price-input'), {
      target: { value: '50000' },
    });

    // 제출
    fireEvent.click(screen.getByTestId('txn-submit-btn'));

    await waitFor(() => {
      expect(addTransaction).toHaveBeenCalledWith(
        'mock-token-049',
        1,
        expect.objectContaining({
          krx_code: '005930',
          txn_type: 'BUY',
          quantity: 10,
          price: 50000,
        })
      );
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// T-049-FE-002: 거래 목록 렌더링
// ─────────────────────────────────────────────────────────────────────────────

describe('T-049-FE-002: 거래 목록 렌더링', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useAuth as ReturnType<typeof vi.fn>).mockReturnValue({
      token: 'mock-token-049',
      user: { id: 1, username: 'testuser' },
    });
  });

  it('listTransactions 결과를 테이블에 렌더링', async () => {
    (listTransactions as ReturnType<typeof vi.fn>).mockResolvedValue({
      transactions: [
        {
          id: 1,
          portfolio_id: 1,
          krx_code: '005930',
          txn_type: 'BUY',
          quantity: 10,
          price: '50000.00',
          txn_date: '2026-01-01',
          note: null,
        },
        {
          id: 2,
          portfolio_id: 1,
          krx_code: '005930',
          txn_type: 'SELL',
          quantity: 5,
          price: '60000.00',
          txn_date: '2026-01-02',
          note: '수익 실현',
        },
      ],
      total: 2,
      page: 1,
      page_size: 20,
    });
    (getRealizedPnl as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [],
      total_realized_pnl: '0.00',
    });

    const { TransactionTab } = await import('../pages/Portfolio');

    render(
      <MemoryRouter>
        <TransactionTab portfolioId={1} />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('txn-list')).toBeInTheDocument();
    });

    // 거래 항목 렌더링 확인 (두 행 모두 005930 종목이므로 getAllByText 사용)
    const codeElems = screen.getAllByText('005930');
    expect(codeElems.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('BUY')).toBeInTheDocument();
    expect(screen.getByText('SELL')).toBeInTheDocument();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// T-049-FE-003: 실현손익 표시
// ─────────────────────────────────────────────────────────────────────────────

describe('T-049-FE-003: 실현손익 표시', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useAuth as ReturnType<typeof vi.fn>).mockReturnValue({
      token: 'mock-token-049',
      user: { id: 1, username: 'testuser' },
    });
  });

  it('getRealizedPnl 결과를 total_realized_pnl과 함께 렌더링', async () => {
    (listTransactions as ReturnType<typeof vi.fn>).mockResolvedValue({
      transactions: [],
      total: 0,
      page: 1,
      page_size: 20,
    });
    (getRealizedPnl as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [
        { krx_code: '005930', realized_pnl: '7500.00', total_sold_qty: 5 },
      ],
      total_realized_pnl: '7500.00',
    });

    const { TransactionTab } = await import('../pages/Portfolio');

    render(
      <MemoryRouter>
        <TransactionTab portfolioId={1} />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('pnl-total')).toBeInTheDocument();
    });

    // 총 실현손익 표시 확인
    expect(screen.getByTestId('pnl-total')).toHaveTextContent('7500');
  });
});
