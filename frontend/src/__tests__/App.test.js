import { jsx as _jsx } from "react/jsx-runtime";
// App 통합 테스트 - 전체 대시보드 렌더링 및 인터랙션
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';
// API 클라이언트 전체 mock
vi.mock('../api/client', () => ({
    fetchRecommendations: vi.fn(),
    fetchNews: vi.fn(),
    fetchSectorTrends: vi.fn(),
    fetchRecommendationDetail: vi.fn(),
}));
import { fetchRecommendations, fetchNews, fetchSectorTrends, fetchRecommendationDetail, } from '../api/client';
const mockRecommendations = {
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
            reasoning: '삼성전자 강한 매수 신호 감지',
        },
        {
            rank: 2,
            krx_code: '000660',
            total_score: 0.72,
            sentiment_score: 0.4,
            volume_score: 0.5,
            momentum_score: 0.6,
            anomaly_score: 0.3,
            reasoning: 'SK하이닉스 반도체 수요 회복 기대',
        },
    ],
    disclaimer: '이 정보는 투자 참고용입니다.',
    last_updated: '2026-06-01T09:00:00',
};
const mockNews = {
    news: [
        {
            title: '반도체 시장 회복 신호',
            summary: '글로벌 수요 증가',
            sentiment: 'positive',
            source: '한국경제',
            url: 'https://example.com/1',
            published_at: '2026-06-01T08:00:00',
        },
    ],
    total: 1,
};
const mockSectorTrends = {
    trends: [
        {
            sector: '반도체',
            trade_date: '2026-06-01',
            trend_score: 0.82,
            news_volume: 45,
            avg_sentiment: 0.6,
        },
    ],
    days: 7,
};
const mockDetail = {
    krx_code: '005930',
    trade_date: '2026-06-01',
    total_score: 0.85,
    sentiment_score: 0.7,
    volume_score: 0.6,
    momentum_score: 0.8,
    anomaly_score: 0.5,
    reasoning: '삼성전자는 반도체 수요 회복으로 강한 매수 신호가 감지됩니다.',
    contributing_news: [
        {
            title: '삼성전자 반도체 실적 호조',
            summary: '3분기 영업이익 개선',
            sentiment: 'positive',
            published_at: '2026-06-01T09:00:00',
        },
    ],
    disclaimer: '이 정보는 투자 참고용입니다.',
};
describe('App', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        fetchRecommendations.mockResolvedValue(mockRecommendations);
        fetchNews.mockResolvedValue(mockNews);
        fetchSectorTrends.mockResolvedValue(mockSectorTrends);
        fetchRecommendationDetail.mockResolvedValue(mockDetail);
    });
    it('초기 로딩 중 메시지를 표시한다', () => {
        // Promise가 resolve되지 않는 상태 유지
        fetchRecommendations.mockReturnValue(new Promise(() => { }));
        fetchNews.mockReturnValue(new Promise(() => { }));
        fetchSectorTrends.mockReturnValue(new Promise(() => { }));
        render(_jsx(App, {}));
        expect(screen.getByText('데이터를 불러오는 중...')).toBeInTheDocument();
    });
    it('데이터 로드 후 대시보드 제목을 표시한다', async () => {
        render(_jsx(App, {}));
        await waitFor(() => {
            expect(screen.getByText('한국 주식 추천 대시보드')).toBeInTheDocument();
        });
    });
    it('데이터 로드 후 섹터 트렌드 섹션이 표시된다', async () => {
        render(_jsx(App, {}));
        await waitFor(() => {
            expect(screen.getByText('섹터 트렌드')).toBeInTheDocument();
        });
    });
    it('추천 종목 목록을 표시한다', async () => {
        render(_jsx(App, {}));
        await waitFor(() => {
            expect(screen.getByText('005930')).toBeInTheDocument();
            expect(screen.getByText('000660')).toBeInTheDocument();
        });
    });
    it('종목 클릭 시 StockDetail 모달이 표시된다', async () => {
        render(_jsx(App, {}));
        // 데이터 로드 완료 후 목록 탐색
        let firstItem = null;
        await waitFor(() => {
            const list = screen.getByRole('list', { name: '주식 추천 목록' });
            firstItem = list.querySelectorAll('li')[0];
            expect(firstItem).toBeTruthy();
        });
        await userEvent.click(firstItem);
        // 모달 로딩 텍스트 확인
        await waitFor(() => {
            expect(screen.getByRole('dialog')).toBeInTheDocument();
        });
    });
    it('모달 닫기 후 모달이 사라진다', async () => {
        render(_jsx(App, {}));
        let firstItem = null;
        await waitFor(() => {
            const list = screen.getByRole('list', { name: '주식 추천 목록' });
            firstItem = list.querySelectorAll('li')[0];
            expect(firstItem).toBeTruthy();
        });
        await userEvent.click(firstItem);
        await waitFor(() => {
            expect(screen.getByRole('dialog')).toBeInTheDocument();
        });
        // 닫기 버튼 클릭
        const closeBtn = screen.getByRole('button', { name: /닫기/ });
        await userEvent.click(closeBtn);
        await waitFor(() => {
            expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
        });
    });
    it('API 오류 시 오류 메시지를 표시한다', async () => {
        fetchRecommendations.mockRejectedValue(new Error('서버에 연결할 수 없습니다'));
        render(_jsx(App, {}));
        await waitFor(() => {
            expect(screen.getByRole('alert')).toBeInTheDocument();
        });
    });
});
