"""일반 알림 서비스 — 목표가·급등락 알림 설정 관리 및 점검 (SPEC-STOCK-020).

# @MX:ANCHOR: [AUTO] 알림 점검 핵심 진입점 — 라우터·스케줄러·테스트에서 호출
# @MX:REASON: general_alert_router, scheduler/jobs, test_general_alerts 3개 이상에서 직접 임포트
# @MX:SPEC: SPEC-STOCK-020 REQ-ALERT-002
"""
from __future__ import annotations

import os
from datetime import datetime, time, timezone
from typing import Any
from zoneinfo import ZoneInfo

import structlog
from fastapi import HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from stock_picker.db.models import Alert, EmailSubscription, Notification, TelegramSubscription
from stock_picker.notifications.preferences import is_channel_enabled_async
from stock_picker.mapping.prices import get_avg_volume, get_stock_price_data
from stock_picker.notifications.email_service import send_general_alert_email
from stock_picker.telegram.notifier import _send_message_sync

log = structlog.get_logger()

# 지원 알림 유형
_VALID_ALERT_TYPES = {"target_price", "surge_drop", "ex_dividend", "volume_spike"}
# 지원 방향
_VALID_DIRECTIONS = {"above", "below", "either"}

# 장중 시간 게이팅 상수
_KST = ZoneInfo("Asia/Seoul")
_MARKET_OPEN = time(9, 0)
_MARKET_CLOSE = time(15, 30)


# ══════════════════════════════════════════════════════════
# Pydantic 스키마
# ══════════════════════════════════════════════════════════


class AlertCreate(BaseModel):
    """알림 설정 생성 요청 스키마."""

    model_config = ConfigDict(str_strip_whitespace=True)

    krx_code: str = Field(..., min_length=1, max_length=10)
    stock_name: str | None = Field(default=None, max_length=100)
    alert_type: str = Field(...)
    condition_value: float = Field(..., gt=0)
    condition_direction: str | None = Field(default=None)

    @field_validator("alert_type")
    @classmethod
    def validate_alert_type(cls, v: str) -> str:
        if v not in _VALID_ALERT_TYPES:
            raise ValueError(f"alert_type must be one of {_VALID_ALERT_TYPES}")
        return v

    @field_validator("condition_direction", mode="before")
    @classmethod
    def default_direction(cls, v: str | None) -> str | None:
        # surge_drop 기본값은 서비스 레이어에서 처리
        return v

    def model_post_init(self, __context: Any) -> None:
        # surge_drop 기본 방향 either
        if self.alert_type == "surge_drop" and self.condition_direction is None:
            object.__setattr__(self, "condition_direction", "either")


class AlertUpdate(BaseModel):
    """알림 설정 수정 요청 스키마 (부분 업데이트)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    stock_name: str | None = Field(default=None, max_length=100)
    condition_value: float | None = Field(default=None, gt=0)
    condition_direction: str | None = Field(default=None)
    is_active: bool | None = Field(default=None)

    @field_validator("condition_direction")
    @classmethod
    def validate_direction(cls, v: str | None) -> str | None:
        if v is not None and v not in _VALID_DIRECTIONS:
            raise ValueError(f"condition_direction must be one of {_VALID_DIRECTIONS}")
        return v


class AlertSchema(BaseModel):
    """알림 설정 응답 스키마."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    krx_code: str
    stock_name: str | None
    alert_type: str
    condition_value: float
    condition_direction: str | None
    is_active: bool
    is_triggered: bool
    triggered_at: datetime | None
    triggered_message: str | None
    created_at: datetime


# ══════════════════════════════════════════════════════════
# 점검 로직 (순수 함수, DB 불필요)
# ══════════════════════════════════════════════════════════


def check_target_price(
    alert: Any,
    price_data: dict[str, Any] | None,
) -> tuple[bool, str]:
    """목표가 도달 여부 판정.

    # @MX:ANCHOR: [AUTO] 목표가 점검 순수 함수 — 서비스·테스트에서 직접 호출
    # @MX:REASON: check_and_trigger_all_alerts, 유닛 테스트 2곳에서 직접 import

    Args:
        alert: Alert ORM 모델 (condition_value, condition_direction 필드 필요).
        price_data: {"close_price": float, "change_rate": float} 또는 None.

    Returns:
        (triggered: bool, message: str) 튜플. 미발동 시 message는 빈 문자열.
    """
    if price_data is None:
        return False, ""

    close = price_data.get("close_price", 0.0)
    target = alert.condition_value
    direction = alert.condition_direction or "above"

    if direction == "above" and close >= target:
        msg = f"{alert.krx_code} 현재가 {close:,.0f}원이 목표가 {target:,.0f}원에 도달했습니다."
        return True, msg

    if direction == "below" and close <= target:
        msg = f"{alert.krx_code} 현재가 {close:,.0f}원이 하한 목표가 {target:,.0f}원에 도달했습니다."
        return True, msg

    return False, ""


def check_surge_drop(
    alert: Any,
    price_data: dict[str, Any] | None,
) -> tuple[bool, str]:
    """급등락 임계값 초과 여부 판정.

    # @MX:ANCHOR: [AUTO] 급등락 점검 순수 함수 — 서비스·테스트에서 직접 호출
    # @MX:REASON: check_and_trigger_all_alerts, 유닛 테스트 2곳에서 직접 import

    Args:
        alert: Alert ORM 모델 (condition_value: 임계값%, condition_direction 필드 필요).
        price_data: {"close_price": float, "change_rate": float} 또는 None.

    Returns:
        (triggered: bool, message: str) 튜플.
    """
    if price_data is None:
        return False, ""

    rate = price_data.get("change_rate", 0.0)
    threshold = alert.condition_value
    direction = alert.condition_direction or "either"

    triggered = False
    if direction == "above" and rate >= threshold:
        triggered = True
    elif direction == "below" and rate <= -threshold:
        triggered = True
    elif direction == "either" and abs(rate) >= threshold:
        triggered = True

    if triggered:
        sign = "+" if rate >= 0 else ""
        msg = (
            f"{alert.krx_code} 급등락 알림: 전일 대비 {sign}{rate:.2f}% "
            f"(임계값 ±{threshold:.1f}%)"
        )
        return True, msg

    return False, ""


def _is_market_open(now_kst: datetime | None = None) -> bool:
    """주식 시장 개장 여부 반환 (09:00~15:30 KST).

    # @MX:NOTE: [AUTO] 장중 시간 게이팅 헬퍼 — ALERT_MARKET_HOURS_GATE 환경변수로 비활성화 가능
    # @MX:SPEC: SPEC-STOCK-023 REQ-023-020~024

    Args:
        now_kst: 기준 시각 (KST). None이면 현재 시각 사용.

    Returns:
        True이면 장중 (09:00 이상 15:30 이하).
    """
    if now_kst is None:
        now_kst = datetime.now(_KST)
    t = now_kst.time()
    return _MARKET_OPEN <= t <= _MARKET_CLOSE


def check_volume_spike(
    alert: Any,
    volume_data: dict[str, Any] | None,
) -> tuple[bool, str]:
    """거래량 급증 여부 판정.

    # @MX:ANCHOR: [AUTO] 거래량 급증 점검 순수 함수 — 서비스·테스트에서 직접 호출
    # @MX:REASON: check_and_trigger_all_alerts, 유닛 테스트에서 직접 import
    # @MX:SPEC: SPEC-STOCK-023 REQ-023-005~012

    Args:
        alert: Alert ORM 모델 (condition_value: 배수 임계값, 예: 2.0).
        volume_data: {"avg_volume": float, "today_volume": int} 또는 None.

    Returns:
        (triggered: bool, message: str) 튜플.
    """
    if volume_data is None:
        return False, ""

    avg_volume = volume_data.get("avg_volume", 0.0)
    today_volume = volume_data.get("today_volume", 0)

    if avg_volume <= 0:
        return False, ""

    multiplier = alert.condition_value
    ratio = today_volume / avg_volume

    if ratio >= multiplier:
        msg = (
            f"{alert.krx_code} 거래량 급증 알림: "
            f"오늘 거래량 {today_volume:,}주 "
            f"(30일 평균 {avg_volume:,.0f}주의 {ratio:.1f}배)"
        )
        return True, msg

    return False, ""


def build_notification_payload(
    alert: Any,
    message: str,
    triggered_at: datetime,
) -> dict[str, Any]:
    """triggered alert → notifications 테이블 삽입용 딕셔너리 생성.

    related_alert_id=None: 이 테이블은 watchlist_alerts와 무관한 신규 알림.

    Args:
        alert: Alert ORM 모델.
        message: 발동 메시지.
        triggered_at: 발동 시각 (timezone-aware).

    Returns:
        notifications 테이블 INSERT에 필요한 컬럼 딕셔너리.
    """
    type_label_map = {
        "target_price": "목표가 알림",
        "surge_drop": "급등락 알림",
        "ex_dividend": "배당락 알림",
        "volume_spike": "거래량 급증 알림",
    }
    title = f"[{type_label_map.get(alert.alert_type, '알림')}] {alert.krx_code}"
    if hasattr(alert, "stock_name") and alert.stock_name:
        title = f"[{type_label_map.get(alert.alert_type, '알림')}] {alert.stock_name}({alert.krx_code})"

    return {
        "user_id": alert.user_id,
        "type": alert.alert_type,
        "krx_code": alert.krx_code,
        "title": title,
        "body": message,
        "is_read": False,
        "ref_date": triggered_at.date(),
        "related_alert_id": None,  # watchlist_alerts 참조 아님
    }


# ══════════════════════════════════════════════════════════
# 비동기 CRUD 서비스 (AsyncSession 기반)
# ══════════════════════════════════════════════════════════


async def create_alert(
    session: AsyncSession,
    user_id: int,
    data: AlertCreate,
) -> AlertSchema:
    """신규 알림 설정 생성.

    Args:
        session: AsyncSession.
        user_id: 인증된 사용자 ID.
        data: AlertCreate 스키마.

    Returns:
        생성된 AlertSchema.
    """
    # surge_drop 기본 방향 보장
    direction = data.condition_direction
    if data.alert_type == "surge_drop" and direction is None:
        direction = "either"

    stmt = (
        insert(Alert)
        .values(
            user_id=user_id,
            krx_code=data.krx_code,
            stock_name=data.stock_name,
            alert_type=data.alert_type,
            condition_value=data.condition_value,
            condition_direction=direction,
            is_active=True,
            is_triggered=False,
        )
        .returning(Alert)
    )
    result = await session.execute(stmt)
    await session.commit()
    alert = result.scalar_one()
    return AlertSchema.model_validate(alert)


async def get_user_alerts(
    session: AsyncSession,
    user_id: int,
) -> list[AlertSchema]:
    """사용자의 알림 설정 목록 반환.

    Args:
        session: AsyncSession.
        user_id: 사용자 ID.

    Returns:
        AlertSchema 리스트 (최신순).
    """
    stmt = (
        select(Alert)
        .where(Alert.user_id == user_id)
        .order_by(Alert.created_at.desc())
    )
    result = await session.execute(stmt)
    alerts = result.scalars().all()
    return [AlertSchema.model_validate(a) for a in alerts]


async def get_alert(
    session: AsyncSession,
    alert_id: int,
    user_id: int,
) -> AlertSchema:
    """단일 알림 설정 조회 (소유권 검증 포함).

    Args:
        session: AsyncSession.
        alert_id: 알림 ID.
        user_id: 요청자 ID.

    Raises:
        HTTPException(404): 알림 없음 또는 타인 소유.

    Returns:
        AlertSchema.
    """
    stmt = select(Alert).where(Alert.id == alert_id, Alert.user_id == user_id)
    result = await session.execute(stmt)
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="알림을 찾을 수 없습니다.")
    return AlertSchema.model_validate(alert)


async def update_alert(
    session: AsyncSession,
    alert_id: int,
    user_id: int,
    data: AlertUpdate,
) -> AlertSchema:
    """알림 설정 부분 수정.

    Args:
        session: AsyncSession.
        alert_id: 알림 ID.
        user_id: 요청자 ID.
        data: AlertUpdate 스키마.

    Raises:
        HTTPException(404): 알림 없음 또는 타인 소유.

    Returns:
        수정된 AlertSchema.
    """
    # 소유권 검증
    check_stmt = select(Alert).where(Alert.id == alert_id, Alert.user_id == user_id)
    check_result = await session.execute(check_stmt)
    if check_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="알림을 찾을 수 없습니다.")

    update_data = data.model_dump(exclude_none=True)
    if not update_data:
        return await get_alert(session=session, alert_id=alert_id, user_id=user_id)

    stmt = (
        update(Alert)
        .where(Alert.id == alert_id, Alert.user_id == user_id)
        .values(**update_data)
        .returning(Alert)
    )
    result = await session.execute(stmt)
    await session.commit()
    alert = result.scalar_one()
    return AlertSchema.model_validate(alert)


async def delete_alert(
    session: AsyncSession,
    alert_id: int,
    user_id: int,
) -> None:
    """알림 설정 삭제 (소유권 검증 포함).

    Args:
        session: AsyncSession.
        alert_id: 알림 ID.
        user_id: 요청자 ID.

    Raises:
        HTTPException(404): 알림 없음 또는 타인 소유.
    """
    stmt = select(Alert).where(Alert.id == alert_id, Alert.user_id == user_id)
    result = await session.execute(stmt)
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="알림을 찾을 수 없습니다.")

    await session.delete(alert)
    await session.commit()


# ══════════════════════════════════════════════════════════
# 알림 점검 루프 (스케줄러·엔드포인트에서 호출)
# ══════════════════════════════════════════════════════════


async def check_and_trigger_all_alerts(session: AsyncSession) -> int:
    """활성 알림 전체를 점검하여 조건 충족 시 notifications 적재 + 이메일 발송.

    # @MX:WARN: [AUTO] 루프 내 외부 API 호출 — get_stock_price_data per alert
    # @MX:REASON: 종목마다 FinanceDataReader 호출하므로 알림 수 증가 시 지연 발생 가능. 향후 배치 최적화 고려.

    이미 발동된 알림(is_triggered=True)은 건너뜁니다.
    가격/거래량 조회 실패 시 해당 알림만 건너뜁니다 (graceful degradation).
    notifications 적재 시 UNIQUE 제약으로 중복 삽입을 무시합니다.
    ALERT_MARKET_HOURS_GATE=true(기본)이면 장중(09:00~15:30 KST)에만 외부 API 호출.

    Args:
        session: AsyncSession.

    Returns:
        발동된 알림 건수.
    """
    # 장중 시간 게이팅 (REQ-023-020~024)
    gate_enabled = os.getenv("ALERT_MARKET_HOURS_GATE", "true").lower() not in ("false", "0", "no")
    if gate_enabled and not _is_market_open():
        log.info("장 마감 시간 — 알림 점검 건너뜀")
        return 0

    stmt = select(Alert).where(Alert.is_active == True, Alert.is_triggered == False)  # noqa: E712
    result = await session.execute(stmt)
    active_alerts = result.scalars().all()

    triggered_count = 0
    now = datetime.now(timezone.utc)

    for alert in active_alerts:
        # 이미 발동된 알림은 건너뜀 (SQL 필터 외 방어)
        if getattr(alert, "is_triggered", False):
            continue
        try:
            if alert.alert_type == "volume_spike":
                volume_data = await get_avg_volume(alert.krx_code)
                triggered, msg = check_volume_spike(alert, volume_data)
            else:
                price_data = await get_stock_price_data(alert.krx_code)

                if alert.alert_type == "target_price":
                    triggered, msg = check_target_price(alert, price_data)
                elif alert.alert_type == "surge_drop":
                    triggered, msg = check_surge_drop(alert, price_data)
                else:
                    # ex_dividend 등 미구현 유형은 건너뜀
                    continue

            if not triggered:
                continue

            # alerts 테이블 업데이트
            upd = (
                update(Alert)
                .where(Alert.id == alert.id)
                .values(
                    is_triggered=True,
                    triggered_at=now,
                    triggered_message=msg,
                )
            )
            await session.execute(upd)

            # notifications 테이블 삽입 (중복 시 무시)
            notif_payload = build_notification_payload(alert, msg, now)
            ins = pg_insert(Notification).values(**notif_payload)
            ins = ins.on_conflict_do_nothing(
                constraint="uq_notification_user_type_code_date"
            )
            await session.execute(ins)
            await session.commit()

            triggered_count += 1
            log.info("알림 발동", alert_id=alert.id, type=alert.alert_type, code=alert.krx_code)

            # 이메일·텔레그램 채널 발송 (best-effort, 실패 무시)
            await _try_send_alert_email(alert, msg, session)
            await _try_send_telegram(alert, msg, session)

        except Exception:
            log.exception("알림 점검 오류", alert_id=alert.id)
            await session.rollback()

    return triggered_count


async def _try_send_alert_email(alert: Any, message: str, session: AsyncSession) -> None:
    """이메일 구독자에게 알림 이메일 발송 (best-effort).

    채널 설정 확인 후 이메일이 활성인 경우에만 발송 (REQ-PREF-DISPATCH-001).

    Args:
        alert: Alert ORM 모델.
        message: 알림 메시지 본문.
        session: AsyncSession.
    """
    # 이메일 채널 활성 여부 확인 (설정 없거나 예외 시 기본 활성)
    if not await is_channel_enabled_async(session, alert.user_id, alert.alert_type, "email"):
        return
    try:
        result = await session.execute(
            select(EmailSubscription).where(
                EmailSubscription.user_id == alert.user_id,
                EmailSubscription.is_active.is_(True),
            )
        )
        sub = result.scalar_one_or_none()
        if sub:
            send_general_alert_email(sub.email, alert.krx_code, alert.alert_type, message)
    except Exception as e:
        log.error("알림 이메일 발송 실패 user_id=%s: %s", alert.user_id, e)


async def _try_send_telegram(alert: Any, message: str, session: AsyncSession) -> None:
    """텔레그램 구독자에게 알림 메시지 발송 (best-effort).

    채널 설정 확인 후 텔레그램이 활성인 경우에만 발송 (REQ-PREF-DISPATCH-002).

    Args:
        alert: Alert ORM 모델.
        message: 알림 메시지 본문.
        session: AsyncSession.
    """
    # 텔레그램 채널 활성 여부 확인 (설정 없거나 예외 시 기본 활성)
    if not await is_channel_enabled_async(session, alert.user_id, alert.alert_type, "telegram"):
        return
    try:
        result = await session.execute(
            select(TelegramSubscription).where(
                TelegramSubscription.user_id == alert.user_id,
                TelegramSubscription.is_active.is_(True),
            )
        )
        sub = result.scalar_one_or_none()
        if sub:
            _send_message_sync(sub.chat_id, f"[{alert.krx_code}] {message}")
    except Exception as e:
        log.error("텔레그램 발송 실패 user_id=%s: %s", alert.user_id, e)
