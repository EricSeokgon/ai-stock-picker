# 섹터 트렌드 집계 서비스 (SPEC-STOCK-008 TASK-002, TASK-003)
import math
from collections import defaultdict
from datetime import date, datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from stock_picker.db.models import AnalysisResult, Article, SectorTrend

# @MX:ANCHOR: [AUTO] 섹터 트렌드 집계 진입점 - 파이프라인에서 호출
# @MX:REASON: scheduler/jobs.py 및 테스트에서 직접 호출하는 공개 함수

log = structlog.get_logger()


def _compute_trend_score(avg_sentiment: float, news_volume: int) -> float:
    """트렌드 점수 계산.

    공식: avg_sentiment * 0.7 + log(news_volume + 1) * 0.3
    결과는 -1.0 ~ 1.0 범위로 클램핑.

    Args:
        avg_sentiment: 평균 감성 점수 (-1.0 ~ 1.0)
        news_volume: 뉴스 건수

    Returns:
        float: 트렌드 점수 (-1.0 ~ 1.0)
    """
    raw = avg_sentiment * 0.7 + math.log(news_volume + 1) * 0.3
    return max(-1.0, min(1.0, raw))


async def aggregate_sector_trends(db: AsyncSession, trade_date: date) -> int:
    """주어진 날짜의 AnalysisResult를 집계해 sector_trends에 upsert.

    섹터 태그가 비어있는 기사는 건너뛴다.
    멀티 태그 기사(예: ["IT", "바이오"])는 각 섹터에 독립적으로 집계된다.
    해당 날짜 데이터가 없으면 0을 반환하고 행을 생성하지 않는다.

    upsert 충돌 키: uq_sector_trends_sector_date (sector, trade_date)
    충돌 시 news_volume, avg_sentiment, trend_score, computed_at 업데이트.

    Args:
        db: 비동기 DB 세션
        trade_date: 집계 대상 날짜

    Returns:
        int: upsert된 섹터 수
    """
    # trade_date에 해당하는 기사 분석 결과 조회
    # Article.published_at 기준으로 해당 날짜 필터링
    day_start = datetime(trade_date.year, trade_date.month, trade_date.day, 0, 0, 0, tzinfo=timezone.utc)
    day_end = datetime(trade_date.year, trade_date.month, trade_date.day, 23, 59, 59, tzinfo=timezone.utc)

    stmt = (
        select(AnalysisResult)
        .join(Article, AnalysisResult.article_id == Article.id)
        .where(
            Article.published_at >= day_start,
            Article.published_at <= day_end,
        )
    )
    result = await db.execute(stmt)
    analyses = result.scalars().all()

    if not analyses:
        log.info("섹터 집계: 해당 날짜 데이터 없음", trade_date=str(trade_date))
        return 0

    # 섹터별 감성 점수 누적
    sector_sentiments: dict[str, list[float]] = defaultdict(list)
    for analysis in analyses:
        if not analysis.sector_tags:
            continue
        for sector in analysis.sector_tags:
            sector_sentiments[sector].append(float(analysis.sentiment_score))

    if not sector_sentiments:
        log.info("섹터 집계: 유효한 섹터 태그 없음", trade_date=str(trade_date))
        return 0

    # 섹터별 집계값 계산 및 upsert
    trade_date_dt = datetime(
        trade_date.year, trade_date.month, trade_date.day, 0, 0, 0, tzinfo=timezone.utc
    )

    rows = []
    for sector, sentiments in sector_sentiments.items():
        news_volume = len(sentiments)
        avg_sentiment = sum(sentiments) / news_volume
        trend_score = _compute_trend_score(avg_sentiment, news_volume)
        rows.append({
            "sector": sector,
            "trade_date": trade_date_dt,
            "news_volume": news_volume,
            "avg_sentiment": round(avg_sentiment, 3),
            "trend_score": round(trend_score, 3),
        })

    # PostgreSQL upsert: 충돌 시 업데이트
    upsert_stmt = pg_insert(SectorTrend).values(rows)
    upsert_stmt = upsert_stmt.on_conflict_do_update(
        constraint="uq_sector_trends_sector_date",
        set_={
            "news_volume": upsert_stmt.excluded.news_volume,
            "avg_sentiment": upsert_stmt.excluded.avg_sentiment,
            "trend_score": upsert_stmt.excluded.trend_score,
            "computed_at": datetime.now(tz=timezone.utc),
        },
    )

    await db.execute(upsert_stmt)

    count = len(rows)
    log.info("섹터 트렌드 집계 완료", trade_date=str(trade_date), sector_count=count)
    return count
