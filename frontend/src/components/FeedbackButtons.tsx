// 피드백 버튼 컴포넌트 — 좋아요/싫어요 + 카운트 표시
import { useEffect, useState } from 'react';
import { fetchFeedbackSummary, submitFeedback } from '../api/recommendations';

export interface FeedbackButtonsProps {
  krxCode: string;
}

export function FeedbackButtons({ krxCode }: FeedbackButtonsProps) {
  const [upCount, setUpCount] = useState(0);
  const [downCount, setDownCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchFeedbackSummary(krxCode)
      .then((data) => {
        if (cancelled) return;
        setUpCount(data.up);
        setDownCount(data.down);
      })
      .catch(() => {
        if (!cancelled) setError('피드백 정보를 불러올 수 없습니다');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [krxCode]);

  async function handleVote(vote: 'up' | 'down') {
    if (submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const data = await submitFeedback(krxCode, vote);
      setUpCount(data.up);
      setDownCount(data.down);
    } catch {
      setError('피드백 제출 중 오류가 발생했습니다');
    } finally {
      setSubmitting(false);
    }
  }

  const isDisabled = loading || submitting;

  const btnStyle = (active: boolean): React.CSSProperties => ({
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.3rem',
    padding: '0.35rem 0.75rem',
    border: `1px solid ${active ? '#1976d2' : '#ddd'}`,
    borderRadius: '20px',
    background: active ? '#e3f2fd' : '#fafafa',
    cursor: isDisabled ? 'not-allowed' : 'pointer',
    opacity: isDisabled ? 0.6 : 1,
    fontSize: '0.85rem',
    fontWeight: 600,
    color: '#333',
    transition: 'background 0.15s',
  });

  return (
    <div>
      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
        <button
          aria-label={`좋아요 ${upCount}개`}
          disabled={isDisabled}
          onClick={() => { void handleVote('up'); }}
          style={btnStyle(false)}
        >
          <span aria-hidden="true">👍</span>
          <span>{upCount}</span>
        </button>
        <button
          aria-label={`싫어요 ${downCount}개`}
          disabled={isDisabled}
          onClick={() => { void handleVote('down'); }}
          style={btnStyle(false)}
        >
          <span aria-hidden="true">👎</span>
          <span>{downCount}</span>
        </button>
      </div>
      {error && (
        <p
          role="alert"
          style={{ margin: '0.4rem 0 0', fontSize: '0.8rem', color: '#c62828' }}
        >
          {error}
        </p>
      )}
    </div>
  );
}
