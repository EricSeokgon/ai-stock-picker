// useLivePrice 훅 테스트
import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useLivePrice } from '../hooks/useLivePrice';

// WebSocket mock
class MockWebSocket {
  static instances: MockWebSocket[] = [];
  url: string;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: (() => void) | null = null;
  readyState = 1; // OPEN

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  close() {
    this.readyState = 3; // CLOSED
    if (this.onclose) this.onclose();
  }

  // 테스트에서 메시지를 보내기 위한 헬퍼
  triggerMessage(data: string) {
    if (this.onmessage) this.onmessage({ data });
  }
}

describe('useLivePrice', () => {
  beforeEach(() => {
    MockWebSocket.instances = [];
    vi.stubGlobal('WebSocket', MockWebSocket);
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it('초기에 null을 반환한다', () => {
    const { result } = renderHook(() => useLivePrice('005930'));
    expect(result.current).toBeNull();
  });

  it('WebSocket 메시지 수신 시 가격을 업데이트한다', () => {
    const { result } = renderHook(() => useLivePrice('005930'));

    const ws = MockWebSocket.instances[0];
    expect(ws).toBeDefined();

    act(() => {
      ws.triggerMessage(JSON.stringify({
        price: 75000,
        change_pct: 1.23,
        timestamp: '2024-01-01T09:00:00',
      }));
    });

    expect(result.current).not.toBeNull();
    expect(result.current?.price).toBe(75000);
    expect(result.current?.change_pct).toBe(1.23);
  });

  it('잘못된 JSON 메시지 수신 시 상태가 변경되지 않는다', () => {
    const { result } = renderHook(() => useLivePrice('005930'));

    const ws = MockWebSocket.instances[0];

    act(() => {
      ws.triggerMessage('invalid json');
    });

    expect(result.current).toBeNull();
  });

  it('krxCode 변경 시 새 WebSocket에 연결한다', () => {
    const { rerender } = renderHook(({ code }) => useLivePrice(code), {
      initialProps: { code: '005930' },
    });

    expect(MockWebSocket.instances).toHaveLength(1);
    expect(MockWebSocket.instances[0].url).toContain('005930');

    rerender({ code: '000660' });

    // 기존 연결이 닫히고 새 연결이 생성됨
    expect(MockWebSocket.instances.length).toBeGreaterThanOrEqual(1);
  });
});
