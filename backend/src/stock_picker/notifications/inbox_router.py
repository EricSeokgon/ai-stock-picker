# 알림 인박스 REST API — 인앱 알림 CRUD (SPEC-STOCK-013 M2)
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from stock_picker.auth.dependencies import get_current_user
from stock_picker.db.models import Notification, User
from stock_picker.db.session import get_session

# @MX:ANCHOR: [AUTO] 알림 인박스 API 진입점
# @MX:REASON: main.py, inbox_service, scheduler 등 여러 모듈에서 소비되는 공개 API 경계
# @MX:SPEC: SPEC-STOCK-013 REQ-NOTI-002~006

router = APIRouter(tags=["notifications"])


class NotificationSchema(BaseModel):
    """알림 인박스 응답 스키마"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    krx_code: str
    title: str
    body: Optional[str]
    is_read: bool
    ref_date: Optional[str]  # ISO date string
    related_alert_id: Optional[int]
    created_at: datetime
    read_at: Optional[datetime]


class UnreadCountSchema(BaseModel):
    count: int


class MarkAllReadSchema(BaseModel):
    updated: int


def _to_schema(n: Notification) -> NotificationSchema:
    return NotificationSchema(
        id=n.id,
        type=n.type,
        krx_code=n.krx_code,
        title=n.title,
        body=n.body,
        is_read=n.is_read,
        ref_date=n.ref_date.isoformat() if n.ref_date else None,
        related_alert_id=n.related_alert_id,
        created_at=n.created_at,
        read_at=n.read_at,
    )


@router.get("/", response_model=list[NotificationSchema])
async def get_notifications(
    unread_only: bool = Query(False, description="미읽음 알림만 조회"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[NotificationSchema]:
    """인박스 알림 목록 — 최신순 정렬 (REQ-NOTI-002)"""
    stmt = (
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [_to_schema(n) for n in rows]


@router.get("/unread-count", response_model=UnreadCountSchema)
async def get_unread_count(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> UnreadCountSchema:
    """미읽음 알림 개수 (REQ-NOTI-003)"""
    from sqlalchemy import func

    stmt = (
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == current_user.id)
        .where(Notification.is_read.is_(False))
    )
    result = await db.execute(stmt)
    count = result.scalar_one()
    return UnreadCountSchema(count=count)


@router.patch("/{notification_id}/read", response_model=NotificationSchema)
async def mark_as_read(
    notification_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> NotificationSchema:
    """단건 읽음 처리 (REQ-NOTI-004)"""
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notification = result.scalar_one_or_none()
    if notification is None:
        raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다.")
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(notification)
    return _to_schema(notification)


@router.patch("/read-all", response_model=MarkAllReadSchema)
async def mark_all_read(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> MarkAllReadSchema:
    """전체 읽음 처리 (REQ-NOTI-005)"""
    now = datetime.now(timezone.utc)
    stmt = (
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True, read_at=now)
        .returning(Notification.id)
    )
    result = await db.execute(stmt)
    updated = len(result.fetchall())
    await db.commit()
    return MarkAllReadSchema(updated=updated)
