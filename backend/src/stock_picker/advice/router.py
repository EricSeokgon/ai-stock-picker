# AI 투자 조언 REST API — SPEC-STOCK-014 M2-M5
# 리밸런싱·리스크 프로파일·시장 브리핑·이력·피드백 엔드포인트
import json
import logging
from datetime import date, datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from stock_picker.advice import service as advice_service
from stock_picker.auth.dependencies import get_current_user
from stock_picker.db.models import AIAdvice, User, WatchlistItem
from stock_picker.db.session import get_session

# @MX:ANCHOR: [AUTO] AI 투자 조언 API 진입점
# @MX:REASON: /advice prefix로 5개 엔드포인트를 노출하는 공개 API 경계 (SPEC-STOCK-014)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/advice", tags=["advice"])

# Redis 없이도 동작하도록 선택적 임포트
try:
    from stock_picker.cache.redis_client import get_redis_client  # type: ignore[import]
except ImportError:
    def get_redis_client():  # type: ignore[misc]
        return None


# ────────────────────────────────────────────────────────────────
# 응답 스키마
# ────────────────────────────────────────────────────────────────

class AdviceHistoryItem(BaseModel):
    """조언 이력 항목 응답 스키마"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    advice_type: str
    ref_date: date
    title: str
    body: Optional[str]
    risk_score: Optional[int]
    feedback: Optional[str]
    created_at: datetime


class FeedbackRequest(BaseModel):
    """피드백 요청 스키마 (REQ-FB-001)"""

    feedback: str

    @field_validator("feedback")
    @classmethod
    def validate_feedback(cls, v: str) -> str:
        allowed = {"helpful", "not_helpful", "neutral"}
        if v not in allowed:
            raise ValueError(f"feedback는 {allowed} 중 하나여야 합니다.")
        return v


class FeedbackResponse(BaseModel):
    advice_id: int
    feedback: str


# ────────────────────────────────────────────────────────────────
# 내부 헬퍼
# ────────────────────────────────────────────────────────────────

async def _get_holdings(db: AsyncSession, user_id: int) -> list[Any]:
    """사용자 보유 종목(WatchlistItem) 조회."""
    stmt = select(WatchlistItem).where(WatchlistItem.user_id == user_id)
    result = await db.execute(stmt)
    return result.scalars().all()


async def _get_existing_advice(
    db: AsyncSession, user_id: int, advice_type: str, ref_date: date
) -> Optional[AIAdvice]:
    """동일 (user_id, advice_type, ref_date) 조언 조회 (멱등성)."""
    stmt = select(AIAdvice).where(
        AIAdvice.user_id == user_id,
        AIAdvice.advice_type == advice_type,
        AIAdvice.ref_date == ref_date,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _save_advice(
    db: AsyncSession,
    user_id: int,
    advice_type: str,
    ref_date: date,
    title: str,
    body: Optional[str],
    payload: Optional[str],
    risk_score: Optional[int],
) -> AIAdvice:
    """AIAdvice 레코드 저장 후 반환."""
    advice = AIAdvice(
        user_id=user_id,
        advice_type=advice_type,
        ref_date=ref_date,
        title=title,
        body=body,
        payload=payload,
        risk_score=risk_score,
    )
    db.add(advice)
    await db.commit()
    await db.refresh(advice)
    return advice


# ────────────────────────────────────────────────────────────────
# 엔드포인트
# ────────────────────────────────────────────────────────────────

@router.post("/rebalance")
async def rebalance_advice(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """리밸런싱 제안 — 보유 종목과 최신 추천 유니버스 기반 (REQ-RB-001~005).

    # @MX:NOTE: [AUTO] 멱등 처리: 당일 동일 advice_type 존재 시 기존 결과 반환
    """
    today = date.today()

    # 멱등성: 당일 기존 조언 존재 여부 확인
    existing = await _get_existing_advice(db, current_user.id, "rebalance", today)
    if existing and existing.payload:
        payload = json.loads(existing.payload)
        return {"advice_id": existing.id, **payload, "disclaimer": advice_service._DISCLAIMER}

    # 최신 추천 유니버스 조회 (trade_date 기준 최신)
    from stock_picker.db.models import Recommendation
    date_stmt = select(Recommendation.trade_date).order_by(Recommendation.trade_date.desc()).limit(1)
    date_result = await db.execute(date_stmt)
    latest_date = date_result.scalar_one_or_none()

    rec_universe: list[dict[str, Any]] = []
    if latest_date:
        rec_stmt = select(Recommendation).where(Recommendation.trade_date == latest_date).limit(20)
        rec_result = await db.execute(rec_stmt)
        recs = rec_result.scalars().all()
        rec_universe = [
            {"krx_code": r.krx_code, "rank": r.rank if hasattr(r, "rank") else 0, "total_score": 0.0}
            for r in recs
        ]

    # 보유 종목 조회
    holdings = await _get_holdings(db, current_user.id)
    if not holdings:
        return {"message": "보유 종목이 없습니다. 관심 종목을 추가한 후 다시 시도해 주세요."}

    holdings_summary = advice_service.build_holdings_summary(holdings)
    result = advice_service.generate_rebalancing_advice(holdings_summary, rec_universe)

    # 영속화
    payload_str = json.dumps(result, ensure_ascii=False)
    title = "리밸런싱 제안"
    advice = await _save_advice(
        db, current_user.id, "rebalance", today,
        title, None, payload_str, None
    )
    return {"advice_id": advice.id, **result, "disclaimer": advice_service._DISCLAIMER}


@router.post("/risk-profile")
async def risk_profile_advice(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """리스크 프로파일 분석 (REQ-RM-001~005).

    # @MX:NOTE: [AUTO] 멱등 처리: 당일 기존 risk_profile 조언 존재 시 반환
    """
    today = date.today()

    existing = await _get_existing_advice(db, current_user.id, "risk_profile", today)
    if existing and existing.payload:
        payload = json.loads(existing.payload)
        return {"advice_id": existing.id, **payload, "disclaimer": advice_service._DISCLAIMER}

    holdings = await _get_holdings(db, current_user.id)
    if not holdings:
        return {"message": "보유 종목이 없습니다. 관심 종목을 추가한 후 다시 시도해 주세요."}

    holdings_summary = advice_service.build_holdings_summary(holdings)
    result = advice_service.generate_risk_profile(holdings_summary)

    payload_str = json.dumps(result, ensure_ascii=False)
    risk_score = result.get("risk_score") if "error" not in result else None
    advice = await _save_advice(
        db, current_user.id, "risk_profile", today,
        "리스크 프로파일 분석", result.get("explanation"), payload_str, risk_score
    )
    return {"advice_id": advice.id, **result, "disclaimer": advice_service._DISCLAIMER}


@router.get("/market-briefing")
async def market_briefing(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """맞춤형 시장 브리핑 — 1일 1회 생성, Redis 캐시 사용 (REQ-MB-001~005).

    # @MX:WARN: [AUTO] Redis 미사용 시 매 요청마다 DB 조회 및 Claude 호출 발생
    # @MX:REASON: get_redis_client() 실패 시 캐시 없이 동작하는 폴백 경로 포함
    """
    today = date.today()
    user_id = current_user.id

    # Redis 캐시 확인
    redis = get_redis_client()
    cache_key = f"ai_advice:briefing:{user_id}:{today.isoformat()}"
    if redis is not None:
        try:
            cached = await redis.get(cache_key) if hasattr(redis, "get") else redis.get(cache_key)
            if cached:
                data = json.loads(cached)
                return {"cached": True, **data, "disclaimer": advice_service._DISCLAIMER}
        except Exception:
            logger.warning("Redis 캐시 조회 실패 — DB 폴백")

    # DB 멱등 확인
    existing = await _get_existing_advice(db, user_id, "market_briefing", today)
    if existing and existing.payload:
        payload = json.loads(existing.payload)
        return {"advice_id": existing.id, **payload, "disclaimer": advice_service._DISCLAIMER}

    holdings = await _get_holdings(db, user_id)
    holdings_summary = advice_service.build_holdings_summary(holdings) if holdings else []

    # 시장 컨텍스트 구성 (뉴스 감성 분석 기반)
    from stock_picker.db.models import AnalysisResult
    sentiment_stmt = select(AnalysisResult).order_by(AnalysisResult.analyzed_at.desc()).limit(5)
    sentiment_result = await db.execute(sentiment_stmt)
    sentiments = sentiment_result.scalars().all()
    market_context: dict[str, Any] = {}
    if sentiments:
        avg_score = sum(float(s.sentiment_score) for s in sentiments) / len(sentiments)
        market_context = {
            "sentiment_score": round(avg_score, 3),
            "sentiment_label": "긍정" if avg_score > 0.1 else ("부정" if avg_score < -0.1 else "중립"),
            "sample_count": len(sentiments),
        }

    result = advice_service.generate_market_briefing(holdings_summary, market_context)

    payload_str = json.dumps(result, ensure_ascii=False)
    advice = await _save_advice(
        db, user_id, "market_briefing", today,
        "오늘의 시장 브리핑", result.get("briefing"), payload_str, None
    )

    # Redis 캐시 저장
    if redis is not None:
        try:
            ttl = 3600 * 20  # 당일 만료
            if hasattr(redis, "setex"):
                redis.setex(cache_key, ttl, json.dumps(result, ensure_ascii=False))
            elif hasattr(redis, "set"):
                await redis.set(cache_key, json.dumps(result, ensure_ascii=False), ex=ttl)
        except Exception:
            logger.warning("Redis 캐시 저장 실패 — 무시")

    return {"advice_id": advice.id, **result, "disclaimer": advice_service._DISCLAIMER}


@router.get("/history", response_model=list[AdviceHistoryItem])
async def advice_history(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[AdviceHistoryItem]:
    """AI 조언 이력 조회 — 최신순 (REQ-AIV-004)."""
    stmt = (
        select(AIAdvice)
        .where(AIAdvice.user_id == current_user.id)
        .order_by(AIAdvice.created_at.desc())
        .limit(50)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [
        AdviceHistoryItem(
            id=r.id,
            advice_type=r.advice_type,
            ref_date=r.ref_date,
            title=r.title,
            body=r.body,
            risk_score=r.risk_score,
            feedback=r.feedback,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("/{advice_id}/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    advice_id: int,
    body: FeedbackRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> FeedbackResponse:
    """AI 조언 피드백 등록 (REQ-FB-001~003)."""
    stmt = select(AIAdvice).where(
        AIAdvice.id == advice_id,
        AIAdvice.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    advice = result.scalar_one_or_none()

    if advice is None:
        raise HTTPException(status_code=404, detail="조언을 찾을 수 없습니다.")

    advice.feedback = body.feedback
    advice.feedback_at = datetime.now(timezone.utc)
    await db.commit()

    return FeedbackResponse(advice_id=advice.id, feedback=advice.feedback)
