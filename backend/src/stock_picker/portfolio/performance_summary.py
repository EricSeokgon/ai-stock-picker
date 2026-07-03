# 포트폴리오 기간별 성과 요약 서비스 (SPEC-STOCK-030)
# scipy 사용 금지 — numpy + math 표준 라이브러리만 사용
# 전략 A: backtest.py의 프라이빗 함수를 이 파일에서 재구현
from __future__ import annotations

import asyncio
import json
import logging
import math
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from typing import Any


from stock_picker.backtest.metrics import calculate_max_drawdown
from stock_picker.portfolio.fx_rate import _today_kst, get_usd_krw_rate
from stock_picker.portfolio.schemas import PerformanceSummaryResponse, PeriodPerformance
from stock_picker.portfolio.service import get_portfolio_with_holdings

logger = logging.getLogger(__name__)

# ─── 상수 ────────────────────────────────────────────────────────────────────

# @MX:NOTE: [AUTO] 기간 표시 레이블 — 프론트엔드와 공유되는 한국어 표기
PERIOD_DISPLAY_LABELS: dict[str, str] = {
    "ytd": "YTD",
    "1m": "1개월",
    "3m": "3개월",
    "6m": "6개월",
    "1y": "1년",
}

# 거래일 기준 연간 일수 (표준값)
_TRADING_DAYS_PER_YEAR = 252

# Redis TTL (초)
_CACHE_TTL = 3600

# USD/KRW 환율 폴백값
_FX_FALLBACK = 1350.0

# 면책 문구
_DISCLAIMER = (
    "이 성과 요약은 과거 데이터 기반 시뮬레이션이며 미래 수익을 보장하지 않습니다. "
    "투자 결정 시 전문가 상담을 권장합니다."
)

# 스레드풀 (FDR 동기 호출용)
_executor = ThreadPoolExecutor(max_workers=4)


# ─── 캐시 유틸 ───────────────────────────────────────────────────────────────

def _build_cache_key(portfolio_id: int, today_kst: str) -> str:
    """Redis 캐시 키 생성 — portfolio_perf_summary:{id}:{YYYY-MM-DD}"""
    return f"portfolio_perf_summary:{portfolio_id}:{today_kst}"


# ─── 기간 시작일 계산 ────────────────────────────────────────────────────────

def _compute_period_dates(today: date) -> dict[str, date]:
    """
    # @MX:ANCHOR: [AUTO] 기간 시작일 계산 — 5개 표준 기간 정의
    # @MX:REASON: [AUTO] 여러 테스트 및 calculate_performance_summary에서 참조
    # @MX:SPEC: SPEC-STOCK-030 §5.1

    5개 표준 기간의 시작일을 계산한다.
    - ytd: 당해 1월 1일
    - 1m: 오늘 - 30일
    - 3m: 오늘 - 90일
    - 6m: 오늘 - 180일
    - 1y: 오늘 - 365일
    """
    return {
        "ytd": date(today.year, 1, 1),
        "1m": today - timedelta(days=30),
        "3m": today - timedelta(days=90),
        "6m": today - timedelta(days=180),
        "1y": today - timedelta(days=365),
    }


# ─── 가격 데이터 정렬 ────────────────────────────────────────────────────────

def _align_close_series(
    price_data: dict[str, list[dict[str, Any]]],
) -> tuple[list[str], dict[str, list[float]]]:
    """
    여러 종목의 가격 데이터를 공통 거래일 기준으로 내부 조인(inner join)한다.

    Args:
        price_data: {ticker: [{date: str, close: float}, ...]} 형태의 딕셔너리

    Returns:
        (공통_날짜_목록, {ticker: close_목록}) 튜플
    """
    if not price_data:
        return [], {}

    # 각 종목별 날짜 집합 계산
    date_sets = []
    for ticker, series in price_data.items():
        date_sets.append({row["date"] for row in series})

    # 공통 날짜 = 모든 종목에 존재하는 날짜 (교집합)
    common_date_set = date_sets[0]
    for ds in date_sets[1:]:
        common_date_set = common_date_set & ds

    if not common_date_set:
        return [], {}

    # 날짜 정렬
    common_dates = sorted(common_date_set)

    # 각 종목별 공통 날짜의 종가 추출
    aligned: dict[str, list[float]] = {}
    for ticker, series in price_data.items():
        date_to_close = {row["date"]: row["close"] for row in series}
        aligned[ticker] = [date_to_close[d] for d in common_dates]

    return common_dates, aligned


def _apply_fx_rate(
    price_data: list[dict[str, Any]],
    fx_rate: float,
) -> list[dict[str, Any]]:
    """
    가격 데이터에 환율을 적용하여 KRW 기준 가격으로 변환한다.

    Args:
        price_data: [{date: str, close: float}, ...] 형태의 가격 데이터
        fx_rate: 적용할 환율 (KRW 종목은 1.0, USD 종목은 USD/KRW 환율)

    Returns:
        KRW 기준으로 환산된 가격 데이터
    """
    if not price_data:
        return []
    return [{"date": row["date"], "close": row["close"] * fx_rate} for row in price_data]


def _normalize_weights(weights: list[float]) -> list[float]:
    """
    비중 목록을 정규화하여 합이 1.0이 되도록 한다.

    Args:
        weights: 정규화 전 비중 목록

    Returns:
        합이 1.0인 정규화된 비중 목록
        총합이 0이면 동일 비중으로 반환
    """
    total = sum(weights)
    if total == 0:
        n = len(weights)
        return [1.0 / n if n > 0 else 0.0] * n
    return [w / total for w in weights]


def _compute_portfolio_values(
    aligned_closes: dict[str, list[float]],
    weights: list[float],
    tickers: list[str],
) -> list[float]:
    """
    비중 가중 포트폴리오 가치 시계열을 계산한다.
    첫날을 1.0으로 정규화한다.

    Args:
        aligned_closes: {ticker: [close, ...]} 공통 거래일 기준 종가
        weights: 종목별 비중 (합=1.0)
        tickers: 종목 코드 목록 (weights와 순서 대응)

    Returns:
        날짜별 포트폴리오 가치 목록 (첫날=1.0)
    """
    if not tickers or not aligned_closes:
        return []

    n_days = len(next(iter(aligned_closes.values())))
    if n_days == 0:
        return []

    values = []
    for day_idx in range(n_days):
        day_value = 0.0
        for ticker, weight in zip(tickers, weights):
            closes = aligned_closes[ticker]
            base_price = closes[0]
            if base_price == 0:
                continue
            day_value += weight * (closes[day_idx] / base_price)
        values.append(day_value)

    return values


# ─── 수익률 계산 ─────────────────────────────────────────────────────────────

def _compute_period_returns(values: list[float]) -> dict[str, Any]:
    """
    # @MX:ANCHOR: [AUTO] 기간 수익률 계산 핵심 함수
    # @MX:REASON: [AUTO] 5개 기간 각각에 대해 calculate_performance_summary에서 호출
    # @MX:SPEC: SPEC-STOCK-030 §5.2

    포트폴리오 가치 시계열로부터 성과 지표를 계산한다.

    Args:
        values: 포트폴리오 가치 시계열 (첫날≈1.0)

    Returns:
        {has_data, total_return_pct, annualized_return_pct, mdd_pct, trading_days}
    """
    n = len(values)

    # 거래일이 2일 미만이면 데이터 없음으로 처리
    if n < 2:
        return {
            "has_data": False,
            "total_return_pct": None,
            "annualized_return_pct": None,
            "mdd_pct": None,
            "trading_days": n,
        }

    # 총 수익률 (%)
    total_return = (values[-1] / values[0] - 1.0) * 100.0

    # 연환산 수익률 — (1 + r_total)^(252 / n_days) - 1
    trading_days = n - 1  # 간격 수 = 거래일 수
    factor = _TRADING_DAYS_PER_YEAR / trading_days
    annualized_return = (math.pow(1.0 + total_return / 100.0, factor) - 1.0) * 100.0

    # 최대 낙폭 — calculate_max_drawdown은 음수 반환 (단위: 비율)
    mdd_ratio = calculate_max_drawdown(values)
    mdd_pct = mdd_ratio * 100.0  # % 단위로 변환

    return {
        "has_data": True,
        "total_return_pct": round(total_return, 4),
        "annualized_return_pct": round(annualized_return, 4),
        "mdd_pct": round(mdd_pct, 4),
        "trading_days": trading_days,
    }


# ─── FDR 가격 조회 ───────────────────────────────────────────────────────────

def _fetch_price_series_sync(ticker: str, start_date: date, end_date: date) -> list[dict[str, Any]]:
    """
    FDR을 사용하여 종목 가격 시계열을 동기 방식으로 조회한다.
    (Strategy A: backtest.py의 동일 함수를 재구현)

    Args:
        ticker: 종목 코드
        start_date: 시작일
        end_date: 종료일

    Returns:
        [{date: str, close: float}, ...] 형태의 가격 데이터
        실패 시 빈 리스트 반환
    """
    try:
        import FinanceDataReader as fdr  # noqa: PLC0415
        df = fdr.DataReader(ticker, start=str(start_date), end=str(end_date))
        if df is None or df.empty:
            return []
        result = []
        for idx, row in df.iterrows():
            close_val = row.get("Close") or row.get("close")
            if close_val is None:
                continue
            result.append({"date": str(idx.date()), "close": float(close_val)})
        return result
    except Exception as e:  # noqa: BLE001
        logger.warning("FDR 조회 실패 — ticker=%s, error=%s", ticker, e)
        return []


async def _fetch_price_series_for_period(
    ticker: str,
    start_date: date,
    end_date: date,
) -> list[dict[str, Any]]:
    """
    비동기 컨텍스트에서 FDR 동기 함수를 executor로 호출한다.

    Args:
        ticker: 종목 코드
        start_date: 기간 시작일
        end_date: 기간 종료일

    Returns:
        [{date: str, close: float}, ...] 가격 데이터
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _executor,
        _fetch_price_series_sync,
        ticker,
        start_date,
        end_date,
    )


# ─── 메인 오케스트레이션 ─────────────────────────────────────────────────────

async def calculate_performance_summary(
    portfolio_id: int,
    user_id: int,
    db: Any,
    redis: Any,
    refresh: bool = False,
) -> PerformanceSummaryResponse:
    """
    # @MX:ANCHOR: [AUTO] 기간별 성과 요약 진입점 — router와 테스트에서 직접 호출
    # @MX:REASON: [AUTO] router 엔드포인트, 단위 테스트, 통합 테스트 3곳 이상에서 참조
    # @MX:SPEC: SPEC-STOCK-030 REQ-PS-001 ~ REQ-PS-010

    포트폴리오의 5개 표준 기간(YTD/1M/3M/6M/1Y) 성과 요약을 계산한다.

    1. Redis 캐시 확인 (refresh=False인 경우)
    2. 포트폴리오 소유권 검증 (실패 시 HTTP 404)
    3. 빈 포트폴리오 처리 (has_data=False)
    4. USD/KRW 환율 조회 (폴백: 1350.0)
    5. 5개 기간별 FDR 가격 조회 (asyncio.gather 병렬)
    6. 가중 포트폴리오 가치 계산
    7. 수익률/MDD 계산
    8. Redis 캐시 저장
    """
    from fastapi import HTTPException  # noqa: PLC0415 — 순환 import 방지

    today_kst = _today_kst()
    cache_key = _build_cache_key(portfolio_id, today_kst)

    # 1. Redis 캐시 확인
    if not refresh:
        try:
            cached = await redis.get(cache_key)
            if cached:
                data = json.loads(cached)
                return PerformanceSummaryResponse.model_validate(data)
        except Exception as e:  # noqa: BLE001
            logger.warning("Redis 캐시 조회 실패 (무시): %s", e)

    # 2. 포트폴리오 소유권 검증
    portfolio = get_portfolio_with_holdings(db, portfolio_id, user_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="포트폴리오를 찾을 수 없습니다")

    today = date.today()
    period_start_dates = _compute_period_dates(today)
    today_str = str(today)

    # 3. 빈 포트폴리오 처리
    if not portfolio.holdings:
        periods = [
            PeriodPerformance(
                period=period,
                display_label=PERIOD_DISPLAY_LABELS[period],
                start_date=None,
                end_date=None,
                trading_days=0,
                has_data=False,
                total_return_pct=None,
                annualized_return_pct=None,
                mdd_pct=None,
            )
            for period in ["ytd", "1m", "3m", "6m", "1y"]
        ]
        return _build_response(portfolio_id, periods)

    # 4. USD/KRW 환율 조회
    try:
        fx_rate = await get_usd_krw_rate(redis)
    except Exception as e:  # noqa: BLE001
        logger.warning("환율 조회 실패, 폴백 사용: %s", e)
        fx_rate = _FX_FALLBACK

    # 5. 종목 정보 추출
    holdings = portfolio.holdings
    tickers = [h.krx_code for h in holdings]
    raw_weights = [float(h.weight) for h in holdings]
    currencies = [h.currency for h in holdings]
    weights = _normalize_weights(raw_weights)

    # 6. 5개 기간별 성과 계산
    periods: list[PeriodPerformance] = []
    period_order = ["ytd", "1m", "3m", "6m", "1y"]

    for period in period_order:
        start_date = period_start_dates[period]
        period_result = await _calculate_single_period(
            period=period,
            start_date=start_date,
            end_date=today,
            today_str=today_str,
            tickers=tickers,
            weights=weights,
            currencies=currencies,
            fx_rate=fx_rate,
        )
        periods.append(period_result)

    # 7. 응답 생성
    response = _build_response(portfolio_id, periods)

    # 8. Redis 캐시 저장
    try:
        await redis.setex(cache_key, _CACHE_TTL, response.model_dump_json())
    except Exception as e:  # noqa: BLE001
        logger.warning("Redis 캐시 저장 실패 (무시): %s", e)

    return response


async def _calculate_single_period(
    period: str,
    start_date: date,
    end_date: date,
    today_str: str,
    tickers: list[str],
    weights: list[float],
    currencies: list[str],
    fx_rate: float,
) -> PeriodPerformance:
    """
    단일 기간의 성과를 계산한다.

    Args:
        period: 기간 코드 (ytd/1m/3m/6m/1y)
        start_date: 기간 시작일
        end_date: 기간 종료일
        today_str: 오늘 날짜 문자열
        tickers: 종목 코드 목록
        weights: 정규화된 비중 목록
        currencies: 통화 목록 (KRW/USD)
        fx_rate: USD/KRW 환율

    Returns:
        PeriodPerformance 객체
    """
    start_date_str = str(start_date)

    # 종목별 FDR 가격 조회 (병렬)
    fetch_tasks = [
        _fetch_price_series_for_period(ticker, start_date, end_date)
        for ticker in tickers
    ]
    price_results = await asyncio.gather(*fetch_tasks, return_exceptions=False)

    # 빈 결과 처리 — FDR 실패 종목이 있으면 해당 기간 전체를 has_data=False
    price_data: dict[str, list[dict[str, Any]]] = {}
    for ticker, series, currency in zip(tickers, price_results, currencies):
        if not series:
            logger.warning("기간 %s — 종목 %s 가격 데이터 없음", period, ticker)
            continue
        # USD 종목은 KRW으로 환산
        if currency == "USD":
            series = _apply_fx_rate(series, fx_rate)
        price_data[ticker] = series

    if not price_data:
        return PeriodPerformance(
            period=period,
            display_label=PERIOD_DISPLAY_LABELS[period],
            start_date=start_date_str,
            end_date=today_str,
            trading_days=0,
            has_data=False,
            total_return_pct=None,
            annualized_return_pct=None,
            mdd_pct=None,
        )

    # 공통 거래일 기준 정렬
    common_dates, aligned_closes = _align_close_series(price_data)

    if len(common_dates) < 2:
        return PeriodPerformance(
            period=period,
            display_label=PERIOD_DISPLAY_LABELS[period],
            start_date=start_date_str,
            end_date=today_str,
            trading_days=len(common_dates),
            has_data=False,
            total_return_pct=None,
            annualized_return_pct=None,
            mdd_pct=None,
        )

    # 데이터가 있는 종목만 비중 재정규화
    available_tickers = list(price_data.keys())
    available_indices = [tickers.index(t) for t in available_tickers if t in tickers]
    available_weights = _normalize_weights([weights[i] for i in available_indices])

    # 포트폴리오 가치 시계열 계산
    portfolio_values = _compute_portfolio_values(aligned_closes, available_weights, available_tickers)

    # 성과 지표 계산
    metrics = _compute_period_returns(portfolio_values)

    return PeriodPerformance(
        period=period,
        display_label=PERIOD_DISPLAY_LABELS[period],
        start_date=common_dates[0] if common_dates else start_date_str,
        end_date=common_dates[-1] if common_dates else today_str,
        trading_days=metrics["trading_days"],
        has_data=metrics["has_data"],
        total_return_pct=metrics["total_return_pct"],
        annualized_return_pct=metrics["annualized_return_pct"],
        mdd_pct=metrics["mdd_pct"],
    )


def _build_response(portfolio_id: int, periods: list[PeriodPerformance]) -> PerformanceSummaryResponse:
    """성과 요약 응답 객체를 생성한다."""
    now_utc = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return PerformanceSummaryResponse(
        portfolio_id=portfolio_id,
        periods=periods,
        calculated_at=now_utc,
        disclaimer=_DISCLAIMER,
    )
