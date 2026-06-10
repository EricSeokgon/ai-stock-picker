// 주식 추천 목록 컴포넌트 — 모바일 반응형 카드 레이아웃 지원
import type { RecommendationItem } from '../types';

interface RecommendationListProps {
  recommendations: RecommendationItem[];
  // 종목 클릭 시 호출되는 선택 콜백 (상세 모달 표시용)
  onSelect?: (krxCode: string) => void;
}

// 점수를 백분율 바로 시각화
function ScoreBar({ score, label }: { score: number; label: string }) {
  // 점수 범위: -1~1 또는 0~1 가정, 표시용으로 0~100% 변환
  const pct = Math.min(100, Math.max(0, Math.round(score * 100)));
  const color = score >= 0 ? '#2e7d32' : '#c62828';

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
      <span style={{ fontSize: '0.75rem', color: '#666', width: '80px', flexShrink: 0 }}>{label}</span>
      <div
        style={{
          flex: 1,
          height: '8px',
          backgroundColor: '#e0e0e0',
          borderRadius: '4px',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            height: '100%',
            width: `${pct}%`,
            backgroundColor: color,
            borderRadius: '4px',
            transition: 'width 0.3s ease',
          }}
        />
      </div>
      <span style={{ fontSize: '0.75rem', color, width: '45px', textAlign: 'right', flexShrink: 0 }}>
        {score.toFixed(3)}
      </span>
    </div>
  );
}

function RecommendationCard({
  item,
  onSelect,
}: {
  item: RecommendationItem;
  onSelect?: (krxCode: string) => void;
}) {
  const sentimentColor = item.sentiment_score > 0 ? '#2e7d32' : item.sentiment_score < 0 ? '#c62828' : '#555';

  const isClickable = Boolean(onSelect);

  return (
    <li
      onClick={() => onSelect?.(item.krx_code)}
      style={{
        listStyle: 'none',
        border: '1px solid #ddd',
        borderRadius: '8px',
        padding: '1rem 1.25rem',
        backgroundColor: '#fff',
        boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
        cursor: isClickable ? 'pointer' : 'default',
        transition: 'box-shadow 0.15s',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '0.75rem' }}>
        {/* 순위 배지 */}
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '36px',
            height: '36px',
            borderRadius: '50%',
            backgroundColor: item.rank <= 3 ? '#1976d2' : '#546e7a',
            color: '#fff',
            fontWeight: 700,
            fontSize: '0.9rem',
            flexShrink: 0,
          }}
          aria-label={`순위 ${item.rank}위`}
        >
          {item.rank}
        </span>

        {/* 종목코드 */}
        <span
          style={{
            fontWeight: 700,
            fontSize: '1.1rem',
            color: '#212121',
            letterSpacing: '0.05em',
          }}
        >
          {item.krx_code}
        </span>

        {/* 종합 점수 */}
        <span
          style={{
            marginLeft: 'auto',
            fontSize: '0.875rem',
            fontWeight: 600,
            color: sentimentColor,
          }}
        >
          종합 {(item.total_score * 100).toFixed(1)}점
        </span>
      </div>

      {/* 세부 점수 바 */}
      <div style={{ marginBottom: '0.75rem' }}>
        <ScoreBar score={item.sentiment_score} label="감성" />
        <ScoreBar score={item.volume_score} label="거래량" />
        <ScoreBar score={item.momentum_score} label="모멘텀" />
        <ScoreBar score={item.anomaly_score} label="이상감지" />
      </div>

      {/* 피드백 반영 배지 — base_score와 feedback_score가 모두 있고 feedback_score != 0일 때 표시 */}
      {item.base_score != null && item.feedback_score != null && item.feedback_score !== 0 && (
        <div style={{ marginBottom: '0.5rem' }}>
          <span
            style={{
              display: 'inline-block',
              padding: '2px 8px',
              borderRadius: '12px',
              fontSize: '0.75rem',
              fontWeight: 600,
              backgroundColor: item.feedback_score > 0 ? '#e8f5e9' : '#ffebee',
              color: item.feedback_score > 0 ? '#2e7d32' : '#c62828',
            }}
          >
            피드백 반영 {item.feedback_score > 0 ? '+' : ''}{item.feedback_score.toFixed(3)}
          </span>
        </div>
      )}

      {/* 추천 이유 */}
      <p
        style={{
          margin: 0,
          fontSize: '0.875rem',
          color: '#444',
          lineHeight: 1.6,
          borderTop: '1px solid #f0f0f0',
          paddingTop: '0.75rem',
        }}
      >
        {item.reasoning}
      </p>
    </li>
  );
}

// @MX:ANCHOR: [AUTO] RecommendationList - 주식 추천 목록 공개 컴포넌트
// @MX:REASON: App.tsx, Dashboard, 테스트에서 직접 참조. onSelect 콜백 추가로 modal 연계
export function RecommendationList({ recommendations, onSelect }: RecommendationListProps) {
  return (
    <section aria-labelledby="recommendation-heading">
      <h2
        id="recommendation-heading"
        style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '1rem', color: '#212121' }}
      >
        오늘의 주식 추천
      </h2>
      <ul
        className="recommendation-list"
        style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', padding: 0, margin: 0 }}
        aria-label="주식 추천 목록"
      >
        {recommendations.map((item) => (
          <RecommendationCard key={item.krx_code} item={item} onSelect={onSelect} />
        ))}
      </ul>

      {/* 모바일 반응형 — 카드 레이아웃 조정 */}
      <style>{`
        @media (max-width: 767px) {
          .recommendation-list li {
            padding: 0.75rem 1rem !important;
          }
          .recommendation-list li > div:first-child {
            flex-wrap: wrap;
            gap: 0.5rem;
          }
        }
      `}</style>
    </section>
  );
}
