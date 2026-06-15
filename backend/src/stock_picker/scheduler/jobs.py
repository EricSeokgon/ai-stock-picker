# APScheduler 배치 잡 설정 - 일일 파이프라인 및 장중 30분 증분 스케줄링
# REQ-NEWS-001: 일 1회(06:00) 전체 수집 배치
# REQ-NEWS-002: 장중 09:00~15:30 매 30분 증분 수집
import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

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
    새 추천 데이터 저장 후 파생 캐시(필터/정렬 결과)를 무효화한다.
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

    # 파생 캐시 무효화: 새 추천 데이터 반영을 위해 필터/정렬 결과 캐시 삭제
    await cache.invalidate_derived()

    await redis_client.aclose()
    log.info("추천 파이프라인 완료", count=len(result))


async def run_sector_aggregation() -> None:
    """섹터 트렌드 집계 실행.

    오늘 날짜의 AnalysisResult를 집계해 sector_trends에 upsert한다.
    실패 시 로그 기록 후 반환 — 파이프라인 진행 중단 없음.
    Redis 캐시 무효화도 수행 (Redis 장애 시 graceful degradation).
    """
    import os
    from datetime import date

    import redis.asyncio as aioredis

    from stock_picker.db.session import AsyncSessionLocal
    from stock_picker.sector.service import aggregate_sector_trends

    today = date.today()
    log.info("섹터 집계 시작", trade_date=str(today))

    try:
        async with AsyncSessionLocal() as session:
            count = await aggregate_sector_trends(session, today)
            await session.commit()
        log.info("섹터 집계 완료", trade_date=str(today), sector_count=count)
    except Exception:
        log.exception("섹터 집계 오류 — 파이프라인 계속 진행")
        return

    # Redis 캐시 무효화: sector_trends:* 패턴
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        redis_client = aioredis.from_url(redis_url, decode_responses=True)
        # sector_trends:* 및 sector_ranking:* 캐시 삭제
        async with redis_client as r:
            keys_trends = await r.keys("sector_trends:*")
            keys_ranking = await r.keys("sector_ranking:*")
            keys_detail = await r.keys("sector_detail:*")
            all_keys = keys_trends + keys_ranking + keys_detail
            if all_keys:
                await r.delete(*all_keys)
                log.info("섹터 캐시 무효화 완료", deleted_keys=len(all_keys))
    except Exception:
        log.warning("섹터 Redis 캐시 무효화 실패 — 무시하고 계속")


async def run_daily_pipeline() -> None:
    """일일 파이프라인: 수집 → 분석 → 섹터집계 → 추천 → 추천 변동 알림 (REQ-NEWS-001).

    오전 6시에 APScheduler가 호출한다.
    각 단계는 순서대로 실행되며, 섹터 집계 단계 실패 시 이후 단계도 계속된다.
    """
    from stock_picker.notifications.rec_change import check_rec_changes, check_rec_score_changes

    log.info("일일 파이프라인 시작")
    try:
        await collect_all()
        await run_analysis()
        await run_sector_aggregation()
        await run_recommendation()
        # REQ-RC-001: 추천 파이프라인 직후 변동 감지
        try:
            check_rec_changes()
        except Exception:
            log.exception("추천 변동 알림 생성 실패 — 파이프라인 계속 진행")
        # REQ-023-013: 추천 점수 변화 감지
        try:
            check_rec_score_changes()
        except Exception:
            log.exception("추천 점수 변화 알림 생성 실패 — 파이프라인 계속 진행")
        log.info("일일 파이프라인 완료")
    except Exception:
        log.exception("일일 파이프라인 오류 발생")
        raise


async def run_intraday_pipeline() -> None:
    """장중 30분 증분 파이프라인 (REQ-NEWS-002, REQ-REC-006).

    09:00~15:30 매 30분마다 APScheduler가 호출한다.
    증분 수집 → 분석 → 섹터집계 → 추천 재계산 → 추천 변동 알림 순서로 실행한다.
    """
    from stock_picker.notifications.rec_change import check_rec_changes, check_rec_score_changes

    log.info("장중 증분 파이프라인 시작")
    try:
        await collect_all()
        await run_analysis()
        await run_sector_aggregation()
        await run_recommendation()
        # UNIQUE 제약으로 같은 날 중복 생성 방지 (REQ-RC-007)
        try:
            check_rec_changes()
        except Exception:
            log.exception("추천 변동 알림 생성 실패 — 파이프라인 계속 진행")
        # REQ-023-013: 추천 점수 변화 감지 (UNIQUE 제약으로 intraday 중복 안전)
        try:
            check_rec_score_changes()
        except Exception:
            log.exception("추천 점수 변화 알림 생성 실패 — 파이프라인 계속 진행")
        log.info("장중 증분 파이프라인 완료")
    except Exception:
        log.exception("장중 증분 파이프라인 오류 발생")
        raise


def _trigger_alert(alert, current_price: float, db) -> None:
    """알림 발동 처리 — 텔레그램/이메일 발송 후 알림 비활성화.

    # @MX:NOTE: [AUTO] 동기 컨텍스트에서 호출 — DB 세션은 호출부에서 관리
    """
    from datetime import datetime

    from stock_picker.db.models import EmailSubscription, TelegramSubscription
    from stock_picker.notifications.email_service import send_price_alert_email
    from stock_picker.telegram.notifier import _send_message_sync

    # 1) 텔레그램 알림
    tg_sub = (
        db.query(TelegramSubscription)
        .filter(
            TelegramSubscription.user_id == alert.user_id,
            TelegramSubscription.is_active == True,  # noqa: E712
        )
        .first()
    )
    if tg_sub:
        direction_label = "이상" if alert.direction == "above" else "이하"
        msg = (
            f"관심 종목 {alert.krx_code}이(가) "
            f"목표가 {alert.target_price:,.0f}원에 도달했습니다. "
            f"(현재가: {current_price:,.0f}원, 방향: {direction_label})"
        )
        try:
            _send_message_sync(tg_sub.chat_id, msg)
        except Exception:
            log.exception("텔레그램 알림 발송 실패 — alert_id=%s", alert.id)

    # 2) 이메일 알림
    email_sub = (
        db.query(EmailSubscription)
        .filter(
            EmailSubscription.user_id == alert.user_id,
            EmailSubscription.is_active == True,  # noqa: E712
        )
        .first()
    )
    if email_sub:
        try:
            send_price_alert_email(
                to_email=email_sub.email,
                krx_code=alert.krx_code,
                target_price=alert.target_price,
                direction=alert.direction,
                current_price=current_price,
            )
        except Exception:
            log.exception("이메일 알림 발송 실패 — alert_id=%s", alert.id)

    # 3) 인박스 알림 생성 (REQ-PA-001)
    try:
        from stock_picker.db.models import Notification
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        ref_date = datetime.utcnow().date()
        stmt = pg_insert(Notification).values(
            user_id=alert.user_id,
            type="price_alert",
            krx_code=alert.krx_code,
            title=f"[가격 알림] {alert.krx_code} 목표가 도달",
            body=(
                f"현재가 {current_price:,.0f}원이 목표가 "
                f"{alert.target_price:,.0f}원에 도달했습니다."
            ),
            is_read=False,
            ref_date=ref_date,
            related_alert_id=alert.id,
        )
        stmt = stmt.on_conflict_do_nothing(
            constraint="uq_notification_user_type_code_date"
        )
        db.execute(stmt)
    except Exception:
        log.exception("인박스 알림 생성 실패 — alert_id=%s", alert.id)

    # 4) 알림 비활성화
    alert.is_active = False
    alert.triggered_at = datetime.utcnow()
    db.commit()
    log.info("가격 알림 발동 완료 — alert_id=%s, krx_code=%s", alert.id, alert.krx_code)


async def check_price_alerts() -> None:
    """활성 가격 알림을 현재가와 비교해 발동 여부 확인 — 5분 주기 실행.

    # @MX:WARN: [AUTO] DB 세션을 동기 방식으로 사용 — 비동기 스케줄러 내부에서 동기 쿼리 실행
    # @MX:REASON: FinanceDataReader가 동기 라이브러리이므로 전체 처리를 동기로 통일
    """
    from stock_picker.db.models import WatchlistAlert
    from stock_picker.db.session import SyncSessionLocal as SessionLocal
    from stock_picker.notifications.alert_service import evaluate_alert
    from stock_picker.realtime.price_feed import get_current_price

    db = SessionLocal()
    try:
        alerts = (
            db.query(WatchlistAlert)
            .filter(WatchlistAlert.is_active == True)  # noqa: E712
            .all()
        )
        log.info("가격 알림 점검 시작 — 활성 알림 수=%d", len(alerts))
        for alert in alerts:
            try:
                price_data = get_current_price(alert.krx_code)
                if price_data is None:
                    log.warning("가격 조회 실패: %s, 알림 %d 스킵", alert.krx_code, alert.id)
                    continue
                current_price = price_data["price"]
                if evaluate_alert(alert, current_price):
                    _trigger_alert(alert, current_price, db)
            except Exception:
                log.exception("알림 평가 오류 (id=%s)", alert.id)
    finally:
        db.close()


async def send_weekly_email_summary() -> None:
    """주간 상위 5개 추천 종목을 활성 이메일 구독자에게 발송 — 매주 월요일 07:00 KST"""
    from stock_picker.db.models import EmailSubscription, Recommendation
    from stock_picker.db.session import SyncSessionLocal as SessionLocal
    from stock_picker.notifications.email_service import send_weekly_summary_email

    db = SessionLocal()
    try:
        # 최신 추천 상위 5개 조회 (total_score 내림차순)
        recs = (
            db.query(Recommendation)
            .order_by(Recommendation.total_score.desc())
            .limit(5)
            .all()
        )
        if not recs:
            log.info("주간 요약: 추천 종목 없음 — 발송 건너뜀")
            return

        rec_dicts = [
            {
                "name": r.krx_code,
                "krx_code": r.krx_code,
                "score": float(r.total_score),
            }
            for r in recs
        ]

        # 활성 이메일 구독자 전체 발송
        subs = (
            db.query(EmailSubscription)
            .filter(EmailSubscription.is_active == True)  # noqa: E712
            .all()
        )
        log.info("주간 요약 발송 시작 — 구독자 수=%d", len(subs))
        for sub in subs:
            try:
                send_weekly_summary_email(sub.email, rec_dicts)
            except Exception:
                log.exception("주간 요약 메일 발송 실패 (email=%s)", sub.email)
    finally:
        db.close()


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

    # 가격 알림 점검: 5분마다 활성 알림 현재가 확인
    _scheduler.add_job(
        check_price_alerts,
        IntervalTrigger(minutes=5),
        id="check_price_alerts",
        replace_existing=True,
    )

    # 주간 이메일 요약: 매주 월요일 07:00 KST
    _scheduler.add_job(
        send_weekly_email_summary,
        CronTrigger(day_of_week="mon", hour=7, minute=0, timezone="Asia/Seoul"),
        id="weekly_email_summary",
        replace_existing=True,
    )

    # 일반 알림 점검: 10분마다 목표가·급등락 알림 확인 (SPEC-STOCK-020 REQ-ALERT-010)
    _scheduler.add_job(
        _run_general_alert_check,
        IntervalTrigger(minutes=10),
        id="check_alerts",
        replace_existing=True,
    )

    return _scheduler


async def _run_general_alert_check() -> None:
    """일반 알림(목표가·급등락) 점검 잡 — 10분 주기 실행.

    예외 발생 시 로그 기록 후 종료 (graceful degradation).
    """
    from stock_picker.db.session import AsyncSessionLocal
    from stock_picker.notifications.general_alert_service import check_and_trigger_all_alerts

    try:
        async with AsyncSessionLocal() as session:
            count = await check_and_trigger_all_alerts(session=session)
            log.info("일반 알림 점검 완료", triggered=count)
    except Exception:
        log.exception("일반 알림 점검 잡 오류 — 다음 주기에 재시도")
