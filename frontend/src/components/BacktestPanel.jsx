// 포트폴리오 백테스팅 패널 컴포넌트 (SPEC-STOCK-029)
// 날짜 입력 → API 호출 → 지표 표시 + 차트
import React, { useState } from 'react';
import { runPortfolioBacktest } from '../api/portfolio.js';
import { BacktestChart } from './BacktestChart.jsx';

/**
 * 수익률/MDD 포맷 헬퍼
 * @param {number} value 소수 (e.g. 0.12 → "12.00%")
 * @returns {string}
 */
function fmtPct(value) {
    if (typeof value !== 'number' || isNaN(value))
        return '-';
    return `${(value * 100).toFixed(2)}%`;
}

/**
 * 포트폴리오 백테스팅 패널
 *
 * @param {{ token: string, portfolioId: number }} props
 */
export function BacktestPanel({ token, portfolioId }) {
    // 오늘 날짜 기본값 (종료), 1년 전 (시작)
    const today = new Date().toISOString().slice(0, 10);
    const oneYearAgo = new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);

    const [startDate, setStartDate] = useState(oneYearAgo);
    const [endDate, setEndDate] = useState(today);
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    async function handleRun() {
        if (!startDate || !endDate) {
            setError('시작일과 종료일을 입력해주세요.');
            return;
        }
        if (startDate >= endDate) {
            setError('시작일은 종료일보다 이전이어야 합니다.');
            return;
        }
        setLoading(true);
        setError(null);
        setResult(null);
        try {
            const data = await runPortfolioBacktest(token, portfolioId, startDate, endDate);
            setResult(data);
        }
        catch (err) {
            setError(err.message ?? '백테스팅 중 오류가 발생했습니다.');
        }
        finally {
            setLoading(false);
        }
    }

    return (
        <section style={{ marginTop: '24px', border: '1px solid #e5e7eb', borderRadius: '8px', padding: '16px' }}>
            <h3 style={{ marginTop: 0, marginBottom: '12px' }}>포트폴리오 백테스팅</h3>

            {/* 날짜 입력 폼 */}
            <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-end', flexWrap: 'wrap', marginBottom: '12px' }}>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '14px' }}>
                    시작일
                    <input
                        type="date"
                        value={startDate}
                        onChange={(e) => setStartDate(e.target.value)}
                        style={{ padding: '6px', borderRadius: '4px', border: '1px solid #d1d5db' }}
                    />
                </label>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '14px' }}>
                    종료일
                    <input
                        type="date"
                        value={endDate}
                        onChange={(e) => setEndDate(e.target.value)}
                        style={{ padding: '6px', borderRadius: '4px', border: '1px solid #d1d5db' }}
                    />
                </label>
                <button
                    onClick={handleRun}
                    disabled={loading}
                    style={{
                        padding: '8px 20px',
                        background: loading ? '#93c5fd' : '#2563eb',
                        color: '#fff',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: loading ? 'not-allowed' : 'pointer',
                        fontWeight: 600,
                    }}
                >
                    {loading ? '분석 중...' : '백테스팅 실행'}
                </button>
            </div>

            {/* 오류 표시 */}
            {error && (
                <div style={{ color: '#dc2626', marginBottom: '12px', fontSize: '14px' }}>
                    {error}
                </div>
            )}

            {/* 결과 표시 */}
            {result && (
                <div>
                    {/* 요약 지표 */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: '12px', marginBottom: '16px' }}>
                        <MetricCard label="총 수익률" value={fmtPct(result.total_return)} />
                        <MetricCard label="최대 낙폭(MDD)" value={fmtPct(result.mdd)} />
                        <MetricCard label="샤프 비율" value={typeof result.sharpe_ratio === 'number' ? result.sharpe_ratio.toFixed(3) : '-'} />
                        <MetricCard label="거래일 수" value={`${result.period_days}일`} />
                    </div>

                    {/* 제외 종목 */}
                    {result.excluded_tickers && result.excluded_tickers.length > 0 && (
                        <div style={{ marginBottom: '12px', fontSize: '13px', color: '#6b7280' }}>
                            데이터 없음으로 제외된 종목: {result.excluded_tickers.join(', ')}
                        </div>
                    )}

                    {/* 누적 수익률 차트 */}
                    <BacktestChart daily={result.daily} />

                    {/* 면책 문구 */}
                    {result.disclaimer && (
                        <p style={{ fontSize: '12px', color: '#9ca3af', marginTop: '12px', lineHeight: 1.6 }}>
                            {result.disclaimer}
                        </p>
                    )}
                </div>
            )}
        </section>
    );
}

/**
 * 단일 지표 카드
 * @param {{ label: string, value: string }} props
 */
function MetricCard({ label, value }) {
    return (
        <div style={{
            background: '#f9fafb',
            borderRadius: '6px',
            padding: '12px',
            textAlign: 'center',
            border: '1px solid #e5e7eb',
        }}>
            <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>{label}</div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: '#111827' }}>{value}</div>
        </div>
    );
}

export default BacktestPanel;
