// DRIP 복리 시뮬레이터 컴포넌트 (SPEC-STOCK-033)
// @MX:NOTE: [AUTO] DRIPSimulator — 배당 재투자 복리 효과 시뮬레이션 UI
import { useState, useEffect } from 'react';
import { apiGetDRIPProjection } from '../api/portfolio.js';

/**
 * DRIP (배당 재투자 계획) 복리 시뮬레이터
 * @param {Object} props
 * @param {string} props.token - Bearer 인증 토큰
 * @param {number} props.portfolioId - 포트폴리오 ID
 */
export default function DRIPSimulator({ token, portfolioId }) {
    const [projection, setProjection] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    // 시뮬레이션 파라미터
    const [years, setYears] = useState(10);
    const [reinvestRate, setReinvestRate] = useState(1.0);

    const runSimulation = () => {
        if (!token || !portfolioId) return;
        setLoading(true);
        setError(null);
        apiGetDRIPProjection(token, portfolioId, years, reinvestRate)
            .then(setProjection)
            .catch(err => setError(err.message))
            .finally(() => setLoading(false));
    };

    // 최초 마운트 시 자동 실행
    useEffect(() => {
        if (token && portfolioId) runSimulation();
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [token, portfolioId]);

    return (
        <div className="drip-simulator">
            <h3>DRIP 복리 시뮬레이터</h3>
            <p className="drip-description">배당금을 재투자했을 때의 복리 효과를 시뮬레이션합니다.</p>

            <div className="drip-controls">
                <label>
                    시뮬레이션 기간:
                    <select
                        value={years}
                        onChange={e => setYears(Number(e.target.value))}
                    >
                        {[5, 10, 15, 20, 30].map(y => (
                            <option key={y} value={y}>{y}년</option>
                        ))}
                    </select>
                </label>

                <label>
                    배당 재투자 비율:
                    <select
                        value={reinvestRate}
                        onChange={e => setReinvestRate(Number(e.target.value))}
                    >
                        <option value={1.0}>100% (전액 재투자)</option>
                        <option value={0.75}>75%</option>
                        <option value={0.5}>50%</option>
                        <option value={0.25}>25%</option>
                        <option value={0.0}>0% (재투자 없음)</option>
                    </select>
                </label>

                <button onClick={runSimulation} disabled={loading}>
                    {loading ? '시뮬레이션 중...' : '시뮬레이션 실행'}
                </button>
            </div>

            {error && <div className="error">오류: {error}</div>}

            {projection && (
                <div className="drip-results">
                    <div className="drip-meta">
                        <span>초기 포트폴리오 가치: {projection.initial_value.toLocaleString()}원</span>
                        <span>배당 수익률: {projection.dividend_yield_pct.toFixed(2)}%</span>
                        <span>재투자 비율: {(projection.reinvest_rate * 100).toFixed(0)}%</span>
                    </div>

                    <table className="drip-table">
                        <thead>
                            <tr>
                                <th>연도</th>
                                <th>포트폴리오 가치</th>
                                <th>연간 배당금</th>
                                <th>누적 수익률</th>
                            </tr>
                        </thead>
                        <tbody>
                            {projection.years.map(yr => (
                                <tr key={yr.year}>
                                    <td>{yr.year === 0 ? '현재' : `+${yr.year}년`}</td>
                                    <td>{yr.portfolio_value.toLocaleString('ko-KR', { maximumFractionDigits: 0 })}원</td>
                                    <td>{yr.annual_dividend.toLocaleString('ko-KR', { maximumFractionDigits: 0 })}원</td>
                                    <td>{yr.cumulative_return_pct.toFixed(2)}%</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>

                    <p className="drip-disclaimer">{projection.disclaimer}</p>
                </div>
            )}
        </div>
    );
}
