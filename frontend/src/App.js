import { jsx as _jsx, Fragment as _Fragment, jsxs as _jsxs } from "react/jsx-runtime";
// 메인 앱 — 라우팅 및 네비게이션 포함
import { useEffect, useState, useCallback } from 'react';
import { Routes, Route, Link, useNavigate, Navigate } from 'react-router-dom';
import { fetchRecommendations, fetchNews, fetchSectorTrends } from './api/client';
import { DataPreparingState } from './components/DataPreparingState';
import { RecommendationList } from './components/RecommendationList';
import { RecommendationFilterBar } from './components/RecommendationFilterBar';
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
const API_BASE_DASHBOARD = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
// KRX ETF 코드 패턴: 0으로 시작하는 6자리 숫자 중 ETF로 분류된 코드들
// Phase 2 MVP: recommendations에서 ETF로 알려진 코드 패턴으로 분류
// 실제 구분은 백엔드 asset_type 필드 추가 시 교체 예정
const ETF_PREFIXES = ['069', '102', '114', '148', '152', '229', '251', '261', '278', '292', '305'];
function isEtfCode(krxCode) {
    return ETF_PREFIXES.some((prefix) => krxCode.startsWith(prefix));
}
// RecommendationsResponse에 recommendations 속성이 있는지 확인
function isRecommendationsData(data) {
    return 'recommendations' in data;
}
// 인증이 필요한 라우트 — 미로그인 시 /login으로 이동
function ProtectedRoute({ children }) {
    const { isAuthenticated } = useAuth();
    if (!isAuthenticated)
        return _jsx(Navigate, { to: "/login", replace: true });
    return _jsx(_Fragment, { children: children });
}
// 모바일 반응형 NavBar — 768px 미만에서 햄버거 메뉴 표시
function NavBar() {
    const { isAuthenticated, user, logout } = useAuth();
    const navigate = useNavigate();
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    function handleLogout() {
        logout();
        setMobileMenuOpen(false);
        void navigate('/');
    }
    function handleLinkClick() {
        setMobileMenuOpen(false);
    }
    const linkStyle = {
        color: '#1976d2',
        textDecoration: 'none',
        fontWeight: 500,
        fontSize: '0.9rem',
    };
    return (_jsxs("nav", { style: {
            marginBottom: '1.5rem',
            paddingBottom: '0.75rem',
            borderBottom: '2px solid #1976d2',
        }, "aria-label": "\uC8FC \uBA54\uB274", children: [_jsxs("div", { style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between' }, children: [_jsx("span", { style: { fontWeight: 800, fontSize: '1.1rem', color: '#0d47a1' }, children: "\uD55C\uAD6D \uC8FC\uC2DD \uCD94\uCC9C" }), _jsx("button", { className: "nav-hamburger", onClick: () => setMobileMenuOpen((v) => !v), "aria-label": mobileMenuOpen ? '메뉴 닫기' : '메뉴 열기', "aria-expanded": mobileMenuOpen, style: {
                            display: 'none', // CSS로 모바일 표시 처리
                            background: 'none',
                            border: 'none',
                            cursor: 'pointer',
                            fontSize: '1.4rem',
                            lineHeight: 1,
                            color: '#1976d2',
                            padding: '0.25rem',
                        }, children: mobileMenuOpen ? '✕' : '☰' })] }), _jsxs("div", { className: `nav-links${mobileMenuOpen ? ' nav-links--open' : ''}`, style: { display: 'flex', alignItems: 'center', gap: '1rem', marginTop: '0.5rem', flexWrap: 'wrap' }, children: [_jsx(Link, { to: "/", style: linkStyle, onClick: handleLinkClick, children: "\uD648" }), _jsx(Link, { to: "/history", style: linkStyle, onClick: handleLinkClick, children: "\uD788\uC2A4\uD1A0\uB9AC" }), _jsx(Link, { to: "/sectors", style: linkStyle, onClick: handleLinkClick, children: "\uC139\uD130 \uBD84\uC11D" }), _jsx(Link, { to: "/portfolio", style: linkStyle, onClick: handleLinkClick, children: "\uD3EC\uD2B8\uD3F4\uB9AC\uC624" }), _jsx(Link, { to: "/backtest", style: linkStyle, onClick: handleLinkClick, children: "\uBC31\uD14C\uC2A4\uD2B8" }), isAuthenticated && _jsx(Link, { to: "/watchlist", style: linkStyle, onClick: handleLinkClick, children: "\uAD00\uC2EC \uBAA9\uB85D" }), isAuthenticated && _jsx(Link, { to: "/settings", style: linkStyle, onClick: handleLinkClick, children: "\uC124\uC815" }), _jsx("div", { style: { marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '0.75rem' }, children: isAuthenticated ? (_jsxs(_Fragment, { children: [_jsx("span", { style: { fontSize: '0.8rem', color: '#666' }, children: user?.email }), _jsx("button", { onClick: handleLogout, style: {
                                        padding: '0.3rem 0.7rem', border: '1px solid #ccc', borderRadius: '4px',
                                        background: '#fff', cursor: 'pointer', fontSize: '0.8rem',
                                    }, children: "\uB85C\uADF8\uC544\uC6C3" })] })) : (_jsx(Link, { to: "/login", onClick: handleLinkClick, style: { ...linkStyle, padding: '0.3rem 0.7rem', border: '1px solid #1976d2', borderRadius: '4px' }, children: "\uB85C\uADF8\uC778" })) })] }), _jsx("style", { children: `
        @media (max-width: 767px) {
          .nav-hamburger { display: block !important; }
          .nav-links { display: none !important; flex-direction: column; align-items: flex-start; }
          .nav-links--open { display: flex !important; }
          .nav-links > a { padding: 0.4rem 0; width: 100%; }
          .nav-links > div { margin-left: 0 !important; width: 100%; }
        }
      ` })] }));
}
// 메인 대시보드 컴포넌트
function Dashboard() {
    const [loadingState, setLoadingState] = useState('loading');
    const [filterLoading, setFilterLoading] = useState(false);
    const [recommendations, setRecommendations] = useState(null);
    const [newsData, setNewsData] = useState(null);
    const [sectorTrends, setSectorTrends] = useState(null);
    const [errorMessage, setErrorMessage] = useState(null);
    const [filters, setFilters] = useState({ ...DEFAULT_FILTERS });
    // 선택된 종목 코드 (상세 모달 표시용)
    const [selectedKrxCode, setSelectedKrxCode] = useState(null);
    // 필터 파라미터를 URL 쿼리스트링으로 조합
    function buildRecommendationsUrl(f) {
        const params = new URLSearchParams();
        params.set('limit', '10');
        if (f.sort !== 'score')
            params.set('sort', f.sort);
        if (f.sector !== '')
            params.set('sector', f.sector);
        if (f.minScore > 0)
            params.set('min_score', String(f.minScore));
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
                if (cancelled)
                    return;
                setRecommendations(rec);
                setNewsData(news);
                setSectorTrends(trends);
                setLoadingState('ready');
            }
            catch (err) {
                if (cancelled)
                    return;
                setErrorMessage(err instanceof Error ? err.message : '데이터를 불러오는 중 오류가 발생했습니다.');
                setLoadingState('error');
            }
        }
        void loadData();
        return () => { cancelled = true; };
    }, []); // eslint-disable-line react-hooks/exhaustive-deps
    // @MX:WARN: [AUTO] 필터 변경 시 추천 재조회 — 이전 recommendations는 유지하여 UX 보호
    // @MX:REASON: 네트워크 실패 시 목록 소멸을 방지; 로딩 상태는 filterLoading으로 구분
    const handleFilterChange = useCallback(async (newFilters) => {
        setFilters(newFilters);
        setFilterLoading(true);
        try {
            const url = buildRecommendationsUrl(newFilters);
            const res = await fetch(url);
            if (!res.ok)
                throw new Error(`API 오류: ${res.status}`);
            const data = await res.json();
            setRecommendations(data);
            setErrorMessage(null);
        }
        catch (err) {
            setErrorMessage(err instanceof Error ? err.message : '필터 적용 중 오류가 발생했습니다.');
            // 이전 추천 목록 유지 — 목록 클리어 없음
        }
        finally {
            setFilterLoading(false);
        }
    }, []); // eslint-disable-line react-hooks/exhaustive-deps
    const disclaimerText = recommendations && 'disclaimer' in recommendations
        ? recommendations.disclaimer
        : '이 정보는 투자 참고용입니다. 실제 투자 결정은 본인 책임하에 이루어져야 합니다.';
    // 추천 목록을 일반 주식 / ETF로 분류
    const allRecommendations = recommendations && isRecommendationsData(recommendations)
        ? recommendations.recommendations
        : [];
    const stockItems = allRecommendations.filter((item) => !isEtfCode(item.krx_code));
    const etfItems = allRecommendations.filter((item) => isEtfCode(item.krx_code));
    // 현재 추천 목록에서 고유 섹터 추출 (RecommendationItem에 sector 필드가 있을 경우)
    const availableSectors = Array.from(new Set(allRecommendations
        .map((item) => item.sector)
        .filter((s) => Boolean(s))));
    return (_jsxs("div", { children: [_jsx("div", { style: { marginBottom: '1.5rem' }, children: _jsx(PortfolioSummary, {}) }), loadingState === 'loading' && (_jsx("div", { role: "status", "aria-live": "polite", style: { textAlign: 'center', padding: '3rem', color: '#666' }, children: _jsx("p", { children: "\uB370\uC774\uD130\uB97C \uBD88\uB7EC\uC624\uB294 \uC911..." }) })), loadingState === 'error' && (_jsxs("div", { role: "alert", style: {
                    padding: '1rem',
                    backgroundColor: '#ffebee',
                    border: '1px solid #ef9a9a',
                    borderRadius: '4px',
                    color: '#c62828',
                }, children: [_jsx("strong", { children: "\uC624\uB958:" }), " ", errorMessage] })), loadingState === 'ready' && recommendations && !isRecommendationsData(recommendations) && (_jsx(DataPreparingState, {})), loadingState === 'ready' && recommendations && isRecommendationsData(recommendations) && (_jsxs("div", { children: [_jsxs("p", { style: { fontSize: '0.875rem', color: '#666', marginBottom: '1rem' }, children: ["\uAE30\uC900\uC77C: ", _jsx("strong", { children: recommendations.trade_date })] }), _jsx("div", { style: { marginBottom: '1rem' }, children: _jsx(StockSearchBar, { onSelect: setSelectedKrxCode }) }), _jsx(RecommendationFilterBar, { sectors: availableSectors, filters: filters, onFilterChange: (f) => { void handleFilterChange(f); }, isLoading: filterLoading }), errorMessage && loadingState === 'ready' && (_jsxs("div", { role: "alert", style: {
                            padding: '0.6rem 1rem',
                            backgroundColor: '#fff3e0',
                            border: '1px solid #ffcc02',
                            borderRadius: '4px',
                            color: '#e65100',
                            fontSize: '0.875rem',
                            marginBottom: '1rem',
                        }, children: ["\uD544\uD130 \uC801\uC6A9 \uC624\uB958: ", errorMessage] })), sectorTrends && (_jsx("div", { style: { marginBottom: '2rem' }, children: _jsx(SectorTrendChart, { trends: sectorTrends.trends }) })), _jsxs("div", { className: "dashboard-grid", style: {
                            display: 'grid',
                            gridTemplateColumns: 'minmax(0, 3fr) minmax(0, 2fr)',
                            gap: '2rem',
                            alignItems: 'start',
                            marginBottom: '2rem',
                        }, children: [_jsx(RecommendationList, { recommendations: stockItems.length > 0 ? stockItems : recommendations.recommendations, onSelect: setSelectedKrxCode }), newsData && _jsx(NewsFeed, { news: newsData.news })] }), etfItems.length > 0 && (_jsx("div", { style: { marginBottom: '2rem' }, children: _jsx(EtfRecommendationList, { etfItems: etfItems, onSelect: setSelectedKrxCode }) })), _jsx("style", { children: `
            @media (max-width: 767px) {
              .dashboard-grid {
                grid-template-columns: 1fr !important;
              }
            }
          ` })] })), _jsx(Disclaimer, { text: disclaimerText }), selectedKrxCode && (_jsx(StockDetail, { krxCode: selectedKrxCode, onClose: () => setSelectedKrxCode(null) }))] }));
}
export default function App() {
    return (_jsxs("div", { style: {
            maxWidth: '1100px',
            margin: '0 auto',
            padding: '1.5rem',
            fontFamily: "'Segoe UI', 'Apple SD Gothic Neo', sans-serif",
        }, children: [_jsx(NavBar, {}), _jsxs(Routes, { children: [_jsx(Route, { path: "/", element: _jsx(Dashboard, {}) }), _jsx(Route, { path: "/login", element: _jsx(Login, {}) }), _jsx(Route, { path: "/portfolio", element: _jsx(ProtectedRoute, { children: _jsx(Portfolio, {}) }) }), _jsx(Route, { path: "/backtest", element: _jsx(ProtectedRoute, { children: _jsx(Backtest, {}) }) }), _jsx(Route, { path: "/watchlist", element: _jsx(ProtectedRoute, { children: _jsx(Watchlist, {}) }) }), _jsx(Route, { path: "/settings", element: _jsx(ProtectedRoute, { children: _jsx(Settings, {}) }) }), _jsx(Route, { path: "/history", element: _jsx(History, {}) }), _jsx(Route, { path: "/sectors", element: _jsx(Sectors, {}) }), _jsx(Route, { path: "/stocks/:krxCode", element: _jsx(StockDetailPage, {}) })] })] }));
}
