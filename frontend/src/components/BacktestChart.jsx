// 포트폴리오 백테스팅 차트 컴포넌트 (SPEC-STOCK-029)
// Recharts LineChart 기반 누적 수익률 시각화
import React from 'react';
import {
    CartesianGrid,
    Legend,
    Line,
    LineChart,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from 'recharts';

/**
 * 날짜 포맷: YYYY-MM-DD → MM/DD
 * @param {string} dateStr
 * @returns {string}
 */
function formatDate(dateStr) {
    if (!dateStr)
        return '';
    const parts = dateStr.split('-');
    if (parts.length !== 3)
        return dateStr;
    return `${parts[1]}/${parts[2]}`;
}

/**
 * 수익률 툴팁 포맷: 소수 → 백분율
 * @param {number} value
 * @returns {string}
 */
function formatPct(value) {
    if (typeof value !== 'number')
        return '-';
    return `${(value * 100).toFixed(2)}%`;
}

/**
 * 백테스팅 누적 수익률 라인 차트
 *
 * @param {{ daily: Array<{date: string, cumulative_return: number}> }} props
 */
export function BacktestChart({ daily }) {
    if (!daily || daily.length === 0) {
        return (
            <div style={{ padding: '16px', color: '#888', textAlign: 'center' }}>
                백테스팅 데이터가 없습니다.
            </div>
        );
    }
    // Recharts용 데이터 변환 (누적 수익률을 % 단위로)
    const data = daily.map((d) => ({
        date: d.date,
        displayDate: formatDate(d.date),
        cumulative_return_pct: +(d.cumulative_return * 100).toFixed(4),
    }));
    return (
        <div>
            <h4 style={{ marginBottom: '8px' }}>누적 수익률 추이</h4>
            <ResponsiveContainer width="100%" height={300}>
                <LineChart data={data} margin={{ top: 8, right: 24, bottom: 8, left: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                        dataKey="displayDate"
                        tick={{ fontSize: 11 }}
                        interval="preserveStartEnd"
                    />
                    <YAxis
                        tickFormatter={(v) => `${v.toFixed(1)}%`}
                        tick={{ fontSize: 11 }}
                        domain={['auto', 'auto']}
                    />
                    <Tooltip
                        formatter={(value) => [`${value.toFixed(2)}%`, '누적 수익률']}
                        labelFormatter={(label) => `날짜: ${label}`}
                    />
                    <Legend />
                    <Line
                        type="monotone"
                        dataKey="cumulative_return_pct"
                        name="누적 수익률(%)"
                        stroke="#2563eb"
                        dot={false}
                        strokeWidth={2}
                    />
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
}

export default BacktestChart;
