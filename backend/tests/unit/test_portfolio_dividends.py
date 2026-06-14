# 배당 포트폴리오 분석 서비스 테스트 (SPEC-STOCK-019)
# TDD RED 단계: 구현 전 실패 테스트 작성
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from stock_picker.portfolio.dividends import (
    _fetch_dividend_info,
    calculate_portfolio_dividends,
    get_dividend_info,
)
from stock_picker.portfolio.schemas import (
    DividendCalendarMonth,
    HoldingDividend,
    PortfolioDividends,
)


# ─── 픽스처 ───────────────────────────────────────────────────────────────────

def _make_holding(krx_code: str = "005930", quantity: int = 10, avg_buy_price: float = 60000.0):
    """PortfolioHolding 모사 객체 생성."""
    h = MagicMock()
    h.krx_code = krx_code
    h.quantity = quantity
    h.avg_buy_price = avg_buy_price
    return h


def _make_portfolio(holdings: list):
    """Portfolio 모사 객체 생성."""
    p = MagicMock()
    p.id = 1
    p.holdings = holdings
    return p


# ─── 1. _fetch_dividend_info (동기 FDR 조회) ────────────────────────────────


def test_fetch_dividend_info_returns_dict_when_data_available():
    """FDR에 배당 데이터가 있으면 DPS·배당수익률을 dict로 반환한다."""
    import pandas as pd

    mock_df = pd.DataFrame([{
        "Symbol": "005930",
        "Name": "삼성전자",
        "DividendYield": 2.5,
        "DPS": 1444.0,
    }])

    with patch("stock_picker.portfolio.dividends.fdr") as mock_fdr:
        mock_fdr.StockListing.return_value = mock_df
        result = _fetch_dividend_info("005930")

    assert result["dividend_available"] is True
    assert result["dps"] == 1444.0
    assert result["dividend_yield"] == 2.5
    assert result["krx_code"] == "005930"


def test_fetch_dividend_info_returns_unavailable_when_no_row():
    """FDR 목록에 해당 종목이 없으면 dividend_available=False를 반환한다."""
    import pandas as pd

    mock_df = pd.DataFrame([{"Symbol": "000000", "Name": "없음"}])

    with patch("stock_picker.portfolio.dividends.fdr") as mock_fdr:
        mock_fdr.StockListing.return_value = mock_df
        result = _fetch_dividend_info("005930")

    assert result["dividend_available"] is False
    assert result["dps"] is None
    assert result["dividend_yield"] is None


def test_fetch_dividend_info_returns_unavailable_when_dps_nan():
    """FDR 결과에서 DPS가 NaN이면 dividend_available=False를 반환한다."""
    import math

    import pandas as pd

    mock_df = pd.DataFrame([{
        "Symbol": "005930",
        "Name": "삼성전자",
        "DividendYield": float("nan"),
        "DPS": float("nan"),
    }])

    with patch("stock_picker.portfolio.dividends.fdr") as mock_fdr:
        mock_fdr.StockListing.return_value = mock_df
        result = _fetch_dividend_info("005930")

    assert result["dividend_available"] is False
    assert result["dps"] is None


def test_fetch_dividend_info_returns_unavailable_when_fdr_raises():
    """FDR 조회가 예외를 던지면 dividend_available=False graceful degradation."""
    with patch("stock_picker.portfolio.dividends.fdr") as mock_fdr:
        mock_fdr.StockListing.side_effect = RuntimeError("network error")
        result = _fetch_dividend_info("005930")

    assert result["dividend_available"] is False


# ─── 2. get_dividend_info (Redis 캐시 + FDR 조회) ────────────────────────────


@pytest.mark.asyncio
async def test_get_dividend_info_returns_cached_value_on_cache_hit():
    """Redis 캐시 히트 시 FDR를 호출하지 않고 캐시 값을 반환한다."""
    import json

    cached = {
        "krx_code": "005930",
        "name": "삼성전자",
        "dps": 1444.0,
        "dividend_yield": 2.5,
        "ex_dividend_month": 12,
        "dividend_available": True,
        "yoy_dps_change_pct": None,
    }

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=json.dumps(cached))

    result = await get_dividend_info("005930", mock_redis)

    assert result["dividend_available"] is True
    assert result["dps"] == 1444.0
    mock_redis.get.assert_called_once_with("dividends:005930")


@pytest.mark.asyncio
async def test_get_dividend_info_fetches_and_caches_on_cache_miss():
    """Redis 캐시 미스 시 FDR 조회 후 결과를 Redis에 저장한다."""
    import pandas as pd

    mock_df = pd.DataFrame([{
        "Symbol": "005930",
        "Name": "삼성전자",
        "DividendYield": 2.5,
        "DPS": 1444.0,
    }])

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock()

    with patch("stock_picker.portfolio.dividends.fdr") as mock_fdr:
        mock_fdr.StockListing.return_value = mock_df
        result = await get_dividend_info("005930", mock_redis)

    assert result["dividend_available"] is True
    # Redis에 저장됐는지 확인
    mock_redis.set.assert_called_once()
    call_args = mock_redis.set.call_args
    assert call_args[0][0] == "dividends:005930"
    assert call_args[1]["ex"] == 86400


@pytest.mark.asyncio
async def test_get_dividend_info_falls_back_gracefully_when_redis_unavailable():
    """Redis 장애 시 FDR에서 직접 조회하고 예외를 전파하지 않는다."""
    import pandas as pd

    mock_df = pd.DataFrame([{
        "Symbol": "005930",
        "Name": "삼성전자",
        "DividendYield": 1.5,
        "DPS": 800.0,
    }])

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(side_effect=ConnectionError("redis down"))

    with patch("stock_picker.portfolio.dividends.fdr") as mock_fdr:
        mock_fdr.StockListing.return_value = mock_df
        result = await get_dividend_info("005930", mock_redis)

    # Redis 장애에도 FDR 결과 반환
    assert result["dividend_available"] is True
    assert result["dps"] == 800.0


# ─── 3. calculate_portfolio_dividends ────────────────────────────────────────


@pytest.mark.asyncio
async def test_calculate_portfolio_dividends_computes_annual_income():
    """보유 수량 × DPS = 연간 예상 배당 수입이 정확히 계산된다."""
    from stock_picker.portfolio import service as portfolio_service

    holding = _make_holding(krx_code="005930", quantity=10, avg_buy_price=60000.0)
    portfolio = _make_portfolio([holding])

    dividend_data = {
        "krx_code": "005930",
        "name": "삼성전자",
        "dps": 1444.0,
        "dividend_yield": 2.5,
        "ex_dividend_month": 12,
        "dividend_available": True,
        "yoy_dps_change_pct": None,
    }

    mock_redis = AsyncMock()
    mock_db = MagicMock()

    with patch.object(portfolio_service, "get_portfolio_with_holdings", return_value=portfolio):
        with patch("stock_picker.portfolio.dividends.get_dividend_info", return_value=dividend_data):
            result = await calculate_portfolio_dividends(
                portfolio_id=1, user_id=1, db=mock_db, redis=mock_redis
            )

    assert result.total_annual_income == pytest.approx(1444.0 * 10)  # 14440.0
    assert result.coverage_count == 1
    assert result.total_holdings == 1


@pytest.mark.asyncio
async def test_calculate_portfolio_dividends_no_dps_contributes_zero():
    """DPS가 없는 종목은 연간 배당 수입에 0을 기여한다 (REQ-DIV-004)."""
    from stock_picker.portfolio import service as portfolio_service

    holding = _make_holding(krx_code="999999", quantity=5, avg_buy_price=10000.0)
    portfolio = _make_portfolio([holding])

    dividend_data = {
        "krx_code": "999999",
        "name": "무배당종목",
        "dps": None,
        "dividend_yield": None,
        "ex_dividend_month": None,
        "dividend_available": False,
        "yoy_dps_change_pct": None,
    }

    mock_redis = AsyncMock()
    mock_db = MagicMock()

    with patch.object(portfolio_service, "get_portfolio_with_holdings", return_value=portfolio):
        with patch("stock_picker.portfolio.dividends.get_dividend_info", return_value=dividend_data):
            result = await calculate_portfolio_dividends(
                portfolio_id=1, user_id=1, db=mock_db, redis=mock_redis
            )

    assert result.total_annual_income == 0.0
    assert result.coverage_count == 0
    assert result.weighted_avg_yield == 0.0


@pytest.mark.asyncio
async def test_calculate_portfolio_dividends_weighted_avg_yield():
    """가중 평균 배당수익률 = Σ(투자금 × yield) / Σ(투자금)."""
    from stock_picker.portfolio import service as portfolio_service

    h1 = _make_holding("005930", quantity=10, avg_buy_price=60000.0)  # 투자금 600000
    h2 = _make_holding("000660", quantity=5, avg_buy_price=120000.0)  # 투자금 600000
    portfolio = _make_portfolio([h1, h2])

    div1 = {"krx_code": "005930", "name": "삼성전자", "dps": 1444.0,
            "dividend_yield": 2.0, "ex_dividend_month": 12,
            "dividend_available": True, "yoy_dps_change_pct": None}
    div2 = {"krx_code": "000660", "name": "SK하이닉스", "dps": 600.0,
            "dividend_yield": 4.0, "ex_dividend_month": 12,
            "dividend_available": True, "yoy_dps_change_pct": None}

    mock_redis = AsyncMock()
    mock_db = MagicMock()

    side_effects = [div1, div2]

    with patch.object(portfolio_service, "get_portfolio_with_holdings", return_value=portfolio):
        with patch("stock_picker.portfolio.dividends.get_dividend_info", side_effect=side_effects):
            result = await calculate_portfolio_dividends(
                portfolio_id=1, user_id=1, db=mock_db, redis=mock_redis
            )

    # 투자금 동일하므로 가중평균 = (2.0 + 4.0) / 2 = 3.0
    assert result.weighted_avg_yield == pytest.approx(3.0, rel=1e-2)


@pytest.mark.asyncio
async def test_calculate_portfolio_dividends_calendar_groups_by_month():
    """배당 캘린더: ex_dividend_month별로 종목을 그룹핑한다 (REQ-DIV-020)."""
    from stock_picker.portfolio import service as portfolio_service

    h1 = _make_holding("005930", quantity=10, avg_buy_price=60000.0)
    h2 = _make_holding("017670", quantity=20, avg_buy_price=50000.0)
    portfolio = _make_portfolio([h1, h2])

    div1 = {"krx_code": "005930", "name": "삼성전자", "dps": 1000.0,
            "dividend_yield": 2.0, "ex_dividend_month": 12,
            "dividend_available": True, "yoy_dps_change_pct": None}
    div2 = {"krx_code": "017670", "name": "SK텔레콤", "dps": 500.0,
            "dividend_yield": 3.0, "ex_dividend_month": 3,
            "dividend_available": True, "yoy_dps_change_pct": None}

    mock_redis = AsyncMock()
    mock_db = MagicMock()

    with patch.object(portfolio_service, "get_portfolio_with_holdings", return_value=portfolio):
        with patch("stock_picker.portfolio.dividends.get_dividend_info", side_effect=[div1, div2]):
            result = await calculate_portfolio_dividends(
                portfolio_id=1, user_id=1, db=mock_db, redis=mock_redis
            )

    months_in_calendar = {cal.month for cal in result.calendar}
    assert 12 in months_in_calendar
    assert 3 in months_in_calendar

    dec_entry = next(c for c in result.calendar if c.month == 12)
    assert "005930" in dec_entry.holdings

    mar_entry = next(c for c in result.calendar if c.month == 3)
    assert "017670" in mar_entry.holdings


@pytest.mark.asyncio
async def test_calculate_portfolio_dividends_excludes_unknown_month_from_calendar():
    """ex_dividend_month가 None인 종목은 캘린더에서 제외된다 (REQ-DIV-022)."""
    from stock_picker.portfolio import service as portfolio_service

    holding = _make_holding("999999", quantity=5, avg_buy_price=10000.0)
    portfolio = _make_portfolio([holding])

    div_data = {
        "krx_code": "999999", "name": "무기준일종목",
        "dps": 500.0, "dividend_yield": 1.0,
        "ex_dividend_month": None,
        "dividend_available": True, "yoy_dps_change_pct": None,
    }

    mock_redis = AsyncMock()
    mock_db = MagicMock()

    with patch.object(portfolio_service, "get_portfolio_with_holdings", return_value=portfolio):
        with patch("stock_picker.portfolio.dividends.get_dividend_info", return_value=div_data):
            result = await calculate_portfolio_dividends(
                portfolio_id=1, user_id=1, db=mock_db, redis=mock_redis
            )

    assert result.calendar == []  # 지급월 미상 → 캘린더 제외


@pytest.mark.asyncio
async def test_calculate_portfolio_dividends_empty_portfolio():
    """보유 종목이 없으면 빈 응답을 반환한다 (REQ-DIV-API-006)."""
    from stock_picker.portfolio import service as portfolio_service

    portfolio = _make_portfolio([])

    mock_redis = AsyncMock()
    mock_db = MagicMock()

    with patch.object(portfolio_service, "get_portfolio_with_holdings", return_value=portfolio):
        result = await calculate_portfolio_dividends(
            portfolio_id=1, user_id=1, db=mock_db, redis=mock_redis
        )

    assert result.holdings == []
    assert result.total_annual_income == 0.0
    assert result.weighted_avg_yield == 0.0
    assert result.calendar == []
    assert result.coverage_count == 0
    assert result.total_holdings == 0


@pytest.mark.asyncio
async def test_calculate_portfolio_dividends_returns_none_when_portfolio_not_found():
    """포트폴리오 미존재(소유권 없음) 시 None을 반환한다."""
    from stock_picker.portfolio import service as portfolio_service

    mock_redis = AsyncMock()
    mock_db = MagicMock()

    with patch.object(portfolio_service, "get_portfolio_with_holdings", return_value=None):
        result = await calculate_portfolio_dividends(
            portfolio_id=999, user_id=1, db=mock_db, redis=mock_redis
        )

    assert result is None


# ─── 4. 스키마 검증 ──────────────────────────────────────────────────────────


def test_holding_dividend_schema_valid():
    """HoldingDividend 스키마가 올바른 필드를 갖는다."""
    h = HoldingDividend(
        krx_code="005930",
        name="삼성전자",
        quantity=10,
        dps=1444.0,
        dividend_yield=2.5,
        ex_dividend_month=12,
        annual_income=14440.0,
        dividend_available=True,
        yoy_dps_change_pct=None,
    )
    assert h.krx_code == "005930"
    assert h.annual_income == 14440.0
    assert h.yoy_dps_change_pct is None


def test_portfolio_dividends_schema_valid():
    """PortfolioDividends 스키마가 올바른 필드를 갖는다."""
    cal = DividendCalendarMonth(month=12, holdings=["005930"], total_income=14440.0)
    pd_result = PortfolioDividends(
        holdings=[],
        total_annual_income=0.0,
        weighted_avg_yield=0.0,
        calendar=[cal],
        coverage_count=0,
        total_holdings=0,
    )
    assert pd_result.total_annual_income == 0.0
    assert len(pd_result.calendar) == 1
    assert pd_result.calendar[0].month == 12
