// 알림 인박스 API 유닛 테스트 (SPEC-STOCK-013 REQ-FE-001~004)
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  fetchNotifications,
  fetchUnreadCount,
  markNotificationRead,
  markAllNotificationsRead,
  type Notification,
} from '../api/notifications';

const MOCK_TOKEN = 'test-bearer-token';

function makeNotification(overrides?: Partial<Notification>): Notification {
  return {
    id: 1,
    type: 'price_alert',
    krx_code: '005930',
    title: '[가격 알림] 005930 목표가 도달',
    body: '현재가 70000원이 목표가 68000원에 도달했습니다.',
    is_read: false,
    ref_date: '2026-06-11',
    related_alert_id: 42,
    created_at: '2026-06-11T09:00:00Z',
    read_at: null,
    ...overrides,
  };
}

describe('fetchNotifications', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('GET /notifications/ 호출 — 알림 목록 반환', async () => {
    const mockData = [makeNotification({ id: 1 }), makeNotification({ id: 2 })];
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    } as Response);

    const result = await fetchNotifications(MOCK_TOKEN);

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/notifications/'),
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: `Bearer ${MOCK_TOKEN}` }),
      }),
    );
    expect(result).toHaveLength(2);
    expect(result[0].id).toBe(1);
  });

  it('unread_only=true 파라미터 포함', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => [],
    } as Response);

    await fetchNotifications(MOCK_TOKEN, true);

    const calledUrl = (vi.mocked(fetch).mock.calls[0][0] as string);
    expect(calledUrl).toContain('unread_only=true');
  });

  it('HTTP 오류 시 예외 throw', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: false,
      status: 401,
    } as Response);

    await expect(fetchNotifications(MOCK_TOKEN)).rejects.toThrow('401');
  });
});

describe('fetchUnreadCount', () => {
  beforeEach(() => vi.stubGlobal('fetch', vi.fn()));
  afterEach(() => vi.unstubAllGlobals());

  it('GET /notifications/unread-count — count 반환', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ count: 5 }),
    } as Response);

    const count = await fetchUnreadCount(MOCK_TOKEN);
    expect(count).toBe(5);
  });

  it('count 0 반환', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ count: 0 }),
    } as Response);

    const count = await fetchUnreadCount(MOCK_TOKEN);
    expect(count).toBe(0);
  });

  it('HTTP 오류 시 예외 throw', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({ ok: false, status: 403 } as Response);
    await expect(fetchUnreadCount(MOCK_TOKEN)).rejects.toThrow('403');
  });
});

describe('markNotificationRead', () => {
  beforeEach(() => vi.stubGlobal('fetch', vi.fn()));
  afterEach(() => vi.unstubAllGlobals());

  it('PATCH /notifications/{id}/read — 읽음 처리된 알림 반환', async () => {
    const updated = makeNotification({ id: 7, is_read: true });
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => updated,
    } as Response);

    const result = await markNotificationRead(MOCK_TOKEN, 7);

    const calledUrl = vi.mocked(fetch).mock.calls[0][0] as string;
    expect(calledUrl).toContain('/notifications/7/read');
    expect(vi.mocked(fetch).mock.calls[0][1]).toMatchObject({ method: 'PATCH' });
    expect(result.is_read).toBe(true);
  });

  it('HTTP 오류 시 예외 throw', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({ ok: false, status: 404 } as Response);
    await expect(markNotificationRead(MOCK_TOKEN, 99)).rejects.toThrow('404');
  });
});

describe('markAllNotificationsRead', () => {
  beforeEach(() => vi.stubGlobal('fetch', vi.fn()));
  afterEach(() => vi.unstubAllGlobals());

  it('PATCH /notifications/read-all — updated 건수 반환', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ updated: 3 }),
    } as Response);

    const result = await markAllNotificationsRead(MOCK_TOKEN);

    const calledUrl = vi.mocked(fetch).mock.calls[0][0] as string;
    expect(calledUrl).toContain('/notifications/read-all');
    expect(vi.mocked(fetch).mock.calls[0][1]).toMatchObject({ method: 'PATCH' });
    expect(result.updated).toBe(3);
  });

  it('updated 0 반환 (이미 전체 읽음)', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ updated: 0 }),
    } as Response);

    const result = await markAllNotificationsRead(MOCK_TOKEN);
    expect(result.updated).toBe(0);
  });

  it('HTTP 오류 시 예외 throw', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({ ok: false, status: 500 } as Response);
    await expect(markAllNotificationsRead(MOCK_TOKEN)).rejects.toThrow('500');
  });
});
