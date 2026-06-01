# Claude API 클라이언트 단위 테스트
# unittest.mock으로 anthropic SDK mock

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# 픽스처 파일 경로
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def claude_response_json():
    """Claude API 응답 픽스처 JSON 로드"""
    return json.loads((FIXTURES_DIR / "claude_response.json").read_text())


@pytest.fixture
def mock_anthropic_message(claude_response_json):
    """정상 응답 Mock Anthropic Message 객체 생성"""
    message = MagicMock()
    message.content = [MagicMock()]
    message.content[0].text = json.dumps(claude_response_json)
    return message


class TestClaudeAnalysisClientNormalResponse:
    """정상 응답 처리 테스트"""

    @pytest.mark.asyncio
    async def test_analyze_returns_claude_output_on_success(self, mock_anthropic_message):
        """정상 응답 → ClaudeAnalysisOutput 파싱 성공"""
        from stock_picker.analysis.client import ClaudeAnalysisClient
        from stock_picker.analysis.schema import ClaudeAnalysisOutput

        with patch("anthropic.AsyncAnthropic") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value = mock_client
            mock_client.messages.create = AsyncMock(return_value=mock_anthropic_message)

            client = ClaudeAnalysisClient(api_key="test-key")
            result = await client.analyze("삼성전자 실적", "삼성전자가 2분기...")

        assert result is not None
        assert isinstance(result, ClaudeAnalysisOutput)
        assert result.sentiment == "positive"
        assert result.sentiment_score == 0.72

    @pytest.mark.asyncio
    async def test_analyze_parses_all_fields(self, mock_anthropic_message):
        """모든 필드가 올바르게 파싱되는지 확인"""
        from stock_picker.analysis.client import ClaudeAnalysisClient

        with patch("anthropic.AsyncAnthropic") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value = mock_client
            mock_client.messages.create = AsyncMock(return_value=mock_anthropic_message)

            client = ClaudeAnalysisClient(api_key="test-key")
            result = await client.analyze("테스트 제목", "테스트 내용")

        assert result.sector_tags == ["반도체", "수출"]
        assert result.keywords == ["삼성전자", "HBM", "실적"]
        assert "삼성전자" in result.summary


class TestClaudeAnalysisClientRateLimit:
    """속도 제한 오류 재시도 테스트"""

    @pytest.mark.asyncio
    async def test_rate_limit_retries_3_times_then_returns_none(self):
        """Rate limit 오류 → 3회 재시도 후 None 반환"""
        import anthropic
        from stock_picker.analysis.client import ClaudeAnalysisClient

        call_count = 0

        async def raise_rate_limit(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise anthropic.RateLimitError(
                "rate limit", response=MagicMock(status_code=429), body={}
            )

        with patch("anthropic.AsyncAnthropic") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value = mock_client
            mock_client.messages.create = raise_rate_limit

            # 재시도 지연 없이 테스트하기 위해 sleep mock
            with patch("asyncio.sleep", new_callable=AsyncMock):
                client = ClaudeAnalysisClient(api_key="test-key")
                result = await client.analyze("제목", "내용")

        assert result is None
        assert call_count == 3  # MAX_RETRIES = 3

    @pytest.mark.asyncio
    async def test_rate_limit_uses_exponential_backoff(self):
        """지수 백오프 적용 확인 (1s, 2s)"""
        import anthropic
        from stock_picker.analysis.client import ClaudeAnalysisClient

        sleep_calls = []

        async def track_sleep(delay):
            sleep_calls.append(delay)

        async def raise_rate_limit(*args, **kwargs):
            raise anthropic.RateLimitError(
                "rate limit", response=MagicMock(status_code=429), body={}
            )

        with patch("anthropic.AsyncAnthropic") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value = mock_client
            mock_client.messages.create = raise_rate_limit

            with patch("asyncio.sleep", side_effect=track_sleep):
                client = ClaudeAnalysisClient(api_key="test-key")
                await client.analyze("제목", "내용")

        # 첫 재시도: 1s, 두 번째 재시도: 2s
        assert len(sleep_calls) == 2
        assert sleep_calls[0] == 1.0
        assert sleep_calls[1] == 2.0


class TestClaudeAnalysisClientSchemaViolation:
    """스키마 위반 응답 처리 테스트"""

    @pytest.mark.asyncio
    async def test_invalid_schema_retries_and_returns_none(self):
        """스키마 위반 응답 → 재시도 후 None 반환"""
        from stock_picker.analysis.client import ClaudeAnalysisClient

        # sentiment 값이 잘못된 응답
        invalid_response = MagicMock()
        invalid_response.content = [MagicMock()]
        invalid_response.content[0].text = '{"sentiment": "invalid_value", "sentiment_score": 0.5, "sector_tags": [], "keywords": [], "summary": "테스트"}'

        with patch("anthropic.AsyncAnthropic") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value = mock_client
            mock_client.messages.create = AsyncMock(return_value=invalid_response)

            with patch("asyncio.sleep", new_callable=AsyncMock):
                client = ClaudeAnalysisClient(api_key="test-key")
                result = await client.analyze("제목", "내용")

        assert result is None

    @pytest.mark.asyncio
    async def test_non_json_response_retries_and_returns_none(self):
        """JSON이 아닌 응답 → 재시도 후 None 반환"""
        from stock_picker.analysis.client import ClaudeAnalysisClient

        non_json_response = MagicMock()
        non_json_response.content = [MagicMock()]
        non_json_response.content[0].text = "죄송합니다. 분석할 수 없습니다."

        with patch("anthropic.AsyncAnthropic") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value = mock_client
            mock_client.messages.create = AsyncMock(return_value=non_json_response)

            with patch("asyncio.sleep", new_callable=AsyncMock):
                client = ClaudeAnalysisClient(api_key="test-key")
                result = await client.analyze("제목", "내용")

        assert result is None
