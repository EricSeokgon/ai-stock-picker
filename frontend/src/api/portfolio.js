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
/** KRX 장 개장 여부 조회 (인증 불필요, SPEC-039 REQ-MS-001). */
export async function apiGetMarketStatus() {
    const res = await fetch(`${API_BASE}/portfolios/market-status`);
    if (!res.ok)
        throw new Error(`시장 상태 조회 실패: ${res.status}`);
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
    if (refresh)
        url.searchParams.set('refresh', 'true');
    const res = await fetch(url.toString(), { headers: authHeaders(token) });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `성과 요약 조회 실패: ${res.status}`);
    }
    return res.json();
}
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
// @MX:ANCHOR: [AUTO] 배당 수익률 요약 API — DividendSummaryPanel에서 호출
// @MX:REASON: 백엔드 /portfolios/{id}/dividend/summary 연동, fan_in >= 3 예상
export async function apiGetDividendSummary(token, portfolioId) {
    const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/dividend/summary`, {
        headers: authHeaders(token),
    });
    if (!res.ok)
        throw new Error(`배당 수익률 요약 조회 실패: ${res.status}`);
    return res.json();
}
// 배당 캘린더 조회 (연도 파라미터 선택 — 기본값: 현재 연도)
export async function apiGetDividendCalendar(token, portfolioId, year = null) {
    const params = year ? `?year=${year}` : '';
    const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/dividend/calendar${params}`, { headers: authHeaders(token) });
    if (!res.ok)
        throw new Error(`배당 캘린더 조회 실패: ${res.status}`);
    return res.json();
}
// @MX:ANCHOR: [AUTO] DRIP 시뮬레이션 API — DRIPSimulator에서 호출
// @MX:REASON: 백엔드 /portfolios/{id}/dividend/drip 연동, fan_in >= 3 예상
export async function apiGetDRIPProjection(token, portfolioId, years = 10, reinvestRate = 1.0) {
    const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/dividend/drip?years=${years}&reinvest_rate=${reinvestRate}`, { headers: authHeaders(token) });
    if (!res.ok)
        throw new Error(`DRIP 시뮬레이션 조회 실패: ${res.status}`);
    return res.json();
}
// 벤치마크 비교 조회 (SPEC-STOCK-034 REQ-BMK-001~004)
export async function apiGetBenchmarkComparison(token, portfolioId, benchmark = 'KOSPI', period = '1Y') {
    const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/benchmark?benchmark=${benchmark}&period=${period}`, { headers: authHeaders(token) });
    if (!res.ok)
        throw new Error(`벤치마크 비교 조회 실패: ${res.status}`);
    return res.json();
}
// 벤치마크 비교 재기준화 차트 조회 (SPEC-STOCK-034 REQ-BMK-010)
export async function apiGetBenchmarkChart(token, portfolioId, benchmark = 'KOSPI', period = '1Y') {
    const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/benchmark/chart?benchmark=${benchmark}&period=${period}`, { headers: authHeaders(token) });
    if (!res.ok)
        throw new Error(`벤치마크 차트 조회 실패: ${res.status}`);
    return res.json();
}
// 리포트 JSON 요약 또는 CSV Blob 조회 (SPEC-STOCK-035 REQ-RPT-001)
export async function apiGetPortfolioReport(token, portfolioId, format = 'json', period = 'YTD') {
    const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/report?format=${format}&period=${period}`, { headers: authHeaders(token) });
    if (!res.ok)
        throw new Error(`포트폴리오 리포트 조회 실패: ${res.status}`);
    if (format === 'csv') {
        return res.blob();
    }
    return res.json();
}
// 리포트 종합 요약 조회 (SPEC-STOCK-035 REQ-RPT-002)
export async function apiGetPortfolioReportSummary(token, portfolioId, period = 'YTD', includeDividend = false, includeBenchmark = false, benchmark = 'KOSPI') {
    const params = new URLSearchParams({
        period,
        include_dividend: String(includeDividend),
        include_benchmark: String(includeBenchmark),
        benchmark,
    });
    const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/report/summary?${params}`, { headers: authHeaders(token) });
    if (!res.ok)
        throw new Error(`포트폴리오 리포트 요약 조회 실패: ${res.status}`);
    return res.json();
}
// 월별 스냅샷 생성/업데이트 (SPEC-STOCK-035 REQ-RPT-004)
export async function apiCreateMonthlySnapshot(token, portfolioId, month = null) {
    const body = month ? { month } : {};
    const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/report/snapshot`, {
        method: 'POST',
        headers: authHeaders(token),
        body: JSON.stringify(body),
    });
    if (!res.ok)
        throw new Error(`월별 스냅샷 생성 실패: ${res.status}`);
    return res.json();
}
// 월별 스냅샷 목록 조회 (SPEC-STOCK-035 REQ-RPT-004)
export async function apiListMonthlySnapshots(token, portfolioId, limit = 24) {
    const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/report/snapshots?limit=${limit}`, { headers: authHeaders(token) });
    if (!res.ok)
        throw new Error(`월별 스냅샷 목록 조회 실패: ${res.status}`);
    return res.json();
}
// 알림 온디맨드 평가 (SPEC-STOCK-036 REQ-PAL-036-003)
export async function apiEvaluateAlerts(token, portfolioId) {
    const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/alerts/evaluate`, { method: 'POST', headers: authHeaders(token) });
    if (!res.ok)
        throw new Error(`알림 평가 실패: ${res.status}`);
    return res.json();
}
// 알림 히스토리 조회 (SPEC-STOCK-036 REQ-PAL-036-004)
export async function apiGetAlertHistory(token, portfolioId) {
    const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/alerts/history`, { headers: authHeaders(token) });
    if (!res.ok)
        throw new Error(`알림 히스토리 조회 실패: ${res.status}`);
    return res.json();
}
// @MX:ANCHOR: [AUTO] 포트폴리오 공유 API — SharePanel, Portfolio 페이지에서 호출
// @MX:REASON: 공유 생성/삭제/조회 세 함수가 공통 엔드포인트를 사용하는 외부 시스템 연동 지점
export async function apiCreateShare(token, portfolioId) {
    const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/share`, {
        method: 'POST',
        headers: authHeaders(token),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `공유 링크 생성 실패: ${res.status}`);
    }
    return res.json();
}
// 포트폴리오 공유 비활성화 (SPEC-STOCK-042)
export async function apiDeleteShare(token, portfolioId) {
    const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/share`, {
        method: 'DELETE',
        headers: authHeaders(token),
    });
    if (!res.ok && res.status !== 204) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `공유 비활성화 실패: ${res.status}`);
    }
}
// 포트폴리오 현재 공유 상태 조회 — 없으면 null 반환 (SPEC-STOCK-042)
export async function apiGetShare(token, portfolioId) {
    const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/share`, {
        headers: authHeaders(token),
    });
    if (res.status === 204)
        return null;
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `공유 상태 조회 실패: ${res.status}`);
    }
    return res.json();
}
// 포트폴리오 공유 7일 조회 통계 (SPEC-STOCK-044)
export async function getShareStats(token, portfolioId) {
    const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/share/stats`, {
        headers: authHeaders(token),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `통계 조회 실패: ${res.status}`);
    }
    return res.json();
}
// AI 포트폴리오 코멘터리 조회 (SPEC-STOCK-040 REQ-CMNT-001)
export async function getAICommentary(token, portfolioId) {
    const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/ai-commentary`, { headers: authHeaders(token) });
    if (!res.ok)
        throw new Error(`AI 코멘터리 조회 실패: ${res.status}`);
    return res.json();
}
// 포트폴리오 목표 조회 (REQ-GOAL-002) — 활성 목표 없으면 null
export async function getPortfolioGoal(token, portfolioId) {
    const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/goals`, { headers: authHeaders(token) });
    if (res.status === 204)
        return null; // 활성 목표 없음
    if (!res.ok)
        throw new Error(`목표 조회 실패: ${res.status}`);
    return res.json();
}
// 포트폴리오 목표 생성 (REQ-GOAL-001)
export async function createPortfolioGoal(token, portfolioId, payload) {
    const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/goals`, {
        method: 'POST',
        headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });
    if (!res.ok)
        throw new Error(`목표 생성 실패: ${res.status}`);
    return res.json();
}
// 포트폴리오 목표 삭제 (REQ-GOAL-003)
export async function deletePortfolioGoal(token, portfolioId, goalId) {
    const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/goals/${goalId}`, { method: 'DELETE', headers: authHeaders(token) });
    if (!res.ok && res.status !== 204)
        throw new Error(`목표 삭제 실패: ${res.status}`);
}
