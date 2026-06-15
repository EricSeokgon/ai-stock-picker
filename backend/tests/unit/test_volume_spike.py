# 거래량 급증 알림 + 장중 시간 게이팅 + 추천 점수 변화 유닛 테스트 (SPEC-STOCK-023)
from datetime import date, datetime
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

from stock_picker.notifications.general_alert_service import (
    _is_market_open,
    check_volume_spike,
)
from stock_picker.notifications.rec_change import check_rec_score_changes


# ── 장중 시간 게이팅 ────────────────────────────────────────────────────────


class TestIsMarketOpen:
    def test_open_at_start(self):
        """09:00 KST 개장 시각에 True"""
        kst = ZoneInfo("Asia/Seoul")
        now = datetime(2026, 6, 11, 9, 0, tzinfo=kst)
        assert _is_market_open(now) is True

    def test_open_midday(self):
        """12:00 KST 장중에 True"""
        kst = ZoneInfo("Asia/Seoul")
        now = datetime(2026, 6, 11, 12, 0, tzinfo=kst)
        assert _is_market_open(now) is True

    def test_open_at_close(self):
        """15:30 KST 종료 시각에 True (경계 포함)"""
        kst = ZoneInfo("Asia/Seoul")
        now = datetime(2026, 6, 11, 15, 30, tzinfo=kst)
        assert _is_market_open(now) is True

    def test_closed_before_open(self):
        """08:59 KST 장 전에 False"""
        kst = ZoneInfo("Asia/Seoul")
        now = datetime(2026, 6, 11, 8, 59, tzinfo=kst)
        assert _is_market_open(now) is False

    def test_closed_after_close(self):
        """15:31 KST 장 마감 후에 False"""
        kst = ZoneInfo("Asia/Seoul")
        now = datetime(2026, 6, 11, 15, 31, tzinfo=kst)
        assert _is_market_open(now) is False


# ── 거래량 급증 판정 ────────────────────────────────────────────────────────


def _make_alert(condition_value: float = 2.0, krx_code: str = "005930") -> MagicMock:
    alert = MagicMock()
    alert.condition_value = condition_value
    alert.krx_code = krx_code
    return alert


class TestCheckVolumeSpike:
    def test_triggers_when_ratio_exceeds_multiplier(self):
        """오늘 거래량이 30일 평균의 2배 이상이면 True"""
        alert = _make_alert(condition_value=2.0)
        volume_data = {"avg_volume": 1_000_000.0, "today_volume": 2_000_000}
        triggered, msg = check_volume_spike(alert, volume_data)
        assert triggered is True
        assert "005930" in msg
        assert "2,000,000" in msg

    def test_triggers_exactly_at_multiplier(self):
        """정확히 2배일 때도 True (경계 포함)"""
        alert = _make_alert(condition_value=2.0)
        volume_data = {"avg_volume": 500_000.0, "today_volume": 1_000_000}
        triggered, _ = check_volume_spike(alert, volume_data)
        assert triggered is True

    def test_no_trigger_below_multiplier(self):
        """오늘 거래량이 1.99배면 False"""
        alert = _make_alert(condition_value=2.0)
        volume_data = {"avg_volume": 1_000_000.0, "today_volume": 1_999_999}
        triggered, msg = check_volume_spike(alert, volume_data)
        assert triggered is False
        assert msg == ""

    def test_none_input_returns_false(self):
        """volume_data가 None이면 False"""
        alert = _make_alert()
        triggered, msg = check_volume_spike(alert, None)
        assert triggered is False
        assert msg == ""

    def test_zero_avg_volume_guard(self):
        """avg_volume이 0이면 ZeroDivision 없이 False"""
        alert = _make_alert()
        volume_data = {"avg_volume": 0.0, "today_volume": 100_000}
        triggered, msg = check_volume_spike(alert, volume_data)
        assert triggered is False
        assert msg == ""

    def test_custom_multiplier(self):
        """multiplier=3.0 설정 시 3배 이상만 True"""
        alert = _make_alert(condition_value=3.0)
        volume_data = {"avg_volume": 1_000_000.0, "today_volume": 2_999_999}
        triggered, _ = check_volume_spike(alert, volume_data)
        assert triggered is False

        volume_data2 = {"avg_volume": 1_000_000.0, "today_volume": 3_000_000}
        triggered2, _ = check_volume_spike(alert, volume_data2)
        assert triggered2 is True


# ── 추천 점수 변화 감지 ─────────────────────────────────────────────────────


class TestCheckRecScoreChanges:
    def test_exits_early_when_less_than_two_dates(self):
        """trade_date가 1개 이하면 알림 생성 없이 종료"""
        mock_db = MagicMock()
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
            check_rec_score_changes()

        mock_db.commit.assert_not_called()

    def test_creates_notification_for_delta_above_threshold(self):
        """|delta| >= 0.2인 종목 관심 사용자에게 알림 생성"""
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
                "stock_picker.notifications.rec_change._get_scores_for_date",
                side_effect=lambda db, d: (
                    {"005930": 0.9} if d == new_date else {"005930": 0.6}
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
            check_rec_score_changes()

        # delta=0.3 >= 0.2 → 사용자 2명에게 알림
        assert mock_insert.call_count == 2
        for c in mock_insert.call_args_list:
            assert c.kwargs.get("ntype") == "rec_score_change"
            assert c.kwargs.get("krx_code") == "005930"
            assert "+0.30" in c.kwargs.get("body", "")
        mock_db.commit.assert_called_once()

    def test_no_notification_for_small_delta(self):
        """|delta| < 0.2이면 알림 미생성"""
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
                "stock_picker.notifications.rec_change._get_scores_for_date",
                # delta = 0.1 (미만)
                side_effect=lambda db, d: (
                    {"005930": 0.8} if d == new_date else {"005930": 0.7}
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
            check_rec_score_changes()

        assert mock_insert.call_count == 0
        mock_db.commit.assert_called_once()

    def test_skips_codes_only_in_one_date(self):
        """한 날짜에만 존재하는 종목은 비교 대상 제외"""
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
                "stock_picker.notifications.rec_change._get_scores_for_date",
                side_effect=lambda db, d: (
                    # 신규 종목 000660은 prev_date에 없음 → 비교 제외
                    {"005930": 0.9, "000660": 0.8} if d == new_date
                    else {"005930": 0.6}
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
            check_rec_score_changes()

        # 005930만 비교 대상 (delta=0.3 ≥ 0.2) → 1건
        assert mock_insert.call_count == 1
        assert mock_insert.call_args.kwargs["krx_code"] == "005930"
        mock_db.commit.assert_called_once()

    def test_negative_delta_also_triggers(self):
        """점수가 하락해도 |delta| >= 0.2이면 알림 생성"""
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
                "stock_picker.notifications.rec_change._get_scores_for_date",
                side_effect=lambda db, d: (
                    {"005930": 0.5} if d == new_date else {"005930": 0.8}
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
            check_rec_score_changes()

        # delta=-0.3, |delta|=0.3 ≥ 0.2 → 알림 생성
        assert mock_insert.call_count == 1
        body = mock_insert.call_args.kwargs.get("body", "")
        assert "-0.30" in body or "−0.30" in body or "+0" not in body
