# SPEC-STOCK-042: 포트폴리오 공유 & 소셜 서비스 모듈
# @MX:ANCHOR: [AUTO] 포트폴리오 공유 서비스 진입점
# @MX:REASON: router.py(소유자 엔드포인트), 공개 라우터(shared/feed)에서 참조 (fan_in >= 3)
# @MX:SPEC: SPEC-STOCK-042
import secrets
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from stock_picker.db.models import Portfolio, PortfolioLike, PortfolioShare


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
    try:
        like = PortfolioLike(share_id=share.id, user_id=user_id)
        db.add(like)
        db.commit()
    except IntegrityError:
        db.rollback()

    # like_count 파생 계산
    like_count = (
        db.query(func.count(PortfolioLike.id))
        .filter(PortfolioLike.share_id == share.id)
        .scalar()
    ) or 0

    return {"like_count": like_count}


def get_feed(
    db: Session,
    sort: str = "recent",
    page: int = 1,
    size: int = 20,
) -> dict[str, Any]:
    """공개 공유 피드 조회 (REQ-FEED-001).

    sort: "recent" (updated_at DESC, 기본값) | "likes" (like_count DESC).
    page: 1-based. size: 최대 100으로 캡.
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

    # 정렬
    if sort == "likes":
        base_query = base_query.order_by(
            func.coalesce(like_count_subq.c.like_count, 0).desc()
        )
    else:
        # 기본: 최신순 (updated_at DESC)
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
