# Claude Haiku로 한국어 추천 근거 텍스트 생성
# TASK-002: 실패 시 None 반환 — 절대 예외 전파 금지 (파이프라인 중단 방지)
from __future__ import annotations

import os
from typing import Any

import structlog

log = structlog.get_logger()

# 추천 근거 생성에 사용할 Claude 모델
# @MX:NOTE: [AUTO] claude-haiku-4-5 사용 — 근거 생성은 저비용 모델로 충분
_MODEL = "claude-haiku-4-5"
_MAX_TOKENS = 200


def _build_prompt(
    krx_code: str,
    score_breakdown: dict[str, Any],
    top_summary: str,
) -> str:
    """추천 근거 생성용 프롬프트 구성.

    Args:
        krx_code: KRX 종목코드
        score_breakdown: 점수 구성 딕셔너리 (sentiment_score 등)
        top_summary: 상위 기사 요약 텍스트

    Returns:
        사용자 메시지 문자열
    """
    sentiment = round(float(score_breakdown.get("sentiment_score", 0.0)), 3)
    volume = round(float(score_breakdown.get("volume_score", 0.0)), 3)
    momentum = round(float(score_breakdown.get("momentum_score", 0.0)), 3)
    anomaly = round(float(score_breakdown.get("anomaly_score", 0.0)), 3)

    summary_part = f"\n관련 뉴스 요약: {top_summary}" if top_summary else ""

    return (
        f"종목코드: {krx_code}\n"
        f"감성점수: {sentiment} / 거래량점수: {volume} / "
        f"모멘텀점수: {momentum} / 이상거래점수: {anomaly}"
        f"{summary_part}\n\n"
        "위 분석 데이터를 바탕으로 이 종목이 오늘 추천된 이유를 "
        "투자 권유나 수익 보장 표현 없이 분석 근거만 서술하여 "
        "한국어 2~3문장으로 설명하세요."
    )


async def generate_explanation(
    krx_code: str,
    score_breakdown: dict[str, Any],
    top_summary: str,
    api_key: str | None = None,
) -> str | None:
    """Claude Haiku로 한국어 추천 근거 텍스트 생성.

    # @MX:ANCHOR: [AUTO] 추천 근거 생성 단일 진입점 — 파이프라인과 테스트에서 호출
    # @MX:REASON: service.py 파이프라인에서 호출되는 공개 API. 실패 격리 계약 존재.

    Args:
        krx_code: KRX 종목코드
        score_breakdown: 점수 구성 딕셔너리
        top_summary: 상위 기사 요약

    Returns:
        한국어 추천 근거 문자열. API 오류/타임아웃 등 실패 시 None.
    """
    # API 키 확인 — 없으면 생성 불가
    key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        log.warning("ANTHROPIC_API_KEY 미설정 — 설명 생성 건너뜀", krx_code=krx_code)
        return None

    try:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=key)
        user_message = _build_prompt(krx_code, score_breakdown, top_summary)

        message = await client.messages.create(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            system=(
                "당신은 주식 분석 데이터를 바탕으로 객관적인 분석 근거를 서술하는 어시스턴트입니다. "
                "투자 권유, 수익 보장, 매수/매도 권유 표현은 절대 사용하지 마세요."
            ),
            messages=[{"role": "user", "content": user_message}],
        )

        text = message.content[0].text.strip()
        log.info("설명 생성 완료", krx_code=krx_code, chars=len(text))
        return text

    except Exception as e:
        # [HARD] 모든 예외를 잡아서 None 반환 — 파이프라인 중단 금지
        log.warning("설명 생성 실패, 폴백 적용", krx_code=krx_code, error=str(e))
        return None
