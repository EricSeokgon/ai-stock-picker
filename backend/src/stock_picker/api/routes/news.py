# 뉴스 피드 엔드포인트 - 분석 완료 기사 최신 N개 반환

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from stock_picker.api.schemas import NewsItem, NewsResponse
from stock_picker.db.models import Article
from stock_picker.db.session import get_session

router = APIRouter(prefix="/news", tags=["news"])


@router.get("", response_model=NewsResponse)
async def get_news(
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
) -> NewsResponse:
    """최신 뉴스 피드 반환.

    분석 완료 기사(analysis_results 존재)만 대상으로 한다 (REQ-WEB-004).
    """
    # collected 기사도 포함 (analyzed 우선, analyzed 없으면 수집 기사 표시)
    stmt = (
        select(Article)
        .options(selectinload(Article.analysis_results))
        .where(Article.status.in_(["analyzed", "collected"]))
        .order_by(desc(Article.published_at))
        .limit(limit)
    )
    result = await session.execute(stmt)
    articles = result.scalars().all()

    news_items: list[NewsItem] = []
    for article in articles:
        # 분석 결과에서 첫 번째 항목 사용
        analysis = article.analysis_results[0] if article.analysis_results else None
        sentiment = analysis.sentiment if analysis else None
        summary = analysis.summary if analysis else None

        # sentiment_label: analysis_results에 저장된 5단계 라벨 (TASK-009)
        # getattr 사용 — 구 스키마 호환성 보장 (sentiment_label 컬럼 없는 경우 None)
        _label_raw = getattr(analysis, "sentiment_label", None) if analysis else None
        sentiment_label = str(_label_raw) if isinstance(_label_raw, str) else None

        news_items.append(
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

    return NewsResponse(news=news_items, total=len(news_items))
