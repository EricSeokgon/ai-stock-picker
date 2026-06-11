// WebSocket /ws/prices/{krxCode} 구독 훅 (REQ-FE-001, REQ-FE-006)
// - 연결 시 즉시 가격 수신
// - 연결 끊기면 마지막 가격 유지 + 재연결 시도 (REQ-FE-006)
// - 컴포넌트 언마운트 시 WebSocket 정리
import { useEffect, useRef, useState } from 'react';
// @MX:ANCHOR: [AUTO] useLivePrice — WebSocket 가격 스트림 훅 (REQ-FE-001, REQ-FE-006)
// @MX:REASON: LivePriceBadge, Watchlist, PortfolioDetail 등 여러 컴포넌트에서 사용되는 공유 진입점
// @MX:WARN: [AUTO] WebSocket 재연결 타이머 — unmount 시 반드시 clearTimeout 필요
// @MX:REASON: 타이머 누수 방지를 위해 cleanup 함수에서 clearTimeout 호출
export function useLivePrice(krxCode) {
    const [price, setPrice] = useState(null);
    // 재연결 타이머 ref — cleanup에서 clearTimeout
    const reconnectTimerRef = useRef(null);
    // 연결 종료 여부 ref — unmount 시 재연결 방지
    const closedRef = useRef(false);
    useEffect(() => {
        closedRef.current = false;
        function connect() {
            const ws = new WebSocket(`ws://localhost:8000/ws/prices/${krxCode}`);
            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    setPrice(data);
                }
                catch {
                    // 파싱 실패 시 무시
                }
            };
            ws.onerror = () => {
                ws.close();
            };
            ws.onclose = () => {
                if (closedRef.current)
                    return;
                // 5초 후 재연결 시도
                reconnectTimerRef.current = setTimeout(() => {
                    if (!closedRef.current) {
                        connect();
                    }
                }, 5000);
            };
            return ws;
        }
        const ws = connect();
        return () => {
            closedRef.current = true;
            if (reconnectTimerRef.current !== null) {
                clearTimeout(reconnectTimerRef.current);
                reconnectTimerRef.current = null;
            }
            ws.close();
        };
    }, [krxCode]);
    return price;
}
