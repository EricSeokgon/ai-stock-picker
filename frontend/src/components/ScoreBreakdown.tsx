// 스코어 분해 컴포넌트 — 팩터별 기여도 + 피드백 델타 시각화
import type { ScoreBreakdown as ScoreBreakdownType } from '../types';

// 팩터 코드 → 한국어 레이블 매핑
const FACTOR_LABELS: Record<string, string> = {
  sentiment: '감성(40%)',
  volume: '거래량(20%)',
  momentum: '모멘텀(25%)',
  anomaly: '이상거래(15%)',
};

interface ScoreBreakdownProps {
  breakdown: ScoreBreakdownType;
}

// @MX:ANCHOR: [AUTO] ScoreBreakdown - 스코어 분해 공개 컴포넌트
// @MX:REASON: StockDetail, 테스트에서 직접 참조. SPEC-STOCK-009 스코어 투명성 UI
export function ScoreBreakdown({ breakdown }: ScoreBreakdownProps) {
  const { factors, feedback_delta } = breakdown;

  return (
    <div style={{ fontSize: '0.8rem' }}>
      {factors.map((f) => {
        // 최대 가능 기여도 = weight * 1.0 = weight
        const maxContribution = f.weight;
        const barPct = maxContribution > 0
          ? Math.min(100, Math.round((f.contribution / maxContribution) * 100))
          : 0;
        const label = FACTOR_LABELS[f.factor] ?? f.factor;

        return (
          <div
            key={f.factor}
            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.3rem' }}
          >
            <span style={{ width: '80px', flexShrink: 0, color: '#555' }}>{label}</span>
            <div
              style={{
                flex: 1,
                height: '6px',
                backgroundColor: '#e0e0e0',
                borderRadius: '3px',
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  height: '100%',
                  width: `${barPct}%`,
                  backgroundColor: '#1976d2',
                  borderRadius: '3px',
                  transition: 'width 0.3s ease',
                }}
              />
            </div>
            <span style={{ width: '44px', textAlign: 'right', flexShrink: 0, color: '#333' }}>
              {f.contribution.toFixed(3)}
            </span>
          </div>
        );
      })}

      {/* 피드백 조정 행 — delta가 0이 아닐 때만 표시 */}
      {feedback_delta != null && feedback_delta !== 0 && (
        <div
          style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.4rem' }}
        >
          <span style={{ width: '80px', flexShrink: 0, color: '#555' }}>피드백 조정</span>
          <span
            style={{
              fontWeight: 600,
              color: feedback_delta > 0 ? '#2e7d32' : '#c62828',
            }}
          >
            {feedback_delta > 0 ? '+' : ''}{feedback_delta.toFixed(3)}
          </span>
        </div>
      )}
    </div>
  );
}
