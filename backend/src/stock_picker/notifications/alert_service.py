# 가격 알림 서비스 — CRUD 및 알림 조건 평가
import logging
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from stock_picker.db.models import WatchlistAlert
from stock_picker.notifications.schemas import WatchlistAlertCreate

logger = logging.getLogger(__name__)


# @MX:ANCHOR: [AUTO] 가격 알림 CRUD 진입점 — 라우터/스케줄러에서 참조
# @MX:REASON: alert_router.py, jobs.py(check_price_alerts), 테스트 코드 등 3개 이상에서 사용


def create_alert(user_id: int, data: WatchlistAlertCreate, db: Session) -> WatchlistAlert:
    """가격 알림 생성.

    Args:
        user_id: 현재 사용자 ID
        data: 알림 생성 요청 데이터
        db: SQLAlchemy 동기 세션

    Returns:
        생성된 WatchlistAlert 인스턴스
    """
    alert = WatchlistAlert(
        user_id=user_id,
        krx_code=data.krx_code,
        target_price=data.target_price,
        direction=data.direction,
        is_active=True,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    logger.info("가격 알림 생성 — user_id=%d, krx_code=%s, target=%.2f %s",
                user_id, data.krx_code, data.target_price, data.direction)
    return alert


def get_alerts(user_id: int, db: Session) -> list[WatchlistAlert]:
    """사용자의 가격 알림 목록 조회.

    Args:
        user_id: 현재 사용자 ID
        db: SQLAlchemy 동기 세션

    Returns:
        해당 사용자의 알림 목록 (생성 역순)
    """
    return (
        db.query(WatchlistAlert)
        .filter(WatchlistAlert.user_id == user_id)
        .order_by(WatchlistAlert.created_at.desc())
        .all()
    )


def delete_alert(user_id: int, alert_id: int, db: Session) -> None:
    """가격 알림 삭제.

    Args:
        user_id: 현재 사용자 ID
        alert_id: 삭제할 알림 ID
        db: SQLAlchemy 동기 세션

    Raises:
        HTTPException 404: 알림을 찾을 수 없는 경우
        HTTPException 403: 다른 사용자의 알림을 삭제하려는 경우
    """
    alert = db.query(WatchlistAlert).filter(WatchlistAlert.id == alert_id).first()
    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="알림을 찾을 수 없습니다",
        )
    if alert.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="권한이 없습니다",
        )
    db.delete(alert)
    db.commit()
    logger.info("가격 알림 삭제 — alert_id=%d, user_id=%d", alert_id, user_id)


def evaluate_alert(alert: WatchlistAlert, current_price: float) -> bool:
    """알림 발동 조건 평가.

    direction=="above": 현재가 >= 목표가
    direction=="below": 현재가 <= 목표가

    Args:
        alert: 평가할 WatchlistAlert 인스턴스
        current_price: 현재 주가

    Returns:
        알림 발동 여부
    """
    if alert.direction == "above":
        return current_price >= alert.target_price
    elif alert.direction == "below":
        return current_price <= alert.target_price
    # 알 수 없는 direction은 발동하지 않음
    logger.warning("알 수 없는 direction 값 — alert_id=%d, direction=%s", alert.id, alert.direction)
    return False
