# SPEC-STOCK-042: 포트폴리오 공유 & 소셜 서비스 모듈
# SPEC-STOCK-043: unlike, portfolio_like 알림, share_view_stats 확장
# SPEC-STOCK-046: 공유 포트폴리오 댓글 (add_comment, list_comments, remove_comment)
# @MX:ANCHOR: [AUTO] 포트폴리오 공유 서비스 진입점
# @MX:REASON: router.py(소유자 엔드포인트), 공개 라우터(shared/feed), stats 엔드포인트에서 참조 (fan_in >= 3)
# @MX:SPEC: SPEC-STOCK-042, SPEC-STOCK-043, SPEC-STOCK-046
import secrets
from datetime import date, datetime, timedelta  # noqa: TCH003
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from stock_picker.db.models import (
    Notification,
    Portfolio,
    PortfolioComment,
    PortfolioLike,
    PortfolioShare,
    ShareViewStat,
    User,
)

_KST = ZoneInfo("Asia/Seoul")


def _get_portfolio_or_404(db: Session, portfolio_id: int, user_id: int) -> Portfolio:
    """소유자 확인 후 Portfolio 반환. 비소유자 → 404.

    비소유자에게 존재 여부를 노출하지 않기 위해 403 대신 404 반환.
    """
    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
        .first()
    )
    if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="포트폴리오를 찾을 수 없습니다",
        )
    return portfolio


def create_or_reactivate_share(
    db: Session, portfolio_id: int, user_id: int
) -> PortfolioShare:
    """포트폴리오 공유 생성 또는 재활성화 (멱등성 보장).

    # @MX:NOTE: [AUTO] 멱등성 규칙: 기존 레코드 존재 시 is_public=True 업데이트 후 재사용.
    # 존재하지 않으면 새 token 생성 및 레코드 INSERT.

    규칙:
    - 기존 레코드(is_public 무관) 존재 → is_public=True 설정 후 반환
    - 기존 레코드 없음 → 새 share_token 생성 후 INSERT
    """
    # 소유자 확인
    _get_portfolio_or_404(db, portfolio_id, user_id)

    # 기존 공유 레코드 조회
    share = (
        db.query(PortfolioShare)
        .filter(PortfolioShare.portfolio_id == portfolio_id)
        .first()
    )

    if share is not None:
        # 기존 레코드 재활성화 (is_public=True)
        share.is_public = True
        db.commit()
        db.refresh(share)
        return share

    # 새 공유 레코드 생성
    token = secrets.token_urlsafe(16)
    share_url = f"/shared/{token}"
    share = PortfolioShare(
        portfolio_id=portfolio_id,
        share_token=token,
        share_url=share_url,
        is_public=True,
        view_count=0,
    )
    db.add(share)
    db.commit()
    db.refresh(share)
    return share


def deactivate_share(db: Session, portfolio_id: int, user_id: int) -> None:
    """포트폴리오 공유 비활성화 (소프트 삭제).

    is_public=False로 설정 (token/counts 보존).
    비소유자 → 404.
    공유 레코드 없어도 에러 없음 (이미 비활성화 상태로 간주).
    """
    # 소유자 확인
    _get_portfolio_or_404(db, portfolio_id, user_id)

    share = (
        db.query(PortfolioShare)
        .filter(PortfolioShare.portfolio_id == portfolio_id)
        .first()
    )

    if share is None:
        # 공유 레코드 없음 → 이미 비활성화 상태
        return

    share.is_public = False
    db.commit()


def get_share_status(db: Session, portfolio_id: int, user_id: int) -> PortfolioShare:
    """소유자 공유 상태 조회.

    비소유자 → 404.
    공유 레코드 없음 → 404.
    """
    # 소유자 확인
    _get_portfolio_or_404(db, portfolio_id, user_id)

    share = (
        db.query(PortfolioShare)
        .filter(PortfolioShare.portfolio_id == portfolio_id)
        .first()
    )

    if share is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="공유 정보가 없습니다. 먼저 공유를 활성화하세요",
        )

    return share


def get_public_shared_portfolio(db: Session, share_token: str) -> dict[str, Any]:
    """공개 공유 포트폴리오 조회 + 조회수 원자적 증가.

    # @MX:NOTE: [AUTO] view_count 원자적 증가: UPDATE SET view_count = view_count + 1
    # 동시 요청에서 race condition 방지 (SELECT + UPDATE 분리하면 갱신 손실 발생).

    is_public=False 또는 존재하지 않는 token → 404.
    """
    share = (
        db.query(PortfolioShare)
        .filter(
            PortfolioShare.share_token == share_token,
            PortfolioShare.is_public.is_(True),
        )
        .first()
    )

    if share is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="공유 포트폴리오를 찾을 수 없습니다",
        )

    # view_count 원자적 증가
    db.execute(
        text(
            "UPDATE portfolio_shares SET view_count = view_count + 1 WHERE id = :id"
        ),
        {"id": share.id},
    )

    # share_view_stats 일별 집계 upsert (KST 기준)
    # @MX:NOTE: [AUTO] ON CONFLICT DO UPDATE — 동시 요청에서 count 손실 없이 원자적 증가
    kst_today: date = datetime.now(tz=_KST).date()
    db.execute(
        text(
            """
            INSERT INTO share_view_stats (share_id, stat_date, view_count)
            VALUES (:share_id, :stat_date, 1)
            ON CONFLICT (share_id, stat_date)
            DO UPDATE SET view_count = share_view_stats.view_count + 1
            """
        ),
        {"share_id": share.id, "stat_date": kst_today},
    )

    db.commit()
    db.refresh(share)

    # like_count 파생 계산
    like_count = (
        db.query(func.count(PortfolioLike.id))
        .filter(PortfolioLike.share_id == share.id)
        .scalar()
    ) or 0

    # portfolio 이름 조회
    portfolio = db.query(Portfolio).filter(Portfolio.id == share.portfolio_id).first()
    portfolio_name = portfolio.name if portfolio else ""

    return {
        "share_token": share.share_token,
        "share_url": share.share_url,
        "portfolio_id": share.portfolio_id,
        "portfolio_name": portfolio_name,
        "view_count": share.view_count,
        "like_count": like_count,
    }


def add_like(db: Session, share_token: str, user_id: int) -> dict[str, int]:
    """좋아요 추가 (멱등성 보장).

    # @MX:NOTE: [AUTO] 중복 좋아요: try/except IntegrityError 패턴 사용.
    # DB 레벨 UniqueConstraint (share_id, user_id) 위반 시 silently 무시.

    규칙:
    - 소유자 좋아요 → 403
    - 공유 레코드 없음/비공개 → 404
    - 중복 좋아요 → 200 (멱등성, 오류 없음)
    """
    share = (
        db.query(PortfolioShare)
        .filter(
            PortfolioShare.share_token == share_token,
            PortfolioShare.is_public.is_(True),
        )
        .first()
    )

    if share is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="공유 포트폴리오를 찾을 수 없습니다",
        )

    # 소유자 좋아요 금지 — portfolio.user_id 조회
    portfolio = db.query(Portfolio).filter(Portfolio.id == share.portfolio_id).first()
    if portfolio is not None and portfolio.user_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="자신의 포트폴리오에는 좋아요할 수 없습니다",
        )

    # 좋아요 INSERT — 중복 시 IntegrityError 무시 (멱등성)
    # @MX:NOTE: [AUTO] 신규 좋아요만 알림 삽입 — IntegrityError 경로에서는 알림 미생성
    is_new_like = True
    try:
        like = PortfolioLike(share_id=share.id, user_id=user_id)
        db.add(like)
        db.commit()
    except IntegrityError:
        db.rollback()
        is_new_like = False

    # 신규 좋아요 → 소유자에게 portfolio_like 알림 삽입 (UNIQUE constraint safe)
    if is_new_like and portfolio is not None:
        liker: User | None = db.query(User).filter(User.id == user_id).first()
        liker_name = liker.username if liker is not None else "사용자"
        kst_today: date = datetime.now(tz=_KST).date()
        notification = Notification(
            user_id=portfolio.user_id,
            type="portfolio_like",
            krx_code=f"P{portfolio.id}",
            title=f"{liker_name}님이 좋아요를 눌렀습니다",
            body=None,
            is_read=False,
            ref_date=kst_today,
        )
        db.add(notification)
        try:
            db.commit()
        except IntegrityError:
            # UNIQUE(user_id, type, krx_code, ref_date) 충돌 — 오늘 이미 알림 존재
            db.rollback()

    # like_count 파생 계산
    like_count = (
        db.query(func.count(PortfolioLike.id))
        .filter(PortfolioLike.share_id == share.id)
        .scalar()
    ) or 0

    return {"like_count": like_count}


def remove_like(db: Session, share_token: str, user_id: int) -> None:
    """좋아요 취소 (멱등성 보장).

    # @MX:NOTE: [AUTO] 멱등성 규칙: 좋아요 없으면 무시 (204, 404 아님).
    # 소유자 취소 시 403. 비공개/미존재 공유 시 404.

    규칙:
    - 비공개/미존재 share → 404
    - 소유자 취소 → 403
    - 좋아요 없음 → 204 (멱등, 오류 없음)
    - 좋아요 존재 → DELETE + 204
    """
    share = (
        db.query(PortfolioShare)
        .filter(
            PortfolioShare.share_token == share_token,
            PortfolioShare.is_public.is_(True),
        )
        .first()
    )

    if share is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="공유 포트폴리오를 찾을 수 없습니다",
        )

    # 소유자 취소 금지
    portfolio = db.query(Portfolio).filter(Portfolio.id == share.portfolio_id).first()
    if portfolio is not None and portfolio.user_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="자신의 포트폴리오에는 좋아요를 취소할 수 없습니다",
        )

    # 좋아요 조회 및 삭제 (없으면 멱등)
    like = (
        db.query(PortfolioLike)
        .filter(
            PortfolioLike.share_id == share.id,
            PortfolioLike.user_id == user_id,
        )
        .first()
    )
    if like is not None:
        db.delete(like)
        db.commit()


def get_share_stats(
    db: Session, portfolio_id: int, user_id: int
) -> dict[str, Any]:
    """포트폴리오 공유 일별 조회수 통계 조회 (최근 7일, 0-fill).

    # @MX:NOTE: [AUTO] 7일 윈도우 오름차순 반환 — 누락 날짜는 0으로 채움.
    # @MX:SPEC: SPEC-STOCK-043 REQ-STAT-002

    규칙:
    - 비소유자 → 404
    - 공유 레코드 없음 → 200, 7개 항목 모두 view_count=0
    - 오름차순 날짜 정렬
    """
    # 소유자 확인
    _get_portfolio_or_404(db, portfolio_id, user_id)

    # 공유 레코드 조회 (없어도 오류 없음 → 0-fill 반환)
    share = (
        db.query(PortfolioShare)
        .filter(PortfolioShare.portfolio_id == portfolio_id)
        .first()
    )

    # 최근 7일 날짜 윈도우 (KST 기준)
    today = datetime.now(tz=_KST).date()
    date_window = [today - timedelta(days=i) for i in range(6, -1, -1)]  # 오름차순

    if share is None:
        # 공유 레코드 없음 → 모두 0
        stats = [{"date": d.isoformat(), "view_count": 0} for d in date_window]
        return {"stats": stats}

    # DB에서 최근 7일 통계 조회
    start_date = date_window[0]
    end_date = date_window[-1]
    rows = (
        db.query(ShareViewStat)
        .filter(
            ShareViewStat.share_id == share.id,
            ShareViewStat.stat_date >= start_date,
            ShareViewStat.stat_date <= end_date,
        )
        .all()
    )

    # stat_date → view_count 맵 구성
    stat_map: dict[date, int] = {row.stat_date: row.view_count for row in rows}

    # 0-fill 오름차순 반환
    stats = [
        {"date": d.isoformat(), "view_count": stat_map.get(d, 0)}
        for d in date_window
    ]
    return {"stats": stats}


def get_feed(
    db: Session,
    sort: str = "recent",
    page: int = 1,
    size: int = 20,
    q: str | None = None,
) -> dict[str, Any]:
    """공개 공유 피드 조회 (REQ-FEED-001 / REQ-FEED-002 ~ REQ-FEED-007).

    sort: "recent" (updated_at DESC, 기본값) | "likes" (like_count DESC) | "trending" (7일 조회 합계 DESC).
    q:    포트폴리오 이름 부분 검색 (대소문자 무시, 빈 값 → 무시).
    page: 1-based. size: 최대 100으로 캡.
    미지원 sort 값 → recent 폴백 (REQ-FEED-006).
    """
    # @MX:NOTE: [AUTO] size 상한 100 — 과도한 페이지 크기 방지
    size = min(size, 100)
    offset = (page - 1) * size

    # like_count 서브쿼리
    like_count_subq = (
        db.query(
            PortfolioLike.share_id,
            func.count(PortfolioLike.id).label("like_count"),
        )
        .group_by(PortfolioLike.share_id)
        .subquery()
    )

    base_query = (
        db.query(PortfolioShare, Portfolio, like_count_subq.c.like_count)
        .join(Portfolio, Portfolio.id == PortfolioShare.portfolio_id)
        .outerjoin(
            like_count_subq, like_count_subq.c.share_id == PortfolioShare.id
        )
        .filter(PortfolioShare.is_public.is_(True))
    )

    # 이름 검색 필터 — q 비어있으면 무시 (REQ-FEED-005)
    if q and q.strip():
        base_query = base_query.filter(Portfolio.name.ilike(f"%{q}%"))

    # 정렬
    if sort == "likes":
        base_query = base_query.order_by(
            func.coalesce(like_count_subq.c.like_count, 0).desc()
        )
    elif sort == "trending":
        # @MX:NOTE: [AUTO] 최근 7일(KST 기준) 조회수 합계 DESC — 0 조회는 마지막 (REQ-FEED-002/003)
        start_date = datetime.now(tz=_KST).date() - timedelta(days=6)
        trending_subq = (
            db.query(
                ShareViewStat.share_id,
                func.sum(ShareViewStat.view_count).label("recent_views"),
            )
            .filter(ShareViewStat.stat_date >= start_date)
            .group_by(ShareViewStat.share_id)
            .subquery()
        )
        base_query = (
            base_query
            .outerjoin(trending_subq, trending_subq.c.share_id == PortfolioShare.id)
            .order_by(func.coalesce(trending_subq.c.recent_views, 0).desc())
        )
    else:
        # 기본: 최신순 (updated_at DESC) — 미지원 sort 도 이 분기 (REQ-FEED-006)
        base_query = base_query.order_by(PortfolioShare.updated_at.desc())

    total = base_query.count()
    rows = base_query.offset(offset).limit(size).all()

    items = [
        {
            "share_token": share.share_token,
            "share_url": share.share_url,
            "portfolio_id": share.portfolio_id,
            "portfolio_name": portfolio.name,
            "view_count": share.view_count,
            "like_count": int(like_cnt) if like_cnt is not None else 0,
        }
        for share, portfolio, like_cnt in rows
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
    }


# ── SPEC-STOCK-046: 공유 포트폴리오 댓글 서비스 ────────────────────────────────


def _get_public_share_or_404(db: Session, share_token: str) -> PortfolioShare:
    """공개 공유 레코드 조회. 비공개/미존재 → 404."""
    share = (
        db.query(PortfolioShare)
        .filter(
            PortfolioShare.share_token == share_token,
            PortfolioShare.is_public.is_(True),
        )
        .first()
    )
    if share is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="공유 포트폴리오를 찾을 수 없습니다",
        )
    return share


def add_comment(db: Session, share_token: str, user_id: int, content: str) -> dict[str, Any]:
    """공유 포트폴리오에 댓글을 작성한다 (SPEC-STOCK-046 REQ-CMT-001).

    - 비공개/미존재 토큰 → 404
    - 비소유자 댓글 작성 시 portfolio_comment 알림 생성 (일별 중복 억제)
    - 결과: CommentItem 구조의 dict 반환
    """
    share = _get_public_share_or_404(db, share_token)

    # 댓글 저장
    comment = PortfolioComment(
        share_id=share.id,
        user_id=user_id,
        content=content.strip(),
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    # 작성자 정보 조회 (username 포함)
    commenter: User | None = db.query(User).filter(User.id == user_id).first()
    commenter_name = commenter.username if commenter is not None else "사용자"

    # 포트폴리오 소유자 조회 (알림 대상)
    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.id == share.portfolio_id)
        .first()
    )

    # 비소유자가 댓글을 남긴 경우에만 알림 생성
    if portfolio is not None and portfolio.user_id != user_id:
        kst_today: date = datetime.now(tz=_KST).date()
        notification = Notification(
            user_id=portfolio.user_id,
            type="portfolio_comment",
            krx_code=f"P{portfolio.id}",
            title=f"{commenter_name}님이 댓글을 남겼습니다",
            body=content[:100] if len(content) > 100 else content,
            is_read=False,
            ref_date=kst_today,
        )
        db.add(notification)
        try:
            db.commit()
        except IntegrityError:
            # 당일 동일 알림 중복 — 무시 (멱등성)
            db.rollback()

    return {
        "id": comment.id,
        "user_id": comment.user_id,
        "username": commenter_name,
        "content": comment.content,
        "created_at": comment.created_at,
    }


def list_comments(
    db: Session,
    share_token: str,
    page: int = 1,
    size: int = 20,
) -> dict[str, Any]:
    """공유 포트폴리오 댓글 목록 조회 (SPEC-STOCK-046 REQ-CMT-005).

    - 비공개/미존재 토큰 → 404
    - 최신순 정렬 (created_at DESC)
    - 페이지네이션 (최대 size=100)
    """
    share = _get_public_share_or_404(db, share_token)
    size = min(size, 100)

    # 전체 댓글 수 (페이지네이션 total)
    total: int = (
        db.query(PortfolioComment)
        .filter(PortfolioComment.share_id == share.id)
        .count()
    )

    # 최신순 조회 (created_at DESC) + User join (username)
    rows = (
        db.query(PortfolioComment, User)
        .join(User, PortfolioComment.user_id == User.id)
        .filter(PortfolioComment.share_id == share.id)
        .order_by(PortfolioComment.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    items = [
        {
            "id": c.id,
            "user_id": c.user_id,
            "username": u.username,
            "content": c.content,
            "created_at": c.created_at,
        }
        for c, u in rows
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
    }


def remove_comment(db: Session, share_token: str, comment_id: int, user_id: int) -> None:
    """공유 포트폴리오 댓글을 삭제한다 (SPEC-STOCK-046 REQ-CMT-007).

    - 비공개/미존재 토큰 → 404
    - 존재하지 않는 댓글 → 404
    - 삭제 권한: 댓글 작성자 OR 포트폴리오 소유자 (모더레이션)
    - 권한 없음 → 403
    """
    share = _get_public_share_or_404(db, share_token)

    # 댓글 조회
    comment: PortfolioComment | None = (
        db.query(PortfolioComment)
        .filter(
            PortfolioComment.id == comment_id,
            PortfolioComment.share_id == share.id,
        )
        .first()
    )
    if comment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="댓글을 찾을 수 없습니다",
        )

    # 포트폴리오 소유자 확인 (모더레이션 권한)
    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.id == share.portfolio_id)
        .first()
    )
    is_author = comment.user_id == user_id
    is_owner = portfolio is not None and portfolio.user_id == user_id

    if not (is_author or is_owner):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="삭제 권한이 없습니다",
        )

    db.delete(comment)
    db.commit()
