# explanation.py 단위 테스트 — Claude API 목 처리
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from stock_picker.recommendation.explanation import generate_explanation


# 공통 스코어 픽스처
SCORE_BREAKDOWN = {
    "sentiment_score": 0.75,
    "volume_score": 0.5,
    "momentum_score": 0.6,
    "anomaly_score": 0.3,
}


class TestGenerateExplanation:
    """generate_explanation 함수 단위 테스트"""

    @pytest.mark.asyncio
    async def test_success_returns_text(self):
        """API 성공 시 텍스트 문자열 반환"""
        import anthropic as _anthropic

        expected_text = "이 종목은 감성 분석 점수가 높아 긍정적 뉴스 흐름을 보입니다."

        mock_content = MagicMock()
        mock_content.text = expected_text

        mock_message = MagicMock()
        mock_message.content = [mock_content]

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_message)

        with patch.object(_anthropic, "AsyncAnthropic", return_value=mock_client):
            result = await generate_explanation(
                krx_code="005930",
                score_breakdown=SCORE_BREAKDOWN,
                top_summary="반도체 업황 회복 기대감 확산",
                api_key="test-key",
            )

        assert result == expected_text

    @pytest.mark.asyncio
    async def test_api_error_returns_none(self):
        """API 오류 시 None 반환 (예외 전파 금지)"""
        import anthropic as _anthropic

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            side_effect=_anthropic.APIConnectionError(request=MagicMock())
        )

        with patch.object(_anthropic, "AsyncAnthropic", return_value=mock_client):
            result = await generate_explanation(
                krx_code="005930",
                score_breakdown=SCORE_BREAKDOWN,
                top_summary="",
                api_key="test-key",
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_timeout_returns_none(self):
        """타임아웃(APITimeoutError) 발생 시 None 반환"""
        import anthropic as _anthropic

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            side_effect=_anthropic.APITimeoutError(request=MagicMock())
        )

        with patch.object(_anthropic, "AsyncAnthropic", return_value=mock_client):
            result = await generate_explanation(
                krx_code="000660",
                score_breakdown=SCORE_BREAKDOWN,
                top_summary="",
                api_key="test-key",
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_missing_api_key_returns_none(self):
        """API 키 미설정 시 None 반환 (ANTHROPIC_API_KEY 환경변수 없음)"""
        import os
        saved = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            result = await generate_explanation(
                krx_code="035420",
                score_breakdown=SCORE_BREAKDOWN,
                top_summary="",
                api_key="",
            )
        finally:
            if saved is not None:
                os.environ["ANTHROPIC_API_KEY"] = saved

        assert result is None

    @pytest.mark.asyncio
    async def test_rate_limit_error_returns_none(self):
        """RateLimitError 시 None 반환"""
        import anthropic as _anthropic

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            side_effect=_anthropic.RateLimitError(
                message="rate limited",
                response=MagicMock(status_code=429, headers={}),
                body={},
            )
        )

        with patch.object(_anthropic, "AsyncAnthropic", return_value=mock_client):
            result = await generate_explanation(
                krx_code="051910",
                score_breakdown=SCORE_BREAKDOWN,
                top_summary="",
                api_key="test-key",
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_empty_top_summary_still_works(self):
        """top_summary가 빈 문자열이어도 정상 동작"""
        import anthropic as _anthropic

        expected_text = "거래량 점수가 높고 모멘텀이 양호합니다."

        mock_content = MagicMock()
        mock_content.text = expected_text

        mock_message = MagicMock()
        mock_message.content = [mock_content]

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_message)

        with patch.object(_anthropic, "AsyncAnthropic", return_value=mock_client):
            result = await generate_explanation(
                krx_code="005930",
                score_breakdown=SCORE_BREAKDOWN,
                top_summary="",
                api_key="test-key",
            )

        assert result == expected_text

    @pytest.mark.asyncio
    async def test_generic_exception_returns_none(self):
        """예상치 못한 예외도 None 반환 (파이프라인 보호)"""
        import anthropic as _anthropic

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            side_effect=RuntimeError("unexpected error")
        )

        with patch.object(_anthropic, "AsyncAnthropic", return_value=mock_client):
            result = await generate_explanation(
                krx_code="005380",
                score_breakdown=SCORE_BREAKDOWN,
                top_summary="",
                api_key="test-key",
            )

        assert result is None
