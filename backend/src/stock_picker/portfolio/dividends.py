# 배당 포트폴리오 분석 서비스 (SPEC-STOCK-019)
# prices.py 패턴 재사용: run_in_executor로 동기 FDR 격리 + redis.asyncio 캐시
# @MX:NOTE: [AUTO] DB 테이블 의존 없음 — 실시간 FDR 조회 + Redis TTL 86400s
# @MX:SPEC: SPEC-STOCK-019 REQ-DIV-002·API-004·API-005
import asyncio
import json
import logging
import math
from collections import defaultdict
from typing import Any

import FinanceDataReader as fdr  # noqa: N813

from stock_picker.portfolio import service as portfolio_service
from stock_picker.portfolio.schemas import (
    DividendCalendarMonth,
    HoldingDividend,
    PortfolioDividends,
)

logger = logging.getLogger(__name__)

_DIVIDEND_TTL = 86400  # 1일
_CACHE_KEY_PREFIX = "dividends"


def _fetch_dividend_info(krx_code: str) -> dict[str, Any]:
    """동기 FDR 배당 데이터 조회 (스레드 풀에서 실행).

    # @MX:NOTE: [AUTO] 동기 FDR 호출 — run_in_executor에서만 호출할 것
    FDR StockListing('KRX')에서 Symbol 기준으로 해당 종목 행을 찾아
    DividendYield(%), DPS(원) 컬럼을 추출한다.
    컬럼 부재·NaN·예외 모두 graceful degradation으로 dividend_available=False 반환.

    Args:
        krx_code: KRX 종목코드 (예: "005930")

    Returns:
        {krx_code, name, dps, dividend_yield, ex_dividend_month,
         dividend_available, yoy_dps_change_pct} 딕셔너리.
    """
    _empty = {
        "krx_code": krx_code,
        "name": None,
        "dps": None,
        "dividend_yield": None,
        "ex_dividend_month": None,
        "dividend_available": False,
        "yoy_dps_change_pct": None,
    }

    try:
        df = fdr.StockListing("KRX")
    except Exception as e:
        logger.warning("FDR StockListing 조회 실패: %s", e)
        return _empty

    if df is None or df.empty:
        return _empty

    # Symbol 컬럼 기준 종목 검색
    row_mask = df.get("Symbol", df.get("Code", None))
    if row_mask is None:
        return _empty

    match = df[row_mask == krx_code]
    if match.empty:
        return _empty

    row = match.iloc[0]
    name = _safe_str(row, "Name")

    dps = _safe_float(row, "DPS")
    div_yield = _safe_float(row, "DividendYield")

    # 둘 다 NaN이면 배당 없음
    if dps is None and div_yield is None:
        _empty["name"] = name
        return _empty

    # 배당기준일에서 지급 예상 월 파생
    ex_month = _extract_ex_month(row)

    return {
        "krx_code": krx_code,
        "name": name,
        "dps": dps,
        "dividend_yield": div_yield,
        "ex_dividend_month": ex_month,
        "dividend_available": True,
        "yoy_dps_change_pct": None,  # 다년 데이터 미확보 시 N/A
    }


def _safe_float(row: Any, col: str) -> float | None:
    """DataFrame 행에서 float 값을 안전하게 추출. NaN이면 None 반환."""
    val = row.get(col, None)
    if val is None:
        return None
    try:
        f = float(val)
        if math.isnan(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def _safe_str(row: Any, col: str) -> str | None:
    """DataFrame 행에서 str 값을 안전하게 추출."""
    val = row.get(col, None)
    if val is None:
        return None
    return str(val)


def _extract_ex_month(row: Any) -> int | None:
    """배당기준일 컬럼에서 월(1~12)을 파생.

    배당기준일 미확보 시 None 반환 — 추측 단언 금지 (REQ-DIV-022).
    """
    for col in ("RecordDate", "ExDividendDate", "배당기준일"):
        val = row.get(col, None)
        if val is None:
            continue
        try:
            import pandas as pd

            ts = pd.Timestamp(val)
            if pd.isna(ts):
                continue
            return int(ts.month)
        except Exception:
            continue
    return None


async def get_dividend_info(krx_code: str, redis: Any) -> dict[str, Any]:
    """종목 배당 정보 조회 (Redis 캐시 + FDR fallback).

    # @MX:ANCHOR: [AUTO] 배당 데이터 조회 단일 진입점
    # @MX:REASON: calculate_portfolio_dividends에서 보유 종목마다 호출 + 라우터 레이어
    캐시 키: dividends:{krx_code}, TTL 86400s.
    Redis 장애 시 FDR 직접 조회 (REQ-DIV-API-005).

    Args:
        krx_code: KRX 종목코드
        redis: redis.asyncio 클라이언트 (또는 None)

    Returns:
        배당 정보 딕셔너리 (항상 반환, 실패 시 dividend_available=False).
    """
    cache_key = f"{_CACHE_KEY_PREFIX}:{krx_code}"

    # Redis 캐시 조회
    cached_raw: str | None = None
    try:
        cached_raw = await redis.get(cache_key)
    except Exception as e:
        logger.warning("Redis 캐시 조회 실패 — FDR fallback: %s", e)

    if cached_raw is not None:
        try:
            return json.loads(cached_raw)
        except Exception:
            pass  # 손상된 캐시 → 재조회

    # FDR 동기 조회를 스레드 풀에서 실행
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _fetch_dividend_info, krx_code)

    # Redis 캐시 저장 (실패해도 결과는 반환)
    try:
        await redis.set(cache_key, json.dumps(result), ex=_DIVIDEND_TTL)
    except Exception as e:
        logger.warning("Redis 캐시 저장 실패 — krx_code=%s: %s", krx_code, e)

    return result


async def calculate_portfolio_dividends(
    portfolio_id: int,
    user_id: int,
    db: Any,
    redis: Any,
) -> PortfolioDividends | None:
    """포트폴리오 배당 분석 집계.

    # @MX:ANCHOR: [AUTO] 배당 집계 서비스 진입점
    # @MX:REASON: router.py에서 직접 호출, 단일 집계 함수
    포트폴리오 소유권 확인 → 종목별 배당 조회 → 집계(income·yield·캘린더).

    Args:
        portfolio_id: 포트폴리오 ID
        user_id: 사용자 ID (소유권 검증)
        db: SQLAlchemy 세션
        redis: redis.asyncio 클라이언트

    Returns:
        PortfolioDividends 또는 포트폴리오 미존재 시 None.
    """
    portfolio = portfolio_service.get_portfolio_with_holdings(db, portfolio_id, user_id)
    if portfolio is None:
        return None

    holdings = portfolio.holdings
    if not holdings:
        return PortfolioDividends(
            holdings=[],
            total_annual_income=0.0,
            weighted_avg_yield=0.0,
            calendar=[],
            coverage_count=0,
            total_holdings=0,
        )

    holding_results: list[HoldingDividend] = []
    total_income = 0.0
    weighted_yield_sum = 0.0
    total_invested_for_yield = 0.0
    coverage_count = 0

    # 월별 캘린더 집계: month → {holdings: list[str], total_income: float}
    calendar_map: dict[int, dict[str, Any]] = defaultdict(
        lambda: {"holdings": [], "total_income": 0.0}
    )

    for h in holdings:
        div = await get_dividend_info(h.krx_code, redis)

        dps = div.get("dps")
        div_yield = div.get("dividend_yield")
        ex_month = div.get("ex_dividend_month")
        available = div.get("dividend_available", False)

        annual_income = (dps * float(h.quantity)) if dps is not None else 0.0
        invested = float(h.avg_buy_price) * float(h.quantity)

        holding_results.append(
            HoldingDividend(
                krx_code=h.krx_code,
                name=div.get("name"),
                quantity=int(h.quantity),
                dps=dps,
                dividend_yield=div_yield,
                ex_dividend_month=ex_month,
                annual_income=annual_income,
                yoy_dps_change_pct=div.get("yoy_dps_change_pct"),
                dividend_available=available,
            )
        )

        total_income += annual_income

        if available:
            coverage_count += 1

        # 가중 평균 yield 집계 (yield 있는 종목만)
        if div_yield is not None and invested > 0:
            weighted_yield_sum += div_yield * invested
            total_invested_for_yield += invested

        # 캘린더: 지급월 확인된 종목만 추가 (REQ-DIV-022)
        if ex_month is not None:
            calendar_map[ex_month]["holdings"].append(h.krx_code)
            calendar_map[ex_month]["total_income"] += annual_income

    weighted_avg_yield = (
        weighted_yield_sum / total_invested_for_yield if total_invested_for_yield > 0 else 0.0
    )

    # 캘린더 정렬 (월 순서)
    calendar = [
        DividendCalendarMonth(
            month=month,
            holdings=data["holdings"],
            total_income=data["total_income"],
        )
        for month, data in sorted(calendar_map.items())
    ]

    return PortfolioDividends(
        holdings=holding_results,
        total_annual_income=total_income,
        weighted_avg_yield=round(weighted_avg_yield, 4),
        calendar=calendar,
        coverage_count=coverage_count,
        total_holdings=len(holdings),
    )
