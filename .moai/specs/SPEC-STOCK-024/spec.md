# SPEC-STOCK-024 — 알림 채널 연결 (이메일 · 텔레그램)

## 메타데이터

- **SPEC ID**: SPEC-STOCK-024
- **제목**: 알림 채널 연결 — 이메일·텔레그램을 모든 알림 경로에 배선
- **상태**: draft
- **작성일**: 2026-06-16
- **우선순위**: High
- **의존성**: SPEC-STOCK-020 (alerts 테이블), SPEC-STOCK-023 (volume_spike, rec_score_change)
- **마이그레이션**: 없음 (0017 유지)

---

## 배경 및 동기

SPEC-020/023에서 구현한 `alerts` 테이블 기반 알림 시스템(`check_and_trigger_all_alerts`)과
추천 변동 감지(`check_rec_changes`, `check_rec_score_changes`)는 현재 **인박스(in-app) 채널만** 연결되어 있다.

반면 레거시 `watchlist_alerts` 경로(`_trigger_alert`)에서는 이메일·텔레그램 구독을 조회하여 발송한다.

이 SPEC의 목표는 모든 알림 경로에서 이메일·텔레그램 채널이 일관되게 동작하도록 배선을 완성하는 것이다.

또한 텔레그램 `_send_message_sync()` 함수가 현재 TODO 상태(로그만 출력)이므로 실제 Bot API 호출로 교체한다.

---

## 범위 (Scope)

### 포함

1. **텔레그램 실제 발송 구현** (`telegram/notifier.py`)
   - `_send_message_sync(chat_id, message)` — `requests.post` 로 Bot API 호출
   - TELEGRAM_BOT_TOKEN 미설정 시 silent skip

2. **alerts 알림 → 이메일 발송** (`notifications/general_alert_service.py`)
   - `_try_send_alert_email()` stub을 완성 — EmailSubscription 조회 후 발송
   - 신규 범용 이메일 포맷터 `send_general_alert_email()` 추가 (`email_service.py`)

3. **alerts 알림 → 텔레그램 발송** (`notifications/general_alert_service.py`)
   - alert 발동 시 TelegramSubscription 조회 후 `_send_message_sync()` 호출

4. **rec_change 알림 → 이메일·텔레그램 발송** (`notifications/rec_change.py`)
   - `check_rec_changes()` (rec_new, rec_dropped) — 관심목록 보유자에게 이메일·텔레그램 발송
   - `check_rec_score_changes()` (rec_score_change) — 관심목록 보유자에게 이메일·텔레그램 발송

5. **단위 테스트** (`tests/unit/test_channel_dispatch.py`)
   - 이메일/텔레그램 발송 mocking 검증 (SMTP 미설정 skip, 구독 없음 skip, 발송 실패 격리)

### 제외

- 신규 채널(SMS, 슬랙, 웹 푸시) 추가
- 채널 추상화 레이어 도입
- 사용자별 채널 선택 테이블 추가
- 스케줄러 비기동 문제 수정 (SPEC-022 범위)
- 자동매매, 마이그레이션 추가

---

## 요구사항 (EARS 형식)

### REQ-024-001 — 텔레그램 실제 발송
**When** `_send_message_sync(chat_id, message)`가 호출되면
**The system shall** `TELEGRAM_BOT_TOKEN` 환경변수를 읽어 Bot API(`https://api.telegram.org/bot{token}/sendMessage`)로 HTTP POST를 수행한다.

### REQ-024-002 — 텔레그램 Bot 미설정 silent skip
**When** `TELEGRAM_BOT_TOKEN`이 빈 문자열이거나 미설정이면
**The system shall** 경고 로그를 출력하고 발송을 skip하며 예외를 발생시키지 않는다.

### REQ-024-003 — 텔레그램 발송 실패 격리
**When** 텔레그램 Bot API 호출이 실패(네트워크 오류, 4xx/5xx)하면
**The system shall** 오류를 로그에 기록하고 False를 반환하며, 호출자의 실행을 중단시키지 않는다.

### REQ-024-004 — alerts 이메일 발송 (완성)
**When** `check_and_trigger_all_alerts()`에서 `target_price`, `surge_drop`, `volume_spike` 알림이 발동하면
**The system shall** 해당 user_id의 활성 `EmailSubscription`을 조회하여 이메일을 발송한다.

### REQ-024-005 — alerts 이메일 발송 미구독 skip
**When** 발동된 alert의 user_id에 활성 `EmailSubscription`이 없으면
**The system shall** 이메일 발송을 skip하고 인박스 알림은 정상 생성한다.

### REQ-024-006 — alerts 텔레그램 발송
**When** `check_and_trigger_all_alerts()`에서 알림이 발동하면
**The system shall** 해당 user_id의 활성 `TelegramSubscription`을 조회하여 메시지를 발송한다.

### REQ-024-007 — alerts 텔레그램 발송 미구독 skip
**When** 발동된 alert의 user_id에 활성 `TelegramSubscription`이 없으면
**The system shall** 텔레그램 발송을 skip하고 인박스 알림은 정상 생성한다.

### REQ-024-008 — alerts 채널 발송 실패 격리
**When** 이메일 또는 텔레그램 발송이 실패하면
**The system shall** 오류를 로그에 기록하고 나머지 채널 발송 및 alert 처리 루프를 계속 진행한다.

### REQ-024-009 — rec_change 이메일 발송
**When** `check_rec_changes()`가 `rec_new` 또는 `rec_dropped` 인박스 알림을 생성하면
**The system shall** 해당 user_id의 활성 `EmailSubscription`을 조회하여 이메일을 발송한다.

### REQ-024-010 — rec_score_change 이메일 발송
**When** `check_rec_score_changes()`가 `rec_score_change` 인박스 알림을 생성하면
**The system shall** 해당 user_id의 활성 `EmailSubscription`을 조회하여 이메일을 발송한다.

### REQ-024-011 — rec_change 텔레그램 발송
**When** `check_rec_changes()` 또는 `check_rec_score_changes()`가 인박스 알림을 생성하면
**The system shall** 해당 user_id의 활성 `TelegramSubscription`을 조회하여 메시지를 발송한다.

### REQ-024-012 — rec_change 채널 발송 실패 격리
**When** rec_change 채널 발송이 실패하면
**The system shall** 오류를 로그에 기록하고 다음 사용자/종목 처리를 계속한다.

### REQ-024-013 — 이메일 포맷 — 범용 알림
**When** `send_general_alert_email(to_email, krx_code, alert_type, message)`가 호출되면
**The system shall** 제목에 alert_type과 krx_code를 포함하고, 본문에 message를 포함하여 발송한다.

### REQ-024-014 — 하위 호환 보존
**Given** SPEC-024 구현 후
**When** 레거시 `_trigger_alert()` 경로의 테스트를 실행하면
**The system shall** 기존 이메일·텔레그램·인박스 동작이 변경 없이 통과한다.

### REQ-024-015 — 자동매매 제외
**Given** 본 SPEC 구현
**When** 코드를 검토하면
**The system shall** 매수/매도 주문, 자동 매매 로직이 존재하지 않는다.

---

## 수용 기준 (Given-When-Then)

### AC-1 — 텔레그램 실제 발송 (REQ-024-001)
- **Given** TELEGRAM_BOT_TOKEN이 설정된 환경
- **When** `_send_message_sync(chat_id=12345, message="테스트")`가 호출되면
- **Then** `https://api.telegram.org/bot{token}/sendMessage`로 POST 요청이 전송된다.

### AC-2 — 텔레그램 미설정 skip (REQ-024-002)
- **Given** TELEGRAM_BOT_TOKEN이 빈 문자열
- **When** `_send_message_sync()`가 호출되면
- **Then** HTTP 요청 없이 False가 반환되고 예외 없이 종료된다.

### AC-3 — alerts → 이메일 발송 (REQ-024-004, 005)
- **Given** user_id=1의 활성 EmailSubscription(email="a@b.com") 존재, target_price 알림 발동
- **When** `check_and_trigger_all_alerts()`가 실행되면
- **Then** `send_general_alert_email("a@b.com", ...)` 또는 유사 함수가 1회 호출된다.

### AC-4 — alerts → 텔레그램 발송 (REQ-024-006, 007)
- **Given** user_id=1의 활성 TelegramSubscription(chat_id=9999) 존재, volume_spike 알림 발동
- **When** `check_and_trigger_all_alerts()`가 실행되면
- **Then** `_send_message_sync(9999, ...)` 가 1회 호출된다.

### AC-5 — alerts 이메일 구독 없음 skip (REQ-024-005)
- **Given** user_id=2의 EmailSubscription 없음, surge_drop 알림 발동
- **When** `check_and_trigger_all_alerts()`가 실행되면
- **Then** 이메일 발송 함수가 호출되지 않고, 인박스 알림은 정상 생성된다.

### AC-6 — alerts 채널 실패 격리 (REQ-024-008)
- **Given** 텔레그램 발송이 예외를 던지는 환경
- **When** `check_and_trigger_all_alerts()`에서 alerts를 처리하면
- **Then** 텔레그램 오류가 로깅되고 인박스 알림이 생성되며 루프가 계속된다.

### AC-7 — rec_new → 이메일·텔레그램 발송 (REQ-024-009, 011)
- **Given** user_id=3의 활성 EmailSubscription, TelegramSubscription 존재
- **When** `check_rec_changes()`가 rec_new 알림을 생성하면
- **Then** 이메일 발송 함수와 _send_message_sync가 각 1회씩 호출된다.

### AC-8 — rec_score_change → 이메일·텔레그램 발송 (REQ-024-010, 011)
- **Given** user_id=4의 활성 EmailSubscription, TelegramSubscription 존재
- **When** `check_rec_score_changes()`가 rec_score_change 알림을 생성하면
- **Then** 이메일 발송 함수와 _send_message_sync가 각 1회씩 호출된다.

### AC-9 — rec_change 채널 실패 격리 (REQ-024-012)
- **Given** 이메일 발송이 SMTP 오류를 던지는 환경
- **When** `check_rec_changes()`가 rec_new 알림을 생성하면
- **Then** SMTP 오류가 로깅되고 인박스 알림이 생성되며 나머지 처리가 계속된다.

### AC-10 — 범용 이메일 포맷 (REQ-024-013)
- **Given** krx_code="005930", alert_type="volume_spike", message="거래량 3배 급증"
- **When** `send_general_alert_email()` 이 호출되면
- **Then** 발송 이메일 제목에 "005930"과 "volume_spike"가 포함된다.

### AC-11 — 하위 호환 (REQ-024-014)
- **Given** SPEC-024 구현 후
- **When** `uv run pytest tests/unit/test_general_alerts.py`를 실행하면
- **Then** 기존 테스트가 모두 통과한다.

---

## 기술 설계

### M1 — 텔레그램 실제 발송 (`telegram/notifier.py`)

```
_send_message_sync(chat_id, message):
  token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
  if not token:
      logger.warning("TELEGRAM_BOT_TOKEN 미설정")
      return False
  url = f"https://api.telegram.org/bot{token}/sendMessage"
  try:
      resp = requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=5)
      resp.raise_for_status()
      return True
  except Exception as e:
      logger.error(f"텔레그램 발송 실패: {e}")
      return False
```

### M2 — 이메일 범용 함수 (`notifications/email_service.py`)

```
send_general_alert_email(to_email, krx_code, alert_type, message):
  subject = f"[주식 알림] {krx_code} {alert_type} 발동"
  body = f"안녕하세요.\n\n{message}\n\n투자는 본인 책임입니다."
  _send_email(to_email, subject, body)
```

### M3 — alerts 채널 배선 (`notifications/general_alert_service.py`)

```
_try_send_alert_email(alert, message, session):
  sub = session.query(EmailSubscription).filter(
      EmailSubscription.user_id == alert.user_id,
      EmailSubscription.is_active == True,
  ).first()
  if sub:
      try:
          send_general_alert_email(sub.email, alert.krx_code, alert.alert_type, message)
      except Exception as e:
          logger.error(f"이메일 발송 실패: {e}")

_try_send_telegram(alert, message, session):
  sub = session.query(TelegramSubscription).filter(
      TelegramSubscription.user_id == alert.user_id,
      TelegramSubscription.is_active == True,
  ).first()
  if sub:
      _send_message_sync(sub.chat_id, f"[{alert.krx_code}] {message}")
```

### M4 — rec_change 채널 배선 (`notifications/rec_change.py`)

`check_rec_changes()` 및 `check_rec_score_changes()` 에서 `_insert_notification_safe()` 성공 후:
```
try:
    sub_email = session.query(EmailSubscription).filter(user_id == uid, is_active).first()
    if sub_email:
        send_general_alert_email(sub_email.email, krx_code, change_type, body)
except:
    logger.error(...)

try:
    sub_tg = session.query(TelegramSubscription).filter(user_id == uid, is_active).first()
    if sub_tg:
        _send_message_sync(sub_tg.chat_id, f"[{krx_code}] {body}")
except:
    logger.error(...)
```

### M5 — 테스트 (`tests/unit/test_channel_dispatch.py`)

Mock 대상:
- `requests.post` — 텔레그램 Bot API
- `stock_picker.notifications.email_service._send_email` — SMTP 실제 발송
- `stock_picker.db.models.EmailSubscription` / `TelegramSubscription` — DB 조회

---

## 마일스톤 체크리스트

### M1 — 텔레그램 실제 발송 구현 — Priority High
- [ ] `_send_message_sync` → requests.post Bot API 호출
- [ ] TELEGRAM_BOT_TOKEN 미설정 graceful skip
- [ ] 발송 실패 예외 격리

### M2 — 이메일 범용 함수 추가 — Priority High
- [ ] `send_general_alert_email(to_email, krx_code, alert_type, message)` 구현

### M3 — alerts 채널 배선 — Priority High
- [ ] `_try_send_alert_email()` stub 완성 (EmailSubscription 조회 + 발송)
- [ ] `_try_send_telegram()` 신규 추가 (TelegramSubscription 조회 + 발송)
- [ ] `check_and_trigger_all_alerts()` 에서 두 함수 호출

### M4 — rec_change 채널 배선 — Priority Medium
- [ ] `check_rec_changes()` → 이메일·텔레그램 발송 (rec_new, rec_dropped)
- [ ] `check_rec_score_changes()` → 이메일·텔레그램 발송 (rec_score_change)
- [ ] 각 발송 실패 예외 격리 (인박스 적재 보장)

### M5 — 단위 테스트 — Priority Medium
- [ ] `test_send_message_sync_실제발송` — requests.post mock
- [ ] `test_send_message_sync_미설정skip` — TELEGRAM_BOT_TOKEN 빈 문자열
- [ ] `test_alerts_이메일발송` — EmailSubscription 있을 때 발송
- [ ] `test_alerts_이메일없음skip` — EmailSubscription 없을 때 skip
- [ ] `test_alerts_텔레그램발송` — TelegramSubscription 있을 때 발송
- [ ] `test_alerts_채널실패격리` — 이메일 예외 시 루프 지속
- [ ] `test_rec_change_이메일텔레그램발송` — rec_new, rec_dropped
- [ ] `test_rec_score_change_채널발송` — rec_score_change
- [ ] 기존 테스트 통과 확인

---

## 제약사항

- 자동매매·매수/매도 주문: **영구 제외**
- 신규 마이그레이션: **없음** (기존 구독 테이블 재사용)
- 신규 채널(SMS/슬랙): **이 SPEC 제외**
- 채널 추상화 레이어: **이 SPEC 제외** (YAGNI)
- 스케줄러 비기동 수정: **이 SPEC 제외** (SPEC-022 범위)
- 테스트 명령: `uv run pytest`
- 코드 주석 언어: 한국어
- 커밋 메시지: 한국어
