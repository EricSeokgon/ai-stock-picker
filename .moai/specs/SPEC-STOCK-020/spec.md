---
id: SPEC-STOCK-020
version: 0.1.0
status: draft
created: 2026-06-15
updated: 2026-06-15
author: ircp
priority: medium
issue_number: null
---

# SPEC-STOCK-020 — 알림·알림 설정 (Price Alert & Notification System, Phase 20)

## HISTORY

- 2026-06-15 (v0.1.0): 최초 작성. 사용자가 보유/관심 종목에 대해 알림 규칙(목표가·급등락·배당락일)을
  설정하고, 가격 점검 시 조건 충족을 감지하여 인앱 알림(인박스)으로 적재 + 선택적 이메일 발송한다.
  신규 `alerts` 테이블(마이그레이션 0017, down_rev=0016) + `/alerts` CRUD 라우터 + `POST /alerts/check`
  점검 트리거 + 신규 스케줄러 잡 `check_alerts`(IntervalTrigger 기본 10분). 신규 프론트 `/alerts` 페이지.
  **⚠️ 핵심 비자명 사실: 알림 인프라 상당 부분이 이미 존재한다.** 본 SPEC은 이를 재사용하며,
  **신규 `notifications` 테이블을 만들지 않는다**(이미 마이그 0014에 존재). 자세한 충돌 정리는 §1.3·§2.1 참조.

---

## 1. 개요 (Overview)

### 1.1 문제 정의

사용자가 보유/관심 종목에 대해 **스스로 알림 규칙을 정의**하고, 조건이 충족되면 통지받기를 원한다.
요청된 알림 유형은 셋이다:

1. **목표가 알림 (target_price)** — 종목이 지정 목표가에 도달하면 알림.
2. **급등락 알림 (surge_drop)** — 종목의 당일 변동률이 임계치(예: ±5%)를 초과하면 알림.
3. **배당락일 알림 (ex_dividend)** — 배당기준일 N일 전에 알림.

### 1.2 목표

사용자 정의 알림 규칙 CRUD + 가격 점검 시 조건 평가 + 인앱 알림 적재 + 선택적 이메일 발송 +
알림 관리 프론트 UI(`/alerts`)를 추가한다.

### 1.3 비자명 코드베이스 사실 (설계 근거) — **반드시 먼저 읽을 것**

이 기능은 **이미 구현된 인프라와 크게 중복**된다. 중복 재구축은 금지하고 재사용한다.

**이미 존재하므로 재구축 금지:**

- **`notifications` 인앱 알림 인박스 테이블이 이미 존재한다 (마이그 0014, SPEC-STOCK-013).**
  컬럼: `id`(Integer PK), `user_id`(FK CASCADE), `type`(String(20)), `krx_code`, `title`, `body`,
  `is_read`(default False), `ref_date`(Date nullable), `related_alert_id`(FK watchlist_alerts SET NULL),
  `created_at`, `read_at` + `UNIQUE(user_id, type, krx_code, ref_date)` + 미읽음 조회 인덱스.
  → **본 SPEC은 새 `notifications` 테이블을 만들지 않는다.** 요청서의 "notifications 테이블(마이그 0017)"은
    기존 0014 테이블로 충족된다. 신규 생성 시 **파괴적 중복**이 된다.
- **인박스 엔드포인트가 이미 존재한다** (`notifications/inbox_router.py`, prefix `/notifications`):
  `GET /notifications/`(unread_only·limit), `GET /notifications/unread-count`,
  `PATCH /notifications/{id}/read`, `PATCH /notifications/read-all`. → **본 SPEC은 인박스 엔드포인트를
  재구축하지 않고 재사용한다.** (요청서의 `POST /notifications/{id}/read`·`POST /notifications/read-all`·
  `GET /notifications/unread-count`는 기존 `PATCH`·`GET` 엔드포인트로 충족 — 동일 기능의 POST 별칭을
  새로 만들지 않는다. §5 비목표 참조.)
- **목표가 알림이 이미 존재한다** — `watchlist_alerts` 테이블(마이그 0007, SPEC-004) + `/watchlist/alerts`
  CRUD(`notifications/alert_router.py`) + `check_price_alerts` 5분 스케줄러 + `_trigger_alert`(텔레그램+이메일+
  인박스 알림 생성). 이는 본 SPEC의 목표가 알림과 **기능적으로 겹친다**(§2.1에서 정리).
- **이메일 발송이 이미 존재한다** — `notifications/email_service.py`의 `_get_smtp_config()`·`_send_email()`이
  이미 `SMTP_HOST`/`SMTP_PORT`/`SMTP_USER`/**`SMTP_PASSWORD`**/`SMTP_FROM` 환경변수를 읽고, `SMTP_HOST`
  미설정 시 조용히 건너뛴다. **표준 라이브러리 `smtplib`(동기) 사용, `aiosmtplib` 의존성 없음.**
- **프론트 알림 벨이 이미 존재한다** — NavBar 종아이콘+미읽음 배지(unread-count 폴링)·`/notifications`
  페이지·`api/notifications.ts`가 SPEC-013에서 구현됨. → **본 SPEC은 벨/인박스 페이지를 재구축하지 않는다.**

**진짜 신규 (본 SPEC 범위):**

- **`surge_drop`(급등락) 알림 유형** — `watchlist_alerts`는 절대 목표가(above/below)만 지원. 변동률 임계치
  기반 알림은 코드에 없다.
- **`ex_dividend`(배당락일) 알림 유형** — 코드에 없다. **SPEC-019가 명시적으로 제외**했던 영역
  ("배당락/배당기준일 알림·인박스 연동 — Phase H 알림 시스템과 연동하지 않음"). 본 SPEC이 처음 도입.
- **알림 수정(PUT)** — `watchlist_alerts`에는 update 엔드포인트가 없다.
- **세 유형을 통합한 일반화 알림 모델 `alerts`** + 통합 점검 로직.

### 1.4 코드베이스 정합 사실 (재사용 패턴)

- 시세: `mapping/prices.py` `get_stock_price_data(krx_code)` → `{close_price, change_rate, volume}` 또는
  실패 시 None (`run_in_executor`로 동기 FDR 격리, graceful degradation). **급등락 점검은 `change_rate` 사용.**
- 배당: SPEC-019 `portfolio/dividends.py`가 FDR 베스트에포트로 `ex_dividend_date`를 조회(Redis 캐시
  `dividends:{krx_code}` TTL 86400). **배당락일 점검은 이 조회 경로를 재사용**하며, 기준일 미확보 시 발동하지 않는다.
- PK 규약: **코드베이스 전 테이블이 `Integer` autoincrement PK**(asyncpg/Postgres + SQLite 테스트 호환).
  → 요청서의 UUID PK 대신 **Integer PK 사용**(규약 일치, §3에서 명시).
- 소유권 확인 패턴: `db.query(...).filter(model.id==id, model.user_id==current_user.id).first()` → 없으면 404
  (`portfolio/router.py`·`alert_service.delete_alert` 동일).
- 스케줄러: `scheduler/jobs.py`에 `_scheduler.add_job(...)` 패턴, 점검 잡은 예외 격리
  (`run_sector_aggregation` 패턴). 신규 잡 `check_alerts`를 동일 방식으로 추가.

---

## 2. 설계 결정 (Design Decisions)

### 2.1 기존 `watchlist_alerts` 와의 관계 (중복 정리)

목표가 알림은 `watchlist_alerts`(기존)와 신규 `alerts` 양쪽에서 표현 가능하다. 두 점검 엔진을 병행하되
**충돌·중복 제거는 하지 않는다**:

- 신규 `alerts` 테이블이 **세 유형 모두**(목표가·급등락·배당락)를 담는 **일반화 후속 모델**이다.
- 기존 `watchlist_alerts` / `check_price_alerts` / `/watchlist/alerts` 는 **일절 수정·제거하지 않는다**
  (하위호환·회귀 위험 회피). 두 경로가 공존한다.
- 신규 `alerts`의 점검은 **별도 잡 `check_alerts`** 가 담당하고, 발동 시 알림은 **기존 `notifications`
  테이블**에 적재한다.
- 이 공존을 정직하게 노출한다(문서화). 사용자가 동일 종목·목표가를 양쪽에 등록하면 두 알림을 받을 수 있음.

### 2.2 영속화 전략

- **마이그레이션 0017은 `alerts` 테이블만 생성**한다(down_rev=0016). `notifications`는 0014에 존재하므로
  **재생성하지 않는다.**
- `alerts.alert_type` 은 DB enum이 아니라 `String(20)`(코드 레벨 검증). 기존 `notifications.type`·
  `watchlist_alerts.direction` 패턴과 동일(문자열).
- 발동 알림의 `notifications.type` 값은 신규 문자열 `'target_price'`·`'surge_drop'`·`'ex_dividend'`를
  사용한다(컬럼은 String(20), DB enum 없음 → 신규 값 허용).
- 멱등성: 기존 `notifications` UNIQUE(user_id, type, krx_code, ref_date)를 활용. 발동 알림 생성 시
  `ref_date = triggered_at.date()`로 설정하여 동일일 중복 적재를 방지(IntegrityError graceful skip).

### 2.3 점검(check) 로직

- `POST /alerts/check`(무인증, 테스트/수동 트리거)와 스케줄러 잡 `check_alerts`(기본 10분, 설정 가능)가
  **동일 점검 함수**를 호출한다(요청서 지침대로 Celery 미도입, APScheduler 재사용).
- 점검 대상: `is_active = True AND is_triggered = False` 인 모든 알림.
- 유형별 평가:
  - `target_price`: `get_stock_price_data().close_price` vs `condition_value`, `condition_direction`(above/below).
  - `surge_drop`: `get_stock_price_data().change_rate`(%) vs `condition_value`(%), direction(above=급등/below=급락/either=절대값).
  - `ex_dividend`: SPEC-019 배당 조회로 `ex_dividend_date` 확보 시, `오늘 == 기준일 - condition_value일`이면 발동.
    **기준일 미확보 시 발동하지 않음**(추측 금지).
- 발동 시: `is_triggered=True`, `triggered_at=now()`, `triggered_message="..."` 설정 → `notifications` 행 생성
  → 이메일 베스트에포트 발송(SMTP 미설정 시 건너뜀, 발송 실패는 알림 적재와 독립).
- 점검은 시세/배당/이메일/Redis 장애에 대해 graceful degradation(예외 격리, 요청 실패 없음).

### 2.4 엔드포인트

- 신규 라우터 prefix `/alerts`(신규 모듈 `notifications/general_alert_router.py` 또는 `alerts/` —
  RUN에서 기존 `notifications/` 구조와 정합 결정):
  - `POST /alerts`(인증) / `GET /alerts`(인증) / `PUT /alerts/{id}`(인증·소유권) /
    `DELETE /alerts/{id}`(인증·소유권) / `POST /alerts/check`(무인증).
- 인박스 엔드포인트는 **재사용**(신규 없음).

### 2.5 이메일

- 기존 `notifications/email_service.py` 의 `_send_email()`(smtplib·환경변수·graceful skip)을 재사용·확장한다.
  **신규 `aiosmtplib` 의존성을 추가하지 않는다.** 환경변수 이름은 코드 기준
  `SMTP_HOST/SMTP_PORT/SMTP_USER/SMTP_PASSWORD/SMTP_FROM`(요청서의 `SMTP_PASS`가 아니라 `SMTP_PASSWORD`).

---

## 3. 데이터 모델 (Data Model)

신규 ORM 모델 1개. 마이그레이션 0017(down_rev=0016)에서 `alerts` 테이블 생성. **`notifications` 재생성 없음.**

```
Alert  (테이블명: alerts)
- id: Integer PK autoincrement          # 코드베이스 규약(요청서 UUID 대신 Integer)
- user_id: Integer FK → users.id (ondelete=CASCADE), not null
- krx_code: String(10), not null
- stock_name: String(100), nullable
- alert_type: String(20), not null      # 'target_price' | 'surge_drop' | 'ex_dividend'
- condition_value: Float, not null      # target_price=목표가(원) / surge_drop=임계 변동률(%) / ex_dividend=N일
- condition_direction: String(8), nullable  # 'above' | 'below' | 'either' (ex_dividend는 None)
- is_active: Boolean, not null, default True
- is_triggered: Boolean, not null, default False
- triggered_at: DateTime(timezone=True), nullable
- triggered_message: String(500), nullable
- created_at: DateTime(timezone=True), server_default now(), not null
```

응답/요청 Pydantic v2 스키마(신규 모듈 스키마 파일 또는 `notifications/schemas.py` 확장 — RUN 결정):

```
AlertCreate    : krx_code, stock_name?, alert_type, condition_value, condition_direction?
AlertUpdate    : condition_value?, condition_direction?, is_active?   # 부분 수정
AlertResponse  : id, krx_code, stock_name, alert_type, condition_value, condition_direction,
                 is_active, is_triggered, triggered_at, triggered_message, created_at
AlertCheckResult : checked: int, triggered: int   # POST /alerts/check 요약
```

알림(인박스) 스키마는 기존 `inbox_router.NotificationSchema` 재사용(신규 없음).

---

## 4. 요구사항 (EARS Requirements)

### 4.1 알림 규칙 CRUD (REQ-ALERT-*)

- REQ-ALERT-001 (Ubiquitous): The system shall allow an authenticated user to define alert rules of three
  types — `target_price`, `surge_drop`, and `ex_dividend` — for any KRX stock code.
- REQ-ALERT-002 (Event-Driven): WHEN a user creates an alert, the system shall persist it with
  `is_active = true`, `is_triggered = false`, and a null `triggered_at`.
- REQ-ALERT-003 (Ubiquitous): The system shall store, for each alert, its type, a numeric `condition_value`,
  and (for `target_price`/`surge_drop`) a `condition_direction` of `above`, `below`, or `either`.
- REQ-ALERT-004 (Event-Driven): WHEN a user updates an alert they own, the system shall apply the changed
  fields (`condition_value`, `condition_direction`, `is_active`) and leave other fields unchanged.
- REQ-ALERT-005 (Event-Driven): WHEN a user deletes an alert they own, the system shall remove it.
- REQ-ALERT-006 (State-Driven): WHILE an alert has `is_active = false`, the system shall not evaluate it
  during alert checks.

### 4.2 알림 점검 (REQ-ALERT-CHECK-*)

- REQ-ALERT-CHECK-001 (Event-Driven): WHEN an alert check runs, the system shall evaluate every alert with
  `is_active = true` and `is_triggered = false`.
- REQ-ALERT-CHECK-002 (Event-Driven): WHEN evaluating a `target_price` alert, the system shall compare the
  stock's current price against `condition_value` per `condition_direction` (above: price >= value,
  below: price <= value).
- REQ-ALERT-CHECK-003 (Event-Driven): WHEN evaluating a `surge_drop` alert, the system shall compare the
  stock's daily change percentage against `condition_value` per `condition_direction` (above: change >=
  value, below: change <= value, either: absolute change >= value).
- REQ-ALERT-CHECK-004 (Event-Driven): WHEN evaluating an `ex_dividend` alert AND the stock's ex-dividend
  date is available, the system shall trigger when the current date equals (ex-dividend date minus
  `condition_value` days).
- REQ-ALERT-CHECK-005 (State-Driven): WHILE a stock's ex-dividend date cannot be determined, the system
  shall not trigger its `ex_dividend` alert and shall not assert a guessed date.
- REQ-ALERT-CHECK-006 (Event-Driven): WHEN an alert's condition is met, the system shall set
  `is_triggered = true`, set `triggered_at` to the current time, set a human-readable `triggered_message`,
  and create an in-app notification.
- REQ-ALERT-CHECK-007 (State-Driven): WHILE an alert is already triggered (`is_triggered = true`), the
  system shall not re-evaluate or re-notify for it.
- REQ-ALERT-CHECK-008 (Unwanted): IF the current price, change percentage, or dividend data for a stock is
  unavailable, THEN the system shall skip that alert without failing the overall check.

### 4.3 알림 적재 (인박스 재사용) (REQ-ALERT-NOTI-*)

- REQ-ALERT-NOTI-001 (Event-Driven): WHEN an alert triggers, the system shall create a row in the existing
  `notifications` table with the alert owner's `user_id`, a `type` of the alert type, the `krx_code`, a
  title, and a body, and shall NOT create a new notifications table.
- REQ-ALERT-NOTI-002 (Ubiquitous): The system shall set the triggered notification's `ref_date` to the
  trigger date so that the existing UNIQUE(user_id, type, krx_code, ref_date) constraint prevents duplicate
  same-day notifications.
- REQ-ALERT-NOTI-003 (Unwanted): IF inserting the notification violates the uniqueness constraint, THEN the
  system shall skip the duplicate gracefully without failing the check.
- REQ-ALERT-NOTI-004 (Ubiquitous): The system shall expose triggered notifications through the existing
  inbox endpoints (`GET /notifications/`, `GET /notifications/unread-count`,
  `PATCH /notifications/{id}/read`, `PATCH /notifications/read-all`) and shall not duplicate those endpoints.

### 4.4 이메일 발송 (REQ-ALERT-EMAIL-*)

- REQ-ALERT-EMAIL-001 (Event-Driven): WHEN an alert triggers, the system shall attempt to send an email to
  the alert owner using the existing `email_service` SMTP path.
- REQ-ALERT-EMAIL-002 (State-Driven): WHILE SMTP is not configured (`SMTP_HOST` unset), the system shall
  skip the email and log a warning, and the in-app notification shall still be created.
- REQ-ALERT-EMAIL-003 (Unwanted): IF sending the email fails, THEN the failure shall not propagate and
  shall not prevent the alert from being marked triggered or the notification from being created.

### 4.5 API (REQ-ALERT-API-*)

- REQ-ALERT-API-001 (Event-Driven): WHEN a client sends `POST /alerts` with a valid bearer token and a
  valid body, the system shall create the alert and return it.
- REQ-ALERT-API-002 (Event-Driven): WHEN a client sends `GET /alerts` with a valid bearer token, the system
  shall return that user's alerts.
- REQ-ALERT-API-003 (Event-Driven): WHEN a client sends `PUT /alerts/{id}` or `DELETE /alerts/{id}` with a
  valid bearer token for an alert they own, the system shall apply the operation.
- REQ-ALERT-API-004 (Unwanted): IF an alert referenced by `PUT`/`DELETE` does not exist or is not owned by
  the authenticated user, THEN the system shall respond with HTTP 404.
- REQ-ALERT-API-005 (Unwanted): IF a `POST`/`GET`/`PUT`/`DELETE /alerts` request has no valid
  authentication, THEN the system shall respond with HTTP 401.
- REQ-ALERT-API-006 (Event-Driven): WHEN a client sends `POST /alerts/check`, the system shall run the alert
  check and return a summary of how many alerts were checked and triggered, without requiring authentication.

### 4.6 스케줄링 (REQ-ALERT-SCHED-*)

- REQ-ALERT-SCHED-001 (Ubiquitous): The system shall register a background job (`check_alerts`) that runs
  the alert check at a configurable interval defaulting to 10 minutes.
- REQ-ALERT-SCHED-002 (Ubiquitous): The system shall isolate the alert-check job from existing jobs so that
  its failure does not affect other scheduled jobs, and shall not modify the existing
  `check_price_alerts` job.

### 4.7 프론트엔드 (REQ-ALERT-FE-*)

- REQ-ALERT-FE-001 (Ubiquitous): The system shall provide an `/alerts` page listing the user's alerts with
  stock name, alert type, condition, and status (active/triggered).
- REQ-ALERT-FE-002 (Ubiquitous): The `/alerts` page shall allow creating, editing, and deleting alerts for
  all three alert types.
- REQ-ALERT-FE-003 (Event-Driven): WHEN an alert is created, edited, or deleted on the `/alerts` page, the
  list shall reflect the change.
- REQ-ALERT-FE-004 (Ubiquitous): The system shall reuse the existing Navbar notification bell, unread-count
  badge, and `/notifications` inbox page, and shall not rebuild them.
- REQ-ALERT-FE-005 (Event-Driven): WHEN alert data is loading, the `/alerts` page shall show a loading state.

### 4.8 비기능 (REQ-ALERT-NFR-*)

- REQ-ALERT-NFR-001 (Unwanted): IF any feature would execute or schedule trades or orders, THEN it shall NOT
  be built — automated trading is permanently excluded.
- REQ-ALERT-NFR-002 (Ubiquitous): The system shall reuse FinanceDataReader (via existing price and dividend
  paths) as the sole market data source and shall not add a new data provider.
- REQ-ALERT-NFR-003 (Ubiquitous): The system shall not create a new `notifications` table and shall not
  modify the existing `watchlist_alerts` table, its CRUD, or the `check_price_alerts` job.
- REQ-ALERT-NFR-004 (State-Driven): WHILE market or dividend data is unavailable, the system shall degrade
  gracefully (skip the affected alert) rather than failing the check.
- REQ-ALERT-NFR-005 (Ubiquitous): The migration shall advance to 0017 (down_rev=0016) and create only the
  `alerts` table, introducing no breaking change to existing endpoints or tables.

---

## 5. Exclusions (What NOT to Build)

- **자동 매매·주문 실행** — 규제·책임 리스크로 영구 제외 (REQ-ALERT-NFR-001).
- **신규 `notifications` 테이블** — 이미 마이그 0014에 존재. 재생성 금지(파괴적 중복). 기존 테이블 재사용.
- **인박스 엔드포인트 재구축** — `GET /notifications/`·`unread-count`·`{id}/read`·`read-all`은 이미 존재(PATCH).
  요청서의 `POST /notifications/{id}/read`·`POST /notifications/read-all` **POST 별칭을 새로 만들지 않는다**
  (기존 PATCH 재사용 — 계약 드리프트 방지).
- **`watchlist_alerts`·`/watchlist/alerts`·`check_price_alerts`·`_trigger_alert` 수정/제거** — 기존 목표가
  알림 경로는 손대지 않음. 신규 `alerts`와 공존.
- **프론트 알림 벨/배지/인박스 페이지 재구축** — SPEC-013에서 이미 구현. 재사용만.
- **UUID PK** — 코드베이스는 Integer autoincrement PK 규약. `alerts.id`는 Integer 사용.
- **`aiosmtplib` 등 신규 이메일 의존성** — 기존 `email_service.py`(smtplib) 재사용.
- **Celery·메시지 브로커 도입** — APScheduler 잡 + `POST /alerts/check`로 충분.
- **신규 알림 채널(웹푸시/SMS/카카오톡)·WebSocket 실시간 푸시.**
- **배당 데이터 적재 잡(전체 KRX 유니버스 수집)** — SPEC-018 M2(DEFERRED) 영역. 배당락 점검은 보유/관심
  종목 단위 실시간 베스트에포트 조회만.
- **배당락일 추측 단언** — 배당기준일 미확보 종목은 ex_dividend 알림을 발동하지 않음.
- **알림 발동 후 자동 재무장(rearm)·반복 알림** — 1회 발동 후 `is_triggered=True`로 종료(사용자가 재생성).
- **알림 우선순위·ML·개인화·어뷰징 방지·보존기간 정책.**

---

## 6. 영향 범위 (Affected Files)

### 신규
- `backend/alembic/versions/0017_alerts.py` — `alerts` 테이블 생성(down_rev=0016). **notifications 미생성.**
- `backend/src/stock_picker/notifications/general_alert_service.py` — 알림 CRUD + 점검·발동 로직
  (모듈/파일명은 RUN에서 기존 `notifications/` 구조와 정합 결정 가능).
- `backend/src/stock_picker/notifications/general_alert_router.py` — `/alerts` CRUD + `POST /alerts/check`.
- `backend/tests/unit/test_general_alerts.py` — 서비스·라우터·점검·발동·소유권·graceful degradation 테스트.
- `frontend/src/api/alerts.ts` — 알림 API 래퍼 + 타입.
- `frontend/src/pages/Alerts.tsx` — `/alerts` 페이지(목록·생성·수정·삭제·로딩).
- `frontend/src/__tests__/Alerts.test.tsx` — 프론트 테스트.

### 수정
- `backend/src/stock_picker/db/models.py` — `Alert` 모델 추가.
- `backend/src/stock_picker/api/main.py` — `general_alert_router` include_router(prefix `/alerts`) 추가.
- `backend/src/stock_picker/scheduler/jobs.py` — `check_alerts` 잡 + `add_job`(IntervalTrigger 기본 10분) 추가.
  (`check_price_alerts`·`_trigger_alert`는 불변.)
- `backend/src/stock_picker/notifications/email_service.py` — 알림 유형별 이메일 발송 함수 추가(재사용·확장,
  smtplib 유지). 필요 시 `notifications/schemas.py`에 Alert 스키마 추가.
- `frontend/src/App.tsx` — `/alerts` 보호 라우트 + NavBar 링크 추가(벨은 기존 재사용).

### 불변 (절대 수정 금지)
- `notifications` 테이블(마이그 0014)·`inbox_router.py`(인박스 엔드포인트).
- `watchlist_alerts`(마이그 0007)·`alert_router.py`·`alert_service.py`·`check_price_alerts`·`_trigger_alert`.
- 프론트 NavBar 벨·배지·`Notifications.tsx`·`api/notifications.ts`.
- 추천 산식·포트폴리오 성과/배당 엔드포인트.

---

## 7. 마일스톤 (Milestones)

| 마일스톤 | 설명 | 우선순위 |
|----------|------|----------|
| M1 | `Alert` 모델 + 마이그레이션 0017(`alerts`만, down_rev=0016) + Alert 스키마 (REQ-ALERT-001~003, NFR-005) | High |
| M2 | 알림 CRUD 서비스·라우터 (`POST`/`GET`/`PUT`/`DELETE /alerts`, 인증·소유권 404/401, REQ-ALERT-004~006·API-001~005) | High |
| M3 | 점검 로직 (target_price·surge_drop·ex_dividend 평가, prices.py + SPEC-019 배당 조회 재사용, graceful skip, REQ-ALERT-CHECK-*) | High |
| M4 | 발동→인박스 적재(기존 notifications 재사용, ref_date 멱등) + 이메일 베스트에포트(email_service 재사용) (REQ-ALERT-NOTI-*·EMAIL-*) | High |
| M5 | `POST /alerts/check` + 스케줄러 잡 `check_alerts`(예외 격리, 기존 잡 불변, REQ-ALERT-API-006·SCHED-*) | High |
| M6 | 프론트 `/alerts` 페이지(목록·생성·수정·삭제·로딩) + 라우트/링크, 벨 재사용 (REQ-ALERT-FE-*) | Medium |
| M7 | 테스트 & 품질 게이트 (커버리지 ≥85%, 소유권·중복멱등·graceful degradation·SMTP 미설정·기존 경로 회귀) | High |

---

## 8. 위험 (Risks)

- **인프라 중복으로 인한 혼동/회귀** (최대 위험): 알림·인박스·목표가 알림이 이미 존재한다. 신규 코드가
  기존 `notifications` 테이블을 재생성하거나 인박스 엔드포인트를 중복 정의하면 충돌·회귀 발생.
  완화: §1.3·§5에서 재사용/불변 대상을 명시, M7 회귀 테스트로 기존 경로 보호.
- **목표가 알림 이중 발송**: 사용자가 `watchlist_alerts`와 신규 `alerts` 양쪽에 동일 조건 등록 시 알림 2건.
  완화: §2.1에서 공존을 명시(의도된 동작), UI 안내 가능.
- **배당락 데이터 빈약**: FDR이 국내 배당기준일을 안정 제공 못함 → ex_dividend 알림이 거의 발동하지 않을 수
  있음. 완화: 미확보 시 미발동(추측 금지), SPEC-019 캐시 재사용으로 호출 최소화. UI에 데이터 한계 안내.
- **급등락 기준 모호**: `change_rate`가 당일 일간 변동률(전일 종가 대비)이라는 점을 사용자에게 분명히 표기.
- **점검 주기와 휘발성**: 10분 주기 점검은 장중 급등락을 놓칠 수 있음(실시간 아님). 완화: 주기 설정 가능,
  실시간 보장은 비목표로 명시.
- **env 이름 혼동**: 요청서 `SMTP_PASS` vs 실제 코드 `SMTP_PASSWORD`. 완화: 코드 기준 `SMTP_PASSWORD` 사용 명시.
