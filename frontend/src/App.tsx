// 메인 앱 — 라우팅 및 네비게이션 포함
import { useEffect, useState } from 'react';
import { Routes, Route, Link, useNavigate, Navigate } from 'react-router-dom';
import type { ReactNode } from 'react';
import { fetchRecommendations, fetchNews, fetchSectorTrends } from './api/client';
import type { RecommendationsResponse, NewsResponse, SectorTrendsResponse, RecommendationItem } from './types';
import { DataPreparingState } from './components/DataPreparingState';
import { RecommendationList } from './components/RecommendationList';
import { NewsFeed } from './components/NewsFeed';
import { Disclaimer } from './components/Disclaimer';
import { SectorTrendChart } from './components/SectorTrendChart';
import { StockDetail } from './components/StockDetail';
import { EtfRecommendationList } from './components/EtfRecommendationList';
import { PortfolioSummary } from './components/PortfolioSummary';
import { useAuth } from './auth/AuthContext';
import Login from './pages/Login';
import Portfolio from './pages/Portfolio';
import Backtest from './pages/Backtest';

type LoadingState = 'loading' | 'ready' | 'error';

// KRX ETF 코드 패턴: 0으로 시작하는 6자리 숫자 중 ETF로 분류된 코드들
// Phase 2 MVP: recommendations에서 ETF로 알려진 코드 패턴으로 분류
// 실제 구분은 백엔드 asset_type 필드 추가 시 교체 예정
const ETF_PREFIXES = ['069', '102', '114', '148', '152', '229', '251', '261', '278', '292', '305'];

function isEtfCode(krxCode: string): boolean {
  return ETF_PREFIXES.some((prefix) => krxCode.startsWith(prefix));
}

// RecommendationsResponse에 recommendations 속성이 있는지 확인
function isRecommendationsData(
  data: RecommendationsResponse,
): data is Extract<RecommendationsResponse, { recommendations: unknown[] }> {
  return 'recommendations' in data;
}

// 인증이 필요한 라우트 — 미로그인 시 /login으로 이동
function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

// 상단 네비게이션 바
function NavBar() {
  const { isAuthenticated, user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    void navigate('/');
  }

  const navStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: '1rem',
    marginBottom: '1.5rem',
    paddingBottom: '0.75rem',
    borderBottom: '2px solid #1976d2',
    flexWrap: 'wrap',
  };

  const linkStyle: React.CSSProperties = {
    color: '#1976d2',
    textDecoration: 'none',
    fontWeight: 500,
    fontSize: '0.9rem',
  };

  return (
    <nav style={navStyle} aria-label="주 메뉴">
      <span style={{ fontWeight: 800, fontSize: '1.1rem', color: '#0d47a1', marginRight: '0.5rem' }}>
        한국 주식 추천
      </span>
      <Link to="/" style={linkStyle}>홈</Link>
      <Link to="/portfolio" style={linkStyle}>포트폴리오</Link>
      <Link to="/backtest" style={linkStyle}>백테스트</Link>
      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        {isAuthenticated ? (
          <>
            <span style={{ fontSize: '0.8rem', color: '#666' }}>{user?.email}</span>
            <button
              onClick={handleLogout}
              style={{
                padding: '0.3rem 0.7rem', border: '1px solid #ccc', borderRadius: '4px',
                background: '#fff', cursor: 'pointer', fontSize: '0.8rem',
              }}
            >
              로그아웃
            </button>
          </>
        ) : (
          <Link to="/login" style={{ ...linkStyle, padding: '0.3rem 0.7rem', border: '1px solid #1976d2', borderRadius: '4px' }}>
            로그인
          </Link>
        )}
      </div>
    </nav>
  );
}

// 메인 대시보드 컴포넌트
function Dashboard() {
  const [loadingState, setLoadingState] = useState<LoadingState>('loading');
  const [recommendations, setRecommendations] = useState<RecommendationsResponse | null>(null);
  const [newsData, setNewsData] = useState<NewsResponse | null>(null);
  const [sectorTrends, setSectorTrends] = useState<SectorTrendsResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  // 선택된 종목 코드 (상세 모달 표시용)
  const [selectedKrxCode, setSelectedKrxCode] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadData() {
      try {
        setLoadingState('loading');
        // 세 API를 병렬로 호출
        const [rec, news, trends] = await Promise.all([
          fetchRecommendations(),
          fetchNews(20),
          fetchSectorTrends(7),
        ]);
        if (cancelled) return;
        setRecommendations(rec);
        setNewsData(news);
        setSectorTrends(trends);
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

  // 추천 목록을 일반 주식 / ETF로 분류
  const allRecommendations: RecommendationItem[] =
    recommendations && isRecommendationsData(recommendations)
      ? recommendations.recommendations
      : [];

  const stockItems = allRecommendations.filter((item) => !isEtfCode(item.krx_code));
  const etfItems = allRecommendations.filter((item) => isEtfCode(item.krx_code));

  return (
    <div>
      {/* 포트폴리오 요약 위젯 */}
      <div style={{ marginBottom: '1.5rem' }}>
        <PortfolioSummary />
      </div>

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

      {/* 데이터 준비 중 상태 */}
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

          {/* 섹터 트렌드 차트 */}
          {sectorTrends && (
            <div style={{ marginBottom: '2rem' }}>
              <SectorTrendChart trends={sectorTrends.trends} />
            </div>
          )}

          {/* 메인 콘텐츠 그리드 */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'minmax(0, 3fr) minmax(0, 2fr)',
              gap: '2rem',
              alignItems: 'start',
              marginBottom: '2rem',
            }}
          >
            {/* 왼쪽: 주식 추천 목록 */}
            <RecommendationList
              recommendations={stockItems.length > 0 ? stockItems : recommendations.recommendations}
              onSelect={setSelectedKrxCode}
            />
            {/* 오른쪽: 뉴스 피드 */}
            {newsData && <NewsFeed news={newsData.news} />}
          </div>

          {/* ETF 추천 섹션 */}
          {etfItems.length > 0 && (
            <div style={{ marginBottom: '2rem' }}>
              <EtfRecommendationList etfItems={etfItems} onSelect={setSelectedKrxCode} />
            </div>
          )}
        </div>
      )}

      {/* 면책 조항: 항상 표시 */}
      <Disclaimer text={disclaimerText} />

      {/* 종목 상세 모달 */}
      {selectedKrxCode && (
        <StockDetail
          krxCode={selectedKrxCode}
          onClose={() => setSelectedKrxCode(null)}
        />
      )}
    </div>
  );
}

export default function App() {
  return (
    <div
      style={{
        maxWidth: '1100px',
        margin: '0 auto',
        padding: '1.5rem',
        fontFamily: "'Segoe UI', 'Apple SD Gothic Neo', sans-serif",
      }}
    >
      <NavBar />

      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/login" element={<Login />} />
        <Route path="/portfolio" element={
          <ProtectedRoute><Portfolio /></ProtectedRoute>
        } />
        <Route path="/backtest" element={
          <ProtectedRoute><Backtest /></ProtectedRoute>
        } />
      </Routes>
    </div>
  );
}
