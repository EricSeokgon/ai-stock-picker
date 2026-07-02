// 기간별 성과 요약 패널 컴포넌트 (SPEC-STOCK-030)
// YTD/1M/3M/6M/1Y 수익률 및 최대 낙폭을 카드 형태로 표시
import { useEffect, useState } from 'react';
import { apiGetPerformanceSummary } from '../api/portfolio';

// @MX:ANCHOR: [AUTO] 성과 요약 패널 — Portfolio 페이지의 핵심 표시 컴포넌트
// @MX:REASON: [AUTO] Portfolio.js, Portfolio.tsx, 테스트에서 3곳 이상 참조
// @MX:SPEC: SPEC-STOCK-030 수용 기준 AC-009

/**
 * 기간별 성과 요약 패널
 * @param {Object} props
 * @param {string} props.token - Bearer 인증 토큰
 * @param {number} props.portfolioId - 포트폴리오 ID
 */
export default function PerformanceSummaryPanel({ token, portfolioId }) {
    const [summary, setSummary] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const loadSummary = async (refresh = false) => {
        try {
            setLoading(true);
            setError(null);
            const data = await apiGetPerformanceSummary(token, portfolioId, refresh);
            setSummary(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (token && portfolioId) {
            loadSummary();
        }
    }, [token, portfolioId]);

    if (loading) {
        return <div style={styles.container}>성과 데이터를 불러오는 중...</div>;
    }

    if (error) {
        return (
            <div style={styles.container}>
                <p style={styles.errorText}>성과 조회 실패: {error}</p>
            </div>
        );
    }

    if (!summary) return null;

    return (
        <div style={styles.container}>
            <div style={styles.header}>
                <h3 style={styles.title}>기간별 성과 요약</h3>
                <button
                    style={styles.refreshBtn}
                    onClick={() => loadSummary(true)}
                    title="새로 계산"
                >
                    새로 계산
                </button>
            </div>

            <div style={styles.grid}>
                {summary.periods.map((period) => (
                    <PeriodCard key={period.period} period={period} />
                ))}
            </div>

            <p style={styles.disclaimer}>{summary.disclaimer}</p>
            <p style={styles.calculatedAt}>
                기준: {new Date(summary.calculated_at).toLocaleString('ko-KR')}
            </p>
        </div>
    );
}

/**
 * 단일 기간 성과 카드
 * @param {Object} props
 * @param {Object} props.period - PeriodPerformance 데이터
 */
function PeriodCard({ period }) {
    const returnColor = period.total_return_pct === null
        ? '#888'
        : period.total_return_pct >= 0 ? '#2e7d32' : '#c62828';

    return (
        <div style={styles.card}>
            <div style={styles.cardLabel}>{period.display_label}</div>
            {period.has_data ? (
                <>
                    <div style={{ ...styles.returnValue, color: returnColor }}>
                        {period.total_return_pct >= 0 ? '+' : ''}
                        {period.total_return_pct?.toFixed(2)}%
                    </div>
                    <div style={styles.metaRow}>
                        <span style={styles.metaLabel}>연환산</span>
                        <span style={{ color: returnColor }}>
                            {period.annualized_return_pct >= 0 ? '+' : ''}
                            {period.annualized_return_pct?.toFixed(2)}%
                        </span>
                    </div>
                    <div style={styles.metaRow}>
                        <span style={styles.metaLabel}>MDD</span>
                        <span style={{ color: '#c62828' }}>
                            {period.mdd_pct?.toFixed(2)}%
                        </span>
                    </div>
                    <div style={styles.tradingDays}>
                        {period.trading_days}거래일
                    </div>
                </>
            ) : (
                <div style={styles.noData}>데이터 없음</div>
            )}
        </div>
    );
}

// 인라인 스타일 (SPEC-STOCK-030 AC-009: 시각적 명확성 요구사항)
const styles = {
    container: {
        padding: '16px',
        backgroundColor: '#fff',
        borderRadius: '8px',
        boxShadow: '0 1px 3px rgba(0,0,0,0.12)',
        marginBottom: '16px',
    },
    header: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '16px',
    },
    title: {
        margin: 0,
        fontSize: '16px',
        fontWeight: 600,
        color: '#1a1a1a',
    },
    refreshBtn: {
        padding: '4px 12px',
        fontSize: '12px',
        border: '1px solid #ccc',
        borderRadius: '4px',
        cursor: 'pointer',
        backgroundColor: '#f5f5f5',
    },
    grid: {
        display: 'grid',
        gridTemplateColumns: 'repeat(5, 1fr)',
        gap: '8px',
    },
    card: {
        padding: '12px',
        backgroundColor: '#f9f9f9',
        borderRadius: '6px',
        textAlign: 'center',
    },
    cardLabel: {
        fontSize: '12px',
        fontWeight: 600,
        color: '#555',
        marginBottom: '8px',
    },
    returnValue: {
        fontSize: '20px',
        fontWeight: 700,
        marginBottom: '6px',
    },
    metaRow: {
        display: 'flex',
        justifyContent: 'space-between',
        fontSize: '11px',
        marginBottom: '2px',
    },
    metaLabel: {
        color: '#888',
    },
    tradingDays: {
        marginTop: '6px',
        fontSize: '10px',
        color: '#aaa',
    },
    noData: {
        fontSize: '13px',
        color: '#aaa',
        padding: '16px 0',
    },
    errorText: {
        color: '#c62828',
        fontSize: '14px',
    },
    disclaimer: {
        marginTop: '12px',
        fontSize: '10px',
        color: '#888',
        lineHeight: 1.4,
    },
    calculatedAt: {
        fontSize: '10px',
        color: '#aaa',
        marginTop: '4px',
    },
};
