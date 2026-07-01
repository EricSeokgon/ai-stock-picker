# SPEC-STOCK-042: 포트폴리오 공개 공유 & 피드 라우터 (인증 불필요)
# SPEC-STOCK-046: 공유 포트폴리오 댓글 엔드포인트 추가
# /shared/{token}, /shared/{token}/like, /shared/{token}/comments, /feed 엔드포인트
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from stock_picker.auth.dependencies import get_current_user, get_db_session
from stock_picker.db.models import User
from stock_picker.portfolio import sharing
from stock_picker.portfolio.schemas import (
    CommentCreate,
    CommentItem,
    CommentListResponse,
    FeedResponse,
    LikeResponse,
    SharePublicResponse,
)

# 공개 공유 조회/피드 라우터 (인증 불필요)
shared_router = APIRouter(tags=["sharing"])

# 좋아요 라우터 (인증 필요)
like_router = APIRouter(tags=["sharing"])

# 댓글 라우터 (쓰기/삭제는 인증 필요, 읽기는 불필요)
comment_router = APIRouter(tags=["sharing"])


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
    sort: str = Query(
        default="recent",
        description="정렬 기준: recent (최신순) | likes (좋아요순) | trending (7일 조회 합계순)",
    ),
    page: int = Query(default=1, ge=1, description="페이지 번호 (1-based)"),
    size: int = Query(default=20, ge=1, le=100, description="페이지 크기 (최대 100)"),
    q: str | None = Query(
        default=None,
        description="포트폴리오 이름 부분 검색 (대소문자 무시, 빈 값 → 무시)",
    ),
    db: Session = Depends(get_db_session),
) -> FeedResponse:
    """공개 공유 포트폴리오 피드를 조회한다 (REQ-FEED-001, 인증 불필요).

    - sort=recent: updated_at DESC (기본값).
    - sort=likes: like_count DESC.
    - sort=trending: 최근 7일 조회수 합계 DESC.
    - q: 포트폴리오 이름 부분 검색 (ILIKE).
    """
    result = sharing.get_feed(db, sort=sort, page=page, size=size, q=q)
    return FeedResponse(**result)


# ── SPEC-STOCK-046: 공유 포트폴리오 댓글 엔드포인트 ───────────────────────────


@shared_router.get(
    "/shared/{token}/comments",
    response_model=CommentListResponse,
    summary="공유 포트폴리오 댓글 목록 조회 (인증 불필요)",
)
def get_comments(
    token: str,
    page: int = Query(default=1, ge=1, description="페이지 번호 (1-based)"),
    size: int = Query(default=20, ge=1, le=100, description="페이지 크기 (최대 100)"),
    db: Session = Depends(get_db_session),
) -> CommentListResponse:
    """공유 포트폴리오 댓글 목록을 조회한다 (SPEC-STOCK-046 REQ-CMT-005, 인증 불필요).

    - 최신순 정렬 (created_at DESC).
    - 비공개/미존재 토큰 → 404.
    """
    result = sharing.list_comments(db, share_token=token, page=page, size=size)
    return CommentListResponse(**result)


@comment_router.post(
    "/shared/{token}/comments",
    response_model=CommentItem,
    status_code=status.HTTP_201_CREATED,
    summary="공유 포트폴리오 댓글 작성 (인증 필요)",
)
def add_comment(
    token: str,
    body: CommentCreate,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> CommentItem:
    """공유 포트폴리오에 댓글을 작성한다 (SPEC-STOCK-046 REQ-CMT-001, 인증 필요).

    - 비공개/미존재 토큰 → 404.
    - 미인증 → 401.
    - 내용 공백 → 422 (Pydantic str_strip_whitespace).
    """
    result = sharing.add_comment(
        db,
        share_token=token,
        user_id=current_user.id,
        content=body.content,
        parent_comment_id=body.parent_comment_id,
    )
    return CommentItem(**result)


@comment_router.delete(
    "/shared/{token}/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="공유 포트폴리오 댓글 삭제 (인증 필요)",
)
def delete_comment(
    token: str,
    comment_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """공유 포트폴리오 댓글을 삭제한다 (SPEC-STOCK-046 REQ-CMT-007, 인증 필요).

    - 댓글 작성자 또는 포트폴리오 소유자만 삭제 가능.
    - 비공개/미존재 토큰 → 404.
    - 존재하지 않는 댓글 → 404.
    - 권한 없음 → 403.
    - 미인증 → 401.
    """
    sharing.remove_comment(
        db,
        share_token=token,
        comment_id=comment_id,
        user_id=current_user.id,
    )
