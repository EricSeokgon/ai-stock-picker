// 추천 종목 필터 바 컴포넌트 (TASK-008)
// 섹터 드롭다운, 정렬 선택, 최소 점수 입력, 초기화 버튼 제공

export interface FilterState {
  sector: string;      // "" = 전체 섹터
  sort: 'score' | 'sentiment' | 'volume';
  minScore: number;    // 0 = 필터 없음
}

export const DEFAULT_FILTERS: FilterState = {
  sector: '',
  sort: 'score',
  minScore: 0,
};

interface RecommendationFilterBarProps {
  sectors: string[];
  filters: FilterState;
  onFilterChange: (filters: FilterState) => void;
  isLoading?: boolean;
}

const containerStyle: React.CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: '0.75rem',
  alignItems: 'flex-end',
  padding: '0.75rem 1rem',
  backgroundColor: '#f5f7fa',
  border: '1px solid #e0e4eb',
  borderRadius: '8px',
  marginBottom: '1rem',
};

const fieldStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '0.25rem',
};

const labelStyle: React.CSSProperties = {
  fontSize: '0.75rem',
  color: '#555',
  fontWeight: 600,
};

const selectStyle: React.CSSProperties = {
  padding: '0.35rem 0.5rem',
  border: '1px solid #ccc',
  borderRadius: '4px',
  fontSize: '0.875rem',
  backgroundColor: '#fff',
  minWidth: '120px',
};

const numberInputStyle: React.CSSProperties = {
  padding: '0.35rem 0.5rem',
  border: '1px solid #ccc',
  borderRadius: '4px',
  fontSize: '0.875rem',
  width: '80px',
};

const resetBtnStyle: React.CSSProperties = {
  padding: '0.35rem 0.75rem',
  border: '1px solid #aaa',
  borderRadius: '4px',
  background: '#fff',
  cursor: 'pointer',
  fontSize: '0.8rem',
  color: '#444',
  alignSelf: 'flex-end',
};

const loadingStyle: React.CSSProperties = {
  fontSize: '0.8rem',
  color: '#1976d2',
  alignSelf: 'center',
  fontStyle: 'italic',
};

// @MX:ANCHOR: [AUTO] RecommendationFilterBar — 필터 UI 공개 컴포넌트
// @MX:REASON: Dashboard, 테스트에서 직접 참조. FilterState + onFilterChange 계약 유지 필요
export function RecommendationFilterBar({
  sectors,
  filters,
  onFilterChange,
  isLoading = false,
}: RecommendationFilterBarProps) {
  function handleSectorChange(e: React.ChangeEvent<HTMLSelectElement>) {
    onFilterChange({ ...filters, sector: e.target.value });
  }

  function handleSortChange(e: React.ChangeEvent<HTMLSelectElement>) {
    onFilterChange({ ...filters, sort: e.target.value as FilterState['sort'] });
  }

  function handleMinScoreChange(e: React.ChangeEvent<HTMLInputElement>) {
    const val = parseFloat(e.target.value);
    onFilterChange({ ...filters, minScore: isNaN(val) ? 0 : Math.min(1, Math.max(0, val)) });
  }

  function handleReset() {
    onFilterChange({ ...DEFAULT_FILTERS });
  }

  return (
    <div style={containerStyle} role="search" aria-label="추천 종목 필터">
      {/* 섹터 필터 */}
      <div style={fieldStyle}>
        <label htmlFor="filter-sector" style={labelStyle}>섹터</label>
        <select
          id="filter-sector"
          value={filters.sector}
          onChange={handleSectorChange}
          style={selectStyle}
          aria-label="섹터 선택"
        >
          <option value="">전체</option>
          {sectors.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      {/* 정렬 기준 */}
      <div style={fieldStyle}>
        <label htmlFor="filter-sort" style={labelStyle}>정렬</label>
        <select
          id="filter-sort"
          value={filters.sort}
          onChange={handleSortChange}
          style={selectStyle}
          aria-label="정렬 기준 선택"
        >
          <option value="score">추천점수</option>
          <option value="sentiment">감성점수</option>
          <option value="volume">거래량이상</option>
        </select>
      </div>

      {/* 최소 점수 */}
      <div style={fieldStyle}>
        <label htmlFor="filter-min-score" style={labelStyle}>최소 점수</label>
        <input
          id="filter-min-score"
          type="number"
          min={0}
          max={1}
          step={0.1}
          value={filters.minScore}
          onChange={handleMinScoreChange}
          style={numberInputStyle}
          aria-label="최소 점수 입력"
        />
      </div>

      {/* 로딩 표시 */}
      {isLoading && (
        <span style={loadingStyle} role="status" aria-live="polite">
          필터 적용 중...
        </span>
      )}

      {/* 초기화 */}
      <button
        type="button"
        onClick={handleReset}
        style={resetBtnStyle}
        aria-label="필터 초기화"
      >
        필터 초기화
      </button>
    </div>
  );
}
