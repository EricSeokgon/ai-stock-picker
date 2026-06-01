# RSS 수집기 - xml.etree.ElementTree(stdlib)로 XML 파싱
# feedparser 미사용: stdlib만으로 의존성 최소화
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime

import httpx
import structlog

from .base import BaseCollector, RawArticle

log = structlog.get_logger()

# RSS pubDate 파싱 실패 시 사용할 기본값
_FALLBACK_DATE = None


def parse_rss_feed(xml_content: bytes, source: str) -> list[RawArticle]:
    """RSS XML 바이트를 파싱하여 RawArticle 목록 반환.

    # @MX:ANCHOR: [AUTO] 수집 파이프라인 진입점 - 다수의 수집기에서 호출됨
    # @MX:REASON: HankyungCollector, MKCollector, NaverCollector에서 공유 사용

    Args:
        xml_content: RSS XML 원문 바이트
        source: 뉴스 소스 이름 (예: "hankyung", "naver")

    Returns:
        파싱된 기사 목록. 파싱 오류 시 빈 리스트 반환.
    """
    if not xml_content:
        return []

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        # 잘못된 XML → 크래시 없이 빈 리스트 반환
        log.warning("RSS XML 파싱 실패", source=source, error=str(e))
        return []

    articles: list[RawArticle] = []

    # RSS 표준: <rss><channel><item>... 구조
    # Atom 형식도 감안하여 channel 없이 직접 item 검색
    items = root.findall(".//item")

    for item in items:
        title = _get_text(item, "title")
        url = _get_text(item, "link")
        content = _get_text(item, "description") or ""
        pub_date_str = _get_text(item, "pubDate")

        # URL 또는 title 없으면 스킵
        if not url or not title:
            continue

        published_at = _parse_pub_date(pub_date_str, source)

        articles.append(
            RawArticle(
                url=url.strip(),
                title=title.strip(),
                content=content.strip(),
                source=source,
                published_at=published_at,
            )
        )

    return articles


def _get_text(element: ET.Element, tag: str) -> str | None:
    """XML 요소에서 텍스트 추출. 없으면 None 반환."""
    child = element.find(tag)
    if child is not None and child.text:
        return child.text.strip()
    return None


def _parse_pub_date(date_str: str | None, source: str) -> datetime | None:
    """RSS pubDate 문자열을 datetime으로 파싱.

    RFC 2822 형식 (예: "Sun, 01 Jun 2026 06:00:00 +0900")을 처리한다.
    """
    if not date_str:
        return None
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        log.warning("pubDate 파싱 실패", source=source, date_str=date_str)
        return None


class HankyungCollector(BaseCollector):
    """한국경제신문 RSS 수집기"""

    RSS_URL = "https://www.hankyung.com/feed/finance"

    async def collect(self) -> list[RawArticle]:
        """한국경제 금융 RSS 수집."""
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(
                    self.RSS_URL,
                    headers={"User-Agent": self.USER_AGENT},
                    timeout=30.0,
                )
                response.raise_for_status()
                return parse_rss_feed(response.content, source="hankyung")
        except Exception as e:
            log.error("한국경제 RSS 수집 실패", error=str(e))
            return []


class MKCollector(BaseCollector):
    """매일경제 RSS 수집기"""

    RSS_URL = "https://www.mk.co.kr/rss/30000001/"

    async def collect(self) -> list[RawArticle]:
        """매일경제 RSS 수집."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.RSS_URL,
                    headers={"User-Agent": self.USER_AGENT},
                    timeout=30.0,
                )
                response.raise_for_status()
                return parse_rss_feed(response.content, source="mk")
        except Exception as e:
            log.error("매일경제 RSS 수집 실패", error=str(e))
            return []
