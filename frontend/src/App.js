import { jsx as _jsx, Fragment as _Fragment, jsxs as _jsxs } from "react/jsx-runtime";
// 메인 앱 — 라우팅 및 네비게이션 포함
import { useEffect, useState } from 'react';
import { Routes, Route, Link, useNavigate, Navigate } from 'react-router-dom';
import { fetchRecommendations, fetchNews, fetchSectorTrends } from './api/client';
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
import Watchlist from './pages/Watchlist';
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
// 상단 네비게이션 바
function NavBar() {
    const { isAuthenticated, user, logout } = useAuth();
    const navigate = useNavigate();
    function handleLogout() {
        logout();
        void navigate('/');
    }
    const navStyle = {
        display: 'flex',
        alignItems: 'center',
        gap: '1rem',
        marginBottom: '1.5rem',
        paddingBottom: '0.75rem',
        borderBottom: '2px solid #1976d2',
        flexWrap: 'wrap',
    };
    const linkStyle = {
        color: '#1976d2',
        textDecoration: 'none',
        fontWeight: 500,
        fontSize: '0.9rem',
    };
    return (_jsxs("nav", { style: navStyle, "aria-label": "\uC8FC \uBA54\uB274", children: [_jsx("span", { style: { fontWeight: 800, fontSize: '1.1rem', color: '#0d47a1', marginRight: '0.5rem' }, children: "\uD55C\uAD6D \uC8FC\uC2DD \uCD94\uCC9C" }), _jsx(Link, { to: "/", style: linkStyle, children: "\uD648" }), _jsx(Link, { to: "/portfolio", style: linkStyle, children: "\uD3EC\uD2B8\uD3F4\uB9AC\uC624" }), _jsx(Link, { to: "/backtest", style: linkStyle, children: "\uBC31\uD14C\uC2A4\uD2B8" }), isAuthenticated && _jsx(Link, { to: "/watchlist", style: linkStyle, children: "\uAD00\uC2EC \uBAA9\uB85D" }), _jsx("div", { style: { marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '0.75rem' }, children: isAuthenticated ? (_jsxs(_Fragment, { children: [_jsx("span", { style: { fontSize: '0.8rem', color: '#666' }, children: user?.email }), _jsx("button", { onClick: handleLogout, style: {
                                padding: '0.3rem 0.7rem', border: '1px solid #ccc', borderRadius: '4px',
                                background: '#fff', cursor: 'pointer', fontSize: '0.8rem',
                            }, children: "\uB85C\uADF8\uC544\uC6C3" })] })) : (_jsx(Link, { to: "/login", style: { ...linkStyle, padding: '0.3rem 0.7rem', border: '1px solid #1976d2', borderRadius: '4px' }, children: "\uB85C\uADF8\uC778" })) })] }));
}
// 메인 대시보드 컴포넌트
function Dashboard() {
    const [loadingState, setLoadingState] = useState('loading');
    const [recommendations, setRecommendations] = useState(null);
    const [newsData, setNewsData] = useState(null);
    const [sectorTrends, setSectorTrends] = useState(null);
    const [errorMessage, setErrorMessage] = useState(null);
    // 선택된 종목 코드 (상세 모달 표시용)
    const [selectedKrxCode, setSelectedKrxCode] = useState(null);
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
        return () => {
            cancelled = true;
        };
    }, []);
    const disclaimerText = recommendations && 'disclaimer' in recommendations
        ? recommendations.disclaimer
        : '이 정보는 투자 참고용입니다. 실제 투자 결정은 본인 책임하에 이루어져야 합니다.';
    // 추천 목록을 일반 주식 / ETF로 분류
    const allRecommendations = recommendations && isRecommendationsData(recommendations)
        ? recommendations.recommendations
        : [];
    const stockItems = allRecommendations.filter((item) => !isEtfCode(item.krx_code));
    const etfItems = allRecommendations.filter((item) => isEtfCode(item.krx_code));
    return (_jsxs("div", { children: [_jsx("div", { style: { marginBottom: '1.5rem' }, children: _jsx(PortfolioSummary, {}) }), loadingState === 'loading' && (_jsx("div", { role: "status", "aria-live": "polite", style: { textAlign: 'center', padding: '3rem', color: '#666' }, children: _jsx("p", { children: "\uB370\uC774\uD130\uB97C \uBD88\uB7EC\uC624\uB294 \uC911..." }) })), loadingState === 'error' && (_jsxs("div", { role: "alert", style: {
                    padding: '1rem',
                    backgroundColor: '#ffebee',
                    border: '1px solid #ef9a9a',
                    borderRadius: '4px',
                    color: '#c62828',
                }, children: [_jsx("strong", { children: "\uC624\uB958:" }), " ", errorMessage] })), loadingState === 'ready' && recommendations && !isRecommendationsData(recommendations) && (_jsx(DataPreparingState, {})), loadingState === 'ready' && recommendations && isRecommendationsData(recommendations) && (_jsxs("div", { children: [_jsxs("p", { style: { fontSize: '0.875rem', color: '#666', marginBottom: '1.5rem' }, children: ["\uAE30\uC900\uC77C: ", _jsx("strong", { children: recommendations.trade_date })] }), sectorTrends && (_jsx("div", { style: { marginBottom: '2rem' }, children: _jsx(SectorTrendChart, { trends: sectorTrends.trends }) })), _jsxs("div", { style: {
                            display: 'grid',
                            gridTemplateColumns: 'minmax(0, 3fr) minmax(0, 2fr)',
                            gap: '2rem',
                            alignItems: 'start',
                            marginBottom: '2rem',
                        }, children: [_jsx(RecommendationList, { recommendations: stockItems.length > 0 ? stockItems : recommendations.recommendations, onSelect: setSelectedKrxCode }), newsData && _jsx(NewsFeed, { news: newsData.news })] }), etfItems.length > 0 && (_jsx("div", { style: { marginBottom: '2rem' }, children: _jsx(EtfRecommendationList, { etfItems: etfItems, onSelect: setSelectedKrxCode }) }))] })), _jsx(Disclaimer, { text: disclaimerText }), selectedKrxCode && (_jsx(StockDetail, { krxCode: selectedKrxCode, onClose: () => setSelectedKrxCode(null) }))] }));
}
export default function App() {
    return (_jsxs("div", { style: {
            maxWidth: '1100px',
            margin: '0 auto',
            padding: '1.5rem',
            fontFamily: "'Segoe UI', 'Apple SD Gothic Neo', sans-serif",
        }, children: [_jsx(NavBar, {}), _jsxs(Routes, { children: [_jsx(Route, { path: "/", element: _jsx(Dashboard, {}) }), _jsx(Route, { path: "/login", element: _jsx(Login, {}) }), _jsx(Route, { path: "/portfolio", element: _jsx(ProtectedRoute, { children: _jsx(Portfolio, {}) }) }), _jsx(Route, { path: "/backtest", element: _jsx(ProtectedRoute, { children: _jsx(Backtest, {}) }) }), _jsx(Route, { path: "/watchlist", element: _jsx(ProtectedRoute, { children: _jsx(Watchlist, {}) }) })] })] }));
}
