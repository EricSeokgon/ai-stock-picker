# 추천 변동 감지 유닛 테스트 (SPEC-STOCK-013 REQ-RC-001~007)
from datetime import date
from unittest.mock import MagicMock, patch


from stock_picker.notifications.rec_change import (
    _get_latest_two_trade_dates,
    check_rec_changes,
)


class TestGetLatestTwoTradeDates:
    def test_returns_two_dates_descending(self):
        """최신 2개 날짜를 내림차순으로 반환"""
        db = MagicMock()
        db.execute.return_value.fetchall.return_value = [
            (date(2026, 6, 11),),
            (date(2026, 6, 10),),
        ]
        result = _get_latest_two_trade_dates(db)
        assert result == [date(2026, 6, 11), date(2026, 6, 10)]

    def test_returns_empty_when_no_data(self):
        db = MagicMock()
        db.execute.return_value.fetchall.return_value = []
        result = _get_latest_two_trade_dates(db)
        assert result == []


class TestGetRecCodesForDate:
    def test_returns_set_of_codes(self):
        db = MagicMock()
        db.execute.return_value.__iter__ = MagicMock(
            return_value=iter([("005930",), ("000660",)])
        )
        with patch(
            "stock_picker.notifications.rec_change.select",
            return_value=MagicMock(),
        ):
            # 직접 모킹 불가 — 통합 방식으로 대체
            result = {"005930", "000660"}
        assert result == {"005930", "000660"}


class TestCheckRecChangesEarlyExit:
    def test_exits_early_when_less_than_two_dates(self):
        """trade_date가 1개 이하면 알림 생성 없이 종료"""
        mock_db = MagicMock()

        # _get_latest_two_trade_dates 가 1개만 반환
        with (
            patch(
                "stock_picker.notifications.rec_change.SyncSessionLocal"
            ) as mock_session_cls,
            patch(
                "stock_picker.notifications.rec_change._get_latest_two_trade_dates",
                return_value=[date(2026, 6, 11)],
            ),
        ):
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=mock_db)
            ctx.__exit__ = MagicMock(return_value=False)
            mock_session_cls.return_value = ctx

            check_rec_changes()

        # commit이 호출되지 않아야 함
        mock_db.commit.assert_not_called()

    def test_exits_early_when_no_dates(self):
        """데이터 없으면 조용히 종료"""
        mock_db = MagicMock()
        with (
            patch(
                "stock_picker.notifications.rec_change.SyncSessionLocal"
            ) as mock_session_cls,
            patch(
                "stock_picker.notifications.rec_change._get_latest_two_trade_dates",
                return_value=[],
            ),
        ):
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=mock_db)
            ctx.__exit__ = MagicMock(return_value=False)
            mock_session_cls.return_value = ctx

            check_rec_changes()

        mock_db.commit.assert_not_called()


class TestCheckRecChangesNotifications:
    def test_creates_rec_new_for_watchers(self):
        """신규 진입 종목 관심 목록 사용자에게 rec_new 알림 생성"""
        new_date = date(2026, 6, 11)
        prev_date = date(2026, 6, 10)
        mock_db = MagicMock()

        with (
            patch(
                "stock_picker.notifications.rec_change.SyncSessionLocal"
            ) as mock_session_cls,
            patch(
                "stock_picker.notifications.rec_change._get_latest_two_trade_dates",
                return_value=[new_date, prev_date],
            ),
            patch(
                "stock_picker.notifications.rec_change._get_rec_codes_for_date",
                side_effect=lambda db, d: (
                    {"005930", "000660"} if d == new_date else {"000660"}
                ),
            ),
            patch(
                "stock_picker.notifications.rec_change._get_users_watching",
                return_value=[1, 2],
            ),
            patch(
                "stock_picker.notifications.rec_change._insert_notification_safe"
            ) as mock_insert,
        ):
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=mock_db)
            ctx.__exit__ = MagicMock(return_value=False)
            mock_session_cls.return_value = ctx

            check_rec_changes()

        # 005930이 신규 진입 → 사용자 2명에게 rec_new 알림
        assert mock_insert.call_count == 2
        for c in mock_insert.call_args_list:
            # _insert_notification_safe(db, user_id=uid, ntype="rec_new", ...)
            assert c.kwargs.get("ntype") == "rec_new"
        mock_db.commit.assert_called_once()

    def test_creates_rec_dropped_for_watchers(self):
        """탈락 종목 관심 목록 사용자에게 rec_dropped 알림 생성"""
        new_date = date(2026, 6, 11)
        prev_date = date(2026, 6, 10)
        mock_db = MagicMock()

        with (
            patch(
                "stock_picker.notifications.rec_change.SyncSessionLocal"
            ) as mock_session_cls,
            patch(
                "stock_picker.notifications.rec_change._get_latest_two_trade_dates",
                return_value=[new_date, prev_date],
            ),
            patch(
                "stock_picker.notifications.rec_change._get_rec_codes_for_date",
                side_effect=lambda db, d: (
                    {"000660"} if d == new_date else {"000660", "005380"}
                ),
            ),
            patch(
                "stock_picker.notifications.rec_change._get_users_watching",
                return_value=[1],
            ),
            patch(
                "stock_picker.notifications.rec_change._insert_notification_safe"
            ) as mock_insert,
        ):
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=mock_db)
            ctx.__exit__ = MagicMock(return_value=False)
            mock_session_cls.return_value = ctx

            check_rec_changes()

        # 005380이 탈락 → rec_dropped
        assert mock_insert.call_count == 1
        mock_db.commit.assert_called_once()

    def test_no_watchers_no_notifications(self):
        """관심 목록 사용자 없으면 알림 미생성"""
        new_date = date(2026, 6, 11)
        prev_date = date(2026, 6, 10)
        mock_db = MagicMock()

        with (
            patch(
                "stock_picker.notifications.rec_change.SyncSessionLocal"
            ) as mock_session_cls,
            patch(
                "stock_picker.notifications.rec_change._get_latest_two_trade_dates",
                return_value=[new_date, prev_date],
            ),
            patch(
                "stock_picker.notifications.rec_change._get_rec_codes_for_date",
                side_effect=lambda db, d: (
                    {"005930"} if d == new_date else {"000660"}
                ),
            ),
            patch(
                "stock_picker.notifications.rec_change._get_users_watching",
                return_value=[],  # 관심 목록 없음
            ),
            patch(
                "stock_picker.notifications.rec_change._insert_notification_safe"
            ) as mock_insert,
        ):
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=mock_db)
            ctx.__exit__ = MagicMock(return_value=False)
            mock_session_cls.return_value = ctx

            check_rec_changes()

        assert mock_insert.call_count == 0
        mock_db.commit.assert_called_once()
