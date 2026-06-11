// 백테스트 타입·상태·차트 변환 테스트 (T-023)
import { describe, it, expect } from 'vitest';
import type {
  BacktestStartResponse,
  BacktestRun,
  BacktestStatus,
  BacktestDailyResult,
  BacktestRunRequest,
} from '../api/backtest';

// ─── T-023-1: 타입 형태 검증 ───────────────────────────────────────────────

describe('BacktestStartResponse 타입 형태', () => {
  it('run_id(string)과 message(string)를 가져야 한다', () => {
    const resp: BacktestStartResponse = { run_id: 'abc-123', message: '백테스트 시작' };
    expect(resp.run_id).toBe('abc-123');
    expect(resp.message).toBe('백테스트 시작');
    // run_id는 string 타입
    expect(typeof resp.run_id).toBe('string');
  });

  it('run_id는 number가 아닌 string이어야 한다', () => {
    const resp: BacktestStartResponse = { run_id: '42', message: '시작' };
    expect(typeof resp.run_id).toBe('string');
    expect(resp.run_id).not.toBe(42);
  });
});

describe('BacktestRun 타입 형태', () => {
  it('필수 필드가 모두 존재해야 한다', () => {
    const run: BacktestRun = {
      id: 'run-001',
      user_id: 'user-1',
      strategy: 'momentum',
      start_date: '2023-01-01',
      end_date: '2024-01-01',
      status: 'done',
      universe_size: 100,
      top_n: 10,
      cagr: 0.12,
      max_drawdown: -0.05,
      sharpe_ratio: 1.5,
      total_return: 0.15,
      win_rate: 0.6,
      total_trades: 120,
      created_at: '2024-01-01T00:00:00Z',
      completed_at: '2024-01-01T01:00:00Z',
    };
    expect(run.id).toBe('run-001');
    expect(run.user_id).toBe('user-1');
    expect(run.win_rate).toBe(0.6);
    expect(run.total_trades).toBe(120);
    expect(run.completed_at).toBeTruthy();
  });

  it('nullable 필드는 null을 허용해야 한다', () => {
    const run: BacktestRun = {
      id: 'run-002',
      user_id: 'user-1',
      strategy: 'volume',
      start_date: '2023-01-01',
      end_date: '2024-01-01',
      status: 'pending',
      universe_size: null,
      top_n: null,
      cagr: null,
      max_drawdown: null,
      sharpe_ratio: null,
      total_return: null,
      win_rate: null,
      total_trades: null,
      created_at: '2024-01-01T00:00:00Z',
      completed_at: null,
    };
    expect(run.win_rate).toBeNull();
    expect(run.total_trades).toBeNull();
    expect(run.completed_at).toBeNull();
  });
});

describe('BacktestRunRequest 타입', () => {
  it('필수 필드만으로 생성할 수 있어야 한다', () => {
    const req: BacktestRunRequest = {
      strategy: 'momentum',
      start_date: '2023-01-01',
      end_date: '2024-01-01',
    };
    expect(req.universe_size).toBeUndefined();
    expect(req.top_n).toBeUndefined();
  });

  it('선택 필드를 포함할 수 있어야 한다', () => {
    const req: BacktestRunRequest = {
      strategy: 'momentum',
      start_date: '2023-01-01',
      end_date: '2024-01-01',
      universe_size: 200,
      top_n: 15,
    };
    expect(req.universe_size).toBe(200);
    expect(req.top_n).toBe(15);
  });
});

// ─── T-023-2: 상태 배지 매핑 ───────────────────────────────────────────────

describe('BacktestStatus 상태 배지 매핑', () => {
  // 상태별 스타일 분류 헬퍼 (Backtest.tsx의 statusColor 로직 반영)
  function getStatusStyle(status: BacktestStatus): 'success' | 'error' | 'loading' {
    switch (status) {
      case 'done': return 'success';
      case 'failed': return 'error';
      case 'pending':
      case 'running': return 'loading';
    }
  }

  it('"done" 상태는 success 스타일이어야 한다', () => {
    expect(getStatusStyle('done')).toBe('success');
  });

  it('"failed" 상태는 error 스타일이어야 한다', () => {
    expect(getStatusStyle('failed')).toBe('error');
  });

  it('"pending" 상태는 loading 스타일이어야 한다', () => {
    expect(getStatusStyle('pending')).toBe('loading');
  });

  it('"running" 상태는 loading 스타일이어야 한다', () => {
    expect(getStatusStyle('running')).toBe('loading');
  });

  it('"error" 값은 유효한 BacktestStatus가 아니어야 한다', () => {
    // 타입 레벨에서 "error"는 허용되지 않음을 런타임으로도 확인
    const validStatuses: BacktestStatus[] = ['pending', 'running', 'done', 'failed'];
    expect(validStatuses).not.toContain('error');
  });
});

// ─── T-023-3: 차트 데이터 변환 ─────────────────────────────────────────────

describe('BacktestDailyResult 차트 데이터 변환', () => {
  // hasBenchmark 로직 (Backtest.tsx와 동일)
  function hasBenchmark(results: BacktestDailyResult[]): boolean {
    return results.some((r) => r.benchmark_value !== null);
  }

  const sampleResults: BacktestDailyResult[] = [
    { date: '2023-01-02', portfolio_value: 1.0, benchmark_value: 1.0, daily_return: 0.0 },
    { date: '2023-01-03', portfolio_value: 1.02, benchmark_value: null, daily_return: 0.02 },
    { date: '2023-01-04', portfolio_value: 1.01, benchmark_value: 1.01, daily_return: -0.01 },
  ];

  it('일부 benchmark_value가 null이어도 hasBenchmark는 true여야 한다', () => {
    expect(hasBenchmark(sampleResults)).toBe(true);
  });

  it('모든 benchmark_value가 null이면 hasBenchmark는 false여야 한다', () => {
    const noB: BacktestDailyResult[] = [
      { date: '2023-01-02', portfolio_value: 1.0, benchmark_value: null, daily_return: 0.0 },
      { date: '2023-01-03', portfolio_value: 1.02, benchmark_value: null, daily_return: 0.02 },
    ];
    expect(hasBenchmark(noB)).toBe(false);
  });

  it('빈 배열의 경우 hasBenchmark는 false여야 한다', () => {
    expect(hasBenchmark([])).toBe(false);
  });

  it('portfolio_value는 항상 숫자여야 한다', () => {
    sampleResults.forEach((r) => {
      expect(typeof r.portfolio_value).toBe('number');
    });
  });

  it('null benchmark_value를 가진 포인트가 차트 데이터에 포함되어도 타입 오류 없이 처리된다', () => {
    // recharts는 null 값을 gap으로 처리 — 배열 자체는 유효
    const nullPoint = sampleResults.find((r) => r.benchmark_value === null);
    expect(nullPoint).toBeDefined();
    expect(nullPoint!.benchmark_value).toBeNull();
    expect(nullPoint!.portfolio_value).toBeGreaterThan(0);
  });
});

// ─── T-023-4: win_rate 포맷 로직 ──────────────────────────────────────────

describe('win_rate 퍼센트 포맷', () => {
  function fmtWinRate(winRate: number | null): string {
    if (winRate === null) return '-';
    return `${(winRate * 100).toFixed(1)}%`;
  }

  it('0.6 → "60.0%"', () => {
    expect(fmtWinRate(0.6)).toBe('60.0%');
  });

  it('0.333 → "33.3%"', () => {
    expect(fmtWinRate(0.333)).toBe('33.3%');
  });

  it('null → "-"', () => {
    expect(fmtWinRate(null)).toBe('-');
  });

  it('0 → "0.0%"', () => {
    expect(fmtWinRate(0)).toBe('0.0%');
  });
});

describe('total_return 퍼센트 포맷', () => {
  function fmtPct(v: number | null): string {
    if (v === null) return '-';
    return `${(v * 100).toFixed(2)}%`;
  }

  it('0.15 → "15.00%"', () => {
    expect(fmtPct(0.15)).toBe('15.00%');
  });

  it('null → "-"', () => {
    expect(fmtPct(null)).toBe('-');
  });

  it('음수 처리 → "-5.00%"', () => {
    expect(fmtPct(-0.05)).toBe('-5.00%');
  });
});
