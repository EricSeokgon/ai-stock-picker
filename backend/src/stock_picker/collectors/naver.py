# 네이버 금융 RSS 수집기
import httpx
import structlog

from .base import BaseCollector, RawArticle
from .rss import parse_rss_feed

log = structlog.get_logger()


class NaverCollector(BaseCollector):
    """네이버 금융 뉴스 RSS 수집기.

    네이버 금융 RSS 엔드포인트에서 주요 금융 뉴스를 수집한다.
    REQ-NEWS-006: User-Agent 헤더 포함.
    """

    RSS_URL = "https://finance.naver.com/news/news_list.naver"

    async def collect(self) -> list[RawArticle]:
        """네이버 금융 뉴스 RSS 수집.

        Returns:
            수집된 기사 목록. HTTP 오류 시 빈 리스트 반환.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.RSS_URL,
                    headers={"User-Agent": self.USER_AGENT},
                    timeout=30.0,
                )
                response.raise_for_status()
                return parse_rss_feed(response.content, source="naver")
        except Exception as e:
            log.error("네이버 RSS 수집 실패", error=str(e))
            return []
