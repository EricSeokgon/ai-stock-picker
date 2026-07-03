# 알림 인박스 REST API — 인앱 알림 CRUD (SPEC-STOCK-013 M2)
# SPEC-STOCK-047: 딥링크 지원 (_resolve_links, NotificationSchema.link 추가)
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from stock_picker.auth.dependencies import get_current_user
from stock_picker.db.models import Notification, PortfolioShare, User
from stock_picker.db.session import get_session

# @MX:ANCHOR: [AUTO] 알림 인박스 API 진입점
# @MX:REASON: main.py, inbox_service, scheduler 등 여러 모듈에서 소비되는 공개 API 경계
# @MX:SPEC: SPEC-STOCK-013 REQ-NOTI-002~006

router = APIRouter(tags=["notifications"])

# 딥링크 산출 대상 알림 타입 (SPEC-STOCK-047 REQ-NLINK-001)
_PORTFOLIO_NOTIFICATION_TYPES = {"portfolio_like", "portfolio_comment"}
# krx_code → portfolio_id 파싱 패턴 (P{id} 규약, SPEC-STOCK-047 REQ-NLINK-005)
_KRX_PORTFOLIO_PATTERN = re.compile(r"^P(\d+)$")


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
    # SPEC-STOCK-047: 딥링크 필드 (nullable, 하위 호환)
    link: Optional[str] = None


class UnreadCountSchema(BaseModel):
    count: int


class MarkAllReadSchema(BaseModel):
    updated: int


def _to_schema(n: Notification, link: str | None = None) -> NotificationSchema:
    # @MX:NOTE: [AUTO] link 인자는 _resolve_links 결과를 주입받음 (SPEC-STOCK-047)
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
        link=link,
    )


# @MX:ANCHOR: [AUTO] 알림 딥링크 일괄 산출 헬퍼
# @MX:REASON: get_notifications(목록), mark_as_read(단건) 두 엔드포인트에서 공유
# @MX:SPEC: SPEC-STOCK-047 REQ-NLINK-001~007
async def _resolve_links(
    db: AsyncSession,
    notifications: list[Notification],
) -> dict[int, str | None]:
    """알림 목록에서 portfolio_like/portfolio_comment 알림의 딥링크를 일괄 산출한다.

    N+1 회피: 페이지 내 모든 포트폴리오 알림의 share를 단일 쿼리로 조회한다.
    반환: {notification_id → "/shared/{share_token}" or None}
    """
    # 포트폴리오 알림에서 portfolio_id 파싱
    noti_to_portfolio_id: dict[int, int] = {}
    for n in notifications:
        if n.type in _PORTFOLIO_NOTIFICATION_TYPES:
            m = _KRX_PORTFOLIO_PATTERN.match(n.krx_code)
            if m:
                noti_to_portfolio_id[n.id] = int(m.group(1))

    # 포트폴리오 알림 없으면 DB 조회 불필요 (REQ-NLINK-003)
    if not noti_to_portfolio_id:
        return {n.id: None for n in notifications}

    # 단일 배치 쿼리: 활성 공개 공유 조회 (REQ-NLINK-004, REQ-NLINK-007)
    portfolio_ids = set(noti_to_portfolio_id.values())
    result = await db.execute(
        select(PortfolioShare.portfolio_id, PortfolioShare.share_token).where(
            PortfolioShare.portfolio_id.in_(portfolio_ids),
            PortfolioShare.is_public.is_(True),
        )
    )
    share_map: dict[int, str] = {row.portfolio_id: row.share_token for row in result.all()}

    # 알림 id → 링크 매핑
    links: dict[int, str | None] = {}
    for n in notifications:
        if n.id in noti_to_portfolio_id:
            pid = noti_to_portfolio_id[n.id]
            token = share_map.get(pid)
            links[n.id] = f"/shared/{token}" if token else None
        else:
            links[n.id] = None
    return links


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
    # SPEC-STOCK-047: 딥링크 일괄 산출 (N+1 회피)
    links = await _resolve_links(db, list(rows))
    return [_to_schema(n, links.get(n.id)) for n in rows]


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
    # SPEC-STOCK-047: 단건 읽음 응답에도 링크 포함 (REQ-NLINK-006)
    links = await _resolve_links(db, [notification])
    return _to_schema(notification, links.get(notification.id))


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
