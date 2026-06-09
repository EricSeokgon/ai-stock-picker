// 백테스트 API 래퍼 (Bearer 토큰 필요)

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

// 백테스트 전략 타입
export type BacktestStrategy = 'momentum' | 'volume';

// 백테스트 실행 요청 파라미터
export interface BacktestRunRequest {
  strategy: BacktestStrategy;
  start_date: string;  // YYYY-MM-DD
  end_date: string;    // YYYY-MM-DD
  universe_size?: number;
  top_n?: number;
}

// 백테스트 실행 응답
export interface BacktestRunResponse {
  run_id: number;
  message: string;
}

// 백테스트 실행 상태
export type BacktestStatus = 'pending' | 'running' | 'done' | 'failed';

// 백테스트 실행 정보
export interface BacktestRun {
  id: number;
  strategy: BacktestStrategy;
  start_date: string;
  end_date: string;
  universe_size: number | null;
  top_n: number | null;
  status: BacktestStatus;
  cagr: number | null;
  max_drawdown: number | null;
  sharpe_ratio: number | null;
  total_return: number | null;
  created_at: string;
}

// 일별 결과 데이터
export interface BacktestDailyResult {
  date: string;
  portfolio_value: number;
  benchmark_value: number;
  daily_return: number;
}

function authHeaders(token: string): Record<string, string> {
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };
}

// 백테스트 실행 요청
export async function apiRunBacktest(token: string, params: BacktestRunRequest): Promise<BacktestRunResponse> {
  const res = await fetch(`${API_BASE}/backtest/run`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(err.detail ?? `백테스트 실행 실패: ${res.status}`);
  }
  return res.json() as Promise<BacktestRunResponse>;
}

// 백테스트 실행 목록 조회
export async function apiListBacktestRuns(token: string): Promise<BacktestRun[]> {
  const res = await fetch(`${API_BASE}/backtest/runs`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`백테스트 목록 조회 실패: ${res.status}`);
  return res.json() as Promise<BacktestRun[]>;
}

// 특정 백테스트 실행 상세 조회
export async function apiGetBacktestRun(token: string, runId: number): Promise<BacktestRun> {
  const res = await fetch(`${API_BASE}/backtest/runs/${runId}`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`백테스트 조회 실패: ${res.status}`);
  return res.json() as Promise<BacktestRun>;
}

// 백테스트 일별 결과 조회
export async function apiGetBacktestResults(token: string, runId: number): Promise<BacktestDailyResult[]> {
  const res = await fetch(`${API_BASE}/backtest/runs/${runId}/results`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`백테스트 결과 조회 실패: ${res.status}`);
  return res.json() as Promise<BacktestDailyResult[]>;
}
