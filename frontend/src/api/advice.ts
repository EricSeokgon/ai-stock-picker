// AI 투자 조언 API 래퍼 — SPEC-STOCK-014 M6
// Bearer 토큰 인증 필요

// @MX:ANCHOR: [AUTO] AI 투자 조언 API 진입점 — AdviceHistory, Portfolio 페이지에서 사용
// @MX:REASON: rebalance/risk-profile/market-briefing/history/feedback 5개 엔드포인트 노출

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

function authHeaders(token: string): Record<string, string> {
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };
}

// ─────────────────────────────────────────────────────────────────
// 타입 정의
// ─────────────────────────────────────────────────────────────────

export interface RebalanceAction {
  krx_code: string;
  action: 'buy_more' | 'reduce' | 'hold';
  reason: string;
}

export interface RebalanceAdvice {
  advice_id?: number;
  actions?: RebalanceAction[];
  message?: string;
  error?: string;
  disclaimer: string;
}

export interface RiskProfileAdvice {
  advice_id?: number;
  risk_score?: number;
  explanation?: string;
  message?: string;
  error?: string;
  disclaimer: string;
}

export interface MarketBriefingAdvice {
  advice_id?: number;
  briefing?: string;
  cached?: boolean;
  message?: string;
  error?: string;
  disclaimer: string;
}

export interface AdviceHistoryItem {
  id: number;
  advice_type: string;
  ref_date: string;
  title: string;
  body: string | null;
  risk_score: number | null;
  feedback: string | null;
  created_at: string;
}

export type FeedbackValue = 'helpful' | 'not_helpful' | 'neutral';

export interface FeedbackResponse {
  advice_id: number;
  feedback: string;
}

// ─────────────────────────────────────────────────────────────────
// API 함수
// ─────────────────────────────────────────────────────────────────

/** 리밸런싱 제안 요청 (REQ-RB-001) */
export async function fetchRebalanceAdvice(token: string): Promise<RebalanceAdvice> {
  const res = await fetch(`${API_BASE}/advice/rebalance`, {
    method: 'POST',
    headers: authHeaders(token),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(err.detail ?? `리밸런싱 조언 요청 실패: ${res.status}`);
  }
  return res.json() as Promise<RebalanceAdvice>;
}

/** 리스크 프로파일 분석 요청 (REQ-RM-001) */
export async function fetchRiskProfile(token: string): Promise<RiskProfileAdvice> {
  const res = await fetch(`${API_BASE}/advice/risk-profile`, {
    method: 'POST',
    headers: authHeaders(token),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(err.detail ?? `리스크 프로파일 요청 실패: ${res.status}`);
  }
  return res.json() as Promise<RiskProfileAdvice>;
}

/** 시장 브리핑 조회 (REQ-MB-001) */
export async function fetchMarketBriefing(token: string): Promise<MarketBriefingAdvice> {
  const res = await fetch(`${API_BASE}/advice/market-briefing`, {
    method: 'GET',
    headers: authHeaders(token),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(err.detail ?? `시장 브리핑 요청 실패: ${res.status}`);
  }
  return res.json() as Promise<MarketBriefingAdvice>;
}

/** AI 조언 이력 조회 (REQ-AIV-004) */
export async function fetchAdviceHistory(token: string): Promise<AdviceHistoryItem[]> {
  const res = await fetch(`${API_BASE}/advice/history`, {
    method: 'GET',
    headers: authHeaders(token),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(err.detail ?? `조언 이력 조회 실패: ${res.status}`);
  }
  return res.json() as Promise<AdviceHistoryItem[]>;
}

/** 조언 피드백 제출 (REQ-FB-001) */
export async function submitAdviceFeedback(
  token: string,
  adviceId: number,
  feedback: FeedbackValue,
): Promise<FeedbackResponse> {
  const res = await fetch(`${API_BASE}/advice/${adviceId}/feedback`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ feedback }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(err.detail ?? `피드백 제출 실패: ${res.status}`);
  }
  return res.json() as Promise<FeedbackResponse>;
}
