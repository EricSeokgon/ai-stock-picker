import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// 섹터 분석 페이지 — 섹터 랭킹 테이블과 상세 패널 제공
import { useEffect, useState } from 'react';
import { fetchSectorRanking } from '../api/sectors';
import { SectorDetailPanel } from '../components/SectorDetailPanel';
const SORT_OPTIONS = [
    { label: '트렌드 점수', value: 'score' },
    { label: '감성 점수', value: 'sentiment' },
    { label: '뉴스 볼륨', value: 'volume' },
];
// @MX:NOTE: [AUTO] 섹터 랭킹 정렬 기준 — score/sentiment/volume 세 가지 지원
function formatScore(value) {
    return value.toFixed(3);
}
function RankingTable({ sectors, selectedSector, onSelect }) {
    if (sectors.length === 0) {
        return (_jsx("p", { style: {
                color: '#888',
                fontSize: '0.9rem',
                textAlign: 'center',
                padding: '2.5rem 1rem',
                border: '1px solid #e0e0e0',
                borderRadius: '8px',
                backgroundColor: '#fafafa',
            }, children: "\uC139\uD130 \uB370\uC774\uD130\uB97C \uC900\uBE44 \uC911\uC785\uB2C8\uB2E4. \uC2DC\uC2A4\uD15C\uC774 \uB370\uC774\uD130\uB97C \uC218\uC9D1\uD558\uBA74 \uC790\uB3D9\uC73C\uB85C \uD45C\uC2DC\uB429\uB2C8\uB2E4." }));
    }
    return (_jsx("div", { style: { overflowX: 'auto' }, children: _jsxs("table", { style: { width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }, "aria-label": "\uC139\uD130 \uB7AD\uD0B9 \uD14C\uC774\uBE14", children: [_jsx("thead", { children: _jsxs("tr", { style: { backgroundColor: '#f5f5f5' }, children: [_jsx("th", { style: thStyle, children: "\uC139\uD130\uBA85" }), _jsx("th", { style: thStyle, children: "\uD2B8\uB80C\uB4DC \uC810\uC218" }), _jsx("th", { style: thStyle, children: "\uAC10\uC131 \uC810\uC218" }), _jsx("th", { style: thStyle, children: "\uB274\uC2A4 \uBCFC\uB968" })] }) }), _jsx("tbody", { children: sectors.map((item) => {
                        const isSelected = selectedSector === item.sector;
                        return (_jsxs("tr", { onClick: () => onSelect(item.sector), style: {
                                cursor: 'pointer',
                                backgroundColor: isSelected ? '#e3f2fd' : '#fff',
                                borderBottom: '1px solid #e0e0e0',
                                transition: 'background-color 0.15s',
                            }, "aria-selected": isSelected, role: "row", children: [_jsx("td", { style: { ...tdStyle, fontWeight: 600, color: '#1976d2' }, children: item.sector }), _jsx("td", { style: tdStyle, children: formatScore(item.trend_score) }), _jsx("td", { style: tdStyle, children: formatScore(item.avg_sentiment) }), _jsx("td", { style: tdStyle, children: item.news_volume })] }, item.sector));
                    }) })] }) }));
}
const thStyle = {
    padding: '0.6rem 0.875rem',
    textAlign: 'left',
    fontWeight: 600,
    color: '#555',
    borderBottom: '2px solid #e0e0e0',
};
const tdStyle = {
    padding: '0.6rem 0.875rem',
    color: '#212121',
};
export default function Sectors() {
    const [sort, setSort] = useState('score');
    const [sectors, setSectors] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedSector, setSelectedSector] = useState(null);
    useEffect(() => {
        let cancelled = false;
        async function load() {
            setLoading(true);
            setError(null);
            try {
                const result = await fetchSectorRanking(sort, 10);
                if (!cancelled)
                    setSectors(result.sectors);
            }
            catch (err) {
                if (!cancelled)
                    setError(err instanceof Error ? err.message : '섹터 데이터를 불러오는 중 오류가 발생했습니다.');
            }
            finally {
                if (!cancelled)
                    setLoading(false);
            }
        }
        void load();
        return () => { cancelled = true; };
    }, [sort]);
    function handleSortChange(newSort) {
        setSort(newSort);
        setSelectedSector(null);
    }
    function handleRowSelect(sector) {
        setSelectedSector((prev) => (prev === sector ? null : sector));
    }
    return (_jsxs("div", { children: [_jsx("h1", { style: { fontSize: '1.5rem', fontWeight: 700, marginBottom: '1.25rem', color: '#212121' }, children: "\uC139\uD130 \uBD84\uC11D" }), _jsx("div", { role: "group", "aria-label": "\uC815\uB82C \uAE30\uC900 \uC120\uD0DD", style: { display: 'flex', gap: '0.5rem', marginBottom: '1.25rem', flexWrap: 'wrap' }, children: SORT_OPTIONS.map((opt) => {
                    const isActive = sort === opt.value;
                    return (_jsx("button", { onClick: () => handleSortChange(opt.value), "aria-pressed": isActive, style: {
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
                        }, children: opt.label }, opt.value));
                }) }), loading && (_jsx("div", { role: "status", "aria-live": "polite", style: { textAlign: 'center', padding: '3rem', color: '#888' }, children: _jsx("p", { children: "\uC139\uD130 \uB370\uC774\uD130\uB97C \uBD88\uB7EC\uC624\uB294 \uC911..." }) })), !loading && error && (_jsxs("div", { role: "alert", style: {
                    padding: '1rem',
                    backgroundColor: '#ffebee',
                    border: '1px solid #ef9a9a',
                    borderRadius: '4px',
                    color: '#c62828',
                }, children: [_jsx("strong", { children: "\uC624\uB958:" }), " \uC139\uD130 \uB370\uC774\uD130\uB97C \uBD88\uB7EC\uC624\uB294 \uC911 \uC624\uB958\uAC00 \uBC1C\uC0DD\uD588\uC2B5\uB2C8\uB2E4."] })), !loading && !error && (_jsx("div", { style: { marginBottom: '1.5rem' }, children: _jsx(RankingTable, { sectors: sectors, selectedSector: selectedSector, onSelect: handleRowSelect }) })), selectedSector && !loading && !error && (_jsx("div", { style: { marginBottom: '1.5rem' }, children: _jsx(SectorDetailPanel, { sector: selectedSector, onClose: () => setSelectedSector(null) }) })), _jsx("p", { style: {
                    marginTop: '2rem',
                    padding: '0.75rem 1rem',
                    backgroundColor: '#fff8e1',
                    borderLeft: '3px solid #ffc107',
                    borderRadius: '0 4px 4px 0',
                    fontSize: '0.8rem',
                    color: '#5f4000',
                    lineHeight: 1.6,
                }, children: "\uBCF8 \uC139\uD130 \uBD84\uC11D\uC740 \uD22C\uC790 \uAD8C\uC720\uAC00 \uC544\uB2CC \uC815\uBCF4 \uC81C\uACF5 \uBAA9\uC801\uC785\uB2C8\uB2E4." })] }));
}
