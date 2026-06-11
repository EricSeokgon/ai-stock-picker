# SPEC-STOCK-012 진행 상황 (Progress)

- **SPEC ID**: SPEC-STOCK-012
- **제목**: 백테스트 엔진 완성 (Phase 13)
- **Status**: IN_PROGRESS
- **Phase**: Phase 13
- **생성일**: 2026-06-11
- **작성자**: ircp

---

## 단계별 상태

| 단계 | 상태 | 비고 |
| --- | --- | --- |
| Plan (기획) | 완료 | spec/tasks/acceptance/progress 4파일 작성 |
| Run (구현) | 진행 중 | M1~M4 + M6(BE) 완료, M5(FE) 대기 |
| Sync (문서화) | 대기 | README·CHANGELOG 갱신 |

## 마일스톤 진행

- [x] M1. 데이터 계층 — universe_size·top_n 컬럼, status `error`→`failed` 통일 (T-001~003)
  - `0013_backtest_params.py` 마이그레이션 생성
  - `BacktestRun` 모델에 `universe_size`, `top_n` 컬럼 추가
  - runner.py `"error"` → `"failed"` 통일
- [x] M2. 백엔드 스키마·라우터 계약 정합 (T-004~008)
  - `BacktestRunRequest`에 `universe_size`, `top_n` 필드 + 검증자 추가
  - `POST /run` → `BacktestStartResponse({run_id, message})` HTTP 202 반환
  - `BacktestRunDetail`에 `total_return`, `win_rate` 필드 추가
  - `GET /results` → flat array `[DailyResultTimeSeries]` 반환
  - `start_backtest`에서 `universe_size`, `top_n` DB 저장 및 runner 전달
- [x] M3. 메트릭 모듈 확장 — total_return·win_rate·가치 시계열 (T-009~011)
  - `calculate_total_return()` 추가
  - `calculate_win_rate()` 추가
  - `build_portfolio_value_series()` 추가
- [x] M4. 벤치마크 수집·정규화 — KOSPI/KOSDAQ (T-012~015)
  - `_fetch_benchmark_data()` 추가 (KS11, 실패 시 None 반환)
  - `_normalize_series()` 추가
  - 벤치마크 실패 시 run 중단 없이 `benchmark_value=None` 처리
  - `_TOP_N` 하드코딩 제거, `top_n`/`universe_size` 파라미터 사용
- [ ] M5. 프론트엔드 정합 — api 타입·차트·승률 표시 (T-016~019)
- [x] M6(BE). 테스트 — 메트릭 유닛 + runner + 라우터 통합 (T-020~022)
  - `test_backtest_metrics.py`: total_return·win_rate·portfolio_series 신규 케이스 29개
  - `test_backtest_runner.py`: 신규 파일 (상태전환·벤치마크실패·universe 파라미터)
  - `test_backtest_router.py`: POST 202 구조, universe_size/top_n 검증, flat array 결과
  - **전체 테스트: 551/556 통과** (5개 사전 존재 collector HTTP 테스트 실패, 이번 구현 무관)

## 핵심 리스크·메모

- **계약 드리프트가 핵심 문제**: 기존 프론트(`api/backtest.ts`)와 백엔드(`schemas.py`)가 응답 형태·status enum·결과 시계열에서 불일치. 완성의 본질은 신규 기능보다 이 정합화.
- 기존 status `error` → `failed` 통일 시 기존 DB 데이터 영향 검토 필요(M1 T-003).
- 벤치마크 심볼 `KS11`/`KQ11`의 FinanceDataReader 지원 여부는 구현 초기에 실데이터로 확인 권장(미지원 시 폴백 경로 REQ-BT-BENCH-004 활성).
- FinanceDataReader 동기 호출은 반드시 `run_in_executor` 래핑(이벤트 루프 블로킹 방지, 기존 러너 패턴 유지).

## 변경 이력

- 2026-06-11: SPEC 초안 작성 (v0.1.0), Status=PLANNING.
