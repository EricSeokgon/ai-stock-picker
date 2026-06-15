// 알림 설정 API 유닛 테스트 (SPEC-STOCK-020)
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  fetchAlerts,
  createAlert,
  updateAlert,
  deleteAlert,
  toggleAlert,
  type Alert,
  type AlertCreatePayload,
} from '../api/alerts';

const MOCK_TOKEN = 'test-bearer-token';

function makeAlert(overrides?: Partial<Alert>): Alert {
  return {
    id: 1,
    user_id: 1,
    krx_code: '005930',
    stock_name: '삼성전자',
    alert_type: 'target_price',
    condition_value: 80000,
    condition_direction: 'above',
    is_active: true,
    is_triggered: false,
    triggered_at: null,
    triggered_message: null,
    created_at: '2026-06-15T00:00:00Z',
    ...overrides,
  };
}

// ── fetchAlerts ──────────────────────────────────────────────────────────────

describe('fetchAlerts', () => {
  beforeEach(() => vi.stubGlobal('fetch', vi.fn()));
  afterEach(() => vi.unstubAllGlobals());

  it('GET /alerts/ — 알림 목록 반환', async () => {
    const mockData = [makeAlert({ id: 1 }), makeAlert({ id: 2, krx_code: '069500' })];
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    } as Response);

    const result = await fetchAlerts(MOCK_TOKEN);

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/alerts/'),
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: `Bearer ${MOCK_TOKEN}` }),
      }),
    );
    expect(result).toHaveLength(2);
    expect(result[0].alert_type).toBe('target_price');
  });

  it('빈 목록 반환', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => [],
    } as Response);

    const result = await fetchAlerts(MOCK_TOKEN);
    expect(result).toEqual([]);
  });

  it('HTTP 오류 시 예외 throw', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({ ok: false, status: 401 } as Response);
    await expect(fetchAlerts(MOCK_TOKEN)).rejects.toThrow('401');
  });
});

// ── createAlert ───────────────────────────────────────────────────────────────

describe('createAlert', () => {
  beforeEach(() => vi.stubGlobal('fetch', vi.fn()));
  afterEach(() => vi.unstubAllGlobals());

  it('POST /alerts/ — 생성된 알림 반환', async () => {
    const created = makeAlert({ id: 10 });
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => created,
    } as Response);

    const payload: AlertCreatePayload = {
      krx_code: '005930',
      stock_name: '삼성전자',
      alert_type: 'target_price',
      condition_value: 80000,
      condition_direction: 'above',
    };

    const result = await createAlert(MOCK_TOKEN, payload);

    const call = vi.mocked(fetch).mock.calls[0];
    expect(call[1]).toMatchObject({ method: 'POST' });
    expect(call[0]).toContain('/alerts/');
    expect(result.id).toBe(10);
  });

  it('surge_drop 알림 생성 — direction 없으면 서버 기본값 적용', async () => {
    const created = makeAlert({ id: 20, alert_type: 'surge_drop', condition_direction: 'either' });
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => created,
    } as Response);

    const payload: AlertCreatePayload = {
      krx_code: '069500',
      alert_type: 'surge_drop',
      condition_value: 5.0,
    };

    const result = await createAlert(MOCK_TOKEN, payload);
    expect(result.condition_direction).toBe('either');
  });

  it('서버 오류 시 detail 메시지 포함 예외 throw', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: false,
      status: 422,
      json: async () => ({ detail: '조건 값은 양수여야 합니다.' }),
    } as Response);

    const payload: AlertCreatePayload = {
      krx_code: '005930',
      alert_type: 'target_price',
      condition_value: -100,
    };
    await expect(createAlert(MOCK_TOKEN, payload)).rejects.toThrow('조건 값은 양수여야 합니다.');
  });
});

// ── updateAlert ───────────────────────────────────────────────────────────────

describe('updateAlert', () => {
  beforeEach(() => vi.stubGlobal('fetch', vi.fn()));
  afterEach(() => vi.unstubAllGlobals());

  it('PUT /alerts/{id} — 수정된 알림 반환', async () => {
    const updated = makeAlert({ id: 5, is_active: false });
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => updated,
    } as Response);

    const result = await updateAlert(MOCK_TOKEN, 5, { is_active: false });

    const call = vi.mocked(fetch).mock.calls[0];
    expect(call[0]).toContain('/alerts/5');
    expect(call[1]).toMatchObject({ method: 'PUT' });
    expect(result.is_active).toBe(false);
  });

  it('존재하지 않는 알림 수정 시 예외 throw', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ detail: '알림을 찾을 수 없습니다.' }),
    } as Response);

    await expect(updateAlert(MOCK_TOKEN, 999, { is_active: false })).rejects.toThrow('알림을 찾을 수 없습니다.');
  });
});

// ── deleteAlert ───────────────────────────────────────────────────────────────

describe('deleteAlert', () => {
  beforeEach(() => vi.stubGlobal('fetch', vi.fn()));
  afterEach(() => vi.unstubAllGlobals());

  it('DELETE /alerts/{id} — 204 성공 시 void 반환', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({ ok: true } as Response);

    await expect(deleteAlert(MOCK_TOKEN, 3)).resolves.toBeUndefined();

    const call = vi.mocked(fetch).mock.calls[0];
    expect(call[0]).toContain('/alerts/3');
    expect(call[1]).toMatchObject({ method: 'DELETE' });
  });

  it('HTTP 오류 시 예외 throw', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ detail: '알림을 찾을 수 없습니다.' }),
    } as Response);

    await expect(deleteAlert(MOCK_TOKEN, 99)).rejects.toThrow('알림을 찾을 수 없습니다.');
  });
});

// ── toggleAlert ───────────────────────────────────────────────────────────────

describe('toggleAlert', () => {
  beforeEach(() => vi.stubGlobal('fetch', vi.fn()));
  afterEach(() => vi.unstubAllGlobals());

  it('활성화 → 비활성화 토글', async () => {
    const deactivated = makeAlert({ id: 7, is_active: false });
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => deactivated,
    } as Response);

    const result = await toggleAlert(MOCK_TOKEN, 7, false);
    expect(result.is_active).toBe(false);
  });

  it('비활성화 → 활성화 토글', async () => {
    const activated = makeAlert({ id: 8, is_active: true });
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => activated,
    } as Response);

    const result = await toggleAlert(MOCK_TOKEN, 8, true);
    expect(result.is_active).toBe(true);
  });
});
