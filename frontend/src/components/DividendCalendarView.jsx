// 배당 캘린더 뷰 컴포넌트 (SPEC-STOCK-033)
// @MX:NOTE: [AUTO] DividendCalendarView — 월별 배당 일정 시각화
import { useState, useEffect } from 'react';
import { apiGetDividendCalendar } from '../api/portfolio.js';

const MONTH_NAMES = [
    '', '1월', '2월', '3월', '4월', '5월', '6월',
    '7월', '8월', '9월', '10월', '11월', '12월',
];

/**
 * 포트폴리오 배당 캘린더 뷰
 * @param {Object} props
 * @param {string} props.token - Bearer 인증 토큰
 * @param {number} props.portfolioId - 포트폴리오 ID
 * @param {number} [props.year] - 조회 연도 (기본값: 현재 연도)
 */
export default function DividendCalendarView({ token, portfolioId, year = null }) {
    const [calendar, setCalendar] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const currentYear = year ?? new Date().getFullYear();

    useEffect(() => {
        if (!token || !portfolioId) return;
        setLoading(true);
        apiGetDividendCalendar(token, portfolioId, currentYear)
            .then(setCalendar)
            .catch(err => setError(err.message))
            .finally(() => setLoading(false));
    }, [token, portfolioId, currentYear]);

    if (loading) return <div>배당 캘린더 불러오는 중...</div>;
    if (error) return <div>오류: {error}</div>;
    if (!calendar) return null;

    const sortedMonths = Object.keys(calendar.months)
        .map(Number)
        .sort((a, b) => a - b);

    if (sortedMonths.length === 0) {
        return (
            <div className="dividend-calendar-panel">
                <h3>{currentYear}년 배당 캘린더</h3>
                <p>해당 연도에 배당 예정 종목이 없습니다.</p>
            </div>
        );
    }

    return (
        <div className="dividend-calendar-panel">
            <h3>{currentYear}년 배당 캘린더</h3>
            {sortedMonths.map(month => (
                <div key={month} className="calendar-month">
                    <h4>{MONTH_NAMES[month]}</h4>
                    <table className="calendar-events-table">
                        <thead>
                            <tr>
                                <th>종목코드</th>
                                <th>종목명</th>
                                <th>배당기준일</th>
                                <th>지급일</th>
                                <th>주당배당금</th>
                                <th>예상수령액</th>
                            </tr>
                        </thead>
                        <tbody>
                            {calendar.months[month].map((evt, idx) => (
                                <tr key={`${evt.krx_code}-${idx}`}>
                                    <td>{evt.krx_code}</td>
                                    <td>{evt.stock_name}</td>
                                    <td>{evt.ex_dividend_date}</td>
                                    <td>{evt.payment_date ?? '-'}</td>
                                    <td>{evt.dps.toLocaleString()}원</td>
                                    <td>{evt.estimated_total.toLocaleString()}원</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            ))}
        </div>
    );
}
