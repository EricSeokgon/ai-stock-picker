# SPEC-STOCK-024 — Research

## 분석 대상

SPEC-024: 알림 채널 확장 — 이메일/텔레그램 채널을 모든 알림 경로에 연결

작성일: 2026-06-16

---

## 1. 현재 채널 구현 현황

### 1.1 채널 구현체 위치

| 채널 | 파일 | 상태 |
|------|------|------|
| 이메일 (SMTP) | `backend/src/stock_picker/notifications/email_service.py` | 구현 완료 |
| 텔레그램 | `backend/src/stock_picker/telegram/notifier.py` + `bot.py` | 구현 완료 (stub 포함) |
| 인박스 | `backend/src/stock_picker/notifications/inbox_router.py` | 구현 완료 |

### 1.2 이메일 채널 (`email_service.py`)

주요 함수:
- `_get_smtp_config()` — 환경변수에서 SMTP 설정 로드, SMTP_HOST 미설정 시 None 반환 (graceful degradation)
- `_send_email(to_email, subject, body)` — smtplib STARTTLS 발송
- `send_price_alert_email(to_email, krx_code, target_price, direction, current_price)` — 가격 알림 이메일
- `send_weekly_summary_email(to_email, recommendations)` — 주간 요약 이메일

필요한 추가 함수:
- `send_general_alert_email(to_email, krx_code, alert_type, message)` — 범용 알림 이메일 (신규)
- `send_rec_change_email(to_email, krx_code, change_type, body)` — 추천 변동 이메일 (신규)

### 1.3 텔레그램 채널 (`notifier.py`, `bot.py`)

주요 함수:
- `_send_message_sync(chat_id, message)` — 동기 메시지 발송 (현재: 로그만 찍고 실제 발송 TODO)
- `notify_subscribers_sync(db, recommendations)` — 전체 구독자에게 추천 브로드캐스트

현황:
- `_send_message_sync`는 **실제 HTTP 전송 없이 로그만 출력** (TODO 상태)
- 실제 Bot API 호출 로직 미구현 → SPEC-024에서 실제 발송 구현 필요

### 1.4 DB 구독 테이블

```sql
-- 이메일 구독
email_subscriptions (id, user_id UNIQUE, email, is_active, created_at)

-- 텔레그램 구독
telegram_subscriptions (id, user_id, chat_id UNIQUE, is_active, subscribed_at)
```

---

## 2. 알림 발송 경로 분석

### 2.1 경로 A: watchlist_alerts (레거시 가격 알림)
**파일**: `scheduler/jobs.py` → `_trigger_alert()`

```
watchlist_alerts.check_price_alerts()
  → _trigger_alert(alert, price, db)
      ├─ TelegramSubscription 조회 → _send_message_sync()    ✅ 이메일 발송
      ├─ EmailSubscription 조회 → send_price_alert_email()  ✅ 텔레그램 발송
      └─ notifications INSERT (type='price_alert')           ✅ 인박스
```

**상태**: 세 채널 모두 연결됨 (단, 텔레그램 _send_message_sync 실제 발송 미구현)

### 2.2 경로 B: alerts 테이블 (SPEC-020/023 신규 알림)
**파일**: `notifications/general_alert_service.py` → `check_and_trigger_all_alerts()`

```
check_and_trigger_all_alerts(session)
  → market hours gate (09:00~15:30 KST)
  → FOR each alert: target_price | surge_drop | volume_spike
    → IF triggered:
        ├─ Alert.is_triggered = True                          ✅
        ├─ Notification INSERT                                ✅ 인박스
        ├─ _try_send_alert_email() [STUB — 실제 미구현]       ❌ 이메일 미연결
        └─ 텔레그램 발송 없음                                  ❌ 텔레그램 미연결
```

**상태**: 인박스만 연결, 이메일/텔레그램 미구현

현재 `_try_send_alert_email()` 함수:
```python
def _try_send_alert_email(alert: Alert, message: str, session) -> None:
    # TODO: 이메일 구독 조회 후 발송
    pass
```

### 2.3 경로 C: rec_change 알림 (SPEC-013/023)
**파일**: `notifications/rec_change.py`

```
check_rec_changes(session)         → rec_new | rec_dropped
check_rec_score_changes(session)   → rec_score_change

두 함수 모두:
  → notifications INSERT (인박스)   ✅ 인박스
  → 이메일/텔레그램 발송 없음        ❌ 두 채널 모두 미연결
```

---

## 3. 텔레그램 실제 발송 구현 현황

`backend/src/stock_picker/telegram/notifier.py`:

```python
def _send_message_sync(chat_id: int, message: str) -> bool:
    # TODO: 실제 텔레그램 Bot API 호출 구현
    logger.info(f"[텔레그램 TODO] chat_id={chat_id}: {message}")
    return True
```

실제 발송을 위해서는:
- `python-telegram-bot` 또는 직접 `requests`로 Bot API 호출
- `TELEGRAM_BOT_TOKEN` 환경변수 활용
- URL: `https://api.telegram.org/bot{token}/sendMessage`
- 파라미터: `chat_id`, `text`, `parse_mode=HTML` (선택)

**권장 방식**: `requests.post()` 사용 (의존성 최소화, `requests`는 이미 사용 중)

---

## 4. 환경변수 현황

```bash
# 이메일
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=

# 텔레그램
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=   # 현재: 글로벌 설정 (미사용, per-user는 DB에서)
```

미설정 시 graceful degradation 패턴 유지 필요.

---

## 5. 구독 관리 API 현황

현재 구독 관리 라우터:
- `POST /notifications/email` — 이메일 구독 (upsert)
- `DELETE /notifications/email` — 이메일 구독 해제
- 텔레그램 구독 API: `/telegram/` 라우터에 있음 (존재 여부 확인 필요)

---

## 6. 마이그레이션 현황

최신 마이그레이션: `0017_alerts.py` (SPEC-020)

SPEC-024에서 새 DB 테이블/컬럼 불필요:
- `email_subscriptions`는 이미 존재
- `telegram_subscriptions`는 이미 존재
- 채널 발송 로직만 추가하면 되므로 마이그레이션 없음

---

## 7. 테스트 파일 현황

관련 기존 테스트:
- `tests/unit/test_general_alerts.py` — check_and_trigger_all_alerts 테스트
- `tests/unit/test_volume_spike.py` — volume_spike, rec_score_change 테스트

SPEC-024에서 추가/수정할 테스트:
- `tests/unit/test_channel_dispatch.py` (신규) — 이메일/텔레그램 채널 발송 단위 테스트
- `tests/unit/test_general_alerts.py` (수정) — 이메일/텔레그램 발송 경로 추가 검증

---

## 8. 핵심 의존성 관계

```
SPEC-024 구현 시 수정 대상:
  notifications/general_alert_service.py  ← _try_send_alert_email() 완성
  notifications/rec_change.py             ← 이메일/텔레그램 발송 추가
  telegram/notifier.py                    ← _send_message_sync() 실제 구현
  notifications/email_service.py          ← 범용 알림 이메일 함수 추가

신규 파일 없음 (기존 파일 확장만)
마이그레이션 없음 (기존 구독 테이블 재사용)
```

---

## 9. 비-목표 (Non-Goals)

- SMS/슬랙/디스코드 등 신규 채널 추가 — 별도 SPEC
- 채널 추상화 레이어(Channel ABC) 도입 — 불필요한 복잡도
- 사용자별 채널 선택 테이블 (`user_channel_preferences`) — 별도 SPEC
- 자동매매/매수매도 주문 — 영구 제외
- 웹 푸시 알림 — 별도 SPEC
- 스케줄러 비기동 문제 수정 (SPEC-022 범위) — 이 SPEC 제외
