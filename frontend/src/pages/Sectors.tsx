// 섹터 분석 페이지 — 섹터 랭킹 테이블과 상세 패널 제공
import { useEffect, useState } from 'react';
import { fetchSectorRanking } from '../api/sectors';
import type { SectorRankingItem } from '../api/sectors';
import { SectorDetailPanel } from '../components/SectorDetailPanel';

type SortType = 'score' | 'sentiment' | 'volume';

const SORT_OPTIONS: { label: string; value: SortType }[] = [
  { label: '트렌드 점수', value: 'score' },
  { label: '감성 점수', value: 'sentiment' },
  { label: '뉴스 볼륨', value: 'volume' },
];

// @MX:NOTE: [AUTO] 섹터 랭킹 정렬 기준 — score/sentiment/volume 세 가지 지원

function formatScore(value: number): string {
  return value.toFixed(3);
}

interface RankingTableProps {
  sectors: SectorRankingItem[];
  selectedSector: string | null;
  onSelect: (sector: string) => void;
}

function RankingTable({ sectors, selectedSector, onSelect }: RankingTableProps) {
  if (sectors.length === 0) {
    return (
      <p
        style={{
          color: '#888',
          fontSize: '0.9rem',
          textAlign: 'center',
          padding: '2.5rem 1rem',
          border: '1px solid #e0e0e0',
          borderRadius: '8px',
          backgroundColor: '#fafafa',
        }}
      >
        섹터 데이터를 준비 중입니다. 시스템이 데이터를 수집하면 자동으로 표시됩니다.
      </p>
    );
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <table
        style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}
        aria-label="섹터 랭킹 테이블"
      >
        <thead>
          <tr style={{ backgroundColor: '#f5f5f5' }}>
            <th style={thStyle}>섹터명</th>
            <th style={thStyle}>트렌드 점수</th>
            <th style={thStyle}>감성 점수</th>
            <th style={thStyle}>뉴스 볼륨</th>
          </tr>
        </thead>
        <tbody>
          {sectors.map((item) => {
            const isSelected = selectedSector === item.sector;
            return (
              <tr
                key={item.sector}
                onClick={() => onSelect(item.sector)}
                style={{
                  cursor: 'pointer',
                  backgroundColor: isSelected ? '#e3f2fd' : '#fff',
                  borderBottom: '1px solid #e0e0e0',
                  transition: 'background-color 0.15s',
                }}
                aria-selected={isSelected}
                role="row"
              >
                <td style={{ ...tdStyle, fontWeight: 600, color: '#1976d2' }}>{item.sector}</td>
                <td style={tdStyle}>{formatScore(item.trend_score)}</td>
                <td style={tdStyle}>{formatScore(item.avg_sentiment)}</td>
                <td style={tdStyle}>{item.news_volume}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

const thStyle: React.CSSProperties = {
  padding: '0.6rem 0.875rem',
  textAlign: 'left',
  fontWeight: 600,
  color: '#555',
  borderBottom: '2px solid #e0e0e0',
};

const tdStyle: React.CSSProperties = {
  padding: '0.6rem 0.875rem',
  color: '#212121',
};

export default function Sectors() {
  const [sort, setSort] = useState<SortType>('score');
  const [sectors, setSectors] = useState<SectorRankingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSector, setSelectedSector] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const result = await fetchSectorRanking(sort, 10);
        if (!cancelled) setSectors(result.sectors);
      } catch (err) {
        if (!cancelled)
          setError(err instanceof Error ? err.message : '섹터 데이터를 불러오는 중 오류가 발생했습니다.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();
    return () => { cancelled = true; };
  }, [sort]);

  function handleSortChange(newSort: SortType) {
    setSort(newSort);
    setSelectedSector(null);
  }

  function handleRowSelect(sector: string) {
    setSelectedSector((prev) => (prev === sector ? null : sector));
  }

  return (
    <div>
      {/* 페이지 헤더 */}
      <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '1.25rem', color: '#212121' }}>
        섹터 분석
      </h1>

      {/* 정렬 컨트롤 */}
      <div
        role="group"
        aria-label="정렬 기준 선택"
        style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.25rem', flexWrap: 'wrap' }}
      >
        {SORT_OPTIONS.map((opt) => {
          const isActive = sort === opt.value;
          return (
            <button
              key={opt.value}
              onClick={() => handleSortChange(opt.value)}
              aria-pressed={isActive}
              style={{
                padding: '0.4rem 1rem',
                border: '1px solid',
                borderColor: isActive ? '#1976d2' : '#ccc',
                borderRadius: '20px',
                backgroundColor: isActive ? '#1976d2' : '#fff',
                color: isActive ? '#fff' : '#555',
                fontWeight: isActive ? 600 : 400,
                cursor: 'pointer',
                fontSize: '0.875rem',
                transition: 'all 0.15s ease',
              }}
            >
              {opt.label}
            </button>
          );
        })}
      </div>

      {/* 로딩 상태 */}
      {loading && (
        <div
          role="status"
          aria-live="polite"
          style={{ textAlign: 'center', padding: '3rem', color: '#888' }}
        >
          <p>섹터 데이터를 불러오는 중...</p>
        </div>
      )}

      {/* 오류 상태 */}
      {!loading && error && (
        <div
          role="alert"
          style={{
            padding: '1rem',
            backgroundColor: '#ffebee',
            border: '1px solid #ef9a9a',
            borderRadius: '4px',
            color: '#c62828',
          }}
        >
          <strong>오류:</strong> 섹터 데이터를 불러오는 중 오류가 발생했습니다.
        </div>
      )}

      {/* 랭킹 테이블 */}
      {!loading && !error && (
        <div style={{ marginBottom: '1.5rem' }}>
          <RankingTable
            sectors={sectors}
            selectedSector={selectedSector}
            onSelect={handleRowSelect}
          />
        </div>
      )}

      {/* 섹터 상세 패널 */}
      {selectedSector && !loading && !error && (
        <div style={{ marginBottom: '1.5rem' }}>
          <SectorDetailPanel
            sector={selectedSector}
            onClose={() => setSelectedSector(null)}
          />
        </div>
      )}

      {/* 면책 조항 */}
      <p
        style={{
          marginTop: '2rem',
          padding: '0.75rem 1rem',
          backgroundColor: '#fff8e1',
          borderLeft: '3px solid #ffc107',
          borderRadius: '0 4px 4px 0',
          fontSize: '0.8rem',
          color: '#5f4000',
          lineHeight: 1.6,
        }}
      >
        본 섹터 분석은 투자 권유가 아닌 정보 제공 목적입니다.
      </p>
    </div>
  );
}
