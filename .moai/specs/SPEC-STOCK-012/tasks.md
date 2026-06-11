# SPEC-STOCK-012 구현 작업 (Tasks)

Phase 13 — 백테스트 엔진 완성. 핵심은 **프론트엔드/백엔드 계약 일치**와 **벤치마크 비교·신규 지표(총수익률·승률)** 구현이다.

작업 식별자: T-NNN. 담당: BE = expert-backend, FE = expert-frontend, DB = expert-backend(마이그레이션).

우선순위: P-High(계약 정합성·핵심 지표), P-Medium(벤치마크·프론트), P-Low(테스트 보강).

---

## M1. 데이터 계층 — 파라미터 영속화 (DB, P-High)

- **T-001** (DB): 마이그레이션 `0013_backtest_params.py` 작성 — `backtest_runs`에 `universe_size`(Integer, nullable)·`top_n`(Integer, nullable) 컬럼 추가. (REQ-BT-PARAM-002)
- **T-002** (BE): `db/models.py`의 `BacktestRun`에 `universe_size`·`top_n` Mapped 컬럼 추가. (REQ-BT-PARAM-002)
- **T-003** (BE): status 값 통일 결정 — 코드 전반의 `"error"` → `"failed"`로 변경(runner.py `_update_status` 호출부, 관련 테스트). 기존 데이터 영향 검토. (REQ-BT-RUN-004)

## M2. 백엔드 스키마·라우터 계약 정합 (BE, P-High)

- **T-004** (BE): `backtest/schemas.py` — `BacktestRunRequest`에 `universe_size: int | None`·`top_n: int | None` 추가 + 1 미만 거부 검증. (REQ-BT-PARAM-001, REQ-BT-PARAM-004)
- **T-005** (BE): `POST /backtest/run` 응답을 `{run_id, message}` 형태(`BacktestRunResponse` 재정의 또는 신규 스키마)로 변경. (REQ-BT-RUN-001)
- **T-006** (BE): `BacktestRunDetail` 스키마에 `total_return`·`win_rate` 필드 추가, `BacktestRunResponse`(목록용)에 `universe_size`·`top_n` 노출. (REQ-BT-METRIC-004)
- **T-007** (BE): `GET /runs/{run_id}/results` 응답을 일자 단위 시계열(`date`·`portfolio_value`·`benchmark_value`·`daily_return`) flat array로 변경. 기존 `PaginatedDailyResults`(거래 단위) 대체. (REQ-BT-API-003, REQ-BT-BENCH-003)
- **T-008** (BE): `start_backtest`에서 universe_size·top_n을 run 레코드에 저장하고 러너에 전달. (REQ-BT-PARAM-003)

## M3. 메트릭 모듈 확장 (BE, P-High)

- **T-009** (BE): `backtest/metrics.py`에 `calculate_total_return(cumulative)` 추가. (REQ-BT-METRIC-003)
- **T-010** (BE): `backtest/metrics.py`에 `calculate_win_rate(daily_returns)` 추가 — 양수 수익일 비율, 빈 입력 시 0.0. (REQ-BT-METRIC-002, REQ-BT-METRIC-005)
- **T-011** (BE): 일별 결과 → 포트폴리오 가치 시계열 빌더 함수 작성(균등 비중 top_n 포트폴리오 일별 가치). 기존 `_build_cumulative` 확장. (REQ-BT-METRIC-003)

## M4. 벤치마크 수집·정규화 (BE, P-Medium)

- **T-012** (BE): `runner.py`에 KOSPI(`KS11`)·KOSDAQ(`KQ11`) 지수 수집 함수 추가(FinanceDataReader, executor 래핑). (REQ-BT-BENCH-001, REQ-BT-NFR-001)
- **T-013** (BE): 벤치마크·포트폴리오를 시작값 1.0 기준 정규화 시계열로 변환하는 로직 추가. (REQ-BT-BENCH-002)
- **T-014** (BE): 벤치마크 수집 실패 시 `benchmark_value=null` 폴백 + 경고 로깅. (REQ-BT-BENCH-004)
- **T-015** (BE): 러너가 universe_size만큼 유니버스 구성, 전략 시그널 상위 top_n 선정하도록 `_get_krx_universe`·전략 함수 일반화(하드코딩 `_TOP_N=5`·10종목 제거). (REQ-BT-PARAM-003)

## M5. 프론트엔드 정합 (FE, P-Medium)

- **T-016** (FE): `api/backtest.ts` — `BacktestRunResponse`(`{run_id, message}`)·`BacktestStatus`(`failed` 포함)·`BacktestRun`(universe_size·top_n·win_rate 추가)·`BacktestDailyResult`(date·portfolio_value·benchmark_value·daily_return) 타입을 백엔드 응답과 정확히 일치시킴. (REQ-BT-FE-005)
- **T-017** (FE): `pages/Backtest.tsx` 상세 패널에 승률(win_rate) 지표 추가, 총 수익률(total_return) 표시 유지·확인. (REQ-BT-FE-002)
- **T-018** (FE): 결과 차트가 전략 포트폴리오선·벤치마크선을 정규화 가치 기준으로 렌더하도록 확인·보정(벤치마크 null 처리 포함). (REQ-BT-FE-003, REQ-BT-BENCH-004)
- **T-019** (FE): pending/running 상태 시 진행 안내 표시 동작 확인. (REQ-BT-FE-004)

## M6. 테스트·품질 (BE+FE, P-Low)

- **T-020** (BE): metrics 단위 테스트 — total_return·win_rate·정규화 시계열, 빈/단일 입력 엣지 케이스. (REQ-BT-METRIC-005, REQ-BT-NFR-002)
- **T-021** (BE): 라우터 통합 테스트 — POST /run 응답 형태, 소유권 404, 미인증 401, 422 검증(전략·날짜·파라미터). (REQ-BT-API-004, REQ-BT-API-005, REQ-BT-RUN-005·006, REQ-BT-PARAM-004)
- **T-022** (BE): runner 테스트 — 벤치마크 수집 실패 폴백, 전략 실행 후 status `done`/`failed` 전이(FinanceDataReader는 모킹). (REQ-BT-RUN-003·004, REQ-BT-BENCH-004)
- **T-023** (FE): `vitest` — api 타입·차트 렌더 스모크 테스트, 상태 배지 매핑.
- **T-024** (BE+FE): ruff·tsc·vitest·pytest(`--cov-fail-under=85`) 전체 통과 확인. (REQ-BT-NFR-002, REQ-BT-NFR-003)

---

## 의존 순서

M1 → M2 → (M3 ∥ M4) → M5 → M6. M1(컬럼·status 통일)이 선행되어야 M2 스키마·러너가 파라미터를 다룰 수 있다. M3·M4는 독립 병렬 가능. M5는 백엔드 계약 확정(M2·M3·M4) 후 진행. M6은 마지막.
