# 추천 엔드포인트 - 당일 Top 10 추천 리스트 반환 + 종목 추천 근거 상세 + 히스토리
import json
from datetime import date, datetime, timedelta, timezone
from typing import Union

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from stock_picker.api.deps import get_cache, get_session
from stock_picker.api.schemas import (
    ContributingNewsItem,
    DailyRecommendations,
    FeedbackSummaryResponse,
    FeedbackVoteRequest,
    PreparingResponse,
    RecommendationDetailResponse,
    RecommendationHistoryResponse,
    RecommendationItem,
    RecommendationsResponse,
    ScoreBreakdown,
    ScoreFactorContribution,
)
from stock_picker.scoring.engine import decompose_score
from stock_picker.db.models import AnalysisResult, Article, Recommendation, StockMention
from stock_picker.feedback.service import get_feedback_summary, save_feedback
from stock_picker.recommendation.cache import RecommendationCache

# 선택적 Bearer 인증 — 토큰 없어도 오류 미발생
_optional_bearer = HTTPBearer(auto_error=False)


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_optional_bearer),
) -> int | None:
    """선택적 JWT 인증 의존성.

    토큰이 있으면 사용자 ID를 반환하고, 없으면 None을 반환한다.
    토큰 검증 실패 시에도 None을 반환한다 (인증 불필요 엔드포인트용).
    """
    if credentials is None:
        return None
    try:
        from stock_picker.auth.service import decode_token
        # 토큰 유효성만 검증 (서명·만료) — 실제 user_id는 DB 조회 없이는
        # 알 수 없으므로 payload 값과 무관하게 None 반환 (익명 취급)
        decode_token(credentials.credentials)
        return None
    except Exception:
        return None

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


# @MX:ANCHOR: [AUTO] 추천 조회 API - 프론트엔드 주요 진입점
# @MX:REASON: React 대시보드에서 폴링하는 핵심 엔드포인트 (AC-7, AC-10)

# 정렬 필드 → RecommendationItem dict 키 매핑
_SORT_FIELD_MAP = {
    "score": "total_score",
    "sentiment": "sentiment_score",
    "volume": "volume_score",
}


@router.get("", response_model=Union[RecommendationsResponse, PreparingResponse])
async def get_recommendations(
    limit: int = Query(default=10, gt=0, description="반환할 최대 추천 수"),
    sector: str | None = Query(default=None, description="섹터 필터 (sector 필드 일치)"),
    sort: str = Query(
        default="score",
        pattern="^(score|sentiment|volume)$",
        description="정렬 기준: score(총점), sentiment(감성점수), volume(거래량점수)",
    ),
    min_score: float | None = Query(default=None, ge=0.0, description="최소 총점 필터"),
    cache: RecommendationCache = Depends(get_cache),
) -> Union[RecommendationsResponse, PreparingResponse]:
    """당일 추천 리스트 반환 (필터/정렬 지원).

    파라미터 없이 호출 시 기존 동작과 동일 (하위 호환성 보장, AC-7, AC-10).

    필터/정렬 적용 순서:
    1. 파생 캐시 조회 (limit, sector 기반 키)
    2. 기본 캐시에서 데이터 로드
    3. sector 필터 적용
    4. min_score 필터 적용
    5. sort 기준 내림차순 정렬
    6. limit 적용
    7. 파생 캐시 저장 후 반환

    Args:
        limit: 반환할 최대 항목 수 (기본 10, 1 이상)
        sector: 섹터 문자열 필터 (해당 sector 필드 값과 정확히 일치해야 함)
        sort: 정렬 기준 — score(total_score), sentiment(sentiment_score), volume(volume_score)
        min_score: total_score 하한 필터
        cache: Redis 캐시 의존성

    Returns:
        RecommendationsResponse: 추천 목록
        PreparingResponse: 데이터 미준비 상태 (AC-10)
    """
    today = date.today()
    base_cache_key = f"recommendations:{today.isoformat()}"

    # 기본 파라미터 여부 판단 (파생 캐시 적용 범위)
    is_default_params = (limit == 10 and sector is None and sort == "score" and min_score is None)

    # 1. 파생 캐시 조회 (기본 파라미터면 파생 캐시 생략 — 기존 동작과 동일 경로 유지)
    if not is_default_params:
        derived_key = cache.build_derived_key(limit=limit, sector=sector)
        derived_cached = await cache.get_derived(derived_key)
        if derived_cached is not None:
            items = [RecommendationItem(**item) for item in derived_cached]
            return RecommendationsResponse(
                trade_date=today,
                recommendations=items,
                last_updated=datetime.now(tz=timezone.utc),
            )

    # 2. 기본 캐시 조회
    raw = await cache.get(base_cache_key)

    if raw is None:
        # 데이터 아직 준비 안 됨
        return PreparingResponse(last_updated=None)

    # raw가 list인지 JSON 문자열인지 처리
    if isinstance(raw, str):
        items_data: list = json.loads(raw)
    else:
        items_data = raw

    # 기본 파라미터: 기존 동작 그대로 반환
    if is_default_params:
        items = [RecommendationItem(**item) for item in items_data]
        last_updated = datetime.now(tz=timezone.utc)
        return RecommendationsResponse(
            trade_date=today,
            recommendations=items,
            last_updated=last_updated,
        )

    # 3. 필터 적용 — sector
    if sector is not None:
        items_data = [
            item for item in items_data
            if item.get("sector") == sector
        ]

    # 4. 필터 적용 — min_score
    if min_score is not None:
        items_data = [
            item for item in items_data
            if float(item.get("total_score", 0.0)) >= min_score
        ]

    # 5. 정렬 (내림차순)
    sort_field = _SORT_FIELD_MAP[sort]
    items_data = sorted(
        items_data,
        key=lambda x: float(x.get(sort_field, 0.0)),
        reverse=True,
    )

    # 6. limit 적용
    items_data = items_data[:limit]

    # 7. 파생 캐시 저장
    derived_key = cache.build_derived_key(limit=limit, sector=sector)
    await cache.set_derived(derived_key, items_data)

    items = [RecommendationItem(**item) for item in items_data]
    return RecommendationsResponse(
        trade_date=today,
        recommendations=items,
        last_updated=datetime.now(tz=timezone.utc),
    )


@router.get("/history", response_model=RecommendationHistoryResponse)
async def get_recommendation_history(
    days: int = Query(default=7, ge=1, le=90, description="조회할 기간 (1~90일)"),
    session: AsyncSession = Depends(get_session),
) -> RecommendationHistoryResponse:
    """추천 히스토리 조회 — 최근 N일간 날짜별 그룹.

    # @MX:NOTE: [AUTO] /history는 /{krx_code} 보다 먼저 등록해야 경로 충돌 없음

    공개 엔드포인트 (인증 불필요).

    Args:
        days: 조회 기간 (기본 7, 최대 90일)
        session: DB 세션 의존성

    Returns:
        RecommendationHistoryResponse: 날짜별 추천 그룹 목록
    """
    since_dt = datetime.now(tz=timezone.utc) - timedelta(days=days)

    stmt = (
        select(Recommendation)
        .where(Recommendation.trade_date >= since_dt)
        .order_by(Recommendation.trade_date.desc(), Recommendation.rank.asc())
    )
    result = await session.execute(stmt)
    recs = result.scalars().all()

    # 날짜별 그룹화 (YYYY-MM-DD 키)
    groups_map: dict[str, list[RecommendationItem]] = {}
    for rec in recs:
        trade_date_val = rec.trade_date
        if hasattr(trade_date_val, "date"):
            date_str = trade_date_val.date().isoformat()
        else:
            date_str = str(trade_date_val)[:10]

        item = RecommendationItem(
            rank=rec.rank,
            krx_code=rec.krx_code,
            total_score=float(rec.total_score),
            sentiment_score=float(rec.sentiment_score),
            volume_score=float(rec.volume_score),
            momentum_score=float(rec.momentum_score),
            anomaly_score=float(rec.anomaly_score),
            reasoning=rec.reasoning or "",
            explanation=rec.explanation,
        )
        groups_map.setdefault(date_str, []).append(item)

    # 날짜 내림차순 정렬된 그룹 목록 구성
    groups = [
        DailyRecommendations(date=date_str, recommendations=items)
        for date_str, items in sorted(groups_map.items(), reverse=True)
    ]

    return RecommendationHistoryResponse(days=days, groups=groups)


@router.post("/{krx_code}/feedback", response_model=FeedbackSummaryResponse)
async def submit_feedback(
    krx_code: str,
    body: FeedbackVoteRequest,
    session: AsyncSession = Depends(get_session),
    user_id: int | None = Depends(get_optional_user),
) -> FeedbackSummaryResponse:
    """추천 종목 피드백 투표 제출.

    인증 선택적 — 비로그인 사용자도 투표 가능.
    vote 값이 "up" 또는 "down"이 아니면 422 반환.

    Args:
        krx_code: KRX 종목코드
        body: 투표 요청 (vote: "up" | "down")
        session: DB 세션
        user_id: 로그인 사용자 ID (없으면 None)

    Returns:
        FeedbackSummaryResponse: 투표 후 집계 결과
    """
    # ValueError → 422 Unprocessable Entity (FastAPI 기본 동작)
    try:
        await save_feedback(
            db=session,
            krx_code=krx_code,
            vote=body.vote,
            user_id=user_id,
        )
    except ValueError as exc:
        from fastapi import HTTPException as _HTTPException
        raise _HTTPException(status_code=422, detail=str(exc)) from exc

    summary = await get_feedback_summary(db=session, krx_code=krx_code)
    return FeedbackSummaryResponse(**summary)


@router.get("/{krx_code}/feedback", response_model=FeedbackSummaryResponse)
async def get_feedback(
    krx_code: str,
    session: AsyncSession = Depends(get_session),
) -> FeedbackSummaryResponse:
    """추천 종목 피드백 집계 조회.

    공개 엔드포인트 (인증 불필요).

    Args:
        krx_code: KRX 종목코드
        session: DB 세션

    Returns:
        FeedbackSummaryResponse: up/down 투표 수
    """
    summary = await get_feedback_summary(db=session, krx_code=krx_code)
    return FeedbackSummaryResponse(**summary)


@router.get("/{krx_code}", response_model=RecommendationDetailResponse)
async def get_recommendation_detail(
    krx_code: str,
    session: AsyncSession = Depends(get_session),
) -> RecommendationDetailResponse:
    """종목 추천 근거 상세 (REQ-WEB-002, AC-8).

    당일 가장 최근 Recommendation을 조회하고, 해당 종목의 기여 기사를 함께 반환한다.

    Args:
        krx_code: KRX 종목코드
        session: DB 세션 의존성

    Returns:
        RecommendationDetailResponse: 종목 추천 근거 상세

    Raises:
        HTTPException 404: 해당 krx_code의 추천 데이터가 없을 경우
    """
    # 당일 해당 종목의 최근 추천 데이터 조회
    stmt = (
        select(Recommendation)
        .where(Recommendation.krx_code == krx_code)
        .order_by(Recommendation.computed_at.desc())
    )
    result = await session.execute(stmt)
    rec = result.scalar_one_or_none()

    if rec is None:
        raise HTTPException(status_code=404, detail=f"추천 데이터를 찾을 수 없습니다: {krx_code}")

    # 해당 종목의 기여 기사 조회 (StockMention → Article → AnalysisResult)
    news_stmt = (
        select(
            Article.title,
            AnalysisResult.summary,
            AnalysisResult.sentiment,
            Article.published_at,
        )
        .join(StockMention, StockMention.article_id == Article.id)
        .join(AnalysisResult, AnalysisResult.article_id == Article.id)
        .where(StockMention.krx_code == krx_code)
        .order_by(Article.published_at.desc())
        .limit(10)
    )
    news_result = await session.execute(news_stmt)
    news_rows = news_result.all()

    contributing_news = [
        ContributingNewsItem(
            title=row.title,
            summary=row.summary,
            sentiment=row.sentiment,
            published_at=row.published_at or datetime.now(tz=timezone.utc),
        )
        for row in news_rows
    ]

    trade_date = (
        rec.trade_date.date()
        if hasattr(rec.trade_date, "date")
        else rec.trade_date
    )

    # explanation: 구 데이터에 없을 수 있으므로 getattr로 안전하게 접근
    _expl_raw = getattr(rec, "explanation", None)
    explanation_val = _expl_raw if isinstance(_expl_raw, str) else None

    # base_score / feedback_score: 구 데이터는 None일 수 있음
    _base_raw = getattr(rec, "base_score", None)
    base_score_val = float(_base_raw) if _base_raw is not None else None

    _fb_raw = getattr(rec, "feedback_score", None)
    feedback_score_val = float(_fb_raw) if _fb_raw is not None else None

    # 점수 분해 계산 (요인 점수가 모두 존재하는 경우만)
    decomposed = decompose_score(
        sentiment=float(rec.sentiment_score),
        volume=float(rec.volume_score),
        momentum=float(rec.momentum_score),
        anomaly=float(rec.anomaly_score),
    )
    score_breakdown = ScoreBreakdown(
        factors=[ScoreFactorContribution(**f) for f in decomposed],
        feedback_delta=feedback_score_val,
    )

    return RecommendationDetailResponse(
        krx_code=rec.krx_code,
        trade_date=trade_date,
        total_score=float(rec.total_score),
        sentiment_score=float(rec.sentiment_score),
        volume_score=float(rec.volume_score),
        momentum_score=float(rec.momentum_score),
        anomaly_score=float(rec.anomaly_score),
        reasoning=rec.reasoning or "",
        explanation=explanation_val,
        contributing_news=contributing_news,
        base_score=base_score_val,
        feedback_score=feedback_score_val,
        score_breakdown=score_breakdown,
    )
