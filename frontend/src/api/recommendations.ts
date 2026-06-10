// 추천 히스토리 API 클라이언트
import type { RecommendationItem } from '../types';

// @MX:ANCHOR: [AUTO] 추천 히스토리 API 공개 진입점 — History 페이지에서 직접 호출
// @MX:REASON: fan_in >= 3 예상 (History 컴포넌트, 테스트, 잠재적 대시보드 위젯)

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export interface DailyRecommendations {
  date: string;
  recommendations: RecommendationItem[];
}

export interface RecommendationHistoryResponse {
  days: number;
  groups: DailyRecommendations[];
}

export async function getRecommendationHistory(days: number): Promise<RecommendationHistoryResponse> {
  const res = await fetch(`${API_BASE}/recommendations/history?days=${days}`);
  if (!res.ok) throw new Error(`API 오류: ${res.status}`);
  return res.json() as Promise<RecommendationHistoryResponse>;
}

// --- 피드백 API ---

export interface FeedbackSummaryResponse {
  krx_code: string;
  up: number;
  down: number;
}

export async function fetchFeedbackSummary(krxCode: string): Promise<FeedbackSummaryResponse> {
  const res = await fetch(`${API_BASE}/recommendations/${krxCode}/feedback`);
  if (!res.ok) throw new Error(`API 오류: ${res.status}`);
  return res.json() as Promise<FeedbackSummaryResponse>;
}

export async function submitFeedback(krxCode: string, vote: 'up' | 'down'): Promise<FeedbackSummaryResponse> {
  const res = await fetch(`${API_BASE}/recommendations/${krxCode}/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ vote }),
  });
  if (!res.ok) throw new Error(`API 오류: ${res.status}`);
  return res.json() as Promise<FeedbackSummaryResponse>;
}
