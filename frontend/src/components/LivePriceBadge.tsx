// 실시간 시세 배지 (가격 + 등락률, 색상 구분) (REQ-FE-002)
// Props: { krxCode: string }
// - 양수 등락률: 빨간색 (한국 관례)
// - 음수 등락률: 파란색
// - 0: 검정
// - 로딩 중: "시세 조회 중..."

import { useLivePrice } from '../hooks/useLivePrice';

interface LivePriceBadgeProps {
  krxCode: string;
}

// 등락률에 따른 색상 반환 (한국 주식 관례: 상승=빨강, 하락=파랑)
function changePctColor(changePct: number): string {
  if (changePct > 0) return '#c62828'; // 빨간색 — 상승
  if (changePct < 0) return '#1565c0'; // 파란색 — 하락
  return '#333';                        // 검정 — 보합
}

export function LivePriceBadge({ krxCode }: LivePriceBadgeProps) {
  const livePrice = useLivePrice(krxCode);

  if (!livePrice) {
    return (
      <span style={{ fontSize: '0.8rem', color: '#888' }}>
        시세 조회 중...
      </span>
    );
  }

  const { price, change_pct } = livePrice;
  const color = changePctColor(change_pct);
  const sign = change_pct > 0 ? '+' : change_pct < 0 ? '' : '';
  const changePctText = `(${sign}${change_pct.toFixed(2)}%)`;

  return (
    <span style={{ fontSize: '0.85rem', display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
      <span style={{ fontWeight: 600 }}>
        ₩{price.toLocaleString()}
      </span>
      <span style={{ color, fontWeight: 500 }}>
        {changePctText}
      </span>
    </span>
  );
}
