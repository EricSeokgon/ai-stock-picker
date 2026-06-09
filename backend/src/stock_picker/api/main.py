# FastAPI 앱 진입점
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from stock_picker.api.routes import news, recommendations, sectors
from stock_picker.auth.router import router as auth_router
from stock_picker.backtest.router import router as backtest_router
from stock_picker.portfolio.router import router as portfolio_router

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """FastAPI 애플리케이션 팩토리.

    CORS는 React 개발 서버(5173)를 허용한다.
    TELEGRAM_BOT_TOKEN 환경변수 설정 시 텔레그램 봇을 백그라운드에서 시작한다.
    """
    app = FastAPI(
        title="한국 주식 추천 시스템",
        version="0.2.0",
        description="AI 기반 한국 주식 & ETF 추천 서비스",
    )

    # CORS - React 프론트엔드 허용
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 라우터 등록
    app.include_router(auth_router)
    app.include_router(recommendations.router)
    app.include_router(news.router)
    app.include_router(sectors.router)
    app.include_router(portfolio_router)
    app.include_router(backtest_router)

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        """서비스 헬스 체크"""
        return {"status": "ok"}

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
