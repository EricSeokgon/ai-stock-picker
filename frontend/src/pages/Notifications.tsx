// 알림 인박스 페이지 (SPEC-STOCK-013 REQ-FE-003)
// SPEC-STOCK-047: 딥링크 클릭 이동 지원
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import {
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  type Notification,
} from '../api/notifications';

// 타입별 뱃지 색상 (SPEC-STOCK-046: portfolio_comment 추가)
function TypeBadge({ type }: { type: string }) {
  const colors: Record<string, string> = {
    price_alert: 'bg-yellow-100 text-yellow-800',
    rec_new: 'bg-green-100 text-green-800',
    rec_dropped: 'bg-red-100 text-red-800',
    portfolio_like: 'bg-pink-100 text-pink-800',
    portfolio_comment: 'bg-purple-100 text-purple-800',
  };
  const labels: Record<string, string> = {
    price_alert: '가격 알림',
    rec_new: '신규 추천',
    rec_dropped: '추천 탈락',
    portfolio_like: '좋아요',
    portfolio_comment: '댓글',
  };
  return (
    <span
      className={`inline-block text-xs font-medium px-2 py-0.5 rounded ${colors[type] ?? 'bg-gray-100 text-gray-700'}`}
    >
      {labels[type] ?? type}
    </span>
  );
}

export default function NotificationsPage() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadNotifications = async () => {
    if (!token) return;
    try {
      setLoading(true);
      const data = await fetchNotifications(token, false, 100);
      setNotifications(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadNotifications();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const handleMarkRead = async (id: number) => {
    if (!token) return;
    try {
      const updated = await markNotificationRead(token, id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? updated : n)),
      );
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const handleMarkAllRead = async () => {
    if (!token) return;
    try {
      await markAllNotificationsRead(token);
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch (e) {
      setError((e as Error).message);
    }
  };

  // SPEC-STOCK-047: 딥링크 알림 클릭 — 읽음 처리 후 이동 (REQ-NLINK-009, REQ-NLINK-011)
  const handleLinkClick = async (n: Notification) => {
    if (!token || !n.link) return;
    try {
      if (!n.is_read) {
        const updated = await markNotificationRead(token, n.id);
        setNotifications((prev) => prev.map((x) => (x.id === n.id ? updated : x)));
      }
      navigate(n.link);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">알림 인박스</h1>
        {unreadCount > 0 && (
          <button
            onClick={() => void handleMarkAllRead()}
            className="text-sm text-blue-600 hover:underline"
          >
            전체 읽음 처리 ({unreadCount})
          </button>
        )}
      </div>

      {error && (
        <p className="text-red-500 text-sm mb-4">{error}</p>
      )}

      {loading ? (
        <p className="text-gray-500">불러오는 중...</p>
      ) : notifications.length === 0 ? (
        <p className="text-gray-400 text-center py-16">알림이 없습니다.</p>
      ) : (
        <ul className="space-y-2">
          {notifications.map((n) => (
            <li
              key={n.id}
              className={`rounded-lg border p-4 transition-colors ${
                n.is_read ? 'bg-white border-gray-200' : 'bg-blue-50 border-blue-200'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <TypeBadge type={n.type} />
                    <span className="font-medium text-sm text-gray-900 truncate">
                      {n.krx_code}
                    </span>
                  </div>
                  <p className="text-sm text-gray-700">{n.title}</p>
                  {n.body && (
                    <p className="text-xs text-gray-500 mt-0.5">{n.body}</p>
                  )}
                  <p className="text-xs text-gray-400 mt-1">
                    {new Date(n.created_at).toLocaleString('ko-KR')}
                  </p>
                  {/* SPEC-STOCK-047: 딥링크 버튼 — link 있는 알림에만 노출 (REQ-NLINK-008) */}
                  {n.link && (
                    <button
                      data-testid={`notification-link-${n.id}`}
                      onClick={() => void handleLinkClick(n)}
                      className="text-xs text-indigo-600 hover:underline mt-1"
                    >
                      포트폴리오 보기 →
                    </button>
                  )}
                </div>
                {!n.is_read && (
                  <button
                    onClick={() => void handleMarkRead(n.id)}
                    className="shrink-0 text-xs text-blue-600 hover:underline mt-0.5"
                  >
                    읽음
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
