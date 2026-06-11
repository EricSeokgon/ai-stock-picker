# Tasks — SPEC-STOCK-013 알림·모니터링 시스템 (Phase 14)

마일스톤은 우선순위·의존 순서 기준이며 기간 예측은 사용하지 않는다.

---

## M1 — 데이터 모델 & 마이그레이션 (Priority: High)

선행: 없음

- **TASK-013-01**: `db/models.py`에 `Notification` 모델 추가
  - 컬럼: id, user_id(FK users CASCADE), type(String20), krx_code(String10), title(String200), body(Text nullable), is_read(Boolean default False), ref_date(Date nullable), related_alert_id(FK watchlist_alerts nullable), created_at, read_at(nullable)
  - `UNIQUE(user_id, type, krx_code, ref_date)` 제약
  - 인덱스 `(user_id, is_read, created_at)` (REQ-NOTI-001, REQ-NFR-001)
- **TASK-013-02**: Alembic 마이그레이션 `0014_notifications.py` 작성 (down_revision=`0013`)
  - SQLite 테스트 호환(Date·UNIQUE 제약) 확인

산출물: `db/models.py`(수정), `alembic/versions/0014_notifications.py`(신규)

---

## M2 — 인박스 서비스 & 라우터 (Priority: High)

선행: M1

- **TASK-013-03**: `notifications/inbox_service.py` 작성
  - `list_notifications(user_id, unread_only, limit, db)` (REQ-NOTI-002·003·008)
  - `count_unread(user_id, db)` (REQ-NOTI-004)
  - `mark_read(user_id, notification_id, db)` — 타 사용자 시 404 (REQ-NOTI-005·007)
  - `mark_all_read(user_id, db)` (REQ-NOTI-006)
  - `create_notification(...)` — `UNIQUE` 충돌 시 무시(IntegrityError rollback, 멱등) (REQ-RC-005)
- **TASK-013-04**: `notifications/inbox_schemas.py` — `NotificationResponse`, `UnreadCountResponse`, `MarkAllResponse`
- **TASK-013-05**: `notifications/inbox_router.py` — GET 목록, GET unread-count, PATCH {id}/read, PATCH read-all
  - 전부 `get_current_user` 보호 (REQ-NFR-004)
- **TASK-013-06**: `api/main.py`에 인박스 라우터 등록 — 기존 email_router(`/notifications` prefix)와 경로 충돌 검증; 충돌 시 `/notifications/inbox` 네임스페이스로 분리

산출물: `notifications/inbox_service.py`·`inbox_schemas.py`·`inbox_router.py`(신규), `api/main.py`(수정)

---

## M3 — 가격 알림 → 인박스 연동 (Priority: High)

선행: M2

- **TASK-013-07**: `scheduler/jobs.py` `_trigger_alert`에 인박스 레코드 생성 추가
  - 텔레그램/이메일 발송 성공·실패와 무관하게 `create_notification(type='price_alert', related_alert_id=alert.id, ref_date=None)` 호출 (REQ-PA-001·003)
  - 한국어 title/body 구성(목표가·현재가·방향) (REQ-PA-002)
  - 인박스 생성 실패 시 로그만 남기고 잡 계속 (REQ-PA-004)

산출물: `scheduler/jobs.py`(수정)

---

## M4 — 추천 변경 감지 (Priority: High)

선행: M2

- **TASK-013-08**: `notifications/rec_change.py` 작성
  - `detect_recommendation_changes(db)` — 현재 trade_date vs 직전 distinct trade_date 유니버스 집합 차집합 계산 (REQ-RC-001)
  - 진입(`rec_new`)·이탈(`rec_dropped`) 종목 도출, 직전 trade_date 부재 시 dropped 없음 (REQ-RC-006)
  - 관심 종목(`WatchlistItem`) 보유 사용자별로 알림 생성, `ref_date=현재 trade_date` (REQ-RC-002·003·004)
  - `create_notification` 멱등성으로 중복 방지 (REQ-RC-005)
  - 한국어 title/body (REQ-RC-007)
- **TASK-013-09**: `scheduler/jobs.py`에 `run_recommendation_change_detection()` 잡 함수 추가 + `run_daily_pipeline`·`run_intraday_pipeline`에서 `run_recommendation` 직후 호출, 예외 격리 (REQ-MON-001·002·003)

산출물: `notifications/rec_change.py`(신규), `scheduler/jobs.py`(수정)

---

## M5 — 프론트 알림 인박스 UI (Priority: Medium)

선행: M2

- **TASK-013-10**: `frontend/src/api/notifications.ts` 확장 — 인박스 목록/unread-count/read/read-all 호출 추가(기존 알림 CRUD 유지)
- **TASK-013-11**: NavBar(App.tsx)에 종 아이콘 + 미읽음 배지(unread-count 폴링) (REQ-FE-001·004)
- **TASK-013-12**: `frontend/src/pages/Notifications.tsx` 또는 드롭다운 인박스 — 목록·읽음 처리·모두 읽음 (REQ-FE-002·003)
- **TASK-013-13**: `App.tsx`에 `/notifications` 보호 라우트 추가(인박스를 페이지로 둘 경우)

산출물: `frontend/src/api/notifications.ts`(수정), `frontend/src/pages/Notifications.tsx`(신규), `frontend/src/App.tsx`(수정)

---

## M6 — 테스트 & 품질 게이트 (Priority: High)

선행: M3·M4·M5

- **TASK-013-14**: 백엔드 테스트 — 인박스 서비스/라우터(권한 격리·unread filter·read 처리), 멱등 생성, 가격 알림 인박스 연동, 추천 변경 감지(진입/이탈/첫 실행/중복)
- **TASK-013-15**: 프론트 테스트(vitest) — 배지 렌더·읽음 처리 상호작용
- **TASK-013-16**: `ruff check` + `pytest --cov-fail-under=85` 통과, frontend `npm run lint`+`build` 통과 (REQ-NFR-002)

산출물: `backend/tests/...`(신규), `frontend/src/...test`(신규)
