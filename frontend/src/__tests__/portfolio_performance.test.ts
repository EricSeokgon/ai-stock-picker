// SPEC-STOCK-017 포트폴리오 성과 타입 정합성 테스트
import { describe, it, expect } from 'vitest';
import type {
  HoldingPerformance,
  PortfolioPerformance,
  ClassificationSummary,
  SectorPerformance,
} from '../api/portfolio';

// ─── 헬퍼: 목 데이터 생성 ─────────────────────────────────────────────────

function makeHolding(overrides: Partial<HoldingPerformance> = {}): HoldingPerformance {
  return {
    krx_code: '005930',
    quantity: 10,
    avg_buy_price: 70000,
    current_price: 75000,
    return_pct: 7.14,
    classification: 'high',
    sector: '전자/반도체',
    price_unavailable: false,
    ...overrides,
  };
}

function makeClassificationSummary(overrides: Partial<ClassificationSummary> = {}): ClassificationSummary {
  return {
    high: { count: 0, invested: 0, invested_pct: 0 },
    normal: { count: 0, invested: 0, invested_pct: 0 },
    low: { count: 0, invested: 0, invested_pct: 0 },
    ...overrides,
  };
}

function makePerformance(overrides: Partial<PortfolioPerformance> = {}): PortfolioPerformance {
  return {
    holdings: [],
    total_invested: 0,
    total_current: 0,
    total_return_pct: 0,
    classification_summary: makeClassificationSummary(),
    sector_performance: [],
    ...overrides,
  };
}

// ─── HoldingPerformance 타입 검증 ─────────────────────────────────────────

describe('HoldingPerformance 타입', () => {
  it('classification 필드는 high | normal | low 중 하나다', () => {
    const validClasses = ['high', 'normal', 'low'];
    const holding = makeHolding({ classification: 'high' });
    expect(validClasses).toContain(holding.classification);
  });

  it('price_unavailable=true 인 holding은 current_price가 avg_buy_price와 같다', () => {
    // 백엔드 계약: 현재가 미수신 시 buy_price를 그대로 사용
    const holding = makeHolding({
      avg_buy_price: 70000,
      current_price: 70000,
      return_pct: 0,
      price_unavailable: true,
    });
    expect(holding.price_unavailable).toBe(true);
    expect(holding.return_pct).toBe(0);
    expect(holding.current_price).toBe(holding.avg_buy_price);
  });

  it('sector 필드는 빈 문자열이 아닌 문자열이다', () => {
    const holding = makeHolding({ sector: '전자/반도체' });
    expect(holding.sector.length).toBeGreaterThan(0);
  });
});

// ─── PortfolioPerformance 타입 검증 ────────────────────────────────────────

describe('PortfolioPerformance 타입', () => {
  it('total_current 필드가 존재한다 (current_value 드리프트 수정 확인)', () => {
    const perf = makePerformance({ total_current: 750000 });
    // 드리프트 전: current_value 필드 사용
    // 드리프트 후: total_current 필드 사용
    expect(perf.total_current).toBe(750000);
    // @ts-expect-error current_value는 존재하지 않아야 함 (타입 정합화 확인)
    expect(perf.current_value).toBeUndefined();
  });

  it('holdings 배열 길이로 종목 수를 계산한다 (holdings_count 드리프트 수정 확인)', () => {
    const perf = makePerformance({
      holdings: [makeHolding(), makeHolding({ krx_code: '000660' })],
    });
    // 드리프트 전: holdings_count 필드 사용
    // 드리프트 후: holdings.length 사용
    expect(perf.holdings.length).toBe(2);
    // @ts-expect-error holdings_count는 존재하지 않아야 함
    expect(perf.holdings_count).toBeUndefined();
  });

  it('classification_summary에 high/normal/low 세 그룹이 있다', () => {
    const summary = makeClassificationSummary({
      high: { count: 1, invested: 700000, invested_pct: 58.3 },
      normal: { count: 1, invested: 500000, invested_pct: 41.7 },
      low: { count: 0, invested: 0, invested_pct: 0 },
    });
    expect(summary.high.count).toBe(1);
    expect(summary.normal.count).toBe(1);
    expect(summary.low.count).toBe(0);
  });

  it('invested_pct 합계는 100에 가깝다', () => {
    const summary = makeClassificationSummary({
      high: { count: 1, invested: 700000, invested_pct: 58.3 },
      normal: { count: 1, invested: 500000, invested_pct: 41.7 },
      low: { count: 0, invested: 0, invested_pct: 0 },
    });
    const total = summary.high.invested_pct + summary.normal.invested_pct + summary.low.invested_pct;
    expect(total).toBeCloseTo(100, 0);
  });
});

// ─── SectorPerformance 타입 검증 ───────────────────────────────────────────

describe('SectorPerformance 타입', () => {
  it('sector, holding_count, invested, return_pct 필드가 있다', () => {
    const sp: SectorPerformance = {
      sector: '전자/반도체',
      holding_count: 2,
      invested: 1700000,
      return_pct: 3.5,
    };
    expect(sp.sector).toBe('전자/반도체');
    expect(sp.holding_count).toBe(2);
    expect(sp.invested).toBeGreaterThan(0);
  });

  it('빈 sector_performance는 빈 배열이다', () => {
    const perf = makePerformance({ sector_performance: [] });
    expect(perf.sector_performance).toHaveLength(0);
  });
});
