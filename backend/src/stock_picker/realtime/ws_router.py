# FastAPI WebSocket 엔드포인트 — 종목 실시간 가격 스트리밍
# REQ-WS-001: 연결 즉시 최신 가격 1건 전송
# REQ-WS-002: 10초 주기로 가격 갱신 push
# REQ-WS-003: JSON {krx_code, price, change_pct, timestamp}
# REQ-WS-004: 연결 종료 시 폴링 루프 정리
# REQ-WS-005: 잘못된 krx_code는 오류 메시지 1회 전송 후 종료
# REQ-WS-006: 조회 실패 주기는 스킵, 로그, 다음 주기 재시도 (연결 유지)
import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from stock_picker.realtime.price_feed import get_current_price

logger = logging.getLogger(__name__)

router = APIRouter()

# @MX:NOTE: [AUTO] 가격 폴링 간격 — 10초 (REQ-WS-002)
_POLL_INTERVAL_SECONDS = 10


@router.websocket("/ws/prices/{krx_code}")
async def price_stream(websocket: WebSocket, krx_code: str) -> None:
    """종목 실시간 가격 WebSocket 스트림.

    # @MX:WARN: [AUTO] asyncio 루프 내 동기 블로킹 호출 포함
    # @MX:REASON: get_current_price는 동기 FinanceDataReader를 직접 호출하므로
    #             이벤트 루프를 잠시 블로킹할 수 있음. 고부하 환경에서는
    #             run_in_executor로 분리 고려 필요.

    1. 연결 수락 후 즉시 현재가 전송
    2. 잘못된 종목코드면 오류 메시지 후 종료
    3. 10초 주기로 가격 push, 조회 실패는 스킵하고 재시도
    4. WebSocketDisconnect 발생 시 루프 종료
    """
    await websocket.accept()

    # REQ-WS-001: 연결 즉시 첫 번째 가격 전송
    data = get_current_price(krx_code)
    if data is None:
        # REQ-WS-005: 잘못된 종목코드 처리
        await websocket.send_text(
            json.dumps({"error": f"종목 코드 {krx_code}를 찾을 수 없습니다."})
        )
        await websocket.close()
        return

    await websocket.send_text(json.dumps(data))

    # REQ-WS-002/004: 10초 주기 폴링 — WebSocketDisconnect로 루프 종료
    try:
        while True:
            await asyncio.sleep(_POLL_INTERVAL_SECONDS)
            data = get_current_price(krx_code)
            if data is None:
                # REQ-WS-006: 조회 실패 시 스킵 후 다음 주기 재시도
                logger.warning("가격 조회 실패, 다음 주기 재시도 — krx_code=%s", krx_code)
                continue
            await websocket.send_text(json.dumps(data))
    except WebSocketDisconnect:
        # REQ-WS-004: 연결 종료 — 루프 자동 종료 (자원 회수)
        logger.debug("WebSocket 연결 종료 — krx_code=%s", krx_code)
