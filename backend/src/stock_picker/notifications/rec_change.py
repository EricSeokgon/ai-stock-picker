# 추천 변동 감지 — 전일 대비 신규/탈락 종목 탐지 후 인박스 알림 생성 (SPEC-STOCK-013 M3)
import logging
from datetime import date

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from stock_picker.db.models import (
    EmailSubscription,
    Notification,
    Recommendation,
    TelegramSubscription,
    User,
    WatchlistItem,
)
from stock_picker.db.session import SyncSessionLocal
from stock_picker.notifications.email_service import send_general_alert_email
from stock_picker.notifications.preferences import is_channel_enabled_sync
from stock_picker.telegram.notifier import _send_message_sync

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


def _get_scores_for_date(db: Session, trade_date: date) -> dict[str, float]:
    """특정 trade_date의 {krx_code: total_score} 매핑 반환."""
    result = db.execute(
        select(Recommendation.krx_code, Recommendation.total_score).where(
            Recommendation.trade_date == trade_date
        )
    )
    return {row[0]: float(row[1]) for row in result if row[1] is not None}


def check_rec_score_changes() -> None:
    """가장 최근 두 trade_date 간 추천 점수 변화(|delta| >= 0.2)를 감지해 알림 생성.

    # @MX:ANCHOR: [AUTO] 추천 점수 변화 감지 진입점 — scheduler/jobs.py에서 호출
    # @MX:REASON: run_daily_pipeline, run_intraday_pipeline에서 직접 호출되는 공개 함수
    # @MX:SPEC: SPEC-STOCK-023 REQ-023-013~019

    REQ-023-013~019:
    - 두 날짜 모두에 존재하는 종목만 비교 (REQ-023-014)
    - |delta| >= 0.2 이상만 알림 발송 (REQ-023-015)
    - 관심종목 등록자만 알림 수신 (REQ-023-016)
    - UNIQUE 제약으로 intraday 중복 실행 안전 (REQ-023-019)
    - trade_date 가 2개 미만이면 조용히 종료 (REQ-023-018)
    """
    _SCORE_DELTA_THRESHOLD = 0.2

    with SyncSessionLocal() as db:
        dates = _get_latest_two_trade_dates(db)

        if len(dates) < 2:
            logger.info("rec_score_change: trade_date 가 2개 미만 — 비교 건너뜀")
            return

        new_date, prev_date = dates[0], dates[1]
        new_scores = _get_scores_for_date(db, new_date)
        prev_scores = _get_scores_for_date(db, prev_date)

        created = 0
        changed_count = 0

        for krx_code, new_score in new_scores.items():
            if krx_code not in prev_scores:
                continue
            prev_score = prev_scores[krx_code]
            delta = new_score - prev_score
            if abs(delta) < _SCORE_DELTA_THRESHOLD:
                continue

            changed_count += 1
            user_ids = _get_users_watching(db, krx_code)
            body_text = (
                f"추천 점수: {prev_score:.2f} → {new_score:.2f} ({delta:+.2f}), "
                f"기준일: {new_date}"
            )
            for uid in user_ids:
                _insert_notification_safe(
                    db,
                    user_id=uid,
                    ntype="rec_score_change",
                    krx_code=krx_code,
                    title=f"[점수 변화] {krx_code} 추천 점수가 {delta:+.2f} 변경됐습니다.",
                    body=body_text,
                    ref_date=new_date,
                )
                created += 1

                # 이메일 채널 발송 (best-effort, REQ-PREF-DISPATCH-003)
                if is_channel_enabled_sync(db, uid, "rec_score_change", "email"):
                    try:
                        email_sub = db.query(EmailSubscription).filter(
                            EmailSubscription.user_id == uid,
                            EmailSubscription.is_active.is_(True),
                        ).first()
                        if email_sub:
                            send_general_alert_email(email_sub.email, krx_code, "rec_score_change", body_text)
                    except Exception as e:
                        logger.error("rec_score_change 이메일 발송 실패 user_id=%s: %s", uid, e)

                # 텔레그램 채널 발송 (best-effort, REQ-PREF-DISPATCH-004)
                if is_channel_enabled_sync(db, uid, "rec_score_change", "telegram"):
                    try:
                        tg_sub = db.query(TelegramSubscription).filter(
                            TelegramSubscription.user_id == uid,
                            TelegramSubscription.is_active.is_(True),
                        ).first()
                        if tg_sub:
                            _send_message_sync(tg_sub.chat_id, f"[{krx_code}] {body_text}")
                    except Exception as e:
                        logger.error("rec_score_change 텔레그램 발송 실패 user_id=%s: %s", uid, e)

        db.commit()

    logger.info(
        "rec_score_change: %s→%s 비교 완료 — 변화 종목 %d개 알림 %d건 생성",
        prev_date,
        new_date,
        changed_count,
        created,
    )


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
            body_text = f"기준일: {new_date}"
            for uid in user_ids:
                _insert_notification_safe(
                    db,
                    user_id=uid,
                    ntype="rec_new",
                    krx_code=krx_code,
                    title=f"[신규 추천] {krx_code} 종목이 추천 목록에 추가됐습니다.",
                    body=body_text,
                    ref_date=new_date,
                )
                created += 1

                # 이메일 채널 발송 (best-effort, REQ-PREF-DISPATCH-003)
                if is_channel_enabled_sync(db, uid, "rec_new", "email"):
                    try:
                        email_sub = db.query(EmailSubscription).filter(
                            EmailSubscription.user_id == uid,
                            EmailSubscription.is_active.is_(True),
                        ).first()
                        if email_sub:
                            send_general_alert_email(email_sub.email, krx_code, "rec_new", body_text)
                    except Exception as e:
                        logger.error("rec_change 이메일 발송 실패 user_id=%s: %s", uid, e)

                # 텔레그램 채널 발송 (best-effort, REQ-PREF-DISPATCH-004)
                if is_channel_enabled_sync(db, uid, "rec_new", "telegram"):
                    try:
                        tg_sub = db.query(TelegramSubscription).filter(
                            TelegramSubscription.user_id == uid,
                            TelegramSubscription.is_active.is_(True),
                        ).first()
                        if tg_sub:
                            _send_message_sync(tg_sub.chat_id, f"[{krx_code}] {body_text}")
                    except Exception as e:
                        logger.error("rec_change 텔레그램 발송 실패 user_id=%s: %s", uid, e)

        for krx_code in dropped:
            user_ids = _get_users_watching(db, krx_code)
            body_text = f"기준일: {new_date}"
            for uid in user_ids:
                _insert_notification_safe(
                    db,
                    user_id=uid,
                    ntype="rec_dropped",
                    krx_code=krx_code,
                    title=f"[추천 탈락] {krx_code} 종목이 추천 목록에서 제외됐습니다.",
                    body=body_text,
                    ref_date=new_date,
                )
                created += 1

                # 이메일 채널 발송 (best-effort, REQ-PREF-DISPATCH-003)
                if is_channel_enabled_sync(db, uid, "rec_dropped", "email"):
                    try:
                        email_sub = db.query(EmailSubscription).filter(
                            EmailSubscription.user_id == uid,
                            EmailSubscription.is_active.is_(True),
                        ).first()
                        if email_sub:
                            send_general_alert_email(email_sub.email, krx_code, "rec_dropped", body_text)
                    except Exception as e:
                        logger.error("rec_change 이메일 발송 실패 user_id=%s: %s", uid, e)

                # 텔레그램 채널 발송 (best-effort, REQ-PREF-DISPATCH-004)
                if is_channel_enabled_sync(db, uid, "rec_dropped", "telegram"):
                    try:
                        tg_sub = db.query(TelegramSubscription).filter(
                            TelegramSubscription.user_id == uid,
                            TelegramSubscription.is_active.is_(True),
                        ).first()
                        if tg_sub:
                            _send_message_sync(tg_sub.chat_id, f"[{krx_code}] {body_text}")
                    except Exception as e:
                        logger.error("rec_change 텔레그램 발송 실패 user_id=%s: %s", uid, e)

        db.commit()

    logger.info(
        "rec_change: %s→%s 비교 완료 — 신규 %d개 탈락 %d개 알림 %d건 생성",
        prev_date,
        new_date,
        len(added),
        len(dropped),
        created,
    )
