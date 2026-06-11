# 가격 브로드캐스트 단위 테스트 (SPEC-STOCK-016 M2/M6)
# RED: price_broadcast 모듈이 없으므로 실패 예상
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call


@pytest.fixture
def manager():
    from stock_picker.realtime.connection_manager import ConnectionManager
    return ConnectionManager()


def make_ws() -> MagicMock:
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


class TestMockMode:
    """REALTIME_PRICE_MOCK 모킹 모드 (REQ-RT-002)"""

    def test_get_mock_price_returns_deterministic_value(self):
        """mock 모드에서 동일 심볼은 항상 동일한 가격을 반환해야 한다."""
        from stock_picker.realtime.price_broadcast import get_mock_price
        result1 = get_mock_price("005930")
        result2 = get_mock_price("005930")
        # price와 change_pct는 결정론적으로 동일해야 함 (timestamp 제외)
        assert result1["krx_code"] == result2["krx_code"] == "005930"
        assert result1["price"] == result2["price"]
        assert result1["change_pct"] == result2["change_pct"]
        assert result1["price"] > 0
        assert "timestamp" in result1

    def test_get_mock_price_different_symbols_may_differ(self):
        """다른 심볼은 서로 다른 가격을 가질 수 있다."""
        from stock_picker.realtime.price_broadcast import get_mock_price
        r1 = get_mock_price("005930")
        r2 = get_mock_price("000660")
        # 최소한 krx_code는 달라야 함
        assert r1["krx_code"] != r2["krx_code"]

    @pytest.mark.asyncio
    async def test_get_price_or_mock_uses_mock_when_env_set(self):
        """REALTIME_PRICE_MOCK=true 환경변수 설정 시 mock 가격 반환."""
        from stock_picker.realtime.price_broadcast import get_price_or_mock
        with patch.dict(os.environ, {"REALTIME_PRICE_MOCK": "true"}):
            result = await get_price_or_mock("005930")
        assert result is not None
        assert result["krx_code"] == "005930"

    @pytest.mark.asyncio
    async def test_get_price_or_mock_calls_real_fn_when_env_not_set(self):
        """REALTIME_PRICE_MOCK 미설정 시 실제 get_current_price를 호출한다."""
        from stock_picker.realtime.price_broadcast import get_price_or_mock
        mock_result = {"krx_code": "005930", "price": 70000.0, "change_pct": 1.0, "timestamp": "2026-06-12T10:00:00"}
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("REALTIME_PRICE_MOCK", None)
            with patch("stock_picker.realtime.price_broadcast.get_current_price", return_value=mock_result) as mock_fn:
                result = await get_price_or_mock("005930")
        mock_fn.assert_called_once_with("005930")
        assert result == mock_result


class TestBroadcastOnce:
    """단일 폴링 사이클 브로드캐스트 (REQ-SUB-003)"""

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all_subscribers(self, manager):
        """구독 중인 모든 연결에 가격 메시지를 전송해야 한다."""
        from stock_picker.realtime.price_broadcast import broadcast_prices_once
        ws1, ws2 = make_ws(), make_ws()
        await manager.connect(ws1)
        await manager.connect(ws2)
        manager.subscribe(ws1, ["005930"])
        manager.subscribe(ws2, ["005930"])

        mock_price = {"krx_code": "005930", "price": 71000.0, "change_pct": 1.4, "timestamp": "2026-06-12T10:00:00"}
        with patch("stock_picker.realtime.price_broadcast.get_price_or_mock", return_value=mock_price):
            with patch("stock_picker.realtime.price_broadcast.evaluate_alerts"):
                await broadcast_prices_once(manager, db_session_factory=None)

        # 두 연결 모두 수신해야 함
        ws1.send_json.assert_awaited()
        ws2.send_json.assert_awaited()

    @pytest.mark.asyncio
    async def test_broadcast_message_has_type_price(self, manager):
        """브로드캐스트 메시지의 type 필드가 'price'이어야 한다."""
        from stock_picker.realtime.price_broadcast import broadcast_prices_once
        ws = make_ws()
        await manager.connect(ws)
        manager.subscribe(ws, ["005930"])

        mock_price = {"krx_code": "005930", "price": 71000.0, "change_pct": 1.4, "timestamp": "2026-06-12T10:00:00"}
        with patch("stock_picker.realtime.price_broadcast.get_price_or_mock", return_value=mock_price):
            with patch("stock_picker.realtime.price_broadcast.evaluate_alerts"):
                await broadcast_prices_once(manager, db_session_factory=None)

        sent_data = ws.send_json.call_args[0][0]
        assert sent_data["type"] == "price"
        assert sent_data["krx_code"] == "005930"

    @pytest.mark.asyncio
    async def test_broadcast_skips_symbol_on_price_fetch_error(self, manager):
        """심볼 가격 조회 실패 시 해당 심볼을 스킵하고 다른 심볼은 정상 처리 (REQ-RT-003)."""
        from stock_picker.realtime.price_broadcast import broadcast_prices_once
        ws = make_ws()
        await manager.connect(ws)
        manager.subscribe(ws, ["FAIL001", "005930"])

        def side_effect(sym):
            if sym == "FAIL001":
                raise RuntimeError("조회 실패")
            return {"krx_code": sym, "price": 71000.0, "change_pct": 1.4, "timestamp": "2026-06-12T10:00:00"}

        import asyncio
        async def async_side_effect(sym):
            return side_effect(sym)

        with patch("stock_picker.realtime.price_broadcast.get_price_or_mock", side_effect=async_side_effect):
            with patch("stock_picker.realtime.price_broadcast.evaluate_alerts"):
                await broadcast_prices_once(manager, db_session_factory=None)

        # 성공한 심볼만 전송
        ws.send_json.assert_awaited_once()
        sent_data = ws.send_json.call_args[0][0]
        assert sent_data["krx_code"] == "005930"

    @pytest.mark.asyncio
    async def test_broadcast_no_symbols_does_nothing(self, manager):
        """구독 심볼 없으면 전송 없어야 한다 (REQ-SUB-005)."""
        from stock_picker.realtime.price_broadcast import broadcast_prices_once
        ws = make_ws()
        await manager.connect(ws)
        # 아무것도 구독 안 함

        with patch("stock_picker.realtime.price_broadcast.get_price_or_mock") as mock_fn:
            await broadcast_prices_once(manager, db_session_factory=None)

        mock_fn.assert_not_called()
        ws.send_json.assert_not_awaited()


class TestEvaluateAlerts:
    """가격 알림 평가 (REQ-ALERT-001~004)"""

    @pytest.mark.asyncio
    async def test_evaluate_alerts_above_triggers_when_price_above_target(self):
        """direction=above일 때 가격이 목표가 이상이면 알림이 발동되어야 한다."""
        from stock_picker.realtime.price_broadcast import evaluate_alerts

        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.user_id = 10
        mock_alert.krx_code = "005930"
        mock_alert.target_price = 70000.0
        mock_alert.direction = "above"
        mock_alert.is_active = True
        mock_alert.triggered_at = None

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_alert]
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("stock_picker.realtime.price_broadcast._insert_alert_notification_async") as mock_insert:
            mock_insert.return_value = None
            await evaluate_alerts("005930", 75000.0, mock_db)

        mock_insert.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_evaluate_alerts_below_triggers_when_price_below_target(self):
        """direction=below일 때 가격이 목표가 이하이면 알림이 발동되어야 한다."""
        from stock_picker.realtime.price_broadcast import evaluate_alerts

        mock_alert = MagicMock()
        mock_alert.id = 2
        mock_alert.user_id = 10
        mock_alert.krx_code = "005930"
        mock_alert.target_price = 80000.0
        mock_alert.direction = "below"
        mock_alert.is_active = True
        mock_alert.triggered_at = None

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_alert]
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("stock_picker.realtime.price_broadcast._insert_alert_notification_async") as mock_insert:
            mock_insert.return_value = None
            await evaluate_alerts("005930", 75000.0, mock_db)

        mock_insert.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_evaluate_alerts_does_not_trigger_when_condition_not_met(self):
        """조건 미충족 시 알림이 발동되지 않아야 한다."""
        from stock_picker.realtime.price_broadcast import evaluate_alerts

        mock_alert = MagicMock()
        mock_alert.id = 3
        mock_alert.user_id = 10
        mock_alert.krx_code = "005930"
        mock_alert.target_price = 80000.0
        mock_alert.direction = "above"
        mock_alert.is_active = True
        mock_alert.triggered_at = None

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_alert]
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("stock_picker.realtime.price_broadcast._insert_alert_notification_async") as mock_insert:
            await evaluate_alerts("005930", 75000.0, mock_db)  # 75000 < 80000 → 미발동

        mock_insert.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_evaluate_alerts_inactive_alert_not_triggered(self):
        """이미 비활성화된 알림은 재발동되지 않아야 한다 (REQ-ALERT-004)."""
        from stock_picker.realtime.price_broadcast import evaluate_alerts

        mock_alert = MagicMock()
        mock_alert.id = 4
        mock_alert.user_id = 10
        mock_alert.krx_code = "005930"
        mock_alert.target_price = 70000.0
        mock_alert.direction = "above"
        mock_alert.is_active = False  # 이미 비활성

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_alert]
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("stock_picker.realtime.price_broadcast._insert_alert_notification_async") as mock_insert:
            await evaluate_alerts("005930", 75000.0, mock_db)

        mock_insert.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_evaluate_alerts_notification_failure_does_not_propagate(self):
        """알림 생성 실패가 예외를 전파하지 않아야 한다 (REQ-ALERT-005)."""
        from stock_picker.realtime.price_broadcast import evaluate_alerts

        mock_alert = MagicMock()
        mock_alert.id = 5
        mock_alert.user_id = 10
        mock_alert.krx_code = "005930"
        mock_alert.target_price = 70000.0
        mock_alert.direction = "above"
        mock_alert.is_active = True
        mock_alert.triggered_at = None

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_alert]
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("stock_picker.realtime.price_broadcast._insert_alert_notification_async", side_effect=Exception("DB 오류")):
            # 예외 전파 없어야 함
            await evaluate_alerts("005930", 75000.0, mock_db)
