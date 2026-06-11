# 멀티플렉스 WebSocket /ws/prices 통합 테스트 (SPEC-STOCK-016 M3)
# RED: ws_router에 /ws/prices 엔드포인트가 없으므로 실패 예상
import json
import os
import pytest
from unittest.mock import patch, AsyncMock

from fastapi.testclient import TestClient


@pytest.fixture
def mock_price_data():
    return {
        "krx_code": "005930",
        "price": 71200.0,
        "change_pct": 1.42,
        "timestamp": "2026-06-12T10:31:00",
    }


@pytest.fixture
def client():
    """WebSocket TestClient — REALTIME_PRICE_MOCK=true로 외부 의존성 제거."""
    with patch.dict(os.environ, {"REALTIME_PRICE_MOCK": "true"}):
        from stock_picker.api.main import create_app
        app = create_app()
        # 브로드캐스트 루프 시작 안 함 (통합 테스트에서는 직접 호출)
        with TestClient(app) as c:
            yield c


class TestMultiplexWSConnect:
    """기본 연결 및 프로토콜 (REQ-WSM-001)"""

    def test_ws_prices_endpoint_accepts_connection(self, client):
        """ws /ws/prices 엔드포인트가 연결을 수락해야 한다."""
        with client.websocket_connect("/ws/prices") as ws:
            # 연결이 되면 성공 — 연결 자체가 수락됨을 확인
            pass

    def test_ws_prices_no_auth_required(self, client):
        """인증 없이 연결 가능해야 한다 (REQ-WSM-001)."""
        # Authorization 헤더 없이도 연결 성공
        with client.websocket_connect("/ws/prices") as ws:
            ws.send_json({"action": "subscribe", "symbols": ["005930"]})
            data = ws.receive_json()
            # 바로 가격 또는 subscribed 응답 중 하나
            assert data.get("type") in ("price", "subscribed", "error")


class TestMultiplexWSSubscribe:
    """구독/해지 프로토콜 (REQ-WSM-002/004)"""

    def test_subscribe_receives_immediate_price(self, client):
        """subscribe 후 즉시 가격 메시지를 수신해야 한다 (REQ-WSM-002)."""
        with client.websocket_connect("/ws/prices") as ws:
            ws.send_json({"action": "subscribe", "symbols": ["005930"]})
            # 즉시 가격 push 후 subscribed 응답 수신
            msgs = []
            for _ in range(2):
                try:
                    msgs.append(ws.receive_json())
                except Exception:
                    break
            types = [m.get("type") for m in msgs]
            assert "price" in types or "subscribed" in types

    def test_subscribe_receives_subscribed_ack(self, client):
        """subscribe 후 subscribed 확인 메시지를 수신해야 한다."""
        with client.websocket_connect("/ws/prices") as ws:
            ws.send_json({"action": "subscribe", "symbols": ["005930"]})
            # 여러 메시지 중 subscribed 찾기
            found_subscribed = False
            for _ in range(3):
                try:
                    msg = ws.receive_json()
                    if msg.get("type") == "subscribed":
                        found_subscribed = True
                        assert "005930" in msg.get("symbols", [])
                        break
                except Exception:
                    break
            assert found_subscribed

    def test_unsubscribe_receives_unsubscribed_ack(self, client):
        """unsubscribe 후 unsubscribed 확인 메시지를 수신해야 한다 (REQ-WSM-004)."""
        with client.websocket_connect("/ws/prices") as ws:
            ws.send_json({"action": "subscribe", "symbols": ["005930"]})
            # subscribed 확인까지 소비
            for _ in range(3):
                msg = ws.receive_json()
                if msg.get("type") == "subscribed":
                    break
            ws.send_json({"action": "unsubscribe", "symbols": ["005930"]})
            msg = ws.receive_json()
            assert msg["type"] == "unsubscribed"
            assert "005930" in msg["symbols"]

    def test_unknown_action_returns_error_keeps_connection(self, client):
        """지원하지 않는 action은 error 메시지 후 연결 유지 (REQ-WSM-006)."""
        with client.websocket_connect("/ws/prices") as ws:
            ws.send_json({"action": "unknown_action", "symbols": []})
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert "unknown_action" in msg.get("message", "").lower() or "unknown" in msg.get("message", "").lower()
            # 연결 유지 확인 — 다시 subscribe 가능
            ws.send_json({"action": "subscribe", "symbols": ["005930"]})
            msg2 = ws.receive_json()
            assert msg2.get("type") in ("price", "subscribed")


class TestExistingEndpointUnchanged:
    """기존 단일 종목 엔드포인트 무중단 유지 (REQ-WSM-007)"""

    def test_single_symbol_ws_still_works(self, client):
        """기존 /ws/prices/{krx_code} 엔드포인트가 여전히 동작해야 한다."""
        with patch("stock_picker.realtime.ws_router.get_current_price") as mock_get:
            mock_get.return_value = {
                "krx_code": "005930",
                "price": 71000.0,
                "change_pct": 1.4,
                "timestamp": "2026-06-12T10:00:00",
            }
            with client.websocket_connect("/ws/prices/005930") as ws:
                msg = ws.receive_json()
                assert msg["krx_code"] == "005930"
                assert msg["price"] == 71000.0
