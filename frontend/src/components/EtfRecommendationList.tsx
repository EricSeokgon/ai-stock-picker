// ETF 추천 목록 컴포넌트
import type { RecommendationItem } from '../types';

interface EtfRecommendationListProps {
  etfItems: RecommendationItem[];
  onSelect?: (krxCode: string) => void;
}

function EtfItem({
  item,
  onSelect,
}: {
  item: RecommendationItem;
  onSelect?: (krxCode: string) => void;
}) {
  const isClickable = Boolean(onSelect);

  return (
    <li
      onClick={() => onSelect?.(item.krx_code)}
      style={{
        listStyle: 'none',
        padding: '0.75rem 1rem',
        border: '1px solid #ddd',
        borderRadius: '8px',
        backgroundColor: '#fff',
        cursor: isClickable ? 'pointer' : 'default',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.25rem',
        transition: 'box-shadow 0.15s',
      }}
      onMouseEnter={(e) => {
        if (isClickable) (e.currentTarget as HTMLLIElement).style.boxShadow = '0 2px 8px rgba(0,0,0,0.12)';
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLLIElement).style.boxShadow = 'none';
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        {/* 순위 배지 */}
        <span
          aria-label={`순위 ${item.rank}위`}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '28px',
            height: '28px',
            borderRadius: '50%',
            backgroundColor: '#1565c0',
            color: '#fff',
            fontWeight: 700,
            fontSize: '0.8rem',
            flexShrink: 0,
          }}
        >
          {item.rank}
        </span>

        {/* ETF 코드 */}
        <span
          style={{
            fontWeight: 700,
            fontSize: '1rem',
            color: '#212121',
            letterSpacing: '0.04em',
          }}
        >
          {item.krx_code}
        </span>

        {/* 종합 점수 */}
        <span
          style={{
            marginLeft: 'auto',
            fontSize: '0.8rem',
            fontWeight: 600,
            color: '#1565c0',
          }}
        >
          {(item.total_score * 100).toFixed(1)}점
        </span>
      </div>

      {/* 추천 이유 */}
      <p
        style={{
          margin: 0,
          fontSize: '0.8rem',
          color: '#555',
          lineHeight: 1.5,
          paddingLeft: '2.5rem',
        }}
      >
        {item.reasoning}
      </p>
    </li>
  );
}

// @MX:ANCHOR: [AUTO] EtfRecommendationList - ETF 추천 목록 공개 컴포넌트
// @MX:REASON: App.tsx에서 직접 참조하는 외부 노출 컴포넌트
export function EtfRecommendationList({ etfItems, onSelect }: EtfRecommendationListProps) {
  return (
    <section aria-labelledby="etf-heading">
      <h2
        id="etf-heading"
        style={{
          fontSize: '1.25rem',
          fontWeight: 700,
          marginBottom: '1rem',
          color: '#212121',
        }}
      >
        ETF 추천
      </h2>

      {etfItems.length === 0 ? (
        <p style={{ color: '#999', textAlign: 'center', padding: '1rem 0' }}>
          ETF 추천이 없습니다
        </p>
      ) : (
        <ul
          style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', padding: 0, margin: 0 }}
          aria-label="ETF 추천 목록"
        >
          {etfItems.map((item) => (
            <EtfItem key={item.krx_code} item={item} onSelect={onSelect} />
          ))}
        </ul>
      )}
    </section>
  );
}
