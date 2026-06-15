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

// 스코어 투명성 - 개별 팩터 기여도
export interface ScoreFactorContribution {
  factor: string;        // "sentiment" | "volume" | "momentum" | "anomaly"
  weight: number;        // 예: 0.40
  factor_score: number;  // 원시 팩터 점수 0~1
  contribution: number;  // weight * factor_score
}

// 스코어 분해 (피드백 델타 포함)
export interface ScoreBreakdown {
  factors: ScoreFactorContribution[];
  feedback_delta?: number | null;
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
  // 스코어 투명성 필드 (SPEC-STOCK-009)
  base_score?: number | null;
  feedback_score?: number | null;
  score_breakdown?: ScoreBreakdown | null;
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
  // 스코어 투명성 필드 (SPEC-STOCK-009)
  base_score?: number | null;
  feedback_score?: number | null;
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
  // 5단계 한국어 감성 레이블 (백엔드 Phase 2+에서 제공)
  sentiment_label?: string | null;
  source: string;
  url: string;
  published_at: string;
}

export interface NewsResponse {
  news: NewsItem[];
  total: number;
}

// SPEC-STOCK-021: 시장 감성 집계 타입
export interface MarketSentimentResponse {
  avg_score: number | null;
  // score_to_label 결과: "매우긍정"/"긍정"/"중립"/"부정"/"매우부정"/null
  label: string | null;
  positive: number;
  negative: number;
  neutral: number;
  total: number;
  as_of: string;
}

// SPEC-STOCK-021: 수동 수집·분석 트리거 결과
export interface NewsFetchResult {
  collected: number;
  analyzed: number;
}
