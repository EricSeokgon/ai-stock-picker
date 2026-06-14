// 메인 앱 — 라우팅 및 네비게이션 포함
import { useEffect, useState, useCallback, useMemo } from 'react';
import { useLivePrices } from './hooks/useLivePrices';
import { Routes, Route, Link, useNavigate, Navigate } from 'react-router-dom';
import type { ReactNode } from 'react';
import { fetchRecommendations, fetchNews, fetchSectorTrends } from './api/client';
import type { RecommendationsResponse, NewsResponse, SectorTrendsResponse, RecommendationItem } from './types';
import { DataPreparingState } from './components/DataPreparingState';
import { RecommendationList } from './components/RecommendationList';
import { RecommendationFilterBar } from './components/RecommendationFilterBar';
import type { FilterState } from './components/RecommendationFilterBar';
import { DEFAULT_FILTERS } from './components/RecommendationFilterBar';
import { NewsFeed } from './components/NewsFeed';
import { Disclaimer } from './components/Disclaimer';
import { SectorTrendChart } from './components/SectorTrendChart';
import { StockDetail } from './components/StockDetail';
import { EtfRecommendationList } from './components/EtfRecommendationList';
import { PortfolioSummary } from './components/PortfolioSummary';
import { StockSearchBar } from './components/StockSearchBar';
import StockDetailPage from './pages/StockDetailPage';
import { useAuth } from './auth/AuthContext';
import Login from './pages/Login';
import Portfolio from './pages/Portfolio';
import Backtest from './pages/Backtest';
import Watchlist from './pages/Watchlist';
import Settings from './pages/Settings';
import History from './pages/History';
import Sectors from './pages/Sectors';
import NotificationsPage from './pages/Notifications';
import AdviceHistory from './pages/AdviceHistory';
import Screener from './pages/Screener';
import { fetchUnreadCount } from './api/notifications';

const API_BASE_DASHBOARD = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

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

// 모바일 반응형 NavBar — 768px 미만에서 햄버거 메뉴 표시
function NavBar() {
  const { isAuthenticated, user, logout, token } = useAuth();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  // 미읽음 알림 수 — 30초마다 폴링 (REQ-FE-001)
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    if (!isAuthenticated || !token) {
      setUnreadCount(0);
      return;
    }
    const load = () => {
      fetchUnreadCount(token)
        .then(setUnreadCount)
        .catch(() => { /* 네트워크 오류 무시 */ });
    };
    load();
    const interval = setInterval(load, 30_000);
    return () => clearInterval(interval);
  }, [isAuthenticated, token]);

  function handleLogout() {
    logout();
    setMobileMenuOpen(false);
    void navigate('/');
  }

  function handleLinkClick() {
    setMobileMenuOpen(false);
  }

  const linkStyle: React.CSSProperties = {
    color: '#1976d2',
    textDecoration: 'none',
    fontWeight: 500,
    fontSize: '0.9rem',
  };

  return (
    <nav
      style={{
        marginBottom: '1.5rem',
        paddingBottom: '0.75rem',
        borderBottom: '2px solid #1976d2',
      }}
      aria-label="주 메뉴"
    >
      {/* 상단 행: 브랜드 + 햄버거 버튼(모바일) */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontWeight: 800, fontSize: '1.1rem', color: '#0d47a1' }}>
          한국 주식 추천
        </span>

        {/* 햄버거 버튼 — 모바일에서만 표시 */}
        <button
          className="nav-hamburger"
          onClick={() => setMobileMenuOpen((v) => !v)}
          aria-label={mobileMenuOpen ? '메뉴 닫기' : '메뉴 열기'}
          aria-expanded={mobileMenuOpen}
          style={{
            display: 'none', // CSS로 모바일 표시 처리
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            fontSize: '1.4rem',
            lineHeight: 1,
            color: '#1976d2',
            padding: '0.25rem',
          }}
        >
          {mobileMenuOpen ? '✕' : '☰'}
        </button>
      </div>

      {/* 네비게이션 링크 영역 */}
      <div
        className={`nav-links${mobileMenuOpen ? ' nav-links--open' : ''}`}
        style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginTop: '0.5rem', flexWrap: 'wrap' }}
      >
        <Link to="/" style={linkStyle} onClick={handleLinkClick}>홈</Link>
        <Link to="/history" style={linkStyle} onClick={handleLinkClick}>히스토리</Link>
        <Link to="/sectors" style={linkStyle} onClick={handleLinkClick}>섹터 분석</Link>
        <Link to="/portfolio" style={linkStyle} onClick={handleLinkClick}>포트폴리오</Link>
        <Link to="/backtest" style={linkStyle} onClick={handleLinkClick}>백테스트</Link>
        <Link to="/screener" style={linkStyle} onClick={handleLinkClick}>스크리너</Link>
        {isAuthenticated && <Link to="/watchlist" style={linkStyle} onClick={handleLinkClick}>관심 목록</Link>}
        {isAuthenticated && <Link to="/settings" style={linkStyle} onClick={handleLinkClick}>설정</Link>}
        {isAuthenticated && <Link to="/advice/history" style={linkStyle} onClick={handleLinkClick}>AI 조언</Link>}
        {isAuthenticated && (
          <Link
            to="/notifications"
            onClick={handleLinkClick}
            aria-label={`알림${unreadCount > 0 ? ` (미읽음 ${unreadCount}개)` : ''}`}
            style={{ ...linkStyle, position: 'relative', display: 'inline-flex', alignItems: 'center' }}
          >
            🔔
            {unreadCount > 0 && (
              <span
                style={{
                  position: 'absolute',
                  top: '-6px',
                  right: '-8px',
                  background: '#e53935',
                  color: '#fff',
                  borderRadius: '50%',
                  fontSize: '0.65rem',
                  fontWeight: 700,
                  minWidth: '16px',
                  height: '16px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  lineHeight: 1,
                  padding: '0 2px',
                }}
              >
                {unreadCount > 99 ? '99+' : unreadCount}
              </span>
            )}
          </Link>
        )}
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
            <Link to="/login" onClick={handleLinkClick} style={{ ...linkStyle, padding: '0.3rem 0.7rem', border: '1px solid #1976d2', borderRadius: '4px' }}>
              로그인
            </Link>
          )}
        </div>
      </div>

      {/* 반응형 CSS — style 태그로 인라인 삽입 */}
      <style>{`
        @media (max-width: 767px) {
          .nav-hamburger { display: block !important; }
          .nav-links { display: none !important; flex-direction: column; align-items: flex-start; }
          .nav-links--open { display: flex !important; }
          .nav-links > a { padding: 0.4rem 0; width: 100%; }
          .nav-links > div { margin-left: 0 !important; width: 100%; }
        }
      `}</style>
    </nav>
  );
}

// 메인 대시보드 컴포넌트
function Dashboard() {
  const [loadingState, setLoadingState] = useState<LoadingState>('loading');
  const [filterLoading, setFilterLoading] = useState(false);
  const [recommendations, setRecommendations] = useState<RecommendationsResponse | null>(null);
  const [newsData, setNewsData] = useState<NewsResponse | null>(null);
  const [sectorTrends, setSectorTrends] = useState<SectorTrendsResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterState>({ ...DEFAULT_FILTERS });
  // 선택된 종목 코드 (상세 모달 표시용)
  const [selectedKrxCode, setSelectedKrxCode] = useState<string | null>(null);

  // 필터 파라미터를 URL 쿼리스트링으로 조합
  function buildRecommendationsUrl(f: FilterState): string {
    const params = new URLSearchParams();
    params.set('limit', '10');
    if (f.sort !== 'score') params.set('sort', f.sort);
    if (f.sector !== '') params.set('sector', f.sector);
    if (f.minScore > 0) params.set('min_score', String(f.minScore));
    return `${API_BASE_DASHBOARD}/recommendations?${params.toString()}`;
  }

  // 초기 로드 — 뉴스·섹터는 최초 1회만 조회
  useEffect(() => {
    let cancelled = false;

    async function loadData() {
      try {
        setLoadingState('loading');
        // 초기 로드는 기존 fetchRecommendations 사용 (테스트 mock 호환)
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
    return () => { cancelled = true; };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // @MX:WARN: [AUTO] 필터 변경 시 추천 재조회 — 이전 recommendations는 유지하여 UX 보호
  // @MX:REASON: 네트워크 실패 시 목록 소멸을 방지; 로딩 상태는 filterLoading으로 구분
  const handleFilterChange = useCallback(async (newFilters: FilterState) => {
    setFilters(newFilters);
    setFilterLoading(true);
    try {
      const url = buildRecommendationsUrl(newFilters);
      const res = await fetch(url);
      if (!res.ok) throw new Error(`API 오류: ${res.status}`);
      const data = await res.json() as RecommendationsResponse;
      setRecommendations(data);
      setErrorMessage(null);
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : '필터 적용 중 오류가 발생했습니다.');
      // 이전 추천 목록 유지 — 목록 클리어 없음
    } finally {
      setFilterLoading(false);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

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

  // 멀티플렉스 WS — 대시보드 추천 종목 실시간 가격 (SPEC-STOCK-016 M5)
  const dashboardSymbols = useMemo(
    () => allRecommendations.map((i) => i.krx_code),
    [allRecommendations],
  );
  // livePrices는 RecommendationList props로 전달 가능하지만 현재는 대시보드 수준에서만 구독
  // 실제 UI 표시는 RecommendationList 내부의 LivePriceBadge가 담당 (하위 호환 유지)
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const _dashboardLivePrices = useLivePrices(dashboardSymbols);

  // 현재 추천 목록에서 고유 섹터 추출 (RecommendationItem에 sector 필드가 있을 경우)
  const availableSectors: string[] = Array.from(
    new Set(
      allRecommendations
        .map((item) => (item as RecommendationItem & { sector?: string }).sector)
        .filter((s): s is string => Boolean(s)),
    ),
  );

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
          <p style={{ fontSize: '0.875rem', color: '#666', marginBottom: '1rem' }}>
            기준일: <strong>{recommendations.trade_date}</strong>
          </p>

          {/* 종목 검색 바 */}
          <div style={{ marginBottom: '1rem' }}>
            <StockSearchBar onSelect={setSelectedKrxCode} />
          </div>

          {/* 추천 필터 바 */}
          <RecommendationFilterBar
            sectors={availableSectors}
            filters={filters}
            onFilterChange={(f) => { void handleFilterChange(f); }}
            isLoading={filterLoading}
          />

          {/* 필터 오류 — 목록은 유지하되 오류 메시지 표시 */}
          {errorMessage && loadingState === 'ready' && (
            <div
              role="alert"
              style={{
                padding: '0.6rem 1rem',
                backgroundColor: '#fff3e0',
                border: '1px solid #ffcc02',
                borderRadius: '4px',
                color: '#e65100',
                fontSize: '0.875rem',
                marginBottom: '1rem',
              }}
            >
              필터 적용 오류: {errorMessage}
            </div>
          )}

          {/* 섹터 트렌드 차트 */}
          {sectorTrends && (
            <div style={{ marginBottom: '2rem' }}>
              <SectorTrendChart trends={sectorTrends.trends} />
            </div>
          )}

          {/* 메인 콘텐츠 그리드 */}
          <div
            className="dashboard-grid"
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

          {/* 모바일 반응형 — 그리드 단일 컬럼 전환 */}
          <style>{`
            @media (max-width: 767px) {
              .dashboard-grid {
                grid-template-columns: 1fr !important;
              }
            }
          `}</style>
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

// AdviceHistory는 token prop을 받으므로 AuthContext에서 주입하는 래퍼 필요
function AdviceHistoryWrapper() {
  const { token } = useAuth();
  return <AdviceHistory token={token} />;
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
        <Route path="/watchlist" element={
          <ProtectedRoute><Watchlist /></ProtectedRoute>
        } />
        <Route path="/settings" element={
          <ProtectedRoute><Settings /></ProtectedRoute>
        } />
        <Route path="/history" element={<History />} />
        <Route path="/sectors" element={<Sectors />} />
        <Route path="/stocks/:krxCode" element={<StockDetailPage />} />
        <Route path="/notifications" element={
          <ProtectedRoute><NotificationsPage /></ProtectedRoute>
        } />
        <Route path="/advice/history" element={
          <ProtectedRoute><AdviceHistoryWrapper /></ProtectedRoute>
        } />
        <Route path="/screener" element={<Screener />} />
      </Routes>
    </div>
  );
}
