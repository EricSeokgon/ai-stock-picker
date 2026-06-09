// 관심 목록 관리 페이지 (REQ-FE-003)
// - 관심 목록 종목 표시 + LivePriceBadge
// - 삭제 버튼(✕)
// - 목표가 알림 추가/삭제
// - 미인증 시 /login 리다이렉트
// - 빈 목록 안내 메시지

import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import {
  getWatchlist,
  removeFromWatchlist,
  getAlerts,
  createAlert,
  deleteAlert,
  type WatchlistItem,
  type WatchlistAlert,
} from '../api/watchlist';
import { LivePriceBadge } from '../components/LivePriceBadge';

// 알림 추가 인라인 폼 상태
interface AlertFormState {
  krxCode: string;
  targetPrice: string;
  direction: 'above' | 'below';
}

const initialAlertForm: AlertFormState = {
  krxCode: '',
  targetPrice: '',
  direction: 'above',
};

export default function Watchlist() {
  const { isAuthenticated, token } = useAuth();
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [alerts, setAlerts] = useState<WatchlistAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // 열린 알림 폼 — krxCode를 키로 사용, '' 이면 닫힘
  const [openAlertForm, setOpenAlertForm] = useState<string | null>(null);
  const [alertForm, setAlertForm] = useState<AlertFormState>(initialAlertForm);
  const [alertSubmitting, setAlertSubmitting] = useState(false);

  // 미인증 시 로그인 페이지로 이동
  if (!isAuthenticated || !token) {
    return <Navigate to="/login" replace />;
  }

  async function loadData() {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const [watchlistData, alertsData] = await Promise.all([
        getWatchlist(token),
        getAlerts(token),
      ]);
      setItems(watchlistData);
      setAlerts(alertsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : '데이터 조회 실패');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, [token]);

  async function handleRemove(krxCode: string) {
    if (!token) return;
    try {
      await removeFromWatchlist(token, krxCode);
      setItems((prev) => prev.filter((item) => item.krx_code !== krxCode));
    } catch (err) {
      setError(err instanceof Error ? err.message : '삭제 실패');
    }
  }

  function handleOpenAlertForm(krxCode: string) {
    setOpenAlertForm(krxCode);
    setAlertForm({ krxCode, targetPrice: '', direction: 'above' });
    setError(null);
  }

  function handleCloseAlertForm() {
    setOpenAlertForm(null);
    setAlertForm(initialAlertForm);
  }

  // @MX:WARN: [AUTO] 알림 생성 실패 시 UI 롤백 포함 — 낙관적 업데이트 없음
  // @MX:REASON: 서버 응답 전 상태 변경 시 일관성 깨질 수 있음
  async function handleAlertSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!token || !alertForm.targetPrice) return;
    const price = parseFloat(alertForm.targetPrice);
    if (isNaN(price) || price <= 0) {
      setError('유효한 목표가를 입력해주세요.');
      return;
    }
    setAlertSubmitting(true);
    setError(null);
    try {
      const created = await createAlert(token, {
        krx_code: alertForm.krxCode,
        target_price: price,
        direction: alertForm.direction,
      });
      setAlerts((prev) => [...prev, created]);
      handleCloseAlertForm();
    } catch (err) {
      setError(err instanceof Error ? err.message : '알림 추가 실패');
    } finally {
      setAlertSubmitting(false);
    }
  }

  async function handleDeleteAlert(alertId: number) {
    if (!token) return;
    const previous = alerts;
    setAlerts((prev) => prev.filter((a) => a.id !== alertId));
    try {
      await deleteAlert(token, alertId);
    } catch (err) {
      // 실패 시 UI 롤백
      setAlerts(previous);
      setError(err instanceof Error ? err.message : '알림 삭제 실패');
    }
  }

  const rowStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0.6rem 0.8rem',
    borderBottom: '1px solid #eee',
    gap: '0.75rem',
    flexWrap: 'wrap',
  };

  const btnStyle: React.CSSProperties = {
    background: 'none',
    border: '1px solid #ddd',
    borderRadius: '4px',
    cursor: 'pointer',
    padding: '0.2rem 0.5rem',
    fontSize: '0.85rem',
    color: '#666',
  };

  const activeAlerts = alerts.filter((a) => a.is_active);

  return (
    <div>
      <h2 style={{ color: '#0d47a1', marginBottom: '1.5rem' }}>관심 목록</h2>

      {loading && <p style={{ color: '#666' }}>불러오는 중...</p>}

      {error && (
        <p role="alert" style={{ color: '#c62828', fontSize: '0.875rem' }}>
          오류: {error}
        </p>
      )}

      {!loading && items.length === 0 && (
        <p style={{ color: '#666', fontSize: '0.9rem' }}>
          관심 목록이 없습니다. 추천 종목에서 별표를 눌러 추가하세요.
        </p>
      )}

      {items.length > 0 && (
        <div style={{ border: '1px solid #ddd', borderRadius: '6px', overflow: 'hidden', marginBottom: '2rem' }}>
          {items.map((item) => (
            <div key={item.id}>
              <div style={rowStyle}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flex: 1 }}>
                  <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>{item.krx_code}</span>
                  <LivePriceBadge krxCode={item.krx_code} />
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    onClick={() => handleOpenAlertForm(item.krx_code)}
                    aria-label={`${item.krx_code} 알림 추가`}
                    style={{ ...btnStyle, color: '#1976d2', borderColor: '#1976d2' }}
                  >
                    알림 추가
                  </button>
                  <button
                    onClick={() => void handleRemove(item.krx_code)}
                    aria-label={`${item.krx_code} 관심 목록에서 삭제`}
                    style={btnStyle}
                  >
                    ✕
                  </button>
                </div>
              </div>

              {/* 인라인 알림 추가 폼 — 모바일에서 전체 폭 */}
              {openAlertForm === item.krx_code && (
                <form
                  onSubmit={(e) => void handleAlertSubmit(e)}
                  style={{
                    display: 'flex',
                    gap: '0.5rem',
                    padding: '0.5rem 0.8rem',
                    backgroundColor: '#f5f5f5',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                  }}
                  aria-label={`${item.krx_code} 알림 추가 폼`}
                >
                  <input
                    type="number"
                    placeholder="목표가"
                    value={alertForm.targetPrice}
                    onChange={(e) => setAlertForm((prev) => ({ ...prev, targetPrice: e.target.value }))}
                    style={{ flex: '1 1 100px', minWidth: '80px', padding: '0.25rem 0.5rem', border: '1px solid #ccc', borderRadius: '4px' }}
                    aria-label="목표가 입력"
                    min="0"
                    step="any"
                    required
                  />
                  <select
                    value={alertForm.direction}
                    onChange={(e) =>
                      setAlertForm((prev) => ({
                        ...prev,
                        direction: e.target.value as 'above' | 'below',
                      }))
                    }
                    style={{ padding: '0.25rem 0.5rem', border: '1px solid #ccc', borderRadius: '4px' }}
                    aria-label="방향 선택"
                  >
                    <option value="above">이상</option>
                    <option value="below">이하</option>
                  </select>
                  <button
                    type="submit"
                    disabled={alertSubmitting}
                    style={{ ...btnStyle, color: '#fff', background: '#1976d2', borderColor: '#1976d2' }}
                  >
                    {alertSubmitting ? '추가 중...' : '추가'}
                  </button>
                  <button
                    type="button"
                    onClick={handleCloseAlertForm}
                    style={btnStyle}
                  >
                    취소
                  </button>
                </form>
              )}
            </div>
          ))}
        </div>
      )}

      {/* 활성 가격 알림 섹션 */}
      <div>
        <h3 style={{ color: '#333', fontSize: '1rem', marginBottom: '0.75rem' }}>활성 가격 알림</h3>
        {activeAlerts.length === 0 ? (
          <p style={{ color: '#999', fontSize: '0.875rem' }}>등록된 가격 알림이 없습니다.</p>
        ) : (
          <div style={{ border: '1px solid #ddd', borderRadius: '6px', overflow: 'hidden' }}>
            {activeAlerts.map((alert) => (
              <div key={alert.id} style={rowStyle}>
                <span style={{ fontSize: '0.9rem', flex: '1 1 auto', wordBreak: 'break-word' }}>
                  <strong>{alert.krx_code}</strong>{' '}
                  {alert.direction === 'above' ? '이상' : '이하'}{' '}
                  {alert.target_price.toLocaleString()}원
                </span>
                <button
                  onClick={() => void handleDeleteAlert(alert.id)}
                  aria-label={`${alert.krx_code} 알림 삭제`}
                  style={btnStyle}
                >
                  삭제
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
