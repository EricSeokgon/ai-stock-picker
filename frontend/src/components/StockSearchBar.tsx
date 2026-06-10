// 종목 검색 바 — 입력 시 debounce(300ms)로 API 호출, 드롭다운 결과 표시
import { useState, useEffect, useRef, useCallback } from 'react';
import { searchStocks } from '../api/stocks';
import type { StockSearchItem } from '../api/stocks';

export interface StockSearchBarProps {
  onSelect: (krxCode: string) => void;
  placeholder?: string;
}

// @MX:ANCHOR: [AUTO] StockSearchBar — 대시보드 검색 진입점
// @MX:REASON: App.tsx, StockDetailPage, 테스트에서 참조되는 공개 컴포넌트

export function StockSearchBar({ onSelect, placeholder = '종목명 또는 코드 검색...' }: StockSearchBarProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<StockSearchItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 외부 클릭 시 드롭다운 닫기
  useEffect(() => {
    function handleOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleOutside);
    return () => document.removeEventListener('mousedown', handleOutside);
  }, []);

  // @MX:WARN: [AUTO] debounce 타이머 관리 — 언마운트 시 반드시 clear 필요
  // @MX:REASON: 언마운트 후 setState 호출 방지; useEffect cleanup으로 처리
  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setQuery(val);

    if (timerRef.current) clearTimeout(timerRef.current);

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
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  function handleSelect(item: StockSearchItem) {
    setQuery('');
    setResults([]);
    setOpen(false);
    onSelect(item.krx_code);
  }

  const showDropdown = open && query.trim().length > 0;

  return (
    <div
      ref={containerRef}
      style={{ position: 'relative', width: '100%', maxWidth: '420px' }}
      role="search"
      aria-label="종목 검색"
    >
      {/* 검색 입력 */}
      <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
        <span
          aria-hidden="true"
          style={{
            position: 'absolute',
            left: '0.625rem',
            color: '#999',
            fontSize: '0.9rem',
            pointerEvents: 'none',
          }}
        >
          🔍
        </span>
        <input
          type="search"
          aria-label="종목 검색 입력"
          aria-autocomplete="list"
          aria-expanded={showDropdown}
          aria-controls="stock-search-listbox"
          value={query}
          onChange={handleChange}
          placeholder={placeholder}
          style={{
            width: '100%',
            padding: '0.5rem 0.75rem 0.5rem 2rem',
            border: '1px solid #ccc',
            borderRadius: '6px',
            fontSize: '0.9rem',
            outline: 'none',
            boxSizing: 'border-box',
          }}
        />
        {loading && (
          <span
            role="status"
            aria-label="검색 중"
            style={{
              position: 'absolute',
              right: '0.625rem',
              width: '14px',
              height: '14px',
              border: '2px solid #ddd',
              borderTop: '2px solid #1976d2',
              borderRadius: '50%',
              animation: 'spin 0.7s linear infinite',
            }}
          />
        )}
      </div>

      {/* 드롭다운 결과 */}
      {showDropdown && (
        <div
          id="stock-search-listbox"
          role="listbox"
          aria-label="검색 결과"
          style={{
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
          }}
        >
          {/* 오류 */}
          {error && (
            <div
              role="alert"
              style={{ padding: '0.75rem 1rem', color: '#c62828', fontSize: '0.875rem' }}
            >
              {error}
            </div>
          )}

          {/* 결과 없음 */}
          {!error && results.length === 0 && (
            <div
              style={{ padding: '0.75rem 1rem', color: '#888', fontSize: '0.875rem' }}
            >
              검색 결과가 없습니다
            </div>
          )}

          {/* 결과 목록 */}
          {!error && results.map((item) => (
            <div
              key={item.krx_code}
              role="option"
              aria-selected={false}
              onClick={() => handleSelect(item)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleSelect(item); }}
              tabIndex={0}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0.6rem 1rem',
                cursor: 'pointer',
                borderBottom: '1px solid #f5f5f5',
                fontSize: '0.875rem',
              }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.backgroundColor = '#f5f8ff'; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.backgroundColor = ''; }}
            >
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1px' }}>
                <span style={{ fontWeight: 600, color: '#222' }}>{item.name}</span>
                <span style={{ fontSize: '0.75rem', color: '#888' }}>{item.krx_code}</span>
              </div>
              {item.in_recommendations && (
                <span
                  style={{
                    padding: '2px 8px',
                    borderRadius: '10px',
                    backgroundColor: '#e3f2fd',
                    color: '#1565c0',
                    fontSize: '0.7rem',
                    fontWeight: 700,
                    flexShrink: 0,
                    marginLeft: '0.5rem',
                  }}
                >
                  추천
                </span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* 스피너 애니메이션 CSS */}
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
