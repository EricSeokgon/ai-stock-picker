# 미분석 기사 배치 처리 워커
# REQ-AI-001: status='collected' 기사를 Claude로 분석
# REQ-AI-004: 배치 처리로 Claude API 호출 횟수 감소 (BATCH_SIZE개씩 묶음)
# REQ-AI-005: 분석 실패 시 격리 (analysis_failed 상태로 변경)
import math

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .client import ClaudeAnalysisClient
from .schema import ClaudeAnalysisOutput
from .sentiment_label import score_to_label
from ..db.models import AnalysisResult, Article

log = structlog.get_logger()

# 기사 5개를 단일 Claude 호출로 묶음 (REQ-AI-004)
# @MX:NOTE: [AUTO] BATCH_SIZE=5는 Claude API 비용 절감을 위한 최적값
# 1~10 범위 내에서 조정 가능하나 너무 크면 응답 오류율 증가
BATCH_SIZE = 5


class AnalysisWorker:
    """미분석 기사 배치 처리 워커.

    # @MX:ANCHOR: [AUTO] 분석 파이프라인 실행 단위 - 스케줄러에서 호출됨
    # @MX:REASON: APScheduler에서 주기적으로 호출되는 핵심 배치 워커

    REQ-AI-001: status='collected' 기사를 순차 처리
    REQ-AI-004: BATCH_SIZE개씩 묶어 Claude 호출 (run_batch)
    REQ-AI-005: 개별 기사 실패 시 격리, 전체 배치 중단 없음
    """

    def __init__(self, client: ClaudeAnalysisClient | None = None) -> None:
        self.client = client

    async def run(self, session: AsyncSession) -> dict[str, int]:
        """미분석 기사를 Claude로 분석 (개별 처리).

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

    async def run_batch(self, session: AsyncSession) -> dict[str, int]:
        """미분석 기사를 BATCH_SIZE개씩 묶어 Claude로 분석 (REQ-AI-004).

        # @MX:WARN: [AUTO] 배치 실패 시 개별 처리로 폴백 - 복잡한 제어 흐름
        # @MX:REASON: 부분 실패 격리 계약 유지를 위해 폴백 로직 필요

        배치 분석 실패(None 반환) 시 해당 배치의 기사들을 개별 처리로 폴백한다.

        Args:
            session: 비동기 DB 세션

        Returns:
            {"analyzed": int, "failed": int} 처리 결과 카운트
        """
        articles = await self._get_unanalyzed(session)
        results = {"analyzed": 0, "failed": 0}

        if not articles:
            await session.commit()
            return results

        # BATCH_SIZE개씩 배치로 나누어 처리
        total_batches = math.ceil(len(articles) / BATCH_SIZE)
        for batch_idx in range(total_batches):
            start = batch_idx * BATCH_SIZE
            end = start + BATCH_SIZE
            batch = articles[start:end]

            # 배치 단위 Claude 호출
            batch_inputs = [(a.title, a.content or "") for a in batch]
            outputs = await self.client.analyze_batch(batch_inputs)

            if outputs is None:
                # 배치 실패 → 개별 폴백 (REQ-AI-005 격리 계약 유지)
                log.warning(
                    "배치 분석 실패 - 개별 처리로 폴백",
                    batch_idx=batch_idx,
                    batch_size=len(batch),
                )
                for article in batch:
                    output = await self.client.analyze(article.title, article.content or "")
                    if output is not None:
                        await self._save_analysis(session, article, output)
                        article.status = "analyzed"
                        results["analyzed"] += 1
                    else:
                        article.status = "analysis_failed"
                        results["failed"] += 1
                        log.warning("개별 폴백 분석 실패 - 격리", article_id=article.id)
            else:
                # 배치 성공 → 결과 매핑
                for article, output in zip(batch, outputs):
                    if output is not None:
                        await self._save_analysis(session, article, output)
                        article.status = "analyzed"
                        results["analyzed"] += 1
                    else:
                        article.status = "analysis_failed"
                        results["failed"] += 1
                        log.warning("배치 내 기사 분석 실패 - 격리", article_id=article.id)

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
            # 감성 점수 → 5단계 라벨 변환 (TASK-008)
            sentiment_label=score_to_label(float(output.sentiment_score)),
            sector_tags=output.sector_tags,
            keywords=output.keywords,
            summary=output.summary,
        )
        session.add(analysis)
        await session.flush()
