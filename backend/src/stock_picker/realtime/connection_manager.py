# 멀티플렉스 WebSocket 구독 레지스트리 (SPEC-STOCK-016 M1)
# REQ-SUB-001: 연결별 구독 심볼 집합 관리
# REQ-SUB-002: 심볼별 구독자 역색인
# REQ-WSM-005: 연결 종료 시 레지스트리 정리
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)

# @MX:ANCHOR: [AUTO] ConnectionManager — 멀티플렉스 WS 구독 레지스트리 공개 API
# @MX:REASON: ws_router.py, price_broadcast.py에서 공유하는 모듈 수준 싱글턴 진입점 (fan_in >= 3)


class ConnectionManager:
    """인메모리 WebSocket 구독 레지스트리.

    단일 FastAPI 프로세스 내에서 연결별 구독 심볼과
    심볼별 구독자 집합을 관리한다.
    """

    def __init__(self) -> None:
        # 연결 → 구독 심볼 집합
        self._conn_symbols: dict[WebSocket, set[str]] = {}
        # 심볼 → 구독 연결 집합
        self._symbol_conns: dict[str, set[WebSocket]] = {}

    async def connect(self, ws: WebSocket) -> None:
        """WebSocket 연결을 수락하고 레지스트리에 등록."""
        await ws.accept()
        self._conn_symbols[ws] = set()

    def disconnect(self, ws: WebSocket) -> None:
        """연결 해제 시 레지스트리와 역색인에서 제거 (REQ-WSM-005)."""
        symbols = self._conn_symbols.pop(ws, set())
        for sym in symbols:
            self._symbol_conns.get(sym, set()).discard(ws)
            # 구독자 없는 심볼 항목 정리
            if not self._symbol_conns.get(sym):
                self._symbol_conns.pop(sym, None)

    def subscribe(self, ws: WebSocket, symbols: list[str]) -> None:
        """연결에 심볼 목록을 구독 등록."""
        conn_set = self._conn_symbols.setdefault(ws, set())
        for sym in symbols:
            conn_set.add(sym)
            self._symbol_conns.setdefault(sym, set()).add(ws)
            logger.debug("구독 등록 — symbol=%s conn=%s", sym, id(ws))

    def unsubscribe(self, ws: WebSocket, symbols: list[str]) -> None:
        """연결에서 심볼 목록 구독 해지."""
        conn_set = self._conn_symbols.get(ws, set())
        for sym in symbols:
            conn_set.discard(sym)
            sym_set = self._symbol_conns.get(sym, set())
            sym_set.discard(ws)
            if not sym_set:
                self._symbol_conns.pop(sym, None)
            logger.debug("구독 해지 — symbol=%s conn=%s", sym, id(ws))

    def get_all_symbols(self) -> set[str]:
        """현재 최소 1개 이상의 구독자가 있는 심볼 집합 반환 (REQ-SUB-005)."""
        return set(self._symbol_conns.keys())

    def get_connections_for_symbol(self, symbol: str) -> set[WebSocket]:
        """특정 심볼의 구독자 연결 집합 반환."""
        return self._symbol_conns.get(symbol, set())
