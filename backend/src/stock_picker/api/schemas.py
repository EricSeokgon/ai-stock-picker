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
    contributing_news: list[ContributingNewsItem]
    disclaimer: str = DISCLAIMER
