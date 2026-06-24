// 벤치마크 비교 재기준화 차트 컴포넌트 (SPEC-STOCK-034 REQ-BMK-010)
// 포트폴리오와 벤치마크를 100 기준으로 재기준화하여 시각화
import React, { useEffect, useState } from 'react';
import { apiGetBenchmarkChart } from '../api/portfolio';

// 지원 벤치마크 목록
const BENCHMARKS = ['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ'];
// 지원 기간 목록
const PERIODS = ['YTD', '1M', '3M', '6M', '1Y'];

/**
 * BenchmarkChartView: 포트폴리오와 벤치마크 지수 재기준화 차트
 *
 * Props:
 *   portfolioId: 포트폴리오 ID
 *   token: 인증 토큰
 */
export default function BenchmarkChartView({ portfolioId, token }) {
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
                const result = await apiGetBenchmarkChart(token, portfolioId, benchmark, period);
                setData(result);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [portfolioId, token, benchmark, period]);

    // SVG 기반 간단 선 차트
    const renderChart = (chartData) => {
        if (!chartData || chartData.length === 0) {
            return (
                <div style={{ textAlign: 'center', color: '#6b7280', padding: '40px' }}>
                    차트 데이터 없음
                </div>
            );
        }

        const width = 600;
        const height = 200;
        const padding = { top: 20, right: 20, bottom: 40, left: 50 };
        const innerWidth = width - padding.left - padding.right;
        const innerHeight = height - padding.top - padding.bottom;

        // 값 범위 계산
        const allValues = chartData.flatMap((d) => [
            d.portfolio_index,
            ...(d.benchmark_index !== null ? [d.benchmark_index] : []),
        ]);
        const minVal = Math.min(...allValues) * 0.99;
        const maxVal = Math.max(...allValues) * 1.01;
        const valRange = maxVal - minVal || 1;

        const xScale = (i) => padding.left + (i / (chartData.length - 1)) * innerWidth;
        const yScale = (v) => padding.top + innerHeight - ((v - minVal) / valRange) * innerHeight;

        // SVG 경로 생성
        const portfolioPath = chartData
            .map((d, i) => `${i === 0 ? 'M' : 'L'}${xScale(i)},${yScale(d.portfolio_index)}`)
            .join(' ');

        const benchmarkPath = chartData
            .filter((d) => d.benchmark_index !== null)
            .map((d, i, arr) => {
                const origIdx = chartData.indexOf(d);
                return `${i === 0 ? 'M' : 'L'}${xScale(origIdx)},${yScale(d.benchmark_index)}`;
            })
            .join(' ');

        // X축 레이블 (최대 5개)
        const xLabelIndices = [0, Math.floor(chartData.length * 0.25), Math.floor(chartData.length * 0.5), Math.floor(chartData.length * 0.75), chartData.length - 1];

        return (
            <svg
                viewBox={`0 0 ${width} ${height}`}
                style={{ width: '100%', maxWidth: `${width}px`, height: 'auto', overflow: 'visible' }}
            >
                {/* 기준선 (100) */}
                <line
                    x1={padding.left}
                    y1={yScale(100)}
                    x2={width - padding.right}
                    y2={yScale(100)}
                    stroke="#e2e8f0"
                    strokeWidth="1"
                    strokeDasharray="4 2"
                />

                {/* 포트폴리오 라인 */}
                <path d={portfolioPath} fill="none" stroke="#1d4ed8" strokeWidth="2" />

                {/* 벤치마크 라인 */}
                {benchmarkPath && (
                    <path d={benchmarkPath} fill="none" stroke="#f97316" strokeWidth="1.5" strokeDasharray="5 3" />
                )}

                {/* X축 레이블 */}
                {xLabelIndices.map((idx) => {
                    const d = chartData[idx];
                    if (!d) return null;
                    return (
                        <text
                            key={idx}
                            x={xScale(idx)}
                            y={height - 5}
                            textAnchor="middle"
                            fontSize="10"
                            fill="#6b7280"
                        >
                            {d.date.slice(5)}
                        </text>
                    );
                })}

                {/* Y축 레이블 */}
                {[minVal, (minVal + maxVal) / 2, maxVal].map((v, i) => (
                    <text
                        key={i}
                        x={padding.left - 5}
                        y={yScale(v) + 4}
                        textAnchor="end"
                        fontSize="10"
                        fill="#6b7280"
                    >
                        {v.toFixed(0)}
                    </text>
                ))}

                {/* 범례 */}
                <g transform={`translate(${padding.left}, ${height - 15})`}>
                    <line x1={0} y1={0} x2={16} y2={0} stroke="#1d4ed8" strokeWidth="2" />
                    <text x={20} y={4} fontSize="10" fill="#374151">포트폴리오</text>
                    <line x1={90} y1={0} x2={106} y2={0} stroke="#f97316" strokeWidth="1.5" strokeDasharray="4 2" />
                    <text x={110} y={4} fontSize="10" fill="#374151">{data?.benchmark}</text>
                </g>
            </svg>
        );
    };

    return (
        <div style={{ padding: '16px', border: '1px solid #e2e8f0', borderRadius: '8px', backgroundColor: '#fff' }}>
            <h3 style={{ margin: '0 0 12px 0', fontSize: '1rem', fontWeight: '600' }}>
                성과 비교 차트 (100 기준 재기준화)
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
                <div style={{ textAlign: 'center', color: '#6b7280', padding: '40px' }}>
                    불러오는 중...
                </div>
            )}

            {/* 오류 상태 */}
            {error && !loading && (
                <div style={{ color: '#ef4444', fontSize: '0.875rem', padding: '8px' }}>
                    {error}
                </div>
            )}

            {/* 차트 */}
            {data && !loading && (
                <div style={{ overflowX: 'auto' }}>
                    {renderChart(data.chart)}
                </div>
            )}
        </div>
    );
}
