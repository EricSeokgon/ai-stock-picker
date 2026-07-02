import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// 거래 기반 홀딩스 동기화 패널 (SPEC-STOCK-050 REQ-SYNC-014~016)
import { useState } from 'react';
import { useAuth } from '../auth/AuthContext';
import { applyHoldingsSync, previewHoldingsSync, } from '../api/portfolio';
const actionLabel = {
    upsert: '추가/수정',
    delete: '제거',
    unchanged: '변경 없음',
};
const actionColor = {
    upsert: '#1976d2',
    delete: '#c62828',
    unchanged: '#666',
};
export default function HoldingsSyncPanel({ portfolioId, onSynced }) {
    const { token } = useAuth();
    const [items, setItems] = useState(null);
    const [previewLoading, setPreviewLoading] = useState(false);
    const [applyLoading, setApplyLoading] = useState(false);
    const [error, setError] = useState(null);
    const [appliedCount, setAppliedCount] = useState(null);
    async function handlePreview() {
        if (!token)
            return;
        setPreviewLoading(true);
        setError(null);
        setAppliedCount(null);
        try {
            const result = await previewHoldingsSync(token, portfolioId);
            setItems(result.items);
        }
        catch (e) {
            setError(e instanceof Error ? e.message : '동기화 미리보기 실패');
        }
        finally {
            setPreviewLoading(false);
        }
    }
    async function handleApply() {
        if (!token)
            return;
        setApplyLoading(true);
        setError(null);
        try {
            const result = await applyHoldingsSync(token, portfolioId);
            setAppliedCount(result.synced);
            setItems(null);
            onSynced?.(result.holdings);
        }
        catch (e) {
            setError(e instanceof Error ? e.message : '동기화 적용 실패');
        }
        finally {
            setApplyLoading(false);
        }
    }
    const panelStyle = {
        border: '1px solid #e5e7eb',
        borderRadius: 8,
        padding: '1rem',
        marginTop: '1rem',
    };
    const hasChanges = items != null && items.length > 0;
    return (_jsxs("div", { style: panelStyle, children: [_jsx("h3", { style: { margin: '0 0 0.75rem', fontSize: '1rem', fontWeight: 600 }, children: "홀딩스 동기화" }), _jsxs("div", { style: { display: 'flex', gap: '0.5rem', marginBottom: '0.75rem' }, children: [_jsx("button", { onClick: () => void handlePreview(), disabled: previewLoading, style: { padding: '0.4rem 0.8rem', cursor: previewLoading ? 'default' : 'pointer' }, children: previewLoading ? '조회 중...' : '미리보기' }), hasChanges && (_jsx("button", { onClick: () => void handleApply(), disabled: applyLoading, style: { padding: '0.4rem 0.8rem', cursor: applyLoading ? 'default' : 'pointer' }, children: applyLoading ? '적용 중...' : '적용' }))] }), error && _jsx("p", { style: { color: '#dc2626' }, children: error }), appliedCount !== null && (_jsxs("p", { style: { color: '#10b981', fontWeight: 600 }, children: ["동기화 완료 — ", appliedCount, "건 변경됨"] })), items != null && items.length === 0 && (_jsx("p", { style: { color: '#6b7280' }, children: "변경 없음" })), hasChanges && (_jsxs("table", { style: { width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }, children: [_jsx("thead", { children: _jsxs("tr", { style: { background: '#f3f4f6' }, children: [_jsx("th", { style: { textAlign: 'left', padding: '0.35rem 0.5rem' }, children: "종목코드" }), _jsx("th", { style: { textAlign: 'left', padding: '0.35rem 0.5rem' }, children: "변경" }), _jsx("th", { style: { textAlign: 'right', padding: '0.35rem 0.5rem' }, children: "현재 수량" }), _jsx("th", { style: { textAlign: 'right', padding: '0.35rem 0.5rem' }, children: "변경 후 수량" })] }) }), _jsx("tbody", { children: items.map((item) => (_jsxs("tr", { style: { borderBottom: '1px solid #eee' }, children: [_jsx("td", { style: { padding: '0.35rem 0.5rem' }, children: item.krx_code }), _jsx("td", { style: { padding: '0.35rem 0.5rem', color: actionColor[item.action] }, children: actionLabel[item.action] }), _jsx("td", { style: { padding: '0.35rem 0.5rem', textAlign: 'right' }, children: item.current_qty }), _jsx("td", { style: { padding: '0.35rem 0.5rem', textAlign: 'right' }, children: item.derived_qty })] }, item.krx_code))) })] }))] }));
}
