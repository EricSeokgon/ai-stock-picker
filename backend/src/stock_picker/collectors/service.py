# 수집 오케스트레이션 - 멱등 저장 + 부분 실패 처리
from typing import Callable, Awaitable

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseCollector, RawArticle
from .rss import HankyungCollector, MKCollector
from .naver import NaverCollector

log = structlog.get_logger()


class CollectorService:
    """4개 소스 수집 오케스트레이션.

    # @MX:ANCHOR: [AUTO] 수집 파이프라인 진입점 - 스케줄러에서 직접 호출됨
    # @MX:REASON: APScheduler, FastAPI lifespan, CLI에서 호출되는 공유 서비스

    REQ-NEWS-004: URL 중복 기사 멱등 저장
    REQ-NEWS-005: 소스별 실패 격리 - 전체 배치 중단 없음
    """

    def __init__(self) -> None:
        # 기본 수집기 목록
        self.collectors: dict[str, BaseCollector] = {
            "hankyung": HankyungCollector(),
            "mk": MKCollector(),
            "naver": NaverCollector(),
        }

    async def collect_all(self, session: AsyncSession) -> dict[str, int]:
        """모든 소스에서 수집. 실패한 소스는 스킵, 성공한 소스는 저장.

        Args:
            session: 비동기 DB 세션

        Returns:
            {소스명: 저장된 기사 수} 딕셔너리
        """
        results: dict[str, int] = {}

        for source_name, collector in self.collectors.items():
            count = await self._collect_with_error_isolation(
                source_name, collector.collect
            )

            if count > 0:
                # 수집 성공 시 저장
                try:
                    articles = await collector.collect()
                    saved = await self._save_articles(session, articles)
                    results[source_name] = saved
                except Exception as e:
                    log.error("저장 실패", source=source_name, error=str(e))
                    results[source_name] = 0
            else:
                results[source_name] = 0

        return results

    async def _collect_with_error_isolation(
        self,
        source_name: str,
        collect_fn: Callable[[], Awaitable[list[RawArticle]]],
    ) -> int:
        """단일 소스 수집 - 실패 격리.

        REQ-NEWS-005: 소스별 실패는 해당 소스만 영향. 전체 중단 없음.

        Returns:
            수집된 기사 수. 실패 시 0 반환.
        """
        try:
            articles = await collect_fn()
            return len(articles)
        except Exception as e:
            # 소스별 실패 격리 - 전체 배치 중단 없음
            log.error("수집 실패", source=source_name, error=str(e))
            return 0

    async def _save_articles(
        self, session: AsyncSession, articles: list[RawArticle]
    ) -> int:
        """멱등 저장 - URL 중복 시 스킵.

        REQ-NEWS-004: PostgreSQL INSERT ... ON CONFLICT DO NOTHING 사용.

        Returns:
            새로 저장된 기사 수 (중복 제외)
        """
        if not articles:
            return 0

        saved_count = 0

        for article in articles:
            # ON CONFLICT DO NOTHING으로 URL 중복 자동 처리
            stmt = text(
                """
                INSERT INTO articles (url, source, title, content, published_at, status)
                VALUES (:url, :source, :title, :content, :published_at, 'collected')
                ON CONFLICT (url) DO NOTHING
                """
            )
            result = await session.execute(
                stmt,
                {
                    "url": article.url,
                    "source": article.source,
                    "title": article.title,
                    "content": article.content,
                    "published_at": article.published_at,
                },
            )
            # rowcount > 0이면 실제 삽입됨
            if result.rowcount and result.rowcount > 0:
                saved_count += 1

        return saved_count
