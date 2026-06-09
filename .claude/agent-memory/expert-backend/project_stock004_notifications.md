---
name: project-stock004-notifications
description: SPEC-STOCK-004 알림 시스템 구현 완료 — 가격 알림 + 이메일 구독. 테스트 41/41 통과.
metadata:
  type: project
---

SPEC-STOCK-004 TASK-001~009 완료 (알림 시스템).

**Why:** 관심종목 목표가 도달 시 텔레그램/이메일 알림 + 주간 요약 메일 발송.

**How to apply:** 이 SPEC 관련 작업 시 아래 파일 경로 참조.

## 구현된 파일

- `backend/src/stock_picker/db/models.py` — WatchlistAlert, EmailSubscription 모델 추가 (Float 임포트 포함)
- `backend/alembic/versions/0007_watchlist_alerts.py` — watchlist_alerts 마이그레이션
- `backend/alembic/versions/0008_email_subscriptions.py` — email_subscriptions 마이그레이션
- `backend/src/stock_picker/notifications/__init__.py` — 패키지 초기화
- `backend/src/stock_picker/notifications/schemas.py` — WatchlistAlertCreate/Response, EmailSubscriptionCreate/Response
- `backend/src/stock_picker/notifications/alert_service.py` — create_alert, get_alerts, delete_alert, evaluate_alert
- `backend/src/stock_picker/notifications/alert_router.py` — POST/GET/DELETE /watchlist/alerts
- `backend/src/stock_picker/notifications/email_service.py` — SMTP 발송, subscribe/unsubscribe/get_subscription
- `backend/src/stock_picker/notifications/email_router.py` — POST/DELETE /notifications/email
- `backend/src/stock_picker/scheduler/jobs.py` — check_price_alerts(5분), send_weekly_email_summary(월 07:00 KST), _trigger_alert 헬퍼 추가
- `backend/src/stock_picker/api/main.py` — alert_router, email_router 등록

## 테스트 파일

- `backend/tests/unit/test_alert_service.py` — 14개 테스트
- `backend/tests/unit/test_email_service.py` — 9개 테스트
- `backend/tests/integration/test_alert_router.py` — 11개 테스트
- `backend/tests/integration/test_email_router.py` — 7개 테스트

## 주요 패턴

- SMTP 설정은 환경변수만 사용 (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM)
- SMTP_HOST 미설정 시 조용히 False 반환 (예외 미전파)
- 로그인 엔드포인트: /auth/login JSON body (form-data 아님) — 테스트에서 `json=` 사용
- SyncSessionLocal은 session.py에서 `from stock_picker.db.session import SyncSessionLocal` 로 임포트
- test_scheduler_intraday.py의 잡 개수 테스트를 4개 잡 기준으로 업데이트함

## 전체 테스트 결과

알림 관련 41/41 통과. 전체 340/345 통과 (기존 5개 collector HTTP mock 실패는 이전부터 존재).
