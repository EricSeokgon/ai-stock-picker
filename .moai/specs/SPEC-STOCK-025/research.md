# SPEC-STOCK-025 연구 노트 — 알림 채널·유형 설정

작성일: 2026-06-16
대상: ai-stock-picker (한국 주식·ETF 추천 시스템)

---

## 1. 선정 근거 (왜 이 SPEC인가)

SPEC-024가 직전에 이메일·텔레그램 채널을 **모든** 알림 경로에 배선했다. 그 직접적 결과로
양쪽 채널을 등록한 사용자는 모든 알림 유형을 두 채널로 무조건 수신한다. **수신 제어 수단이
존재하지 않는다**. 이는 알림 시스템 아크(013 → 020 → 023 → 024)의 자연스러운 다음 공백이다.

후보 비교:

| 후보 | 사용자 가치 | 복잡도 | 단일 SPEC 적합성 | 판정 |
|------|------------|--------|----------------|------|
| #1 채널·유형 설정 | 높음 (텔레그램 스팸 차단) | 중 (마이그 1개) | 적합 | **채택** |
| #2 웹 푸시 | 중 | 높음 (SW·VAPID·신규 채널) | 과대 | 보류 |
| #3 포트폴리오 AI 최적화 | 중 | 매우 높음 | 과대 | 보류 |
| #4 해외 자산 | 높음 | 매우 높음 (데이터층 전반) | 과대 | 보류 |
| #5 알림 설정 UI | 중 | 낮음 | 단독은 불완전 | **#1에 흡수** |

결론: #1(백엔드) + #5(프론트 UI)를 하나의 완결 수직 기능으로 결합 = **SPEC-025 알림 채널·유형 설정**.
백엔드+프론트 완결성, 정당한 마이그레이션 1개, SPEC-024 위에 직접 구축, 명확한 사용자 가치.

---

## 2. 비자명 코드베이스 사실 (구현 시 주의)

### 2.1 디스패치 발생 지점 (게이트를 넣을 곳)

알림 채널 발송은 **두 곳**에서 일어난다:

1. **`notifications/general_alert_service.py`** (AsyncSession):
   - `check_and_trigger_all_alerts()` → 발동 후 `_try_send_alert_email()` + `_try_send_telegram()` 호출
   - 두 헬퍼는 이미 `EmailSubscription`/`TelegramSubscription`을 `user_id + is_active`로 조회하여 발송
   - 대상 유형: `target_price`, `surge_drop`, `volume_spike` (`ex_dividend`는 점검 미구현 — `continue`로 skip)
   - 발송은 best-effort (try/except로 격리, 실패해도 루프 지속)

2. **`notifications/rec_change.py`** (동기 `Session`, `SyncSessionLocal`):
   - `check_rec_changes()` → `rec_new`/`rec_dropped`
   - `check_rec_score_changes()` → `rec_score_change`
   - 이미 `EmailSubscription`/`TelegramSubscription` 조회 + `send_general_alert_email` / `_send_message_sync` 호출
   - 관심목록(`WatchlistItem`) 보유 사용자만 대상

→ **게이트 헬퍼는 async·sync 양쪽 모두 필요**하다. 핵심 쿼리(select NotificationPreference)는 동일하나
세션 타입이 다르므로 두 함수로 노출한다.

### 2.2 인박스 알림은 게이트 대상이 아님

`build_notification_payload()` → `pg_insert(Notification).on_conflict_do_nothing(constraint="uq_notification_user_type_code_date")`
는 채널 발송과 **독립적으로** 항상 실행된다. 인앱 인박스는 비침투적·무료이므로 설정 토글 대상에서
제외하고 항상 생성한다 (REQ-PREF-DISPATCH-005). 이는 SPEC-024의 "채널 실패와 독립적으로 인박스 생성"
원칙의 연장이다.

### 2.3 구독 테이블 구조

- `EmailSubscription` (마이그 0008): `user_id` FK CASCADE, `email`, `is_active`
- `TelegramSubscription` (마이그 0003): `user_id` FK CASCADE, `chat_id` BigInteger UNIQUE, `is_active`
- 두 테이블은 사용자가 채널을 **등록했는지** 여부만 표현. **유형별 ON/OFF 개념이 없음** → 신규 테이블 필요.

### 2.4 alert_type 값 집합

`general_alert_service._VALID_ALERT_TYPES = {"target_price", "surge_drop", "ex_dividend", "volume_spike"}`.
추천 변동(`rec_change.py`)에서 쓰는 notifications.type 값: `rec_new`, `rec_dropped`, `rec_score_change`.
→ 설정 대상 7개 유형 = 위 4개(ex_dividend 포함, 미래 대비) + rec 3개.

레거시 `price_alert`(SPEC-013 watchlist_alerts 경로)는 본 SPEC 제외 → 설정 유형에 포함하지 않음(하위 호환).

### 2.5 마이그레이션 체인

현재 최신 = `0017_alerts.py` (SPEC-020). 신규 = `0018_notification_preferences.py`,
`down_revision="0017"`. SPEC-021~024는 신규 마이그레이션 없음(0017 유지).

### 2.6 라우터 마운트 패턴 (main.py)

```
app.include_router(email_router, prefix="/notifications", tags=["notifications"])
app.include_router(inbox_router, prefix="/notifications", tags=["notifications"])
app.include_router(general_alert_router, prefix="/alerts", tags=["alerts"])
```

→ 신규 프리퍼런스 엔드포인트는 `/notifications/preferences`로 두는 것이 일관적.
기존 `email_router`(`/notifications/email`)·`inbox_router`(`/notifications/...`)와 경로 충돌 없음
(`/preferences` 하위 경로). 신규 `pref_router`를 만들어 `prefix="/notifications"`로 마운트하거나
`inbox_router`에 추가. 충돌 회피 위해 신규 `pref_router` 권장(RUN에서 최종 확인).

### 2.7 인증 의존성

- 동기 라우터(email_router, inbox_router): `from stock_picker.auth.dependencies import get_current_user, get_db_session`
- general_alert_router는 async 패턴. 프리퍼런스 GET/PUT은 설정 영속화이므로 **동기 라우터 패턴**
  (`get_current_user` + `get_db_session`, Session)으로 작성하면 기존 inbox/email 라우터와 일관.
  단, 디스패치 게이트는 async(general_alert_service)·sync(rec_change) 양쪽에서 호출되므로 서비스 함수는 두 버전 제공.

### 2.8 프론트 설정 페이지 현황

`pages/Settings.tsx`는 현재 **이메일 구독 단일 섹션**만 보유(subscribe/unsubscribe).
`api/notifications.ts`에 `subscribeEmail`/`unsubscribeEmail` 존재. 매트릭스 UI와
`getPreferences`/`updatePreferences` API를 추가하되 기존 이메일 섹션은 보존.

---

## 3. 설계 결정

### 3.1 행 구조: per-(user,type), 채널은 컬럼

대안 A: `(user, type)` 1행 + `email_enabled`/`telegram_enabled` 컬럼 — **채택**
대안 B: `(user, type, channel)` 1행 — 행 수 2배, 조회 시 채널별 분기 필요

A가 단순(UNIQUE 1개, 행 수 절반, 조회 1회로 두 채널 판정). 신규 채널 추가 시 컬럼 추가가 필요하나
신규 채널은 본 SPEC 제외이므로 YAGNI 위배 아님.

### 3.2 opt-out 기본값 (하위 호환의 핵심)

설정 행이 없으면 두 채널 모두 활성으로 간주. 이로써 기존 사용자(설정 미생성)의 SPEC-024 수신 경험이
**완전히 동일하게 유지**된다. opt-in으로 했다면 모든 기존 사용자가 갑자기 외부 알림을 못 받는 회귀가 발생.

### 3.3 게이트 조회 실패 시 fail-open

설정 조회가 예외를 던지면 기본값(활성)으로 처리. 알림 누락(사용자가 받아야 할 알림을 놓침)이
중복 발송보다 더 나쁜 실패 모드이므로 fail-open 채택. 기존 디스패치의 best-effort 철학과 일치.

---

## 4. 위험 및 완화

| 위험 | 영향 | 완화 |
|------|------|------|
| async/sync 헬퍼 중복 | 유지보수 부담 | 핵심 select 로직만 공유, 세션 호출부만 분리 |
| 라우터 경로 충돌 | 404/오동작 | `/notifications/preferences` 하위 경로 + RUN에서 경로 검증 |
| 하위 호환 회귀 | 기존 사용자 알림 중단 | opt-out 기본값 + AC-10 하위 호환 테스트 |
| 게이트 누락 (한 경로만 적용) | 일부 알림 제어 안 됨 | 4개 디스패치 지점(alerts 2 + rec_change 2) 모두 T3에 명시 |

---

## 5. 참고 파일

- `backend/src/stock_picker/notifications/general_alert_service.py` (디스패치 #1)
- `backend/src/stock_picker/notifications/rec_change.py` (디스패치 #2)
- `backend/src/stock_picker/notifications/email_service.py` (`send_general_alert_email`)
- `backend/src/stock_picker/telegram/notifier.py` (`_send_message_sync`)
- `backend/src/stock_picker/db/models.py` (EmailSubscription·TelegramSubscription·Notification)
- `backend/src/stock_picker/api/main.py` (라우터 마운트)
- `backend/alembic/versions/0017_alerts.py` (마이그레이션 체인 최신)
- `frontend/src/pages/Settings.tsx` · `frontend/src/api/notifications.ts` (프론트)
