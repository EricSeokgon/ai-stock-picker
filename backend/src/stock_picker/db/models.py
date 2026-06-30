# ORM 모델 정의 - SQLAlchemy 2.0 선언적 스타일
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    Float,
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
    # 감성 5단계 라벨: 매우긍정/긍정/중립/부정/매우부정 (TASK-008, 마이그레이션 0009)
    sentiment_label: Mapped[str | None] = mapped_column(String(20), nullable=True)
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
    # Claude Haiku가 생성한 한국어 추천 근거 텍스트 (TASK-002, 마이그레이션 0009)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 피드백 조정 전 기본 점수 (SPEC-STOCK-009 TASK-001, 마이그레이션 0012)
    base_score: Mapped[float | None] = mapped_column(Numeric(6, 3), nullable=True)
    # 피드백 조정량 (adjusted - base), 조정 없으면 None (SPEC-STOCK-009 TASK-001)
    feedback_score: Mapped[float | None] = mapped_column(Numeric(6, 3), nullable=True)
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
    """포트폴리오 보유 종목 테이블 (SPEC-STOCK-028: 해외 자산 지원)

    # @MX:ANCHOR: [AUTO] 보유 종목 핵심 엔티티 — 해외 자산(NYSE/NASDAQ) 포함
    # @MX:REASON: service.py, router.py, dividends.py, risk_analysis.py 등 4개 이상 모듈에서 참조
    # @MX:SPEC: SPEC-STOCK-028 REQ-FA-001
    """

    __tablename__ = "portfolio_holdings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    portfolio_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    # krx_code: KRX 종목코드 또는 해외 티커 식별자 (컬럼명 유지 — 하위 호환)
    krx_code: Mapped[str] = mapped_column(String(10), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_buy_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    # market: 상장 거래소 — KRX(기본), NYSE, NASDAQ
    market: Mapped[str] = mapped_column(String(10), nullable=False, server_default="KRX")
    # currency: 결제 통화 — KRW(기본), USD
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="KRW")
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # 연관 관계
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="holdings")

    __table_args__ = (
        # (portfolio_id, krx_code, market) 복합 UNIQUE — 동일 시장 내 종목 중복 방지
        UniqueConstraint(
            "portfolio_id", "krx_code", "market",
            name="uq_holding_portfolio_ticker_market",
        ),
    )


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


# ── Phase F: 알림 시스템 ───────────────────────────────────────────────────────

class WatchlistAlert(Base):
    """관심종목 가격 알림 테이블 — 목표가 도달 시 알림 발송"""

    # @MX:ANCHOR: [AUTO] 가격 알림 핵심 엔티티 — 알림 서비스/스케줄러에서 참조
    # @MX:REASON: alert_service.py, jobs.py(check_price_alerts), alert_router.py 등 3개 이상에서 사용

    __tablename__ = "watchlist_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    krx_code: Mapped[str] = mapped_column(String(10), nullable=False)
    # 목표가: 알림 발동 기준 가격
    target_price: Mapped[float] = mapped_column(Float, nullable=False)
    # direction: "above" (이상) 또는 "below" (이하)
    direction: Mapped[str] = mapped_column(String(5), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    # triggered_at: 알림 발동 시각 (발동 전 NULL)
    triggered_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class EmailSubscription(Base):
    """이메일 구독 테이블 — 주간 요약 및 가격 알림 메일 수신"""

    __tablename__ = "email_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # 사용자당 이메일 구독 1개 제한
    __table_args__ = (UniqueConstraint("user_id", name="uq_email_sub_user"),)


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
    # 상태: pending → running → done / failed
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # 파라미터: 유니버스 크기, 상위 종목 수 (NULL이면 기본값 사용)
    universe_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    top_n: Mapped[int | None] = mapped_column(Integer, nullable=True)

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


# ── Phase G: 추천 피드백 ────────────────────────────────────────────────────────

class RecommendationFeedback(Base):
    """추천 종목 사용자 피드백 테이블 — 좋아요/싫어요 투표"""

    # @MX:ANCHOR: [AUTO] 피드백 서비스 핵심 엔티티
    # @MX:REASON: feedback/service.py, recommendations 라우터, 피드백 집계 등 3개 이상에서 사용

    __tablename__ = "recommendation_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 투표 대상 종목코드 (KRX)
    krx_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    # 투표: "up" 또는 "down"
    vote: Mapped[str] = mapped_column(String(4), nullable=False)
    # 비로그인 사용자도 투표 가능 (nullable)
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ── Phase H: 알림·모니터링 시스템 (SPEC-STOCK-013) ─────────────────────────────

class Notification(Base):
    """인앱 알림 인박스 — 가격 알림·추천 변동을 사용자별로 수신"""

    # @MX:ANCHOR: [AUTO] 알림 인박스 핵심 엔티티
    # @MX:REASON: inbox_router, _trigger_alert (scheduler), rec_change 등 3개 이상 모듈에서 생성·조회
    # @MX:SPEC: SPEC-STOCK-013 REQ-NOTI-001

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # 알림 타입: price_alert | rec_new | rec_dropped
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    krx_code: Mapped[str] = mapped_column(String(10), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # 기준일 (rec 변동 → trade_date, price_alert → triggered_at.date)
    ref_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    related_alert_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("watchlist_alerts.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    read_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMPTZ(timezone=True), nullable=True
    )

    __table_args__ = (
        # 중복 알림 방지: 동일 사용자·타입·종목·기준일 알림 1회만 허용
        UniqueConstraint(
            "user_id", "type", "krx_code", "ref_date",
            name="uq_notification_user_type_code_date",
        ),
        # 미읽음 우선 목록 조회 최적화
        Index("ix_notifications_user_read_created", "user_id", "is_read", "created_at"),
    )

    # 연관 관계
    user: Mapped["User"] = relationship("User", lazy="noload")
    related_alert: Mapped["WatchlistAlert | None"] = relationship(
        "WatchlistAlert", lazy="noload"
    )


# ── Phase I: AI 투자 조언 (SPEC-STOCK-014) ────────────────────────────────────

class AIAdvice(Base):
    """AI 투자 조언 영속화 테이블 — 리밸런싱·리스크·시장브리핑 조언과 피드백"""

    # @MX:ANCHOR: [AUTO] AI 조언 서비스 핵심 엔티티
    # @MX:REASON: advice/router.py, 조언 생성 서비스, 피드백 집계 등 3개 이상 모듈에서 사용
    # @MX:SPEC: SPEC-STOCK-014 REQ-AIV-001

    __tablename__ = "ai_advice"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # 조언 타입: rebalance | risk_profile | market_briefing
    advice_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # 기준일 — 동일 날짜 중복 요청 방지 및 이력 정렬용
    ref_date: Mapped[date] = mapped_column(Date, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    # 조언 본문 (서술형 한국어)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 구조화 데이터 (JSON 직렬화 — 리밸런싱 액션 목록 등)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 리스크 점수 0~100 (risk_profile 타입만 사용)
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 피드백: helpful | not_helpful | None(미평가)
    feedback: Mapped[str | None] = mapped_column(String(20), nullable=True)
    feedback_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMPTZ(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        # 동일 사용자·타입·기준일 조언 1회만 생성 (멱등성 보장)
        UniqueConstraint(
            "user_id", "advice_type", "ref_date",
            name="uq_ai_advice_user_type_date",
        ),
        # 사용자별 타입별 최신 이력 조회 최적화
        Index("ix_ai_advice_user_type", "user_id", "advice_type", "created_at"),
    )

    # 연관 관계
    user: Mapped["User"] = relationship("User", lazy="noload")


# ── Phase J: 종목 스크리너 (SPEC-STOCK-018) ───────────────────────────────────


class StockFundamental(Base):
    """종목별 재무지표 스냅샷 테이블 — 일일 수집 잡이 upsert (SPEC-STOCK-018)

    # @MX:ANCHOR: [AUTO] 스크리너 서비스 핵심 데이터 엔티티
    # @MX:REASON: screener/service.py(필터 쿼리), screener/router.py, 일일 수집 잡 등 3곳 이상 참조
    # @MX:SPEC: SPEC-STOCK-018 REQ-SCR-DATA-001
    """

    __tablename__ = "stock_fundamentals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    krx_code: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    current_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    change_pct: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    per: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    pbr: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    roe: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    market_cap: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    dividend_yield: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    week52_high: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    week52_low: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    # 현재가의 52주 레인지 내 위치 (%) — (current - low) / (high - low) * 100
    price_vs_52w_pct: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("krx_code", "snapshot_date", name="uq_fundamentals_code_date"),
        Index("ix_fundamentals_snapshot_date", "snapshot_date"),
    )


class ScreenerPreset(Base):
    """스크리너 프리셋 — 사용자별 필터 조합 저장 (SPEC-STOCK-018)

    사용자당 최대 5개. criteria는 JSON 직렬화 문자열.
    """

    __tablename__ = "screener_presets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # 필터 조건 JSON 직렬화 문자열 (ScreenerCriteria)
    criteria: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        # 동일 사용자·이름 중복 방지 (REQ-SCR-PRESET-006)
        UniqueConstraint("user_id", "name", name="uq_screener_preset_user_name"),
    )


# ── Phase J: 일반 알림 설정 (SPEC-STOCK-020) ─────────────────────────────────


class Alert(Base):
    """사용자 정의 알림 설정 — 목표가·급등락 조건 기반 알림 (SPEC-STOCK-020).

    # @MX:ANCHOR: [AUTO] 알림 설정 핵심 엔티티 — 라우터·서비스·스케줄러에서 참조
    # @MX:REASON: general_alert_router, general_alert_service, scheduler/jobs 3개 이상에서 사용
    # @MX:SPEC: SPEC-STOCK-020 REQ-ALERT-001
    """

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    krx_code: Mapped[str] = mapped_column(String(10), nullable=False)
    stock_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # target_price | surge_drop | ex_dividend
    alert_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # 목표가(원) 또는 급등락 임계값(%)
    condition_value: Mapped[float] = mapped_column(Float, nullable=False)
    # above | below | either (surge_drop 기본값 either)
    condition_direction: Mapped[str | None] = mapped_column(String(8), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_triggered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    triggered_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMPTZ(timezone=True), nullable=True
    )
    triggered_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_alerts_user_active", "user_id", "is_active"),
    )

    user: Mapped["User"] = relationship("User", lazy="noload")


# ── Phase J-2: 포트폴리오 알림 (SPEC-STOCK-031) ───────────────────────────────


class PortfolioAlert(Base):
    """포트폴리오 목표 수익률·MDD 임계값 알림 설정 (SPEC-STOCK-031).

    # @MX:ANCHOR: [AUTO] 포트폴리오 알림 핵심 엔티티 — router, portfolio_alerts 서비스, 스케줄러에서 참조
    # @MX:REASON: portfolio/router.py CRUD 엔드포인트, portfolio_alerts.py 오케스트레이션, scheduler/jobs.py 3곳 이상
    # @MX:SPEC: SPEC-STOCK-031 REQ-PAL-001
    """

    __tablename__ = "portfolio_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    portfolio_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    # 알림 유형: portfolio_target_return | portfolio_mdd_breach | portfolio_value_below | holding_return
    alert_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # 목표 수익률(%) 또는 MDD 임계값(%) 또는 평가액(KRW) — 음수 가능 (-15.0 등)
    condition_value: Mapped[float] = mapped_column(Float, nullable=False)
    # @MX:NOTE: [AUTO] target_krx_code: 종목 알림 대상 종목코드, NULL=비종목형 알림 (SPEC-036)
    target_krx_code: Mapped[str | None] = mapped_column(String, nullable=True)
    # @MX:NOTE: [AUTO] condition_direction: 방향 조건 "above"/"below", NULL=above 기본값 (SPEC-036)
    condition_direction: Mapped[str | None] = mapped_column(String(5), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_triggered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    triggered_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMPTZ(timezone=True), nullable=True
    )
    triggered_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        # 동일 (user_id, portfolio_id, alert_type) 중복 방지 (REQ-PAL-008)
        UniqueConstraint(
            "user_id", "portfolio_id", "alert_type",
            name="uq_portfolio_alert_user_pf_type",
        ),
        # 활성 알림 조회 최적화
        Index("ix_portfolio_alerts_user_active", "user_id", "is_active"),
    )

    user: Mapped["User"] = relationship("User", lazy="noload")


# ── Phase K: 알림 채널·유형별 수신 설정 (SPEC-STOCK-025) ──────────────────────


class NotificationPreference(Base):
    """사용자별 알림 유형·채널 ON/OFF 설정 테이블 (SPEC-STOCK-025).

    # @MX:ANCHOR: [AUTO] 알림 채널 게이팅 핵심 엔티티 — preferences 서비스·라우터에서 참조
    # @MX:REASON: preferences.py(is_channel_enabled), preferences_router.py, general_alert_service.py 3곳 이상
    # @MX:SPEC: SPEC-STOCK-025 REQ-PREF-001, REQ-PREF-002

    하위 호환(opt-out) 모델:
    - 설정 행이 없으면 email_enabled=True, telegram_enabled=True로 간주
    - (user_id, alert_type) 단위 UNIQUE 제약으로 유형당 1행 유지
    """

    __tablename__ = "notification_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # 지원 유형: target_price|surge_drop|volume_spike|ex_dividend|rec_new|rec_dropped|rec_score_change
    alert_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # 이메일 채널 활성 여부 (기본값 True)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # 텔레그램 채널 활성 여부 (기본값 True)
    telegram_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ(timezone=True),
        server_default=func.now(),
        nullable=False,
        onupdate=func.now(),
    )

    __table_args__ = (
        # (user_id, alert_type) 조합 UNIQUE — 유형당 1행 유지
        UniqueConstraint("user_id", "alert_type", name="uq_pref_user_type"),
    )

    user: Mapped["User"] = relationship("User", lazy="noload")


# ── Phase L: 리밸런싱 계획 저장 (SPEC-STOCK-032) ─────────────────────────────


class RebalancingPlan(Base):
    """포트폴리오 리밸런싱 계획서 저장 테이블 (SPEC-STOCK-032 RBA-005).

    dry_run=False 요청 시 생성된 주문 계획을 영구 보관한다.
    orders_json: RebalancingOrder 리스트를 JSON 직렬화한 Text (SQLite 호환)
    """

    __tablename__ = "rebalancing_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    portfolio_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    budget: Mapped[float] = mapped_column(Float, nullable=False)
    total_buy_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_sell_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_commission: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # RebalancingOrder 목록 JSON 직렬화 (SQLite JSONB 미지원으로 Text 사용)
    orders_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    portfolio: Mapped["Portfolio"] = relationship("Portfolio", lazy="noload")
    user: Mapped["User"] = relationship("User", lazy="noload")


# ── Phase L-2: 포트폴리오 월별 스냅샷 (SPEC-STOCK-035) ──────────────────────────


class PortfolioMonthlySnapshot(Base):
    """포트폴리오 월별 평가액·수익률 스냅샷 (SPEC-STOCK-035 REQ-RPT-004).

    월말 또는 사용자 요청 시점에 기록되는 포트폴리오 집계 데이터.
    (portfolio_id, month) 조합이 UNIQUE — 동일 월 upsert는 SELECT-then-write로 처리.
    """

    __tablename__ = "portfolio_monthly_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    portfolio_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 월 키: "YYYY-MM" 7자 문자열 (예: "2026-05")
    month: Mapped[str] = mapped_column(String(7), nullable=False)
    # 포트폴리오 총 평가액 (KRW)
    total_value_krw: Mapped[float] = mapped_column(Float, nullable=False)
    # 기간 수익률 (%) — 기간 비교 불가 시 NULL
    total_return_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 보유 종목 수 (스냅샷 시점)
    holding_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # (portfolio_id, month) 복합 UNIQUE — SELECT-then-write upsert 보장
    __table_args__ = (
        UniqueConstraint("portfolio_id", "month", name="uq_snapshot_portfolio_month"),
    )

    portfolio: Mapped["Portfolio"] = relationship("Portfolio", lazy="noload")


# ── Phase M: AI 개인화 추천 (SPEC-STOCK-037) ────────────────────────────────────


class UserRecommendationPreference(Base):
    """사용자별 종목 선호(좋아요/싫어요) 테이블 (SPEC-STOCK-037 REQ-AIEX-PREF).

    SELECT-then-write(NFR-005)로 upsert — ON CONFLICT 미사용.
    UNIQUE(user_id, portfolio_id, krx_code): 포트폴리오·종목당 선호 1개.
    """

    __tablename__ = "recommendation_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    portfolio_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    # 종목 코드 (KRX 또는 해외 티커)
    krx_code: Mapped[str] = mapped_column(String(10), nullable=False)
    # 섹터 — 선호 적용 시 유사 섹터 판단에 사용 (nullable)
    sector: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # 선호 값: "liked" 또는 "disliked"
    preference: Mapped[str] = mapped_column(String(8), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ(timezone=True),
        server_default=func.now(),
        nullable=False,
        onupdate=func.now(),
    )

    __table_args__ = (
        # (user_id, portfolio_id, krx_code) 복합 UNIQUE — 중복 선호 방지
        UniqueConstraint(
            "user_id", "portfolio_id", "krx_code",
            name="uq_rec_preference_user_pf_code",
        ),
    )

    user: Mapped["User"] = relationship("User", lazy="noload")
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", lazy="noload")


class RecommendationHistory(Base):
    """개인화 추천 히스토리 스냅샷 테이블 (SPEC-STOCK-037 REQ-AIEX-HIST).

    개인화 추천 산출 시 결과를 JSON으로 영속화. 사용자별 과거 추천 조회에 사용.
    """

    __tablename__ = "recommendation_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    portfolio_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    # 추천 항목 목록 JSON 직렬화 (SQLite 호환 Text)
    recommendations: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        # (user_id, portfolio_id, created_at) 최신순 조회 최적화
        Index("ix_rec_history_user_pf_created", "user_id", "portfolio_id", "created_at"),
    )

    user: Mapped["User"] = relationship("User", lazy="noload")
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", lazy="noload")


# ── SPEC-STOCK-041: 포트폴리오 목표 관리 ────────────────────────────────────────

class PortfolioShare(Base):
    """포트폴리오 공유 링크 테이블 (SPEC-STOCK-042).

    # @MX:ANCHOR: [AUTO] 포트폴리오 공유 핵심 엔티티
    # @MX:REASON: sharing.py 서비스, portfolio router, 공개 피드 엔드포인트에서 참조
    # @MX:SPEC: SPEC-STOCK-042 REQ-SHARE-001~005

    share_token: secrets.token_urlsafe(16) 생성 (22자, VARCHAR(32)).
    is_public=False는 소프트 삭제 (token/counts 보존).
    포트폴리오당 공유 레코드 1개 (portfolio_id UNIQUE).
    view_count: 원자적 UPDATE SET view_count = view_count + 1.
    """

    __tablename__ = "portfolio_shares"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    portfolio_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    # share_token: 고유 공유 토큰 (22자, VARCHAR(32))
    share_token: Mapped[str] = mapped_column(String(32), nullable=False)
    # share_url: 상대 경로 공유 URL (/shared/{token})
    share_url: Mapped[str] = mapped_column(String(128), nullable=False)
    # is_public: 공개 여부 (소프트 삭제 시 False, token/counts 보존)
    is_public: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    # view_count: 조회수 (원자적 증가)
    view_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # 연관 관계
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", lazy="noload")
    likes: Mapped[list["PortfolioLike"]] = relationship(
        "PortfolioLike", back_populates="share", lazy="noload", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_portfolio_shares_portfolio_id", "portfolio_id"),
        Index("ix_portfolio_shares_is_public", "is_public"),
        UniqueConstraint("share_token", name="uq_portfolio_shares_token"),
        UniqueConstraint("portfolio_id", name="uq_portfolio_shares_portfolio_id"),
    )


class PortfolioLike(Base):
    """포트폴리오 좋아요 테이블 (SPEC-STOCK-042).

    (share_id, user_id) 복합 유니크 — 중복 좋아요 DB 레벨 방지.
    소유자 좋아요 금지는 앱 레벨에서 강제 (403).
    like_count는 COUNT(*) 쿼리로 파생 (비정규화 카운터 없음).
    """

    __tablename__ = "portfolio_likes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    share_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("portfolio_shares.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # 연관 관계
    share: Mapped["PortfolioShare"] = relationship("PortfolioShare", back_populates="likes", lazy="noload")

    __table_args__ = (
        Index("ix_portfolio_likes_share_id", "share_id"),
        Index("ix_portfolio_likes_user_id", "user_id"),
        UniqueConstraint("share_id", "user_id", name="uq_portfolio_likes_share_user"),
    )


class ShareViewStat(Base):
    """포트폴리오 공유 일별 조회수 통계 테이블 (SPEC-STOCK-043).

    # @MX:NOTE: [AUTO] 날짜별 조회수 집계 — portfolio_shares.view_count(누적)와 별개 테이블
    # @MX:SPEC: SPEC-STOCK-043 REQ-STAT-001

    upsert 패턴: INSERT ... ON CONFLICT (share_id, stat_date) DO UPDATE SET view_count = view_count + 1
    stat_date: KST(Asia/Seoul) 기준 날짜
    """

    __tablename__ = "share_view_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    share_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("portfolio_shares.id", ondelete="CASCADE"), nullable=False
    )
    stat_date: Mapped[date] = mapped_column(Date, nullable=False)
    view_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )

    __table_args__ = (
        UniqueConstraint("share_id", "stat_date", name="uq_share_view_stats_share_date"),
        Index("ix_share_view_stats_share_id_date", "share_id", "stat_date"),
    )


class PortfolioGoal(Base):
    """포트폴리오 투자 목표 테이블 (SPEC-STOCK-041).

    # @MX:ANCHOR: [AUTO] 포트폴리오 목표 핵심 엔티티
    # @MX:REASON: goals.py 서비스, router.py 엔드포인트, scheduler/jobs.py 스케줄러에서 참조
    # @MX:SPEC: SPEC-STOCK-041 REQ-GOAL-001~007

    포트폴리오당 활성 목표 1개 제한 (is_active=True 기준).
    소프트 삭제: DELETE 시 is_active=False, 이력 보존.
    """

    __tablename__ = "portfolio_goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    portfolio_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    # target_amount: 목표 평가액 (KRW), target_return_rate: 목표 수익률(%)
    # 둘 중 하나 이상은 반드시 설정해야 함 (Pydantic 스키마에서 검증)
    target_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    target_return_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    # deadline: 목표 달성 기한 (설정 선택사항)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    # is_active: 활성 목표 여부 (소프트 삭제 시 False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    # goal_reached_notified: 목표 달성 알림 발송 여부 (멱등성 보장)
    goal_reached_notified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # 연관 관계
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", lazy="noload")

    __table_args__ = (
        Index("ix_portfolio_goals_portfolio_id", "portfolio_id"),
    )
