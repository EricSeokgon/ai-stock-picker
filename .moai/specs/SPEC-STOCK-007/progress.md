# SPEC-STOCK-007 — 진행 현황 (Progress)

Phase 8: 종목 검색 · 상세 페이지 · 추천 품질 피드백

상태 범례: ⬜ 대기(pending) · 🟦 진행 중(in-progress) · ✅ 완료(done) · ⛔ 차단(blocked)

최종 갱신: 2026-06-10 (Plan 단계 — 전체 대기)

---

## 작업 상태

| 작업 | 설명 | 도메인 | 상태 |
|------|------|--------|------|
| TASK-001 | 피드백 모델 + 마이그레이션 0010 | backend/db | ⬜ pending |
| TASK-002 | 검색 서비스 로직 | backend/search | ⬜ pending |
| TASK-003 | stocks 라우터 + 검색 엔드포인트 + 스키마 | backend/api | ⬜ pending |
| TASK-004 | 가격 시계열 함수 + 캐시 | backend/mapping | ⬜ pending |
| TASK-005 | 가격 엔드포인트 + 스키마 | backend/api | ⬜ pending |
| TASK-006 | 피드백 서비스 로직 | backend/feedback | ⬜ pending |
| TASK-007 | 피드백 엔드포인트 + 스키마 | backend/api | ⬜ pending |
| TASK-008 | 검색 테스트 | backend/test | ⬜ pending |
| TASK-009 | 가격 시계열 테스트 | backend/test | ⬜ pending |
| TASK-010 | 피드백 테스트 | backend/test | ⬜ pending |
| TASK-011 | 검색 컴포넌트 + API 클라이언트/타입 | frontend | ⬜ pending |
| TASK-012 | 가격 차트(Recharts) + StockDetail 통합 | frontend | ⬜ pending |
| TASK-013 | 피드백 버튼 + 종목 상세 라우트 페이지 | frontend | ⬜ pending |
| TASK-014 | 프론트 테스트 | frontend/test | ⬜ pending |

진행률: 0/14 (0%)

---

## 반복 로그 (Iteration Log)

재계획 게이트 감지를 위한 반복별 기록. 각 Run 반복 종료 시 추가한다.

| 반복 | 충족 수용 기준 수 | 오류 수 변화 | 비고 |
|------|------------------|-------------|------|
| (Plan) | 0 | 0 | SPEC 초안 작성 완료, 구현 미착수 |

---

## 비고

- 모든 신규 자산(엔드포인트·테이블·스키마·컴포넌트)은 추가 전용 — 기존 SPEC-STOCK-001~006 동작 보존 필수.
- `prices.py`의 기존 `get_stock_price_data()`는 변경 금지(추천 파이프라인 의존).
- 자동 매매·피드백 재가중은 영구/현 sprint 제외(spec.md §4).
