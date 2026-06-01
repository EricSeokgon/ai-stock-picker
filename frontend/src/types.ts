// 도메인 타입 정의

// 섹터 트렌드 데이터 포인트
export interface SectorTrendPoint {
  sector: string;
  trade_date: string;
  trend_score: number;      // 0.0~1.0
  news_volume: number;
  avg_sentiment: number;    // -1.0~1.0
}

// 섹터 트렌드 API 응답
export interface SectorTrendsResponse {
  trends: SectorTrendPoint[];
  days: number;
}

// 추천 종목 기여 뉴스
export interface ContributingNewsItem {
  title: string;
  summary: string | null;
  sentiment: string;        // "positive" | "negative" | "neutral"
  published_at: string;
}

// 개별 종목 추천 상세 정보
export interface RecommendationDetail {
  krx_code: string;
  trade_date: string;
  total_score: number;
  sentiment_score: number;
  volume_score: number;
  momentum_score: number;
  anomaly_score: number;
  reasoning: string;
  contributing_news: ContributingNewsItem[];
  disclaimer: string;
}

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
