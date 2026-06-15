"""SPEC-STOCK-020: 일반 알림(목표가·급등락) 서비스 유닛 테스트.

# @MX:ANCHOR: [AUTO] 알림 서비스 핵심 로직 테스트 — 6개 이상 호출 지점
# @MX:REASON: check_alert_condition, create_notification_if_triggered 등 서비스 함수가 라우터·스케줄러에서 직접 참조됨
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

# ---- 모델/스키마 임포트 (아직 존재 안 함 → RED) ----
from stock_picker.notifications.general_alert_service import (
    AlertCreate,
    AlertUpdate,
    AlertSchema,
    check_target_price,
    check_surge_drop,
    build_notification_payload,
    create_alert,
    get_user_alerts,
    get_alert,
    update_alert,
    delete_alert,
    check_and_trigger_all_alerts,
)


# ======================================================================
# 스키마 / Pydantic 유효성 검사 테스트
# ======================================================================

class TestAlertCreate:
    """AlertCreate 스키마 유효성."""

    def test_target_price_valid(self) -> None:
        """목표가 알림 — 필수 필드 모두 있을 때 생성 성공."""
        payload = AlertCreate(
            krx_code="005930",
            stock_name="삼성전자",
            alert_type="target_price",
            condition_value=80000.0,
            condition_direction="above",
        )
        assert payload.krx_code == "005930"
        assert payload.alert_type == "target_price"

    def test_surge_drop_valid(self) -> None:
        """급등락 알림 — direction 없어도 기본 'either' 적용."""
        payload = AlertCreate(
            krx_code="069500",
            alert_type="surge_drop",
            condition_value=5.0,
        )
        assert payload.condition_direction == "either"

    def test_invalid_alert_type(self) -> None:
        """알 수 없는 alert_type 거부."""
        with pytest.raises(Exception):
            AlertCreate(
                krx_code="005930",
                alert_type="invalid_type",
                condition_value=100.0,
            )

    def test_condition_value_positive(self) -> None:
        """condition_value 음수 거부."""
        with pytest.raises(Exception):
            AlertCreate(
                krx_code="005930",
                alert_type="target_price",
                condition_value=-100.0,
                condition_direction="above",
            )


# ======================================================================
# 점검 로직 — check_target_price
# ======================================================================

class TestCheckTargetPrice:
    """목표가 도달 판정 로직."""

    def test_above_triggered(self) -> None:
        """현재가가 목표가 이상이면 발동."""
        alert = MagicMock()
        alert.condition_value = 70000.0
        alert.condition_direction = "above"
        price_data = {"close_price": 75000.0, "change_rate": 1.5}

        triggered, msg = check_target_price(alert, price_data)

        assert triggered is True
        assert "75000" in msg or "75,000" in msg

    def test_above_not_triggered(self) -> None:
        """현재가가 목표가 미달이면 미발동."""
        alert = MagicMock()
        alert.condition_value = 70000.0
        alert.condition_direction = "above"
        price_data = {"close_price": 65000.0, "change_rate": -1.0}

        triggered, msg = check_target_price(alert, price_data)

        assert triggered is False

    def test_below_triggered(self) -> None:
        """현재가가 하한가 이하면 발동."""
        alert = MagicMock()
        alert.condition_value = 50000.0
        alert.condition_direction = "below"
        price_data = {"close_price": 48000.0, "change_rate": -2.0}

        triggered, msg = check_target_price(alert, price_data)

        assert triggered is True

    def test_below_not_triggered(self) -> None:
        """현재가가 하한가 초과면 미발동."""
        alert = MagicMock()
        alert.condition_value = 50000.0
        alert.condition_direction = "below"
        price_data = {"close_price": 52000.0, "change_rate": 1.0}

        triggered, msg = check_target_price(alert, price_data)

        assert triggered is False

    def test_no_price_data_returns_false(self) -> None:
        """가격 데이터 없으면 미발동."""
        alert = MagicMock()
        alert.condition_value = 70000.0
        alert.condition_direction = "above"

        triggered, msg = check_target_price(alert, None)

        assert triggered is False
        assert msg == ""


# ======================================================================
# 점검 로직 — check_surge_drop
# ======================================================================

class TestCheckSurgeDrop:
    """급등락 판정 로직."""

    def test_surge_above_triggered(self) -> None:
        """급등(변화율 이상) 발동."""
        alert = MagicMock()
        alert.condition_value = 5.0
        alert.condition_direction = "above"
        price_data = {"close_price": 75000.0, "change_rate": 6.5}

        triggered, msg = check_surge_drop(alert, price_data)

        assert triggered is True
        assert "6.5" in msg or "6.50" in msg

    def test_drop_below_triggered(self) -> None:
        """급락(변화율 이하 음수) 발동."""
        alert = MagicMock()
        alert.condition_value = 5.0
        alert.condition_direction = "below"
        price_data = {"close_price": 48000.0, "change_rate": -7.0}

        triggered, msg = check_surge_drop(alert, price_data)

        assert triggered is True

    def test_either_surge_triggered(self) -> None:
        """either — 절댓값이 임계값 초과 시 발동."""
        alert = MagicMock()
        alert.condition_value = 5.0
        alert.condition_direction = "either"
        price_data = {"close_price": 75000.0, "change_rate": -6.0}

        triggered, msg = check_surge_drop(alert, price_data)

        assert triggered is True

    def test_either_not_triggered(self) -> None:
        """either — 절댓값이 임계값 이하 시 미발동."""
        alert = MagicMock()
        alert.condition_value = 5.0
        alert.condition_direction = "either"
        price_data = {"close_price": 75000.0, "change_rate": 3.0}

        triggered, msg = check_surge_drop(alert, price_data)

        assert triggered is False

    def test_no_price_data_returns_false(self) -> None:
        """가격 데이터 없으면 미발동."""
        alert = MagicMock()
        alert.condition_value = 5.0
        alert.condition_direction = "either"

        triggered, msg = check_surge_drop(alert, None)

        assert triggered is False
        assert msg == ""


# ======================================================================
# 알림 페이로드 빌더
# ======================================================================

class TestBuildNotificationPayload:
    """notifications 테이블 삽입용 딕셔너리 생성."""

    def test_target_price_payload_keys(self) -> None:
        """target_price 알림 — 필수 컬럼 존재."""
        alert = MagicMock()
        alert.user_id = 1
        alert.krx_code = "005930"
        alert.alert_type = "target_price"
        now = datetime.now(timezone.utc)

        payload = build_notification_payload(alert, "삼성전자 75,000원 도달", now)

        assert payload["user_id"] == 1
        assert payload["type"] == "target_price"
        assert payload["krx_code"] == "005930"
        assert "title" in payload
        assert "body" in payload
        assert payload["ref_date"] == now.date()
        assert payload.get("related_alert_id") is None  # watchlist_alerts 아님

    def test_surge_drop_payload_keys(self) -> None:
        """surge_drop 알림 — 필수 컬럼 존재."""
        alert = MagicMock()
        alert.user_id = 2
        alert.krx_code = "069500"
        alert.alert_type = "surge_drop"
        now = datetime.now(timezone.utc)

        payload = build_notification_payload(alert, "KODEX200 -6.0% 급락", now)

        assert payload["type"] == "surge_drop"
        assert payload["related_alert_id"] is None


# ======================================================================
# 비동기 서비스 함수 — CRUD (DB 모킹)
# ======================================================================

class TestCreateAlert:
    """create_alert — DB insert 확인."""

    @pytest.mark.asyncio
    async def test_create_alert_returns_schema(self) -> None:
        """알림 생성 시 AlertSchema 반환."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        fake_alert = MagicMock()
        fake_alert.id = 1
        fake_alert.user_id = 1
        fake_alert.krx_code = "005930"
        fake_alert.stock_name = "삼성전자"
        fake_alert.alert_type = "target_price"
        fake_alert.condition_value = 80000.0
        fake_alert.condition_direction = "above"
        fake_alert.is_active = True
        fake_alert.is_triggered = False
        fake_alert.triggered_at = None
        fake_alert.triggered_message = None
        fake_alert.created_at = datetime.now(timezone.utc)

        mock_result.scalar_one.return_value = fake_alert
        mock_session.execute.return_value = mock_result

        payload = AlertCreate(
            krx_code="005930",
            stock_name="삼성전자",
            alert_type="target_price",
            condition_value=80000.0,
            condition_direction="above",
        )

        result = await create_alert(session=mock_session, user_id=1, data=payload)

        assert mock_session.execute.called
        assert mock_session.commit.called
        assert isinstance(result, AlertSchema)
        assert result.krx_code == "005930"


class TestGetUserAlerts:
    """get_user_alerts — 사용자 알림 목록 조회."""

    @pytest.mark.asyncio
    async def test_returns_list(self) -> None:
        """목록 반환 시 AlertSchema 리스트."""
        mock_session = AsyncMock()
        mock_scalars = MagicMock()
        fake_alert = MagicMock()
        fake_alert.id = 1
        fake_alert.user_id = 1
        fake_alert.krx_code = "005930"
        fake_alert.stock_name = "삼성전자"
        fake_alert.alert_type = "target_price"
        fake_alert.condition_value = 80000.0
        fake_alert.condition_direction = "above"
        fake_alert.is_active = True
        fake_alert.is_triggered = False
        fake_alert.triggered_at = None
        fake_alert.triggered_message = None
        fake_alert.created_at = datetime.now(timezone.utc)

        mock_scalars.all.return_value = [fake_alert]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        results = await get_user_alerts(session=mock_session, user_id=1)

        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0].krx_code == "005930"


class TestDeleteAlert:
    """delete_alert — 소유권 검증 후 삭제."""

    @pytest.mark.asyncio
    async def test_delete_own_alert(self) -> None:
        """본인 알림 삭제 성공."""
        mock_session = AsyncMock()
        fake_alert = MagicMock()
        fake_alert.id = 1
        fake_alert.user_id = 1

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = fake_alert
        mock_session.execute.return_value = mock_result

        await delete_alert(session=mock_session, alert_id=1, user_id=1)

        mock_session.delete.assert_called_once_with(fake_alert)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_other_user_alert_raises(self) -> None:
        """타인 알림 삭제 시 404/403 예외."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with pytest.raises(Exception):
            await delete_alert(session=mock_session, alert_id=99, user_id=1)


# ======================================================================
# check_and_trigger_all_alerts — 통합 점검 루프
# ======================================================================

class TestCheckAndTriggerAllAlerts:
    """check_and_trigger_all_alerts — 전체 활성 알림 점검."""

    @pytest.mark.asyncio
    async def test_triggers_target_price_and_creates_notification(self) -> None:
        """목표가 도달 알림 → notifications 테이블 삽입 시도."""
        mock_session = AsyncMock()

        fake_alert = MagicMock()
        fake_alert.id = 1
        fake_alert.user_id = 1
        fake_alert.krx_code = "005930"
        fake_alert.stock_name = "삼성전자"
        fake_alert.alert_type = "target_price"
        fake_alert.condition_value = 70000.0
        fake_alert.condition_direction = "above"
        fake_alert.is_active = True
        fake_alert.is_triggered = False

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [fake_alert]
        mock_list_result = MagicMock()
        mock_list_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_list_result

        price_data = {"close_price": 75000.0, "change_rate": 2.0}

        with (
            patch(
                "stock_picker.notifications.general_alert_service.get_stock_price_data",
                new=AsyncMock(return_value=price_data),
            ),
            patch(
                "stock_picker.notifications.general_alert_service._is_market_open",
                return_value=True,
            ),
        ):
            triggered_count = await check_and_trigger_all_alerts(session=mock_session)

        assert triggered_count >= 1

    @pytest.mark.asyncio
    async def test_no_price_data_skips_gracefully(self) -> None:
        """가격 조회 실패 시 예외 없이 건너뜀."""
        mock_session = AsyncMock()

        fake_alert = MagicMock()
        fake_alert.id = 2
        fake_alert.user_id = 1
        fake_alert.krx_code = "999999"
        fake_alert.alert_type = "target_price"
        fake_alert.condition_value = 10000.0
        fake_alert.condition_direction = "above"
        fake_alert.is_active = True
        fake_alert.is_triggered = False

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [fake_alert]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        with patch(
            "stock_picker.notifications.general_alert_service.get_stock_price_data",
            new=AsyncMock(return_value=None),
        ):
            triggered_count = await check_and_trigger_all_alerts(session=mock_session)

        assert triggered_count == 0

    @pytest.mark.asyncio
    async def test_already_triggered_alert_skipped(self) -> None:
        """이미 발동된 알림은 재발동하지 않음."""
        mock_session = AsyncMock()

        fake_alert = MagicMock()
        fake_alert.id = 3
        fake_alert.user_id = 1
        fake_alert.krx_code = "005930"
        fake_alert.alert_type = "target_price"
        fake_alert.condition_value = 70000.0
        fake_alert.condition_direction = "above"
        fake_alert.is_active = True
        fake_alert.is_triggered = True  # 이미 발동

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [fake_alert]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        with patch(
            "stock_picker.notifications.general_alert_service.get_stock_price_data",
            new=AsyncMock(return_value={"close_price": 80000.0, "change_rate": 5.0}),
        ):
            triggered_count = await check_and_trigger_all_alerts(session=mock_session)

        assert triggered_count == 0
