# 스크리너 라우터 — SPEC-STOCK-018 REQ-SCR-API-001~005
import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from stock_picker.auth.dependencies import get_current_user, get_db_session
from stock_picker.screener.schemas import (
    ScreenerPresetCreate,
    ScreenerPresetResponse,
    ScreenerRequest,
    ScreenerResponse,
    ScreenerResult,
)
from stock_picker.screener.service import (
    create_preset,
    delete_preset,
    list_presets,
    run_screener,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/screener", tags=["screener"])


@router.post("/run", response_model=ScreenerResponse)
def run_screener_endpoint(
    req: ScreenerRequest,
    db: Session = Depends(get_db_session),
) -> ScreenerResponse:
    """스크리너 실행 — 인증 불필요 (REQ-SCR-API-001).

    # @MX:ANCHOR: [AUTO] 스크리너 API 진입점
    # @MX:REASON: 프론트엔드, 테스트, 프리셋 로드 등 3곳 이상에서 호출
    # @MX:SPEC: SPEC-STOCK-018 REQ-SCR-API-001
    """
    results: list[ScreenerResult] = run_screener(
        criteria=req.filters,
        db=db,
        limit=req.limit,
    )
    return ScreenerResponse(
        snapshot_date=None,
        total=len(results),
        results=results,
    )


@router.get("/presets", response_model=list[ScreenerPresetResponse])
def list_presets_endpoint(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[ScreenerPresetResponse]:
    """사용자 프리셋 목록 조회 — 인증 필요 (REQ-SCR-API-002)"""
    presets = list_presets(user_id=current_user.id, db=db)
    return [ScreenerPresetResponse.from_orm_preset(p) for p in presets]


@router.post("/presets", response_model=ScreenerPresetResponse, status_code=200)
def create_preset_endpoint(
    req: ScreenerPresetCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ScreenerPresetResponse:
    """프리셋 저장 — 최대 5개 (REQ-SCR-API-003, REQ-SCR-PRESET-002)"""
    preset = create_preset(user_id=current_user.id, req=req, db=db)
    return ScreenerPresetResponse.from_orm_preset(preset)


@router.delete("/presets/{preset_id}", status_code=204)
def delete_preset_endpoint(
    preset_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> Response:
    """프리셋 삭제 — 소유자만 가능, 204 반환 (REQ-SCR-API-004)"""
    delete_preset(user_id=current_user.id, preset_id=preset_id, db=db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
