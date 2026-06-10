// 종목 상세 전체 페이지 뷰 — /stocks/:krxCode 라우트
import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { fetchRecommendationDetail } from '../api/client';
import type { RecommendationDetail, ContributingNewsItem } from '../types';
import { PriceChart } from '../components/PriceChart';
import { FeedbackButtons } from '../components/FeedbackButtons';

const DISCLAIMER = '본 정보는 투자 권유가 아닌 참고 목적입니다';

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

function ScoreRow({ label, score }: { label: string; score: number }) {
  const pct = Math.min(100, Math.max(0, Math.round(score * 100)));
  const color = score >= 0 ? '#2e7d32' : '#c62828';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
      <span style={{ fontSize: '0.75rem', color: '#666', width: '72px', flexShrink: 0 }}>{label}</span>
      <div style={{ flex: 1, height: '6px', backgroundColor: '#e0e0e0', borderRadius: '3px', overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${pct}%`, backgroundColor: color, borderRadius: '3px' }} />
      </div>
      <span style={{ fontSize: '0.75rem', color, width: '42px', textAlign: 'right', flexShrink: 0 }}>
        {score.toFixed(3)}
      </span>
    </div>
  );
}

function NewsListItem({ item }: { item: ContributingNewsItem }) {
  return (
    <li style={{ padding: '0.5rem 0', borderBottom: '1px solid #f0f0f0', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem' }}>
        <SentimentBadge sentiment={item.sentiment} />
        <span style={{ fontSize: '0.875rem', color: '#333', lineHeight: 1.4 }}>{item.title}</span>
      </div>
      {item.summary && (
        <p style={{ margin: 0, fontSize: '0.8rem', color: '#666', paddingLeft: '2.5rem' }}>{item.summary}</p>
      )}
    </li>
  );
}

// 전체 페이지용 인라인 종목 상세 컴포넌트
function InlineStockDetail({ krxCode }: { krxCode: string }) {
  const [detail, setDetail] = useState<RecommendationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchRecommendationDetail(krxCode)
      .then((data) => { if (!cancelled) setDetail(data); })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : '상세 정보를 불러올 수 없습니다.');
      })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  }, [krxCode]);

  return (
    <div style={{ padding: '1.25rem' }}>
      <h2 style={{ margin: '0 0 0.5rem', fontSize: '1.2rem', fontWeight: 700, color: '#0d47a1' }}>
        {loading ? krxCode : (detail?.krx_code ?? krxCode)}
      </h2>

      {loading && (
        <p style={{ textAlign: 'center', color: '#888', padding: '2rem 0' }}>불러오는 중...</p>
      )}

      {error && (
        <p style={{ color: '#c62828', padding: '1rem 0' }}>오류: {error}</p>
      )}

      {detail && !loading && (
        <>
          <p style={{ margin: '0 0 0.75rem', fontSize: '0.8rem', color: '#888' }}>기준일: {detail.trade_date}</p>

          {/* 점수 분석 */}
          <div style={{ marginBottom: '1rem' }}>
            <p style={{ margin: '0 0 0.5rem', fontSize: '0.85rem', fontWeight: 600, color: '#333' }}>
              점수 분석 (종합: {(detail.total_score * 100).toFixed(1)}점)
            </p>
            <ScoreRow label="감성" score={detail.sentiment_score} />
            <ScoreRow label="거래량" score={detail.volume_score} />
            <ScoreRow label="모멘텀" score={detail.momentum_score} />
            <ScoreRow label="이상감지" score={detail.anomaly_score} />
          </div>

          {/* 가격 차트 — 실패해도 나머지 컨텐츠에 영향 없음 */}
          <div style={{ marginBottom: '1rem' }}>
            <PriceChart krxCode={krxCode} />
          </div>

          {/* 피드백 버튼 */}
          <div style={{ marginBottom: '1rem' }}>
            <p style={{ margin: '0 0 0.4rem', fontSize: '0.85rem', fontWeight: 600, color: '#333' }}>이 추천이 도움이 됐나요?</p>
            <FeedbackButtons krxCode={krxCode} />
          </div>

          {/* 추천 이유 */}
          <div style={{ marginBottom: '1rem' }}>
            <p style={{ margin: '0 0 0.5rem', fontSize: '0.85rem', fontWeight: 600, color: '#333' }}>추천 이유</p>
            <p style={{ margin: 0, fontSize: '0.875rem', color: '#444', lineHeight: 1.6, backgroundColor: '#f5f5f5', padding: '0.75rem', borderRadius: '6px' }}>
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
                  <NewsListItem key={idx} item={news} />
                ))}
              </ul>
            </div>
          )}

          <p style={{ marginTop: '1rem', fontSize: '0.75rem', color: '#999', fontStyle: 'italic' }}>
            {detail.disclaimer}
          </p>
        </>
      )}
    </div>
  );
}

export default function StockDetailPage() {
  const { krxCode } = useParams<{ krxCode: string }>();

  if (!krxCode) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#c62828' }}>
        종목 코드가 올바르지 않습니다.
      </div>
    );
  }

  return (
    <div style={{ maxWidth: '640px', margin: '0 auto', padding: '1rem 0' }}>
      {/* 뒤로가기 링크 */}
      <div style={{ marginBottom: '1rem' }}>
        <Link to="/" style={{ color: '#1976d2', textDecoration: 'none', fontSize: '0.875rem' }}>
          ← 홈으로
        </Link>
      </div>

      {/* 종목 상세 카드 */}
      <div
        style={{
          background: '#fff',
          borderRadius: '12px',
          boxShadow: '0 2px 12px rgba(0,0,0,0.1)',
          overflow: 'hidden',
        }}
      >
        <InlineStockDetail krxCode={krxCode} />
      </div>

      {/* 투자 면책 조항 */}
      <p
        style={{
          marginTop: '1.5rem',
          padding: '0.75rem 1rem',
          backgroundColor: '#fffde7',
          border: '1px solid #fff176',
          borderRadius: '6px',
          fontSize: '0.8rem',
          color: '#795548',
          fontStyle: 'italic',
        }}
        role="note"
      >
        {DISCLAIMER}
      </p>
    </div>
  );
}
