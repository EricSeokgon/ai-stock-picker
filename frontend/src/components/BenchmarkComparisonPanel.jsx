// 벤치마크 비교 패널 컴포넌트 (SPEC-STOCK-034)
// 알파·베타·수익률 비교 표시
import React, { useEffect, useState } from 'react';
import { apiGetBenchmarkComparison } from '../api/portfolio';

// 지원 벤치마크 목록
const BENCHMARKS = ['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ'];
// 지원 기간 목록
const PERIODS = ['YTD', '1M', '3M', '6M', '1Y'];

/**
 * BenchmarkComparisonPanel: 포트폴리오와 벤치마크 지수 비교 패널
 *
 * Props:
 *   portfolioId: 포트폴리오 ID
 *   token: 인증 토큰
 */
export default function BenchmarkComparisonPanel({ portfolioId, token }) {
    const [benchmark, setBenchmark] = useState('KOSPI');
    const [period, setPeriod] = useState('1Y');
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!portfolioId || !token) return;

        const fetchData = async () => {
            setLoading(true);
            setError(null);
            try {
                const result = await apiGetBenchmarkComparison(token, portfolioId, benchmark, period);
                setData(result);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [portfolioId, token, benchmark, period]);

    // 수익률 표시용 포맷 (부호 포함)
    const formatReturn = (value) => {
        if (value === null || value === undefined) return '—';
        const sign = value >= 0 ? '+' : '';
        return `${sign}${value.toFixed(2)}%`;
    };

    // 색상 결정 (양수: 초록, 음수: 빨강)
    const returnColor = (value) => {
        if (value === null || value === undefined) return '#666';
        return value >= 0 ? '#22c55e' : '#ef4444';
    };

    return (
        <div style={{ padding: '16px', border: '1px solid #e2e8f0', borderRadius: '8px', backgroundColor: '#fff' }}>
            <h3 style={{ margin: '0 0 12px 0', fontSize: '1rem', fontWeight: '600' }}>
                벤치마크 비교
            </h3>

            {/* 필터 */}
            <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', flexWrap: 'wrap' }}>
                <select
                    value={benchmark}
                    onChange={(e) => setBenchmark(e.target.value)}
                    style={{ padding: '4px 8px', borderRadius: '4px', border: '1px solid #cbd5e1', fontSize: '0.875rem' }}
                >
                    {BENCHMARKS.map((b) => (
                        <option key={b} value={b}>{b}</option>
                    ))}
                </select>

                <div style={{ display: 'flex', gap: '4px' }}>
                    {PERIODS.map((p) => (
                        <button
                            key={p}
                            onClick={() => setPeriod(p)}
                            style={{
                                padding: '4px 10px',
                                borderRadius: '4px',
                                border: '1px solid #cbd5e1',
                                backgroundColor: period === p ? '#1d4ed8' : '#f8fafc',
                                color: period === p ? '#fff' : '#374151',
                                cursor: 'pointer',
                                fontSize: '0.875rem',
                            }}
                        >
                            {p}
                        </button>
                    ))}
                </div>
            </div>

            {/* 로딩 상태 */}
            {loading && (
                <div style={{ textAlign: 'center', color: '#6b7280', padding: '20px' }}>
                    불러오는 중...
                </div>
            )}

            {/* 오류 상태 */}
            {error && !loading && (
                <div style={{ color: '#ef4444', fontSize: '0.875rem', padding: '8px' }}>
                    {error}
                </div>
            )}

            {/* 비교 데이터 */}
            {data && !loading && (
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
                    <thead>
                        <tr style={{ borderBottom: '1px solid #e2e8f0', textAlign: 'left' }}>
                            <th style={{ padding: '8px 4px', color: '#6b7280', fontWeight: '500' }}>항목</th>
                            <th style={{ padding: '8px 4px', color: '#6b7280', fontWeight: '500', textAlign: 'right' }}>포트폴리오</th>
                            <th style={{ padding: '8px 4px', color: '#6b7280', fontWeight: '500', textAlign: 'right' }}>{data.benchmark}</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr style={{ borderBottom: '1px solid #f1f5f9' }}>
                            <td style={{ padding: '8px 4px', color: '#374151' }}>수익률</td>
                            <td style={{ padding: '8px 4px', textAlign: 'right', color: returnColor(data.portfolio_return_pct), fontWeight: '600' }}>
                                {formatReturn(data.portfolio_return_pct)}
                            </td>
                            <td style={{ padding: '8px 4px', textAlign: 'right', color: returnColor(data.benchmark_return_pct) }}>
                                {formatReturn(data.benchmark_return_pct)}
                            </td>
                        </tr>
                        <tr style={{ borderBottom: '1px solid #f1f5f9' }}>
                            <td style={{ padding: '8px 4px', color: '#374151' }}>초과 수익 (알파)</td>
                            <td colSpan={2} style={{ padding: '8px 4px', textAlign: 'right', color: returnColor(data.excess_return_pct), fontWeight: '600' }}>
                                {formatReturn(data.excess_return_pct)}
                            </td>
                        </tr>
                        <tr style={{ borderBottom: '1px solid #f1f5f9' }}>
                            <td style={{ padding: '8px 4px', color: '#374151' }}>연환산 알파</td>
                            <td colSpan={2} style={{ padding: '8px 4px', textAlign: 'right', color: returnColor(data.alpha) }}>
                                {formatReturn(data.alpha)}
                            </td>
                        </tr>
                        <tr>
                            <td style={{ padding: '8px 4px', color: '#374151' }}>베타</td>
                            <td colSpan={2} style={{ padding: '8px 4px', textAlign: 'right', color: '#374151' }}>
                                {data.beta !== null && data.beta !== undefined ? data.beta.toFixed(3) : '—'}
                            </td>
                        </tr>
                    </tbody>
                </table>
            )}
        </div>
    );
}
