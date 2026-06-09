# 가격 알림 라우터 — REST API 엔드포인트
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from stock_picker.auth.dependencies import get_current_user, get_db_session
from stock_picker.db.models import User
from stock_picker.notifications import alert_service
from stock_picker.notifications.schemas import WatchlistAlertCreate, WatchlistAlertResponse

router = APIRouter()


@router.post(
    "/watchlist/alerts",
    response_model=WatchlistAlertResponse,
    status_code=status.HTTP_201_CREATED,
    summary="가격 알림 등록",
)
def create_alert(
    data: WatchlistAlertCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> WatchlistAlertResponse:
    """관심종목 목표가 알림 등록 — 목표가 도달 시 텔레그램/이메일로 알림 발송"""
    alert = alert_service.create_alert(
        user_id=current_user.id, data=data, db=db
    )
    return WatchlistAlertResponse.model_validate(alert)


@router.get(
    "/watchlist/alerts",
    response_model=list[WatchlistAlertResponse],
    summary="가격 알림 목록 조회",
)
def list_alerts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[WatchlistAlertResponse]:
    """현재 사용자의 가격 알림 목록 반환"""
    alerts = alert_service.get_alerts(user_id=current_user.id, db=db)
    return [WatchlistAlertResponse.model_validate(a) for a in alerts]


@router.delete(
    "/watchlist/alerts/{alert_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="가격 알림 삭제",
)
def delete_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> None:
    """가격 알림 삭제 — 본인 알림만 삭제 가능"""
    alert_service.delete_alert(user_id=current_user.id, alert_id=alert_id, db=db)
