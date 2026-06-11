# ConnectionManager 단위 테스트 (SPEC-STOCK-016 M1)
# RED: ConnectionManager가 존재하지 않으므로 모든 테스트 실패 예상
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def manager():
    """ConnectionManager 인스턴스 생성."""
    from stock_picker.realtime.connection_manager import ConnectionManager
    return ConnectionManager()


def make_ws() -> MagicMock:
    """가짜 WebSocket 객체 생성."""
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


class TestConnectionManagerConnect:
    """연결/해제 기본 동작"""

    @pytest.mark.asyncio
    async def test_connect_accepts_websocket(self, manager):
        """connect()가 WebSocket.accept()를 호출해야 한다."""
        ws = make_ws()
        await manager.connect(ws)
        ws.accept.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_connected_ws_tracked_in_registry(self, manager):
        """connect() 후 해당 연결이 레지스트리에 등록되어야 한다."""
        ws = make_ws()
        await manager.connect(ws)
        # 연결 후에는 빈 구독 집합으로 등록
        assert ws in manager._conn_symbols

    def test_disconnect_removes_connection(self, manager):
        """disconnect() 후 연결이 레지스트리에서 제거되어야 한다."""
        ws = make_ws()
        manager._conn_symbols[ws] = set()
        manager.disconnect(ws)
        assert ws not in manager._conn_symbols

    def test_disconnect_unknown_ws_does_not_raise(self, manager):
        """미등록 연결 해제 시 예외가 발생하지 않아야 한다."""
        ws = make_ws()
        manager.disconnect(ws)  # 예외 없어야 함


class TestConnectionManagerSubscribe:
    """구독/해지 레지스트리 동작"""

    @pytest.mark.asyncio
    async def test_subscribe_adds_symbols_to_connection(self, manager):
        """subscribe()가 해당 연결에 심볼을 등록해야 한다."""
        ws = make_ws()
        await manager.connect(ws)
        manager.subscribe(ws, ["005930", "000660"])
        assert "005930" in manager._conn_symbols[ws]
        assert "000660" in manager._conn_symbols[ws]

    @pytest.mark.asyncio
    async def test_subscribe_updates_reverse_index(self, manager):
        """subscribe()가 심볼→연결 역색인을 갱신해야 한다 (REQ-SUB-002)."""
        ws = make_ws()
        await manager.connect(ws)
        manager.subscribe(ws, ["005930"])
        assert ws in manager._symbol_conns.get("005930", set())

    @pytest.mark.asyncio
    async def test_subscribe_multiple_connections_same_symbol(self, manager):
        """동일 심볼을 여러 연결이 구독할 수 있어야 한다 (REQ-SUB-003)."""
        ws1, ws2 = make_ws(), make_ws()
        await manager.connect(ws1)
        await manager.connect(ws2)
        manager.subscribe(ws1, ["005930"])
        manager.subscribe(ws2, ["005930"])
        assert len(manager._symbol_conns["005930"]) == 2

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_symbols(self, manager):
        """unsubscribe()가 해당 연결에서 심볼을 제거해야 한다."""
        ws = make_ws()
        await manager.connect(ws)
        manager.subscribe(ws, ["005930", "000660"])
        manager.unsubscribe(ws, ["005930"])
        assert "005930" not in manager._conn_symbols[ws]
        assert "000660" in manager._conn_symbols[ws]

    @pytest.mark.asyncio
    async def test_unsubscribe_updates_reverse_index(self, manager):
        """unsubscribe() 후 역색인에서도 제거되어야 한다."""
        ws = make_ws()
        await manager.connect(ws)
        manager.subscribe(ws, ["005930"])
        manager.unsubscribe(ws, ["005930"])
        assert ws not in manager._symbol_conns.get("005930", set())

    @pytest.mark.asyncio
    async def test_disconnect_cleans_reverse_index(self, manager):
        """disconnect() 시 역색인에서도 해당 연결이 제거되어야 한다 (REQ-WSM-005)."""
        ws = make_ws()
        await manager.connect(ws)
        manager.subscribe(ws, ["005930"])
        manager.disconnect(ws)
        assert ws not in manager._symbol_conns.get("005930", set())


class TestConnectionManagerGetAll:
    """구독 집합 조회"""

    @pytest.mark.asyncio
    async def test_get_all_symbols_returns_subscribed(self, manager):
        """get_all_symbols()가 최소 1명 이상 구독한 심볼 집합을 반환해야 한다."""
        ws = make_ws()
        await manager.connect(ws)
        manager.subscribe(ws, ["005930", "000660"])
        result = manager.get_all_symbols()
        assert result == {"005930", "000660"}

    @pytest.mark.asyncio
    async def test_get_all_symbols_empty_when_no_subscribers(self, manager):
        """구독자 없으면 빈 집합을 반환해야 한다 (REQ-SUB-005)."""
        ws = make_ws()
        await manager.connect(ws)
        manager.subscribe(ws, ["005930"])
        manager.unsubscribe(ws, ["005930"])
        result = manager.get_all_symbols()
        assert "005930" not in result

    @pytest.mark.asyncio
    async def test_get_connections_for_symbol(self, manager):
        """get_connections_for_symbol()이 해당 심볼 구독자 집합을 반환해야 한다."""
        ws1, ws2 = make_ws(), make_ws()
        await manager.connect(ws1)
        await manager.connect(ws2)
        manager.subscribe(ws1, ["005930"])
        manager.subscribe(ws2, ["005930"])
        conns = manager.get_connections_for_symbol("005930")
        assert ws1 in conns
        assert ws2 in conns

    def test_get_connections_for_unsubscribed_symbol_returns_empty(self, manager):
        """구독자 없는 심볼은 빈 집합을 반환해야 한다."""
        conns = manager.get_connections_for_symbol("999999")
        assert len(conns) == 0
