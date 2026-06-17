// 포트폴리오 최적화 점수 카드 컴포넌트 (SPEC-STOCK-026)
// 인라인 스타일 사용 (기존 Portfolio.tsx와 동일한 스타일 패턴)
import React from 'react';
import type { ScoreBreakdown } from '../api/portfolio';

interface PortfolioScoreCardProps {
  score: number;
  breakdown: ScoreBreakdown;
}

// 점수에 따른 색상 반환 (0-40: 빨강, 41-70: 주황, 71-100: 초록)
function scoreColor(value: number): string {
  if (value >= 71) return '#16a34a';
  if (value >= 41) return '#d97706';
  return '#dc2626';
}

interface BreakdownBarProps {
  label: string;
  value: number;
}

function BreakdownBar({ label, value }: BreakdownBarProps) {
  const color = scoreColor(value);
  return (
    <div style={{ marginBottom: '8px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
        <span style={{ fontSize: '13px', color: '#4b5563' }}>{label}</span>
        <span style={{ fontSize: '13px', fontWeight: 600, color }}>{value}</span>
      </div>
      <div
        style={{
          height: '8px',
          background: '#e5e7eb',
          borderRadius: '4px',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            height: '100%',
            width: `${value}%`,
            background: color,
            borderRadius: '4px',
            transition: 'width 0.4s ease',
          }}
        />
      </div>
    </div>
  );
}

export default function PortfolioScoreCard({ score, breakdown }: PortfolioScoreCardProps) {
  const mainColor = scoreColor(score);

  return (
    <div
      style={{
        border: '1px solid #e5e7eb',
        borderRadius: '12px',
        padding: '20px',
        background: '#fff',
        maxWidth: '400px',
      }}
    >
      {/* 종합 점수 원형 표시 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '20px', marginBottom: '20px' }}>
        <div
          style={{
            width: '80px',
            height: '80px',
            borderRadius: '50%',
            border: `6px solid ${mainColor}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          <span style={{ fontSize: '22px', fontWeight: 700, color: mainColor }}>{score}</span>
        </div>
        <div>
          <p style={{ margin: 0, fontWeight: 600, fontSize: '16px', color: '#111827' }}>
            포트폴리오 종합 점수
          </p>
          <p style={{ margin: '4px 0 0', fontSize: '13px', color: '#6b7280' }}>
            {score >= 71 ? '우수' : score >= 41 ? '보통' : '개선 필요'}
          </p>
        </div>
      </div>

      {/* 세부 점수 바 */}
      <div>
        <BreakdownBar label="분산도" value={breakdown.diversification} />
        <BreakdownBar label="위험 균형" value={breakdown.risk_balance} />
        <BreakdownBar label="모멘텀" value={breakdown.momentum} />
      </div>
    </div>
  );
}
