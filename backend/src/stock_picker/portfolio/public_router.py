# SPEC-STOCK-042: 포트폴리오 공개 공유 & 피드 라우터 (인증 불필요)
# /shared/{token}, /shared/{token}/like, /feed 엔드포인트
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from stock_picker.auth.dependencies import get_current_user, get_db_session
from stock_picker.db.models import User
from stock_picker.portfolio import sharing
from stock_picker.portfolio.schemas import FeedResponse, LikeResponse, SharePublicResponse

# 공개 공유 조회/피드 라우터 (인증 불필요)
shared_router = APIRouter(tags=["sharing"])

# 좋아요 라우터 (인증 필요)
like_router = APIRouter(tags=["sharing"])


@shared_router.get(
    "/shared/{token}",
    response_model=SharePublicResponse,
    summary="공개 공유 포트폴리오 조회",
)
def get_shared_portfolio(
    token: str,
    db: Session = Depends(get_db_session),
) -> SharePublicResponse:
    """공개 공유 포트폴리오를 조회한다 (REQ-SHARE-002, 인증 불필요).

    - 조회 시 view_count 원자적 증가 (UPDATE SET view_count = view_count + 1).
    - is_public=False 또는 존재하지 않는 token → 404.
    """
    data = sharing.get_public_shared_portfolio(db, share_token=token)
    return SharePublicResponse(**data)


@like_router.post(
    "/shared/{token}/like",
    response_model=LikeResponse,
    summary="공유 포트폴리오 좋아요",
)
def like_shared_portfolio(
    token: str,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> LikeResponse:
    """공유 포트폴리오에 좋아요를 추가한다 (REQ-LIKE-001, 인증 필요).

    - 자신의 포트폴리오 좋아요 → 403.
    - 중복 좋아요 → 200 (멱등성, 오류 없음).
    - 미인증 → 401.
    """
    result = sharing.add_like(db, share_token=token, user_id=current_user.id)
    return LikeResponse(**result)


@like_router.delete(
    "/shared/{token}/like",
    status_code=204,
    summary="공유 포트폴리오 좋아요 취소",
)
def unlike_shared_portfolio(
    token: str,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """공유 포트폴리오 좋아요를 취소한다 (REQ-UNLIKE-001, 인증 필요).

    - 자신의 포트폴리오 취소 → 403.
    - 좋아요 없어도 204 (멱등성).
    - 비공개/미존재 공유 → 404.
    - 미인증 → 401.
    """
    sharing.remove_like(db, share_token=token, user_id=current_user.id)


@shared_router.get(
    "/feed",
    response_model=FeedResponse,
    summary="공개 공유 포트폴리오 피드",
)
def get_sharing_feed(
    sort: str = Query(default="recent", description="정렬 기준: recent (최신순) | likes (좋아요순)"),
    page: int = Query(default=1, ge=1, description="페이지 번호 (1-based)"),
    size: int = Query(default=20, ge=1, le=100, description="페이지 크기 (최대 100)"),
    db: Session = Depends(get_db_session),
) -> FeedResponse:
    """공개 공유 포트폴리오 피드를 조회한다 (REQ-FEED-001, 인증 불필요).

    - sort=recent: updated_at DESC (기본값).
    - sort=likes: like_count DESC.
    """
    result = sharing.get_feed(db, sort=sort, page=page, size=size)
    return FeedResponse(**result)
