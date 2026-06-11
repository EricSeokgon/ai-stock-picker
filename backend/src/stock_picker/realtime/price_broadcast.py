# 멀티플렉스 가격 브로드캐스트 루프 (SPEC-STOCK-016 M2/M6)
# REQ-RT-001: get_current_price 재사용
# REQ-RT-002: REALTIME_PRICE_MOCK 모킹 모드
# REQ-RT-003: 심볼별 실패 스킵·로그·재시도
# REQ-ALERT-001~005: 가격 알림 평가 및 멱등 알림 생성
import asyncio
import logging
import os
from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from stock_picker.db.models import Notification, WatchlistAlert
from stock_picker.realtime.connection_manager import ConnectionManager
from stock_picker.realtime.price_feed import get_current_price

logger = logging.getLogger(__name__)

# @MX:NOTE: [AUTO] 폴링 간격 — 기본 10초 (REQ-NFR-003)
_POLL_INTERVAL = int(os.getenv("REALTIME_POLL_INTERVAL", "10"))


def get_mock_price(krx_code: str) -> dict[str, Any]:
    """결정론적 mock 가격 생성 (REQ-RT-002).

    개발/테스트 환경에서 외부 데이터소스 없이 동작하도록 한다.
    price = hash(krx_code) % 100000 + 10000
    """
    price = abs(hash(krx_code)) % 100_000 + 10_000
    return {
        "krx_code": krx_code,
        "price": float(price),
        "change_pct": 0.5,
        "timestamp": datetime.now().isoformat(),
    }


async def get_price_or_mock(krx_code: str) -> dict[str, Any] | None:
    """REALTIME_PRICE_MOCK 환경변수에 따라 mock 또는 실제 가격 반환."""
    if os.getenv("REALTIME_PRICE_MOCK", "").lower() in ("1", "true", "yes"):
        return get_mock_price(krx_code)
    return get_current_price(krx_code)


async def _insert_alert_notification_async(
    db: AsyncSession,
    user_id: int,
    krx_code: str,
    target_price: float,
    direction: str,
    alert_id: int,
) -> None:
    """가격 알림 인박스 멱등 insert (REQ-ALERT-002/003).

    UNIQUE 제약 uq_notification_user_type_code_date로 중복 방지.
    """
    today = date.today()
    title = f"{krx_code} 가격 알림 — 목표가 {direction} {target_price:,.0f}원 도달"
    stmt = (
        pg_insert(Notification)
        .values(
            user_id=user_id,
            type="price_alert",
            krx_code=krx_code,
            title=title,
            body=None,
            is_read=False,
            ref_date=today,
            related_alert_id=alert_id,
        )
        .on_conflict_do_nothing(constraint="uq_notification_user_type_code_date")
    )
    await db.execute(stmt)
    await db.commit()


async def evaluate_alerts(krx_code: str, price: float, db: AsyncSession) -> None:
    """해당 심볼의 활성 알림을 평가하여 임계 도달 시 인박스 알림 생성 (REQ-ALERT-001~005).

    # @MX:WARN: [AUTO] DB 조회 포함 — 브로드캐스트 루프에서 매 폴링마다 호출됨
    # @MX:REASON: 고부하 시 N개 심볼 × M개 알림 쿼리 발생; 스케일링 시 배치 최적화 고려
    """
    try:
        stmt = select(WatchlistAlert).where(
            WatchlistAlert.krx_code == krx_code,
            WatchlistAlert.is_active.is_(True),
            WatchlistAlert.triggered_at.is_(None),
        )
        result = await db.execute(stmt)
        alerts = result.scalars().all()

        for alert in alerts:
            # REQ-ALERT-004: is_active=False이거나 이미 triggered된 알림 재발동 방지
            if not alert.is_active or alert.triggered_at is not None:
                continue
            triggered = False
            if alert.direction == "above" and price >= alert.target_price:
                triggered = True
            elif alert.direction == "below" and price <= alert.target_price:
                triggered = True

            if triggered:
                try:
                    await _insert_alert_notification_async(
                        db,
                        user_id=alert.user_id,
                        krx_code=krx_code,
                        target_price=alert.target_price,
                        direction=alert.direction,
                        alert_id=alert.id,
                    )
                    logger.info(
                        "가격 알림 발동 — user_id=%s krx_code=%s price=%s target=%s direction=%s",
                        alert.user_id, krx_code, price, alert.target_price, alert.direction,
                    )
                except Exception:
                    # REQ-ALERT-005: 알림 실패가 스트림을 끊지 않음
                    logger.exception("알림 생성 실패 (스트림 계속) — krx_code=%s alert_id=%s", krx_code, alert.id)
    except Exception:
        logger.exception("알림 평가 실패 (스트림 계속) — krx_code=%s", krx_code)


async def broadcast_prices_once(
    manager: ConnectionManager,
    db_session_factory: Any,
) -> None:
    """단일 폴링 사이클 — 구독 심볼별 가격 조회 후 팬아웃 (REQ-SUB-003).

    # @MX:ANCHOR: [AUTO] 브로드캐스트 루프 핵심 함수
    # @MX:REASON: price_broadcast_loop, 테스트, ws_router lifespan에서 호출 (fan_in >= 3)
    """
    symbols = manager.get_all_symbols()
    if not symbols:
        return

    for sym in list(symbols):
        try:
            price_data = await get_price_or_mock(sym)
            if price_data is None:
                logger.warning("가격 데이터 없음, 스킵 — symbol=%s", sym)
                continue

            msg = {"type": "price", **price_data}
            conns = manager.get_connections_for_symbol(sym)
            dead_conns: list = []
            for ws in list(conns):
                try:
                    await ws.send_json(msg)
                except Exception:
                    logger.warning("연결 전송 실패, 연결 제거 — symbol=%s", sym)
                    dead_conns.append(ws)

            # 죽은 연결 정리 (REQ-NFR-002)
            for ws in dead_conns:
                manager.disconnect(ws)

            # 알림 평가 — DB 세션이 있을 때만
            if db_session_factory is not None:
                try:
                    async with db_session_factory() as db:
                        await evaluate_alerts(sym, price_data["price"], db)
                except Exception:
                    logger.exception("알림 평가 DB 세션 오류 (스트림 계속) — symbol=%s", sym)

        except Exception:
            # REQ-RT-003: 심볼별 실패 스킵 후 다음 심볼 계속
            logger.exception("가격 브로드캐스트 실패, 스킵 — symbol=%s", sym)


async def price_broadcast_loop(
    manager: ConnectionManager,
    db_session_factory: Any,
    poll_interval: int = _POLL_INTERVAL,
) -> None:
    """무한 브로드캐스트 루프 — lifespan 백그라운드 태스크로 실행.

    # @MX:WARN: [AUTO] 백그라운드 asyncio 태스크 — 취소(CancelledError)로만 종료
    # @MX:REASON: FastAPI lifespan에서 task.cancel()로 정리; 런타임 외 종료 경로 없음
    """
    logger.info("가격 브로드캐스트 루프 시작 — 간격=%ds", poll_interval)
    while True:
        await asyncio.sleep(poll_interval)
        await broadcast_prices_once(manager, db_session_factory)
