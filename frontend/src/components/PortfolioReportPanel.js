// 포트폴리오 성과 리포트 패널 컴포넌트 (SPEC-STOCK-035 REQ-RPT-001~004)
// JSON 요약 표시 + CSV 다운로드 + 월별 스냅샷 저장 기능 제공
import React, { useState } from 'react';
import {
    apiGetPortfolioReport,
    apiGetPortfolioReportSummary,
    apiCreateMonthlySnapshot,
    apiListMonthlySnapshots,
} from '../api/portfolio.js';

/**
 * 포트폴리오 성과 리포트 패널.
 *
 * 제공 기능:
 * - JSON 리포트 요약 (보유 종목 손익 테이블)
 * - CSV 리포트 다운로드
 * - 월별 스냅샷 저장 및 이력 조회
 *
 * @param {object} props
 * @param {string} props.token    - Bearer 인증 토큰
 * @param {number} props.portfolioId - 포트폴리오 ID
 */
export default function PortfolioReportPanel({ token, portfolioId }) {
    const [period, setPeriod] = useState('YTD');
    const [summary, setSummary] = useState(null);
    const [snapshots, setSnapshots] = useState([]);
    const [loading, setLoading] = useState(false);
    const [snapshotLoading, setSnapshotLoading] = useState(false);
    const [error, setError] = useState(null);

    // 리포트 JSON 요약 조회
    const handleLoadSummary = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await apiGetPortfolioReportSummary(token, portfolioId, period);
            setSummary(data);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    };

    // CSV 다운로드
    const handleDownloadCsv = async () => {
        setError(null);
        try {
            const blob = await apiGetPortfolioReport(token, portfolioId, 'csv', period);
            // 브라우저 다운로드 트리거
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `portfolio_${portfolioId}_report.csv`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (e) {
            setError(`CSV 다운로드 실패: ${e.message}`);
        }
    };

    // 현재 시점 스냅샷 저장
    const handleSaveSnapshot = async () => {
        setSnapshotLoading(true);
        setError(null);
        try {
            await apiCreateMonthlySnapshot(token, portfolioId);
            // 저장 후 목록 새로고침
            const list = await apiListMonthlySnapshots(token, portfolioId);
            setSnapshots(list);
        } catch (e) {
            setError(`스냅샷 저장 실패: ${e.message}`);
        } finally {
            setSnapshotLoading(false);
        }
    };

    // 스냅샷 이력 조회
    const handleLoadSnapshots = async () => {
        setSnapshotLoading(true);
        setError(null);
        try {
            const list = await apiListMonthlySnapshots(token, portfolioId);
            setSnapshots(list);
        } catch (e) {
            setError(`스냅샷 목록 조회 실패: ${e.message}`);
        } finally {
            setSnapshotLoading(false);
        }
    };

    return (
        <div className="portfolio-report-panel">
            <h3>포트폴리오 성과 리포트</h3>

            {/* 기간 선택 */}
            <div className="report-controls">
                <label htmlFor="period-select">기간: </label>
                <select
                    id="period-select"
                    value={period}
                    onChange={(e) => setPeriod(e.target.value)}
                >
                    <option value="YTD">올해 (YTD)</option>
                    <option value="1M">최근 1개월</option>
                    <option value="3M">최근 3개월</option>
                    <option value="6M">최근 6개월</option>
                    <option value="1Y">최근 1년</option>
                </select>
                <button onClick={handleLoadSummary} disabled={loading}>
                    {loading ? '조회 중...' : '리포트 조회'}
                </button>
                <button onClick={handleDownloadCsv} disabled={loading}>
                    CSV 다운로드
                </button>
            </div>

            {/* 에러 메시지 */}
            {error && <p className="error-message">{error}</p>}

            {/* 리포트 요약 테이블 */}
            {summary && (
                <div className="report-summary">
                    <p>
                        생성 시각: {new Date(summary.generated_at).toLocaleString('ko-KR')} |
                        기간: {summary.period} |
                        총 평가액: {summary.total_value_krw.toLocaleString()}원 |
                        기간 수익률: {summary.total_return_pct?.toFixed(2)}%
                        {summary.mdd_pct != null && ` | MDD: ${summary.mdd_pct.toFixed(2)}%`}
                    </p>
                    <table className="holding-report-table">
                        <thead>
                            <tr>
                                <th>종목코드</th>
                                <th>종목명</th>
                                <th>보유수량</th>
                                <th>평균단가</th>
                                <th>현재가</th>
                                <th>손익(KRW)</th>
                                <th>수익률(%)</th>
                                <th>비중(%)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {summary.holdings.map((row) => (
                                <tr key={row.ticker}>
                                    <td>{row.ticker}</td>
                                    <td>{row.name}</td>
                                    <td>{row.quantity.toLocaleString()}</td>
                                    <td>{row.avg_cost.toLocaleString()}</td>
                                    <td>{row.current_price.toLocaleString()}</td>
                                    <td style={{ color: row.pnl_amount >= 0 ? 'blue' : 'red' }}>
                                        {row.pnl_amount.toLocaleString()}
                                    </td>
                                    <td style={{ color: row.pnl_pct >= 0 ? 'blue' : 'red' }}>
                                        {row.pnl_pct.toFixed(2)}%
                                    </td>
                                    <td>{row.weight_pct.toFixed(2)}%</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {/* 월별 스냅샷 */}
            <div className="snapshot-section">
                <h4>월별 스냅샷</h4>
                <button onClick={handleSaveSnapshot} disabled={snapshotLoading}>
                    {snapshotLoading ? '저장 중...' : '이번 달 스냅샷 저장'}
                </button>
                <button onClick={handleLoadSnapshots} disabled={snapshotLoading}>
                    스냅샷 이력 보기
                </button>
                {snapshots.length > 0 && (
                    <table className="snapshot-table">
                        <thead>
                            <tr>
                                <th>월</th>
                                <th>총 평가액(KRW)</th>
                                <th>수익률(%)</th>
                                <th>보유 종목 수</th>
                            </tr>
                        </thead>
                        <tbody>
                            {snapshots.map((s) => (
                                <tr key={s.id}>
                                    <td>{s.month}</td>
                                    <td>{s.total_value_krw.toLocaleString()}</td>
                                    <td>
                                        {s.total_return_pct != null
                                            ? `${s.total_return_pct.toFixed(2)}%`
                                            : '-'}
                                    </td>
                                    <td>{s.holding_count}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
}
