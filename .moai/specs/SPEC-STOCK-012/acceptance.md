# SPEC-STOCK-012 인수 기준 (Acceptance Criteria)

Given-When-Then 형식. 모든 기준은 테스트 가능해야 한다. 인증이 필요한 엔드포인트는 유효 Bearer 토큰 보유 사용자를 전제로 한다.

---

## AC-1: 백테스트 실행 제출 — 응답 형태

- **Given** 인증된 사용자와 유효한 요청 본문(`strategy="momentum"`, `start_date="2023-01-01"`, `end_date="2024-01-01"`)
- **When** `POST /backtest/run`을 호출하면
- **Then** HTTP 202가 반환되고, 응답 본문은 `run_id`(정수)와 `message`(문자열) 필드를 가지며, `backtest_runs`에 status `pending`인 레코드가 생성된다.
- 검증: REQ-BT-RUN-001

## AC-2: 실행 파라미터 영속화

- **Given** 인증된 사용자가 `universe_size=100`, `top_n=10`을 포함해 실행을 제출함
- **When** 해당 run을 `GET /backtest/runs/{run_id}`로 조회하면
- **Then** 응답에 `universe_size=100`, `top_n=10`이 포함되고 DB `backtest_runs` 레코드에도 동일 값이 저장되어 있다.
- 검증: REQ-BT-PARAM-001, REQ-BT-PARAM-002, REQ-BT-PARAM-003

## AC-3: 잘못된 전략 거부

- **Given** 인증된 사용자
- **When** `strategy="invalid"`로 `POST /backtest/run`을 호출하면
- **Then** HTTP 422가 반환되고 run 레코드는 생성되지 않는다.
- 검증: REQ-BT-RUN-005

## AC-4: 잘못된 기간 거부

- **Given** 인증된 사용자
- **When** `end_date`가 `start_date`보다 이전이거나 같은 요청을 제출하면
- **Then** HTTP 422가 반환된다.
- 검증: REQ-BT-RUN-006

## AC-5: 잘못된 파라미터 거부

- **Given** 인증된 사용자
- **When** `universe_size=0` 또는 `top_n=0`으로 실행을 제출하면
- **Then** HTTP 422가 반환된다.
- 검증: REQ-BT-PARAM-004

## AC-6: 상태 전이 — done

- **Given** 가격 데이터가 정상 수집되는 백테스트 작업
- **When** 비동기 실행이 정상 완료되면
- **Then** run의 status는 `running`을 거쳐 `done`이 되고 `completed_at`이 설정된다.
- 검증: REQ-BT-RUN-002, REQ-BT-RUN-003

## AC-7: 상태 전이 — failed (error 아님)

- **Given** 실행 중 예외가 발생하는 백테스트 작업
- **When** 러너가 예외를 만나면
- **Then** run의 status는 `failed`로 갱신된다(문자열 `error`가 아니라 `failed`). 예외는 로깅된다.
- 검증: REQ-BT-RUN-004

## AC-8: 승률 계산

- **Given** 일별 수익률 시퀀스(예: `[0.01, -0.02, 0.03, 0.0, 0.01]`)
- **When** `calculate_win_rate`를 호출하면
- **Then** (양수 수익일 수 / 전체 유효일 수) = 3/5 = 0.6 이 0.0~1.0 범위로 반환된다.
- 검증: REQ-BT-METRIC-001, REQ-BT-METRIC-002

## AC-9: 총수익률 계산

- **Given** 시작값 1.0인 누적 가치 시계열(예: 마지막 값 1.25)
- **When** `calculate_total_return`을 호출하면
- **Then** 0.25(=25%)가 반환된다.
- 검증: REQ-BT-METRIC-003

## AC-10: 빈/단일 데이터 안전성

- **Given** 빈 리스트 또는 1건짜리 일별 수익률
- **When** win_rate·total_return·sharpe·cagr·max_drawdown을 호출하면
- **Then** 0으로 나누기 예외 없이 0.0을 반환한다.
- 검증: REQ-BT-METRIC-005

## AC-11: 상세 지표 응답

- **Given** status `done`인 run
- **When** `GET /backtest/runs/{run_id}`를 호출하면
- **Then** 응답에 `cagr`, `max_drawdown`, `sharpe_ratio`, `total_return`, `win_rate`, `total_trades`가 모두 포함된다.
- 검증: REQ-BT-METRIC-004

## AC-12: 결과 시계열 형태

- **Given** status `done`인 run
- **When** `GET /backtest/runs/{run_id}/results`를 호출하면
- **Then** 응답은 일자 단위 객체의 배열이며 각 객체는 `date`, `portfolio_value`, `benchmark_value`, `daily_return` 키를 가진다.
- 검증: REQ-BT-API-003, REQ-BT-BENCH-003

## AC-13: 벤치마크 정규화

- **Given** 동일 기간의 전략 포트폴리오와 KOSPI/KOSDAQ 지수 데이터
- **When** 결과 시계열을 산출하면
- **Then** `portfolio_value`와 `benchmark_value`는 동일 시작 기준(정규화)으로 비교 가능한 가치 시계열이다.
- 검증: REQ-BT-BENCH-001, REQ-BT-BENCH-002

## AC-14: 벤치마크 수집 실패 폴백

- **Given** 벤치마크 지수 데이터 수집이 실패하는 상황(모킹)
- **When** 백테스트를 실행하면
- **Then** 백테스트는 status `done`으로 완료되고 결과 시계열의 `benchmark_value`는 null이며 경고가 로깅된다.
- 검증: REQ-BT-BENCH-004

## AC-15: 소유권 격리

- **Given** 사용자 A가 생성한 run_id
- **When** 사용자 B가 `GET /backtest/runs/{run_id}` 또는 `.../results`를 호출하면
- **Then** HTTP 404가 반환된다.
- 검증: REQ-BT-API-004

## AC-16: 미인증 거부

- **Given** Bearer 토큰 없는 요청
- **When** 임의의 `/backtest/*` 엔드포인트를 호출하면
- **Then** HTTP 401이 반환된다.
- 검증: REQ-BT-API-005

## AC-17: 프론트엔드 지표 표시

- **Given** status `done`인 run 이력 항목
- **When** 사용자가 항목을 펼치면
- **Then** CAGR·최대 낙폭·샤프 비율·총 수익률·승률이 화면에 표시된다.
- 검증: REQ-BT-FE-002

## AC-18: 프론트엔드 벤치마크 차트

- **Given** status `done`인 run의 결과 시계열
- **When** 상세 패널이 렌더되면
- **Then** 전략 포트폴리오 가치선과 벤치마크 가치선이 동일 차트에 표시된다(벤치마크 null인 경우 해당 선은 비표시).
- 검증: REQ-BT-FE-003, REQ-BT-BENCH-004

## AC-19: 프론트엔드 진행 상태

- **Given** status `pending` 또는 `running`인 run
- **When** 사용자가 항목을 펼치면
- **Then** 상태 배지가 표시되고 차트 대신 진행 안내 문구가 표시된다.
- 검증: REQ-BT-FE-004

## AC-20: 품질 게이트

- **Given** 본 SPEC의 모든 코드 변경
- **When** `ruff check`, `tsc`, `vitest`, `pytest --cov-fail-under=85`를 실행하면
- **Then** 모두 통과한다(백엔드 커버리지 85% 이상).
- 검증: REQ-BT-NFR-001, REQ-BT-NFR-002, REQ-BT-NFR-003

---

## Definition of Done

- [ ] AC-1 ~ AC-20 전부 통과
- [ ] 프론트엔드/백엔드 계약 불일치(응답 형태·status enum·파라미터·결과 시계열) 완전 해소
- [ ] 마이그레이션 0013 작성·적용 가능 확인
- [ ] 벤치마크(KOSPI·KOSDAQ) 비교 차트 동작
- [ ] total_return·win_rate 지표 백엔드 산출·프론트 표시
- [ ] 실거래/주문/실시간 데이터 미포함(Exclusions 준수)
