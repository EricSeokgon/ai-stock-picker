# 뉴스 피드 엔드포인트 - 분석 완료 기사 최신 N개 반환
# SPEC-STOCK-021: 시장 감성 집계, 종목별 뉴스, 수동 트리거 추가

# @MX:ANCHOR: [AUTO] 뉴스 라우터 공개 API 경계
# @MX:REASON: 프론트엔드·scheduler 모두 의존. GET /news, GET /news/market-sentiment, POST /news/fetch
# @MX:SPEC: SPEC-STOCK-021 REQ-NEWS-SENT-*, REQ-NEWS-FEED-*, REQ-NEWS-FETCH-*

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from stock_picker.api.schemas import (
    MarketSentimentResponse,
    NewsFetchResult,
    NewsItem,
    NewsResponse,
    StockNewsItem,
)
from stock_picker.db.models import Article
from stock_picker.db.session import get_session
from stock_picker.api.deps import get_redis_client
from stock_picker.news.sentiment_service import (
    get_market_sentiment,
    get_news_by_stock,
    trigger_news_fetch,
)

router = APIRouter(prefix="/news", tags=["news"])


@router.get("/market-sentiment", response_model=MarketSentimentResponse)
async def market_sentiment(
    session: AsyncSession = Depends(get_session),
    redis=Depends(get_redis_client),
) -> MarketSentimentResponse:
    """시장 전체 감성 집계 (최근 24시간 분석 기사 기준).

    REQ-NEWS-SENT-001/003/004: Redis 캐시(TTL 1800s) 우선, 미스 시 DB 집계.
    인증 불필요 (/health 패턴과 동일).
    """
    return await get_market_sentiment(redis=redis, db=session)


@router.get("", response_model=NewsResponse)
async def get_news(
    limit: int = 20,
    krx_code: str | None = None,
    session: AsyncSession = Depends(get_session),
    redis=Depends(get_redis_client),
) -> NewsResponse:
    """최신 뉴스 피드 반환.

    - krx_code 없음: 전체 뉴스 (기존 동작 유지 REQ-NEWS-FEED-001)
    - krx_code 있음: 해당 종목 뉴스 (REQ-NEWS-FEED-002, Redis 캐시 적용)
    분석 완료 기사(analysis_results 존재)만 대상으로 한다 (REQ-WEB-004).
    """
    # 종목 필터가 있으면 별도 서비스 사용 (캐시 + JOIN)
    if krx_code is not None:
        stock_items: list[StockNewsItem] = await get_news_by_stock(
            krx_code=krx_code,
            limit=limit,
            redis=redis,
            db=session,
        )
        # StockNewsItem → NewsItem 변환 (기존 응답 구조 유지)
        news_items = [
            NewsItem(
                title=item.title,
                summary=item.ai_summary,
                sentiment=item.sentiment,
                sentiment_label=item.sentiment_label,
                source=item.source,
                url=item.url,
                published_at=item.published_at,
            )
            for item in stock_items
        ]
        return NewsResponse(news=news_items, total=len(news_items))

    # 전체 뉴스 조회 (기존 로직 유지)
    stmt = (
        select(Article)
        .options(selectinload(Article.analysis_results))
        .where(Article.status.in_(["analyzed", "collected"]))
        .order_by(desc(Article.published_at))
        .limit(limit)
    )
    result = await session.execute(stmt)
    articles = result.scalars().all()

    news_items_list: list[NewsItem] = []
    for article in articles:
        # 분석 결과에서 첫 번째 항목 사용
        analysis = article.analysis_results[0] if article.analysis_results else None
        sentiment = analysis.sentiment if analysis else None
        summary = analysis.summary if analysis else None

        # sentiment_label: analysis_results에 저장된 5단계 라벨 (TASK-009)
        # getattr 사용 — 구 스키마 호환성 보장 (sentiment_label 컬럼 없는 경우 None)
        _label_raw = getattr(analysis, "sentiment_label", None) if analysis else None
        sentiment_label = str(_label_raw) if isinstance(_label_raw, str) else None

        news_items_list.append(
            NewsItem(
                title=article.title,
                summary=summary,
                sentiment=sentiment,
                sentiment_label=sentiment_label,
                source=article.source,
                url=article.url,
                published_at=article.published_at,
            )
        )

    return NewsResponse(news=news_items_list, total=len(news_items_list))


@router.post("/fetch", response_model=NewsFetchResult)
async def fetch_news(
    session: AsyncSession = Depends(get_session),
    redis=Depends(get_redis_client),
) -> NewsFetchResult:
    """수동 뉴스 수집·분석 트리거.

    REQ-NEWS-FETCH-001/002/003: 수집 → 분석 순서 실행.
    실패 시 partial 결과 반환 (500 없음).
    인증 불필요.
    """
    result = await trigger_news_fetch(db=session, redis=redis)
    return NewsFetchResult(
        collected=result["collected"],
        analyzed=result["analyzed"],
    )
