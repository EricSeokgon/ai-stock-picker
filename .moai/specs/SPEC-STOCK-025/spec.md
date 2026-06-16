---
id: SPEC-STOCK-025
version: 0.1.0
status: draft
created: 2026-06-16
updated: 2026-06-16
author: ircp
priority: High
issue_number: null
---

# SPEC-STOCK-025 — 사용자별 알림 채널·유형 설정 (Notification Preferences)

## 메타데이터

- **SPEC ID**: SPEC-STOCK-025
- **제목**: 사용자별 알림 채널·유형 설정 — 알림 유형별 이메일·텔레그램 수신 ON/OFF
- **상태**: draft
- **작성일**: 2026-06-16
- **우선순위**: High
- **의존성**: SPEC-STOCK-024 (채널 배선), SPEC-STOCK-020 (alerts 테이블), SPEC-STOCK-013 (notifications·rec_change)
- **마이그레이션**: 0018 (신규 테이블 `notification_preferences`, down_revision=0017)

---

## 배경 및 동기

SPEC-024에서 이메일·텔레그램 채널을 모든 알림 경로(`alerts` 발동·추천 변동 감지)에 배선했다.
그 결과, `EmailSubscription`과 `TelegramSubscription`을 모두 등록한 사용자는 **모든 알림 유형을
두 채널 모두로 무조건 수신**한다. 채널·유형별로 끄거나 켤 방법이 전혀 없다.

현재 동작의 문제점:

1. 거래량 급증(`volume_spike`)은 텔레그램으로만 받고 싶어도 이메일까지 강제 발송된다.
2. 추천 점수 변화(`rec_score_change`) 알림이 과하다고 느껴도 끌 수 없다.
3. 이메일 구독을 유지하면서 특정 유형만 제외하려면 구독 자체를 해지해야 한다 (전부 아니면 전무).

이 SPEC의 목표는 사용자가 **알림 유형별로 이메일·텔레그램 채널을 개별 ON/OFF**할 수 있게 하는 것이다.
인앱 인박스 알림은 비침투적이고 무료이므로 항상 생성하며(토글 대상 아님), 설정은 **외부 채널(이메일·텔레그램)만**
제어한다.

핵심 설계 원칙은 **하위 호환(opt-out 모델)**이다. 설정 행이 없는 사용자는 기존 SPEC-024 동작 그대로
두 채널 모두 활성으로 간주한다. 기존 사용자의 수신 경험은 변하지 않는다.

---

## 범위 (Scope)

### 포함 (What to Build)

1. **`notification_preferences` 테이블** (마이그레이션 0018)
   - `(user_id, alert_type)` 단위 1행, `email_enabled`·`telegram_enabled` Boolean 보유
   - UNIQUE(user_id, alert_type)

2. **프리퍼런스 서비스** (`notifications/preferences.py` 신규)
   - 사용자 설정 조회(누락 유형은 기본값 채움)
   - 설정 일괄 upsert
   - 채널 활성 여부 판정 헬퍼: `is_channel_enabled()` — async·sync 양쪽 제공

3. **설정 API** (`get_current_user` 보호, prefix `/notifications/preferences`)
   - `GET /notifications/preferences` — 7개 알림 유형의 유효 설정 반환(기본값 포함)
   - `PUT /notifications/preferences` — 설정 일괄 저장(upsert)

4. **디스패치 게이팅** — 기존 발송 직전 설정 확인
   - `general_alert_service._try_send_alert_email` / `_try_send_telegram`
     → `target_price`, `surge_drop`, `volume_spike` 알림에 게이트 적용
   - `rec_change.py` (`check_rec_changes`, `check_rec_score_changes`)
     → `rec_new`, `rec_dropped`, `rec_score_change` 알림에 게이트 적용

5. **프론트 설정 UI** (`pages/Settings.tsx` 확장 + `api/notifications.ts` 확장)
   - 알림 유형 × 채널(이메일·텔레그램) 체크박스 매트릭스
   - 기존 이메일 구독 섹션은 보존

6. **단위 테스트** (`tests/unit/test_notification_preferences.py`)

### 제외 (What NOT to Build)

- **인앱 인박스 알림 토글**: 인박스 알림은 항상 생성(비침투적·무료). 설정 대상 아님.
- **레거시 `watchlist_alerts` / `price_alert` 경로 변경**: SPEC-013 이전 경로는 하위 호환을 위해 불변.
- **신규 채널(웹 푸시·SMS·슬랙·카카오톡)**: 별도 SPEC. 채널 추상화 레이어 도입도 제외(YAGNI).
- **종목별(per-stock) 세분화 설정**: 본 SPEC은 알림 유형(per-type) 단위만.
- **조용한 시간(quiet hours)·발송 시간대 스케줄링·다이제스트 빈도 설정**: 제외.
- **스케줄러 비기동 결함 수정**: SPEC-022 범위.
- **자동매매·매수/매도 주문**: 영구 제외 (규제·책임 리스크).

---

## 요구사항 (EARS 형식)

### 모델 · 서비스 (REQ-PREF-*)

#### REQ-PREF-001 — 프리퍼런스 테이블
**The system shall** `(user_id, alert_type)` 단위로 `email_enabled`·`telegram_enabled` Boolean을 저장하는 `notification_preferences` 테이블을 제공한다.

#### REQ-PREF-002 — 유형별 유일성
**The system shall** `(user_id, alert_type)` 조합에 UNIQUE 제약을 적용하여 유형당 1행만 존재하도록 한다.

#### REQ-PREF-003 — 기본값 활성 (하위 호환)
**Where** 특정 `(user_id, alert_type)`에 대한 설정 행이 존재하지 않으면
**The system shall** 이메일·텔레그램 두 채널 모두 활성(enabled)으로 간주한다.

#### REQ-PREF-004 — 채널 활성 판정 헬퍼
**When** `is_channel_enabled(user_id, alert_type, channel)`이 호출되면
**The system shall** 해당 설정 행의 `{channel}_enabled` 값을 반환하고, 행이 없으면 True를 반환한다.

#### REQ-PREF-005 — 설정 upsert
**When** 사용자가 설정을 저장하면
**The system shall** 기존 행이 있으면 갱신하고 없으면 삽입하여 `(user_id, alert_type)` 단위로 1행을 유지한다.

### API (REQ-PREF-API-*)

#### REQ-PREF-API-001 — 설정 조회
**When** 인증된 사용자가 `GET /notifications/preferences`를 호출하면
**The system shall** 지원되는 7개 알림 유형 각각에 대해 유효한 `email_enabled`·`telegram_enabled` 값을 반환한다 (설정 없는 유형은 기본값 True).

#### REQ-PREF-API-002 — 설정 저장
**When** 인증된 사용자가 `PUT /notifications/preferences`로 설정 목록을 전송하면
**The system shall** 각 항목을 upsert하고 갱신된 전체 설정을 반환한다.

#### REQ-PREF-API-003 — 미인증 차단
**If** 인증 토큰 없이 설정 엔드포인트를 호출하면
**then the system shall** 401을 반환하고 설정을 노출하지 않는다.

#### REQ-PREF-API-004 — 미지원 유형 거부
**If** `PUT` 요청에 지원하지 않는 `alert_type`이 포함되면
**then the system shall** 422를 반환하고 어떤 행도 저장하지 않는다.

### 디스패치 게이팅 (REQ-PREF-DISPATCH-*)

#### REQ-PREF-DISPATCH-001 — alerts 이메일 게이트
**When** `_try_send_alert_email()`이 호출되면
**The system shall** `is_channel_enabled(user_id, alert.alert_type, "email")`가 True인 경우에만 이메일을 발송한다.

#### REQ-PREF-DISPATCH-002 — alerts 텔레그램 게이트
**When** `_try_send_telegram()`이 호출되면
**The system shall** `is_channel_enabled(user_id, alert.alert_type, "telegram")`가 True인 경우에만 텔레그램 메시지를 발송한다.

#### REQ-PREF-DISPATCH-003 — rec_change 이메일 게이트
**When** `check_rec_changes()` 또는 `check_rec_score_changes()`가 이메일을 발송하려 할 때
**The system shall** 해당 알림 유형(`rec_new`/`rec_dropped`/`rec_score_change`)에 대해 이메일이 활성인 사용자에게만 발송한다.

#### REQ-PREF-DISPATCH-004 — rec_change 텔레그램 게이트
**When** `check_rec_changes()` 또는 `check_rec_score_changes()`가 텔레그램을 발송하려 할 때
**The system shall** 해당 알림 유형에 대해 텔레그램이 활성인 사용자에게만 발송한다.

#### REQ-PREF-DISPATCH-005 — 인박스 알림 무조건 생성
**While** 알림이 발동하면
**The system shall** 채널 설정과 무관하게 인앱 인박스 알림(notifications 테이블)을 항상 생성한다.

#### REQ-PREF-DISPATCH-006 — 게이트 조회 실패 격리
**If** 설정 조회가 예외를 던지면
**then the system shall** 오류를 로그에 기록하고 해당 채널을 기본값(활성)으로 처리하여 발송 누락을 방지한다.

### 프론트엔드 (REQ-PREF-FE-*)

#### REQ-PREF-FE-001 — 설정 매트릭스 표시
**When** 인증된 사용자가 설정 페이지를 열면
**The system shall** 알림 유형 행 × 이메일·텔레그램 열로 구성된 체크박스 매트릭스를 현재 설정값으로 렌더링한다.

#### REQ-PREF-FE-002 — 설정 저장
**When** 사용자가 체크박스를 변경하고 저장하면
**The system shall** `PUT /notifications/preferences`를 호출하고 저장 결과를 반영한다.

#### REQ-PREF-FE-003 — 미인증 리다이렉트
**If** 미인증 상태로 설정 페이지에 접근하면
**then the system shall** `/login`으로 리다이렉트한다.

### 비기능 (REQ-PREF-NFR-*)

#### REQ-PREF-NFR-001 — 자동매매 제외
**The system shall** 매수/매도 주문, 자동 매매 로직을 포함하지 않는다.

#### REQ-PREF-NFR-002 — 코드 주석·커밋 언어
**The system shall** 코드 주석과 커밋 메시지를 한국어로 작성한다.

#### REQ-PREF-NFR-003 — 테스트 커버리지
**The system shall** 신규 코드에 대해 단위 테스트를 제공하고 프로젝트 커버리지 기준(85%)을 유지한다.

---

## 수용 기준 (Given-When-Then)

### AC-1 — 설정 없는 사용자 기본 활성 (REQ-PREF-003, 004)
- **Given** user_id=1에 대한 `notification_preferences` 행이 없음
- **When** `is_channel_enabled(1, "volume_spike", "email")`이 호출되면
- **Then** True가 반환된다.

### AC-2 — 설정 조회 7개 유형 (REQ-PREF-API-001)
- **Given** user_id=2가 일부 유형만 설정 저장
- **When** `GET /notifications/preferences`를 호출하면
- **Then** 지원 7개 유형 전부가 응답에 포함되고, 미설정 유형은 email_enabled=true, telegram_enabled=true로 표시된다.

### AC-3 — 설정 저장 upsert (REQ-PREF-API-002, REQ-PREF-005)
- **Given** user_id=3
- **When** `PUT /notifications/preferences`로 `volume_spike` email_enabled=false를 전송하면
- **Then** 행이 1개 생성/갱신되고, 재조회 시 `volume_spike` email_enabled=false가 반환된다.

### AC-4 — 미지원 유형 거부 (REQ-PREF-API-004)
- **Given** 인증된 사용자
- **When** `PUT`에 `alert_type="unknown"`을 포함하면
- **Then** 422가 반환되고 어떤 행도 저장되지 않는다.

### AC-5 — 미인증 차단 (REQ-PREF-API-003)
- **Given** 토큰 없음
- **When** `GET /notifications/preferences`를 호출하면
- **Then** 401이 반환된다.

### AC-6 — alerts 이메일 OFF 시 미발송 (REQ-PREF-DISPATCH-001, 005)
- **Given** user_id=4가 `surge_drop` email_enabled=false로 설정, EmailSubscription 존재, surge_drop 알림 발동
- **When** `check_and_trigger_all_alerts()`가 실행되면
- **Then** 이메일 발송 함수가 호출되지 않고, 인박스 알림은 정상 생성된다.

### AC-7 — alerts 텔레그램 ON 시 발송 (REQ-PREF-DISPATCH-002)
- **Given** user_id=4가 `surge_drop` telegram_enabled=true(기본), TelegramSubscription 존재, surge_drop 알림 발동
- **When** `check_and_trigger_all_alerts()`가 실행되면
- **Then** `_send_message_sync()`가 1회 호출된다.

### AC-8 — rec_score_change 이메일 OFF (REQ-PREF-DISPATCH-003)
- **Given** user_id=5가 `rec_score_change` email_enabled=false로 설정, EmailSubscription·관심목록 종목 보유
- **When** `check_rec_score_changes()`가 알림을 생성하면
- **Then** 이메일 발송이 skip되고 인박스 알림은 생성된다.

### AC-9 — 게이트 조회 실패 시 기본 발송 (REQ-PREF-DISPATCH-006)
- **Given** 설정 조회가 예외를 던지는 환경, EmailSubscription 존재, 알림 발동
- **When** 디스패치가 실행되면
- **Then** 오류가 로깅되고 기본값(활성)으로 이메일이 발송된다.

### AC-10 — 하위 호환 (REQ-PREF-003)
- **Given** SPEC-024 시점 사용자(설정 행 없음), EmailSubscription·TelegramSubscription 존재, 알림 발동
- **When** 디스패치가 실행되면
- **Then** 이메일·텔레그램 모두 SPEC-024와 동일하게 발송된다.

### AC-11 — 프론트 매트릭스 (REQ-PREF-FE-001, 002)
- **Given** 인증 사용자가 설정 페이지 진입
- **When** 매트릭스가 렌더되고 체크박스를 변경해 저장하면
- **Then** `PUT /notifications/preferences`가 호출된다.

---

## 기술 설계

### M1 — 모델 + 마이그레이션 0018

```
# db/models.py
class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    id: int PK
    user_id: int FK(users.id, CASCADE)
    alert_type: str(20)              # target_price|surge_drop|volume_spike|ex_dividend|rec_new|rec_dropped|rec_score_change
    email_enabled: bool default True
    telegram_enabled: bool default True
    updated_at: datetime server_default now()
    __table_args__ = (UniqueConstraint("user_id", "alert_type", name="uq_pref_user_type"),)
```

지원 유형 상수:
```
_SUPPORTED_ALERT_TYPES = (
    "target_price", "surge_drop", "volume_spike", "ex_dividend",
    "rec_new", "rec_dropped", "rec_score_change",
)
```

마이그레이션 `0018_notification_preferences.py` (down_revision="0017").

### M2 — 프리퍼런스 서비스 (`notifications/preferences.py`)

```
# 채널 활성 판정 — async (general_alert_service에서 사용)
async def is_channel_enabled_async(session, user_id, alert_type, channel) -> bool:
    try:
        row = await session.execute(select(NotificationPreference).where(...))
        pref = row.scalar_one_or_none()
        if pref is None:
            return True              # 기본 활성 (하위 호환)
        return getattr(pref, f"{channel}_enabled", True)
    except Exception:
        log.error(...); return True  # 조회 실패 시 기본 활성

# 채널 활성 판정 — sync (rec_change에서 사용)
def is_channel_enabled_sync(db, user_id, alert_type, channel) -> bool: ...

# 조회 (기본값 채움) / upsert
async def get_preferences(session, user_id) -> list[PreferenceSchema]: ...
async def upsert_preferences(session, user_id, items) -> list[PreferenceSchema]: ...
```

### M3 — API 엔드포인트

`/notifications/preferences` (inbox_router 또는 신규 pref_router, prefix `/notifications`):
- `GET` → 7개 유형 유효 설정
- `PUT` → 일괄 upsert + 갱신 결과

### M4 — 디스패치 게이팅

`general_alert_service.py`:
```
async def _try_send_alert_email(alert, message, session):
    if not await is_channel_enabled_async(session, alert.user_id, alert.alert_type, "email"):
        return
    ... 기존 발송 ...
```
`rec_change.py` — 각 발송 직전 `is_channel_enabled_sync(db, uid, change_type, "email"/"telegram")` 확인.

### M5 — 테스트 (`tests/unit/test_notification_preferences.py`)

Mock 대상: `send_general_alert_email`, `_send_message_sync`, 설정 조회. 검증: 기본 활성·OFF skip·인박스 무조건 생성·조회 실패 기본 발송·하위 호환.

---

## 마일스톤 체크리스트

### M1 — 모델 + 마이그레이션 + 서비스 — Priority High
- [ ] T1-1: `NotificationPreference` 모델 + UNIQUE(user_id, alert_type)
- [ ] T1-2: 마이그레이션 `0018_notification_preferences.py` (down_revision=0017)
- [ ] T1-3: `is_channel_enabled_async` (기본 활성·예외 격리)
- [ ] T1-4: `is_channel_enabled_sync`
- [ ] T1-5: `get_preferences` (7개 유형 기본값 채움)
- [ ] T1-6: `upsert_preferences` (미지원 유형 거부)

### M2 — 설정 API — Priority High
- [ ] T2-1: `GET /notifications/preferences` (인증 보호)
- [ ] T2-2: `PUT /notifications/preferences` (upsert + 422 검증)
- [ ] T2-3: 라우터 mount (main.py)

### M3 — 디스패치 게이팅 — Priority High
- [ ] T3-1: `_try_send_alert_email` 이메일 게이트
- [ ] T3-2: `_try_send_telegram` 텔레그램 게이트
- [ ] T3-3: `check_rec_changes` 이메일·텔레그램 게이트 (rec_new/rec_dropped)
- [ ] T3-4: `check_rec_score_changes` 이메일·텔레그램 게이트 (rec_score_change)
- [ ] T3-5: 인박스 알림 무조건 생성 유지 확인

### M4 — 프론트 설정 UI — Priority Medium
- [ ] T4-1: `api/notifications.ts` — getPreferences/updatePreferences 추가
- [ ] T4-2: `Settings.tsx` — 알림 유형 × 채널 매트릭스 + 저장
- [ ] T4-3: 기존 이메일 구독 섹션 보존

### M5 — 단위 테스트 — Priority Medium
- [ ] T5-1: `test_기본활성` — 행 없을 때 True
- [ ] T5-2: `test_설정조회_7유형` — 기본값 채움
- [ ] T5-3: `test_upsert` — 생성/갱신 1행 유지
- [ ] T5-4: `test_미지원유형_거부` — 422
- [ ] T5-5: `test_alerts_이메일OFF_skip`
- [ ] T5-6: `test_alerts_텔레그램ON_발송`
- [ ] T5-7: `test_rec_change_이메일OFF_skip`
- [ ] T5-8: `test_게이트조회실패_기본발송`
- [ ] T5-9: `test_인박스_무조건생성`
- [ ] T5-10: 기존 테스트(test_channel_dispatch.py 등) 통과 확인

---

## 제약사항

- 자동매매·매수/매도 주문: **영구 제외**
- 신규 마이그레이션: **0018 (notification_preferences)** — 사용자별 설정 영속화에 필수
- 하위 호환: 설정 행 없는 사용자는 SPEC-024 동작 그대로 (opt-out 모델)
- 인앱 인박스 알림: 토글 대상 아님 (항상 생성)
- 레거시 `watchlist_alerts`/`price_alert` 경로: **불변**
- 신규 채널·종목별 세분화·quiet hours: **이 SPEC 제외**
- 테스트 명령: `uv run pytest`
- 코드 주석 언어: 한국어
- 커밋 메시지 언어: 한국어
