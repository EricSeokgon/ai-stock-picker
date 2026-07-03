"""사용자별 알림 채널·유형 설정 서비스 (SPEC-STOCK-025).

# @MX:ANCHOR: [AUTO] 알림 채널 게이팅 핵심 서비스 — general_alert_service, rec_change, preferences_router에서 호출
# @MX:REASON: is_channel_enabled_async와 is_channel_enabled_sync가 3개 이상 모듈에서 직접 호출됨
# @MX:SPEC: SPEC-STOCK-025 REQ-PREF-003, REQ-PREF-004, REQ-PREF-005

opt-out 모델:
- 설정 행이 없으면 True (활성) 반환 → SPEC-024 기존 동작 유지 (하위 호환)
- 조회 예외 발생 시 True 반환 → 발송 누락 방지 (fail-open)
"""
from __future__ import annotations

import logging
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from stock_picker.db.models import NotificationPreference

log = structlog.get_logger()
logger = logging.getLogger(__name__)

# 지원 알림 유형 상수 (SPEC-STOCK-025 기준)
SUPPORTED_ALERT_TYPES: tuple[str, ...] = (
    "target_price",
    "surge_drop",
    "volume_spike",
    "ex_dividend",
    "rec_new",
    "rec_dropped",
    "rec_score_change",
    # SPEC-STOCK-031: 포트폴리오 알림 유형 추가
    "portfolio_target_return",
    "portfolio_mdd_breach",
)


async def is_channel_enabled_async(
    session: AsyncSession,
    user_id: int,
    alert_type: str,
    channel: str,
) -> bool:
    """알림 채널 활성 여부 판정 (비동기 — AsyncSession 사용).

    # @MX:NOTE: [AUTO] fail-open 설계 — 예외 시 True 반환하여 발송 누락 방지
    # @MX:SPEC: SPEC-STOCK-025 REQ-PREF-003, REQ-PREF-004, REQ-PREF-DISPATCH-006

    Args:
        session: AsyncSession.
        user_id: 사용자 ID.
        alert_type: 알림 유형 (예: "surge_drop").
        channel: 채널명 "email" 또는 "telegram".

    Returns:
        True이면 해당 채널로 발송 가능. 설정 행 없거나 예외 시 True.
    """
    try:
        result = await session.execute(
            select(NotificationPreference).where(
                NotificationPreference.user_id == user_id,
                NotificationPreference.alert_type == alert_type,
            )
        )
        pref = result.scalar_one_or_none()
        if pref is None:
            # 설정 행 없음 → 기본 활성 (하위 호환)
            return True
        return bool(getattr(pref, f"{channel}_enabled", True))
    except Exception as e:
        # 조회 실패 시 기본 활성으로 처리 (REQ-PREF-DISPATCH-006)
        log.error("알림 채널 설정 조회 실패 — 기본값(활성) 사용", user_id=user_id, alert_type=alert_type, error=str(e))
        return True


def is_channel_enabled_sync(
    db: Session,
    user_id: int,
    alert_type: str,
    channel: str,
) -> bool:
    """알림 채널 활성 여부 판정 (동기 — sync Session 사용).

    # @MX:NOTE: [AUTO] rec_change.py 동기 컨텍스트 전용 — fail-open 설계
    # @MX:SPEC: SPEC-STOCK-025 REQ-PREF-003, REQ-PREF-004, REQ-PREF-DISPATCH-006

    Args:
        db: 동기 Session.
        user_id: 사용자 ID.
        alert_type: 알림 유형.
        channel: 채널명 "email" 또는 "telegram".

    Returns:
        True이면 해당 채널로 발송 가능. 설정 행 없거나 예외 시 True.
    """
    try:
        pref = db.query(NotificationPreference).filter(
            NotificationPreference.user_id == user_id,
            NotificationPreference.alert_type == alert_type,
        ).first()
        if pref is None:
            # 설정 행 없음 → 기본 활성 (하위 호환)
            return True
        return bool(getattr(pref, f"{channel}_enabled", True))
    except Exception as e:
        # 조회 실패 시 기본 활성으로 처리 (REQ-PREF-DISPATCH-006)
        logger.error("알림 채널 설정 조회 실패 — 기본값(활성) 사용 user_id=%s: %s", user_id, e)
        return True


async def get_preferences(
    session: AsyncSession,
    user_id: int,
) -> list[dict[str, Any]]:
    """사용자의 알림 설정 목록 반환 (7개 유형 기본값 채움).

    # @MX:SPEC: SPEC-STOCK-025 REQ-PREF-API-001

    미설정 유형은 email_enabled=True, telegram_enabled=True 기본값으로 채움.

    Args:
        session: AsyncSession.
        user_id: 사용자 ID.

    Returns:
        7개 유형의 설정 딕셔너리 리스트.
    """
    result = await session.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == user_id
        )
    )
    existing = {pref.alert_type: pref for pref in result.scalars().all()}

    # 7개 유형 전체를 포함하되 미설정 유형은 기본값으로 채움
    return [
        {
            "alert_type": alert_type,
            "email_enabled": existing[alert_type].email_enabled if alert_type in existing else True,
            "telegram_enabled": existing[alert_type].telegram_enabled if alert_type in existing else True,
        }
        for alert_type in SUPPORTED_ALERT_TYPES
    ]


async def upsert_preferences(
    session: AsyncSession,
    user_id: int,
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """알림 설정 일괄 upsert.

    # @MX:SPEC: SPEC-STOCK-025 REQ-PREF-005, REQ-PREF-API-002, REQ-PREF-API-004

    Args:
        session: AsyncSession.
        user_id: 사용자 ID.
        items: [{"alert_type": str, "email_enabled": bool, "telegram_enabled": bool}, ...].

    Returns:
        갱신 후 7개 유형 전체 설정 목록.

    Raises:
        ValueError: 지원하지 않는 alert_type 포함 시.
    """
    # 미지원 유형 검증 (REQ-PREF-API-004)
    for item in items:
        if item["alert_type"] not in SUPPORTED_ALERT_TYPES:
            raise ValueError(f"지원하지 않는 alert_type: {item['alert_type']!r}")

    # PostgreSQL INSERT ... ON CONFLICT DO UPDATE 방식으로 upsert
    for item in items:
        stmt = pg_insert(NotificationPreference).values(
            user_id=user_id,
            alert_type=item["alert_type"],
            email_enabled=item["email_enabled"],
            telegram_enabled=item["telegram_enabled"],
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_pref_user_type",
            set_={
                "email_enabled": stmt.excluded.email_enabled,
                "telegram_enabled": stmt.excluded.telegram_enabled,
                "updated_at": stmt.excluded.updated_at,
            },
        )
        await session.execute(stmt)

    await session.commit()

    # 갱신 후 전체 설정 반환
    return await get_preferences(session, user_id)
