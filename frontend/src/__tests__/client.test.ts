// API 클라이언트 테스트
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { fetchRecommendations, fetchNews } from '../api/client';
import type { RecommendationsData, PreparingData, NewsResponse } from '../types';

// fetch 전역 모킹
const mockFetch = vi.fn();

beforeEach(() => {
  vi.stubGlobal('fetch', mockFetch);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('fetchRecommendations', () => {
  it('정상 응답 시 RecommendationsData를 반환한다', async () => {
    const mockData: RecommendationsData = {
      trade_date: '2026-06-01',
      recommendations: [
        {
          rank: 1,
          krx_code: '005930',
          total_score: 0.85,
          sentiment_score: 0.7,
          volume_score: 0.6,
          momentum_score: 0.8,
          anomaly_score: 0.5,
          reasoning: '삼성전자 강한 매수 신호',
        },
      ],
      disclaimer: '투자 결정은 본인 책임입니다.',
      last_updated: '2026-06-01T09:00:00Z',
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    });

    const result = await fetchRecommendations();
    expect(result).toEqual(mockData);
    expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/recommendations');
  });

  it('preparing 상태 응답을 반환한다', async () => {
    const mockData: PreparingData = {
      status: 'preparing',
      last_updated: null,
      disclaimer: '데이터를 준비 중입니다.',
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    });

    const result = await fetchRecommendations();
    expect(result).toEqual(mockData);
  });

  it('500 오류 응답 시 Error를 던진다', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
    });

    await expect(fetchRecommendations()).rejects.toThrow('API 오류: 500');
  });

  it('404 오류 응답 시 Error를 던진다', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
    });

    await expect(fetchRecommendations()).rejects.toThrow('API 오류: 404');
  });
});

describe('fetchNews', () => {
  it('뉴스 목록을 반환한다', async () => {
    const mockData: NewsResponse = {
      news: [
        {
          title: '코스피 상승세 지속',
          summary: '코스피가 연속 상승세를 보이고 있다.',
          sentiment: 'positive',
          source: '한국경제',
          url: 'https://example.com/news/1',
          published_at: '2026-06-01T08:00:00Z',
        },
      ],
      total: 1,
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    });

    const result = await fetchNews();
    expect(result).toEqual(mockData);
    expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/news?limit=20');
  });

  it('커스텀 limit 파라미터를 URL에 포함한다', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ news: [], total: 0 }),
    });

    await fetchNews(5);
    expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/news?limit=5');
  });

  it('오류 응답 시 Error를 던진다', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 503,
    });

    await expect(fetchNews()).rejects.toThrow('API 오류: 503');
  });
});
