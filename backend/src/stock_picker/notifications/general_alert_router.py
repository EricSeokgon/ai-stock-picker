"""일반 알림 설정 REST API — 목표가·급등락 알림 CRUD + 점검 트리거 (SPEC-STOCK-020).

# @MX:ANCHOR: [AUTO] /alerts API 공개 경계 — main.py prefix="/alerts" 로 등록됨
# @MX:REASON: main.py, 스케줄러, 프론트엔드 api/alerts.ts 등 3개 이상 소비자
# @MX:SPEC: SPEC-STOCK-020 REQ-ALERT-003
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from stock_picker.auth.dependencies import get_current_user
from stock_picker.db.models import User
from stock_picker.db.session import get_session
from stock_picker.notifications.general_alert_service import (
    AlertCreate,
    AlertSchema,
    AlertUpdate,
    check_and_trigger_all_alerts,
    create_alert,
    delete_alert,
    get_alert,
    get_user_alerts,
    update_alert,
)

router = APIRouter(tags=["alerts"])


# ── CRUD 엔드포인트 ──────────────────────────────────────


@router.get("/", response_model=list[AlertSchema])
async def list_alerts(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[AlertSchema]:
    """사용자 알림 설정 목록 (REQ-ALERT-004)."""
    return await get_user_alerts(session=db, user_id=current_user.id)


@router.post("/", response_model=AlertSchema, status_code=status.HTTP_201_CREATED)
async def create_alert_endpoint(
    data: AlertCreate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AlertSchema:
    """신규 알림 설정 등록 (REQ-ALERT-005)."""
    return await create_alert(session=db, user_id=current_user.id, data=data)


@router.get("/{alert_id}", response_model=AlertSchema)
async def get_alert_endpoint(
    alert_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AlertSchema:
    """단일 알림 설정 조회 (REQ-ALERT-006)."""
    return await get_alert(session=db, alert_id=alert_id, user_id=current_user.id)


@router.put("/{alert_id}", response_model=AlertSchema)
async def update_alert_endpoint(
    alert_id: int,
    data: AlertUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AlertSchema:
    """알림 설정 수정 (REQ-ALERT-007)."""
    return await update_alert(
        session=db,
        alert_id=alert_id,
        user_id=current_user.id,
        data=data,
    )


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert_endpoint(
    alert_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """알림 설정 삭제 (REQ-ALERT-008)."""
    await delete_alert(session=db, alert_id=alert_id, user_id=current_user.id)


# ── 점검 트리거 ──────────────────────────────────────────


class CheckResult:
    """알림 점검 결과 응답."""

    def __init__(self, triggered: int) -> None:
        self.triggered = triggered


@router.post("/check", status_code=status.HTTP_200_OK)
async def trigger_check(
    db: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    """활성 알림 즉시 점검 트리거 — 무인증 (REQ-ALERT-009).

    스케줄러 외 수동 실행용 엔드포인트. 운영 환경에서는 API Gateway 레벨에서 접근 제한 권장.
    """
    triggered = await check_and_trigger_all_alerts(session=db)
    return {"triggered": triggered}
