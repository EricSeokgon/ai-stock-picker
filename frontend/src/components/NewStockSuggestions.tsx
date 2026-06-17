// 신규 종목 추천 목록 컴포넌트 (SPEC-STOCK-026)
// 인라인 스타일 사용 (기존 Portfolio.tsx와 동일한 스타일 패턴)
import React from 'react';
import type { NewStockItem } from '../api/portfolio';

interface NewStockSuggestionsProps {
  stocks: NewStockItem[];
}

export default function NewStockSuggestions({ stocks }: NewStockSuggestionsProps) {
  if (stocks.length === 0) {
    return (
      <p style={{ color: '#9ca3af', textAlign: 'center', padding: '16px' }}>
        추천할 신규 종목이 없습니다.
      </p>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
      {stocks.map((stock) => (
        <div
          key={stock.krx_code}
          style={{
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            padding: '14px 16px',
            background: '#fff',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '6px' }}>
            <span
              style={{
                fontFamily: 'monospace',
                fontWeight: 700,
                color: '#1d4ed8',
                fontSize: '15px',
              }}
            >
              {stock.krx_code}
            </span>
            <span style={{ fontWeight: 600, color: '#111827', fontSize: '15px' }}>
              {stock.name}
            </span>
            <span
              style={{
                background: '#f3f4f6',
                borderRadius: '4px',
                padding: '2px 8px',
                fontSize: '12px',
                color: '#6b7280',
              }}
            >
              {stock.sector}
            </span>
          </div>
          <p style={{ margin: 0, fontSize: '13px', color: '#4b5563', lineHeight: 1.5 }}>
            {stock.reason}
          </p>
        </div>
      ))}
    </div>
  );
}
