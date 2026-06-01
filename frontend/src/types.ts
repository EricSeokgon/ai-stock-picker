// 도메인 타입 정의

export interface RecommendationItem {
  rank: number;
  krx_code: string;
  total_score: number;
  sentiment_score: number;
  volume_score: number;
  momentum_score: number;
  anomaly_score: number;
  reasoning: string;
}

export interface RecommendationsData {
  trade_date: string;
  recommendations: RecommendationItem[];
  disclaimer: string;
  last_updated: string | null;
}

export interface PreparingData {
  status: 'preparing';
  last_updated: null;
  disclaimer: string;
}

export type RecommendationsResponse = RecommendationsData | PreparingData;

export interface NewsItem {
  title: string;
  summary: string | null;
  sentiment: string | null;
  source: string;
  url: string;
  published_at: string;
}

export interface NewsResponse {
  news: NewsItem[];
  total: number;
}
