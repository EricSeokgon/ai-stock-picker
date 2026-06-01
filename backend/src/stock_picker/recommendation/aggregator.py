# 종목별 뉴스 감성/볼륨 집계
from datetime import date
from typing import Any

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import AnalysisResult, Article, StockMention

log = structlog.get_logger()


class StockAggregator:
    """종목별 뉴스 감성 점수 및 볼륨 집계.

    # @MX:ANCHOR: [AUTO] 추천 파이프라인 집계 단계 - 추천 서비스에서 호출됨
    # @MX:REASON: RecommendationService.run()에서 단독 호출
    """

    async def aggregate(
        self, session: AsyncSession, trade_date: date
    ) -> dict[str, dict[str, Any]]:
        """종목별 감성 점수 및 뉴스 볼륨 집계.

        Args:
            session: 비동기 DB 세션
            trade_date: 집계 기준 날짜

        Returns:
            {krx_code: {"avg_sentiment": float, "news_count": int, "top_summary": str}}
        """
        # 당일 분석 완료된 기사의 종목 언급 집계
        # StockMention → AnalysisResult → Article 조인
        stmt = (
            select(
                StockMention.krx_code,
                func.avg(AnalysisResult.sentiment_score).label("avg_sentiment"),
                func.count(StockMention.id).label("news_count"),
                func.max(AnalysisResult.summary).label("top_summary"),
            )
            .join(Article, StockMention.article_id == Article.id)
            .join(AnalysisResult, AnalysisResult.article_id == Article.id)
            .where(
                StockMention.krx_code.isnot(None),
                StockMention.mention_status == "mapped",
                Article.status == "analyzed",
            )
            .group_by(StockMention.krx_code)
        )

        result = await session.execute(stmt)
        rows = result.all()

        aggregated: dict[str, dict[str, Any]] = {}
        for row in rows:
            if row.krx_code:
                aggregated[row.krx_code] = {
                    "avg_sentiment": float(row.avg_sentiment or 0.0),
                    "news_count": int(row.news_count or 0),
                    "top_summary": row.top_summary or "",
                }

        return aggregated
