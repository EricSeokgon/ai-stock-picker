# Task Decomposition
SPEC: SPEC-STOCK-004

## 마일스톤

- **Phase A** (TASK-001~005): 관심 목록 가격 알림(Watchlist Price Alerts) — Priority High
- **Phase B** (TASK-006~009): 이메일 알림(Email Notifications) — Priority Medium
- **Phase C** (TASK-010): 프론트엔드 통합 — Priority Medium

## 설계 확정값
- 가격 알림: 신규 테이블 `watchlist_alerts` (마이그레이션 0007), direction ∈ {above, below}, 1회성(도달 시 is_active=false + triggered_at)
- 가격 점검: 기존 `scheduler/jobs.py` `AsyncIOScheduler`에 IntervalTrigger 약 5분 작업 추가, `get_current_price(krx_code)` 재사용
- 텔레그램 전송: SPEC-STOCK-002 `telegram/notifier.py`(`_send_message_sync`) 재사용
- 이메일: Python 표준 `smtplib`+`email`, plain text 한국어, 환경 변수 `SMTP_HOST/PORT/USER/PASSWORD/FROM`
- 주간 요약: 신규 테이블 `email_subscriptions` (마이그레이션 0008, UNIQUE(user_id)), CronTrigger 월요일 07:00 Asia/Seoul, 상위 5개 추천
- 인증: SPEC-STOCK-002의 `get_current_user` 의존성 재사용
- 메일/알림 모두 면책·해지 안내 포함, 자동 매매 영구 제외

## 의존성
- Phase A는 SPEC-STOCK-003(`watchlist_items`, `get_current_price`) + SPEC-STOCK-002(텔레그램, JWT) + 기존 APScheduler에 의존, 먼저 구현
- Phase B는 SPEC-STOCK-002(JWT) + 기존 APScheduler + `recommendations`(주간 요약 입력)에 의존
- 가격 도달 이메일(TASK-008)은 Phase A의 트리거(TASK-005)에 연결되므로 Phase A 이후 통합

| ID | 설명 | Feature | 주요 파일 | 상태 |
|----|------|---------|----------|------|
| TASK-001 | watchlist_alerts 테이블(direction/target_price/is_active/triggered_at) + Alembic 마이그레이션 (0007) | 가격 알림 | db/models.py, alembic/versions/0007_watchlist_alerts.py | done |
| TASK-002 | 가격 알림 서비스(생성/조회/삭제, 소유권 검증) | 가격 알림 | notifications/alert_service.py, notifications/schemas.py | done |
| TASK-003 | 가격 알림 라우터 POST/GET/DELETE /watchlist/alerts + 인증·401/403/404 처리 | 가격 알림 | notifications/alert_router.py, api/main.py | done |
| TASK-004 | 가격 점검 작업: 활성 알림 above/below 조건 평가 + 알림 단위 예외 격리 | 가격 알림 | scheduler/jobs.py, notifications/alert_service.py | done |
| TASK-005 | 조건 충족 시 텔레그램 1회 전송 + is_active=false + triggered_at 기록 + 텔레그램 미구독 안전 스킵 | 가격 알림 | scheduler/jobs.py, telegram/notifier.py(재사용) | done |
| TASK-006 | email_subscriptions 테이블(UNIQUE(user_id)) + Alembic 마이그레이션 (0008) | 이메일 | db/models.py, alembic/versions/0008_email_subscriptions.py | done |
| TASK-007 | SMTP 발송 모듈(smtplib+email) + plain text 한국어 템플릿(가격 도달·주간 요약) + 면책/해지 안내 + 실패 격리 | 이메일 | notifications/email_service.py | done |
| TASK-008 | 이메일 구독 라우터 POST/DELETE /notifications/email + 유효성(422)/인증(401) + 가격 도달 메일 트리거 연동 | 이메일 | notifications/email_router.py, scheduler/jobs.py | done |
| TASK-009 | 주간 요약 작업: 월요일 07:00 KST CronTrigger, 활성 구독자에게 상위 5개 추천 메일 발송 | 이메일 | scheduler/jobs.py, notifications/email_service.py | done |
| TASK-010 | 프론트: Watchlist 목표가 알림 추가·목록·삭제 UI + /settings 이메일 구독 토글 페이지 + 라우트·인증 가드 + 실패 롤백 | Frontend | pages/Watchlist.tsx, pages/Settings.tsx, 라우팅, API 클라이언트 | done |
