import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// 실시간 시세 배지 (가격 + 등락률, 색상 구분) (REQ-FE-002)
// Props: { krxCode: string }
// - 양수 등락률: 빨간색 (한국 관례)
// - 음수 등락률: 파란색
// - 0: 검정
// - 로딩 중: "시세 조회 중..."
import { useLivePrice } from '../hooks/useLivePrice';
// 등락률에 따른 색상 반환 (한국 주식 관례: 상승=빨강, 하락=파랑)
function changePctColor(changePct) {
    if (changePct > 0)
        return '#c62828'; // 빨간색 — 상승
    if (changePct < 0)
        return '#1565c0'; // 파란색 — 하락
    return '#333'; // 검정 — 보합
}
export function LivePriceBadge({ krxCode }) {
    const livePrice = useLivePrice(krxCode);
    if (!livePrice) {
        return (_jsx("span", { style: { fontSize: '0.8rem', color: '#888' }, children: "\uC2DC\uC138 \uC870\uD68C \uC911..." }));
    }
    const { price, change_pct } = livePrice;
    const color = changePctColor(change_pct);
    const sign = change_pct > 0 ? '+' : change_pct < 0 ? '' : '';
    const changePctText = `(${sign}${change_pct.toFixed(2)}%)`;
    return (_jsxs("span", { style: { fontSize: '0.85rem', display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }, children: [_jsxs("span", { style: { fontWeight: 600 }, children: ["\u20A9", price.toLocaleString()] }), _jsx("span", { style: { color, fontWeight: 500 }, children: changePctText })] }));
}
