# Claude API 응답 JSON 스키마 - pydantic v2로 강제 검증
from typing import Literal

from pydantic import BaseModel, field_validator


class ClaudeAnalysisOutput(BaseModel):
    """
    Claude API 뉴스 분석 결과 스키마.

    Claude가 반환하는 JSON을 엄격하게 검증하여
    하위 처리 파이프라인의 안정성을 보장한다.
    """

    # 감성 분류: 세 가지 값만 허용
    sentiment: Literal["positive", "negative", "neutral"]

    # 감성 점수: -1.0(완전 부정) ~ 1.0(완전 긍정)
    sentiment_score: float

    # 섹터 태그: 빈 배열 허용
    sector_tags: list[str]

    # 키워드 목록: 리스트 타입만 허용
    keywords: list[str]

    # 1문장 요약: 빈 문자열 및 공백만 있는 문자열 불허
    summary: str

    @field_validator("sentiment_score")
    @classmethod
    def validate_score_range(cls, v: float) -> float:
        """sentiment_score 범위 검증: -1.0 ~ 1.0"""
        if v < -1.0 or v > 1.0:
            raise ValueError(
                f"sentiment_score는 -1.0 이상 1.0 이하여야 합니다. 입력값: {v}"
            )
        return v

    @field_validator("summary")
    @classmethod
    def validate_summary_not_empty(cls, v: str) -> str:
        """summary 빈 문자열 및 공백 문자열 불허"""
        if not v or not v.strip():
            raise ValueError("summary는 비어있을 수 없습니다")
        return v
