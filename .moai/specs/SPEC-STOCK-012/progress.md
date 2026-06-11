# SPEC-STOCK-012 진행 상황 (Progress)

- **SPEC ID**: SPEC-STOCK-012
- **제목**: 백테스트 엔진 완성 (Phase 13)
- **Status**: PLANNING
- **Phase**: Phase 13
- **생성일**: 2026-06-11
- **작성자**: ircp

---

## 단계별 상태

| 단계 | 상태 | 비고 |
| --- | --- | --- |
| Plan (기획) | 진행 중 | spec/tasks/acceptance/progress 4파일 작성 |
| Run (구현) | 대기 | M1~M6 (expert-backend·expert-frontend) |
| Sync (문서화) | 대기 | README·CHANGELOG 갱신 |

## 마일스톤 진행

- [ ] M1. 데이터 계층 — universe_size·top_n 컬럼, status `error`→`failed` 통일 (T-001~003)
- [ ] M2. 백엔드 스키마·라우터 계약 정합 (T-004~008)
- [ ] M3. 메트릭 모듈 확장 — total_return·win_rate·가치 시계열 (T-009~011)
- [ ] M4. 벤치마크 수집·정규화 — KOSPI/KOSDAQ (T-012~015)
- [ ] M5. 프론트엔드 정합 — api 타입·차트·승률 표시 (T-016~019)
- [ ] M6. 테스트·품질 — 커버리지 85%·ruff·tsc·vitest (T-020~024)

## 핵심 리스크·메모

- **계약 드리프트가 핵심 문제**: 기존 프론트(`api/backtest.ts`)와 백엔드(`schemas.py`)가 응답 형태·status enum·결과 시계열에서 불일치. 완성의 본질은 신규 기능보다 이 정합화.
- 기존 status `error` → `failed` 통일 시 기존 DB 데이터 영향 검토 필요(M1 T-003).
- 벤치마크 심볼 `KS11`/`KQ11`의 FinanceDataReader 지원 여부는 구현 초기에 실데이터로 확인 권장(미지원 시 폴백 경로 REQ-BT-BENCH-004 활성).
- FinanceDataReader 동기 호출은 반드시 `run_in_executor` 래핑(이벤트 루프 블로킹 방지, 기존 러너 패턴 유지).

## 변경 이력

- 2026-06-11: SPEC 초안 작성 (v0.1.0), Status=PLANNING.
