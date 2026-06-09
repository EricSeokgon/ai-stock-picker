# 관심종목 서비스 레이어 — CRUD
import logging

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from stock_picker.db.models import WatchlistItem

logger = logging.getLogger(__name__)


def get_watchlist(user_id: int, db: Session) -> list[WatchlistItem]:
    """사용자의 관심종목 목록 조회.

    # @MX:ANCHOR: [AUTO] 관심종목 조회 단일 진입점
    # @MX:REASON: router.py(GET), 테스트 코드에서 3회 이상 참조
    """
    return (
        db.query(WatchlistItem)
        .filter(WatchlistItem.user_id == user_id)
        .order_by(WatchlistItem.added_at.desc())
        .all()
    )


def add_to_watchlist(user_id: int, krx_code: str, db: Session) -> WatchlistItem:
    """관심종목 추가.

    중복 추가 시 409 Conflict 반환.
    """
    item = WatchlistItem(user_id=user_id, krx_code=krx_code)
    db.add(item)
    try:
        db.commit()
        db.refresh(item)
        return item
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"종목 {krx_code}은(는) 이미 관심종목에 등록되어 있습니다",
        )


def remove_from_watchlist(user_id: int, krx_code: str, db: Session) -> None:
    """관심종목 삭제.

    해당 종목이 없으면 404 Not Found 반환.
    """
    item = (
        db.query(WatchlistItem)
        .filter(
            WatchlistItem.user_id == user_id,
            WatchlistItem.krx_code == krx_code,
        )
        .first()
    )
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"관심종목에서 {krx_code}을(를) 찾을 수 없습니다",
        )
    db.delete(item)
    db.commit()
