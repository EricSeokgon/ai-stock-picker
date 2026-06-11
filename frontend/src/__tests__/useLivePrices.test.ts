// useLivePrices 멀티플렉스 훅 테스트 (SPEC-STOCK-016 M6)
import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useLivePrices } from '../hooks/useLivePrices';

// WebSocket mock — onopen 지원 포함
class MockWebSocket {
  static instances: MockWebSocket[] = [];
  url: string;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: (() => void) | null = null;
  readyState = 1; // OPEN
  sentMessages: string[] = [];

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  send(data: string) {
    this.sentMessages.push(data);
  }

  close() {
    this.readyState = 3; // CLOSED
    if (this.onclose) this.onclose();
  }

  // 테스트에서 서버 메시지 시뮬레이션
  triggerMessage(data: object) {
    if (this.onmessage) this.onmessage({ data: JSON.stringify(data) });
  }

  // 연결 수립 시뮬레이션
  triggerOpen() {
    if (this.onopen) this.onopen();
  }
}

describe('useLivePrices', () => {
  beforeEach(() => {
    MockWebSocket.instances = [];
    vi.stubGlobal('WebSocket', MockWebSocket);
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it('초기에 빈 맵을 반환한다', () => {
    const { result } = renderHook(() => useLivePrices(['005930']));
    expect(result.current).toEqual({});
  });

  it('/ws/prices 엔드포인트에 연결한다', () => {
    renderHook(() => useLivePrices(['005930']));
    const ws = MockWebSocket.instances[0];
    expect(ws).toBeDefined();
    expect(ws.url).toContain('/ws/prices');
    // 단일 심볼 엔드포인트가 아니어야 함
    expect(ws.url).not.toMatch(/\/ws\/prices\/\w+/);
  });

  it('연결 수립 시 subscribe 메시지를 전송한다', () => {
    renderHook(() => useLivePrices(['005930', '000660']));
    const ws = MockWebSocket.instances[0];

    act(() => {
      ws.triggerOpen();
    });

    expect(ws.sentMessages).toHaveLength(1);
    const msg = JSON.parse(ws.sentMessages[0]) as { action: string; symbols: string[] };
    expect(msg.action).toBe('subscribe');
    expect(msg.symbols).toContain('005930');
    expect(msg.symbols).toContain('000660');
  });

  it('price 메시지 수신 시 해당 종목 가격을 갱신한다', () => {
    const { result } = renderHook(() => useLivePrices(['005930']));
    const ws = MockWebSocket.instances[0];

    act(() => {
      ws.triggerMessage({
        type: 'price',
        krx_code: '005930',
        price: 71000,
        change_pct: 1.42,
        timestamp: '2026-06-12T10:00:00',
      });
    });

    expect(result.current['005930']).toBeDefined();
    expect(result.current['005930'].price).toBe(71000);
    expect(result.current['005930'].change_pct).toBe(1.42);
  });

  it('여러 종목의 가격을 독립적으로 갱신한다', () => {
    const { result } = renderHook(() => useLivePrices(['005930', '000660']));
    const ws = MockWebSocket.instances[0];

    act(() => {
      ws.triggerMessage({ type: 'price', krx_code: '005930', price: 71000, change_pct: 1.0, timestamp: 't1' });
    });
    act(() => {
      ws.triggerMessage({ type: 'price', krx_code: '000660', price: 140000, change_pct: -0.5, timestamp: 't2' });
    });

    expect(result.current['005930'].price).toBe(71000);
    expect(result.current['000660'].price).toBe(140000);
  });

  it('subscribed 메시지는 가격 맵을 변경하지 않는다', () => {
    const { result } = renderHook(() => useLivePrices(['005930']));
    const ws = MockWebSocket.instances[0];

    act(() => {
      ws.triggerMessage({ type: 'subscribed', symbols: ['005930'] });
    });

    expect(result.current).toEqual({});
  });

  it('잘못된 JSON 메시지는 무시한다', () => {
    const { result } = renderHook(() => useLivePrices(['005930']));
    const ws = MockWebSocket.instances[0];

    act(() => {
      if (ws.onmessage) ws.onmessage({ data: 'invalid-json' });
    });

    expect(result.current).toEqual({});
  });

  it('언마운트 시 WebSocket을 닫는다', () => {
    const { unmount } = renderHook(() => useLivePrices(['005930']));
    const ws = MockWebSocket.instances[0];

    unmount();

    expect(ws.readyState).toBe(3); // CLOSED
  });

  it('symbols가 비어도 연결은 유지된다', () => {
    renderHook(() => useLivePrices([]));
    expect(MockWebSocket.instances).toHaveLength(1);
  });
});
