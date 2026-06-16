# SPEC-STOCK-025 진행 상황

- **SPEC**: SPEC-STOCK-025 — 사용자별 알림 채널·유형 설정 (Notification Preferences)
- **상태**: completed
- **작성일**: 2026-06-16
- **완료일**: 2026-06-16
- **개발 방법론**: DDD (ANALYZE-PRESERVE-IMPROVE) — 기존 코드베이스 확장

---

## 단계별 진행

| 단계 | 상태 | 비고 |
|------|------|------|
| Plan (spec/research/progress) | 완료 | 3파일 작성 |
| Run (구현) | 완료 | M1~M5 전체 구현 |
| Sync (문서·PR) | 대기 | |

---

## 마일스톤 진행

### M1 — 모델 + 마이그레이션 + 서비스 (High)
- [x] T1-1 NotificationPreference 모델 (`db/models.py`)
- [x] T1-2 마이그레이션 0018 (down_revision=0017, `alembic/versions/0018_notification_preferences.py`)
- [x] T1-3 is_channel_enabled_async (예외 시 fail-open)
- [x] T1-4 is_channel_enabled_sync
- [x] T1-5 get_preferences (7개 유형 기본값 채움)
- [x] T1-6 upsert_preferences (미지원 유형 ValueError)

### M2 — 설정 API (High)
- [x] T2-1 GET /notifications/preferences (인증 보호)
- [x] T2-2 PUT /notifications/preferences (upsert + 422)
- [x] T2-3 라우터 mount (`api/main.py`)

### M3 — 디스패치 게이팅 (High)
- [x] T3-1 _try_send_alert_email 이메일 게이트 (`general_alert_service.py`)
- [x] T3-2 _try_send_telegram 텔레그램 게이트 (`general_alert_service.py`)
- [x] T3-3 check_rec_changes 게이트 (rec_new/rec_dropped)
- [x] T3-4 check_rec_score_changes 게이트 (rec_score_change)
- [x] T3-5 인박스 무조건 생성 유지 확인

### M4 — 프론트 설정 UI (Medium)
- [x] T4-1 api/notifications.ts — getNotificationPreferences / updateNotificationPreferences 추가
- [x] T4-2 Settings.tsx — 7×2 체크박스 매트릭스 + 저장 버튼
- [x] T4-3 기존 이메일 구독 섹션 보존 (미수정)

### M5 — 단위 테스트 (Medium)
- [x] T5-1 test_기본활성 — 행 없을 때 True
- [x] T5-2 test_설정조회_7유형 — 기본값 채움
- [x] T5-3 test_upsert_생성 / test_upsert_갱신
- [x] T5-4 test_미지원유형_거부 (422)
- [x] T5-5 test_alerts_이메일OFF_skip
- [x] T5-6 test_alerts_텔레그램ON_발송
- [x] T5-7 test_rec_change_이메일OFF_skip
- [x] T5-8 test_게이트조회실패_기본발송
- [x] T5-9 test_인박스_무조건생성
- [x] T5-10 기존 테스트 통과 확인 (820/826, +20 신규)

---

## 테스트 결과

- 신규 테스트: 20개 전원 통과 (`tests/unit/test_notification_preferences.py`)
- 전체: 820/826 통과 (기존 584 기준 초과)
- 기존 실패 3개는 SPEC-025 범위 외 기존 오류

---

## 반복 로그

| 회차 | 충족 AC 수 | 오류 델타 | 메모 |
|------|-----------|----------|------|
| 1 | 11/11 | 0 | 전 AC 충족, 구현 완료 |

---

## 핵심 불변식 (회귀 방지)

1. 설정 행 없는 사용자 = 두 채널 모두 활성 (SPEC-024 하위 호환) — AC-10
2. 인앱 인박스 알림은 채널 설정과 무관하게 항상 생성 — AC-7/AC-8/REQ-PREF-DISPATCH-005
3. 게이트 조회 실패 시 fail-open (기본 발송) — AC-9
4. 레거시 watchlist_alerts / price_alert 경로 불변
5. 신규 마이그레이션은 0018 단일, down_revision=0017

---

## 제외 확인 (스코프 가드)

- 자동매매 — 영구 제외
- 신규 채널(웹 푸시·SMS·슬랙) — 제외
- 종목별 세분화·quiet hours·다이제스트 빈도 — 제외
- 인박스 토글 — 제외 (항상 생성)
- 스케줄러 비기동 수정 — SPEC-022 범위
