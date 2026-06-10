// 섹터 분석 API 클라이언트
// @MX:ANCHOR: [AUTO] 섹터 랭킹 및 상세 조회 공개 진입점 — Sectors 페이지에서 직접 호출
// @MX:REASON: fan_in >= 3 (Sectors 페이지, SectorDetailPanel, 테스트)

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export interface SectorRankingItem {
  sector: string;
  trade_date: string;
  news_volume: number;
  avg_sentiment: number;
  trend_score: number;
}

export interface SectorRankingResponse {
  sort: string;
  limit: number;
  sectors: SectorRankingItem[];
  total: number;
}

export interface SectorTrendPoint {
  sector: string;
  trade_date: string;
  trend_score: number;
  news_volume: number;
  avg_sentiment: number;
}

export interface SectorStockItem {
  krx_code: string;
  mention_count: number;
}

export interface SectorDetailResponse {
  sector: string;
  days: number;
  trends: SectorTrendPoint[];
  stocks: SectorStockItem[];
  total_stocks: number;
}

export async function fetchSectorRanking(
  sort?: 'score' | 'sentiment' | 'volume',
  limit?: number,
): Promise<SectorRankingResponse> {
  const params = new URLSearchParams();
  if (sort) params.set('sort', sort);
  if (limit !== undefined) params.set('limit', String(limit));
  const query = params.toString();
  const url = `${API_BASE}/sectors/ranking${query ? `?${query}` : ''}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`API 오류: ${res.status}`);
  return res.json() as Promise<SectorRankingResponse>;
}

export async function fetchSectorDetail(
  sector: string,
  days?: number,
): Promise<SectorDetailResponse> {
  const params = new URLSearchParams();
  if (days !== undefined) params.set('days', String(days));
  const query = params.toString();
  const url = `${API_BASE}/sectors/${encodeURIComponent(sector)}/detail${query ? `?${query}` : ''}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`API 오류: ${res.status}`);
  return res.json() as Promise<SectorDetailResponse>;
}
