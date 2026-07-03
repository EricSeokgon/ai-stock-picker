# 텔레그램 봇 초기화 및 백그라운드 실행 — FastAPI 이벤트 루프와 분리된 별도 스레드로 운영
import asyncio
import logging
import threading
from typing import TYPE_CHECKING

from telegram.ext import Application, CommandHandler

from stock_picker.telegram.handlers import (
    help_handler,
    recommend_handler,
    start_handler,
    status_handler,
    stop_handler,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def create_bot(token: str) -> Application:
    """python-telegram-bot Application 인스턴스 생성.

    # @MX:ANCHOR: [AUTO] 텔레그램 봇 진입점
    # @MX:REASON: main.py, notifier.py, 테스트에서 참조 — 3개 이상 호출부
    """
    app = Application.builder().token(token).build()

    # 커맨드 핸들러 등록
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("stop", stop_handler))
    app.add_handler(CommandHandler("status", status_handler))
    app.add_handler(CommandHandler("recommend", recommend_handler))
    app.add_handler(CommandHandler("help", help_handler))

    return app


def run_bot_in_background(telegram_app: Application) -> threading.Thread:
    """텔레그램 봇을 별도 스레드에서 폴링 모드로 실행.

    # @MX:WARN: [AUTO] 별도 스레드에서 새 이벤트 루프 생성 — asyncio 루프 충돌 주의
    # @MX:REASON: FastAPI가 메인 이벤트 루프를 점유하므로 봇은 독립 루프가 필요

    Args:
        telegram_app: create_bot()으로 생성된 Application 인스턴스

    Returns:
        실행 중인 데몬 스레드 (FastAPI 종료 시 자동 종료됨)
    """
    def _run() -> None:
        # 별도 스레드에서 새 이벤트 루프 생성
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # run_polling은 내부적으로 loop.run_until_complete를 사용
            telegram_app.run_polling(
                allowed_updates=["message"],
                drop_pending_updates=True,
            )
        except Exception:
            logger.exception("텔레그램 봇 폴링 중 오류 발생")
        finally:
            loop.close()

    thread = threading.Thread(target=_run, daemon=True, name="telegram-bot")
    thread.start()
    logger.info("텔레그램 봇 백그라운드 스레드 시작")
    return thread
