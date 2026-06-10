# 추천 피드백 서비스 — 좋아요/싫어요 저장 및 집계 (SPEC-STOCK-007 TASK-006)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from stock_picker.db.models import RecommendationFeedback

# 허용 투표값 집합
_VALID_VOTES = {"up", "down"}


# @MX:ANCHOR: [AUTO] 피드백 저장/조회 서비스 — 라우터와 테스트에서 사용
# @MX:REASON: recommendations 라우터, 단위 테스트, 통합 테스트에서 3개 이상 참조


async def save_feedback(
    db: AsyncSession,
    krx_code: str,
    vote: str,
    user_id: int | None = None,
) -> RecommendationFeedback:
    """피드백 투표 저장.

    Args:
        db: 비동기 DB 세션
        krx_code: KRX 종목코드
        vote: "up" 또는 "down"
        user_id: 사용자 ID (비로그인 시 None)

    Returns:
        저장된 RecommendationFeedback 인스턴스

    Raises:
        ValueError: vote가 "up" 또는 "down"이 아닌 경우
    """
    if vote not in _VALID_VOTES:
        raise ValueError(f"투표 값이 유효하지 않습니다: '{vote}'. 허용값: up, down")

    from datetime import datetime

    feedback = RecommendationFeedback(
        krx_code=krx_code,
        vote=vote,
        user_id=user_id,
        created_at=datetime.utcnow(),
    )
    db.add(feedback)
    await db.flush()
    await db.commit()
    await db.refresh(feedback)
    return feedback


async def get_feedback_summary(
    db: AsyncSession,
    krx_code: str,
) -> dict:
    """종목별 피드백 집계 조회.

    Args:
        db: 비동기 DB 세션
        krx_code: KRX 종목코드

    Returns:
        {"krx_code": str, "up": int, "down": int}
    """
    stmt = (
        select(
            RecommendationFeedback.vote,
            func.count(RecommendationFeedback.id).label("cnt"),
        )
        .where(RecommendationFeedback.krx_code == krx_code)
        .group_by(RecommendationFeedback.vote)
    )
    result = await db.execute(stmt)
    rows = result.all()

    counts = {"up": 0, "down": 0}
    for row in rows:
        if row.vote in counts:
            counts[row.vote] = row.cnt

    return {"krx_code": krx_code, "up": counts["up"], "down": counts["down"]}


# @MX:ANCHOR: [AUTO] 복수 종목 피드백 벌크 조회 - 추천 서비스에서 N+1 방지용으로 호출
# @MX:REASON: RecommendationService.run(), 단위 테스트, 통합 테스트에서 3개 이상 참조


async def get_bulk_feedback(
    db: AsyncSession,
    krx_codes: list[str],
) -> dict[str, dict[str, int]]:
    """여러 종목의 up/down 합계를 단일 GROUP BY 쿼리로 조회.

    N+1 쿼리 방지 — krx_code, vote 기준 GROUP BY 단일 쿼리 사용.

    Args:
        db: 비동기 DB 세션
        krx_codes: 조회할 KRX 종목코드 목록

    Returns:
        {krx_code: {"up": int, "down": int}}
        목록에 없는 종목은 {"up": 0, "down": 0} 기본값으로 포함됨
    """
    # 기본값으로 모든 종목 초기화
    result_map: dict[str, dict[str, int]] = {
        code: {"up": 0, "down": 0} for code in krx_codes
    }

    if not krx_codes:
        return result_map

    stmt = (
        select(
            RecommendationFeedback.krx_code,
            RecommendationFeedback.vote,
            func.count(RecommendationFeedback.id).label("cnt"),
        )
        .where(RecommendationFeedback.krx_code.in_(krx_codes))
        .group_by(RecommendationFeedback.krx_code, RecommendationFeedback.vote)
    )
    rows = await db.execute(stmt)

    for row in rows.all():
        if row.krx_code in result_map and row.vote in ("up", "down"):
            result_map[row.krx_code][row.vote] = row.cnt

    return result_map
