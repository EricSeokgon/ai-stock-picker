# 종목 검색 및 주가 히스토리 라우터 (SPEC-STOCK-007 TASK-003, TASK-005)
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from stock_picker.api.deps import get_session
from stock_picker.api.schemas import (
    PricePoint,
    StockPricesResponse,
    StockSearchItem,
    StockSearchResponse,
)
from stock_picker.mapping.prices import get_stock_price_history
from stock_picker.search.service import search_stocks

router = APIRouter(tags=["stocks"])


@router.get("/stocks/search", response_model=StockSearchResponse)
async def search_stocks_endpoint(
    q: str = Query(..., min_length=1, description="검색 쿼리 (종목명 부분 일치 또는 코드 접두어)"),
    db: AsyncSession = Depends(get_session),
) -> StockSearchResponse:
    """종목 검색 API.

    종목명 부분 일치 또는 KRX 코드 접두어로 종목을 검색한다.
    최근 추천 종목은 결과 상단에 정렬된다.

    Args:
        q: 검색어 (최소 1자)
        db: 비동기 DB 세션

    Returns:
        StockSearchResponse: 검색 결과 (최대 20건)
    """
    items = await search_stocks(q=q, db=db)
    results = [
        StockSearchItem(
            krx_code=item["krx_code"],
            name=item["name"],
            in_recommendations=item["in_recommendations"],
        )
        for item in items
    ]
    return StockSearchResponse(query=q, results=results, total=len(results))


@router.get("/stocks/{krx_code}/prices", response_model=StockPricesResponse)
async def get_stock_prices(
    krx_code: str,
    days: int = Query(default=30, ge=1, le=90, description="조회 기간 (1~90일)"),
    db: AsyncSession = Depends(get_session),
) -> StockPricesResponse:
    """종목 주가 히스토리 조회 API.

    FinanceDataReader를 통해 최근 N일간의 일별 종가를 반환한다.
    조회 실패 시 available=False로 응답 (예외 전파 없음).

    Args:
        krx_code: KRX 종목코드
        days: 조회 기간 (기본 30, 최대 90)
        db: 비동기 DB 세션 (의존성 주입용, 직접 사용 없음)

    Returns:
        StockPricesResponse: 주가 히스토리
    """
    raw_prices = await get_stock_price_history(krx_code=krx_code, days=days)

    if not raw_prices:
        return StockPricesResponse(
            krx_code=krx_code,
            days=days,
            prices=[],
            available=False,
        )

    prices = [PricePoint(date=p["date"], close=p["close"]) for p in raw_prices]
    return StockPricesResponse(
        krx_code=krx_code,
        days=days,
        prices=prices,
        available=True,
    )
