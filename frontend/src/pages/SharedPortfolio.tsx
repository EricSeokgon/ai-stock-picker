// 공유 포트폴리오 공개 보기 페이지 (SPEC-STOCK-042, 인증 불필요)
// SPEC-STOCK-046: 댓글 UI 추가
import { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  addComment,
  deleteComment,
  getComments,
  getSharedPortfolio,
  likeSharedPortfolio,
  unlikeSharedPortfolio,
  type CommentItem,
  type SharePublicResponse,
} from '../api/feed';
import { useAuth } from '../auth/AuthContext';

// 수익률 색상
function rateColor(rate: number): string {
  return rate >= 0 ? '#2e7d32' : '#c62828';
}

function formatRate(rate: number): string {
  return `${rate >= 0 ? '+' : ''}${rate.toFixed(2)}%`;
}

// @MX:NOTE: [AUTO] SharedPortfolio 페이지 — 공개 포트폴리오 상세 보기, 좋아요, 댓글 (SPEC-STOCK-042, SPEC-STOCK-046)
export default function SharedPortfolio() {
  const { shareToken } = useParams<{ shareToken: string }>();
  const { token } = useAuth();

  const [data, setData] = useState<SharePublicResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [likeCount, setLikeCount] = useState(0);
  const [liked, setLiked] = useState(false);
  const [likeLoading, setLikeLoading] = useState(false);
  const [likeError, setLikeError] = useState<string | null>(null);

  // 댓글 상태
  const [comments, setComments] = useState<CommentItem[]>([]);
  const [commentTotal, setCommentTotal] = useState(0);
  const [commentLoading, setCommentLoading] = useState(false);
  const [commentError, setCommentError] = useState<string | null>(null);
  const [newComment, setNewComment] = useState('');
  const [submitLoading, setSubmitLoading] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const commentInputRef = useRef<HTMLTextAreaElement>(null);

  // 공유 포트폴리오 데이터 조회
  useEffect(() => {
    if (!shareToken) return;
    setLoading(true);
    setError(null);
    getSharedPortfolio(shareToken)
      .then((res) => {
        setData(res);
        setLikeCount(res.like_count);
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : '포트폴리오를 불러올 수 없습니다.');
      })
      .finally(() => setLoading(false));
  }, [shareToken]);

  // 댓글 목록 조회
  useEffect(() => {
    if (!shareToken) return;
    setCommentLoading(true);
    setCommentError(null);
    getComments(shareToken)
      .then((res) => {
        setComments(res.items);
        setCommentTotal(res.total);
      })
      .catch((e: unknown) => {
        setCommentError(e instanceof Error ? e.message : '댓글을 불러올 수 없습니다.');
      })
      .finally(() => setCommentLoading(false));
  }, [shareToken]);

  // 댓글 작성 핸들러
  async function handleCommentSubmit() {
    if (!shareToken || !newComment.trim()) return;
    if (!token) {
      setSubmitError('로그인 후 댓글을 작성할 수 있습니다.');
      return;
    }
    setSubmitLoading(true);
    setSubmitError(null);
    try {
      const created = await addComment(shareToken, newComment, token);
      setComments((prev) => [created, ...prev]);
      setCommentTotal((t) => t + 1);
      setNewComment('');
    } catch (e: unknown) {
      setSubmitError(e instanceof Error ? e.message : '댓글 작성에 실패했습니다.');
    } finally {
      setSubmitLoading(false);
    }
  }

  // 댓글 삭제 핸들러
  async function handleCommentDelete(commentId: number) {
    if (!shareToken || !token) return;
    try {
      await deleteComment(shareToken, commentId, token);
      setComments((prev) => prev.filter((c) => c.id !== commentId));
      setCommentTotal((t) => t - 1);
    } catch (e: unknown) {
      setCommentError(e instanceof Error ? e.message : '댓글 삭제에 실패했습니다.');
    }
  }

  // 좋아요/취소 토글 처리 (session-local: 초기값 false, 서버 응답 확인 후 상태 변경)
  async function handleLike() {
    if (!shareToken) return;
    if (!token) {
      setLikeError('로그인 후 좋아요를 누를 수 있습니다.');
      return;
    }
    setLikeLoading(true);
    setLikeError(null);
    try {
      if (liked) {
        await unlikeSharedPortfolio(shareToken, token);
        setLiked(false);
        setLikeCount((c) => c - 1);
      } else {
        const res = await likeSharedPortfolio(shareToken, token);
        setLiked(true);
        setLikeCount(res.like_count);
      }
    } catch (e: unknown) {
      setLikeError(e instanceof Error ? e.message : '좋아요 처리에 실패했습니다.');
    } finally {
      setLikeLoading(false);
    }
  }

  if (loading) {
    return (
      <div role="status" aria-live="polite" style={{ textAlign: 'center', padding: '3rem', color: '#666' }}>
        로딩 중...
      </div>
    );
  }

  if (error) {
    return (
      <div
        role="alert"
        style={{
          padding: '1rem',
          background: '#ffebee',
          border: '1px solid #ef9a9a',
          borderRadius: '4px',
          color: '#c62828',
        }}
      >
        {error}
      </div>
    );
  }

  if (!data) return null;

  const cellStyle: React.CSSProperties = { padding: '0.4rem 0.6rem', fontSize: '0.875rem' };

  return (
    <div>
      {/* 헤더 */}
      <div style={{ marginBottom: '1.5rem' }}>
        <h2 style={{ margin: '0 0 0.5rem', color: '#0d47a1' }}>{data.portfolio_name}</h2>

        {/* 수익률 + 통계 */}
        <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap', alignItems: 'center' }}>
          <div>
            <span style={{ fontSize: '0.75rem', color: '#666' }}>총 수익률</span>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: rateColor(data.total_return_rate) }}>
              {formatRate(data.total_return_rate)}
            </div>
          </div>

          {/* 목표 달성률 (있을 경우) */}
          {data.goal_progress !== null && (
            <div>
              <span style={{ fontSize: '0.75rem', color: '#666' }}>목표 달성률</span>
              <div style={{ fontSize: '1.1rem', fontWeight: 600, color: data.goal_progress >= 100 ? '#2e7d32' : '#1565c0' }}>
                {data.goal_progress.toFixed(1)}%
              </div>
            </div>
          )}

          <div>
            <span style={{ fontSize: '0.75rem', color: '#666' }}>조회수</span>
            <div style={{ fontSize: '1rem', fontWeight: 600 }}>{data.view_count.toLocaleString()}</div>
          </div>
        </div>
      </div>

      {/* 좋아요 버튼 */}
      <div style={{ marginBottom: '1.5rem' }}>
        <button
          data-testid="like-btn"
          onClick={() => void handleLike()}
          disabled={likeLoading}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.4rem',
            padding: '0.45rem 1rem',
            background: liked ? '#e91e63' : '#fff',
            border: '1px solid #e91e63',
            color: liked ? '#fff' : '#e91e63',
            borderRadius: '20px',
            cursor: likeLoading ? 'default' : 'pointer',
            fontSize: '0.875rem',
            fontWeight: 600,
            opacity: likeLoading ? 0.7 : 1,
          }}
        >
          {liked ? '♥ 좋아요 취소' : '♡ 좋아요'}
        </button>
        <span
          data-testid="like-count"
          style={{ marginLeft: '0.5rem', fontSize: '0.875rem', color: '#666' }}
        >
          {likeCount.toLocaleString()}개
        </span>
        {likeError && (
          <span
            data-testid="like-error"
            style={{ marginLeft: '0.75rem', fontSize: '0.8rem', color: '#c62828' }}
          >
            {likeError}
          </span>
        )}
      </div>

      {/* 보유 종목 테이블 */}
      <div>
        <h3 style={{ margin: '0 0 0.75rem', fontSize: '1rem', color: '#333' }}>보유 종목</h3>
        {data.holdings.length === 0 ? (
          <p style={{ color: '#666', fontSize: '0.875rem' }}>보유 종목 정보가 없습니다.</p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem', minWidth: '360px' }}>
              <thead>
                <tr style={{ background: '#e3f2fd' }}>
                  <th style={cellStyle}>티커</th>
                  <th style={{ ...cellStyle, textAlign: 'right' }}>보유 수량</th>
                  <th style={{ ...cellStyle, textAlign: 'right' }}>매수 단가</th>
                </tr>
              </thead>
              <tbody>
                {data.holdings.map((h) => (
                  <tr key={h.ticker} style={{ borderBottom: '1px solid #eee' }}>
                    <td style={{ ...cellStyle, fontWeight: 600 }}>{h.ticker}</td>
                    <td style={{ ...cellStyle, textAlign: 'right' }}>{h.shares.toLocaleString()}</td>
                    <td style={{ ...cellStyle, textAlign: 'right' }}>
                      {h.purchase_price.toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 댓글 섹션 (SPEC-STOCK-046) */}
      <div data-testid="comments-section" style={{ marginTop: '2rem' }}>
        <h3 style={{ margin: '0 0 0.75rem', fontSize: '1rem', color: '#333' }}>
          댓글 <span data-testid="comment-count" style={{ color: '#666', fontWeight: 400 }}>({commentTotal})</span>
        </h3>

        {/* 댓글 작성 영역 */}
        {token ? (
          <div style={{ marginBottom: '1.25rem' }}>
            <textarea
              ref={commentInputRef}
              data-testid="comment-input"
              value={newComment}
              onChange={(e) => setNewComment(e.target.value)}
              placeholder="댓글을 입력하세요 (최대 500자)"
              maxLength={500}
              rows={3}
              style={{
                width: '100%',
                padding: '0.5rem',
                border: '1px solid #ccc',
                borderRadius: '4px',
                fontSize: '0.875rem',
                resize: 'vertical',
                boxSizing: 'border-box',
              }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.4rem' }}>
              <span style={{ fontSize: '0.75rem', color: '#999' }}>{newComment.length}/500</span>
              <button
                data-testid="comment-submit-btn"
                onClick={() => void handleCommentSubmit()}
                disabled={submitLoading || !newComment.trim()}
                style={{
                  padding: '0.4rem 1rem',
                  background: '#1565c0',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: submitLoading || !newComment.trim() ? 'default' : 'pointer',
                  fontSize: '0.875rem',
                  opacity: submitLoading || !newComment.trim() ? 0.6 : 1,
                }}
              >
                {submitLoading ? '게시 중...' : '댓글 게시'}
              </button>
            </div>
            {submitError && (
              <p data-testid="comment-submit-error" style={{ color: '#c62828', fontSize: '0.8rem', marginTop: '0.3rem' }}>
                {submitError}
              </p>
            )}
          </div>
        ) : (
          <p style={{ fontSize: '0.875rem', color: '#666', marginBottom: '1rem' }}>
            댓글을 작성하려면 로그인이 필요합니다.
          </p>
        )}

        {/* 댓글 목록 */}
        {commentLoading ? (
          <p style={{ color: '#666', fontSize: '0.875rem' }}>댓글 불러오는 중...</p>
        ) : commentError ? (
          <p data-testid="comment-error" style={{ color: '#c62828', fontSize: '0.875rem' }}>{commentError}</p>
        ) : comments.length === 0 ? (
          <p data-testid="no-comments" style={{ color: '#999', fontSize: '0.875rem' }}>첫 댓글을 남겨보세요!</p>
        ) : (
          <ul data-testid="comment-list" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {comments.map((c) => (
              <li
                key={c.id}
                data-testid={`comment-item-${c.id}`}
                style={{
                  padding: '0.75rem 0',
                  borderBottom: '1px solid #eee',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  gap: '0.5rem',
                }}
              >
                <div>
                  <span style={{ fontWeight: 600, fontSize: '0.85rem', color: '#333' }}>{c.username}</span>
                  <span style={{ fontSize: '0.75rem', color: '#999', marginLeft: '0.5rem' }}>
                    {new Date(c.created_at).toLocaleString('ko-KR')}
                  </span>
                  <p style={{ margin: '0.2rem 0 0', fontSize: '0.875rem', color: '#444' }}>{c.content}</p>
                </div>
                {token && (
                  <button
                    data-testid={`comment-delete-btn-${c.id}`}
                    onClick={() => void handleCommentDelete(c.id)}
                    style={{
                      flexShrink: 0,
                      background: 'none',
                      border: 'none',
                      color: '#999',
                      cursor: 'pointer',
                      fontSize: '0.8rem',
                      padding: '0.2rem 0.4rem',
                    }}
                  >
                    삭제
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* 면책 조항 */}
      <p style={{ marginTop: '1.5rem', fontSize: '0.75rem', color: '#888' }}>
        이 정보는 참고용이며, 실제 투자 결정은 본인 책임하에 이루어져야 합니다.
      </p>
    </div>
  );
}
