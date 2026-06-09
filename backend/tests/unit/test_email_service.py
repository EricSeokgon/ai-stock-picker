# 이메일 서비스 유닛 테스트 — SMTP mock 및 구독 CRUD 검증
import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from stock_picker.db.models import EmailSubscription
from stock_picker.notifications import email_service
from stock_picker.notifications.email_service import DISCLAIMER


def _make_sub(id: int = 1, user_id: int = 1, email: str = "test@example.com") -> EmailSubscription:
    """테스트용 EmailSubscription 인스턴스 생성"""
    sub = EmailSubscription()
    sub.id = id
    sub.user_id = user_id
    sub.email = email
    sub.is_active = True
    sub.created_at = datetime(2024, 1, 1)
    return sub


class TestSendPriceAlertEmail:
    """send_price_alert_email 테스트"""

    def test_success_with_mock_smtp(self):
        """mock SMTP로 발송 성공 시 True 반환"""
        with (
            patch.dict(os.environ, {
                "SMTP_HOST": "smtp.example.com",
                "SMTP_PORT": "587",
                "SMTP_USER": "user@example.com",
                "SMTP_PASSWORD": "secret",
                "SMTP_FROM": "noreply@example.com",
            }),
            patch("smtplib.SMTP") as mock_smtp,
        ):
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            result = email_service.send_price_alert_email(
                to_email="dest@example.com",
                krx_code="005930",
                target_price=80000.0,
                direction="above",
                current_price=82000.0,
            )

        assert result is True
        mock_server.sendmail.assert_called_once()

    def test_skips_when_no_smtp_host(self):
        """SMTP_HOST 미설정 시 False 반환 (조용히 건너뜀)"""
        # SMTP_HOST 환경변수 제거
        env = {k: v for k, v in os.environ.items() if k != "SMTP_HOST"}
        with patch.dict(os.environ, env, clear=True):
            result = email_service.send_price_alert_email(
                to_email="dest@example.com",
                krx_code="005930",
                target_price=80000.0,
                direction="above",
                current_price=82000.0,
            )

        assert result is False

    def test_returns_false_on_smtp_error(self):
        """SMTP 오류 발생 시 False 반환 (예외 미전파)"""
        with (
            patch.dict(os.environ, {"SMTP_HOST": "smtp.example.com"}),
            patch("smtplib.SMTP", side_effect=ConnectionRefusedError("연결 거부")),
        ):
            result = email_service.send_price_alert_email(
                to_email="dest@example.com",
                krx_code="005930",
                target_price=80000.0,
                direction="below",
                current_price=75000.0,
            )

        assert result is False

    def test_weekly_summary_includes_disclaimer(self):
        """주간 요약 이메일 본문에 면책 조항 포함"""
        captured_body: list[str] = []

        def fake_send(to, subject, body):
            captured_body.append(body)
            return True

        with patch.object(email_service, "_send_email", side_effect=fake_send):
            email_service.send_weekly_summary_email(
                to_email="dest@example.com",
                recommendations=[
                    {"name": "삼성전자", "krx_code": "005930", "score": 0.85},
                ],
            )

        assert len(captured_body) == 1
        assert DISCLAIMER in captured_body[0]

    def test_weekly_summary_formats_top5(self):
        """주간 요약 이메일: 최대 5개 항목만 포함"""
        captured_body: list[str] = []

        def fake_send(to, subject, body):
            captured_body.append(body)
            return True

        recs = [
            {"name": f"종목{i}", "krx_code": f"00{i:04d}", "score": 0.9 - i * 0.05}
            for i in range(7)
        ]

        with patch.object(email_service, "_send_email", side_effect=fake_send):
            email_service.send_weekly_summary_email(
                to_email="dest@example.com",
                recommendations=recs,
            )

        body = captured_body[0]
        # 5개 항목만 번호로 포함 (6, 7번째 항목 없어야 함)
        assert "  5." in body
        assert "  6." not in body


class TestSubscribeEmail:
    """subscribe_email 테스트"""

    def test_creates_new_subscription(self):
        """신규 구독 생성"""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        captured: list[EmailSubscription] = []

        def capture_add(obj):
            captured.append(obj)

        db.add.side_effect = capture_add

        email_service.subscribe_email(user_id=1, email="new@example.com", db=db)

        assert len(captured) == 1
        assert captured[0].email == "new@example.com"
        assert captured[0].is_active is True
        db.commit.assert_called_once()

    def test_reactivates_existing_subscription(self):
        """기존 구독 비활성화 상태에서 재활성화"""
        db = MagicMock()
        existing = _make_sub()
        existing.is_active = False
        db.query.return_value.filter.return_value.first.return_value = existing

        result = email_service.subscribe_email(user_id=1, email="updated@example.com", db=db)

        assert existing.email == "updated@example.com"
        assert existing.is_active is True
        db.commit.assert_called_once()


class TestUnsubscribeEmail:
    """unsubscribe_email 테스트"""

    def test_deactivates_subscription(self):
        """구독 is_active=False 처리"""
        db = MagicMock()
        sub = _make_sub()
        db.query.return_value.filter.return_value.first.return_value = sub

        email_service.unsubscribe_email(user_id=1, db=db)

        assert sub.is_active is False
        db.commit.assert_called_once()

    def test_no_error_when_no_subscription(self):
        """구독 없어도 오류 없이 처리"""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        # 예외 발생하지 않아야 함
        email_service.unsubscribe_email(user_id=99, db=db)

        db.commit.assert_not_called()
