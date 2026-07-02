// 배당 수익률 요약 패널 컴포넌트 (SPEC-STOCK-033)
// @MX:NOTE: [AUTO] DividendSummaryPanel — 포트폴리오 배당 수익률 요약 표시
import { useState, useEffect } from 'react';
import { apiGetDividendSummary } from '../api/portfolio.js';

/**
 * 포트폴리오 배당 수익률 요약 패널
 * @param {Object} props
 * @param {string} props.token - Bearer 인증 토큰
 * @param {number} props.portfolioId - 포트폴리오 ID
 */
export default function DividendSummaryPanel({ token, portfolioId }) {
    const [summary, setSummary] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!token || !portfolioId) return;
        setLoading(true);
        apiGetDividendSummary(token, portfolioId)
            .then(setSummary)
            .catch(err => setError(err.message))
            .finally(() => setLoading(false));
    }, [token, portfolioId]);

    if (loading) return <div>배당 수익률 분석 중...</div>;
    if (error) return <div>오류: {error}</div>;
    if (!summary) return null;

    return (
        <div className="dividend-summary-panel">
            <h3>배당 수익률 요약</h3>
            <div className="summary-stats">
                <div className="stat">
                    <span className="label">포트폴리오 가중 평균 배당수익률</span>
                    <span className="value">{summary.portfolio_dividend_yield_pct.toFixed(2)}%</span>
                </div>
                <div className="stat">
                    <span className="label">연간 예상 배당 수익</span>
                    <span className="value">{summary.total_annual_dividend.toLocaleString()}원</span>
                </div>
                <div className="stat">
                    <span className="label">포트폴리오 총 평가액</span>
                    <span className="value">{summary.total_portfolio_value.toLocaleString()}원</span>
                </div>
            </div>

            <h4>보유 종목별 배당 내역</h4>
            <table className="holdings-table">
                <thead>
                    <tr>
                        <th>종목코드</th>
                        <th>종목명</th>
                        <th>보유주수</th>
                        <th>주당배당금</th>
                        <th>배당수익률</th>
                        <th>연간예상배당</th>
                    </tr>
                </thead>
                <tbody>
                    {summary.holdings.map(h => (
                        <tr key={h.krx_code}>
                            <td>{h.krx_code}</td>
                            <td>{h.stock_name}</td>
                            <td>{h.shares.toLocaleString()}</td>
                            <td>{h.annual_dps.toLocaleString()}원</td>
                            <td>{h.dividend_yield_pct.toFixed(2)}%</td>
                            <td>{h.estimated_annual_dividend.toLocaleString()}원</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
