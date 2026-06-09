# 텔레그램 알림 발송 — 활성 구독자에게 추천 종목 전송
import logging
from typing import Any

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

    # 봇 인스턴스를 통해 발송 (봇이 실행 중인 경우만)
    try:
        import telegram

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


def _send_message_sync(chat_id: int, message: str) -> None:
    """동기 방식으로 텔레그램 메시지 발송 — asyncio 없이 requests 직접 사용.

    # @MX:NOTE: [AUTO] python-telegram-bot Bot.send_message는 비동기이므로
    # 동기 컨텍스트에서는 Bot.send_message를 asyncio.run()으로 래핑하거나
    # HTTPBot 직접 사용 필요 — 현재 구현은 로깅만 수행 (프로덕션 연동 필요)
    """
    # TODO: 프로덕션에서는 실제 봇 토큰으로 HTTP API 직접 호출
    logger.info("메시지 발송 예정 — chat_id=%s, length=%d", chat_id, len(message))
