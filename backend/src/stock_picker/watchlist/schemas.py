# 관심종목 Pydantic 스키마 — 요청/응답 직렬화
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class WatchlistItemCreate(BaseModel):
    """관심종목 추가 요청 스키마"""

    krx_code: str

    @field_validator("krx_code")
    @classmethod
    def validate_krx_code(cls, v: str) -> str:
        """krx_code 공백 제거 및 길이 검증"""
        v = v.strip()
        if not v:
            raise ValueError("종목코드가 비어 있습니다")
        if len(v) > 10:
            raise ValueError("종목코드는 10자 이하여야 합니다")
        return v


class WatchlistItemResponse(BaseModel):
    """관심종목 응답 스키마"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    krx_code: str
    added_at: datetime
