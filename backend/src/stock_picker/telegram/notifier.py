# 텔레그램 알림 발송 — 활성 구독자에게 추천 종목 전송
import logging
import os
from typing import Any

import requests
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def notify_subscribers_sync(db: Session, recommendations: list[dict[str, Any]]) -> None:
    """동기 버전 — 활성 구독자에게 추천 종목 알림 발송.

    # @MX:ANCHOR: [AUTO] 텔레그램 알림 발송 진입점
    # @MX:REASON: 스케줄러, API 엔드포인트, 수동 트리거 등에서 호출 예정

    Args:
        db: SQLAlchemy 동기 세션
        recommendations: 추천 종목 목록 (dict 형태)
    """
    from stock_picker.db.models import TelegramSubscription

    if not recommendations:
        logger.debug("전송할 추천 종목이 없습니다")
        return

    # 활성 구독자 조회
    subscriptions = (
        db.query(TelegramSubscription)
        .filter(TelegramSubscription.is_active == True)  # noqa: E712
        .all()
    )

    if not subscriptions:
        logger.debug("활성 구독자가 없습니다")
        return

    # 추천 메시지 생성
    message = _format_recommendations(recommendations)

    # 봇 인스턴스를 통해 발송
    try:
        for sub in subscriptions:
            _send_message_sync(sub.chat_id, message)
            logger.info("알림 발송 완료 — chat_id=%s", sub.chat_id)
    except Exception:
        logger.exception("텔레그램 알림 발송 실패")


def _format_recommendations(recommendations: list[dict[str, Any]]) -> str:
    """추천 종목 목록을 텔레그램 메시지 형식으로 변환"""
    lines = ["오늘의 추천 종목\n"]
    for i, rec in enumerate(recommendations[:5], 1):  # 상위 5개만
        krx_code = rec.get("krx_code", "N/A")
        score = rec.get("total_score", 0)
        lines.append(f"{i}. {krx_code} (점수: {score:.3f})")
    return "\n".join(lines)


def _send_message_sync(chat_id: int, message: str) -> bool:
    """동기 방식으로 텔레그램 메시지 발송 — Telegram Bot API HTTP 직접 호출.

    # @MX:ANCHOR: [AUTO] 텔레그램 단건 메시지 발송 — 일반 알림·추천 변동 경로에서 호출
    # @MX:REASON: general_alert_service._try_send_telegram, rec_change 채널 발송에서 호출

    TELEGRAM_BOT_TOKEN 미설정 시 False 반환 (발송 skip).
    HTTP 오류 발생 시 로깅 후 False 반환 (예외 미전파).

    Args:
        chat_id: 텔레그램 채팅 ID.
        message: 발송할 메시지 본문.

    Returns:
        발송 성공 여부.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN 미설정 — 텔레그램 발송 skip (chat_id=%s)", chat_id)
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = requests.post(
            url,
            json={"chat_id": chat_id, "text": message},
            timeout=5,
        )
        resp.raise_for_status()
        logger.info("텔레그램 발송 완료 — chat_id=%s", chat_id)
        return True
    except Exception as e:
        logger.error("텔레그램 발송 실패 chat_id=%s: %s", chat_id, e)
        return False
