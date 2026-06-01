# 연합뉴스 경제 RSS 수집기 (네이버 금융은 RSS 미지원으로 연합뉴스로 대체)
import httpx
import structlog

from .base import BaseCollector, RawArticle
from .rss import parse_rss_feed

log = structlog.get_logger()


class NaverCollector(BaseCollector):
    """연합뉴스 경제 RSS 수집기.

    연합뉴스 경제 섹션 RSS에서 금융 뉴스를 수집한다.
    REQ-NEWS-006: User-Agent 헤더 포함.
    """

    # 연합뉴스 경제 RSS (네이버 금융 RSS 미지원으로 대체)
    RSS_URL = "https://www.yna.co.kr/rss/economy.xml"

    async def collect(self) -> list[RawArticle]:
        """연합뉴스 경제 RSS 수집.

        Returns:
            수집된 기사 목록. HTTP 오류 시 빈 리스트 반환.
        """
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(
                    self.RSS_URL,
                    headers={"User-Agent": self.USER_AGENT},
                    timeout=30.0,
                )
                response.raise_for_status()
                return parse_rss_feed(response.content, source="yonhap")
        except Exception as e:
            log.error("연합뉴스 RSS 수집 실패", error=str(e))
            return []
