# 관심종목 라우터 — CRUD 엔드포인트
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from stock_picker.auth.dependencies import get_current_user, get_db_session
from stock_picker.db.models import User
from stock_picker.watchlist import service
from stock_picker.watchlist.schemas import WatchlistItemCreate, WatchlistItemResponse

router = APIRouter(tags=["watchlist"])


@router.get("", response_model=list[WatchlistItemResponse])
def list_watchlist(
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list:
    """관심종목 목록 조회 — 인증 필요"""
    return service.get_watchlist(user_id=current_user.id, db=db)


@router.post("", response_model=WatchlistItemResponse, status_code=status.HTTP_201_CREATED)
def add_watchlist(
    body: WatchlistItemCreate,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """관심종목 추가 — 중복 시 409"""
    return service.add_to_watchlist(user_id=current_user.id, krx_code=body.krx_code, db=db)


@router.delete("/{krx_code}", status_code=status.HTTP_204_NO_CONTENT)
def remove_watchlist(
    krx_code: str,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """관심종목 삭제 — 없으면 404"""
    service.remove_from_watchlist(user_id=current_user.id, krx_code=krx_code, db=db)
