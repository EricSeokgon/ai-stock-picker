import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// 성과 분류 도넛 차트 컴포넌트 (SPEC-STOCK-017 REQ-CHART-001)
// recharts PieChart/Pie 사용, innerRadius 설정으로 도넛 형태
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';
// 분류별 색상 및 레이블
const CLS_COLORS = {
    high: '#2e7d32',
    normal: '#1565c0',
    low: '#c62828',
};
const CLS_LABELS = {
    high: '고수익',
    normal: '보통',
    low: '저수익',
};
// @MX:NOTE: [AUTO] PerformanceDonutChart — SPEC-STOCK-017 REQ-CHART-001
// @MX:SPEC: SPEC-STOCK-017
export function PerformanceDonutChart({ summary }) {
    const data = ['high', 'normal', 'low']
        .map((cls) => ({
        name: CLS_LABELS[cls],
        value: summary[cls].count,
        investedPct: summary[cls].invested_pct,
    }))
        .filter((d) => d.value > 0);
    // 모든 종목이 0이면 플레이스홀더 표시
    if (data.length === 0) {
        return (_jsx("div", { style: { width: '100%', height: 160, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#aaa', fontSize: '0.8rem' }, children: "\uC131\uACFC \uB370\uC774\uD130 \uC5C6\uC74C" }));
    }
    return (_jsxs("div", { children: [_jsx("h5", { style: { margin: '0 0 0.25rem', fontSize: '0.8rem', color: '#555' }, children: "\uC131\uACFC \uBD84\uB958 \uBE44\uC911" }), _jsx(ResponsiveContainer, { width: "100%", height: 160, children: _jsxs(PieChart, { children: [_jsx(Pie, { data: data, cx: "50%", cy: "50%", innerRadius: 40, outerRadius: 65, paddingAngle: 2, dataKey: "value", labelLine: false, children: data.map((entry) => {
                                // CLS_COLORS에 없는 key에 대한 fallback
                                const originalCls = Object.keys(CLS_LABELS).find((k) => CLS_LABELS[k] === entry.name) ?? '';
                                return (_jsx(Cell, { fill: CLS_COLORS[originalCls] ?? '#999' }, `cell-${entry.name}`));
                            }) }), _jsx(Tooltip, { formatter: (value, name, props) => [`${value}종목 (${props.payload?.investedPct?.toFixed(1) ?? 0}%)`, name] }), _jsx(Legend, { iconSize: 10, iconType: "circle", wrapperStyle: { fontSize: '0.75rem' } })] }) })] }));
}
