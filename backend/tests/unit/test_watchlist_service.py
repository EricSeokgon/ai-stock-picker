# 관심종목 서비스 유닛 테스트 — mock DB
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from stock_picker.db.models import WatchlistItem
from stock_picker.watchlist import service


def _make_item(
    id: int = 1, user_id: int = 1, krx_code: str = "005930"
) -> WatchlistItem:
    """테스트용 WatchlistItem 인스턴스 생성"""
    item = WatchlistItem()
    item.id = id
    item.user_id = user_id
    item.krx_code = krx_code
    item.added_at = datetime(2024, 1, 1)
    return item


class TestGetWatchlist:
    """get_watchlist 테스트"""

    def test_returns_items_for_user(self):
        """사용자 관심종목 목록 반환"""
        db = MagicMock()
        items = [_make_item(1, 1, "005930"), _make_item(2, 1, "000660")]

        # 쿼리 체인 mock
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = items

        result = service.get_watchlist(user_id=1, db=db)

        assert len(result) == 2
        assert result[0].krx_code == "005930"

    def test_returns_empty_list_when_no_items(self):
        """관심종목 없으면 빈 목록 반환"""
        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        result = service.get_watchlist(user_id=99, db=db)

        assert result == []


class TestAddToWatchlist:
    """add_to_watchlist 테스트"""

    def test_adds_item_successfully(self):
        """정상 추가 — WatchlistItem 반환"""
        db = MagicMock()

        def mock_refresh(item):
            item.id = 1

        db.refresh.side_effect = mock_refresh

        result = service.add_to_watchlist(user_id=1, krx_code="005930", db=db)

        db.add.assert_called_once()
        db.commit.assert_called_once()
        assert result.krx_code == "005930"
        assert result.user_id == 1

    def test_duplicate_raises_409(self):
        """중복 추가 시 409 Conflict"""
        db = MagicMock()
        db.commit.side_effect = IntegrityError("uq_watchlist_user_krx", {}, None)

        with pytest.raises(HTTPException) as exc_info:
            service.add_to_watchlist(user_id=1, krx_code="005930", db=db)

        assert exc_info.value.status_code == 409
        db.rollback.assert_called_once()


class TestRemoveFromWatchlist:
    """remove_from_watchlist 테스트"""

    def test_removes_existing_item(self):
        """정상 삭제"""
        db = MagicMock()
        item = _make_item()
        db.query.return_value.filter.return_value.first.return_value = item

        service.remove_from_watchlist(user_id=1, krx_code="005930", db=db)

        db.delete.assert_called_once_with(item)
        db.commit.assert_called_once()

    def test_not_found_raises_404(self):
        """없는 종목 삭제 시 404 Not Found"""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            service.remove_from_watchlist(user_id=1, krx_code="NONE99", db=db)

        assert exc_info.value.status_code == 404
        db.delete.assert_not_called()
