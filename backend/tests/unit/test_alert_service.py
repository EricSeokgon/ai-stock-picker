# 가격 알림 서비스 유닛 테스트 — mock DB 사용
from datetime import datetime
from unittest.mock import MagicMock, call

import pytest
from fastapi import HTTPException

from stock_picker.db.models import WatchlistAlert
from stock_picker.notifications import alert_service
from stock_picker.notifications.schemas import WatchlistAlertCreate


def _make_alert(
    id: int = 1,
    user_id: int = 1,
    krx_code: str = "005930",
    target_price: float = 80000.0,
    direction: str = "above",
    is_active: bool = True,
) -> WatchlistAlert:
    """테스트용 WatchlistAlert 인스턴스 생성"""
    alert = WatchlistAlert()
    alert.id = id
    alert.user_id = user_id
    alert.krx_code = krx_code
    alert.target_price = target_price
    alert.direction = direction
    alert.is_active = is_active
    alert.triggered_at = None
    alert.created_at = datetime(2024, 1, 1)
    return alert


class TestCreateAlert:
    """create_alert 테스트"""

    def test_creates_alert_and_returns(self):
        """알림 생성 후 WatchlistAlert 반환"""
        db = MagicMock()
        data = WatchlistAlertCreate(krx_code="005930", target_price=80000.0, direction="above")

        # db.refresh가 alert 객체를 그대로 반환하도록 설정
        created_alert = _make_alert()
        db.refresh.side_effect = lambda x: None

        # add → commit → refresh 순서
        result = alert_service.create_alert(user_id=1, data=data, db=db)

        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()

    def test_sets_correct_fields(self):
        """생성된 알림의 필드값 검증"""
        db = MagicMock()
        data = WatchlistAlertCreate(krx_code="000660", target_price=50000.0, direction="below")

        added_alert: WatchlistAlert | None = None

        def capture_add(obj):
            nonlocal added_alert
            added_alert = obj

        db.add.side_effect = capture_add

        alert_service.create_alert(user_id=2, data=data, db=db)

        assert added_alert is not None
        assert added_alert.user_id == 2
        assert added_alert.krx_code == "000660"
        assert added_alert.target_price == 50000.0
        assert added_alert.direction == "below"
        assert added_alert.is_active is True


class TestGetAlerts:
    """get_alerts 테스트"""

    def test_returns_alerts_for_user(self):
        """사용자의 알림 목록 반환"""
        db = MagicMock()
        alerts = [_make_alert(1, 1, "005930"), _make_alert(2, 1, "000660")]
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = alerts

        result = alert_service.get_alerts(user_id=1, db=db)

        assert len(result) == 2
        assert result[0].krx_code == "005930"

    def test_returns_empty_list_for_no_alerts(self):
        """알림 없으면 빈 목록 반환"""
        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        result = alert_service.get_alerts(user_id=99, db=db)

        assert result == []


class TestDeleteAlert:
    """delete_alert 테스트"""

    def test_deletes_existing_alert(self):
        """존재하는 알림 삭제"""
        db = MagicMock()
        alert = _make_alert(id=1, user_id=1)
        db.query.return_value.filter.return_value.first.return_value = alert

        alert_service.delete_alert(user_id=1, alert_id=1, db=db)

        db.delete.assert_called_once_with(alert)
        db.commit.assert_called_once()

    def test_raises_404_when_not_found(self):
        """알림 없으면 404 발생"""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            alert_service.delete_alert(user_id=1, alert_id=999, db=db)

        assert exc_info.value.status_code == 404

    def test_raises_403_when_wrong_user(self):
        """다른 사용자의 알림 삭제 시 403 발생"""
        db = MagicMock()
        # user_id=2 소유의 알림을 user_id=1이 삭제 시도
        alert = _make_alert(id=1, user_id=2)
        db.query.return_value.filter.return_value.first.return_value = alert

        with pytest.raises(HTTPException) as exc_info:
            alert_service.delete_alert(user_id=1, alert_id=1, db=db)

        assert exc_info.value.status_code == 403


class TestEvaluateAlert:
    """evaluate_alert 테스트"""

    def test_above_triggers_when_price_exceeds_target(self):
        """above 방향: 현재가 >= 목표가이면 True"""
        alert = _make_alert(target_price=80000.0, direction="above")

        assert alert_service.evaluate_alert(alert, 85000.0) is True

    def test_above_no_trigger_when_price_below_target(self):
        """above 방향: 현재가 < 목표가이면 False"""
        alert = _make_alert(target_price=80000.0, direction="above")

        assert alert_service.evaluate_alert(alert, 75000.0) is False

    def test_below_triggers_when_price_under_target(self):
        """below 방향: 현재가 <= 목표가이면 True"""
        alert = _make_alert(target_price=50000.0, direction="below")

        assert alert_service.evaluate_alert(alert, 45000.0) is True

    def test_below_no_trigger_when_price_above_target(self):
        """below 방향: 현재가 > 목표가이면 False"""
        alert = _make_alert(target_price=50000.0, direction="below")

        assert alert_service.evaluate_alert(alert, 55000.0) is False

    def test_edge_case_equal_to_target_above(self):
        """above 방향: 현재가 == 목표가이면 True (경계값)"""
        alert = _make_alert(target_price=80000.0, direction="above")

        assert alert_service.evaluate_alert(alert, 80000.0) is True

    def test_edge_case_equal_to_target_below(self):
        """below 방향: 현재가 == 목표가이면 True (경계값)"""
        alert = _make_alert(target_price=50000.0, direction="below")

        assert alert_service.evaluate_alert(alert, 50000.0) is True

    def test_unknown_direction_returns_false(self):
        """알 수 없는 direction은 False 반환"""
        alert = _make_alert(direction="sideways")

        assert alert_service.evaluate_alert(alert, 80000.0) is False
