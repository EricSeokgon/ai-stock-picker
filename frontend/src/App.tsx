// 메인 대시보드 컴포넌트
import { useEffect, useState } from 'react';
import { fetchRecommendations, fetchNews } from './api/client';
import type { RecommendationsResponse, NewsResponse } from './types';
import { DataPreparingState } from './components/DataPreparingState';
import { RecommendationList } from './components/RecommendationList';
import { NewsFeed } from './components/NewsFeed';
import { Disclaimer } from './components/Disclaimer';

type LoadingState = 'loading' | 'ready' | 'error';

// RecommendationsResponse에 recommendations 속성이 있는지 확인
function isRecommendationsData(
  data: RecommendationsResponse,
): data is Extract<RecommendationsResponse, { recommendations: unknown[] }> {
  return 'recommendations' in data;
}

export default function App() {
  const [loadingState, setLoadingState] = useState<LoadingState>('loading');
  const [recommendations, setRecommendations] = useState<RecommendationsResponse | null>(null);
  const [newsData, setNewsData] = useState<NewsResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadData() {
      try {
        setLoadingState('loading');
        const [rec, news] = await Promise.all([fetchRecommendations(), fetchNews(20)]);
        if (cancelled) return;
        setRecommendations(rec);
        setNewsData(news);
        setLoadingState('ready');
      } catch (err) {
        if (cancelled) return;
        setErrorMessage(err instanceof Error ? err.message : '데이터를 불러오는 중 오류가 발생했습니다.');
        setLoadingState('error');
      }
    }

    void loadData();
    return () => {
      cancelled = true;
    };
  }, []);

  const disclaimerText =
    recommendations && 'disclaimer' in recommendations
      ? recommendations.disclaimer
      : '이 정보는 투자 참고용입니다. 실제 투자 결정은 본인 책임하에 이루어져야 합니다.';

  return (
    <div
      style={{
        maxWidth: '900px',
        margin: '0 auto',
        padding: '1.5rem',
        fontFamily: "'Segoe UI', 'Apple SD Gothic Neo', sans-serif",
      }}
    >
      {/* 헤더 */}
      <header style={{ marginBottom: '2rem', borderBottom: '2px solid #1976d2', paddingBottom: '1rem' }}>
        <h1 style={{ margin: 0, fontSize: '1.75rem', color: '#0d47a1', fontWeight: 800 }}>
          한국 주식 추천 대시보드
        </h1>
        <p style={{ margin: '0.25rem 0 0', fontSize: '0.875rem', color: '#666' }}>
          AI 기반 한국 주식 및 ETF 추천 시스템
        </p>
      </header>

      {/* 로딩 상태 */}
      {loadingState === 'loading' && (
        <div role="status" aria-live="polite" style={{ textAlign: 'center', padding: '3rem', color: '#666' }}>
          <p>데이터를 불러오는 중...</p>
        </div>
      )}

      {/* 오류 상태 */}
      {loadingState === 'error' && (
        <div
          role="alert"
          style={{
            padding: '1rem',
            backgroundColor: '#ffebee',
            border: '1px solid #ef9a9a',
            borderRadius: '4px',
            color: '#c62828',
          }}
        >
          <strong>오류:</strong> {errorMessage}
        </div>
      )}

      {/* 데이터 준비 중 상태 (AC-10) */}
      {loadingState === 'ready' && recommendations && !isRecommendationsData(recommendations) && (
        <DataPreparingState />
      )}

      {/* 데이터 정상 표시 */}
      {loadingState === 'ready' && recommendations && isRecommendationsData(recommendations) && (
        <div>
          {/* 거래일 표시 */}
          <p style={{ fontSize: '0.875rem', color: '#666', marginBottom: '1.5rem' }}>
            기준일: <strong>{recommendations.trade_date}</strong>
          </p>

          {/* 메인 콘텐츠: 추천 목록 + 뉴스 */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'minmax(0, 3fr) minmax(0, 2fr)',
              gap: '2rem',
              alignItems: 'start',
            }}
          >
            <RecommendationList recommendations={recommendations.recommendations} />
            {newsData && <NewsFeed news={newsData.news} />}
          </div>
        </div>
      )}

      {/* 면책 조항: 항상 표시 */}
      <Disclaimer text={disclaimerText} />
    </div>
  );
}
