# 텔레그램 봇 커맨드 핸들러 — /start, /stop, /status, /recommend, /help
import logging

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start 커맨드 핸들러 — 구독 등록 안내"""
    if update.message is None:
        return

    chat_id = update.effective_chat.id if update.effective_chat else None
    await update.message.reply_text(
        "안녕하세요! 한국 주식 추천 봇입니다.\n\n"
        f"채팅 ID: {chat_id}\n\n"
        "구독을 활성화하려면 웹 서비스에서 이 채팅 ID를 등록해 주세요.\n\n"
        "사용 가능한 명령어:\n"
        "/help - 도움말\n"
        "/status - 구독 상태 확인\n"
        "/stop - 알림 중단\n"
        "/recommend - 즉시 추천 조회"
    )
    logger.info("start 커맨드 수신 — chat_id=%s", chat_id)


async def stop_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/stop 커맨드 핸들러 — 구독 비활성화 안내"""
    if update.message is None:
        return

    chat_id = update.effective_chat.id if update.effective_chat else None
    # DB 업데이트는 notifier 레이어에서 처리 — 여기서는 안내만
    await update.message.reply_text(
        "알림을 중단하려면 웹 서비스에서 구독을 해제해 주세요.\n"
        f"채팅 ID: {chat_id}"
    )
    logger.info("stop 커맨드 수신 — chat_id=%s", chat_id)


async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/status 커맨드 핸들러 — 현재 구독 상태 안내"""
    if update.message is None:
        return

    chat_id = update.effective_chat.id if update.effective_chat else None
    await update.message.reply_text(
        f"채팅 ID: {chat_id}\n\n"
        "웹 서비스에서 구독 상태를 확인해 주세요."
    )
    logger.info("status 커맨드 수신 — chat_id=%s", chat_id)


async def recommend_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/recommend 커맨드 핸들러 — 즉시 추천 조회 안내"""
    if update.message is None:
        return

    await update.message.reply_text(
        "최신 추천 종목은 웹 서비스에서 확인하거나,\n"
        "정기 알림이 설정되어 있으면 오늘의 추천을 받으실 수 있습니다."
    )
    logger.info("recommend 커맨드 수신 — chat_id=%s", update.effective_chat.id if update.effective_chat else None)


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/help 커맨드 핸들러 — 사용법 안내"""
    if update.message is None:
        return

    await update.message.reply_text(
        "한국 주식 추천 봇 사용법\n\n"
        "/start - 봇 시작 및 채팅 ID 확인\n"
        "/status - 구독 상태 확인\n"
        "/stop - 알림 중단 안내\n"
        "/recommend - 추천 조회 안내\n"
        "/help - 이 도움말 표시"
    )
