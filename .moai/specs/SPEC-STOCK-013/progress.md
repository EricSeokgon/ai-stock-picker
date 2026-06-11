# Progress — SPEC-STOCK-013 알림·모니터링 시스템 (Phase 14)

- **상태**: PLANNING
- **생성**: 2026-06-11
- **갱신**: 2026-06-11
- **작성자**: ircp

---

## 현재 단계

| 단계 | 상태 |
|------|------|
| Plan (기획) | 완료 |
| Run (구현) | 대기 |
| Sync (문서화) | 대기 |

---

## 마일스톤 진행

| 마일스톤 | 설명 | 상태 |
|----------|------|------|
| M1 | 데이터 모델 & 마이그레이션 0014 (notifications) | TODO |
| M2 | 인박스 서비스 & 라우터 | TODO |
| M3 | 가격 알림 → 인박스 연동 | TODO |
| M4 | 추천 변경 감지 | TODO |
| M5 | 프론트 알림 인박스 UI | TODO |
| M6 | 테스트 & 품질 게이트 | TODO |

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

## 다음 액션

- `/moai run SPEC-STOCK-013` 으로 M1(모델·마이그레이션)부터 구현 시작.
- RUN 단계에서 `/notifications` prefix 경로 충돌(기존 email_router) 여부를 검증하고 필요 시 `/notifications/inbox` 네임스페이스로 분리.
