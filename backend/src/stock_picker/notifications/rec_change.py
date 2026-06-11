# 추천 변동 감지 — 전일 대비 신규/탈락 종목 탐지 후 인박스 알림 생성 (SPEC-STOCK-013 M3)
import logging
from datetime import date

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from stock_picker.db.models import Notification, Recommendation, User, WatchlistItem
from stock_picker.db.session import SyncSessionLocal

logger = logging.getLogger(__name__)


def _get_latest_two_trade_dates(db: Session) -> list[date]:
    """recommendations 테이블에서 최신 trade_date 2개를 내림차순으로 반환."""
    result = db.execute(
        text("SELECT DISTINCT trade_date FROM recommendations ORDER BY trade_date DESC LIMIT 2")
    )
    rows = result.fetchall()
    return [row[0] for row in rows]


def _get_rec_codes_for_date(db: Session, trade_date: date) -> set[str]:
    """특정 trade_date에 추천된 KRX 종목코드 집합 반환."""
    result = db.execute(
        select(Recommendation.krx_code).where(Recommendation.trade_date == trade_date)
    )
    return {row[0] for row in result}


def _get_users_watching(db: Session, krx_code: str) -> list[int]:
    """관심 목록에 해당 종목을 보유한 사용자 ID 목록."""
    result = db.execute(
        select(WatchlistItem.user_id).where(WatchlistItem.krx_code == krx_code)
    )
    return [row[0] for row in result]


def _get_all_user_ids(db: Session) -> list[int]:
    """활성 사용자 ID 전체 목록."""
    result = db.execute(select(User.id).where(User.is_active.is_(True)))
    return [row[0] for row in result]


def _insert_notification_safe(
    db: Session,
    user_id: int,
    ntype: str,
    krx_code: str,
    title: str,
    body: str,
    ref_date: date,
) -> None:
    """UNIQUE 제약에 걸리면 조용히 건너뜀 (idempotent)."""
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    stmt = pg_insert(Notification).values(
        user_id=user_id,
        type=ntype,
        krx_code=krx_code,
        title=title,
        body=body,
        is_read=False,
        ref_date=ref_date,
    )
    # conflict → nothing (idempotent: 동일 날짜 중복 알림 방지)
    stmt = stmt.on_conflict_do_nothing(
        constraint="uq_notification_user_type_code_date"
    )
    db.execute(stmt)


def check_rec_changes() -> None:
    """가장 최근 두 trade_date 를 비교해 신규/탈락 알림을 인박스에 생성.

    REQ-RC-001~007:
    - 최신 2개 날짜가 없으면(첫 실행) 조용히 종료 (REQ-RC-006)
    - 관심종목 등록자만 알림 수신 (REQ-RC-003, REQ-RC-004)
    - UNIQUE 제약으로 intraday 중복 실행 안전 (REQ-RC-007)
    """
    # @MX:ANCHOR: [AUTO] 추천 변동 감지 진입점 — scheduler/jobs.py에서 호출
    # @MX:REASON: run_daily_pipeline, run_intraday_pipeline에서 직접 호출되는 공개 함수
    # @MX:SPEC: SPEC-STOCK-013 REQ-RC-001~007

    with SyncSessionLocal() as db:
        dates = _get_latest_two_trade_dates(db)

        if len(dates) < 2:
            # REQ-RC-006: 이전 날짜 데이터 없으면 건너뜀
            logger.info("rec_change: trade_date 가 2개 미만 — 비교 건너뜀")
            return

        new_date, prev_date = dates[0], dates[1]
        new_codes = _get_rec_codes_for_date(db, new_date)
        prev_codes = _get_rec_codes_for_date(db, prev_date)

        added = new_codes - prev_codes     # 신규 진입
        dropped = prev_codes - new_codes   # 탈락

        created = 0

        for krx_code in added:
            user_ids = _get_users_watching(db, krx_code)
            for uid in user_ids:
                _insert_notification_safe(
                    db,
                    user_id=uid,
                    ntype="rec_new",
                    krx_code=krx_code,
                    title=f"[신규 추천] {krx_code} 종목이 추천 목록에 추가됐습니다.",
                    body=f"기준일: {new_date}",
                    ref_date=new_date,
                )
                created += 1

        for krx_code in dropped:
            user_ids = _get_users_watching(db, krx_code)
            for uid in user_ids:
                _insert_notification_safe(
                    db,
                    user_id=uid,
                    ntype="rec_dropped",
                    krx_code=krx_code,
                    title=f"[추천 탈락] {krx_code} 종목이 추천 목록에서 제외됐습니다.",
                    body=f"기준일: {new_date}",
                    ref_date=new_date,
                )
                created += 1

        db.commit()

    logger.info(
        "rec_change: %s→%s 비교 완료 — 신규 %d개 탈락 %d개 알림 %d건 생성",
        prev_date,
        new_date,
        len(added),
        len(dropped),
        created,
    )
