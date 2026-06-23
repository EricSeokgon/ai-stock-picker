// 포트폴리오 API 래퍼 (Bearer 토큰 필요)
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
// @MX:ANCHOR: [AUTO] 포트폴리오 API 공통 헤더 생성 — Portfolio/Backtest/AuthContext에서 호출
// @MX:REASON: Bearer 토큰 헤더 패턴이 3개 모듈에서 공유됨
function authHeaders(token) {
    return {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
    };
}
// 포트폴리오 목록 조회
export async function apiListPortfolios(token) {
    const res = await fetch(`${API_BASE}/portfolios`, {
        headers: authHeaders(token),
    });
    if (!res.ok)
        throw new Error(`포트폴리오 조회 실패: ${res.status}`);
    return res.json();
}
// 포트폴리오 생성
export async function apiCreatePortfolio(token, name, description) {
    const res = await fetch(`${API_BASE}/portfolios`, {
        method: 'POST',
        headers: authHeaders(token),
        body: JSON.stringify({ name, description }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `포트폴리오 생성 실패: ${res.status}`);
    }
    return res.json();
}
// 보유 종목 조회
export async function apiListHoldings(token, portfolioId) {
    const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/holdings`, {
        headers: authHeaders(token),
    });
    if (!res.ok)
        throw new Error(`보유 종목 조회 실패: ${res.status}`);
    return res.json();
}
// 보유 종목 추가 (SPEC-STOCK-028: market/currency 파라미터 추가, 기본값으로 역방향 호환)
export async function apiAddHolding(token, portfolioId, krx_code, quantity, avg_buy_price, market = 'KRX', currency = 'KRW') {
    const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/holdings`, {
        method: 'POST',
        headers: authHeaders(token),
        body: JSON.stringify({ krx_code, quantity, avg_buy_price, market, currency }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `종목 추가 실패: ${res.status}`);
    }
    return res.json();
}
// 포트폴리오 성과 조회
export async function apiGetPerformance(token, portfolioId) {
    const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/performance`, {
        headers: authHeaders(token),
    });
    if (!res.ok)
        throw new Error(`성과 조회 실패: ${res.status}`);
    return res.json();
}
// 포트폴리오 AI 최적화 분석 호출 (SPEC-STOCK-026)
export async function apiOptimizePortfolio(token, portfolioId, refresh = false) {
    const url = `${API_BASE}/portfolios/${portfolioId}/optimize${refresh ? '?refresh=true' : ''}`;
    const res = await fetch(url, {
        method: 'POST',
        headers: authHeaders(token),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `최적화 분석 실패: ${res.status}`);
    }
    return res.json();
}
// @MX:ANCHOR: [AUTO] 리스크 분석 API 공개 엔드포인트 — RiskAnalysisPanel에서 호출
// @MX:REASON: 외부 시스템(백엔드 /portfolios/{id}/risk-analysis) 연동 지점으로 fan_in >= 3 예상
export async function apiGetRiskAnalysis(token, portfolioId, period = 90, refresh = false) {
    const params = new URLSearchParams({ period: String(period) });
    if (refresh)
        params.set('refresh', 'true');
    const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/risk-analysis?${params.toString()}`, {
        headers: authHeaders(token),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `리스크 분석 조회 실패: ${res.status}`);
    }
    return res.json();
}
// @MX:ANCHOR: [AUTO] 기간별 성과 요약 API 엔드포인트 (SPEC-STOCK-030)
// @MX:REASON: [AUTO] PerformanceSummaryPanel, Portfolio 페이지, 테스트에서 3곳 이상 참조
export async function apiGetPerformanceSummary(token, portfolioId, refresh = false) {
    const url = new URL(`${API_BASE}/portfolios/${portfolioId}/performance-summary`);
    if (refresh) url.searchParams.set('refresh', 'true');
    const res = await fetch(url.toString(), { headers: authHeaders(token) });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `성과 요약 조회 실패: ${res.status}`);
    }
    return res.json();
}
// ── SPEC-STOCK-031: 포트폴리오 알림 API 함수 ──────────────────────────────────
// @MX:NOTE: [AUTO] 포트폴리오 알림 목록 조회 (SPEC-STOCK-031 REQ-PAL-001)
export async function apiListPortfolioAlerts(token, portfolioId) {
    const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/alerts`, {
        headers: authHeaders(token),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `알림 목록 조회 실패: ${res.status}`);
    }
    return res.json();
}
// @MX:NOTE: [AUTO] 포트폴리오 알림 생성 (SPEC-STOCK-031 REQ-PAL-001)
export async function apiCreatePortfolioAlert(token, portfolioId, data) {
    const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/alerts`, {
        method: 'POST',
        headers: authHeaders(token),
        body: JSON.stringify(data),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `알림 생성 실패: ${res.status}`);
    }
    return res.json();
}
// @MX:NOTE: [AUTO] 포트폴리오 알림 수정 (SPEC-STOCK-031 REQ-PAL-001)
export async function apiUpdatePortfolioAlert(token, portfolioId, alertId, data) {
    const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/alerts/${alertId}`, {
        method: 'PATCH',
        headers: authHeaders(token),
        body: JSON.stringify(data),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `알림 수정 실패: ${res.status}`);
    }
    return res.json();
}
// @MX:NOTE: [AUTO] 포트폴리오 알림 삭제 (SPEC-STOCK-031 REQ-PAL-001)
export async function apiDeletePortfolioAlert(token, portfolioId, alertId) {
    const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/alerts/${alertId}`, {
        method: 'DELETE',
        headers: authHeaders(token),
    });
    if (!res.ok && res.status !== 204) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `알림 삭제 실패: ${res.status}`);
    }
}

// @MX:ANCHOR: [AUTO] 백테스팅 API 공개 엔드포인트 — BacktestPanel에서 호출
// @MX:REASON: 외부 시스템(백엔드 /portfolios/{id}/backtest) 연동 지점으로 fan_in >= 3 예상
export async function runPortfolioBacktest(token, portfolioId, startDate, endDate) {
    const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/backtest`, {
        method: 'POST',
        headers: authHeaders(token),
        body: JSON.stringify({ start_date: startDate, end_date: endDate }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `백테스팅 실패: ${res.status}`);
    }
    return res.json();
}
