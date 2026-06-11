// WebSocket /ws/prices 멀티플렉스 구독 훅 (SPEC-STOCK-016 M4)
// - 단일 WebSocket 연결로 여러 종목 동시 구독 (REQ-FE-010)
// - 연결 끊기면 마지막 가격 맵 유지 + 재연결 시도
// - 컴포넌트 언마운트 시 WebSocket 정리

import { useCallback, useEffect, useRef, useState } from 'react';
import { LivePrice } from './useLivePrice';

// 심볼 → 최신 가격 맵
export type LivePricesMap = Record<string, LivePrice>;

// 서버에서 오는 멀티플렉스 가격 메시지 타입
interface PriceMessage extends LivePrice {
  type: 'price';
  krx_code: string;
}

// @MX:ANCHOR: [AUTO] useLivePrices — 멀티플렉스 WebSocket 가격 훅 (SPEC-STOCK-016 REQ-FE-010)
// @MX:REASON: Watchlist, Dashboard 등 여러 페이지에서 공유하는 단일 WS 연결 진입점 (fan_in >= 3)
// @MX:WARN: [AUTO] WebSocket 재연결 타이머 — unmount 시 clearTimeout 필수
// @MX:REASON: 타이머 누수 방지를 위해 cleanup 함수에서 clearTimeout 호출
export function useLivePrices(symbols: string[]): LivePricesMap {
  const [prices, setPrices] = useState<LivePricesMap>({});
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const closedRef = useRef(false);
  // 현재 구독 심볼 집합 — ref로 관리해 effect 재실행 없이 접근
  const symbolsRef = useRef<string[]>(symbols);

  // symbols prop이 바뀌면 ref 동기화 + 구독 갱신
  useEffect(() => {
    symbolsRef.current = symbols;
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ action: 'subscribe', symbols }));
    }
  }, [symbols]);

  const connect = useCallback(() => {
    const ws = new WebSocket('ws://localhost:8000/ws/prices');
    wsRef.current = ws;

    ws.onopen = () => {
      if (symbolsRef.current.length > 0) {
        ws.send(JSON.stringify({ action: 'subscribe', symbols: symbolsRef.current }));
      }
    };

    ws.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data as string) as { type: string } & Partial<PriceMessage>;
        if (data.type === 'price' && data.krx_code) {
          const { krx_code, price, change_pct, timestamp } = data as PriceMessage;
          setPrices((prev) => ({
            ...prev,
            [krx_code]: { price, change_pct, timestamp },
          }));
        }
        // subscribed / unsubscribed / error 메시지는 무시
      } catch {
        // 파싱 실패 시 무시
      }
    };

    ws.onerror = () => {
      ws.close();
    };

    ws.onclose = () => {
      wsRef.current = null;
      if (closedRef.current) return;
      // 5초 후 재연결 시도
      reconnectTimerRef.current = setTimeout(() => {
        if (!closedRef.current) {
          connect();
        }
      }, 5000);
    };
  }, []);

  useEffect(() => {
    closedRef.current = false;
    connect();

    return () => {
      closedRef.current = true;
      if (reconnectTimerRef.current !== null) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      wsRef.current?.close();
      wsRef.current = null;
    };
    // connect는 useCallback으로 안정적이므로 의존성에 포함
  }, [connect]);

  return prices;
}
