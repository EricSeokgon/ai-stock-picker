# 이메일 구독 라우터 — REST API 엔드포인트
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from stock_picker.auth.dependencies import get_current_user, get_db_session
from stock_picker.db.models import User
from stock_picker.notifications import email_service
from stock_picker.notifications.schemas import EmailSubscriptionCreate, EmailSubscriptionResponse

router = APIRouter()


@router.post(
    "/email",
    response_model=EmailSubscriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="이메일 구독 등록/재활성화",
)
def subscribe_email(
    data: EmailSubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> EmailSubscriptionResponse:
    """이메일 구독 등록 — 기존 구독 있으면 이메일 갱신 및 재활성화"""
    sub = email_service.subscribe_email(
        user_id=current_user.id, email=data.email, db=db
    )
    return EmailSubscriptionResponse.model_validate(sub)


@router.delete(
    "/email",
    status_code=status.HTTP_200_OK,
    summary="이메일 구독 해지",
)
def unsubscribe_email(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> dict[str, str]:
    """이메일 구독 해지"""
    email_service.unsubscribe_email(user_id=current_user.id, db=db)
    return {"message": "구독이 해지되었습니다."}
