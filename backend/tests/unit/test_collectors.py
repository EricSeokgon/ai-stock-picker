# RSS 수집기 단위 테스트
# respx로 HTTP 요청 mock

import pytest
import respx
import httpx
from datetime import datetime
from pathlib import Path

# 픽스처 파일 경로
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestParseRssFeed:
    """parse_rss_feed 함수 단위 테스트"""

    def test_parse_valid_rss_returns_articles(self):
        """유효한 RSS XML에서 기사 목록 반환"""
        from stock_picker.collectors.rss import parse_rss_feed

        xml_content = (FIXTURES_DIR / "sample_rss.xml").read_bytes()
        articles = parse_rss_feed(xml_content, source="hankyung")

        # 두 개 기사가 파싱되어야 함
        assert len(articles) == 2

    def test_parse_rss_extracts_title(self):
        """title 필드 추출 확인"""
        from stock_picker.collectors.rss import parse_rss_feed

        xml_content = (FIXTURES_DIR / "sample_rss.xml").read_bytes()
        articles = parse_rss_feed(xml_content, source="hankyung")

        assert articles[0].title == "삼성전자, 2분기 실적 예상 상회"
        assert articles[1].title == "SK하이닉스 HBM 수출 증가"

    def test_parse_rss_extracts_url(self):
        """url 필드 추출 확인"""
        from stock_picker.collectors.rss import parse_rss_feed

        xml_content = (FIXTURES_DIR / "sample_rss.xml").read_bytes()
        articles = parse_rss_feed(xml_content, source="hankyung")

        assert articles[0].url == "https://www.hankyung.com/news/article/2026060101"

    def test_parse_rss_extracts_content(self):
        """content(description) 필드 추출 확인"""
        from stock_picker.collectors.rss import parse_rss_feed

        xml_content = (FIXTURES_DIR / "sample_rss.xml").read_bytes()
        articles = parse_rss_feed(xml_content, source="hankyung")

        assert "삼성전자" in articles[0].content
        assert "HBM" in articles[0].content

    def test_parse_rss_extracts_published_at(self):
        """published_at 날짜 파싱 확인"""
        from stock_picker.collectors.rss import parse_rss_feed

        xml_content = (FIXTURES_DIR / "sample_rss.xml").read_bytes()
        articles = parse_rss_feed(xml_content, source="hankyung")

        assert isinstance(articles[0].published_at, datetime)
        assert articles[0].published_at.year == 2026

    def test_parse_rss_sets_source(self):
        """source 필드가 파라미터 값으로 설정되는지 확인"""
        from stock_picker.collectors.rss import parse_rss_feed

        xml_content = (FIXTURES_DIR / "sample_rss.xml").read_bytes()
        articles = parse_rss_feed(xml_content, source="hankyung")

        assert articles[0].source == "hankyung"

    def test_parse_invalid_xml_returns_empty_list(self):
        """잘못된 XML → 빈 리스트 반환 (크래시 없음)"""
        from stock_picker.collectors.rss import parse_rss_feed

        invalid_xml = b"<not valid xml <<<"
        articles = parse_rss_feed(invalid_xml, source="test")

        assert articles == []

    def test_parse_empty_xml_returns_empty_list(self):
        """빈 XML → 빈 리스트 반환"""
        from stock_picker.collectors.rss import parse_rss_feed

        empty_xml = b""
        articles = parse_rss_feed(empty_xml, source="test")

        assert articles == []

    def test_parse_rss_no_items_returns_empty_list(self):
        """아이템 없는 RSS → 빈 리스트 반환"""
        from stock_picker.collectors.rss import parse_rss_feed

        no_items_xml = (
            b'<?xml version="1.0" encoding="UTF-8"?>'
            b"<rss version=\"2.0\"><channel><title>Test</title></channel></rss>"
        )
        articles = parse_rss_feed(no_items_xml, source="test")

        assert articles == []


class TestNaverCollectorHTTP:
    """네이버 수집기 HTTP 요청 테스트"""

    @pytest.mark.asyncio
    async def test_naver_collector_sends_get_request(self):
        """네이버 RSS 엔드포인트로 HTTP GET 요청 전송 확인"""
        from stock_picker.collectors.naver import NaverCollector

        xml_content = (FIXTURES_DIR / "sample_rss.xml").read_bytes()

        with respx.mock:
            route = respx.get("https://finance.naver.com/news/news_list.naver").mock(
                return_value=httpx.Response(200, content=xml_content)
            )
            collector = NaverCollector()
            await collector.collect()

            # GET 요청이 전송되었는지 확인
            assert route.called

    @pytest.mark.asyncio
    async def test_naver_collector_sends_user_agent(self):
        """REQ-NEWS-006: User-Agent 헤더가 설정되어 있는지 확인"""
        from stock_picker.collectors.naver import NaverCollector
        from stock_picker.collectors.base import BaseCollector

        xml_content = (FIXTURES_DIR / "sample_rss.xml").read_bytes()

        with respx.mock:
            route = respx.get("https://finance.naver.com/news/news_list.naver").mock(
                return_value=httpx.Response(200, content=xml_content)
            )
            collector = NaverCollector()
            await collector.collect()

            # 요청 헤더에 User-Agent가 있는지 확인
            request = route.calls[0].request
            assert "User-Agent" in request.headers
            assert BaseCollector.USER_AGENT in request.headers["User-Agent"]

    @pytest.mark.asyncio
    async def test_naver_collector_returns_articles(self):
        """네이버 수집기가 기사 목록을 반환하는지 확인"""
        from stock_picker.collectors.naver import NaverCollector

        xml_content = (FIXTURES_DIR / "sample_rss.xml").read_bytes()

        with respx.mock:
            respx.get("https://finance.naver.com/news/news_list.naver").mock(
                return_value=httpx.Response(200, content=xml_content)
            )
            collector = NaverCollector()
            articles = await collector.collect()

            assert len(articles) == 2
            assert articles[0].source == "naver"

    @pytest.mark.asyncio
    async def test_naver_collector_http_error_returns_empty(self):
        """HTTP 오류 시 빈 리스트 반환 (크래시 없음)"""
        from stock_picker.collectors.naver import NaverCollector

        with respx.mock:
            respx.get("https://finance.naver.com/news/news_list.naver").mock(
                return_value=httpx.Response(500)
            )
            collector = NaverCollector()
            articles = await collector.collect()

            assert articles == []


class TestHankyungCollectorHTTP:
    """한국경제 수집기 HTTP 요청 테스트"""

    @pytest.mark.asyncio
    async def test_hankyung_collector_sends_user_agent(self):
        """REQ-NEWS-006: User-Agent 헤더 설정 확인"""
        from stock_picker.collectors.rss import HankyungCollector
        from stock_picker.collectors.base import BaseCollector

        xml_content = (FIXTURES_DIR / "sample_rss.xml").read_bytes()

        with respx.mock:
            route = respx.get("https://rss.hankyung.com/feed/finance.xml").mock(
                return_value=httpx.Response(200, content=xml_content)
            )
            collector = HankyungCollector()
            await collector.collect()

            request = route.calls[0].request
            assert "User-Agent" in request.headers
            assert BaseCollector.USER_AGENT in request.headers["User-Agent"]

    @pytest.mark.asyncio
    async def test_hankyung_collector_returns_articles(self):
        """한국경제 수집기 기사 목록 반환 확인"""
        from stock_picker.collectors.rss import HankyungCollector

        xml_content = (FIXTURES_DIR / "sample_rss.xml").read_bytes()

        with respx.mock:
            respx.get("https://rss.hankyung.com/feed/finance.xml").mock(
                return_value=httpx.Response(200, content=xml_content)
            )
            collector = HankyungCollector()
            articles = await collector.collect()

            assert len(articles) == 2
            assert articles[0].source == "hankyung"
