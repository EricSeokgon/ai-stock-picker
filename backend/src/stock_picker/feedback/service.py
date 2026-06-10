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
