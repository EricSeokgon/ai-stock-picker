# 스크리너 Pydantic 스키마 — SPEC-STOCK-018
from typing import Any

from pydantic import BaseModel, Field, model_validator


class FilterRange(BaseModel):
    """단일 지표의 min/max 범위 필터.

    min > max이면 ValidationError (REQ-SCR-006).
    """

    min: float | None = None
    max: float | None = None

    @model_validator(mode="after")
    def check_min_lte_max(self) -> "FilterRange":
        """min이 max보다 크면 안 됨 (REQ-SCR-006)"""
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError(
                f"FilterRange: min({self.min}) must be <= max({self.max})"
            )
        return self


class ScreenerCriteria(BaseModel):
    """스크리너 필터 조건 — 모든 항목 선택적 (AND 조합).

    필드가 None이면 해당 지표 필터 비활성화.
    """

    per: FilterRange | None = None
    pbr: FilterRange | None = None
    roe: FilterRange | None = None
    market_cap: FilterRange | None = None
    dividend_yield: FilterRange | None = None
    # 현재가의 52주 레인지 위치 (0~100%)
    week52_position: FilterRange | None = None

    def to_json(self) -> str:
        """프리셋 저장용 JSON 직렬화"""
        return self.model_dump_json()

    @classmethod
    def from_json(cls, raw: str) -> "ScreenerCriteria":
        """프리셋 로드용 JSON 역직렬화"""
        return cls.model_validate_json(raw)


class ScreenerRequest(BaseModel):
    """POST /screener/run 요청 본문"""

    filters: ScreenerCriteria = Field(default_factory=ScreenerCriteria)
    sort_by: str | None = None
    sort_order: str = "desc"
    limit: int = Field(default=100, ge=1, le=500)


class ScreenerResult(BaseModel):
    """스크리너 결과 단일 종목"""

    krx_code: str
    name: str | None = None
    sector: str | None = None
    current_price: float | None = None
    change_pct: float | None = None
    per: float | None = None
    pbr: float | None = None
    roe: float | None = None
    market_cap: float | None = None
    dividend_yield: float | None = None
    week52_position: float | None = None
    in_watchlist: bool = False
    in_recommendations: bool = False


class ScreenerResponse(BaseModel):
    """POST /screener/run 응답"""

    snapshot_date: str | None = None
    total: int
    results: list[ScreenerResult]


class ScreenerPresetCreate(BaseModel):
    """프리셋 저장 요청"""

    name: str = Field(..., min_length=1, max_length=100)
    criteria: ScreenerCriteria = Field(default_factory=ScreenerCriteria)


class ScreenerPresetResponse(BaseModel):
    """프리셋 응답"""

    id: int
    user_id: int
    name: str
    criteria: ScreenerCriteria
    created_at: Any = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_preset(cls, preset: Any) -> "ScreenerPresetResponse":
        """ORM ScreenerPreset → ScreenerPresetResponse 변환"""
        criteria = ScreenerCriteria.from_json(preset.criteria)
        return cls(
            id=preset.id,
            user_id=preset.user_id,
            name=preset.name,
            criteria=criteria,
            created_at=preset.created_at,
        )
