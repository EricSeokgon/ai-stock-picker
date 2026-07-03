// SPEC-STOCK-039 — 시장 상태 배지 컴포넌트
import React from 'react';

interface MarketStatusBadgeProps {
  /** KRX 장 개장 여부 */
  isOpen: boolean;
  /** 마지막 갱신 시각 (null이면 미표시) */
  lastUpdated: Date | null;
}

/**
 * KRX 시장 상태 배지.
 *
 * - 장 중: 초록색 배지 + "장 중" 텍스트
 * - 장 마감: 회색 배지 + "장 마감" 텍스트
 * - lastUpdated: 마지막 가격 갱신 시각 표시 (있을 때만)
 */
export function MarketStatusBadge({ isOpen, lastUpdated }: MarketStatusBadgeProps): React.ReactElement {
  const badgeStyle: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '4px 10px',
    borderRadius: '12px',
    fontSize: '0.8rem',
    fontWeight: 600,
    backgroundColor: isOpen ? '#e8f5e9' : '#f5f5f5',
    color: isOpen ? '#2e7d32' : '#757575',
    border: `1px solid ${isOpen ? '#a5d6a7' : '#e0e0e0'}`,
  };

  const dotStyle: React.CSSProperties = {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    backgroundColor: isOpen ? '#43a047' : '#9e9e9e',
    // 장 중일 때 깜빡이는 애니메이션
    animation: isOpen ? 'pulse 1.5s infinite' : 'none',
  };

  const containerStyle: React.CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-start',
    gap: '4px',
  };

  const timestampStyle: React.CSSProperties = {
    fontSize: '0.7rem',
    color: '#9e9e9e',
  };

  return (
    <div style={containerStyle}>
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
      <span style={badgeStyle}>
        <span style={dotStyle} />
        {isOpen ? '장 중' : '장 마감'}
      </span>
      {lastUpdated && (
        <span style={timestampStyle}>
          최종 갱신: {lastUpdated.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
        </span>
      )}
    </div>
  );
}

export default MarketStatusBadge;
