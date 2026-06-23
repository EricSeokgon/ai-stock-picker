import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { apiCalculateRebalancing } from "../api/portfolio";
// 액션별 색상 반환
function actionColor(action) {
    if (action === 'buy')
        return '#16a34a';
    if (action === 'sell')
        return '#dc2626';
    return '#6b7280';
}
// 액션 한글 레이블
function actionLabel(action) {
    if (action === 'buy')
        return '매수';
    if (action === 'sell')
        return '매도';
    return '홀드';
}
// 금액 포맷 (천원 단위)
function formatKrw(amount) {
    if (amount >= 1_000_000)
        return `${(amount / 1_000_000).toFixed(1)}백만원`;
    if (amount >= 10_000)
        return `${(amount / 10_000).toFixed(0)}만원`;
    return `${amount.toLocaleString()}원`;
}
// 단일 주문 행
function OrderRow({ order }) {
    const color = actionColor(order.action);
    const label = actionLabel(order.action);
    return _jsxs("tr", {
        children: [
            _jsx("td", { style: { padding: '10px 12px', fontWeight: 500 }, children: order.stock_name }),
            _jsx("td", { style: { padding: '10px 12px', color: '#6b7280', fontSize: '13px' }, children: order.krx_code }),
            _jsx("td", { style: { padding: '10px 12px' }, children: _jsx("span", { style: {
                        background: `${color}18`,
                        color,
                        padding: '2px 8px',
                        borderRadius: '999px',
                        fontWeight: 600,
                        fontSize: '13px',
                    }, children: label }) }),
            _jsx("td", { style: { padding: '10px 12px', textAlign: 'right', fontWeight: 600 }, children: order.action === 'hold' ? '—' : `${order.quantity.toLocaleString()}주` }),
            _jsx("td", { style: { padding: '10px 12px', textAlign: 'right' }, children: order.action === 'hold' ? '—' : formatKrw(order.estimated_amount) }),
            _jsx("td", { style: { padding: '10px 12px', textAlign: 'right', color: '#9ca3af', fontSize: '13px' }, children: order.action === 'hold' ? '—' : formatKrw(order.estimated_commission) }),
            _jsxs("td", { style: { padding: '10px 12px', textAlign: 'right', fontSize: '13px', color: '#6b7280' }, children: [order.current_weight.toFixed(1), '% → ', _jsx("b", { children: `${order.target_weight.toFixed(1)}%` })] }),
        ],
    });
}
// @MX:NOTE: [AUTO] SPEC-STOCK-032 리밸런싱 주문 패널 컴포넌트
// @MX:SPEC: SPEC-STOCK-032
export default function RebalancingOrderPanel({ portfolioId, token }) {
    const [plan, setPlan] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [dryRun, setDryRun] = useState(true);

    async function handleCalculate() {
        setLoading(true);
        setError(null);
        try {
            const result = await apiCalculateRebalancing(token, portfolioId, { dryRun });
            setPlan(result);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }

    return _jsxs("div", {
        style: { border: '1px solid #e5e7eb', borderRadius: '12px', padding: '20px', background: '#fff' },
        children: [
            _jsxs("div", {
                style: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' },
                children: [
                    _jsx("h3", { style: { margin: 0, fontSize: '16px', fontWeight: 700 }, children: '리밸런싱 주문 계획' }),
                    _jsxs("div", {
                        style: { display: 'flex', gap: '8px', alignItems: 'center' },
                        children: [
                            _jsxs("label", {
                                style: { fontSize: '13px', color: '#6b7280', display: 'flex', alignItems: 'center', gap: '4px' },
                                children: [
                                    _jsx("input", {
                                        type: 'checkbox',
                                        checked: dryRun,
                                        onChange: e => setDryRun(e.target.checked),
                                    }),
                                    '시뮬레이션만',
                                ],
                            }),
                            _jsx("button", {
                                onClick: handleCalculate,
                                disabled: loading,
                                style: {
                                    background: '#2563eb',
                                    color: '#fff',
                                    border: 'none',
                                    borderRadius: '8px',
                                    padding: '8px 16px',
                                    fontWeight: 600,
                                    cursor: loading ? 'not-allowed' : 'pointer',
                                    opacity: loading ? 0.6 : 1,
                                },
                                children: loading ? '계산 중...' : '리밸런싱 계산',
                            }),
                        ],
                    }),
                ],
            }),
            error && _jsx("div", { style: { color: '#dc2626', fontSize: '13px', marginBottom: '12px' }, children: error }),
            plan && _jsxs("div", {
                children: [
                    // 요약 정보
                    _jsxs("div", {
                        style: { display: 'flex', gap: '16px', marginBottom: '16px', flexWrap: 'wrap' },
                        children: [
                            _jsxs("div", { style: { fontSize: '13px', color: '#4b5563' }, children: ['예산: ', _jsx("b", { children: formatKrw(plan.budget) })] }),
                            _jsxs("div", { style: { fontSize: '13px', color: '#16a34a' }, children: ['총 매수: ', _jsx("b", { children: formatKrw(plan.total_buy_amount) })] }),
                            _jsxs("div", { style: { fontSize: '13px', color: '#dc2626' }, children: ['총 매도: ', _jsx("b", { children: formatKrw(plan.total_sell_amount) })] }),
                            _jsxs("div", { style: { fontSize: '13px', color: '#9ca3af' }, children: ['총 수수료: ', _jsx("b", { children: formatKrw(plan.total_commission) })] }),
                        ],
                    }),
                    // 주문 테이블
                    _jsx("div", {
                        style: { overflowX: 'auto' },
                        children: _jsxs("table", {
                            style: { width: '100%', borderCollapse: 'collapse', fontSize: '14px' },
                            children: [
                                _jsx("thead", {
                                    children: _jsxs("tr", {
                                        style: { borderBottom: '2px solid #e5e7eb', textAlign: 'left' },
                                        children: [
                                            _jsx("th", { style: { padding: '8px 12px', fontWeight: 600, color: '#374151' }, children: '종목명' }),
                                            _jsx("th", { style: { padding: '8px 12px', fontWeight: 600, color: '#374151' }, children: '코드' }),
                                            _jsx("th", { style: { padding: '8px 12px', fontWeight: 600, color: '#374151' }, children: '액션' }),
                                            _jsx("th", { style: { padding: '8px 12px', textAlign: 'right', fontWeight: 600, color: '#374151' }, children: '수량' }),
                                            _jsx("th", { style: { padding: '8px 12px', textAlign: 'right', fontWeight: 600, color: '#374151' }, children: '예상 금액' }),
                                            _jsx("th", { style: { padding: '8px 12px', textAlign: 'right', fontWeight: 600, color: '#374151' }, children: '수수료' }),
                                            _jsx("th", { style: { padding: '8px 12px', textAlign: 'right', fontWeight: 600, color: '#374151' }, children: '비중 변화' }),
                                        ],
                                    }),
                                }),
                                _jsx("tbody", {
                                    children: plan.orders.map((order, i) => _jsx(OrderRow, { order }, i)),
                                }),
                            ],
                        }),
                    }),
                    dryRun && _jsx("p", {
                        style: { fontSize: '12px', color: '#9ca3af', marginTop: '12px' },
                        children: '* 시뮬레이션 모드입니다. 실제 주문을 저장하려면 "시뮬레이션만" 체크를 해제하세요.',
                    }),
                ],
            }),
        ],
    });
}
