// 종목 상세 정보 모달 컴포넌트
import { useEffect, useState } from 'react';
import { fetchRecommendationDetail } from '../api/client';
import type { RecommendationDetail, ContributingNewsItem } from '../types';
import { PriceChart } from './PriceChart';
import { FeedbackButtons } from './FeedbackButtons';
import { ScoreBreakdown } from './ScoreBreakdown';

interface StockDetailProps {
  krxCode: string;
  onClose: () => void;
}

// 감성 레이블 및 색상 맵
const SENTIMENT_MAP: Record<string, { label: string; color: string; bg: string }> = {
  positive: { label: '긍정', color: '#1b5e20', bg: '#e8f5e9' },
  negative: { label: '부정', color: '#b71c1c', bg: '#ffebee' },
  neutral:  { label: '중립', color: '#37474f', bg: '#eceff1' },
};

function SentimentBadge({ sentiment }: { sentiment: string }) {
  const info = SENTIMENT_MAP[sentiment] ?? SENTIMENT_MAP['neutral'];
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '1px 8px',
        borderRadius: '12px',
        fontSize: '0.75rem',
        fontWeight: 600,
        color: info.color,
        backgroundColor: info.bg,
        flexShrink: 0,
      }}
    >
      {info.label}
    </span>
  );
}

function NewsItem({ item }: { item: ContributingNewsItem }) {
  return (
    <li
      style={{
        padding: '0.5rem 0',
        borderBottom: '1px solid #f0f0f0',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.25rem',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem' }}>
        <SentimentBadge sentiment={item.sentiment} />
        <span style={{ fontSize: '0.875rem', color: '#333', lineHeight: 1.4 }}>{item.title}</span>
      </div>
      {item.summary && (
        <p style={{ margin: 0, fontSize: '0.8rem', color: '#666', paddingLeft: '2.5rem' }}>
          {item.summary}
        </p>
      )}
    </li>
  );
}

function ScoreRow({ label, score }: { label: string; score: number }) {
  const pct = Math.min(100, Math.max(0, Math.round(score * 100)));
  const color = score >= 0 ? '#2e7d32' : '#c62828';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
      <span style={{ fontSize: '0.75rem', color: '#666', width: '72px', flexShrink: 0 }}>{label}</span>
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
          style={{ height: '100%', width: `${pct}%`, backgroundColor: color, borderRadius: '3px' }}
        />
      </div>
      <span style={{ fontSize: '0.75rem', color, width: '42px', textAlign: 'right', flexShrink: 0 }}>
        {score.toFixed(3)}
      </span>
    </div>
  );
}

// @MX:ANCHOR: [AUTO] StockDetail - 종목 상세 모달 공개 컴포넌트
// @MX:REASON: App.tsx, 테스트에서 직접 참조. 내부에서 API 호출 수행
export function StockDetail({ krxCode, onClose }: StockDetailProps) {
  const [detail, setDetail] = useState<RecommendationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadDetail() {
      try {
        setLoading(true);
        setError(null);
        const data = await fetchRecommendationDetail(krxCode);
        if (!cancelled) setDetail(data);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : '상세 정보를 불러올 수 없습니다.');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void loadDetail();
    return () => { cancelled = true; };
  }, [krxCode]);

  // 오버레이 클릭 시 모달 닫기
  const handleOverlayClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) onClose();
  };

  return (
    // 모달 오버레이
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`${krxCode} 종목 상세`}
      onClick={handleOverlayClick}
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0,0,0,0.45)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: '1rem',
      }}
    >
      {/* 모달 카드 */}
      <div
        style={{
          background: '#fff',
          borderRadius: '12px',
          boxShadow: '0 8px 32px rgba(0,0,0,0.18)',
          width: '100%',
          maxWidth: '560px',
          maxHeight: '80vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {/* 헤더 */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '1rem 1.25rem',
            borderBottom: '1px solid #eee',
          }}
        >
          <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700, color: '#0d47a1' }}>
            {loading ? '종목 상세' : (detail?.krx_code ?? krxCode)}
          </h3>
          <button
            onClick={onClose}
            aria-label="닫기"
            style={{
              background: 'none',
              border: 'none',
              fontSize: '1.25rem',
              cursor: 'pointer',
              color: '#555',
              padding: '0.25rem 0.5rem',
              borderRadius: '4px',
            }}
          >
            ✕
          </button>
        </div>

        {/* 본문 */}
        <div style={{ overflow: 'auto', padding: '1rem 1.25rem', flex: 1 }}>
          {loading && (
            <p style={{ textAlign: 'center', color: '#888', padding: '2rem 0' }}>
              불러오는 중...
            </p>
          )}

          {error && (
            <p style={{ color: '#c62828', padding: '1rem 0' }}>오류: {error}</p>
          )}

          {detail && !loading && (
            <>
              {/* 날짜 */}
              <p style={{ margin: '0 0 0.75rem', fontSize: '0.8rem', color: '#888' }}>
                기준일: {detail.trade_date}
              </p>

              {/* 점수 브레이크다운 */}
              <div style={{ marginBottom: '1rem' }}>
                <p style={{ margin: '0 0 0.5rem', fontSize: '0.85rem', fontWeight: 600, color: '#333' }}>
                  점수 분석 (종합: {(detail.total_score * 100).toFixed(1)}점)
                </p>
                <ScoreRow label="감성" score={detail.sentiment_score} />
                <ScoreRow label="거래량" score={detail.volume_score} />
                <ScoreRow label="모멘텀" score={detail.momentum_score} />
                <ScoreRow label="이상감지" score={detail.anomaly_score} />
              </div>

              {/* 스코어 분해 — score_breakdown이 있을 때만 표시 */}
              {detail.score_breakdown && (
                <div style={{ marginTop: '1rem', marginBottom: '1rem' }}>
                  <h4 style={{ fontSize: '0.875rem', color: '#555', marginBottom: '0.5rem', margin: '0 0 0.5rem' }}>
                    스코어 분해
                  </h4>
                  <ScoreBreakdown breakdown={detail.score_breakdown} />
                </div>
              )}

              {/* 가격 차트 — 실패해도 나머지 컨텐츠 영향 없음 */}
              <div style={{ marginBottom: '1rem' }}>
                <PriceChart krxCode={krxCode} />
              </div>

              {/* 피드백 버튼 */}
              <div style={{ marginBottom: '1rem' }}>
                <p style={{ margin: '0 0 0.4rem', fontSize: '0.85rem', fontWeight: 600, color: '#333' }}>
                  이 추천이 도움이 됐나요?
                </p>
                <FeedbackButtons krxCode={krxCode} />
              </div>

              {/* 추천 이유 */}
              <div style={{ marginBottom: '1rem' }}>
                <p style={{ margin: '0 0 0.5rem', fontSize: '0.85rem', fontWeight: 600, color: '#333' }}>
                  추천 이유
                </p>
                <p
                  style={{
                    margin: 0,
                    fontSize: '0.875rem',
                    color: '#444',
                    lineHeight: 1.6,
                    backgroundColor: '#f5f5f5',
                    padding: '0.75rem',
                    borderRadius: '6px',
                  }}
                >
                  {detail.reasoning}
                </p>
              </div>

              {/* 기여 뉴스 */}
              {detail.contributing_news.length > 0 && (
                <div>
                  <p style={{ margin: '0 0 0.5rem', fontSize: '0.85rem', fontWeight: 600, color: '#333' }}>
                    기여 뉴스 ({detail.contributing_news.length}건)
                  </p>
                  <ul style={{ margin: 0, padding: 0, listStyle: 'none' }}>
                    {detail.contributing_news.map((news, idx) => (
                      <NewsItem key={idx} item={news} />
                    ))}
                  </ul>
                </div>
              )}

              {/* 면책 조항 */}
              <p
                style={{
                  marginTop: '1rem',
                  fontSize: '0.75rem',
                  color: '#999',
                  fontStyle: 'italic',
                }}
              >
                {detail.disclaimer}
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
