# Progress — SPEC-STOCK-013 알림·모니터링 시스템 (Phase 14)

- **상태**: SYNC COMPLETE
- **생성**: 2026-06-11
- **갱신**: 2026-06-11
- **작성자**: ircp

---

## 현재 단계

| 단계 | 상태 |
|------|------|
| Plan (기획) | 완료 |
| Run (구현) | 완료 |
| Sync (문서화) | 완료 |

---

## 마일스톤 진행

| 마일스톤 | 설명 | 상태 |
|----------|------|------|
| M1 | 데이터 모델 & 마이그레이션 0014 (notifications) | DONE |
| M2 | 인박스 서비스 & 라우터 | DONE |
| M3 | 가격 알림 → 인박스 연동 | DONE |
| M4 | 추천 변경 감지 | DONE |
| M5 | 프론트 알림 인박스 UI | DONE |
| M6 | 테스트 & 품질 게이트 | DONE |

---

## 핵심 설계 결정 (Plan 단계 확정)

1. **관심 종목 등록은 신규 구현 아님** — Phase E(`watchlist/`, 마이그 0006)에서 완성됨. 추천 변경 알림 대상 집합으로 조회만 재사용.
2. **가격 알림 CRUD도 신규 구현 아님** — Phase F(`notifications/alert_*`, 마이그 0007)에서 완성됨. 발동 로직(`_trigger_alert`)에 인박스 기록만 추가.
3. **신규 알림 채널 없음** — 텔레그램·이메일 기존 채널 + 인앱 인박스만. 웹푸시/SMS/WebSocket 푸시 제외.
4. **추천 변경 감지는 전용 타이머 없이** 기존 추천 파이프라인(`run_recommendation`) 직후 단계로 연결. 직전 distinct `trade_date` 유니버스와 차집합 비교.
5. **중복 방지**: `UNIQUE(user_id, type, krx_code, ref_date)`로 장중 30분 재실행 멱등성 보장.
6. **마이그레이션 0014 단일 추가** (notifications 테이블). down_revision=0013.
7. **자동 매매·주문 영구 제외** 유지.

---

## 구현 결과 (M6 완료 기준)

- **백엔드 테스트**: 18/18 통과
  - `backend/tests/unit/test_rec_change.py` (8개): `check_rec_changes()`, `_insert_notification_safe()` 단위 테스트
  - `backend/tests/integration/test_inbox_router.py` (10개): 인박스 HTTP 엔드포인트 통합 테스트
- **프론트엔드 테스트**: 170/170 통과
  - `frontend/src/__tests__/notifications_inbox.test.ts` (11개): 인박스 API 함수 단위 테스트
  - `frontend/src/__tests__/Settings.test.tsx` (importOriginal 패턴 적용)
- **버그 수정**: `frontend/src/api/*.js` 스테일 컴파일 아티팩트 삭제 (vitest가 `.ts` 대신 `.js` 로드하던 문제)

## 다음 액션

SPEC-STOCK-013 완료. 다음 SPEC 계획 시 /moai plan 사용.
