# FastAPI 앱 진입점
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from stock_picker.api.routes import news, recommendations, sectors, stocks
from stock_picker.api.routes.health import router as health_router
from stock_picker.auth.router import router as auth_router
from stock_picker.backtest.router import router as backtest_router
from stock_picker.notifications.alert_router import router as alert_router
from stock_picker.notifications.email_router import router as email_router
from stock_picker.advice.router import router as advice_router
from stock_picker.notifications.inbox_router import router as inbox_router
from stock_picker.notifications.general_alert_router import router as general_alert_router
from stock_picker.notifications.preferences_router import router as preferences_router
from stock_picker.screener.router import router as screener_router
from stock_picker.portfolio.router import router as portfolio_router
from stock_picker.portfolio.public_router import shared_router, like_router
from stock_picker.realtime.ws_router import router as ws_router
from stock_picker.watchlist.router import router as watchlist_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """FastAPI lifespan — 브로드캐스트 루프 및 APScheduler를 시작/종료.

    # @MX:WARN: [AUTO] asyncio 백그라운드 태스크 — task.cancel() 로만 종료
    # @MX:REASON: CancelledError를 catch하지 않으면 종료 시 예외가 로그에 남음
    # @MX:NOTE: [AUTO] ENABLE_SCHEDULER=false 시 스케줄러 비활성화 (멀티워커/테스트 환경)
    # @MX:SPEC: SPEC-STOCK-022
    """
    from stock_picker.realtime.price_broadcast import price_broadcast_loop
    from stock_picker.realtime.ws_router import manager

    # DB 세션 팩토리 — 선택적 (DB 미설정 환경에서도 동작)
    db_session_factory = None
    try:
        from stock_picker.db.session import async_session_factory
        db_session_factory = async_session_factory
    except Exception:
        logger.debug("DB 세션 팩토리 미설정 — 가격 알림 평가 비활성화")

    task = asyncio.create_task(
        price_broadcast_loop(manager, db_session_factory),
        name="price_broadcast_loop",
    )
    logger.info("가격 브로드캐스트 백그라운드 루프 시작")

    # APScheduler — ENABLE_SCHEDULER=false/0/no 시 비활성화
    scheduler = None
    enable_scheduler = os.getenv("ENABLE_SCHEDULER", "true").lower() not in ("false", "0", "no")
    if enable_scheduler:
        try:
            from stock_picker.scheduler.jobs import setup_scheduler
            scheduler = setup_scheduler()
            scheduler.start()
            logger.info("APScheduler 시작 완료 — 등록 잡 수=%d", len(scheduler.get_jobs()))
        except Exception:
            logger.exception("APScheduler 시작 실패 — 서비스는 계속 실행됩니다")
            scheduler = None
    else:
        logger.info("ENABLE_SCHEDULER=%s — 스케줄러 비활성화", os.getenv("ENABLE_SCHEDULER"))

    try:
        yield
    finally:
        # APScheduler 종료
        if scheduler is not None:
            try:
                scheduler.shutdown()
                logger.info("APScheduler 종료 완료")
            except Exception:
                logger.exception("APScheduler 종료 중 오류 — 무시하고 계속")

        # 가격 브로드캐스트 루프 종료
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        logger.info("가격 브로드캐스트 백그라운드 루프 종료")


def create_app() -> FastAPI:
    """FastAPI 애플리케이션 팩토리.

    CORS는 React 개발 서버(5173)를 허용한다.
    TELEGRAM_BOT_TOKEN 환경변수 설정 시 텔레그램 봇을 백그라운드에서 시작한다.
    """
    app = FastAPI(
        title="한국 주식 추천 시스템",
        version="0.2.0",
        description="AI 기반 한국 주식 & ETF 추천 서비스",
        lifespan=_lifespan,
    )

    # CORS — CORS_ORIGINS 환경변수 (쉼표 구분), 기본값: 개발 서버
    cors_origins_raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
    cors_origins = [o.strip() for o in cors_origins_raw.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 라우터 등록
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(recommendations.router)
    app.include_router(news.router)
    app.include_router(sectors.router)
    app.include_router(stocks.router)
    app.include_router(portfolio_router)
    app.include_router(shared_router)
    app.include_router(like_router)
    app.include_router(backtest_router)
    app.include_router(ws_router, tags=["realtime"])
    app.include_router(watchlist_router, prefix="/watchlist", tags=["watchlist"])
    app.include_router(alert_router, tags=["notifications"])
    app.include_router(email_router, prefix="/notifications", tags=["notifications"])
    app.include_router(inbox_router, prefix="/notifications", tags=["notifications"])
    app.include_router(advice_router)
    app.include_router(screener_router)
    app.include_router(general_alert_router, prefix="/alerts", tags=["alerts"])
    app.include_router(preferences_router, prefix="/notifications", tags=["notification-preferences"])

    # 텔레그램 봇 선택적 시작 — TELEGRAM_BOT_TOKEN 환경변수 필요
    _start_telegram_bot_if_configured(app)

    return app


def _start_telegram_bot_if_configured(app: FastAPI) -> None:
    """TELEGRAM_BOT_TOKEN이 설정된 경우 봇을 백그라운드 스레드에서 시작.

    토큰이 없으면 조용히 건너뜀.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        logger.debug("TELEGRAM_BOT_TOKEN 미설정 — 텔레그램 봇 비활성화")
        return

    try:
        from stock_picker.telegram.bot import create_bot, run_bot_in_background
        telegram_app = create_bot(token)
        thread = run_bot_in_background(telegram_app)
        logger.info("텔레그램 봇 시작 완료 (thread=%s)", thread.name)
    except Exception:
        logger.exception("텔레그램 봇 시작 실패 — 서비스는 계속 실행됩니다")


# 직접 실행 또는 uvicorn 진입점용 전역 앱 인스턴스
app = create_app()
