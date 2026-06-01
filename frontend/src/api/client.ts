// API 클라이언트 - fetch 래퍼
import type { RecommendationsResponse, NewsResponse } from '../types';

// 프로덕션에서는 VITE_API_BASE_URL 환경변수 필수 설정
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export async function fetchRecommendations(): Promise<RecommendationsResponse> {
  const res = await fetch(`${API_BASE}/recommendations`);
  if (!res.ok) throw new Error(`API 오류: ${res.status}`);
  return res.json() as Promise<RecommendationsResponse>;
}

export async function fetchNews(limit = 20): Promise<NewsResponse> {
  const res = await fetch(`${API_BASE}/news?limit=${limit}`);
  if (!res.ok) throw new Error(`API 오류: ${res.status}`);
  return res.json() as Promise<NewsResponse>;
}
