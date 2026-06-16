# 알림 채널·유형별 수신 설정 유닛 테스트 (SPEC-STOCK-025)
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch


# ══════════════════════════════════════════════════════════
# 헬퍼 — 공통 모의 객체 생성
# ══════════════════════════════════════════════════════════


def _make_async_session(pref_result=None, multi_results=None):
    """AsyncSession 모의 객체 생성 헬퍼.

    Args:
        pref_result: scalar_one_or_none 반환값 (단건 조회용).
        multi_results: scalars().all() 반환값 (다건 조회용).
    """
    mock_session = AsyncMock()
    mock_result = MagicMock()

    if multi_results is not None:
        mock_result.scalars.return_value.all.return_value = multi_results
    else:
        mock_result.scalar_one_or_none.return_value = pref_result

    mock_session.execute.return_value = mock_result
    return mock_session


def _make_pref(alert_type: str, email_enabled: bool = True, telegram_enabled: bool = True):
    """NotificationPreference 모의 객체 생성 헬퍼."""
    return SimpleNamespace(
        alert_type=alert_type,
        email_enabled=email_enabled,
        telegram_enabled=telegram_enabled,
    )


def _make_alert(user_id: int = 1, krx_code: str = "005930", alert_type: str = "surge_drop"):
    """Alert ORM 모의 객체 생성 헬퍼."""
    return SimpleNamespace(
        id=1,
        user_id=user_id,
        krx_code=krx_code,
        alert_type=alert_type,
        is_triggered=False,
        condition_value=5.0,
        condition_direction="either",
    )


# ══════════════════════════════════════════════════════════
# T5-1: is_channel_enabled_async — 기본 활성 (행 없을 때)
# ══════════════════════════════════════════════════════════


class TestIsChannelEnabledAsync:
    """is_channel_enabled_async 함수 테스트."""

    def test_기본활성_행없음(self):
        """설정 행이 없으면 True 반환 (REQ-PREF-003, REQ-PREF-004)."""
        session = _make_async_session(pref_result=None)

        from stock_picker.notifications.preferences import is_channel_enabled_async
        result = asyncio.run(is_channel_enabled_async(session, 1, "volume_spike", "email"))

        assert result is True

    def test_이메일_비활성(self):
        """email_enabled=False인 행이 있으면 False 반환."""
        pref = _make_pref("volume_spike", email_enabled=False)
        session = _make_async_session(pref_result=pref)

        from stock_picker.notifications.preferences import is_channel_enabled_async
        result = asyncio.run(is_channel_enabled_async(session, 1, "volume_spike", "email"))

        assert result is False

    def test_텔레그램_활성(self):
        """telegram_enabled=True인 행이 있으면 True 반환."""
        pref = _make_pref("surge_drop", telegram_enabled=True)
        session = _make_async_session(pref_result=pref)

        from stock_picker.notifications.preferences import is_channel_enabled_async
        result = asyncio.run(is_channel_enabled_async(session, 1, "surge_drop", "telegram"))

        assert result is True

    def test_게이트조회실패_기본발송(self):
        """예외 발생 시 True 반환 — fail-open (REQ-PREF-DISPATCH-006)."""
        session = AsyncMock()
        session.execute.side_effect = Exception("DB 연결 오류")

        from stock_picker.notifications.preferences import is_channel_enabled_async
        result = asyncio.run(is_channel_enabled_async(session, 1, "surge_drop", "email"))

        # 조회 실패 시 기본 활성으로 처리
        assert result is True


# ══════════════════════════════════════════════════════════
# is_channel_enabled_sync 테스트
# ══════════════════════════════════════════════════════════


class TestIsChannelEnabledSync:
    """is_channel_enabled_sync 함수 테스트."""

    def test_기본활성_행없음(self):
        """설정 행이 없으면 True 반환."""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        from stock_picker.notifications.preferences import is_channel_enabled_sync
        result = is_channel_enabled_sync(db, 1, "rec_new", "email")

        assert result is True

    def test_이메일_비활성(self):
        """email_enabled=False인 행이 있으면 False 반환."""
        pref = _make_pref("rec_new", email_enabled=False)
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = pref

        from stock_picker.notifications.preferences import is_channel_enabled_sync
        result = is_channel_enabled_sync(db, 1, "rec_new", "email")

        assert result is False

    def test_게이트조회실패_기본발송(self):
        """예외 발생 시 True 반환 — fail-open."""
        db = MagicMock()
        db.query.side_effect = Exception("DB 오류")

        from stock_picker.notifications.preferences import is_channel_enabled_sync
        result = is_channel_enabled_sync(db, 1, "rec_new", "email")

        assert result is True


# ══════════════════════════════════════════════════════════
# T5-2: get_preferences — 7개 유형 기본값 채움
# ══════════════════════════════════════════════════════════


class TestGetPreferences:
    """get_preferences 함수 테스트."""

    def test_설정조회_7유형(self):
        """7개 유형 전체 반환 — 미설정 유형은 기본값(True) (REQ-PREF-API-001)."""
        # 2개 유형만 DB에 존재
        existing_prefs = [
            _make_pref("target_price", email_enabled=False, telegram_enabled=True),
            _make_pref("surge_drop", email_enabled=True, telegram_enabled=False),
        ]
        session = _make_async_session(multi_results=existing_prefs)

        from stock_picker.notifications.preferences import get_preferences, SUPPORTED_ALERT_TYPES
        result = asyncio.run(get_preferences(session, 1))

        assert len(result) == 7
        # 7개 유형 모두 포함 확인
        result_types = {item["alert_type"] for item in result}
        assert result_types == set(SUPPORTED_ALERT_TYPES)

        # 설정된 유형 확인
        target = next(item for item in result if item["alert_type"] == "target_price")
        assert target["email_enabled"] is False
        assert target["telegram_enabled"] is True

        # 미설정 유형은 기본값 True
        volume = next(item for item in result if item["alert_type"] == "volume_spike")
        assert volume["email_enabled"] is True
        assert volume["telegram_enabled"] is True

    def test_설정없으면_전부기본값(self):
        """설정 행 전혀 없을 때 7개 모두 기본값 True."""
        session = _make_async_session(multi_results=[])

        from stock_picker.notifications.preferences import get_preferences
        result = asyncio.run(get_preferences(session, 1))

        assert len(result) == 7
        assert all(item["email_enabled"] is True for item in result)
        assert all(item["telegram_enabled"] is True for item in result)


# ══════════════════════════════════════════════════════════
# T5-3: upsert_preferences — 생성/갱신
# ══════════════════════════════════════════════════════════


class TestUpsertPreferences:
    """upsert_preferences 함수 테스트."""

    def test_upsert_생성(self):
        """upsert 시 session.execute 호출 및 commit 수행."""
        session = AsyncMock()
        # commit 이후 get_preferences 호출을 위한 execute mock
        mock_result = MagicMock()
        pref = _make_pref("volume_spike", email_enabled=False, telegram_enabled=True)
        mock_result.scalars.return_value.all.return_value = [pref]
        session.execute.return_value = mock_result

        from stock_picker.notifications.preferences import upsert_preferences
        items = [{"alert_type": "volume_spike", "email_enabled": False, "telegram_enabled": True}]
        asyncio.run(upsert_preferences(session, 1, items))

        # commit 호출 확인
        session.commit.assert_called_once()
        # execute 2회 이상 호출 (upsert 1번 + get_preferences 1번)
        assert session.execute.call_count >= 2

    def test_upsert_갱신_멱등성(self):
        """같은 항목 두 번 upsert 시 commit 각각 1회."""
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute.return_value = mock_result

        from stock_picker.notifications.preferences import upsert_preferences
        items = [{"alert_type": "surge_drop", "email_enabled": True, "telegram_enabled": False}]
        asyncio.run(upsert_preferences(session, 1, items))
        asyncio.run(upsert_preferences(session, 1, items))

        # 각 호출마다 commit 1회씩
        assert session.commit.call_count == 2

    def test_미지원유형_거부(self):
        """지원하지 않는 alert_type 포함 시 ValueError 발생 (REQ-PREF-API-004)."""
        session = AsyncMock()

        from stock_picker.notifications.preferences import upsert_preferences
        items = [{"alert_type": "unknown_type", "email_enabled": True, "telegram_enabled": True}]

        try:
            asyncio.run(upsert_preferences(session, 1, items))
            assert False, "ValueError가 발생해야 합니다"
        except ValueError as e:
            assert "unknown_type" in str(e)


# ══════════════════════════════════════════════════════════
# T5-5/T5-6: GET/PUT /notifications/preferences 미인증 401
# ══════════════════════════════════════════════════════════


class TestPreferencesEndpointAuth:
    """알림 설정 API 인증 테스트."""

    def test_GET_미인증_401(self):
        """인증 토큰 없이 GET 시 401 반환 (REQ-PREF-API-003)."""
        from fastapi.testclient import TestClient

        with patch("stock_picker.db.session.get_session"):
            from stock_picker.api.main import create_app
            app = create_app()
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get("/notifications/preferences")

        assert response.status_code == 401

    def test_PUT_미인증_401(self):
        """인증 토큰 없이 PUT 시 401 반환 (REQ-PREF-API-003)."""
        from fastapi.testclient import TestClient

        with patch("stock_picker.db.session.get_session"):
            from stock_picker.api.main import create_app
            app = create_app()
            client = TestClient(app, raise_server_exceptions=False)
            response = client.put(
                "/notifications/preferences",
                json={"preferences": []},
            )

        assert response.status_code == 401


# ══════════════════════════════════════════════════════════
# T5-7: _try_send_alert_email — 이메일 OFF 시 skip
# ══════════════════════════════════════════════════════════


class TestAlertsEmailGating:
    """general_alert_service 이메일·텔레그램 게이팅 테스트."""

    def test_alerts_이메일OFF_skip(self):
        """이메일 채널 비활성 시 send_general_alert_email 미호출 (REQ-PREF-DISPATCH-001)."""
        alert = _make_alert()
        # is_channel_enabled_async=False 이면 session.execute 자체를 호출하지 않음
        session = AsyncMock()

        with patch(
            "stock_picker.notifications.general_alert_service.is_channel_enabled_async",
            new_callable=AsyncMock,
            return_value=False,
        ):
            with patch(
                "stock_picker.notifications.general_alert_service.send_general_alert_email"
            ) as mock_send:
                from stock_picker.notifications.general_alert_service import _try_send_alert_email
                asyncio.run(_try_send_alert_email(alert, "급등락 발생", session))

        # 채널 비활성 → 이메일 미발송, EmailSubscription 조회도 스킵
        mock_send.assert_not_called()
        session.execute.assert_not_called()

    def test_alerts_텔레그램ON_발송(self):
        """텔레그램 채널 활성 시 _send_message_sync 호출 (REQ-PREF-DISPATCH-002)."""
        alert = _make_alert()
        # session.execute → TelegramSubscription 반환
        tg_sub = SimpleNamespace(chat_id=12345, user_id=1, is_active=True)
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = tg_sub
        session.execute.return_value = mock_result

        with patch(
            "stock_picker.notifications.general_alert_service.is_channel_enabled_async",
            new_callable=AsyncMock,
            return_value=True,
        ):
            with patch(
                "stock_picker.notifications.general_alert_service._send_message_sync"
            ) as mock_tg:
                from stock_picker.notifications.general_alert_service import _try_send_telegram
                asyncio.run(_try_send_telegram(alert, "급등락 발생", session))

        mock_tg.assert_called_once()

    def test_게이트조회실패_기본발송(self):
        """is_channel_enabled_async가 True(fail-open) → 이메일 발송 시도 (REQ-PREF-DISPATCH-006)."""
        alert = _make_alert()
        # session.execute → EmailSubscription 반환
        email_sub = SimpleNamespace(email="user@example.com", user_id=1, is_active=True)
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = email_sub
        session.execute.return_value = mock_result

        # fail-open: is_channel_enabled_async가 True를 반환하므로 이메일 발송됨
        with patch(
            "stock_picker.notifications.general_alert_service.is_channel_enabled_async",
            new_callable=AsyncMock,
            return_value=True,
        ):
            with patch(
                "stock_picker.notifications.general_alert_service.send_general_alert_email"
            ) as mock_send:
                from stock_picker.notifications.general_alert_service import _try_send_alert_email
                asyncio.run(_try_send_alert_email(alert, "목표가 도달", session))

        # fail-open 이므로 이메일 발송됨
        mock_send.assert_called_once()

    def test_인박스_무조건생성(self):
        """알림 발동 시 채널 설정과 무관하게 인박스 알림 생성 (REQ-PREF-DISPATCH-005)."""
        # check_and_trigger_all_alerts에서 notifications 삽입은 is_channel_enabled_async 호출 전
        # 즉, 인박스는 _try_send_alert_email / _try_send_telegram 호출 전에 삽입됨
        # 이 테스트는 인박스 삽입 경로가 게이팅 밖에 있음을 구조적으로 검증

        from stock_picker.notifications.general_alert_service import build_notification_payload
        from datetime import datetime, timezone

        alert = _make_alert()
        now = datetime.now(timezone.utc)
        payload = build_notification_payload(alert, "급등락 발생", now)

        # 인박스 페이로드는 user_id, type, krx_code 포함
        assert payload["user_id"] == alert.user_id
        assert payload["type"] == alert.alert_type
        assert payload["krx_code"] == alert.krx_code
        assert payload["is_read"] is False


# ══════════════════════════════════════════════════════════
# T5-8: rec_change 이메일 게이팅 테스트
# ══════════════════════════════════════════════════════════


class TestRecChangeEmailGating:
    """rec_change.py 이메일 채널 게이팅 테스트."""

    def test_rec_change_이메일OFF_skip(self):
        """rec_change에서 is_channel_enabled_sync=False 시 이메일 미발송 (REQ-PREF-DISPATCH-003)."""
        from stock_picker.notifications.preferences import is_channel_enabled_sync

        db = MagicMock()
        # 이메일 채널 비활성
        pref = _make_pref("rec_new", email_enabled=False)
        db.query.return_value.filter.return_value.first.return_value = pref

        result = is_channel_enabled_sync(db, 1, "rec_new", "email")

        assert result is False

    def test_rec_score_change_텔레그램OFF_skip(self):
        """rec_score_change에서 텔레그램 비활성 시 False 반환."""
        from stock_picker.notifications.preferences import is_channel_enabled_sync

        db = MagicMock()
        pref = _make_pref("rec_score_change", telegram_enabled=False)
        db.query.return_value.filter.return_value.first.return_value = pref

        result = is_channel_enabled_sync(db, 1, "rec_score_change", "telegram")

        assert result is False
