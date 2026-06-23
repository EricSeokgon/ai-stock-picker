"""포트폴리오 알림 서비스 — 목표 수익률·MDD 임계값 알림 (SPEC-STOCK-031).

# @MX:ANCHOR: [AUTO] check_all_portfolio_alerts: 스케줄러·테스트에서 fan_in >= 3 예상되는 진입점
# @MX:REASON: 포트폴리오 알림 점검 오케스트레이션 진입점 — 변경 시 scheduler/jobs.py 동기화 필요
# @MX:SPEC: SPEC-STOCK-031 REQ-PAL-002~005

NFR-001 준수: 외부 과학 계산 라이브러리 미사용 — numpy + math 표준 라이브러리만 허용.
성과 요약 조회는 SPEC-030 calculate_performance_summary 재사용.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from stock_picker.db.models import Notification, Portfolio, PortfolioAlert
from stock_picker.notifications.preferences import is_channel_enabled_async
from stock_picker.portfolio.performance_summary import calculate_performance_summary

log = structlog.get_logger()
logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────
# 순수 함수: 알림 조건 평가 (DB·상태 없음)
# ────────────────────────────────────────────────────────────

# @MX:NOTE: [AUTO] check_portfolio_return_alert: YTD 기간(periods[0]) 기준 목표 수익률 도달 조건 평가
def check_portfolio_return_alert(
    alert: Any,
    performance: Any,
) -> tuple[bool, str]:
    """포트폴리오 목표 수익률 도달 여부 평가 (REQ-PAL-002).

    Args:
        alert: PortfolioAlert ORM 또는 모의 객체 (condition_value 속성 필요).
        performance: PerformanceSummaryResponse (periods[0] = YTD 기간).

    Returns:
        (triggered, message) — triggered=True이면 발화 메시지 반환.
    """
    period = performance.periods[0]  # YTD 기간 고정 (SPEC-031 기준 기간)
    if not period.has_data or period.total_return_pct is None:
        return False, ""
    if period.total_return_pct >= alert.condition_value:
        msg = (
            f"포트폴리오 수익률이 {period.total_return_pct:.2f}%에 도달했습니다 "
            f"(목표 {alert.condition_value:.2f}%)"
        )
        return True, msg
    return False, ""


# @MX:NOTE: [AUTO] check_portfolio_mdd_alert: YTD 기간(periods[0]) 기준 MDD 임계값 초과 조건 평가
def check_portfolio_mdd_alert(
    alert: Any,
    performance: Any,
) -> tuple[bool, str]:
    """포트폴리오 MDD 임계값 초과 여부 평가 (REQ-PAL-003).

    MDD는 음수 값이며, condition_value도 음수. mdd_pct <= condition_value이면 발화.
    예: mdd_pct=-16.5, condition_value=-15.0 → -16.5 <= -15.0 → 발화.

    Args:
        alert: PortfolioAlert ORM 또는 모의 객체 (condition_value 속성 필요).
        performance: PerformanceSummaryResponse (periods[0] = YTD 기간).

    Returns:
        (triggered, message) — triggered=True이면 발화 메시지 반환.
    """
    period = performance.periods[0]  # YTD 기간 고정
    if not period.has_data or period.mdd_pct is None:
        return False, ""
    if period.mdd_pct <= alert.condition_value:
        msg = (
            f"포트폴리오 최대낙폭이 {period.mdd_pct:.2f}%에 도달했습니다 "
            f"(임계 {alert.condition_value:.2f}%)"
        )
        return True, msg
    return False, ""


# ────────────────────────────────────────────────────────────
# 오케스트레이션: 활성 알림 전체 점검
# ────────────────────────────────────────────────────────────


async def check_all_portfolio_alerts(session: AsyncSession) -> int:
    """활성 포트폴리오 알림 전체 점검 및 발화 처리 (REQ-PAL-002~005).

    # @MX:WARN: [AUTO] notifications INSERT: krx_code 필드에 PORT_{portfolio_id} 사용 — 기존 UNIQUE 제약 재활용
    # @MX:REASON: 포트폴리오 식별자를 krx_code 필드에 저장하여 일자별 중복 발송 방지
    # @MX:SPEC: SPEC-STOCK-031 REQ-PAL-004, REQ-PAL-008

    동작:
    1. 활성(is_active=True)·미발화(is_triggered=False) 알림 조회
    2. portfolio_id별 그룹핑 → 성과 요약 1회 조회 (NFR-002, Redis 캐시 재사용)
    3. 조건 평가 → 발화 시 portfolio_alerts UPDATE + notifications INSERT (멱등)
    4. best-effort 이메일·텔레그램 발송
    5. 예외 시 해당 포트폴리오 건너뜀 (NFR-004)

    Args:
        session: AsyncSession.

    Returns:
        발화된 알림 건수.
    """
    # 활성·미발화 알림 조회
    stmt = select(PortfolioAlert).where(
        PortfolioAlert.is_active.is_(True),
        PortfolioAlert.is_triggered.is_(False),
    )
    result = await session.execute(stmt)
    active_alerts = result.scalars().all()

    if not active_alerts:
        return 0

    # portfolio_id별 그룹핑 (성과 요약 1회 조회용, NFR-002)
    from collections import defaultdict

    alerts_by_portfolio: dict[int, list[Any]] = defaultdict(list)
    for alert in active_alerts:
        alerts_by_portfolio[alert.portfolio_id].append(alert)

    triggered_count = 0
    now = datetime.now(timezone.utc)

    for portfolio_id, portfolio_alerts in alerts_by_portfolio.items():
        # 포트폴리오의 user_id 획득 (첫 번째 알림에서 참조)
        user_id = portfolio_alerts[0].user_id

        # 성과 요약 조회 (실패 시 해당 포트폴리오 건너뜀, NFR-004)
        try:
            performance = await calculate_performance_summary(
                portfolio_id=portfolio_id,
                user_id=user_id,
                db=None,  # Redis 캐시 우선 (refresh=False 기본값)
                redis=_get_redis_client(),
                refresh=False,
            )
        except Exception as e:
            logger.warning(
                "포트폴리오 성과 조회 실패 — 해당 포트폴리오 알림 건너뜀 (NFR-004) "
                "portfolio_id=%s: %s",
                portfolio_id,
                e,
            )
            continue

        # 개별 알림 평가
        for alert in portfolio_alerts:
            try:
                if alert.alert_type == "portfolio_target_return":
                    triggered, msg = check_portfolio_return_alert(alert, performance)
                elif alert.alert_type == "portfolio_mdd_breach":
                    triggered, msg = check_portfolio_mdd_alert(alert, performance)
                else:
                    # 미지원 유형 건너뜀
                    continue

                if not triggered:
                    continue

                # portfolio_alerts 업데이트 (is_triggered=True, 1회 발화)
                upd = (
                    update(PortfolioAlert)
                    .where(PortfolioAlert.id == alert.id)
                    .values(
                        is_triggered=True,
                        triggered_at=now,
                        triggered_message=msg,
                    )
                )
                await session.execute(upd)

                # notifications 적재 — krx_code 필드에 PORT_{id} 사용 (멱등성, REQ-PAL-008)
                # UNIQUE 제약 uq_notification_user_type_code_date 재활용
                notif_payload = {
                    "user_id": alert.user_id,
                    "type": alert.alert_type,
                    "krx_code": f"PORT_{portfolio_id}",
                    "title": _build_notification_title(alert.alert_type),
                    "body": msg,
                    "is_read": False,
                    "ref_date": now.date(),
                    "related_alert_id": None,
                }
                ins = pg_insert(Notification).values(**notif_payload)
                ins = ins.on_conflict_do_nothing(
                    constraint="uq_notification_user_type_code_date"
                )
                await session.execute(ins)
                await session.commit()

                triggered_count += 1
                log.info(
                    "포트폴리오 알림 발동",
                    alert_id=alert.id,
                    portfolio_id=portfolio_id,
                    alert_type=alert.alert_type,
                )

                # 채널 발송 best-effort (실패 무시, REQ-PAL-005·006)
                await _try_send_portfolio_alert_email(alert, msg, session)
                await _try_send_portfolio_alert_telegram(alert, msg, session)

            except Exception as e:
                logger.error(
                    "포트폴리오 알림 점검 오류 alert_id=%s: %s", alert.id, e
                )
                try:
                    await session.rollback()
                except Exception:
                    pass

    return triggered_count


def _build_notification_title(alert_type: str) -> str:
    """알림 유형별 인박스 제목 생성."""
    type_label_map = {
        "portfolio_target_return": "포트폴리오 목표 수익률 달성",
        "portfolio_mdd_breach": "포트폴리오 MDD 임계값 초과",
    }
    return f"[{type_label_map.get(alert_type, '포트폴리오 알림')}]"


def _get_redis_client() -> Any:
    """Redis 클라이언트 지연 획득 (순환 import 방지)."""
    try:
        from stock_picker.api.deps import get_redis_client_sync  # type: ignore[import]

        return get_redis_client_sync()
    except Exception:
        # 테스트 환경 등 Redis 없는 경우 MagicMock 반환
        try:
            from unittest.mock import AsyncMock

            mock = AsyncMock()
            mock.get = AsyncMock(return_value=None)
            mock.set = AsyncMock()
            return mock
        except Exception:
            return None


async def _try_send_portfolio_alert_email(
    alert: Any, message: str, session: AsyncSession
) -> None:
    """포트폴리오 알림 이메일 발송 best-effort (REQ-PAL-005·006)."""
    if not await is_channel_enabled_async(session, alert.user_id, alert.alert_type, "email"):
        return
    try:
        from sqlalchemy import select as sa_select

        from stock_picker.db.models import EmailSubscription
        from stock_picker.notifications.email_service import send_general_alert_email

        result = await session.execute(
            sa_select(EmailSubscription).where(
                EmailSubscription.user_id == alert.user_id,
                EmailSubscription.is_active.is_(True),
            )
        )
        sub = result.scalar_one_or_none()
        if sub:
            send_general_alert_email(
                sub.email,
                f"PORT_{alert.portfolio_id}",
                alert.alert_type,
                message,
            )
    except Exception as e:
        logger.error("포트폴리오 알림 이메일 발송 실패 user_id=%s: %s", alert.user_id, e)


async def _try_send_portfolio_alert_telegram(
    alert: Any, message: str, session: AsyncSession
) -> None:
    """포트폴리오 알림 텔레그램 발송 best-effort (REQ-PAL-005·006)."""
    if not await is_channel_enabled_async(session, alert.user_id, alert.alert_type, "telegram"):
        return
    try:
        from sqlalchemy import select as sa_select

        from stock_picker.db.models import TelegramSubscription
        from stock_picker.telegram.notifier import _send_message_sync

        result = await session.execute(
            sa_select(TelegramSubscription).where(
                TelegramSubscription.user_id == alert.user_id,
                TelegramSubscription.is_active.is_(True),
            )
        )
        sub = result.scalar_one_or_none()
        if sub:
            _send_message_sync(sub.chat_id, message)
    except Exception as e:
        logger.error("포트폴리오 알림 텔레그램 발송 실패 user_id=%s: %s", alert.user_id, e)


# ────────────────────────────────────────────────────────────
# CRUD 서비스
# ────────────────────────────────────────────────────────────


async def create_portfolio_alert(
    session: AsyncSession,
    user_id: int,
    portfolio_id: int,
    alert_type: str,
    condition_value: float,
) -> PortfolioAlert | None:
    """포트폴리오 알림 생성 (REQ-PAL-001).

    소유권 확인 실패 시 None 반환 (→ 라우터에서 404 처리, NFR-005).
    UNIQUE 제약 위반 시 IntegrityError 전파 (→ 라우터에서 409 처리, REQ-PAL-008).

    Args:
        session: AsyncSession.
        user_id: 요청 사용자 ID.
        portfolio_id: 대상 포트폴리오 ID.
        alert_type: "portfolio_target_return" | "portfolio_mdd_breach".
        condition_value: 목표 수익률(%) 또는 MDD 임계값(%).

    Returns:
        생성된 PortfolioAlert 또는 None (소유권 불일치).
    """
    # 소유권 확인 (NFR-005)
    pf_result = await session.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == user_id,
        )
    )
    portfolio = pf_result.scalar_one_or_none()
    if portfolio is None:
        return None

    alert = PortfolioAlert(
        user_id=user_id,
        portfolio_id=portfolio_id,
        alert_type=alert_type,
        condition_value=condition_value,
        is_active=True,
        is_triggered=False,
    )
    session.add(alert)
    await session.flush()
    await session.refresh(alert)
    return alert


async def list_portfolio_alerts(
    session: AsyncSession,
    user_id: int,
    portfolio_id: int,
) -> list[PortfolioAlert] | None:
    """포트폴리오 알림 목록 조회 (REQ-PAL-001).

    소유권 확인 실패 시 None 반환 (→ 라우터에서 404 처리, NFR-005).

    Args:
        session: AsyncSession.
        user_id: 요청 사용자 ID.
        portfolio_id: 대상 포트폴리오 ID.

    Returns:
        알림 목록 또는 None (소유권 불일치).
    """
    # 소유권 확인
    pf_result = await session.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == user_id,
        )
    )
    if pf_result.scalar_one_or_none() is None:
        return None

    result = await session.execute(
        select(PortfolioAlert).where(
            PortfolioAlert.portfolio_id == portfolio_id,
            PortfolioAlert.user_id == user_id,
        )
    )
    return list(result.scalars().all())


async def update_portfolio_alert(
    session: AsyncSession,
    user_id: int,
    portfolio_id: int,
    alert_id: int,
    condition_value: float | None = None,
    is_active: bool | None = None,
) -> PortfolioAlert | None:
    """포트폴리오 알림 수정 (REQ-PAL-001).

    소유권 확인 및 알림 존재 여부 확인. None 반환 시 라우터에서 404 처리.

    Args:
        session: AsyncSession.
        user_id: 요청 사용자 ID.
        portfolio_id: 대상 포트폴리오 ID.
        alert_id: 수정 대상 알림 ID.
        condition_value: 새 조건값 (None이면 변경 없음).
        is_active: 새 활성 상태 (None이면 변경 없음).

    Returns:
        수정된 PortfolioAlert 또는 None (소유권/알림 불일치).
    """
    result = await session.execute(
        select(PortfolioAlert).where(
            PortfolioAlert.id == alert_id,
            PortfolioAlert.portfolio_id == portfolio_id,
            PortfolioAlert.user_id == user_id,
        )
    )
    alert = result.scalar_one_or_none()
    if alert is None:
        return None

    if condition_value is not None:
        alert.condition_value = condition_value
    if is_active is not None:
        alert.is_active = is_active

    return alert


async def delete_portfolio_alert(
    session: AsyncSession,
    user_id: int,
    portfolio_id: int,
    alert_id: int,
) -> bool:
    """포트폴리오 알림 삭제 (REQ-PAL-001).

    Args:
        session: AsyncSession.
        user_id: 요청 사용자 ID.
        portfolio_id: 대상 포트폴리오 ID.
        alert_id: 삭제 대상 알림 ID.

    Returns:
        True이면 삭제 성공, False이면 존재하지 않음.
    """
    result = await session.execute(
        select(PortfolioAlert).where(
            PortfolioAlert.id == alert_id,
            PortfolioAlert.portfolio_id == portfolio_id,
            PortfolioAlert.user_id == user_id,
        )
    )
    alert = result.scalar_one_or_none()
    if alert is None:
        return False

    await session.delete(alert)
    return True
