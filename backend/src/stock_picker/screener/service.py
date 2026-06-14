# 스크리너 서비스 — 필터 로직 + 프리셋 CRUD (SPEC-STOCK-018)
import logging
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from stock_picker.db.models import ScreenerPreset, StockFundamental
from stock_picker.screener.schemas import (
    FilterRange,
    ScreenerCriteria,
    ScreenerPresetCreate,
    ScreenerPresetResponse,
    ScreenerResult,
)

logger = logging.getLogger(__name__)

# 사용자당 최대 프리셋 수 (REQ-SCR-PRESET-002)
MAX_PRESETS_PER_USER = 5


# ── 필터 로직 ─────────────────────────────────────────────────────────────────


def _passes_range(value: float | None, filt: FilterRange | None) -> bool:
    """단일 값이 FilterRange를 통과하는지 검사.

    # @MX:NOTE: [AUTO] NULL 처리 규칙 — 필터 활성화 시 NULL 값은 제외 (REQ-SCR-003)
    필터가 None이면 항상 True (해당 조건 비활성화).
    필터가 활성화됐는데 값이 None이면 False (자동 제외).
    """
    if filt is None:
        return True
    if value is None:
        # 필터가 있는데 값이 NULL → 제외 (REQ-SCR-003)
        if filt.min is not None or filt.max is not None:
            return False
        return True
    if filt.min is not None and float(value) < filt.min:
        return False
    if filt.max is not None and float(value) > filt.max:
        return False
    return True


def apply_filters(
    rows: list[Any],
    criteria: ScreenerCriteria,
) -> list[Any]:
    """펀더멘털 행 목록에 AND 필터를 적용해 조건 충족 행만 반환 (REQ-SCR-001).

    # @MX:ANCHOR: [AUTO] 스크리너 핵심 필터 함수
    # @MX:REASON: screener/service.py(run_screener), 테스트 코드에서 직접 호출 등 3곳 이상 사용
    # @MX:SPEC: SPEC-STOCK-018 REQ-SCR-001~003
    """
    result = []
    for row in rows:
        if not _passes_range(row.per, criteria.per):
            continue
        if not _passes_range(row.pbr, criteria.pbr):
            continue
        if not _passes_range(row.roe, criteria.roe):
            continue
        if not _passes_range(row.market_cap, criteria.market_cap):
            continue
        if not _passes_range(row.dividend_yield, criteria.dividend_yield):
            continue
        if not _passes_range(row.price_vs_52w_pct, criteria.week52_position):
            continue
        result.append(row)
    return result


def to_screener_result(
    row: Any,
    watchlist_codes: set[str] | None = None,
    recommendation_codes: set[str] | None = None,
) -> ScreenerResult:
    """StockFundamental ORM 행 → ScreenerResult 변환"""
    return ScreenerResult(
        krx_code=row.krx_code,
        name=row.name,
        sector=row.sector,
        current_price=float(row.current_price) if row.current_price is not None else None,
        change_pct=float(row.change_pct) if row.change_pct is not None else None,
        per=float(row.per) if row.per is not None else None,
        pbr=float(row.pbr) if row.pbr is not None else None,
        roe=float(row.roe) if row.roe is not None else None,
        market_cap=float(row.market_cap) if row.market_cap is not None else None,
        dividend_yield=float(row.dividend_yield) if row.dividend_yield is not None else None,
        week52_position=(
            float(row.price_vs_52w_pct) if row.price_vs_52w_pct is not None else None
        ),
        in_watchlist=row.krx_code in (watchlist_codes or set()),
        in_recommendations=row.krx_code in (recommendation_codes or set()),
    )


def run_screener(
    criteria: ScreenerCriteria,
    db: Session,
    limit: int = 100,
    watchlist_codes: set[str] | None = None,
    recommendation_codes: set[str] | None = None,
) -> list[ScreenerResult]:
    """스크리너 실행 — 최신 스냅샷 조회 후 필터 적용 (REQ-SCR-001~007).

    # @MX:ANCHOR: [AUTO] 스크리너 실행 진입점
    # @MX:REASON: router.py(POST /screener/run), 테스트 코드에서 3곳 이상 호출
    # @MX:SPEC: SPEC-STOCK-018 REQ-SCR-007
    """
    from sqlalchemy import func as sa_func

    # 최신 snapshot_date 조회
    latest_date = db.query(sa_func.max(StockFundamental.snapshot_date)).scalar()
    if latest_date is None:
        return []

    # 최신 날짜 스냅샷 전체 로드
    rows = (
        db.query(StockFundamental)
        .filter(StockFundamental.snapshot_date == latest_date)
        .all()
    )

    # 필터 적용
    filtered = apply_filters(rows, criteria)

    # 결과 변환 (limit 적용)
    results = [
        to_screener_result(row, watchlist_codes, recommendation_codes)
        for row in filtered[:limit]
    ]
    return results


# ── 프리셋 CRUD ───────────────────────────────────────────────────────────────


def list_presets(user_id: int, db: Session) -> list[ScreenerPreset]:
    """사용자 프리셋 목록 조회 (REQ-SCR-PRESET-003)"""
    return (
        db.query(ScreenerPreset)
        .filter(ScreenerPreset.user_id == user_id)
        .order_by(ScreenerPreset.created_at.desc())
        .all()
    )


def create_preset(
    user_id: int, req: ScreenerPresetCreate, db: Session
) -> ScreenerPreset:
    """프리셋 생성 — 5개 초과 시 409 (REQ-SCR-PRESET-001~002).

    # @MX:NOTE: [AUTO] 사용자당 최대 5개 제한 비즈니스 규칙
    """
    # 기존 개수 확인
    count = (
        db.query(ScreenerPreset)
        .filter(ScreenerPreset.user_id == user_id)
        .count()
    )
    if count >= MAX_PRESETS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"프리셋은 최대 {MAX_PRESETS_PER_USER}개까지 저장할 수 있습니다",
        )

    preset = ScreenerPreset(
        user_id=user_id,
        name=req.name,
        criteria=req.criteria.to_json(),
    )
    db.add(preset)
    try:
        db.commit()
        db.refresh(preset)
        return preset
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"이미 '{req.name}' 이름의 프리셋이 존재합니다 (REQ-SCR-PRESET-006)",
        )


def delete_preset(user_id: int, preset_id: int, db: Session) -> None:
    """프리셋 삭제 — 소유권 검증 (REQ-SCR-PRESET-004~005)"""
    preset = (
        db.query(ScreenerPreset)
        .filter(ScreenerPreset.id == preset_id)
        .first()
    )
    if preset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"프리셋 {preset_id}을(를) 찾을 수 없습니다",
        )
    if preset.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="해당 프리셋에 대한 권한이 없습니다 (REQ-SCR-PRESET-005)",
        )
    db.delete(preset)
    db.commit()
