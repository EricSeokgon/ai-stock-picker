// 리밸런싱 목표 비중 테이블 컴포넌트 (SPEC-STOCK-026)
// 인라인 스타일 사용 (기존 Portfolio.tsx와 동일한 스타일 패턴)
import React from 'react';
import type { TargetWeightItem } from '../api/portfolio';

interface RebalancingTableProps {
  items: TargetWeightItem[];
}

// action 유형별 배경색
function actionStyle(action: 'buy' | 'sell' | 'hold'): React.CSSProperties {
  switch (action) {
    case 'buy':
      return { color: '#16a34a', fontWeight: 600 };
    case 'sell':
      return { color: '#dc2626', fontWeight: 600 };
    case 'hold':
    default:
      return { color: '#6b7280', fontWeight: 600 };
  }
}

function actionLabel(action: 'buy' | 'sell' | 'hold'): string {
  switch (action) {
    case 'buy': return '매수';
    case 'sell': return '매도';
    case 'hold': return '유지';
  }
}

export default function RebalancingTable({ items }: RebalancingTableProps) {
  if (items.length === 0) {
    return (
      <p style={{ color: '#9ca3af', textAlign: 'center', padding: '16px' }}>
        리밸런싱 대상 종목이 없습니다.
      </p>
    );
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <table
        style={{
          width: '100%',
          borderCollapse: 'collapse',
          fontSize: '14px',
        }}
      >
        <thead>
          <tr style={{ background: '#f9fafb', borderBottom: '1px solid #e5e7eb' }}>
            {['종목코드', '현재비중', '목표비중', '조정', '수량변화'].map((h) => (
              <th
                key={h}
                style={{
                  padding: '10px 12px',
                  textAlign: 'left',
                  fontWeight: 600,
                  color: '#374151',
                  whiteSpace: 'nowrap',
                }}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr
              key={item.krx_code}
              style={{ borderBottom: '1px solid #f3f4f6' }}
            >
              <td style={{ padding: '10px 12px', fontFamily: 'monospace', color: '#111827' }}>
                {item.krx_code}
              </td>
              <td style={{ padding: '10px 12px', color: '#6b7280' }}>
                {item.current_pct.toFixed(1)}%
              </td>
              <td style={{ padding: '10px 12px', fontWeight: 600, color: '#111827' }}>
                {item.target_pct.toFixed(1)}%
              </td>
              <td style={{ padding: '10px 12px', ...actionStyle(item.action) }}>
                {actionLabel(item.action)}
              </td>
              <td
                style={{
                  padding: '10px 12px',
                  color: item.delta_shares > 0 ? '#16a34a' : item.delta_shares < 0 ? '#dc2626' : '#6b7280',
                  fontWeight: 600,
                }}
              >
                {item.delta_shares > 0 ? `+${item.delta_shares}` : item.delta_shares}주
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
