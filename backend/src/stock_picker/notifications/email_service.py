# 이메일 서비스 — SMTP를 통한 가격 알림 및 주간 요약 메일 발송
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from stock_picker.db.models import EmailSubscription

logger = logging.getLogger(__name__)

# 투자 면책 조항 — 모든 이메일에 포함
DISCLAIMER = (
    "본 메일은 투자 권유가 아닌 정보 제공 목적이며, "
    "수신을 원치 않으시면 /notifications/email DELETE 요청으로 구독을 해지할 수 있습니다."
)


# ── SMTP 설정 ──────────────────────────────────────────────────────────────────

def _get_smtp_config() -> dict | None:
    """환경변수에서 SMTP 설정 로드. SMTP_HOST 미설정 시 None 반환.

    # @MX:NOTE: [AUTO] SMTP 설정 미존재 시 None 반환 — 호출부에서 None 체크 필수
    """
    host = os.getenv("SMTP_HOST")
    if not host:
        return None
    return {
        "host": host,
        "port": int(os.getenv("SMTP_PORT", "587")),
        "user": os.getenv("SMTP_USER", ""),
        "password": os.getenv("SMTP_PASSWORD", ""),
        "from": os.getenv("SMTP_FROM", ""),
    }


def _send_email(to_email: str, subject: str, body: str) -> bool:
    """내부 이메일 발송 헬퍼.

    SMTP_HOST 미설정 시 조용히 False 반환.
    SMTP 오류 발생 시 로깅 후 False 반환 (예외 미전파).

    Returns:
        발송 성공 여부
    """
    config = _get_smtp_config()
    if config is None:
        logger.warning("SMTP_HOST 미설정 — 이메일 발송 건너뜀 (to=%s)", to_email)
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = config["from"]
        msg["To"] = to_email
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(config["host"], config["port"]) as server:
            server.ehlo()
            server.starttls()
            if config["user"]:
                server.login(config["user"], config["password"])
            server.sendmail(config["from"], [to_email], msg.as_string())

        logger.info("이메일 발송 완료 — to=%s, subject=%s", to_email, subject)
        return True
    except Exception:
        logger.error("이메일 발송 실패 — to=%s, subject=%s", to_email, subject, exc_info=True)
        return False


# ── 공개 이메일 발송 함수 ──────────────────────────────────────────────────────

def send_price_alert_email(
    to_email: str,
    krx_code: str,
    target_price: float,
    direction: str,
    current_price: float,
) -> bool:
    """목표가 도달 알림 이메일 발송.

    Args:
        to_email: 수신자 이메일
        krx_code: KRX 종목코드
        target_price: 목표가
        direction: "above" 또는 "below"
        current_price: 현재가

    Returns:
        발송 성공 여부
    """
    direction_label = "이상" if direction == "above" else "이하"
    subject = f"[주식 알림] {krx_code} 목표가 {target_price:,.0f}원 도달"
    body = (
        f"안녕하세요.\n\n"
        f"관심 종목 [{krx_code}]이(가) 목표가에 도달했습니다.\n\n"
        f"  - 종목코드: {krx_code}\n"
        f"  - 목표가: {target_price:,.0f}원 ({direction_label})\n"
        f"  - 현재가: {current_price:,.0f}원\n\n"
        f"{DISCLAIMER}"
    )
    return _send_email(to_email, subject, body)


def send_weekly_summary_email(
    to_email: str,
    recommendations: list[dict],
) -> bool:
    """주간 상위 5개 추천 종목 요약 이메일 발송.

    Args:
        to_email: 수신자 이메일
        recommendations: 추천 목록 (dict: name, krx_code, score 등)

    Returns:
        발송 성공 여부
    """
    subject = "[AI 주식 추천] 이번 주 상위 추천 종목 안내"
    lines = ["이번 주 AI 추천 상위 종목을 안내드립니다.\n"]
    for i, rec in enumerate(recommendations[:5], 1):
        krx_code = rec.get("krx_code", "N/A")
        name = rec.get("name", krx_code)
        score = rec.get("score", rec.get("total_score", 0))
        lines.append(f"  {i}. {name} ({krx_code}) — 점수: {float(score):.3f}")

    lines.append(f"\n{DISCLAIMER}")
    body = "\n".join(lines)
    return _send_email(to_email, subject, body)


# ── 이메일 구독 CRUD ───────────────────────────────────────────────────────────

def subscribe_email(user_id: int, email: str, db: Session) -> EmailSubscription:
    """이메일 구독 등록 또는 재활성화 (upsert).

    기존 구독이 있으면 이메일 갱신 + is_active=True로 업데이트.

    Args:
        user_id: 사용자 ID
        email: 구독 이메일
        db: SQLAlchemy 동기 세션

    Returns:
        EmailSubscription 인스턴스
    """
    existing = db.query(EmailSubscription).filter(
        EmailSubscription.user_id == user_id
    ).first()

    if existing:
        # 기존 구독 재활성화
        existing.email = email
        existing.is_active = True
        db.commit()
        db.refresh(existing)
        logger.info("이메일 구독 재활성화 — user_id=%d, email=%s", user_id, email)
        return existing

    sub = EmailSubscription(user_id=user_id, email=email, is_active=True)
    db.add(sub)
    db.commit()
    db.refresh(sub)
    logger.info("이메일 구독 등록 — user_id=%d, email=%s", user_id, email)
    return sub


def unsubscribe_email(user_id: int, db: Session) -> None:
    """이메일 구독 해지 (is_active=False).

    구독 정보가 없어도 오류 없이 처리.

    Args:
        user_id: 사용자 ID
        db: SQLAlchemy 동기 세션
    """
    sub = db.query(EmailSubscription).filter(
        EmailSubscription.user_id == user_id
    ).first()
    if sub is None:
        # 구독 없으면 조용히 반환
        logger.debug("이메일 구독 없음 — user_id=%d", user_id)
        return
    sub.is_active = False
    db.commit()
    logger.info("이메일 구독 해지 — user_id=%d", user_id)


def get_subscription(user_id: int, db: Session) -> EmailSubscription | None:
    """사용자의 이메일 구독 조회.

    Args:
        user_id: 사용자 ID
        db: SQLAlchemy 동기 세션

    Returns:
        EmailSubscription 인스턴스 또는 None
    """
    return db.query(EmailSubscription).filter(
        EmailSubscription.user_id == user_id
    ).first()
