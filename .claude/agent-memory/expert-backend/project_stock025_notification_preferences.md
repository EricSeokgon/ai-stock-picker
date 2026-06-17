---
name: project-stock025-notification-preferences
description: SPEC-STOCK-025 사용자별 알림 채널·유형 설정 구현 완료. M1~M3+M5 완료, 테스트 820/826.
metadata:
  type: project
---

SPEC-STOCK-025 알림 채널·유형 설정 구현 완료 (M1~M3, M5 — M4 프론트 제외).

**Why:** 사용자가 이메일·텔레그램 채널을 알림 유형별로 독립적으로 ON/OFF할 수 있어야 함.

**How to apply:** 향후 채널 발송 로직 수정 시 is_channel_enabled_async/sync 게이트 패턴 참조.

## 구현 파일

- `backend/alembic/versions/0018_notification_preferences.py` — migration (down_revision=0017)
- `backend/src/stock_picker/db/models.py` — NotificationPreference ORM 모델 추가
- `backend/src/stock_picker/notifications/preferences.py` — 서비스 (is_channel_enabled_async/sync, get_preferences, upsert_preferences)
- `backend/src/stock_picker/notifications/preferences_router.py` — GET/PUT /notifications/preferences
- `backend/src/stock_picker/notifications/general_alert_service.py` — _try_send_alert_email/_try_send_telegram 게이팅 추가
- `backend/src/stock_picker/notifications/rec_change.py` — check_rec_score_changes/check_rec_changes 게이팅 추가
- `backend/tests/unit/test_notification_preferences.py` — 유닛 테스트 20개

## 핵심 설계 결정

- opt-out 모델: 행 없음 = 채널 활성 (SPEC-024 하위 호환)
- fail-open: is_channel_enabled_async/sync 예외 시 True 반환
- 인박스 Notification은 채널 설정과 무관하게 항상 생성 (REQ-PREF-DISPATCH-005)
- 7개 지원 알림 유형: target_price, surge_drop, volume_spike, ex_dividend, rec_new, rec_dropped, rec_score_change

## 테스트 결과

- 신규: 20개 (test_notification_preferences.py)
- 전체: 820/826 통과 (6개 실패는 기존 test_collectors, test_portfolio_router — 이번 SPEC과 무관)
