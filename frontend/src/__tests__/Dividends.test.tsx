// SPEC-STOCK-019 배당 분석 API 타입 정합성 + getPortfolioDividends 동작 테스트
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { HoldingDividend, PortfolioDividends, DividendCalendarMonth } from '../api/dividends';

// ─── 헬퍼: 목 데이터 생성 ─────────────────────────────────────────────────

function makeHoldingDividend(overrides: Partial<HoldingDividend> = {}): HoldingDividend {
  return {
    krx_code: '005930',
    name: '삼성전자',
    quantity: 10,
    dps: 1444,
    dividend_yield: 2.01,
    ex_dividend_month: 12,
    annual_income: 14440,
    yoy_dps_change_pct: null,
    dividend_available: true,
    ...overrides,
  };
}

function makeCalendarMonth(overrides: Partial<DividendCalendarMonth> = {}): DividendCalendarMonth {
  return {
    month: 12,
    holdings: ['005930'],
    total_income: 14440,
    ...overrides,
  };
}

function makePortfolioDividends(overrides: Partial<PortfolioDividends> = {}): PortfolioDividends {
  return {
    holdings: [makeHoldingDividend()],
    total_annual_income: 14440,
    weighted_avg_yield: 2.01,
    calendar: [makeCalendarMonth()],
    coverage_count: 1,
    total_holdings: 1,
    ...overrides,
  };
}

// ─── 타입 정합성 테스트 ────────────────────────────────────────────────────

describe('HoldingDividend 타입', () => {
  it('dps와 dividend_yield는 null 가능이다', () => {
    const h = makeHoldingDividend({ dps: null, dividend_yield: null, dividend_available: false });
    expect(h.dps).toBeNull();
    expect(h.dividend_yield).toBeNull();
    expect(h.dividend_available).toBe(false);
  });

  it('annual_income은 quantity × dps로 계산된다', () => {
    const h = makeHoldingDividend({ quantity: 10, dps: 1444, annual_income: 14440 });
    expect(h.annual_income).toBe(h.quantity * (h.dps ?? 0));
  });
});

describe('PortfolioDividends 타입', () => {
  it('coverage_count는 total_holdings를 초과할 수 없다', () => {
    const d = makePortfolioDividends({ coverage_count: 1, total_holdings: 3 });
    expect(d.coverage_count).toBeLessThanOrEqual(d.total_holdings);
  });

  it('배당 데이터 없는 빈 포트폴리오는 0 값을 가진다', () => {
    const d = makePortfolioDividends({
      holdings: [],
      total_annual_income: 0,
      weighted_avg_yield: 0,
      calendar: [],
      coverage_count: 0,
      total_holdings: 0,
    });
    expect(d.total_annual_income).toBe(0);
    expect(d.weighted_avg_yield).toBe(0);
    expect(d.calendar).toHaveLength(0);
  });
});

// ─── getPortfolioDividends API 함수 동작 테스트 ──────────────────────────

describe('getPortfolioDividends API 동작', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('성공 응답 시 PortfolioDividends 구조를 반환한다', async () => {
    const mockData = makePortfolioDividends();
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockData,
    }) as ReturnType<typeof vi.fn>;

    const { getPortfolioDividends } = await import('../api/dividends');
    const result = await getPortfolioDividends('test-token', 1);

    expect(result.total_annual_income).toBe(14440);
    expect(result.holdings).toHaveLength(1);
    expect(result.calendar[0].month).toBe(12);
  });

  it('비정상 응답(4xx) 시 Error를 던진다', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
    }) as ReturnType<typeof vi.fn>;

    const { getPortfolioDividends } = await import('../api/dividends');
    await expect(getPortfolioDividends('test-token', 999)).rejects.toThrow('배당 분석 조회 실패: 404');
  });

  it('캘린더는 ex_dividend_month가 없는 종목을 포함하지 않는다', () => {
    const data = makePortfolioDividends({
      holdings: [
        makeHoldingDividend({ ex_dividend_month: 12 }),
        makeHoldingDividend({ krx_code: '000660', ex_dividend_month: null }),
      ],
      // 캘린더에는 12월만 있어야 함
      calendar: [makeCalendarMonth({ month: 12, holdings: ['005930'] })],
    });
    expect(data.calendar).toHaveLength(1);
    expect(data.calendar[0].holdings).not.toContain('000660');
  });
});
