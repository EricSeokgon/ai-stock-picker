# 배당 수익률 분석 강화 서비스 (SPEC-STOCK-033)
# SPEC-019 dividends.py를 데이터 레이어로 재사용 — 수정 금지
# scipy 금지 (NFR-001): numpy + math 모듈만 사용
#
# @MX:NOTE: [AUTO] SPEC-019 get_dividend_info 재사용, 수정 금지
# @MX:WARN: [AUTO] dividends.py 확장: 하위 호환성 유지 필수 (019 테스트 불변)
# @MX:REASON: SPEC-019 기존 엔드포인트와 충돌 방지 — /dividend/(단수) vs /dividends(복수)
import logging
from datetime import date
from typing import Any

from fastapi import HTTPException, status

from stock_picker.portfolio import service as portfolio_service
from stock_picker.portfolio.dividends import get_dividend_info
from stock_picker.portfolio.schemas import (
    DividendCalendar,
    DividendEvent,
    DividendHolding,
    DividendSummary,
    DRIPProjection,
    DRIPYearData,
)

logger = logging.getLogger(__name__)

_DRIP_DISCLAIMER = "배당률 고정, 가격 성장 미반영 — 참고용 시뮬레이션입니다"


def calculate_dividend_summary(
    portfolio_id: int,
    holdings: list[dict[str, Any]],
) -> DividendSummary:
    """배당 수익률 요약 계산 — 순수 함수, DB/외부 의존 없음.

    # @MX:NOTE: [AUTO] SPEC-019 get_dividend_info 재사용, 수정 금지
    # 가중 평균 수익률: Σ(value_i * yield_i) / total_value (단순 평균 아님)

    Args:
        portfolio_id: 포트폴리오 ID (응답 스키마 포함용)
        holdings: 보유 종목 딕셔너리 목록
                  각 항목: {krx_code, stock_name, shares, current_price, annual_dps}

    Returns:
        DividendSummary 스키마 인스턴스.
    """
    holding_results: list[DividendHolding] = []
    total_portfolio_value = 0.0
    total_annual_dividend = 0.0
    weighted_yield_sum = 0.0

    for h in holdings:
        shares = int(h.get("shares", 0))
        current_price = float(h.get("current_price", 0.0))
        annual_dps = float(h.get("annual_dps", 0.0))

        # 종목 가치 = 보유 수 * 현재가
        holding_value = shares * current_price
        total_portfolio_value += holding_value

        # 종목별 연간 예상 배당 = 보유 수 * DPS
        estimated_annual_dividend = shares * annual_dps
        total_annual_dividend += estimated_annual_dividend

        # 종목별 배당 수익률 = DPS / 현재가 * 100 (현재가 0이면 0)
        dividend_yield_pct = (annual_dps / current_price * 100.0) if current_price > 0 else 0.0

        # 가중 평균용: value_i * yield_i 누적
        weighted_yield_sum += holding_value * dividend_yield_pct

        holding_results.append(
            DividendHolding(
                krx_code=h.get("krx_code", ""),
                stock_name=h.get("stock_name", ""),
                shares=shares,
                annual_dps=annual_dps,
                dividend_yield_pct=round(dividend_yield_pct, 4),
                estimated_annual_dividend=estimated_annual_dividend,
            )
        )

    # 포트폴리오 가중 평균 배당 수익률
    portfolio_dividend_yield_pct = (
        weighted_yield_sum / total_portfolio_value if total_portfolio_value > 0 else 0.0
    )

    return DividendSummary(
        portfolio_id=portfolio_id,
        total_portfolio_value=total_portfolio_value,
        total_annual_dividend=total_annual_dividend,
        portfolio_dividend_yield_pct=round(portfolio_dividend_yield_pct, 4),
        holdings=holding_results,
    )


def calculate_drip_projection(
    portfolio_id: int,
    initial_value: float,
    dividend_yield_pct: float,
    reinvest_rate: float,
    years: int,
) -> DRIPProjection:
    """DRIP 복리 시뮬레이션 — 순수 함수, scipy 미사용.

    # @MX:ANCHOR: [AUTO] DRIP 복리 시뮬레이션 진입점 (API·테스트 fan_in >= 3)
    # @MX:REASON: 순수 함수 — scipy 금지, DB 없이 테스트 가능, reinvest_rate 0~1 복리 공식

    공식:
        value[0] = initial_value
        value[t] = value[t-1] × (1 + dividend_yield_pct/100 × reinvest_rate)
        annual_dividend[t] = value[t-1] × dividend_yield_pct/100
        cumulative_return_pct[t] = (value[t] / initial_value - 1) × 100

    Args:
        portfolio_id: 포트폴리오 ID
        initial_value: 초기 포트폴리오 가치 (KRW)
        dividend_yield_pct: 연간 배당 수익률 (%)
        reinvest_rate: 재투자 비율 (0.0 ~ 1.0)
        years: 시뮬레이션 연수 (0 ~ years 포함, 총 years+1 포인트)

    Returns:
        DRIPProjection 스키마 인스턴스.
    """
    year_data: list[DRIPYearData] = []
    yield_decimal = dividend_yield_pct / 100.0

    current_value = initial_value

    for t in range(years + 1):
        if t == 0:
            # year 0: 초기값, 배당 없음
            year_data.append(
                DRIPYearData(
                    year=0,
                    portfolio_value=initial_value,
                    annual_dividend=0.0,
                    cumulative_return_pct=0.0,
                )
            )
        else:
            prev_value = current_value
            # 해당 연도 배당 = 전년 가치 * 배당수익률
            annual_dividend = prev_value * yield_decimal
            # 재투자 후 가치 = 전년 가치 * (1 + yield * reinvest_rate)
            current_value = prev_value * (1 + yield_decimal * reinvest_rate)
            # 누적 수익률
            cumulative_return_pct = (current_value / initial_value - 1) * 100

            year_data.append(
                DRIPYearData(
                    year=t,
                    portfolio_value=current_value,
                    annual_dividend=annual_dividend,
                    cumulative_return_pct=cumulative_return_pct,
                )
            )

    return DRIPProjection(
        portfolio_id=portfolio_id,
        initial_value=initial_value,
        dividend_yield_pct=dividend_yield_pct,
        reinvest_rate=reinvest_rate,
        years=year_data,
        disclaimer=_DRIP_DISCLAIMER,
    )


def calculate_dividend_calendar(
    portfolio_id: int,
    year: int,
    events: list[dict[str, Any]],
) -> DividendCalendar:
    """배당 캘린더 계산 — 순수 함수, 월별 이벤트 그룹화.

    Args:
        portfolio_id: 포트폴리오 ID
        year: 조회 연도 (필터 기준)
        events: 배당 이벤트 딕셔너리 목록
                각 항목: {krx_code, stock_name, ex_dividend_date, payment_date, dps, shares}

    Returns:
        DividendCalendar 스키마 인스턴스.
    """
    months: dict[int, list[DividendEvent]] = {}

    for ev in events:
        ex_date: date = ev["ex_dividend_date"]
        # 연도 필터
        if ex_date.year != year:
            continue

        month = ex_date.month
        dps = float(ev.get("dps", 0.0))
        shares = int(ev.get("shares", 0))
        estimated_total = shares * dps

        event = DividendEvent(
            krx_code=ev.get("krx_code", ""),
            stock_name=ev.get("stock_name", ""),
            ex_dividend_date=ex_date,
            payment_date=ev.get("payment_date"),
            dps=dps,
            shares=shares,
            estimated_total=estimated_total,
        )

        if month not in months:
            months[month] = []
        months[month].append(event)

    return DividendCalendar(
        portfolio_id=portfolio_id,
        year=year,
        months=months,
    )


async def get_dividend_summary(
    portfolio_id: int,
    user_id: int,
    db: Any,
    redis: Any,
) -> DividendSummary:
    """포트폴리오 배당 수익률 요약 조회 (SPEC-STOCK-033 API 오케스트레이션).

    소유권 미일치 시 HTTP 404 반환.

    Args:
        portfolio_id: 포트폴리오 ID
        user_id: 인증된 사용자 ID
        db: SQLAlchemy 세션
        redis: redis.asyncio 클라이언트

    Returns:
        DividendSummary 스키마 인스턴스.
    """
    portfolio = portfolio_service.get_portfolio_with_holdings(db, portfolio_id, user_id)
    if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="포트폴리오를 찾을 수 없습니다",
        )

    holdings_data: list[dict[str, Any]] = []
    for h in portfolio.holdings:
        div = await get_dividend_info(h.krx_code, redis)
        dps = div.get("dps") or 0.0

        # 현재가: FDR DPS 데이터에서 역산 또는 0 (요약용 최선노력)
        # 배당수익률이 있으면 역산: current_price = dps / (yield/100)
        div_yield = div.get("dividend_yield")
        if div_yield and div_yield > 0 and dps > 0:
            current_price = dps / (div_yield / 100.0)
        else:
            # 현재가 미확보: avg_buy_price 사용 (근사치)
            current_price = float(h.avg_buy_price)

        holdings_data.append({
            "krx_code": h.krx_code,
            "stock_name": div.get("name") or h.krx_code,
            "shares": int(h.quantity),
            "current_price": current_price,
            "annual_dps": dps,
        })

    return calculate_dividend_summary(portfolio_id=portfolio_id, holdings=holdings_data)


async def get_dividend_calendar(
    portfolio_id: int,
    user_id: int,
    db: Any,
    redis: Any,
    year: int,
) -> DividendCalendar:
    """포트폴리오 배당 캘린더 조회 (SPEC-STOCK-033 API 오케스트레이션).

    소유권 미일치 시 HTTP 404 반환.

    Args:
        portfolio_id: 포트폴리오 ID
        user_id: 인증된 사용자 ID
        db: SQLAlchemy 세션
        redis: redis.asyncio 클라이언트
        year: 조회 연도

    Returns:
        DividendCalendar 스키마 인스턴스.
    """
    portfolio = portfolio_service.get_portfolio_with_holdings(db, portfolio_id, user_id)
    if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="포트폴리오를 찾을 수 없습니다",
        )

    events: list[dict[str, Any]] = []
    for h in portfolio.holdings:
        div = await get_dividend_info(h.krx_code, redis)
        if not div.get("dividend_available", False):
            continue

        # ex_dividend_month에서 날짜 구성 (FDR 베스트에포트)
        ex_month = div.get("ex_dividend_month")
        if ex_month is None:
            continue

        # 배당기준일: 해당 연도의 ex_month 말일(근사치)
        import calendar
        last_day = calendar.monthrange(year, ex_month)[1]
        ex_div_date = date(year, ex_month, last_day)

        dps = div.get("dps") or 0.0
        events.append({
            "krx_code": h.krx_code,
            "stock_name": div.get("name") or h.krx_code,
            "ex_dividend_date": ex_div_date,
            "payment_date": None,  # FDR에서 지급일 미확보
            "dps": dps,
            "shares": int(h.quantity),
        })

    return calculate_dividend_calendar(portfolio_id=portfolio_id, year=year, events=events)


async def get_drip_projection(
    portfolio_id: int,
    user_id: int,
    db: Any,
    redis: Any,
    years: int = 10,
    reinvest_rate: float = 1.0,
) -> DRIPProjection:
    """포트폴리오 DRIP 복리 시뮬레이션 (SPEC-STOCK-033 API 오케스트레이션).

    소유권 미일치 시 HTTP 404 반환.

    Args:
        portfolio_id: 포트폴리오 ID
        user_id: 인증된 사용자 ID
        db: SQLAlchemy 세션
        redis: redis.asyncio 클라이언트
        years: 시뮬레이션 연수 (기본 10년)
        reinvest_rate: 배당 재투자 비율 0.0~1.0 (기본 1.0 = 전액 재투자)

    Returns:
        DRIPProjection 스키마 인스턴스.
    """
    portfolio = portfolio_service.get_portfolio_with_holdings(db, portfolio_id, user_id)
    if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="포트폴리오를 찾을 수 없습니다",
        )

    # 포트폴리오 초기 가치 및 가중 평균 배당 수익률 산출
    total_value = 0.0
    weighted_yield_sum = 0.0

    for h in portfolio.holdings:
        div = await get_dividend_info(h.krx_code, redis)
        dps = div.get("dps") or 0.0
        div_yield = div.get("dividend_yield") or 0.0

        holding_value = float(h.avg_buy_price) * float(h.quantity)
        total_value += holding_value
        weighted_yield_sum += holding_value * div_yield

    portfolio_yield_pct = (weighted_yield_sum / total_value) if total_value > 0 else 0.0
    initial_value = total_value if total_value > 0 else 1_000_000.0  # 기본값

    return calculate_drip_projection(
        portfolio_id=portfolio_id,
        initial_value=initial_value,
        dividend_yield_pct=portfolio_yield_pct,
        reinvest_rate=reinvest_rate,
        years=years,
    )
