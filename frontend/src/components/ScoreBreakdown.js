import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// 팩터 코드 → 한국어 레이블 매핑
const FACTOR_LABELS = {
    sentiment: '감성(40%)',
    volume: '거래량(20%)',
    momentum: '모멘텀(25%)',
    anomaly: '이상거래(15%)',
};
// @MX:ANCHOR: [AUTO] ScoreBreakdown - 스코어 분해 공개 컴포넌트
// @MX:REASON: StockDetail, 테스트에서 직접 참조. SPEC-STOCK-009 스코어 투명성 UI
export function ScoreBreakdown({ breakdown }) {
    const { factors, feedback_delta } = breakdown;
    return (_jsxs("div", { style: { fontSize: '0.8rem' }, children: [factors.map((f) => {
                // 최대 가능 기여도 = weight * 1.0 = weight
                const maxContribution = f.weight;
                const barPct = maxContribution > 0
                    ? Math.min(100, Math.round((f.contribution / maxContribution) * 100))
                    : 0;
                const label = FACTOR_LABELS[f.factor] ?? f.factor;
                return (_jsxs("div", { style: { display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.3rem' }, children: [_jsx("span", { style: { width: '80px', flexShrink: 0, color: '#555' }, children: label }), _jsx("div", { style: {
                                flex: 1,
                                height: '6px',
                                backgroundColor: '#e0e0e0',
                                borderRadius: '3px',
                                overflow: 'hidden',
                            }, children: _jsx("div", { style: {
                                    height: '100%',
                                    width: `${barPct}%`,
                                    backgroundColor: '#1976d2',
                                    borderRadius: '3px',
                                    transition: 'width 0.3s ease',
                                } }) }), _jsx("span", { style: { width: '44px', textAlign: 'right', flexShrink: 0, color: '#333' }, children: f.contribution.toFixed(3) })] }, f.factor));
            }), feedback_delta != null && feedback_delta !== 0 && (_jsxs("div", { style: { display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.4rem' }, children: [_jsx("span", { style: { width: '80px', flexShrink: 0, color: '#555' }, children: "\uD53C\uB4DC\uBC31 \uC870\uC815" }), _jsxs("span", { style: {
                            fontWeight: 600,
                            color: feedback_delta > 0 ? '#2e7d32' : '#c62828',
                        }, children: [feedback_delta > 0 ? '+' : '', feedback_delta.toFixed(3)] })] }))] }));
}
