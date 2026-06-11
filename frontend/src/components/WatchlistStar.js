import { jsx as _jsx } from "react/jsx-runtime";
// 관심 목록 별표 토글 컴포넌트 (REQ-FE-004)
// Props: { krxCode: string; isWatchlisted: boolean; onToggle: () => void }
// - ★: 관심 목록에 있음
// - ☆: 관심 목록에 없음
// - 미인증 상태: 로그인 페이지로 이동
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
export function WatchlistStar({ krxCode: _krxCode, isWatchlisted, onToggle }) {
    const { isAuthenticated } = useAuth();
    const navigate = useNavigate();
    function handleClick() {
        if (!isAuthenticated) {
            // 미인증 시 로그인 페이지로 이동
            void navigate('/login');
            return;
        }
        onToggle();
    }
    return (_jsx("button", { onClick: handleClick, "aria-label": isWatchlisted ? '관심 목록에서 제거' : '관심 목록에 추가', title: isWatchlisted ? '관심 목록에서 제거' : '관심 목록에 추가', style: {
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            fontSize: '1.1rem',
            padding: '0.1rem 0.25rem',
            lineHeight: 1,
            color: isWatchlisted ? '#f9a825' : '#aaa',
        }, children: isWatchlisted ? '★' : '☆' }));
}
