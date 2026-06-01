# ORM 모델 정의 - SQLAlchemy 2.0 선언적 스타일
from datetime import datetime
from sqlalchemy import (
    String,
    Text,
    Integer,
    DateTime,
    Numeric,
    ForeignKey,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from stock_picker.db.base import Base


class Article(Base):
    """뉴스 기사 수집 테이블"""

    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # URL은 중복 수집 방지를 위해 UNIQUE 제약조건 적용
    url: Mapped[str] = mapped_column(String(2048), unique=True, nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    # 처리 상태: collected → analyzed → done
    status: Mapped[str] = mapped_column(String(50), default="collected", nullable=False)

    # 연관 관계
    analysis_results: Mapped[list["AnalysisResult"]] = relationship(
        back_populates="article", cascade="all, delete-orphan"
    )
    stock_mentions: Mapped[list["StockMention"]] = relationship(
        back_populates="article", cascade="all, delete-orphan"
    )


class AnalysisResult(Base):
    """Claude API 분석 결과 저장 테이블"""

    __tablename__ = "analysis_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # articles 테이블 외래키
    article_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )
    sentiment: Mapped[str] = mapped_column(String(20), nullable=False)
    # 감성 점수: -1.0 ~ 1.0 범위 (정밀도 4, 소수점 3자리)
    sentiment_score: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    # 섹터 태그: PostgreSQL TEXT 배열
    sector_tags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    keywords: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # 연관 관계
    article: Mapped["Article"] = relationship(back_populates="analysis_results")


class StockMention(Base):
    """기사 내 종목 언급 테이블"""

    __tablename__ = "stock_mentions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )
    stock_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # KRX 종목코드: 매핑 실패 시 NULL 허용
    krx_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    mention_status: Mapped[str] = mapped_column(String(50), nullable=False)

    # 연관 관계
    article: Mapped["Article"] = relationship(back_populates="stock_mentions")


class SectorTrend(Base):
    """섹터별 일일 트렌드 집계 테이블"""

    __tablename__ = "sector_trends"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sector: Mapped[str] = mapped_column(String(100), nullable=False)
    trade_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # 해당 섹터 당일 뉴스 수
    news_volume: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 평균 감성 점수 (정밀도 4, 소수점 3자리)
    avg_sentiment: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False, default=0)
    # 트렌드 종합 점수 (정밀도 6, 소수점 3자리)
    trend_score: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False, default=0)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Recommendation(Base):
    """일일 종목/ETF 추천 결과 테이블"""

    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # 자산 유형: stock 또는 etf
    asset_type: Mapped[str] = mapped_column(String(20), nullable=False)
    krx_code: Mapped[str] = mapped_column(String(10), nullable=False)
    # 순위 (1 = 최고 추천)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    # 종합 점수 (정밀도 6, 소수점 3자리)
    total_score: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False)
    sentiment_score: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False, default=0)
    volume_score: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False, default=0)
    momentum_score: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False, default=0)
    anomaly_score: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False, default=0)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # 복합 인덱스: 날짜별, 자산유형별 순위 조회 최적화
    __table_args__ = (
        Index("ix_recommendations_date_type_rank", "trade_date", "asset_type", "rank"),
    )
