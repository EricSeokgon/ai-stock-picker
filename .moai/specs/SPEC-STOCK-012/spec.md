---
id: SPEC-STOCK-012
version: 0.1.0
status: planning
created: 2026-06-11
updated: 2026-06-11
author: ircp
priority: high
issue_number: null
---

# SPEC-STOCK-012: 백테스트 엔진 완성 (Phase 13)

## HISTORY

- 2026-06-11 (v0.1.0): 초안 작성. Phase 1~12 완료 위에 미완성 백테스트 시스템을 완성하는 SPEC. 백엔드 모듈(backtest/router.py, runner.py, metrics.py, schemas.py)·프론트(pages/Backtest.tsx, api/backtest.ts)·DB 테이블(backtest_runs, backtest_daily_results)이 이미 존재하나 프론트엔드/백엔드 계약이 불일치하고 벤치마크 비교·포트폴리오 가치 시계열·총수익률·승률 지표가 미구현 상태. 본 SPEC이 이를 완성.

---

## 1. 개요 (Overview)

### 1.1 목적

ai-stock-picker의 백테스트 시스템을 완성하여, 사용자가 과거 기간을 지정해 추천 전략을 백테스트하고 그 성과를 KOSPI/KOSDAQ 벤치마크와 비교하며, 누적 수익률·최대 낙폭·샤프 비율·승률 지표를 프론트엔드 대시보드에서 확인할 수 있게 한다.

### 1.2 배경 — 현재 코드베이스 상태 (비자명 사실)

본 SPEC은 신규 기능이 아니라 **미완성 기능의 완성**이다. 다음 자산이 이미 존재한다.

- DB: `backtest_runs`(id, user_id, strategy, start_date, end_date, status, created_at, completed_at)·`backtest_daily_results`(id, run_id, trade_date, krx_code, signal, price, return_pct) 테이블 + 마이그레이션 `0005_backtest.py`.
- 백엔드: `backtest/router.py`(POST /backtest/run, GET /runs, GET /runs/{id}, GET /runs/{id}/results), `runner.py`(momentum·volume 전략 + FinanceDataReader), `metrics.py`(calculate_cagr·calculate_max_drawdown·calculate_sharpe_ratio), `schemas.py`. 라우터는 `api/main.py`에 이미 `include_router` 됨.
- 프론트: `pages/Backtest.tsx`(실행 폼·이력·상세 차트), `api/backtest.ts`, `App.tsx`에 `/backtest` 보호 라우트.

### 1.3 핵심 문제 — 프론트엔드/백엔드 계약 불일치 (완성이 필요한 이유)

| 항목 | 백엔드 현재 | 프론트 현재 기대 | 완성 방향 |
| --- | --- | --- | --- |
| POST /run 응답 | `BacktestRunResponse`(id, user_id, ...) | `{run_id, message}` | 백엔드를 `{run_id, message}` 형태로 통일 |
| 요청 파라미터 | strategy, start_date, end_date | + universe_size, top_n | 백엔드 스키마·테이블·러너에 universe_size·top_n 반영 |
| 상태 enum | pending/running/done/**error** | pending/running/done/**failed** | `error` → `failed`로 통일 |
| 일별 결과 응답 | `PaginatedDailyResults`(거래 단위: trade_date, krx_code, signal, price, return_pct) | flat array(date, portfolio_value, benchmark_value, daily_return) | 일자 단위 시계열(포트폴리오·벤치마크 가치) 신규 산출 |
| 벤치마크 | 없음 | benchmark_value 차트 렌더 | KOSPI/KOSDAQ 지수 데이터 수집·정규화 시계열 추가 |
| 지표 | cagr, max_drawdown, sharpe | + total_return, win_rate | total_return·win_rate 신규 계산 |

### 1.4 사용자 가치

- WHO: ai-stock-picker 로그인 사용자(투자 의사결정 전 전략 검증을 원함).
- WHAT: 기간·전략을 골라 백테스트를 돌리고 벤치마크 대비 성과를 시각적으로 확인.
- WHY: 추천 전략이 단순 보유(벤치마크) 대비 우월한지 과거 데이터로 검증.

---

## 2. EARS 요구사항 (Requirements)

### 2.1 백테스트 실행 — REQ-BT-RUN-*

- **REQ-BT-RUN-001** (EVENT-DRIVEN): WHEN 인증된 사용자가 `POST /backtest/run`에 strategy·start_date·end_date를 제출하면, the backtest system SHALL `backtest_runs` 레코드를 status `pending`으로 생성하고 HTTP 202와 `{run_id, message}` 형태의 응답을 반환한다.
- **REQ-BT-RUN-002** (EVENT-DRIVEN): WHEN 백테스트 작업이 비동기로 시작되면, the backtest system SHALL 해당 run의 status를 `running`으로 갱신한다.
- **REQ-BT-RUN-003** (EVENT-DRIVEN): WHEN 백테스트 작업이 정상 종료되면, the backtest system SHALL status를 `done`으로, `completed_at`을 현재 시각으로 갱신한다.
- **REQ-BT-RUN-004** (UNWANTED): IF 백테스트 실행 중 예외가 발생하면, THEN the backtest system SHALL status를 `failed`로 갱신하고 예외를 로깅한다. (기존 `error` 문자열을 `failed`로 통일)
- **REQ-BT-RUN-005** (UBIQUITOUS): The backtest system SHALL `strategy`가 `momentum` 또는 `volume` 중 하나임을 검증하고, 그 외 값은 HTTP 422로 거부한다.
- **REQ-BT-RUN-006** (UNWANTED): IF `end_date`가 `start_date` 이전이거나 같으면, THEN the backtest system SHALL HTTP 422로 요청을 거부한다.

### 2.2 실행 파라미터 — REQ-BT-PARAM-*

- **REQ-BT-PARAM-001** (UBIQUITOUS): The backtest request schema SHALL 선택 파라미터 `universe_size`(정수, 기본값 정의)와 `top_n`(정수, 기본값 정의)을 수용한다.
- **REQ-BT-PARAM-002** (UBIQUITOUS): The `backtest_runs` 테이블 SHALL `universe_size`와 `top_n` 컬럼(nullable, 정수)을 보유하여 실행 시점 파라미터를 영속화한다.
- **REQ-BT-PARAM-003** (EVENT-DRIVEN): WHEN 백테스트 러너가 종목 유니버스를 구성하면, the backtest runner SHALL 요청된 `universe_size`만큼의 종목을 선정하고 전략 시그널 상위 `top_n` 종목으로 포트폴리오를 구성한다.
- **REQ-BT-PARAM-004** (UNWANTED): IF `universe_size` 또는 `top_n`이 1 미만이면, THEN the backtest system SHALL HTTP 422로 요청을 거부한다.

### 2.3 성과 지표 — REQ-BT-METRIC-*

- **REQ-BT-METRIC-001** (UBIQUITOUS): The backtest metrics module SHALL 누적 수익률(total_return), 최대 낙폭(max_drawdown), 샤프 비율(sharpe_ratio), 승률(win_rate), CAGR을 산출한다.
- **REQ-BT-METRIC-002** (UBIQUITOUS): The backtest system SHALL win_rate를 (수익이 양수인 거래일 수 / 전체 유효 거래일 수)로 계산하고 0.0~1.0 범위의 값으로 반환한다.
- **REQ-BT-METRIC-003** (UBIQUITOUS): The backtest system SHALL total_return을 포트폴리오 최종 가치 대비 초기 가치의 비율에서 1을 뺀 값으로 계산한다.
- **REQ-BT-METRIC-004** (EVENT-DRIVEN): WHEN 사용자가 완료된 run의 상세를 조회하면, the backtest system SHALL cagr·max_drawdown·sharpe_ratio·total_return·win_rate·total_trades를 응답에 포함한다.
- **REQ-BT-METRIC-005** (UNWANTED): IF 거래일 데이터가 비어 있거나 1건 이하이면, THEN the backtest metrics module SHALL 0으로 나누는 오류 없이 안전한 기본값(0.0)을 반환한다.

### 2.4 벤치마크 비교 — REQ-BT-BENCH-*

- **REQ-BT-BENCH-001** (UBIQUITOUS): The backtest runner SHALL 동일 기간의 KOSPI(`KS11`) 및 KOSDAQ(`KQ11`) 지수 데이터를 FinanceDataReader로 수집한다.
- **REQ-BT-BENCH-002** (UBIQUITOUS): The backtest system SHALL 벤치마크 지수와 전략 포트폴리오를 모두 시작값 동일 기준(정규화)으로 변환한 가치 시계열로 산출한다.
- **REQ-BT-BENCH-003** (EVENT-DRIVEN): WHEN 일별 결과 시계열이 산출되면, the backtest system SHALL 각 거래일에 대해 `date`·`portfolio_value`·`benchmark_value`·`daily_return`을 포함하는 레코드를 반환한다.
- **REQ-BT-BENCH-004** (UNWANTED): IF 벤치마크 지수 데이터 수집에 실패하면, THEN the backtest system SHALL 백테스트 자체는 계속 진행하되 `benchmark_value`를 null로 채우고 경고를 로깅한다.

### 2.5 결과 조회 API — REQ-BT-API-*

- **REQ-BT-API-001** (EVENT-DRIVEN): WHEN 사용자가 `GET /backtest/runs`를 호출하면, the backtest system SHALL 해당 사용자의 run 목록을 최신순으로 반환한다.
- **REQ-BT-API-002** (EVENT-DRIVEN): WHEN 사용자가 `GET /backtest/runs/{run_id}`를 호출하면, the backtest system SHALL run 메타데이터와 성과 지표를 포함한 상세를 반환한다.
- **REQ-BT-API-003** (EVENT-DRIVEN): WHEN 사용자가 `GET /backtest/runs/{run_id}/results`를 호출하면, the backtest system SHALL 일자 단위 가치 시계열(date·portfolio_value·benchmark_value·daily_return)을 반환한다.
- **REQ-BT-API-004** (UNWANTED): IF 사용자가 자신이 소유하지 않은 run_id에 접근하면, THEN the backtest system SHALL HTTP 404를 반환한다.
- **REQ-BT-API-005** (UNWANTED): IF 미인증 요청이 백테스트 엔드포인트에 접근하면, THEN the backtest system SHALL HTTP 401을 반환한다.

### 2.6 프론트엔드 표시 — REQ-BT-FE-*

- **REQ-BT-FE-001** (UBIQUITOUS): The frontend backtest page SHALL 전략·기간·universe_size·top_n 입력 폼을 제공하고 실행을 제출한다.
- **REQ-BT-FE-002** (EVENT-DRIVEN): WHEN 실행 이력 항목을 펼치면, the frontend SHALL CAGR·최대 낙폭·샤프 비율·총 수익률·승률 지표를 표시한다.
- **REQ-BT-FE-003** (EVENT-DRIVEN): WHEN 완료된 run의 결과가 로드되면, the frontend SHALL 전략 포트폴리오 가치선과 벤치마크 가치선을 동일 차트에 렌더한다.
- **REQ-BT-FE-004** (STATE-DRIVEN): WHILE run의 status가 `pending` 또는 `running`이면, the frontend SHALL 상태 배지를 표시하고 차트 대신 진행 안내 문구를 표시한다.
- **REQ-BT-FE-005** (UBIQUITOUS): The frontend api client(`api/backtest.ts`) SHALL 백엔드 응답 스키마(`{run_id, message}`·status enum·결과 시계열)와 정확히 일치하는 타입을 사용한다.

### 2.7 비기능 요구사항 — REQ-BT-NFR-*

- **REQ-BT-NFR-001** (UBIQUITOUS): The backtest runner SHALL FinanceDataReader 동기 호출을 `run_in_executor`로 래핑하여 asyncio 이벤트 루프를 블로킹하지 않는다.
- **REQ-BT-NFR-002** (UBIQUITOUS): The backtest backend test suite SHALL pytest 커버리지 85% 이상을 유지한다(프로젝트 `fail_under=85` 준수).
- **REQ-BT-NFR-003** (UBIQUITOUS): The backtest code SHALL ruff lint를 통과하고 Python 3.11 타깃 문법을 준수한다.

---

## 3. Exclusions (What NOT to Build)

- **실거래·주문 실행·실시간 데이터**: 영구 제외(규제·책임 리스크). 백테스트는 과거 데이터 기반 시뮬레이션만 수행한다.
- **거래 비용·슬리피지·세금 모델링**: 본 SPEC 범위 밖(향후 별도 SPEC). 단순 종가 기반 수익률만 사용.
- **신규 전략 추가**: momentum·volume 외 전략(예: mean-reversion, 추천엔진 스코어 기반 전략) 추가는 범위 밖.
- **백테스트 결과 캐싱/Redis**: 결과는 DB에 영속되며 본 SPEC에서 Redis 캐시는 도입하지 않는다.
- **포트폴리오 리밸런싱 정교화**: 일별 비중 최적화·켈리 베팅 등은 범위 밖. 균등 비중 단순 모델 사용.
- **CSV/PDF 내보내기·결과 공유**: 범위 밖.
- **다중 벤치마크 사용자 선택 UI**: KOSPI·KOSDAQ 고정. 사용자 지정 벤치마크 선택은 범위 밖.

---

## 4. 의존성·전제 (Dependencies & Assumptions)

- FinanceDataReader가 `KS11`(KOSPI)·`KQ11`(KOSDAQ) 지수 심볼을 지원함을 전제(기존 종목 가격 조회에 이미 FinanceDataReader 사용 중).
- 인증은 기존 `auth.dependencies.get_current_user`·`get_db_session` 재사용.
- DB는 PostgreSQL + 동기 세션(러너는 `create_engine` 동기 엔진 사용, 기존 패턴 유지).
- 마이그레이션은 누적: 현재 최신 `0012`. 본 SPEC은 `0013`(backtest_runs에 universe_size·top_n 컬럼 추가)을 신규 작성.
- 기존 status 값 `error`를 `failed`로 변경 시 기존 데이터 마이그레이션 또는 코드 일원화 필요(M1에서 결정).
