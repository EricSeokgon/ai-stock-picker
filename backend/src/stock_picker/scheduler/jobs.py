# APScheduler 배치 잡 설정 - 일일 파이프라인 및 장중 30분 증분 스케줄링
# REQ-NEWS-001: 일 1회(06:00) 전체 수집 배치
# REQ-NEWS-002: 장중 09:00~15:30 매 30분 증분 수집
import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

log = structlog.get_logger()

# @MX:NOTE: [AUTO] 스케줄러는 모듈 레벨 싱글톤이 아닌 setup_scheduler()가 반환하는 인스턴스 사용
# 테스트 시 setup_scheduler()를 직접 호출해 독립 인스턴스를 생성한다.

scheduler = AsyncIOScheduler()


async def collect_all() -> list:
    """뉴스 수집 파이프라인 실행.

    CollectorService를 사용해 모든 소스에서 기사를 수집한다 (REQ-NEWS-001).
    """
    from stock_picker.collectors.service import CollectorService
    from stock_picker.db.session import AsyncSessionLocal

    log.info("뉴스 수집 시작")
    async with AsyncSessionLocal() as session:
        svc = CollectorService(session)
        articles = await svc.collect_all()
        await session.commit()
    log.info("뉴스 수집 완료", count=len(articles))
    return articles


async def run_analysis() -> None:
    """분석 워커 실행.

    수집된 기사를 Claude API로 분석한다.
    """
    from stock_picker.analysis.worker import AnalysisWorker
    from stock_picker.db.session import AsyncSessionLocal

    log.info("분석 워커 시작")
    async with AsyncSessionLocal() as session:
        worker = AnalysisWorker(session)
        await worker.run()
        await session.commit()
    log.info("분석 워커 완료")


async def run_recommendation() -> None:
    """추천 파이프라인 실행.

    스코어 계산 후 Redis에 결과를 캐시한다.
    """
    import os

    import redis.asyncio as aioredis

    from stock_picker.db.session import AsyncSessionLocal
    from stock_picker.recommendation.cache import RecommendationCache
    from stock_picker.recommendation.service import RecommendationService

    log.info("추천 파이프라인 시작")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_client = aioredis.from_url(redis_url, decode_responses=True)
    cache = RecommendationCache(redis_client)

    async with AsyncSessionLocal() as session:
        svc = RecommendationService(cache=cache)
        result = await svc.run(session)
        await session.commit()

    await redis_client.aclose()
    log.info("추천 파이프라인 완료", count=len(result))


async def run_daily_pipeline() -> None:
    """일일 파이프라인: 수집 → 분석 → 추천 (REQ-NEWS-001).

    오전 6시에 APScheduler가 호출한다.
    각 단계는 순서대로 실행되며, 단계 실패 시 이후 단계도 중단된다.
    """
    log.info("일일 파이프라인 시작")
    try:
        await collect_all()
        await run_analysis()
        await run_recommendation()
        log.info("일일 파이프라인 완료")
    except Exception:
        log.exception("일일 파이프라인 오류 발생")
        raise


async def run_intraday_pipeline() -> None:
    """장중 30분 증분 파이프라인 (REQ-NEWS-002, REQ-REC-006).

    09:00~15:30 매 30분마다 APScheduler가 호출한다.
    증분 수집 → 분석 → 추천 재계산 순서로 실행한다.
    """
    log.info("장중 증분 파이프라인 시작")
    try:
        await collect_all()
        await run_analysis()
        await run_recommendation()
        log.info("장중 증분 파이프라인 완료")
    except Exception:
        log.exception("장중 증분 파이프라인 오류 발생")
        raise


def setup_scheduler() -> AsyncIOScheduler:
    """일 배치 + 장중 30분 증분 스케줄 등록 후 스케줄러 인스턴스 반환.

    # @MX:ANCHOR: [AUTO] 스케줄러 설정 진입점 - app lifespan에서 호출
    # @MX:REASON: FastAPI 앱 시작 시 단 한번 호출되는 스케줄러 설정 함수

    등록되는 잡:
    - daily_collection: 매일 06:00 KST 전체 배치 (REQ-NEWS-001)
    - intraday_collection: 09:00~15:xx 매 30분 증분 (REQ-NEWS-002)
    """
    # 매 호출마다 새 인스턴스를 반환해 테스트 격리를 보장
    _scheduler = AsyncIOScheduler()

    # 일 배치: 매일 06:00 KST
    _scheduler.add_job(
        run_daily_pipeline,
        CronTrigger(hour=6, minute=0, timezone="Asia/Seoul"),
        id="daily_collection",
        replace_existing=True,
    )

    # 장중 30분 증분: 09:00~15:xx 매 30분 (REQ-NEWS-002)
    _scheduler.add_job(
        run_intraday_pipeline,
        CronTrigger(hour="9-15", minute="*/30", timezone="Asia/Seoul"),
        id="intraday_collection",
        replace_existing=True,
    )

    return _scheduler
