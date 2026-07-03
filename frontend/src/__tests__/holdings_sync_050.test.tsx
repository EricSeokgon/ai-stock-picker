// SPEC-STOCK-050: 거래 기반 홀딩스 동기화 — 프론트엔드 단위 테스트 (2개)
// F-050-001 ~ F-050-002
//
// RED phase: previewHoldingsSync, applyHoldingsSync 함수가 아직 없어
// import 오류 또는 TypeError로 실패 예정
//
// 테스트 실행:
//   cd frontend && npx --yes vitest run src/__tests__/holdings_sync_050.test.tsx

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// fetch 전역 모킹
const mockFetch = vi.fn();

beforeEach(() => {
  vi.stubGlobal('fetch', mockFetch);
});

afterEach(() => {
  vi.restoreAllMocks();
});

// F-050-001: previewHoldingsSync — GET /portfolios/{id}/holdings/sync/preview 호출
describe('previewHoldingsSync', () => {
  it('올바른 엔드포인트로 GET 요청을 보낸다', async () => {
    // 준비: SyncPreviewResponse 목 데이터
    const mockPreviewData = {
      items: [
        {
          krx_code: '005930',
          action: 'upsert',
          current_qty: 0,
          derived_qty: 10,
          current_avg: null,
          derived_avg: '1000.00',
        },
      ],
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockPreviewData,
    });

    // RED: previewHoldingsSync가 portfolio.ts에 없으므로 import 실패
    const { previewHoldingsSync } = await import('../api/portfolio');

    const token = 'test-token';
    const portfolioId = 1;

    const result = await previewHoldingsSync(token, portfolioId);

    // 올바른 엔드포인트 호출 검증
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining(`/portfolios/${portfolioId}/holdings/sync/preview`),
      expect.objectContaining({
        method: 'GET',
        headers: expect.objectContaining({
          Authorization: `Bearer ${token}`,
        }),
      })
    );
    expect(result).toEqual(mockPreviewData);
  });
});

// F-050-002: applyHoldingsSync — POST /portfolios/{id}/holdings/sync 호출
describe('applyHoldingsSync', () => {
  it('올바른 엔드포인트로 POST 요청을 보내고 SyncApplyResponse를 반환한다', async () => {
    // 준비: SyncApplyResponse 목 데이터
    const mockApplyData = {
      synced: 2,
      holdings: [
        {
          krx_code: '005930',
          quantity: 15,
          avg_buy_price: '1500.00',
        },
      ],
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockApplyData,
    });

    // RED: applyHoldingsSync가 portfolio.ts에 없으므로 import 실패
    const { applyHoldingsSync } = await import('../api/portfolio');

    const token = 'test-token';
    const portfolioId = 1;

    const result = await applyHoldingsSync(token, portfolioId);

    // 올바른 엔드포인트 호출 검증
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining(`/portfolios/${portfolioId}/holdings/sync`),
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          Authorization: `Bearer ${token}`,
        }),
      })
    );
    expect(result.synced).toBe(2);
    expect(result.holdings).toHaveLength(1);
  });
});
