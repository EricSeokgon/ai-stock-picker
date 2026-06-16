"""알림 채널·유형별 수신 설정 REST API (SPEC-STOCK-025).

# @MX:SPEC: SPEC-STOCK-025 REQ-PREF-API-001, REQ-PREF-API-002, REQ-PREF-API-003, REQ-PREF-API-004
"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from stock_picker.auth.dependencies import get_current_user
from stock_picker.db.models import User
from stock_picker.db.session import get_session
from stock_picker.notifications.preferences import (
    SUPPORTED_ALERT_TYPES,
    get_preferences,
    upsert_preferences,
)

router = APIRouter(tags=["notification-preferences"])


class PreferenceItem(BaseModel):
    """알림 설정 항목 스키마."""

    model_config = ConfigDict(str_strip_whitespace=True)

    alert_type: str
    email_enabled: bool
    telegram_enabled: bool


class PreferencesResponse(BaseModel):
    """알림 설정 응답 스키마."""

    preferences: list[PreferenceItem]


class PreferencesUpdateRequest(BaseModel):
    """알림 설정 일괄 수정 요청 스키마."""

    preferences: list[PreferenceItem]


@router.get(
    "/preferences",
    response_model=PreferencesResponse,
    summary="알림 채널 설정 조회",
)
async def get_notification_preferences(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Any:
    """지원되는 7개 알림 유형 각각의 이메일·텔레그램 수신 설정을 반환.

    미설정 유형은 기본값(email_enabled=true, telegram_enabled=true)으로 응답.

    REQ-PREF-API-001, REQ-PREF-API-003
    """
    prefs = await get_preferences(session, current_user.id)
    return {"preferences": prefs}


@router.put(
    "/preferences",
    response_model=PreferencesResponse,
    summary="알림 채널 설정 일괄 저장",
)
async def update_notification_preferences(
    body: PreferencesUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Any:
    """알림 유형·채널 설정을 일괄 upsert하고 갱신된 전체 설정을 반환.

    - 지원하지 않는 alert_type 포함 시 422 반환 (REQ-PREF-API-004)
    - 기존 행이 있으면 갱신, 없으면 삽입 (REQ-PREF-005)

    REQ-PREF-API-002, REQ-PREF-API-003, REQ-PREF-API-004
    """
    items = [item.model_dump() for item in body.preferences]
    try:
        updated = await upsert_preferences(session, current_user.id, items)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    return {"preferences": updated}
