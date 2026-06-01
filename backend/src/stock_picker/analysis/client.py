# Claude API 클라이언트 - 재시도 및 스키마 검증
# REQ-AI-003: Rate limit 시 지수 백오프로 최대 3회 재시도
# REQ-AI-004: 스키마 위반 응답은 실패 처리
import asyncio
import json

import anthropic
import structlog
from pydantic import ValidationError

from .prompt import SYSTEM_PROMPT, build_user_message
from .schema import ClaudeAnalysisOutput

log = structlog.get_logger()


class ClaudeAnalysisClient:
    """Claude API 비동기 클라이언트.

    # @MX:ANCHOR: [AUTO] Claude API 호출 단일 진입점 - 워커에서 직접 호출됨
    # @MX:REASON: AnalysisWorker에서 호출. Rate limit 재시도 로직 포함.

    REQ-AI-003: Rate limit/스키마 오류 시 3회 재시도 (지수 백오프)
    REQ-AI-005: 실패 시 None 반환 (파이프라인 중단 없음)
    """

    MAX_RETRIES = 3
    RETRY_BASE_DELAY = 1.0  # 초 (지수 백오프 기준)

    def __init__(self, api_key: str) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def analyze(
        self, title: str, content: str
    ) -> ClaudeAnalysisOutput | None:
        """기사 분석 요청.

        # @MX:WARN: [AUTO] 재시도 루프 - 최대 3회 호출 가능
        # @MX:REASON: Rate limit 상황에서 최대 3회 * 지수 지연 발생

        Args:
            title: 기사 제목
            content: 기사 본문

        Returns:
            분석 결과. 재시도 후에도 실패하면 None 반환.
        """
        user_message = build_user_message(title, content)

        for attempt in range(self.MAX_RETRIES):
            try:
                message = await self._client.messages.create(
                    model="claude-haiku-4-5",
                    max_tokens=512,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": user_message}],
                )

                # 응답 텍스트 추출
                response_text = message.content[0].text

                # JSON 파싱 시도
                data = json.loads(response_text)

                # Pydantic v2로 스키마 검증
                return ClaudeAnalysisOutput.model_validate(data)

            except anthropic.RateLimitError as e:
                # Rate limit: 지수 백오프 후 재시도
                if attempt < self.MAX_RETRIES - 1:
                    delay = self.RETRY_BASE_DELAY * (2 ** attempt)
                    log.warning(
                        "Rate limit 발생, 재시도",
                        attempt=attempt + 1,
                        delay=delay,
                        error=str(e),
                    )
                    await asyncio.sleep(delay)
                    continue
                log.error("Rate limit - 최대 재시도 초과", error=str(e))
                return None

            except (json.JSONDecodeError, ValidationError) as e:
                # 스키마 위반: 재시도 처리
                if attempt < self.MAX_RETRIES - 1:
                    delay = self.RETRY_BASE_DELAY * (2 ** attempt)
                    log.warning(
                        "응답 파싱 실패, 재시도",
                        attempt=attempt + 1,
                        delay=delay,
                        error=str(e),
                    )
                    await asyncio.sleep(delay)
                    continue
                log.error("응답 파싱 실패 - 최대 재시도 초과", error=str(e))
                return None

            except Exception as e:
                log.error("Claude API 예상치 못한 오류", error=str(e))
                return None

        return None
