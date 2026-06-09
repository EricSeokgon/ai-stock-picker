# 알림 시스템 Pydantic 스키마 — 요청/응답 모델 정의
import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


# ── 가격 알림 스키마 ───────────────────────────────────────────────────────────

class WatchlistAlertCreate(BaseModel):
    """가격 알림 생성 요청 스키마"""

    model_config = ConfigDict(extra="forbid")

    krx_code: str
    target_price: float
    # direction: "above" (목표가 이상) 또는 "below" (목표가 이하)
    direction: Literal["above", "below"]

    @field_validator("krx_code")
    @classmethod
    def validate_krx_code(cls, v: str) -> str:
        """KRX 종목코드 형식 검증 — 숫자 1~10자리"""
        v = v.strip()
        if not v:
            raise ValueError("krx_code는 비어있을 수 없습니다")
        return v

    @field_validator("target_price")
    @classmethod
    def validate_target_price(cls, v: float) -> float:
        """목표가는 양수여야 함"""
        if v <= 0:
            raise ValueError("target_price는 0보다 커야 합니다")
        return v


class WatchlistAlertResponse(BaseModel):
    """가격 알림 응답 스키마"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    krx_code: str
    target_price: float
    direction: str
    is_active: bool
    triggered_at: datetime | None = None


# ── 이메일 구독 스키마 ─────────────────────────────────────────────────────────

# 이메일 형식 검증 정규식
_EMAIL_REGEX = re.compile(r"^[^@]+@[^@]+\.[^@]+$")


class EmailSubscriptionCreate(BaseModel):
    """이메일 구독 생성 요청 스키마"""

    model_config = ConfigDict(extra="forbid")

    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """이메일 형식 검증"""
        v = v.strip().lower()
        if not _EMAIL_REGEX.match(v):
            raise ValueError("올바른 이메일 형식이 아닙니다")
        return v


class EmailSubscriptionResponse(BaseModel):
    """이메일 구독 응답 스키마"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    is_active: bool
    created_at: datetime
