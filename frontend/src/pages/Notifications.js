import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// 알림 인박스 페이지 (SPEC-STOCK-013 REQ-FE-003)
import { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { fetchNotifications, markAllNotificationsRead, markNotificationRead, } from '../api/notifications';
// 타입별 뱃지 색상
function TypeBadge({ type }) {
    const colors = {
        price_alert: 'bg-yellow-100 text-yellow-800',
        rec_new: 'bg-green-100 text-green-800',
        rec_dropped: 'bg-red-100 text-red-800',
    };
    const labels = {
        price_alert: '가격 알림',
        rec_new: '신규 추천',
        rec_dropped: '추천 탈락',
    };
    return (_jsx("span", { className: `inline-block text-xs font-medium px-2 py-0.5 rounded ${colors[type] ?? 'bg-gray-100 text-gray-700'}`, children: labels[type] ?? type }));
}
export default function NotificationsPage() {
    const { token } = useAuth();
    const [notifications, setNotifications] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const loadNotifications = async () => {
        if (!token)
            return;
        try {
            setLoading(true);
            const data = await fetchNotifications(token, false, 100);
            setNotifications(data);
        }
        catch (e) {
            setError(e.message);
        }
        finally {
            setLoading(false);
        }
    };
    useEffect(() => {
        void loadNotifications();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [token]);
    const handleMarkRead = async (id) => {
        if (!token)
            return;
        try {
            const updated = await markNotificationRead(token, id);
            setNotifications((prev) => prev.map((n) => (n.id === id ? updated : n)));
        }
        catch (e) {
            setError(e.message);
        }
    };
    const handleMarkAllRead = async () => {
        if (!token)
            return;
        try {
            await markAllNotificationsRead(token);
            setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
        }
        catch (e) {
            setError(e.message);
        }
    };
    const unreadCount = notifications.filter((n) => !n.is_read).length;
    return (_jsxs("div", { className: "max-w-2xl mx-auto px-4 py-8", children: [_jsxs("div", { className: "flex items-center justify-between mb-6", children: [_jsx("h1", { className: "text-2xl font-bold", children: "\uC54C\uB9BC \uC778\uBC15\uC2A4" }), unreadCount > 0 && (_jsxs("button", { onClick: () => void handleMarkAllRead(), className: "text-sm text-blue-600 hover:underline", children: ["\uC804\uCCB4 \uC77D\uC74C \uCC98\uB9AC (", unreadCount, ")"] }))] }), error && (_jsx("p", { className: "text-red-500 text-sm mb-4", children: error })), loading ? (_jsx("p", { className: "text-gray-500", children: "\uBD88\uB7EC\uC624\uB294 \uC911..." })) : notifications.length === 0 ? (_jsx("p", { className: "text-gray-400 text-center py-16", children: "\uC54C\uB9BC\uC774 \uC5C6\uC2B5\uB2C8\uB2E4." })) : (_jsx("ul", { className: "space-y-2", children: notifications.map((n) => (_jsx("li", { className: `rounded-lg border p-4 transition-colors ${n.is_read ? 'bg-white border-gray-200' : 'bg-blue-50 border-blue-200'}`, children: _jsxs("div", { className: "flex items-start justify-between gap-2", children: [_jsxs("div", { className: "flex-1 min-w-0", children: [_jsxs("div", { className: "flex items-center gap-2 mb-1", children: [_jsx(TypeBadge, { type: n.type }), _jsx("span", { className: "font-medium text-sm text-gray-900 truncate", children: n.krx_code })] }), _jsx("p", { className: "text-sm text-gray-700", children: n.title }), n.body && (_jsx("p", { className: "text-xs text-gray-500 mt-0.5", children: n.body })), _jsx("p", { className: "text-xs text-gray-400 mt-1", children: new Date(n.created_at).toLocaleString('ko-KR') })] }), !n.is_read && (_jsx("button", { onClick: () => void handleMarkRead(n.id), className: "shrink-0 text-xs text-blue-600 hover:underline mt-0.5", children: "\uC77D\uC74C" }))] }) }, n.id))) }))] }));
}
