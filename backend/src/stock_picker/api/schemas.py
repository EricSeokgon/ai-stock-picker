# API 응답 스키마 (Pydantic v2)
from datetime import datetime, date
from typing import Literal

from pydantic import BaseModel

# @MX:ANCHOR: [AUTO] API 공개 계약 - 프론트엔드와 공유되는 응답 스키마
# @MX:REASON: 프론트엔드 React 앱이 이 스키마를 직접 의존하며, 변경 시 하위 호환성 검토 필수

DISCLAIMER = (
    "이 서비스는 투자 정보 제공 목적으로만 사용됩니다. "
    "투자 권유나 자문이 아니며, 투자 결과에 대한 책임은 투자자 본인에게 있습니다."
)


class RecommendationItem(BaseModel):
    """개별 추천 종목 항목"""

    rank: int
    krx_code: str
    total_score: float
    sentiment_score: float
    volume_score: float
    momentum_score: float
    anomaly_score: float
    reasoning: str
    # Claude Haiku가 생성한 한국어 추천 근거 (TASK-004, nullable — 하위 호환성 유지)
    explanation: str | None = None


class RecommendationsResponse(BaseModel):
    """추천 결과 응답"""

    trade_date: date | None = None
    recommendations: list[RecommendationItem]
    disclaimer: str = DISCLAIMER
    last_updated: datetime | None = None


class PreparingResponse(BaseModel):
    """데이터 준비 중 상태 응답 (AC-10)"""

    status: Literal["preparing"] = "preparing"
    last_updated: datetime | None = None
    disclaimer: str = DISCLAIMER


class NewsItem(BaseModel):
    """개별 뉴스 항목"""

    title: str
    summary: str | None = None
    sentiment: str | None = None
    # 감성 5단계 라벨 (TASK-009, nullable — 하위 호환성 유지)
    sentiment_label: str | None = None
    source: str
    url: str
    published_at: datetime


class NewsResponse(BaseModel):
    """뉴스 피드 응답"""

    news: list[NewsItem]
    total: int


# ---------------------------------------------------------------------------
# 섹터 트렌드 스키마 (TASK-024)
# ---------------------------------------------------------------------------


class SectorTrendItem(BaseModel):
    """섹터별 트렌드 집계 항목"""

    sector: str
    trade_date: date
    trend_score: float
    news_volume: int
    avg_sentiment: float


class SectorTrendsResponse(BaseModel):
    """섹터 트렌드 응답"""

    trends: list[SectorTrendItem]
    days: int = 7


# ---------------------------------------------------------------------------
# 섹터 랭킹 / 상세 스키마 (SPEC-STOCK-008 TASK-005, TASK-006)
# ---------------------------------------------------------------------------


class SectorRankingItem(BaseModel):
    """섹터 랭킹 개별 항목"""

    sector: str
    trade_date: date
    news_volume: int
    avg_sentiment: float
    trend_score: float


class SectorRankingResponse(BaseModel):
    """섹터 랭킹 응답"""

    sort: str
    limit: int
    sectors: list[SectorRankingItem]
    total: int


class SectorStockItem(BaseModel):
    """섹터 구성 종목 항목"""

    krx_code: str
    mention_count: int


class SectorDetailResponse(BaseModel):
    """섹터 상세 응답 (트렌드 시계열 + 구성 종목)"""

    sector: str
    days: int
    trends: list[SectorTrendItem]
    stocks: list[SectorStockItem]
    total_stocks: int


# ---------------------------------------------------------------------------
# 추천 근거 상세 스키마 (TASK-025)
# ---------------------------------------------------------------------------


class ContributingNewsItem(BaseModel):
    """추천 근거에 기여한 뉴스 항목"""

    title: str
    summary: str | None = None
    sentiment: str
    published_at: datetime


class RecommendationDetailResponse(BaseModel):
    """종목 추천 근거 상세 응답 (REQ-WEB-002, AC-8)"""

    krx_code: str
    trade_date: date
    total_score: float
    sentiment_score: float
    volume_score: float
    momentum_score: float
    anomaly_score: float
    reasoning: str
    # Claude Haiku가 생성한 한국어 추천 근거 (TASK-004, nullable — 하위 호환성 유지)
    explanation: str | None = None
    contributing_news: list[ContributingNewsItem]
    disclaimer: str = DISCLAIMER


# ---------------------------------------------------------------------------
# 추천 히스토리 스키마 (TASK-005+006)
# ---------------------------------------------------------------------------


class DailyRecommendations(BaseModel):
    """날짜별 추천 그룹"""

    date: str  # YYYY-MM-DD
    recommendations: list[RecommendationItem]


class RecommendationHistoryResponse(BaseModel):
    """추천 히스토리 응답 (days일간 날짜별 그룹)"""

    days: int
    groups: list[DailyRecommendations]


# ---------------------------------------------------------------------------
# 종목 검색 스키마 (SPEC-STOCK-007 TASK-003)
# ---------------------------------------------------------------------------


class StockSearchItem(BaseModel):
    """검색 결과 개별 종목 항목"""

    krx_code: str
    name: str
    in_recommendations: bool = False


class StockSearchResponse(BaseModel):
    """종목 검색 응답"""

    query: str
    results: list[StockSearchItem]
    total: int


# ---------------------------------------------------------------------------
# 주가 히스토리 스키마 (SPEC-STOCK-007 TASK-005)
# ---------------------------------------------------------------------------


class PricePoint(BaseModel):
    """단일 날짜 종가 데이터 포인트"""

    date: str  # YYYY-MM-DD
    close: float


class StockPricesResponse(BaseModel):
    """주가 히스토리 응답"""

    krx_code: str
    days: int
    prices: list[PricePoint]
    # FinanceDataReader 조회 실패 시 False
    available: bool


# ---------------------------------------------------------------------------
# 피드백 스키마 (SPEC-STOCK-007 TASK-007)
# ---------------------------------------------------------------------------


class FeedbackVoteRequest(BaseModel):
    """피드백 투표 요청 — vote는 'up' 또는 'down'"""

    vote: str  # "up" or "down"


class FeedbackSummaryResponse(BaseModel):
    """피드백 집계 응답"""

    krx_code: str
    up: int
    down: int
