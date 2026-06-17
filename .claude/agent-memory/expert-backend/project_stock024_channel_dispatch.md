---
name: project-stock024-channel-dispatch
description: SPEC-STOCK-024 채널 배선 구현 완료. Telegram Bot API HTTP 직접 호출, send_general_alert_email 신규 추가, alerts/rec_change 경로에 이중 채널 연결.
metadata:
  type: project
---

SPEC-STOCK-024 알림 채널 배선 M1~M5 완료 (2026-06-16).

**Why:** 기존 알림 시스템이 인박스(DB Notification 테이블)만 적재하고 이메일·텔레그램 실제 발송을 하지 않았음. 모든 alert 트리거 경로에 두 채널을 연결하는 작업.

**How to apply:** 유사한 채널 배선 작업 시 아래 패턴 참고.

## 구현 패턴

### M1 — `telegram/notifier.py`
- `_send_message_sync(chat_id, message) -> bool` 실제 구현
- `TELEGRAM_BOT_TOKEN` 환경변수 없으면 False 반환 (발송 skip)
- `requests.post` → `https://api.telegram.org/bot{token}/sendMessage`
- 예외 발생 시 False 반환 (미전파)

### M2 — `notifications/email_service.py`
- `send_general_alert_email(to_email, krx_code, alert_type, message) -> bool` 신규 추가
- 내부적으로 `_send_email` 헬퍼 호출

### M3 — `notifications/general_alert_service.py`
- `_try_send_alert_email(alert, message, session: AsyncSession)` → `async def`로 변경
- `_try_send_telegram(alert, message, session: AsyncSession)` 신규 추가
- `check_and_trigger_all_alerts`에서 `await` 두 함수 모두 호출

### M4 — `notifications/rec_change.py`
- `check_rec_changes()`, `check_rec_score_changes()` 루프 내부에 이메일·텔레그램 채널 추가
- 동기 Session 기반이므로 `db.query(EmailSubscription).filter(...).first()` 패턴

### M5 — `backend/tests/unit/test_channel_dispatch.py` 신규
- 12개 테스트 모두 통과
- `requests.post` mock, `AsyncMock` 세션 패턴 사용

## 주의사항
- `general_alert_service.py`는 `AsyncSession` 기반 → 채널 발송 함수도 `async def` 필수
- `rec_change.py`는 동기 `Session` 기반 → try/except 블록으로 직접 호출
- Python 3.11에서 `asyncio.coroutine`이 제거됨 → `AsyncMock(new_callable=AsyncMock)` 사용
