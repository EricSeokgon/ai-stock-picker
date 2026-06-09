// 추천 히스토리 페이지
import { useState, useEffect } from 'react';
import { getRecommendationHistory } from '../api/recommendations';
import type { RecommendationHistoryResponse, DailyRecommendations } from '../api/recommendations';
import type { RecommendationItem } from '../types';

// 기간 선택 옵션
const PERIOD_OPTIONS: { label: string; days: number }[] = [
  { label: '7일', days: 7 },
  { label: '14일', days: 14 },
  { label: '30일', days: 30 },
];

// 점수를 백분율 표시로 변환
function formatScore(score: number): string {
  return (score * 100).toFixed(1);
}

interface RecommendationCardProps {
  item: RecommendationItem;
}

function RecommendationCard({ item }: RecommendationCardProps) {
  return (
    <li
      style={{
        listStyle: 'none',
        border: '1px solid #e0e0e0',
        borderRadius: '8px',
        padding: '0.875rem 1rem',
        backgroundColor: '#fff',
        boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.4rem' }}>
        {/* 순위 배지 */}
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '1.75rem',
            height: '1.75rem',
            borderRadius: '50%',
            backgroundColor: '#1976d2',
            color: '#fff',
            fontSize: '0.75rem',
            fontWeight: 700,
            flexShrink: 0,
          }}
          aria-label={`순위 ${item.rank}`}
        >
          {item.rank}
        </span>

        {/* 종목 정보 */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <span style={{ fontWeight: 600, fontSize: '0.95rem', color: '#212121' }}>
            {/* name 필드가 있으면 표시, 없으면 krx_code 표시 */}
            {(item as RecommendationItem & { name?: string }).name ?? item.krx_code}
          </span>
          <span style={{ marginLeft: '0.5rem', fontSize: '0.8rem', color: '#888' }}>
            {item.krx_code}
          </span>
        </div>

        {/* 종합 점수 */}
        <span
          style={{
            fontSize: '0.85rem',
            fontWeight: 600,
            color: '#1976d2',
            flexShrink: 0,
          }}
          aria-label={`종합 점수 ${formatScore(item.total_score)}`}
        >
          {formatScore(item.total_score)}점
        </span>
      </div>

      {/* explanation / reasoning */}
      {item.reasoning && (
        <p
          style={{
            margin: '0 0 0 2.5rem',
            fontSize: '0.8rem',
            color: '#666',
            lineHeight: 1.5,
          }}
        >
          {item.reasoning}
        </p>
      )}
    </li>
  );
}

interface DailyGroupProps {
  group: DailyRecommendations;
}

function DailyGroup({ group }: DailyGroupProps) {
  return (
    <section aria-labelledby={`date-${group.date}`} style={{ marginBottom: '1.5rem' }}>
      {/* 날짜 헤더 */}
      <h3
        id={`date-${group.date}`}
        style={{
          fontSize: '0.95rem',
          fontWeight: 700,
          color: '#424242',
          margin: '0 0 0.75rem 0',
          padding: '0.4rem 0.75rem',
          backgroundColor: '#f5f5f5',
          borderLeft: '3px solid #1976d2',
          borderRadius: '0 4px 4px 0',
        }}
      >
        {group.date}
      </h3>
      <ul style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', padding: 0, margin: 0 }}>
        {group.recommendations.map((item) => (
          <RecommendationCard key={`${group.date}-${item.krx_code}`} item={item} />
        ))}
      </ul>
    </section>
  );
}

export default function History() {
  const [selectedDays, setSelectedDays] = useState<number>(7);
  const [data, setData] = useState<RecommendationHistoryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadHistory() {
      setLoading(true);
      setError(null);
      try {
        const result = await getRecommendationHistory(selectedDays);
        if (!cancelled) {
          setData(result);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : '히스토리를 불러오는 중 오류가 발생했습니다.');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadHistory();
    return () => {
      cancelled = true;
    };
  }, [selectedDays]);

  return (
    <div>
      {/* 페이지 헤더 */}
      <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '1.25rem', color: '#212121' }}>
        추천 히스토리
      </h1>

      {/* 기간 선택 탭 */}
      <div
        role="tablist"
        aria-label="기간 선택"
        style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}
      >
        {PERIOD_OPTIONS.map((opt) => (
          <button
            key={opt.days}
            role="tab"
            aria-selected={selectedDays === opt.days}
            onClick={() => setSelectedDays(opt.days)}
            style={{
              padding: '0.4rem 1rem',
              border: '1px solid',
              borderColor: selectedDays === opt.days ? '#1976d2' : '#ccc',
              borderRadius: '20px',
              backgroundColor: selectedDays === opt.days ? '#1976d2' : '#fff',
              color: selectedDays === opt.days ? '#fff' : '#555',
              fontWeight: selectedDays === opt.days ? 600 : 400,
              cursor: 'pointer',
              fontSize: '0.875rem',
              transition: 'all 0.15s ease',
            }}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* 로딩 상태 */}
      {loading && (
        <div
          role="status"
          aria-live="polite"
          style={{ textAlign: 'center', padding: '3rem', color: '#888' }}
        >
          <p>히스토리를 불러오는 중...</p>
        </div>
      )}

      {/* 오류 상태 */}
      {!loading && error && (
        <div
          role="alert"
          style={{
            padding: '1rem',
            backgroundColor: '#ffebee',
            border: '1px solid #ef9a9a',
            borderRadius: '4px',
            color: '#c62828',
          }}
        >
          <strong>오류:</strong> {error}
        </div>
      )}

      {/* 빈 결과 */}
      {!loading && !error && data && data.groups.length === 0 && (
        <p style={{ color: '#888', fontSize: '0.9rem', textAlign: 'center', padding: '2rem' }}>
          히스토리 데이터가 없습니다.
        </p>
      )}

      {/* 날짜별 그룹 목록 */}
      {!loading && !error && data && data.groups.length > 0 && (
        <div>
          {data.groups.map((group) => (
            <DailyGroup key={group.date} group={group} />
          ))}
        </div>
      )}

      {/* 면책 고지 */}
      <p
        style={{
          marginTop: '2rem',
          padding: '0.75rem 1rem',
          backgroundColor: '#fff8e1',
          borderLeft: '3px solid #ffc107',
          borderRadius: '0 4px 4px 0',
          fontSize: '0.8rem',
          color: '#5f4000',
          lineHeight: 1.6,
        }}
      >
        본 히스토리는 투자 권유가 아닌 정보 제공 목적입니다. 과거 추천 이력이 미래 수익을 보장하지 않으며,
        투자 결정은 본인 책임하에 이루어져야 합니다.
      </p>
    </div>
  );
}
