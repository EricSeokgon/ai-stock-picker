# 포트폴리오 벤치마크 비교 서비스 (SPEC-STOCK-034)
# scipy 사용 금지 (NFR-001) — numpy + math 표준 라이브러리만 사용
# 순수 함수로 구성 — DB 없이 테스트 가능 (데이터 주입 방식)
from __future__ import annotations

import asyncio
import logging
import math
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

import numpy as np

from stock_picker.portfolio.schemas import (
    BenchmarkChartData,
    BenchmarkChartPoint,
    BenchmarkComparison,
)
from stock_picker.portfolio.service import get_portfolio_with_holdings

logger = logging.getLogger(__name__)

# ─── 상수 ────────────────────────────────────────────────────────────────────

# @MX:NOTE: [AUTO] BENCHMARK_SYMBOLS: KOSPI=^KS11 / KOSDAQ=^KQ11 / SP500=^GSPC / NASDAQ=^IXIC
# 지수 심볼은 FDR(FinanceDataReader) 조회 시 그대로 사용된다
BENCHMARK_SYMBOLS: dict[str, str] = {
    "KOSPI": "^KS11",
    "KOSDAQ": "^KQ11",
    "SP500": "^GSPC",
    "NASDAQ": "^IXIC",
}

# 거래일 기준 연간 일수
_TRADING_DAYS_PER_YEAR = 252

# 스레드풀 (FDR 동기 호출용)
_executor = ThreadPoolExecutor(max_workers=2)

# 지원하는 기간 코드
_VALID_PERIODS = {"YTD", "1M", "3M", "6M", "1Y"}

# 지원하는 벤치마크
_VALID_BENCHMARKS = set(BENCHMARK_SYMBOLS.keys())


# ─── 기간 시작일 계산 ────────────────────────────────────────────────────────

def _get_period_start(period: str, today: date) -> date:
    """
    기간 코드에 따른 시작일을 반환한다.

    Args:
        period: "YTD", "1M", "3M", "6M", "1Y" 중 하나
        today: 기준일 (보통 오늘)

    Returns:
        해당 기간의 시작일
    """
    period_upper = period.upper()
    if period_upper == "YTD":
        return date(today.year, 1, 1)
    elif period_upper == "1M":
        return today - timedelta(days=30)
    elif period_upper == "3M":
        return today - timedelta(days=90)
    elif period_upper == "6M":
        return today - timedelta(days=180)
    elif period_upper == "1Y":
        return today - timedelta(days=365)
    else:
        # 알 수 없는 기간은 1M으로 폴백
        return today - timedelta(days=30)


# ─── 순수 함수: 베타 산출 ─────────────────────────────────────────────────────

def calculate_beta(
    portfolio_daily_returns: list[float],
    benchmark_daily_returns: list[float],
) -> Optional[float]:
    """
    포트폴리오와 벤치마크 일별 수익률로 베타를 계산한다.

    scipy 금지 (NFR-001) — numpy cov/var만 사용:
        beta = cov(portfolio, benchmark) / var(benchmark)

    Args:
        portfolio_daily_returns: 포트폴리오 일별 수익률 리스트
        benchmark_daily_returns: 벤치마크 일별 수익률 리스트

    Returns:
        베타 값 (float), 다음 경우 None:
        - 데이터 포인트 < 20
        - 벤치마크 분산 == 0
        - 결과가 NaN 또는 Inf
    """
    n = len(portfolio_daily_returns)

    # < 20 데이터 포인트 → None
    if n < 20 or len(benchmark_daily_returns) < 20:
        return None

    try:
        p = np.array(portfolio_daily_returns, dtype=float)
        b = np.array(benchmark_daily_returns, dtype=float)

        # NaN 검사
        if np.any(np.isnan(p)) or np.any(np.isnan(b)):
            return None

        # 분산 == 0 검사 (무변동 벤치마크)
        bench_var = np.var(b, ddof=1)
        if bench_var == 0.0:
            return None

        # scipy 금지 — numpy cov만 사용
        cov_matrix = np.cov(p, b)
        cov_pb = cov_matrix[0, 1]
        beta = cov_pb / bench_var

        # NaN/Inf 검사
        if math.isnan(beta) or math.isinf(beta):
            return None

        return float(beta)

    except Exception as e:
        logger.warning("베타 계산 실패: %s", e)
        return None


# ─── 순수 함수: 벤치마크 비교 ────────────────────────────────────────────────

# @MX:ANCHOR: [AUTO] calculate_benchmark_comparison — 벤치마크 비교 진입점
# @MX:REASON: [AUTO] 순수 함수 — API·서비스·테스트 fan_in >= 3, scipy 금지, DB 없이 테스트 가능
# @MX:NOTE: [AUTO] 단순 알파: 무위험수익률 미반영, 연환산 초과수익 단순 차이 (SPEC-034 §제외)
# @MX:SPEC: SPEC-STOCK-034 REQ-BMK-001~004
def calculate_benchmark_comparison(
    portfolio_history: list[dict[str, Any]],
    benchmark_history: list[dict[str, Any]],
    period: str,
    portfolio_id: int,
    benchmark: str,
) -> BenchmarkComparison:
    """
    포트폴리오와 벤치마크를 기간별로 비교하여 수익률·초과수익·알파·베타를 계산한다.

    Args:
        portfolio_history: [{"date": date, "portfolio_value": float}, ...] 리스트
        benchmark_history: [{"date": date, "close_price": float}, ...] 리스트
        period: "YTD", "1M", "3M", "6M", "1Y" 중 하나
        portfolio_id: 포트폴리오 ID
        benchmark: "KOSPI", "KOSDAQ", "SP500", "NASDAQ" 중 하나

    Returns:
        BenchmarkComparison 스키마 인스턴스
    """
    today = date.today()
    period_start = _get_period_start(period, today)

    # 기간 필터링
    filtered_port = [
        h for h in portfolio_history
        if h["date"] >= period_start
    ]
    filtered_bench = [
        h for h in benchmark_history
        if h["date"] >= period_start
    ]

    # 포트폴리오 수익률 계산
    if len(filtered_port) < 2:
        port_return_pct = 0.0
    else:
        first_val = filtered_port[0]["portfolio_value"]
        last_val = filtered_port[-1]["portfolio_value"]
        port_return_pct = (last_val / first_val - 1) * 100 if first_val != 0 else 0.0

    # 벤치마크 수익률 계산 (데이터 없으면 None)
    bench_return_pct: Optional[float] = None
    excess_return_pct: Optional[float] = None

    if len(filtered_bench) >= 2:
        first_close = filtered_bench[0]["close_price"]
        last_close = filtered_bench[-1]["close_price"]
        if first_close != 0:
            bench_return_pct = (last_close / first_close - 1) * 100
            excess_return_pct = port_return_pct - bench_return_pct

    # 공통 거래일 inner join (날짜 기준)
    port_date_map = {h["date"]: h["portfolio_value"] for h in filtered_port}
    bench_date_map = {h["date"]: h["close_price"] for h in filtered_bench}
    common_dates = sorted(set(port_date_map.keys()) & set(bench_date_map.keys()))

    n_common = len(common_dates)

    # 일별 수익률 계산 (공통 거래일 기준)
    port_daily_returns: list[float] = []
    bench_daily_returns: list[float] = []

    if n_common >= 2:
        port_values = [port_date_map[d] for d in common_dates]
        bench_values = [bench_date_map[d] for d in common_dates]

        for i in range(1, n_common):
            if port_values[i - 1] != 0:
                port_daily_returns.append(port_values[i] / port_values[i - 1] - 1)
            if bench_values[i - 1] != 0:
                bench_daily_returns.append(bench_values[i] / bench_values[i - 1] - 1)

    # 알파 계산 (연환산 초과수익률)
    # 무위험수익률 미반영 — 단순 연환산 차이 (SPEC-034 §제외)
    alpha: Optional[float] = None
    if bench_return_pct is not None and len(common_dates) >= 2:
        n_intervals = len(common_dates) - 1
        if n_intervals > 0:
            # 연환산: (1 + total/100)^(252/n) - 1
            ann_port = (math.pow(1 + port_return_pct / 100, _TRADING_DAYS_PER_YEAR / n_intervals) - 1) * 100
            ann_bench = (math.pow(1 + bench_return_pct / 100, _TRADING_DAYS_PER_YEAR / n_intervals) - 1) * 100
            alpha_val = ann_port - ann_bench
            if not (math.isnan(alpha_val) or math.isinf(alpha_val)):
                alpha = round(alpha_val, 4)

    # 베타 계산
    beta = calculate_beta(port_daily_returns, bench_daily_returns)

    return BenchmarkComparison(
        portfolio_id=portfolio_id,
        benchmark=benchmark,
        period=period.upper(),
        portfolio_return_pct=round(port_return_pct, 4),
        benchmark_return_pct=round(bench_return_pct, 4) if bench_return_pct is not None else None,
        excess_return_pct=round(excess_return_pct, 4) if excess_return_pct is not None else None,
        alpha=alpha,
        beta=round(beta, 6) if beta is not None else None,
        calculated_at=datetime.now(tz=timezone.utc),
    )


# ─── 순수 함수: 재기준화 차트 ────────────────────────────────────────────────

# @MX:ANCHOR: [AUTO] calculate_benchmark_chart — 벤치마크 차트 진입점
# @MX:REASON: [AUTO] router·서비스·테스트 fan_in >= 3, 100 기준 재기준화 로직 경계
# @MX:SPEC: SPEC-STOCK-034 REQ-BMK-010
def calculate_benchmark_chart(
    portfolio_history: list[dict[str, Any]],
    benchmark_history: list[dict[str, Any]],
    period: str,
    portfolio_id: int,
    benchmark: str,
) -> BenchmarkChartData:
    """
    포트폴리오와 벤치마크를 기간 시작 100 기준으로 재기준화한 차트 데이터를 반환한다.

    Args:
        portfolio_history: [{"date": date, "portfolio_value": float}, ...] 리스트
        benchmark_history: [{"date": date, "close_price": float}, ...] 리스트
        period: "YTD", "1M", "3M", "6M", "1Y" 중 하나
        portfolio_id: 포트폴리오 ID
        benchmark: "KOSPI", "KOSDAQ", "SP500", "NASDAQ" 중 하나

    Returns:
        BenchmarkChartData 스키마 인스턴스
    """
    today = date.today()
    period_start = _get_period_start(period, today)

    # 기간 필터링
    filtered_port = sorted(
        [h for h in portfolio_history if h["date"] >= period_start],
        key=lambda x: x["date"],
    )
    filtered_bench = sorted(
        [h for h in benchmark_history if h["date"] >= period_start],
        key=lambda x: x["date"],
    )

    # 포트폴리오 날짜→가치 매핑
    port_date_map = {h["date"]: h["portfolio_value"] for h in filtered_port}
    bench_date_map = {h["date"]: h["close_price"] for h in filtered_bench}

    # 포트폴리오 날짜 기준으로 차트 포인트 생성
    port_dates = sorted(port_date_map.keys())

    if not port_dates:
        return BenchmarkChartData(
            portfolio_id=portfolio_id,
            benchmark=benchmark,
            period=period.upper(),
            chart=[],
        )

    # 재기준화: 첫날 값을 100으로 정규화
    first_port_value = port_date_map[port_dates[0]]
    first_bench_close = bench_date_map.get(port_dates[0])

    chart_points: list[BenchmarkChartPoint] = []
    for d in port_dates:
        port_val = port_date_map[d]
        port_index = (port_val / first_port_value * 100) if first_port_value != 0 else 100.0

        bench_index: Optional[float] = None
        if first_bench_close is not None and first_bench_close != 0:
            bench_close = bench_date_map.get(d)
            if bench_close is not None:
                bench_index = bench_close / first_bench_close * 100

        chart_points.append(BenchmarkChartPoint(
            date=d,
            portfolio_index=round(port_index, 4),
            benchmark_index=round(bench_index, 4) if bench_index is not None else None,
        ))

    return BenchmarkChartData(
        portfolio_id=portfolio_id,
        benchmark=benchmark,
        period=period.upper(),
        chart=chart_points,
    )


# ─── FDR 벤치마크 가격 조회 ─────────────────────────────────────────────────

# @MX:WARN: [AUTO] yfinance/FDR 조회: run_in_executor로 동기 I/O 비동기 래핑 필요
# @MX:REASON: [AUTO] FDR/yfinance가 async를 지원하지 않아 asyncio 이벤트 루프 블로킹 방지
def _fetch_benchmark_sync(symbol: str, start_date: date, end_date: date) -> list[dict[str, Any]]:
    """
    FDR로 벤치마크 지수 가격 시계열을 동기 조회한다 (스레드 풀에서 실행).

    Args:
        symbol: 지수 심볼 (예: ^KS11)
        start_date: 조회 시작일
        end_date: 조회 종료일

    Returns:
        [{"date": date, "close_price": float}, ...] 리스트
        실패 시 빈 리스트 반환 (graceful degradation)
    """
    try:
        import FinanceDataReader as fdr  # noqa: PLC0415

        df = fdr.DataReader(symbol, start=str(start_date), end=str(end_date))
        if df is None or df.empty:
            return []

        result = []
        for idx, row in df.iterrows():
            close_val = row.get("Close") or row.get("close")
            if close_val is None:
                continue
            result.append({"date": idx.date(), "close_price": float(close_val)})
        return result

    except Exception as e:
        logger.warning("FDR 벤치마크 조회 실패 — symbol=%s: %s", symbol, e)
        return []


async def _fetch_benchmark_async(
    symbol: str,
    start_date: date,
    end_date: date,
) -> list[dict[str, Any]]:
    """비동기 컨텍스트에서 FDR 동기 함수를 executor로 호출한다."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _executor,
        _fetch_benchmark_sync,
        symbol,
        start_date,
        end_date,
    )


# ─── 포트폴리오 일별 가치 시계열 ─────────────────────────────────────────────

def _compute_portfolio_daily_history(
    portfolio: Any,
    start_date: date,
    end_date: date,
    usd_krw_rate: float = 1350.0,
) -> list[dict[str, Any]]:
    """
    포트폴리오 보유 종목의 일별 가치 시계열을 계산한다.

    SPEC-030 performance_summary.py의 로직을 재사용하되,
    일별 시계열 전체를 반환한다 (비교·차트 모두 필요).

    Args:
        portfolio: Portfolio ORM 객체 (holdings 포함)
        start_date: 조회 시작일
        end_date: 조회 종료일
        usd_krw_rate: USD/KRW 환율 (해외 종목 KRW 환산용)

    Returns:
        [{"date": date, "portfolio_value": float}, ...] 리스트
        FDR 조회 실패 시 빈 리스트 반환
    """
    try:
        import FinanceDataReader as fdr  # noqa: PLC0415

        holdings = portfolio.holdings
        if not holdings:
            return []

        # 각 종목 가격 시계열 조회 (동기 — 서비스에서 run_in_executor로 호출)
        price_data: dict[str, list[dict]] = {}
        weights: list[float] = []
        tickers: list[str] = []

        for holding in holdings:
            ticker = holding.krx_code
            fx = usd_krw_rate if holding.currency == "USD" else 1.0

            df = fdr.DataReader(ticker, start=str(start_date), end=str(end_date))
            if df is None or df.empty:
                continue

            series = []
            for idx, row in df.iterrows():
                close_val = row.get("Close") or row.get("close")
                if close_val is None:
                    continue
                series.append({"date": str(idx.date()), "close": float(close_val) * fx})

            if series:
                price_data[ticker] = series
                # 비중 = 수량 × 평균매수가 (× 환율)
                weight = float(holding.quantity) * float(holding.avg_buy_price)
                if holding.currency == "USD":
                    weight *= usd_krw_rate
                weights.append(weight)
                tickers.append(ticker)

        if not tickers:
            return []

        # 공통 거래일 inner join
        date_sets = [{row["date"] for row in series} for series in price_data.values()]
        common_date_set = date_sets[0]
        for ds in date_sets[1:]:
            common_date_set = common_date_set & ds

        if not common_date_set:
            return []

        common_dates = sorted(common_date_set)

        # 비중 정규화
        total_weight = sum(weights)
        if total_weight == 0:
            norm_weights = [1.0 / len(weights)] * len(weights)
        else:
            norm_weights = [w / total_weight for w in weights]

        # 첫날 기준 정규화 포트폴리오 가치 계산
        result = []
        base_prices: dict[str, float] = {}
        for ticker in tickers:
            date_to_close = {row["date"]: row["close"] for row in price_data[ticker]}
            base_prices[ticker] = date_to_close[common_dates[0]]

        for d in common_dates:
            day_value = 0.0
            for ticker, weight in zip(tickers, norm_weights):
                date_to_close = {row["date"]: row["close"] for row in price_data[ticker]}
                close = date_to_close.get(d)
                base = base_prices.get(ticker, 0)
                if close is not None and base != 0:
                    day_value += weight * (close / base)

            result.append({"date": date.fromisoformat(d), "portfolio_value": day_value * 10000})

        return result

    except Exception as e:
        logger.warning("포트폴리오 일별 가치 시계열 계산 실패: %s", e)
        return []


# ─── 서비스 오케스트레이션 ────────────────────────────────────────────────────

async def get_benchmark_comparison_service(
    portfolio_id: int,
    benchmark: str,
    period: str,
    user_id: int,
    db: Any,
) -> BenchmarkComparison:
    """
    포트폴리오 벤치마크 비교 서비스.

    소유권 확인 → 가격 조회 → 순수 함수 호출 → 응답 반환.

    Args:
        portfolio_id: 포트폴리오 ID
        benchmark: "KOSPI", "KOSDAQ", "SP500", "NASDAQ"
        period: "YTD", "1M", "3M", "6M", "1Y"
        user_id: 현재 사용자 ID
        db: DB 세션

    Raises:
        HTTPException(404): 포트폴리오를 찾을 수 없거나 소유권 없음

    Returns:
        BenchmarkComparison 스키마
    """
    from fastapi import HTTPException, status  # noqa: PLC0415

    # 소유권 확인
    portfolio = get_portfolio_with_holdings(db, portfolio_id=portfolio_id, user_id=user_id)
    if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="포트폴리오를 찾을 수 없습니다",
        )

    # 벤치마크 심볼 매핑 (미지원 벤치마크 graceful degradation)
    symbol = BENCHMARK_SYMBOLS.get(benchmark)

    # 기간 시작일 계산
    today = date.today()
    period_start = _get_period_start(period, today)

    # 포트폴리오 일별 가치 시계열 조회 (동기 FDR → executor)
    loop = asyncio.get_event_loop()
    try:
        from stock_picker.portfolio.fx_rate import get_usd_krw_rate  # noqa: PLC0415
        usd_krw = await get_usd_krw_rate()
    except Exception:
        usd_krw = 1350.0

    port_history = await loop.run_in_executor(
        _executor,
        _compute_portfolio_daily_history,
        portfolio,
        period_start,
        today,
        usd_krw,
    )

    # 벤치마크 가격 시계열 조회 (graceful degradation)
    bench_history: list[dict[str, Any]] = []
    if symbol:
        bench_history = await _fetch_benchmark_async(symbol, period_start, today)

    return calculate_benchmark_comparison(
        portfolio_history=port_history,
        benchmark_history=bench_history,
        period=period,
        portfolio_id=portfolio_id,
        benchmark=benchmark,
    )


async def get_benchmark_chart_service(
    portfolio_id: int,
    benchmark: str,
    period: str,
    user_id: int,
    db: Any,
) -> BenchmarkChartData:
    """
    포트폴리오 벤치마크 비교 차트 데이터 서비스.

    소유권 확인 → 가격 조회 → 순수 함수 호출 → 응답 반환.

    Args:
        portfolio_id: 포트폴리오 ID
        benchmark: "KOSPI", "KOSDAQ", "SP500", "NASDAQ"
        period: "YTD", "1M", "3M", "6M", "1Y"
        user_id: 현재 사용자 ID
        db: DB 세션

    Raises:
        HTTPException(404): 포트폴리오를 찾을 수 없거나 소유권 없음

    Returns:
        BenchmarkChartData 스키마
    """
    from fastapi import HTTPException, status  # noqa: PLC0415

    # 소유권 확인
    portfolio = get_portfolio_with_holdings(db, portfolio_id=portfolio_id, user_id=user_id)
    if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="포트폴리오를 찾을 수 없습니다",
        )

    # 벤치마크 심볼 매핑
    symbol = BENCHMARK_SYMBOLS.get(benchmark)

    # 기간 시작일 계산
    today = date.today()
    period_start = _get_period_start(period, today)

    # 포트폴리오 일별 가치 시계열 조회
    loop = asyncio.get_event_loop()
    try:
        from stock_picker.portfolio.fx_rate import get_usd_krw_rate  # noqa: PLC0415
        usd_krw = await get_usd_krw_rate()
    except Exception:
        usd_krw = 1350.0

    port_history = await loop.run_in_executor(
        _executor,
        _compute_portfolio_daily_history,
        portfolio,
        period_start,
        today,
        usd_krw,
    )

    # 벤치마크 가격 시계열 조회
    bench_history: list[dict[str, Any]] = []
    if symbol:
        bench_history = await _fetch_benchmark_async(symbol, period_start, today)

    return calculate_benchmark_chart(
        portfolio_history=port_history,
        benchmark_history=bench_history,
        period=period,
        portfolio_id=portfolio_id,
        benchmark=benchmark,
    )
