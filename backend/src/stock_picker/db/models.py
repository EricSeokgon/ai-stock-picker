# ORM 모델 정의 - SQLAlchemy 2.0 선언적 스타일
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    String,
    Text,
    Integer,
    DateTime,
    Numeric,
    ForeignKey,
    Index,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, TIMESTAMP as TIMESTAMPTZ
from sqlalchemy.orm import Mapped, mapped_column, relationship

from stock_picker.db.base import Base


class User(Base):
    """사용자 계정 모델 (JWT 인증 기반)"""

    # @MX:ANCHOR: [AUTO] 인증 시스템 핵심 엔티티 — auth 라우터/의존성/토큰 서비스에서 참조
    # @MX:REASON: JWT 인증, 포트폴리오 연결(Phase C), 텔레그램 구독 등 3개 이상 모듈에서 사용

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    # is_active: 계정 비활성화 시 로그인 차단
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Phase C 포트폴리오 관계
    portfolios: Mapped[list["Portfolio"]] = relationship(
        "Portfolio", back_populates="user", lazy="noload"
    )
    # Phase B 텔레그램 구독 관계
    telegram_subscriptions: Mapped[list["TelegramSubscription"]] = relationship(
        "TelegramSubscription", back_populates="user", lazy="noload"
    )
    # Phase D 백테스트 관계
    backtest_runs: Mapped[list["BacktestRun"]] = relationship(
        "BacktestRun", back_populates="user", lazy="noload"
    )


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


# ── Phase B: 텔레그램 구독 ──────────────────────────────────────────────────────

class TelegramSubscription(Base):
    """텔레그램 구독 테이블 — 사용자와 텔레그램 채팅 연결"""

    __tablename__ = "telegram_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # 텔레그램 chat_id: BigInteger (SQLite 테스트에서는 Integer로 처리됨)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    subscribed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # 연관 관계
    user: Mapped["User"] = relationship("User", back_populates="telegram_subscriptions")


# ── Phase C: 포트폴리오 ────────────────────────────────────────────────────────

class Portfolio(Base):
    """포트폴리오 테이블 — 사용자별 보유 종목 그룹"""

    # @MX:ANCHOR: [AUTO] 포트폴리오 서비스 핵심 엔티티
    # @MX:REASON: portfolio/service.py, portfolio/router.py, 성과 계산 등 3개 이상 모듈에서 사용

    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # 연관 관계
    user: Mapped["User"] = relationship("User", back_populates="portfolios")
    holdings: Mapped[list["PortfolioHolding"]] = relationship(
        "PortfolioHolding", back_populates="portfolio", cascade="all, delete-orphan"
    )


class PortfolioHolding(Base):
    """포트폴리오 보유 종목 테이블"""

    __tablename__ = "portfolio_holdings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    portfolio_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    krx_code: Mapped[str] = mapped_column(String(10), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_buy_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # 연관 관계
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="holdings")


# ── Phase E: 관심종목 위시리스트 ───────────────────────────────────────────────

class WatchlistItem(Base):
    """관심종목 위시리스트 테이블 — 사용자별 즐겨찾기 종목"""

    __tablename__ = "watchlist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    krx_code: Mapped[str] = mapped_column(String(10), nullable=False)
    # added_at: 추가 시각 (서버 기본값)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # 동일 사용자가 같은 종목을 중복 추가 방지
    __table_args__ = (UniqueConstraint("user_id", "krx_code", name="uq_watchlist_user_krx"),)


# ── Phase D: 백테스팅 ──────────────────────────────────────────────────────────

class BacktestRun(Base):
    """백테스트 실행 테이블 — 비동기 작업 상태 추적"""

    # @MX:ANCHOR: [AUTO] 백테스트 엔진 핵심 엔티티
    # @MX:REASON: backtest/runner.py, backtest/router.py, 결과 저장 등 3개 이상 모듈에서 사용

    __tablename__ = "backtest_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # 전략: momentum, volume
    strategy: Mapped[str] = mapped_column(String(50), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    # 상태: pending → running → done / error
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # 연관 관계
    user: Mapped["User"] = relationship("User", back_populates="backtest_runs")
    daily_results: Mapped[list["BacktestDailyResult"]] = relationship(
        "BacktestDailyResult", back_populates="run", cascade="all, delete-orphan"
    )


class BacktestDailyResult(Base):
    """백테스트 일별 거래 결과 테이블"""

    __tablename__ = "backtest_daily_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("backtest_runs.id", ondelete="CASCADE"), nullable=False
    )
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    krx_code: Mapped[str] = mapped_column(String(10), nullable=False)
    # 시그널: buy, sell, hold
    signal: Mapped[str] = mapped_column(String(10), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    # 수익률: NULL 허용 (첫 거래일 등)
    return_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)

    # 연관 관계
    run: Mapped["BacktestRun"] = relationship("BacktestRun", back_populates="daily_results")
