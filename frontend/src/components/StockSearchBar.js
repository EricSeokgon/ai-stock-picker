import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// 종목 검색 바 — 입력 시 debounce(300ms)로 API 호출, 드롭다운 결과 표시
import { useState, useEffect, useRef, useCallback } from 'react';
import { searchStocks } from '../api/stocks';
// @MX:ANCHOR: [AUTO] StockSearchBar — 대시보드 검색 진입점
// @MX:REASON: App.tsx, StockDetailPage, 테스트에서 참조되는 공개 컴포넌트
export function StockSearchBar({ onSelect, placeholder = '종목명 또는 코드 검색...' }) {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [open, setOpen] = useState(false);
    const containerRef = useRef(null);
    const timerRef = useRef(null);
    // 외부 클릭 시 드롭다운 닫기
    useEffect(() => {
        function handleOutside(e) {
            if (containerRef.current && !containerRef.current.contains(e.target)) {
                setOpen(false);
            }
        }
        document.addEventListener('mousedown', handleOutside);
        return () => document.removeEventListener('mousedown', handleOutside);
    }, []);
    // @MX:WARN: [AUTO] debounce 타이머 관리 — 언마운트 시 반드시 clear 필요
    // @MX:REASON: 언마운트 후 setState 호출 방지; useEffect cleanup으로 처리
    const handleChange = useCallback((e) => {
        const val = e.target.value;
        setQuery(val);
        if (timerRef.current)
            clearTimeout(timerRef.current);
        if (val.trim().length === 0) {
            setResults([]);
            setOpen(false);
            setError(null);
            return;
        }
        timerRef.current = setTimeout(() => {
            setLoading(true);
            setError(null);
            searchStocks(val.trim())
                .then((data) => {
                setResults(data.results);
                setOpen(true);
            })
                .catch(() => {
                setError('검색 중 오류가 발생했습니다');
                setResults([]);
                setOpen(true);
            })
                .finally(() => setLoading(false));
        }, 300);
    }, []);
    // 언마운트 시 타이머 정리
    useEffect(() => {
        return () => {
            if (timerRef.current)
                clearTimeout(timerRef.current);
        };
    }, []);
    function handleSelect(item) {
        setQuery('');
        setResults([]);
        setOpen(false);
        onSelect(item.krx_code);
    }
    const showDropdown = open && query.trim().length > 0;
    return (_jsxs("div", { ref: containerRef, style: { position: 'relative', width: '100%', maxWidth: '420px' }, role: "search", "aria-label": "\uC885\uBAA9 \uAC80\uC0C9", children: [_jsxs("div", { style: { position: 'relative', display: 'flex', alignItems: 'center' }, children: [_jsx("span", { "aria-hidden": "true", style: {
                            position: 'absolute',
                            left: '0.625rem',
                            color: '#999',
                            fontSize: '0.9rem',
                            pointerEvents: 'none',
                        }, children: "\uD83D\uDD0D" }), _jsx("input", { type: "search", "aria-label": "\uC885\uBAA9 \uAC80\uC0C9 \uC785\uB825", "aria-autocomplete": "list", "aria-expanded": showDropdown, "aria-controls": "stock-search-listbox", value: query, onChange: handleChange, placeholder: placeholder, style: {
                            width: '100%',
                            padding: '0.5rem 0.75rem 0.5rem 2rem',
                            border: '1px solid #ccc',
                            borderRadius: '6px',
                            fontSize: '0.9rem',
                            outline: 'none',
                            boxSizing: 'border-box',
                        } }), loading && (_jsx("span", { role: "status", "aria-label": "\uAC80\uC0C9 \uC911", style: {
                            position: 'absolute',
                            right: '0.625rem',
                            width: '14px',
                            height: '14px',
                            border: '2px solid #ddd',
                            borderTop: '2px solid #1976d2',
                            borderRadius: '50%',
                            animation: 'spin 0.7s linear infinite',
                        } }))] }), showDropdown && (_jsxs("div", { id: "stock-search-listbox", role: "listbox", "aria-label": "\uAC80\uC0C9 \uACB0\uACFC", style: {
                    position: 'absolute',
                    top: '100%',
                    left: 0,
                    right: 0,
                    zIndex: 200,
                    background: '#fff',
                    border: '1px solid #ddd',
                    borderTop: 'none',
                    borderRadius: '0 0 6px 6px',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                    maxHeight: '280px',
                    overflowY: 'auto',
                }, children: [error && (_jsx("div", { role: "alert", style: { padding: '0.75rem 1rem', color: '#c62828', fontSize: '0.875rem' }, children: error })), !error && results.length === 0 && (_jsx("div", { style: { padding: '0.75rem 1rem', color: '#888', fontSize: '0.875rem' }, children: "\uAC80\uC0C9 \uACB0\uACFC\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4" })), !error && results.map((item) => (_jsxs("div", { role: "option", "aria-selected": false, onClick: () => handleSelect(item), onKeyDown: (e) => { if (e.key === 'Enter')
                            handleSelect(item); }, tabIndex: 0, style: {
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            padding: '0.6rem 1rem',
                            cursor: 'pointer',
                            borderBottom: '1px solid #f5f5f5',
                            fontSize: '0.875rem',
                        }, onMouseEnter: (e) => { e.currentTarget.style.backgroundColor = '#f5f8ff'; }, onMouseLeave: (e) => { e.currentTarget.style.backgroundColor = ''; }, children: [_jsxs("div", { style: { display: 'flex', flexDirection: 'column', gap: '1px' }, children: [_jsx("span", { style: { fontWeight: 600, color: '#222' }, children: item.name }), _jsx("span", { style: { fontSize: '0.75rem', color: '#888' }, children: item.krx_code })] }), item.in_recommendations && (_jsx("span", { style: {
                                    padding: '2px 8px',
                                    borderRadius: '10px',
                                    backgroundColor: '#e3f2fd',
                                    color: '#1565c0',
                                    fontSize: '0.7rem',
                                    fontWeight: 700,
                                    flexShrink: 0,
                                    marginLeft: '0.5rem',
                                }, children: "\uCD94\uCC9C" }))] }, item.krx_code)))] })), _jsx("style", { children: `
        @keyframes spin { to { transform: rotate(360deg); } }
      ` })] }));
}
