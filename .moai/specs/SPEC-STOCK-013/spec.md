---
id: SPEC-STOCK-013
version: 0.1.0
status: draft
created: 2026-06-11
updated: 2026-06-11
author: ircp
priority: medium
issue_number: null
---

# 알림·모니터링 시스템 (Phase 14)

## HISTORY

- 2026-06-11 (v0.1.0): 최초 작성. 인앱 알림 인박스 + 추천 변경 감지 + 모니터링 백그라운드 연동.

---

## 1. 개요 (Overview)

기존 가격 알림은 **텔레그램/이메일로 1회 발송 후 알림을 비활성화**(`WatchlistAlert.is_active=False`)할 뿐, 앱 내부에 **영속적인 알림 기록이 남지 않는다**. 또한 사용자의 관심 종목이 추천 목록에 새로 진입하거나 이탈해도 이를 알려주는 수단이 없다.

이 SPEC은 다음을 추가한다.

1. **인앱 알림 인박스(Notification Inbox)** — 미읽음/읽음 상태를 가진 영속 알림 레코드와 조회·읽음 처리 API.
2. **가격 알림 → 인박스 연동** — 기존 `check_price_alerts` 발동 시 인박스 레코드도 함께 생성.
3. **추천 변경 알림** — 관심 종목이 추천 목록에 신규 진입(`rec_new`)하거나 이탈(`rec_dropped`)하면 인박스 알림 생성.
4. **모니터링 백그라운드 태스크 연동** — 추천 변경 감지를 기존 추천 파이프라인 직후 단계로 연결(신규 타이머 도입 없음).
5. **프론트 알림 인박스 UI** — NavBar 종 아이콘(미읽음 배지) + 알림 목록 페이지·읽음 처리.

> 비기능: 신규 알림 채널(웹푸시/SMS)·자동 매매·WebSocket 실시간 푸시는 도입하지 않는다. 알림 전달은 기존 텔레그램/이메일 채널 + 인앱 폴링 인박스로 한정한다.

---

## 2. 기존 자산 재사용 (Existing Assets — Reuse, Do NOT Redefine)

이 SPEC은 아래 기존 구현을 **재정의하지 않고 재사용·연동**한다.

| 자산 | 위치 | 상태 | SPEC-013에서의 취급 |
|------|------|------|---------------------|
| `WatchlistItem` 테이블 + `GET/POST/DELETE /watchlist` | `watchlist/router.py`, `watchlist/service.py`, 마이그 0006 | 존재 | **관심 종목 등록 = 이미 완성**. 추천 변경 알림의 대상 집합으로 조회만 함 |
| `WatchlistAlert` 테이블 + `GET/POST/DELETE /watchlist/alerts` | `notifications/alert_router.py`, `notifications/alert_service.py`, 마이그 0007 | 존재 | 가격 알림 CRUD = 이미 완성. 발동 로직에 인박스 기록만 추가 |
| `check_price_alerts` (5분 IntervalTrigger) + `_trigger_alert` | `scheduler/jobs.py` | 존재 | 발동 시 인박스 레코드 생성 호출만 추가 |
| `run_recommendation` + `run_daily_pipeline`·`run_intraday_pipeline` | `scheduler/jobs.py` | 존재 | 추천 적재 직후 변경 감지 단계 연결 |
| `Recommendation` 테이블 (`trade_date`·`asset_type`·`krx_code`·`rank`) | `db/models.py`, 진실 소스 | 존재 | 추천 변경 감지의 비교 기준(현재 vs 직전 trade_date) |
| 텔레그램 `_send_message_sync`·이메일 `send_price_alert_email` | `telegram/notifier.py`, `notifications/email_service.py` | 존재 | 그대로 사용. 채널 추가 없음 |

---

## 3. 환경·전제 (Environment & Assumptions)

- 백엔드: Python 3.11 + FastAPI + SQLAlchemy 2.0(async API / sync 백그라운드) + PostgreSQL + APScheduler.
- 인증: JWT 기반. 인박스 API는 모두 `get_current_user` 의존성으로 보호한다.
- 알림은 **사용자별(user_id)** 로 귀속된다. 비로그인 사용자는 인박스를 사용할 수 없다.
- `check_price_alerts`·`_trigger_alert`는 **동기 세션**(`SyncSessionLocal`)에서 동작하므로, 인박스 쓰기도 동일 동기 세션에서 수행한다.
- 추천 변경 감지는 추천 파이프라인이 실행될 때(일 1회 06:00 + 장중 30분)만 발생한다. 추천이 갱신되지 않으면 변경도 없다.
- DB 마이그레이션은 누적이며 최신은 0013이다. 이 SPEC은 **0014 단일 마이그레이션**(notifications 테이블)만 추가한다.

---

## 4. 데이터 모델 (Data Model)

### 4.1 `notifications` 테이블 (신규, 마이그레이션 0014)

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| `id` | Integer | PK, autoincrement | |
| `user_id` | Integer | FK → users.id, ON DELETE CASCADE, NOT NULL | 알림 수신자 |
| `type` | String(20) | NOT NULL | `price_alert` \| `rec_new` \| `rec_dropped` |
| `krx_code` | String(10) | NOT NULL | 대상 종목코드 |
| `title` | String(200) | NOT NULL | 한국어 알림 제목 |
| `body` | Text | nullable | 한국어 상세 본문 |
| `is_read` | Boolean | NOT NULL, default False | 읽음 여부 |
| `ref_date` | Date | nullable | 추천 변경 알림 중복 방지용 비교 기준일(trade_date). 가격 알림은 NULL |
| `related_alert_id` | Integer | FK → watchlist_alerts.id, nullable | 가격 알림 출처 추적용 |
| `created_at` | DateTime | server_default now() | |
| `read_at` | DateTime | nullable | 읽음 처리 시각 |

- **중복 방지 제약**: `UNIQUE(user_id, type, krx_code, ref_date)`
  - 추천 변경 알림은 동일 사용자·종목·타입·기준일 조합이 1회만 생성된다(장중 30분 재실행 시 중복 방지).
  - 가격 알림은 `ref_date=NULL`이며 발동 1회마다 1건이 정상이다(알림은 발동 후 비활성화되므로 재발동 없음).
- 인덱스: `(user_id, is_read, created_at DESC)` — 미읽음 우선 목록 조회 최적화.

---

## 5. 기능 요구사항 (EARS Requirements)

### 5.1 알림 인박스 (REQ-NOTI-*)

- **REQ-NOTI-001** (Ubiquitous): The system **shall** persist every generated notification as a `notifications` row owned by a single `user_id`.
- **REQ-NOTI-002** (Event-Driven): **When** an authenticated user requests `GET /notifications`, the system **shall** return that user's notifications ordered by `created_at` descending.
- **REQ-NOTI-003** (State-Driven): **While** the `unread_only=true` query parameter is set, the system **shall** return only notifications with `is_read=false`.
- **REQ-NOTI-004** (Event-Driven): **When** an authenticated user requests `GET /notifications/unread-count`, the system **shall** return the integer count of that user's `is_read=false` notifications.
- **REQ-NOTI-005** (Event-Driven): **When** an authenticated user sends `PATCH /notifications/{id}/read`, the system **shall** set `is_read=true` and `read_at=now()` for that notification and return the updated record.
- **REQ-NOTI-006** (Event-Driven): **When** an authenticated user sends `PATCH /notifications/read-all`, the system **shall** mark all of that user's unread notifications as read.
- **REQ-NOTI-007** (Unwanted): **If** a user requests or mutates a notification that does not belong to that user, **then** the system **shall** respond `404 Not Found` and **shall not** expose or modify the record.
- **REQ-NOTI-008** (State-Driven): **While** a `limit` query parameter is provided (default 50, max 100), the system **shall** cap the number of returned notifications to that value.

### 5.2 가격 알림 → 인박스 연동 (REQ-PA-*)

- **REQ-PA-001** (Event-Driven): **When** `check_price_alerts` triggers an active `WatchlistAlert`, the system **shall** create a `notifications` row with `type='price_alert'`, `krx_code` and `related_alert_id` of the alert, and `user_id` of the alert owner, **in addition to** the existing telegram/email delivery.
- **REQ-PA-002** (Ubiquitous): The system **shall** compose the price-alert notification `title`/`body` in Korean including the target price, current price, and direction (이상/이하).
- **REQ-PA-003** (Unwanted): **If** telegram or email delivery fails for a triggered alert, **then** the system **shall** still create the in-app notification row (in-app inbox is independent of external channel success).
- **REQ-PA-004** (Unwanted): **If** inbox row creation fails, **then** the system **shall** log the error and **shall not** abort the price-alert job for remaining alerts.

### 5.3 추천 변경 알림 (REQ-RC-*)

- **REQ-RC-001** (Event-Driven): **When** the recommendation pipeline completes a run, the system **shall** compute the change set between the current `trade_date` recommendation universe and the immediately previous distinct `trade_date` universe.
- **REQ-RC-002** (Event-Driven): **When** a `krx_code` appears in the current universe but not in the previous one **and** that `krx_code` is in a user's watchlist, the system **shall** create a `type='rec_new'` notification for that user.
- **REQ-RC-003** (Event-Driven): **When** a `krx_code` appears in the previous universe but not in the current one **and** that `krx_code` is in a user's watchlist, the system **shall** create a `type='rec_dropped'` notification for that user.
- **REQ-RC-004** (Ubiquitous): The system **shall** set `ref_date` to the current `trade_date` on every recommendation-change notification for deduplication.
- **REQ-RC-005** (Unwanted): **If** a recommendation-change notification with the same `(user_id, type, krx_code, ref_date)` already exists, **then** the system **shall not** create a duplicate (intraday re-runs are idempotent).
- **REQ-RC-006** (Unwanted): **If** there is no previous distinct `trade_date` (first ever run), **then** the system **shall** create no `rec_dropped` notifications and **may** create no `rec_new` notifications.
- **REQ-RC-007** (Ubiquitous): The system **shall** compose `rec_new`/`rec_dropped` `title`/`body` in Korean naming the stock and its recommendation status change.

### 5.4 모니터링 백그라운드 연동 (REQ-MON-*)

- **REQ-MON-001** (Event-Driven): **When** `run_daily_pipeline` or `run_intraday_pipeline` finishes `run_recommendation`, the system **shall** invoke the recommendation-change detection step.
- **REQ-MON-002** (Unwanted): **If** the recommendation-change detection step raises an exception, **then** the system **shall** log it and **shall not** fail the overall pipeline (graceful degradation, consistent with `run_sector_aggregation`).
- **REQ-MON-003** (Ubiquitous): The system **shall not** introduce a new standalone timer for recommendation-change detection; detection is bound to the existing recommendation pipeline cadence.

### 5.5 프론트 알림 인박스 UI (REQ-FE-*)

- **REQ-FE-001** (Event-Driven): **When** an authenticated user is on any page, the NavBar **shall** display a notification bell icon with an unread-count badge sourced from `GET /notifications/unread-count`.
- **REQ-FE-002** (Event-Driven): **When** the user opens the notification inbox, the UI **shall** list notifications (newest first) with read/unread visual distinction.
- **REQ-FE-003** (Event-Driven): **When** the user clicks a notification or a "모두 읽음" action, the UI **shall** call the corresponding read endpoint and update the badge.
- **REQ-FE-004** (State-Driven): **While** the user is not authenticated, the UI **shall not** render the notification bell.

### 5.6 비기능 요구사항 (REQ-NFR-*)

- **REQ-NFR-001**: 인박스 목록·미읽음 카운트 API는 인덱스를 활용해 사용자당 P95 200ms 이내 응답한다.
- **REQ-NFR-002**: 백엔드 신규 코드 테스트 커버리지는 `fail_under=85`를 충족한다.
- **REQ-NFR-003**: 알림 본문·코드 주석·커밋 메시지는 한국어, 식별자·EARS 키워드는 영어로 작성한다.
- **REQ-NFR-004**: 모든 신규 인박스 엔드포인트는 JWT 인증으로 보호하며 타 사용자 데이터 접근을 차단한다.

---

## 6. API 계약 (API Contract)

신규 라우터 `notifications` (prefix `/notifications`, 인증 필요):

| 메서드 | 경로 | 설명 | 응답 |
|--------|------|------|------|
| GET | `/notifications` | 인박스 목록 (`unread_only`, `limit` 쿼리) | `NotificationResponse[]` |
| GET | `/notifications/unread-count` | 미읽음 개수 | `{ "unread_count": int }` |
| PATCH | `/notifications/{id}/read` | 단건 읽음 처리 | `NotificationResponse` |
| PATCH | `/notifications/read-all` | 전체 읽음 처리 | `{ "updated": int }` |

> 주의: 기존 `email_router`가 이미 prefix `/notifications`로 등록되어 있다(`/notifications/...` 이메일 구독). 신규 알림 인박스 라우터는 경로 충돌을 피하기 위해 **`/notifications/inbox`** 하위로 등록하거나 별도 라우터를 `/notifications` prefix로 추가하되 위 4개 경로가 기존 email 경로(`/notifications/email...`)와 겹치지 않음을 RUN 단계에서 검증한다. (계약 확정: 충돌 시 `/notifications/inbox`·`/notifications/inbox/unread-count` 등으로 네임스페이스 분리.)

`NotificationResponse`: `{ id, type, krx_code, title, body, is_read, ref_date, related_alert_id, created_at, read_at }`

---

## 7. 제외 범위 (Exclusions — What NOT to Build)

- **자동 매매·주문 실행** — 프로젝트 영구 제외(규제·책임 리스크). 절대 포함 금지.
- **신규 알림 채널** — 웹푸시(Web Push)·SMS·카카오 알림톡 등 신규 전달 채널 도입 안 함. 기존 텔레그램·이메일 + 인앱 인박스만.
- **관심 종목 등록 CRUD 신규 구현** — Phase E(`watchlist/`, 마이그 0006)에서 이미 완성. 조회 재사용만.
- **가격 알림 CRUD 신규 구현** — Phase F(`notifications/alert_*`, 마이그 0007)에서 이미 완성. 발동 시 인박스 기록 추가만.
- **WebSocket 실시간 알림 푸시** — 인박스는 폴링(unread-count) 기반. 실시간 서버푸시는 범위 밖.
- **알림 환경설정 UI 고도화** — 사용자별 알림 on/off·채널 선택·빈도 설정 화면은 범위 밖.
- **추천 변경 임계값·랭크 변동 알림** — "순위 N단계 변동" 같은 세분화 알림은 제외. 진입(`rec_new`)/이탈(`rec_dropped`) 2종만.
- **ML 기반 알림 우선순위·요약·다이제스트** — 범위 밖.
- **알림 보존 기간 정책·자동 삭제(아카이빙)** — 범위 밖.

---

## 8. 관련 SPEC (Related SPECs)

- SPEC-STOCK-003 (관심목록 Phase 4, `watchlist_items` 0006) — 관심 종목 등록 의존.
- SPEC-STOCK-004 (알림 고도화 Phase 5, `watchlist_alerts` 0007·`email_subscriptions` 0008) — 가격 알림·이메일 채널 의존.
- SPEC-STOCK-006 (추천 근거 투명성) — `recommendations` 진실 소스 활용.
