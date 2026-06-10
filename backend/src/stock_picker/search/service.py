# 종목 검색 서비스 — KRX 마스터 기반 종목명/코드 검색
from datetime import datetime, timedelta, timezone
from pathlib import Path

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from stock_picker.db.models import Recommendation
from stock_picker.mapping.krx_master import load_krx_master

log = structlog.get_logger()

# KRX 마스터 CSV 기본 경로 (패키지 기준 상대 경로)
_DEFAULT_CSV = (
    Path(__file__).parent.parent.parent.parent.parent
    / "tests"
    / "fixtures"
    / "krx_master.csv"
)


# @MX:ANCHOR: [AUTO] 종목 검색 API 진입점 — stocks 라우터와 테스트에서 호출
# @MX:REASON: stocks 라우터, 단위 테스트, 통합 테스트에서 3개 이상 모듈이 사용


async def search_stocks(
    q: str,
    db: AsyncSession,
    max_results: int = 20,
    csv_path: Path | None = None,
) -> list[dict]:
    """KRX 종목명 또는 코드 접두어로 종목 검색.

    검색 기준:
    - 종목명 부분 일치 (대소문자 무관)
    - KRX 코드 접두어 일치

    정렬 기준:
    1. in_recommendations=True인 종목 우선
    2. 종목명 가나다 순

    Args:
        q: 검색 쿼리 (최소 1자)
        db: 비동기 DB 세션
        max_results: 최대 반환 건수 (기본 20)
        csv_path: KRX 마스터 CSV 경로 (None이면 기본 경로)

    Returns:
        검색 결과 dict 목록. 각 항목에 krx_code, name, in_recommendations 포함.
    """
    if not q:
        return []

    # KRX 마스터 로딩 (종목명 → 코드)
    try:
        master = load_krx_master(csv_path)
    except Exception:
        log.warning("KRX 마스터 로딩 실패", query=q)
        master = {}

    # 최근 추천 종목 코드 집합 조회 (최근 7일)
    recent_codes = await _get_recent_recommended_codes(db)

    q_lower = q.lower()

    # 검색 수행: 종목명 부분 일치 또는 코드 접두어 일치
    results: list[dict] = []
    for name, code in master.items():
        name_match = q_lower in name.lower()
        code_match = code.startswith(q)

        if name_match or code_match:
            results.append(
                {
                    "krx_code": code,
                    "name": name,
                    "in_recommendations": code in recent_codes,
                }
            )

    # 정렬: in_recommendations 우선 → 종목명 가나다 순
    results.sort(key=lambda x: (not x["in_recommendations"], x["name"]))

    return results[:max_results]


async def _get_recent_recommended_codes(db: AsyncSession) -> set[str]:
    """최근 7일 이내 추천된 종목 코드 집합 반환.

    DB 조회 실패 시 빈 집합 반환 (검색은 계속 동작).
    """
    try:
        since = datetime.now(tz=timezone.utc) - timedelta(days=7)
        stmt = select(Recommendation.krx_code).where(
            Recommendation.trade_date >= since
        ).distinct()
        result = await db.execute(stmt)
        return {row[0] for row in result.all()}
    except Exception:
        log.warning("최근 추천 종목 조회 실패")
        return set()
