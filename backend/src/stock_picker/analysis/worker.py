# 미분석 기사 배치 처리 워커
# REQ-AI-001: status='collected' 기사를 Claude로 분석
# REQ-AI-005: 분석 실패 시 격리 (analysis_failed 상태로 변경)

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .client import ClaudeAnalysisClient
from .schema import ClaudeAnalysisOutput
from ..db.models import AnalysisResult, Article

log = structlog.get_logger()


class AnalysisWorker:
    """미분석 기사 배치 처리 워커.

    # @MX:ANCHOR: [AUTO] 분석 파이프라인 실행 단위 - 스케줄러에서 호출됨
    # @MX:REASON: APScheduler에서 주기적으로 호출되는 핵심 배치 워커

    REQ-AI-001: status='collected' 기사를 순차 처리
    REQ-AI-005: 개별 기사 실패 시 격리, 전체 배치 중단 없음
    """

    def __init__(self, client: ClaudeAnalysisClient | None = None) -> None:
        self.client = client

    async def run(self, session: AsyncSession) -> dict[str, int]:
        """미분석 기사를 Claude로 분석.

        Args:
            session: 비동기 DB 세션

        Returns:
            {"analyzed": int, "failed": int} 처리 결과 카운트
        """
        articles = await self._get_unanalyzed(session)
        results = {"analyzed": 0, "failed": 0}

        for article in articles:
            output = await self.client.analyze(article.title, article.content or "")

            if output is not None:
                await self._save_analysis(session, article, output)
                article.status = "analyzed"
                results["analyzed"] += 1
            else:
                # 분석 실패: 격리 처리 (REQ-AI-005)
                article.status = "analysis_failed"
                results["failed"] += 1
                log.warning(
                    "기사 분석 실패 - 격리",
                    article_id=article.id,
                    title=article.title[:50],
                )

        await session.commit()
        return results

    async def _get_unanalyzed(self, session: AsyncSession) -> list[Article]:
        """status='collected'인 미분석 기사 조회.

        Args:
            session: 비동기 DB 세션

        Returns:
            미분석 기사 목록
        """
        stmt = select(Article).where(Article.status == "collected")
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def _save_analysis(
        self,
        session: AsyncSession,
        article: Article,
        output: ClaudeAnalysisOutput,
    ) -> None:
        """분석 결과를 analysis_results 테이블에 저장.

        Args:
            session: 비동기 DB 세션
            article: 분석 대상 기사
            output: Claude 분석 결과
        """
        analysis = AnalysisResult(
            article_id=article.id,
            sentiment=output.sentiment,
            sentiment_score=float(output.sentiment_score),
            sector_tags=output.sector_tags,
            keywords=output.keywords,
            summary=output.summary,
        )
        session.add(analysis)
        await session.flush()
