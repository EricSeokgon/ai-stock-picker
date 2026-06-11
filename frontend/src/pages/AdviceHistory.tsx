// AI 투자 조언 이력 페이지 — SPEC-STOCK-014 M6
import React, { useEffect, useState } from 'react';
import {
  AdviceHistoryItem,
  FeedbackValue,
  fetchAdviceHistory,
  submitAdviceFeedback,
} from '../api/advice';

interface AdviceHistoryProps {
  token: string | null;
}

const ADVICE_TYPE_LABEL: Record<string, string> = {
  rebalance: '리밸런싱 제안',
  risk_profile: '리스크 프로파일',
  market_briefing: '시장 브리핑',
};

const FEEDBACK_LABEL: Record<string, string> = {
  helpful: '도움됨',
  not_helpful: '도움 안됨',
  neutral: '보통',
};

// @MX:NOTE: [AUTO] feedback 버튼 상태 변경 후 즉시 UI 반영 (낙관적 업데이트 패턴)

const AdviceHistory: React.FC<AdviceHistoryProps> = ({ token }) => {
  const [history, setHistory] = useState<AdviceHistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [feedbackPending, setFeedbackPending] = useState<number | null>(null);

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    fetchAdviceHistory(token)
      .then(setHistory)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token]);

  const handleFeedback = async (adviceId: number, feedback: FeedbackValue) => {
    if (!token || feedbackPending !== null) return;
    setFeedbackPending(adviceId);
    try {
      await submitAdviceFeedback(token, adviceId, feedback);
      // 낙관적 업데이트: 로컬 상태 즉시 반영
      setHistory((prev) =>
        prev.map((item) =>
          item.id === adviceId ? { ...item, feedback } : item
        )
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : '피드백 제출 실패');
    } finally {
      setFeedbackPending(null);
    }
  };

  if (!token) {
    return (
      <div className="container mx-auto p-4">
        <p className="text-gray-500">로그인이 필요합니다.</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="container mx-auto p-4">
        <p className="text-gray-500">AI 조언 이력을 불러오는 중...</p>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">AI 투자 조언 이력</h1>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded p-3 mb-4 text-red-700">
          {error}
        </div>
      )}

      {history.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <p>아직 생성된 AI 조언이 없습니다.</p>
          <p className="text-sm mt-2">포트폴리오 페이지에서 AI 조언을 요청해 보세요.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {history.map((item) => (
            <div
              key={item.id}
              className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="inline-block bg-blue-100 text-blue-800 text-xs font-medium px-2 py-1 rounded">
                  {ADVICE_TYPE_LABEL[item.advice_type] ?? item.advice_type}
                </span>
                <span className="text-xs text-gray-400">{item.ref_date}</span>
              </div>

              <h3 className="font-semibold text-gray-800 mb-1">{item.title}</h3>

              {item.body && (
                <p className="text-sm text-gray-600 mb-2 line-clamp-3">{item.body}</p>
              )}

              {item.risk_score !== null && item.risk_score !== undefined && (
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs text-gray-500">리스크 점수:</span>
                  <span
                    className={`font-bold text-sm ${
                      item.risk_score >= 70
                        ? 'text-red-600'
                        : item.risk_score >= 40
                        ? 'text-yellow-600'
                        : 'text-green-600'
                    }`}
                  >
                    {item.risk_score}/100
                  </span>
                </div>
              )}

              {/* 피드백 버튼 */}
              <div className="flex items-center gap-2 mt-3 pt-3 border-t border-gray-100">
                <span className="text-xs text-gray-400">도움이 되었나요?</span>
                {(['helpful', 'neutral', 'not_helpful'] as FeedbackValue[]).map((fb) => (
                  <button
                    key={fb}
                    disabled={feedbackPending === item.id}
                    onClick={() => handleFeedback(item.id, fb)}
                    className={`text-xs px-2 py-1 rounded border transition-colors ${
                      item.feedback === fb
                        ? 'bg-blue-600 text-white border-blue-600'
                        : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
                    } disabled:opacity-50`}
                  >
                    {FEEDBACK_LABEL[fb]}
                  </button>
                ))}
              </div>

              <p className="text-xs text-gray-300 mt-2">
                {new Date(item.created_at).toLocaleString('ko-KR')}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default AdviceHistory;
