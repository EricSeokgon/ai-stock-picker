// 백테스트 API 래퍼 (Bearer 토큰 필요)
// @MX:ANCHOR: [AUTO] 백테스트 API 진입점 — Backtest.tsx, backtest.test.ts에서 직접 참조
// @MX:REASON: 이 파일의 타입·함수는 3개 이상 컴포넌트가 직접 import하는 공개 계약

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

// 백테스트 전략 타입
export type BacktestStrategy = 'momentum' | 'volume';

// 백테스트 실행 요청 파라미터
export interface BacktestRunRequest {
  strategy: string;
  start_date: string;  // YYYY-MM-DD
  end_date: string;    // YYYY-MM-DD
  universe_size?: number;
  top_n?: number;
}

// POST /backtest/run 응답 (HTTP 202)
export interface BacktestStartResponse {
  run_id: string;
  message: string;
}

// 백테스트 실행 상태 — "failed" 사용, "error" 미사용
export type BacktestStatus = 'pending' | 'running' | 'done' | 'failed';

// 백테스트 실행 정보 (GET /runs, GET /runs/{id})
export interface BacktestRun {
  id: string;
  user_id: string;
  strategy: string;
  start_date: string;
  end_date: string;
  status: BacktestStatus;
  universe_size: number | null;
  top_n: number | null;
  cagr: number | null;
  max_drawdown: number | null;
  sharpe_ratio: number | null;
  total_return: number | null;
  win_rate: number | null;
  total_trades: number | null;
  created_at: string;
  completed_at: string | null;
}

// 일별 결과 데이터 (GET /runs/{id}/results)
export interface BacktestDailyResult {
  date: string;
  portfolio_value: number;
  benchmark_value: number | null;
  daily_return: number;
}

function authHeaders(token: string): Record<string, string> {
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };
}

// 백테스트 실행 요청 (POST /backtest/run → HTTP 202)
export async function runBacktest(token: string, req: BacktestRunRequest): Promise<BacktestStartResponse> {
  const res = await fetch(`${API_BASE}/backtest/run`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(err.detail ?? `백테스트 실행 실패: ${res.status}`);
  }
  return res.json() as Promise<BacktestStartResponse>;
}

// 하위 호환 별칭
export const apiRunBacktest = runBacktest;

// 백테스트 실행 목록 조회
export async function getBacktestRuns(token: string): Promise<BacktestRun[]> {
  const res = await fetch(`${API_BASE}/backtest/runs`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`백테스트 목록 조회 실패: ${res.status}`);
  return res.json() as Promise<BacktestRun[]>;
}

export const apiListBacktestRuns = getBacktestRuns;

// 특정 백테스트 실행 상세 조회
export async function getBacktestRun(token: string, runId: string): Promise<BacktestRun> {
  const res = await fetch(`${API_BASE}/backtest/runs/${runId}`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`백테스트 조회 실패: ${res.status}`);
  return res.json() as Promise<BacktestRun>;
}

export const apiGetBacktestRun = getBacktestRun;

// 백테스트 일별 결과 조회
export async function getBacktestResults(token: string, runId: string): Promise<BacktestDailyResult[]> {
  const res = await fetch(`${API_BASE}/backtest/runs/${runId}/results`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`백테스트 결과 조회 실패: ${res.status}`);
  return res.json() as Promise<BacktestDailyResult[]>;
}

export const apiGetBacktestResults = getBacktestResults;
