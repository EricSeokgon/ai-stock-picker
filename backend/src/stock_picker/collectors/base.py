# 뉴스 수집기 추상 인터페이스 - 모든 소스별 수집기의 기반 클래스
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class RawArticle:
    """수집된 뉴스 원문 데이터"""

    url: str
    title: str
    content: str
    source: str
    published_at: datetime | None


class BaseCollector(ABC):
    """뉴스 소스별 수집기 기본 클래스.

    모든 수집기는 이 클래스를 상속하고 collect()를 구현해야 한다.
    REQ-NEWS-006: User-Agent 헤더를 항상 포함해야 함.
    """

    # REQ-NEWS-006: 모든 HTTP 요청에 User-Agent 헤더 포함
    USER_AGENT = "StockPickerBot/1.0 (research tool)"

    @abstractmethod
    async def collect(self) -> list[RawArticle]:
        """뉴스 기사 수집 후 RawArticle 목록 반환.

        실패 시 빈 리스트 반환 (예외 전파 금지).
        """
        ...
