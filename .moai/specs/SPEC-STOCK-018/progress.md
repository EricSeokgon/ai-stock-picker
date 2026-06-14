# Progress — SPEC-STOCK-018 종목 스크리너 (Phase 18)

- **상태**: SYNC COMPLETE
- **생성**: 2026-06-12
- **갱신**: 2026-06-15
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
| M1 | DB 모델 & 마이그레이션 0016 (`stock_fundamentals`·`screener_presets`, down_rev=0015) | DONE |
| M2 | 펀더멘털 수집 잡 (FDR 기반 지표 산출·upsert·일일 파이프라인 연동, REQ-SCR-DATA-*) | DEFERRED |
| M3 | 스크리너 실행 서비스·라우터 (`POST /screener/run`, AND 필터·NULL 제외, REQ-SCR-001~007) | DONE |
| M4 | 프리셋 CRUD 라우터 (5개 상한·소유권 검증, REQ-SCR-PRESET-*·REQ-SCR-API-*) | DONE |
| M5 | 프론트 스크리너 페이지 (필터 패널·정렬 테이블·로딩·프리셋, REQ-SCR-FE-*) | DONE |
| M6 | 테스트 & 품질 게이트 (커버리지: 33 backend + 7 frontend 신규 테스트 통과) | DONE |

---

## 구현 요약 (TDD RED-GREEN-REFACTOR)

### RED 단계 (이전 세션)
- `backend/tests/unit/test_screener_service.py` — 24개 테스트 작성 (FilterRange, apply_filters, to_screener_result, 프리셋 CRUD)
- `backend/tests/unit/test_screener_router.py` — 9개 테스트 작성 (POST /screener/run, 프리셋 엔드포인트)
- `backend/src/stock_picker/db/models.py` — `StockFundamental`, `ScreenerPreset` 모델 추가

### GREEN 단계 (이번 세션)
- `backend/src/stock_picker/screener/__init__.py`
- `backend/src/stock_picker/screener/schemas.py` — Pydantic v2 스키마 (FilterRange, ScreenerCriteria, ScreenerRequest/Response, Preset*)
- `backend/src/stock_picker/screener/service.py` — 필터 로직 + 프리셋 CRUD (apply_filters, to_screener_result, run_screener, list/create/delete_preset)
- `backend/src/stock_picker/screener/router.py` — FastAPI 라우터 (POST /screener/run, GET/POST/DELETE /screener/presets)
- `backend/alembic/versions/0016_screener.py` — Alembic 마이그레이션 (revision=0016, down_revision=0015)
- `backend/src/stock_picker/api/main.py` — screener_router 등록
- `frontend/src/api/screener.ts` — TypeScript API 래퍼
- `frontend/src/pages/Screener.tsx` — 스크리너 페이지 (필터 패널 + 정렬 테이블 + 프리셋 UI)
- `frontend/src/__tests__/Screener.test.tsx` — 7개 프론트엔드 테스트
- `frontend/src/App.tsx` — /screener 라우트 + 네비 링크 추가

### 테스트 결과
- 백엔드 신규: **33/33 통과** (test_screener_service.py 24개 + test_screener_router.py 9개)
- 프론트엔드 신규: **7/7 통과**
- 기존 실패 5개 (test_collectors.py) — pre-existing, 범위 외

### M2 유보 사유
일일 FDR 수집 잡은 DB 연결 + 스케줄러 환경이 필요하여 별도 SPEC(SPEC-STOCK-019) 또는 운영 환경 연동 시 구현 예정. `stock_fundamentals` 테이블과 마이그레이션은 이미 생성 완료 — 수집 잡만 추가하면 됨.

---

## 핵심 설계 결정 (Plan 단계)

1. **신규 테이블 2개**: `stock_fundamentals`(지표 스냅샷)·`screener_presets`(프리셋). 마이그 0016, down_rev=0015.
2. **NULL 지표 자동 제외** — 특정 지표 조건이 걸린 종목이 해당 지표 NULL이면 그 조건에서 제외.
3. **다중 조건 AND 만 지원** — OR/복합 논리 제외.
4. **신규 라우터 prefix = `/screener`** — 인증 없이 실행 가능, 프리셋만 인증 필요.
5. **프리셋 최대 5개 per user** — 초과 시 HTTP 409.
