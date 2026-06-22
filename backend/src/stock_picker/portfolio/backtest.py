# 포트폴리오 백테스팅 서비스 (SPEC-STOCK-029)
# buy-and-hold 수익률 시뮬레이션: FDR 가격 시계열 → MDD/Sharpe/총수익률 산출
# 기존 backtest/metrics.py 재사용, scipy 금지(REQ-PBT-NFR-001)
import asyncio
import logging
from datetime import date

import FinanceDataReader as fdr  # noqa: N813
from fastapi import HTTPException, status

from stock_picker.backtest.metrics import (
    calculate_max_drawdown,
    calculate_sharpe_ratio,
    calculate_total_return,
)
from stock_picker.portfolio.fx_rate import get_usd_krw_rate
from stock_picker.portfolio.schemas import BacktestResult, DailyReturn
from stock_picker.portfolio.service import get_portfolio_with_holdings

logger = logging.getLogger(__name__)

# 면책 문구 (AC-14, REQ-PBT-NFR-003)
DISCLAIMER = (
    "본 백테스팅 결과는 과거 데이터 기반 시뮬레이션으로, 미래 수익을 보장하지 않습니다. "
    "투자 권유가 아니며 정보 제공 목적으로만 활용하시기 바랍니다."
)


def _normalize_weights(weights: list[float]) -> list[float]:
    """비중 목록을 합이 1.0이 되도록 정규화한다 (REQ-PBT-023).

    Args:
        weights: 비중 목록 (정수 또는 소수)

    Returns:
        정규화된 비중 목록 (합 = 1.0)
    """
    total = sum(weights)
    if total == 0:
        n = len(weights)
        return [1.0 / n] * n
    return [w / total for w in weights]


def _align_close_series(
    price_data: dict[str, list[dict]],
) -> tuple[list[str], dict[str, list[float]]]:
    """종가 시계열을 공통 거래일 기준으로 내부 조인 정렬한다 (REQ-PBT-012).

    Args:
        price_data: 종목코드 → [{date, close}, ...] 딕셔너리

    Returns:
        (공통날짜 목록, 종목코드 → 종가목록 딕셔너리)
    """
    if not price_data:
        return [], {}

    # 종목별 {date: close} 딕셔너리 생성
    date_close: dict[str, dict[str, float]] = {
        ticker: {row["date"]: float(row["close"]) for row in rows}
        for ticker, rows in price_data.items()
    }

    # 공통 거래일 계산 (inner join)
    date_sets = [set(dc.keys()) for dc in date_close.values()]
    common_dates = sorted(date_sets[0].intersection(*date_sets[1:]))

    closes: dict[str, list[float]] = {
        ticker: [date_close[ticker][d] for d in common_dates]
        for ticker in price_data
    }
    return common_dates, closes


def _daily_portfolio_values(
    aligned_closes: dict[str, list[float]],
    weights: list[float],
    tickers: list[str],
) -> list[float]:
    """정렬된 종가에 비중을 적용해 일별 포트폴리오 가치를 계산한다 (1.0 정규화).

    Args:
        aligned_closes: 종목코드 → 종가목록 (공통 거래일 기준)
        weights: 정규화된 비중 목록 (tickers 순서 일치)
        tickers: 종목코드 목록

    Returns:
        일별 포트폴리오 가치 목록 (첫날=1.0 기준)
    """
    if not tickers:
        return []

    n_days = len(aligned_closes[tickers[0]])
    if n_days == 0:
        return []

    # 각 종목의 초기 종가 (첫날 기준 정규화)
    initial_closes = {ticker: aligned_closes[ticker][0] for ticker in tickers}

    values: list[float] = []
    for day_idx in range(n_days):
        # 비중 가중 포트폴리오 가치 = Σ(weight_i × close_i / initial_close_i)
        pf_value = sum(
            weights[i] * (aligned_closes[ticker][day_idx] / initial_closes[ticker])
            for i, ticker in enumerate(tickers)
        )
        values.append(pf_value)

    return values


def _compute_returns(
    values: list[float],
) -> tuple[list[float], list[float]]:
    """포트폴리오 가치 시계열에서 일별·누적 수익률을 계산한다.

    Args:
        values: 일별 포트폴리오 가치 (1.0 기준 정규화)

    Returns:
        (daily_returns, cumulative_returns)
        - daily_returns[0] = 0.0 (첫날 기준점)
        - cumulative_returns[i] = values[i] / values[0] - 1
    """
    if not values:
        return [], []

    if len(values) == 1:
        return [0.0], [0.0]

    initial = values[0]
    daily: list[float] = [0.0]
    cumulative: list[float] = [0.0]

    for i in range(1, len(values)):
        # 일별 수익률: (현재값 - 전일값) / 전일값
        dr = (values[i] - values[i - 1]) / values[i - 1] if values[i - 1] != 0 else 0.0
        daily.append(dr)
        # 누적 수익률: 최초값 대비 변화율
        cum = (values[i] / initial - 1.0) if initial != 0 else 0.0
        cumulative.append(cum)

    return daily, cumulative


# @MX:WARN: [AUTO] 동기 FDR 호출 — run_in_executor에서만 호출할 것
# @MX:REASON: asyncio 이벤트 루프 블로킹 방지 (REQ-PBT-011); 직접 async 컨텍스트에서 호출 금지
def _fetch_price_series_sync(
    ticker: str,
    start_date: date,
    end_date: date,
) -> list[dict]:
    """FDR로 종목 종가 시계열 동기 조회 (스레드 풀에서 실행).

    Args:
        ticker: 종목 코드 (KRX 6자리 또는 NYSE/NASDAQ 심볼)
        start_date: 조회 시작일
        end_date: 조회 종료일

    Returns:
        [{date: "YYYY-MM-DD", close: float}, ...] 목록
        빈 데이터·NaN·예외 발생 시 [] 반환
    """
    try:
        df = fdr.DataReader(ticker, start_date, end_date)
    except Exception as exc:
        logger.warning("FDR 조회 실패 ticker=%s: %s", ticker, exc)
        return []

    if df is None or df.empty:
        return []

    # Close 컬럼 찾기 (대소문자 허용)
    close_col = None
    for col in df.columns:
        if col.lower() == "close":
            close_col = col
            break

    if close_col is None:
        logger.warning("ticker=%s: Close 컬럼 없음, columns=%s", ticker, list(df.columns))
        return []

    result = []
    for idx, row in df.iterrows():
        close_val = row[close_col]
        # NaN 제외
        if close_val != close_val:  # NaN 검사 (math.isnan 대신 self-comparison)
            continue
        try:
            close_f = float(close_val)
        except (TypeError, ValueError):
            continue
        result.append({"date": str(idx.date()), "close": close_f})

    return result


# @MX:ANCHOR: [AUTO] 포트폴리오 백테스팅 메인 진입점
# @MX:REASON: router, 단위 테스트, 통합 테스트에서 fan_in >= 3
# @MX:NOTE: [AUTO] buy-and-hold 포트폴리오 백테스트: FDR 가격 시계열 → 가중 수익률 → MDD/Sharpe
async def run_portfolio_backtest(
    portfolio_id: int,
    user_id: int,
    db: object,
    redis: object,
    start_date: date,
    end_date: date,
) -> BacktestResult:
    """포트폴리오 백테스팅 실행 — buy-and-hold 수익률 시뮬레이션.

    Args:
        portfolio_id: 백테스팅할 포트폴리오 ID
        user_id: 소유자 사용자 ID (소유권 확인)
        db: SQLAlchemy 세션
        redis: redis.asyncio 클라이언트
        start_date: 백테스팅 시작일
        end_date: 백테스팅 종료일

    Returns:
        BacktestResult: 일별 결과·MDD·샤프·총수익률 포함

    Raises:
        HTTPException 404: 포트폴리오 없거나 타사용자 소유
        HTTPException 400: 보유 종목 없음
        HTTPException 422: 유효 종목 없음 (전 종목 FDR 실패)
    """
    # 1. 포트폴리오 + 보유 종목 조회 (소유권 확인)
    portfolio = get_portfolio_with_holdings(db, portfolio_id, user_id)
    if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="포트폴리오를 찾을 수 없습니다",
        )

    holdings = portfolio.holdings
    if not holdings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="포트폴리오에 보유 종목이 없습니다 (REQ-PBT-021)",
        )

    # 2. USD 종목 존재 시 환율 조회
    has_usd = any(getattr(h, "currency", "KRW") == "USD" for h in holdings)
    usd_krw_rate = 1.0
    if has_usd:
        usd_krw_rate = await get_usd_krw_rate(redis)

    # 3. 병렬 FDR 조회 (run_in_executor로 블로킹 격리)
    loop = asyncio.get_event_loop()
    price_tasks = [
        loop.run_in_executor(None, _fetch_price_series_sync, h.krx_code, start_date, end_date)
        for h in holdings
    ]
    price_results = await asyncio.gather(*price_tasks)

    # 4. 유효/제외 종목 분리
    valid_holdings = []
    valid_prices: dict[str, list[dict]] = {}
    excluded_tickers: list[str] = []

    for h, prices in zip(holdings, price_results):
        if prices:
            valid_holdings.append(h)
            valid_prices[h.krx_code] = prices
        else:
            excluded_tickers.append(h.krx_code)

    if not valid_holdings:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="모든 종목의 가격 데이터 조회에 실패했습니다. 종목 코드 또는 날짜 범위를 확인하세요.",
        )

    # 5. 공통 거래일 정렬
    dates, aligned_closes = _align_close_series(valid_prices)

    if not dates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="공통 거래일이 없습니다. 날짜 범위를 넓혀주세요.",
        )

    # 6. USD 종목 환산 (KRW로 통일)
    for h in valid_holdings:
        if getattr(h, "currency", "KRW") == "USD":
            aligned_closes[h.krx_code] = [c * usd_krw_rate for c in aligned_closes[h.krx_code]]

    # 7. 비중 정규화 (quantity 기반 → 균등 비중으로 처리)
    # 종목별 비중은 quantity가 아닌 균등 분배 (buy-and-hold 단순화)
    n_valid = len(valid_holdings)
    raw_weights = [1.0] * n_valid  # 균등 비중
    weights = _normalize_weights(raw_weights)
    tickers = [h.krx_code for h in valid_holdings]

    # 8. 일별 포트폴리오 가치 계산
    values = _daily_portfolio_values(aligned_closes, weights, tickers)

    if not values:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="포트폴리오 가치 계산에 실패했습니다.",
        )

    # 9. 수익률 계산
    daily_returns, cumulative_returns = _compute_returns(values)

    # 10. 지표 계산 (기존 backtest/metrics.py 재사용)
    mdd = calculate_max_drawdown(values)  # 1.0 기준 누적 가치 시계열 입력
    sharpe = calculate_sharpe_ratio(daily_returns[1:], risk_free_rate=0.035)  # 첫날 제외(0)
    total_ret = calculate_total_return(values)

    # 11. 일별 결과 조합
    daily_entries = [
        DailyReturn(
            date=dates[i],
            portfolio_value=values[i],
            daily_return=daily_returns[i],
            cumulative_return=cumulative_returns[i],
        )
        for i in range(len(dates))
    ]

    return BacktestResult(
        daily=daily_entries,
        mdd=mdd,
        sharpe_ratio=sharpe,
        total_return=total_ret,
        period_days=len(dates),
        excluded_tickers=excluded_tickers,
        used_tickers=tickers,
        disclaimer=DISCLAIMER,
    )
