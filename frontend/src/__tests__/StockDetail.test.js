import { jsx as _jsx } from "react/jsx-runtime";
// StockDetail 모달 컴포넌트 테스트
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { StockDetail } from '../components/StockDetail';
// fetchRecommendationDetail mock
vi.mock('../api/client', () => ({
    fetchRecommendationDetail: vi.fn(),
}));
import { fetchRecommendationDetail } from '../api/client';
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
            summary: '3분기 영업이익 큰 폭 개선',
            sentiment: 'positive',
            published_at: '2026-06-01T09:00:00',
        },
        {
            title: '반도체 시장 회복 신호',
            summary: null,
            sentiment: 'neutral',
            published_at: '2026-06-01T08:00:00',
        },
    ],
    disclaimer: '이 정보는 투자 참고용입니다.',
};
describe('StockDetail', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });
    it('로딩 중에 스피너(로딩 텍스트)를 표시한다', () => {
        // fetchRecommendationDetail가 resolve되지 않도록 pending 상태 유지
        fetchRecommendationDetail.mockReturnValue(new Promise(() => { }));
        render(_jsx(StockDetail, { krxCode: "005930", onClose: () => { } }));
        expect(screen.getByText('불러오는 중...')).toBeInTheDocument();
    });
    it('데이터 로드 후 krx_code를 표시한다', async () => {
        fetchRecommendationDetail.mockResolvedValue(mockDetail);
        render(_jsx(StockDetail, { krxCode: "005930", onClose: () => { } }));
        await waitFor(() => {
            expect(screen.getByText('005930')).toBeInTheDocument();
        });
    });
    it('reasoning 텍스트를 표시한다', async () => {
        fetchRecommendationDetail.mockResolvedValue(mockDetail);
        render(_jsx(StockDetail, { krxCode: "005930", onClose: () => { } }));
        await waitFor(() => {
            expect(screen.getByText('삼성전자는 반도체 수요 회복으로 강한 매수 신호가 감지됩니다.')).toBeInTheDocument();
        });
    });
    it('기여 뉴스 목록을 표시한다', async () => {
        fetchRecommendationDetail.mockResolvedValue(mockDetail);
        render(_jsx(StockDetail, { krxCode: "005930", onClose: () => { } }));
        await waitFor(() => {
            expect(screen.getByText('삼성전자 반도체 실적 호조')).toBeInTheDocument();
            expect(screen.getByText('반도체 시장 회복 신호')).toBeInTheDocument();
        });
    });
    it('감성 배지를 표시한다 (positive)', async () => {
        fetchRecommendationDetail.mockResolvedValue(mockDetail);
        render(_jsx(StockDetail, { krxCode: "005930", onClose: () => { } }));
        await waitFor(() => {
            // positive 감성 배지
            expect(screen.getByText('긍정')).toBeInTheDocument();
        });
    });
    it('닫기 버튼 클릭 시 onClose가 호출된다', async () => {
        fetchRecommendationDetail.mockResolvedValue(mockDetail);
        const onClose = vi.fn();
        render(_jsx(StockDetail, { krxCode: "005930", onClose: onClose }));
        await waitFor(() => {
            expect(screen.getByText('005930')).toBeInTheDocument();
        });
        const closeBtn = screen.getByRole('button', { name: /닫기/ });
        await userEvent.click(closeBtn);
        expect(onClose).toHaveBeenCalledTimes(1);
    });
});
