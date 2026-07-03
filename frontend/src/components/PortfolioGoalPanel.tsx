// 포트폴리오 목표 관리 패널 (SPEC-STOCK-041)
import { useEffect, useState } from 'react';
import { useAuth } from '../auth/AuthContext';
import {
  createPortfolioGoal,
  deletePortfolioGoal,
  getPortfolioGoal,
  type GoalCreate,
  type GoalWithProgressResponse,
} from '../api/portfolio';

// @MX:NOTE: [AUTO] SPEC-STOCK-041 — 목표 설정/달성률 패널.
// @MX:SPEC: SPEC-STOCK-041 REQ-GOAL-001~006

interface Props {
  portfolioId: number;
}

export default function PortfolioGoalPanel({ portfolioId }: Props) {
  const { token } = useAuth();
  const [goal, setGoal] = useState<GoalWithProgressResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 신규 목표 입력 폼 상태
  const [showForm, setShowForm] = useState(false);
  const [targetAmount, setTargetAmount] = useState('');
  const [targetReturnRate, setTargetReturnRate] = useState('');
  const [deadline, setDeadline] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!token) return;
    void loadGoal();
  }, [portfolioId, token]);

  async function loadGoal() {
    setLoading(true);
    setError(null);
    try {
      const data = await getPortfolioGoal(token!, portfolioId);
      setGoal(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : '오류가 발생했습니다');
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate() {
    if (!token) return;
    const amount = targetAmount ? parseFloat(targetAmount) : null;
    const rate = targetReturnRate ? parseFloat(targetReturnRate) : null;

    if (!amount && !rate) {
      setError('목표 평가액 또는 목표 수익률 중 하나 이상을 입력해주세요.');
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const payload: GoalCreate = {
        target_amount: amount,
        target_return_rate: rate,
        deadline: deadline || null,
      };
      await createPortfolioGoal(token, portfolioId, payload);
      setShowForm(false);
      setTargetAmount('');
      setTargetReturnRate('');
      setDeadline('');
      await loadGoal();
    } catch (e) {
      setError(e instanceof Error ? e.message : '목표 생성 실패');
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete() {
    if (!token || !goal) return;
    if (!window.confirm('목표를 삭제하시겠습니까?')) return;
    setLoading(true);
    try {
      await deletePortfolioGoal(token, portfolioId, goal.id);
      setGoal(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : '목표 삭제 실패');
    } finally {
      setLoading(false);
    }
  }

  const panelStyle: React.CSSProperties = {
    border: '1px solid #e5e7eb',
    borderRadius: 8,
    padding: '1rem',
    marginTop: '1rem',
  };

  return (
    <div style={panelStyle}>
      <h3 style={{ margin: '0 0 0.75rem', fontSize: '1rem', fontWeight: 600 }}>
        투자 목표
      </h3>

      {loading && <p style={{ color: '#6b7280' }}>불러오는 중...</p>}
      {error && <p style={{ color: '#dc2626' }}>{error}</p>}

      {!loading && !goal && !showForm && (
        <div>
          <p style={{ color: '#6b7280', marginBottom: '0.5rem' }}>설정된 목표가 없습니다.</p>
          <button
            onClick={() => setShowForm(true)}
            style={{ padding: '0.4rem 0.8rem', cursor: 'pointer' }}
          >
            목표 설정
          </button>
        </div>
      )}

      {showForm && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxWidth: 340 }}>
          <label>
            목표 평가액 (원)
            <input
              type="number"
              value={targetAmount}
              onChange={e => setTargetAmount(e.target.value)}
              placeholder="예: 10000000"
              style={{ display: 'block', width: '100%', marginTop: 2, padding: '0.3rem' }}
            />
          </label>
          <label>
            목표 수익률 (%)
            <input
              type="number"
              value={targetReturnRate}
              onChange={e => setTargetReturnRate(e.target.value)}
              placeholder="예: 15"
              style={{ display: 'block', width: '100%', marginTop: 2, padding: '0.3rem' }}
            />
          </label>
          <label>
            달성 기한 (선택)
            <input
              type="date"
              value={deadline}
              onChange={e => setDeadline(e.target.value)}
              style={{ display: 'block', width: '100%', marginTop: 2, padding: '0.3rem' }}
            />
          </label>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              onClick={() => void handleCreate()}
              disabled={submitting}
              style={{ padding: '0.4rem 0.8rem', cursor: 'pointer' }}
            >
              {submitting ? '저장 중...' : '저장'}
            </button>
            <button
              onClick={() => { setShowForm(false); setError(null); }}
              style={{ padding: '0.4rem 0.8rem', cursor: 'pointer' }}
            >
              취소
            </button>
          </div>
        </div>
      )}

      {!loading && goal && (
        <div>
          {/* 달성률 프로그레스 바 */}
          <div style={{ marginBottom: '0.75rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <span style={{ fontSize: '0.875rem', color: '#374151' }}>달성률</span>
              <span style={{ fontWeight: 600 }}>{goal.achievement_rate.toFixed(1)}%</span>
            </div>
            <div style={{ height: 8, background: '#e5e7eb', borderRadius: 4, overflow: 'hidden' }}>
              <div
                style={{
                  height: '100%',
                  width: `${Math.min(goal.achievement_rate, 100)}%`,
                  background: goal.achievement_rate >= 100 ? '#10b981' : '#3b82f6',
                  transition: 'width 0.3s',
                }}
              />
            </div>
          </div>

          {/* 목표 상세 */}
          <div style={{ fontSize: '0.875rem', color: '#4b5563', display: 'flex', flexDirection: 'column', gap: 4 }}>
            {goal.target_amount != null && (
              <span>목표 평가액: {goal.target_amount.toLocaleString()}원</span>
            )}
            {goal.target_return_rate != null && (
              <span>목표 수익률: {goal.target_return_rate}%</span>
            )}
            {goal.deadline && (
              <span>
                달성 기한: {goal.deadline}
                {goal.days_remaining !== null && (
                  <span style={{ marginLeft: 4, color: goal.days_remaining === 0 ? '#dc2626' : '#6b7280' }}>
                    ({goal.days_remaining === 0 ? '기한 만료' : `D-${goal.days_remaining}`})
                  </span>
                )}
              </span>
            )}
            {goal.goal_reached_notified && (
              <span style={{ color: '#10b981', fontWeight: 600 }}>달성 완료 — 알림 발송됨</span>
            )}
          </div>

          <button
            onClick={() => void handleDelete()}
            style={{ marginTop: '0.75rem', padding: '0.4rem 0.8rem', cursor: 'pointer', color: '#dc2626' }}
          >
            목표 삭제
          </button>
        </div>
      )}
    </div>
  );
}
