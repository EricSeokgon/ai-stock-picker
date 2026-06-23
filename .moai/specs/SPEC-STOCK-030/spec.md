---
id: "SPEC-STOCK-030"
version: "0.3.0"
status: "draft"
created_at: "2026-06-23"
updated_at: "2026-06-23"
author: "ircp"
priority: "medium"
issue_number: 0
labels: ["portfolio", "performance", "backend", "frontend"]
---

# SPEC-STOCK-030: 포트폴리오 기간별 성과 요약 (Portfolio Period Performance Summary)

> Roadmap Phase 3 "포트폴리오 AI 최적화" 계열 SPEC. SPEC-029(포트폴리오 백테스팅)가 임의 기간 시뮬레이션을 제공하는 것과 달리, 본 SPEC은 사전 정의된 5개 표준 기간(YTD/1M/3M/6M/1Y)의 성과 요약을 한 번에 제공한다.

## HISTORY

| 버전 | 날짜 | 변경 내용 |
|------|------|-----------|
| 0.1.0 | 2026-06-23 | 최초 작성 |
| 0.2.0 | 2026-06-23 | plan-auditor v1 지적사항 반영: frontmatter 수정(created_at·labels), REQ-PS-003 HOW 제거, REQ-PS-004 구현 세부사항 이동, REQ-PS-010 NFR-001 통합, Delta Marker 명확화, 프라이빗 함수 공유 계획 추가 |
| 0.3.0 | 2026-06-23 | plan-auditor v2 지적사항 반영: §5.3 소유권 불일치 HTTP 상태 코드를 403→404로 수정(코드베이스 관례 일관성) |

> **REQ 접두사 설계 원칙**: 본 SPEC은 `REQ-PS-*`(Performance Summary) 접두사를 사용한다. SPEC-029(포트폴리오 백테스트)가 `REQ-PBT-*`를, SPEC-027(리스크 분석)이 `REQ-RISK-*`를 점유하므로 충돌을 회피한다.

> **번호 체계**: REQ-PS-001~010 연속 번호를 사용한다.

---

## 1. 개요 (Overview)

### 1.1 기능 설명

사용자가 보유한 포트폴리오(종목 + 비중)에 대해 **사전 정의된 5개 표준 기간**(YTD, 1M, 3M, 6M, 1Y)의 성과를 한 번의 요청으로 일괄 계산하여 요약 카드 형태로 제공한다. 각 기간별로 **총수익률(%)·연환산수익률(%)·최대낙폭(MDD %)**을 산출한다. 모든 가치는 KRW 기준으로 통일하여 계산하며, KRX(원화) 종목과 NYSE/NASDAQ(달러→원화 환산) 종목을 혼합 지원한다.

### 1.2 동기 (Motivation)

현재 포트폴리오 도메인은 다음 기능을 제공한다.

- **SPEC-029(포트폴리오 백테스트)**: 사용자가 시작일·종료일을 직접 입력하여 임의 기간의 일별/누적 수익률을 시뮬레이션.
- **SPEC-027(리스크 분석)**: 상관관계·변동성 등 통계적 리스크 프로필.

그러나 사용자가 "내 포트폴리오가 올해(YTD), 최근 1개월·3개월·6개월·1년 동안 각각 얼마나 수익을 냈는가"를 **한눈에 비교**할 표준 대시보드가 없다. 백테스트는 매번 날짜를 입력해야 하고 단일 기간만 보여준다. 본 SPEC은 표준 기간 5개를 한 번에 계산하여 요약 카드로 제시함으로써 성과 추적성을 높인다.

### 1.3 목표 (Goals)

- 5개 표준 기간(YTD/1M/3M/6M/1Y)의 성과를 단일 엔드포인트로 일괄 제공한다.
- 각 기간별 총수익률·연환산수익률·MDD를 numpy 기반으로 산출한다.
- Redis 캐싱으로 동일 일자 반복 요청 시 FDR 호출을 회피한다.
- KRX + 해외(NYSE/NASDAQ) 혼합 포트폴리오를 KRW 통일 기준으로 지원한다.
- 프론트엔드 5개 기간 카드 패널로 시각화한다.

### 1.4 기술 스택 (확정·재사용)

FastAPI + PostgreSQL(asyncpg) + Redis + React + Recharts + FinanceDataReader(FDR) + numpy. 신규 라이브러리는 도입하지 않는다(`finance-datareader>=0.9`·`numpy>=1.26`는 pyproject.toml에 이미 존재). 통계 계산은 numpy + 표준 라이브러리(math)만 사용하며 **scipy는 사용하지 않는다**.

---

## 2. 범위 (Scope)

### 2.1 포함 (In Scope)

- 신규 서비스 `portfolio/performance_summary.py`(성과 요약 계산, risk_analysis.py·backtest.py 형제).
- 신규 엔드포인트 `GET /portfolios/{portfolio_id}/performance-summary?refresh={bool}`(인증·소유권).
- `PerformanceSummaryResponse`·`PeriodPerformance` Pydantic 스키마 추가(`portfolio/schemas.py`).
- 5개 기간(YTD/1M/3M/6M/1Y) 시작일 산출 로직.
- FDR 기간 시세 조회(KRX: KRW, NYSE/NASDAQ: USD→KRW 환산) — 기존 `_fetch_price_series_sync()` 재사용.
- 각 기간별 총수익률·연환산수익률·MDD numpy 산출.
- Redis 캐싱(키 `portfolio_perf_summary:{portfolio_id}:{today_kst}`, TTL 3600s, `?refresh=true` 강제 갱신).
- 프론트엔드 `PerformanceSummaryPanel.js`(5개 기간 카드) + API 클라이언트 확장.
- 단위 테스트 + 통합 테스트.

### 2.2 제외 (What NOT to Build)

> [HARD] 본 SPEC은 다음을 **빌드하지 않는다**.

- **자동 매매/주문 실행**: 규제·책임 리스크로 프로젝트 전체에서 **영구 제외**.
- **일별 수익률 시계열 조회**: 일별 데이터 포인트 배열 반환은 SPEC-029(백테스팅)의 영역. 본 SPEC은 기간별 요약 스칼라값(총수익률·연환산·MDD)만 반환한다.
- **종목별 개별 성과 분석**: 포트폴리오 합산 성과만 제공하며, 보유 종목 각각의 기여도·개별 수익률은 산출하지 않는다.
- **비교 벤치마크(KOSPI, S&P500 대비)**: 포트폴리오 자체 수익률만 계산. 벤치마크 대비 초과수익은 향후 SPEC.
- **배당 수익률 포함 계산**: 가격 변동 수익률만 반영. 배당 재투자·배당 수익률은 SPEC-019(배당 분석) 영역으로 제외.
- **샤프 비율·변동성 등 위험조정 지표**: MDD 외 위험조정수익 지표는 SPEC-029(샤프)·SPEC-027(변동성) 영역.
- **거래 비용(수수료·세금·슬리피지)·리밸런싱**: 단순 보유(buy-and-hold) 가정만 계산.
- **사용자 정의 기간**: 5개 고정 기간만 지원. 임의 기간은 SPEC-029 백테스트 사용.
- **결과 영속화·히스토리**: one-shot 계산 + Redis 캐시만. 신규 DB 테이블·마이그레이션 없음(0018 유지).

---

## 3. 기능 요구사항 (EARS Requirements)

### REQ-PS-001 (Ubiquitous)

THE 시스템 SHALL `GET /portfolios/{portfolio_id}/performance-summary` 엔드포인트를 제공하여 인증된 소유자에게 포트폴리오 기간별 성과 요약을 반환한다.

### REQ-PS-002 (Event-driven)

WHEN 사용자가 성과 요약을 요청하면 THEN THE 시스템 SHALL YTD·1M·3M·6M·1Y 5개 기간 전체를 계산하여 응답에 포함한다.

### REQ-PS-003 (Ubiquitous)

THE 시스템 SHALL 각 기간별로 총수익률(`total_return_pct`)·연환산수익률(`annualized_return_pct`)·최대낙폭(`mdd_pct`)을 산출한다. 각 지표의 수식 및 산출 방법은 §5.2 기술 접근 방식에 정의한다.

### REQ-PS-004 (State-driven)

WHILE Redis 캐시가 유효한 동안 THE 시스템 SHALL FDR 조회·재계산 없이 캐시된 성과 요약을 반환한다. 캐시 키 포맷·TTL은 §5.3에 정의한다.

### REQ-PS-005 (Unwanted)

IF 보유 종목이 없거나 모든 종목의 시세 데이터가 부족한 경우, THEN THE 시스템 SHALL `200 OK`와 함께 5개 기간 모두 빈 성과 데이터(empty periods)를 반환하며 4xx 오류를 발생시키지 않는다.

### REQ-PS-006 (Ubiquitous)

THE 시스템 SHALL KRX(원화) 종목과 NYSE/NASDAQ(달러) 종목을 혼합한 포트폴리오를 지원하며, 해외 종목의 USD 종가에 USD/KRW 환율을 적용하여 KRW 환산 가치로 통일 계산한다.

### REQ-PS-007 (Event-driven)

WHEN `refresh=true` 쿼리 파라미터가 제공되면 THEN THE 시스템 SHALL 기존 캐시를 무시하고 FDR에서 최신 시세를 재조회하여 재계산한 뒤 캐시를 갱신한다.

### REQ-PS-008 (Optional)

WHERE 특정 기간의 시작일 이전 거래일 시세 데이터가 존재하지 않는 경우(예: 신규 상장 종목으로 1Y 데이터 미확보) THE 시스템 SHALL 가용한 가장 이른 거래일을 기준으로 해당 기간을 계산하거나, 유효 거래일이 2일 미만이면 해당 기간을 빈 데이터로 표시한다.

### REQ-PS-009 (Ubiquitous)

THE 프론트엔드 SHALL `PerformanceSummaryPanel` 컴포넌트로 5개 기간을 카드 형태로 표시하며, 각 카드는 기간 라벨·총수익률(양수 녹색·음수 적색)을 노출한다.

### REQ-PS-010 (Ubiquitous)

THE 시스템 SHALL `PerformanceSummaryResponse`에 `calculated_at`(ISO-8601 UTC 문자열)·`disclaimer`(문자열) 필드를 포함하여 반환하며, 다른 SPEC(SPEC-028·SPEC-029)과 동일한 응답 봉투 구조를 유지한다.

> Note: scipy 금지 원칙은 NFR-001에 정의됩니다.

---

## 4. 비기능 요구사항 (NFR)

- **NFR-001 (scipy 금지)**: THE 시스템 SHALL 모든 통계·수익률 계산에서 `scipy`를 import하지 않으며 numpy + math 표준 라이브러리만 사용한다(SPEC-027·028·029와의 일관성).
- **NFR-002 (응답시간)**: THE 시스템 SHALL Redis 캐시 히트 시 500ms 이내에 응답한다. 캐시 미스 시 FDR 조회는 `run_in_executor` + `asyncio.gather`로 병렬화하여 이벤트 루프를 블로킹하지 않는다.
- **NFR-003 (테스트 커버리지)**: THE `portfolio/performance_summary.py` 서비스·순수 함수 코드 SHALL 단위 테스트 커버리지 85% 이상을 충족한다.
- **NFR-004 (FDR graceful degradation)**: IF FDR 시세 조회가 실패하면 THEN THE 시스템 SHALL 예외를 전파하지 않고 해당 종목/기간을 제외하거나 빈 데이터를 반환하여 계산을 완료한다.
- **NFR-005 (환율 fallback)**: IF USD/KRW 환율 조회가 실패하면 THEN THE 시스템 SHALL fallback 기본값(`1350.0`)을 사용하여 계산을 중단하지 않는다.

---

## 5. 기술 접근 방식 (Technical Approach)

### 5.1 기간 시작일 산출

`today`(KST 기준) 대비 각 기간 시작일을 산출한다.

```
YTD: date(today.year, 1, 1)        # 당해 1월 1일
1M:  today - timedelta(days=30)
3M:  today - timedelta(days=90)
6M:  today - timedelta(days=180)
1Y:  today - timedelta(days=365)
```

종료일은 모든 기간 공통으로 `today`이다.

### 5.2 성과 계산 알고리즘 (기간별)

```
입력: holdings[{ticker, weight, market, currency}], period_start, period_end

1. 각 종목 FDR 시세 조회(period_start~period_end)
   → _fetch_price_series_sync() 재사용, run_in_executor + asyncio.gather 병렬
2. 해외(NYSE/NASDAQ) 종목: USD 종가 × USD/KRW 환율 → KRW 환산
3. 공통 거래일 기준 정렬(inner join) — _align_close_series() 재사용
4. 비중 정규화: w_i = weight_i / Σweight
5. 일별 포트폴리오 가치 = Σ(w_i × 종가[t] / 종가[0])  # 시작일 정규화
6. total_return_pct = (가치[-1] / 가치[0] - 1) × 100
7. annualized_return_pct = ((가치[-1]/가치[0])^(252/거래일수) - 1) × 100
8. mdd_pct = min((가치[t] - 이전최고가치) / 이전최고가치) × 100
   → backtest/metrics.calculate_max_drawdown 재사용 가능
9. 유효 거래일 < 2일 또는 데이터 없음 → 해당 기간 빈 데이터

출력: PeriodPerformance{period, display_label, total_return_pct,
       annualized_return_pct, mdd_pct, start_date, end_date, trading_days}
```

### 5.3 오케스트레이션 (`portfolio/performance_summary.py`)

`risk_analysis.py`·`backtest.py` 패턴을 모방한다.

1. 소유권 확인(`get_portfolio_with_holdings`) → 포트폴리오 없거나 소유권 불일치 시 404(코드베이스 관례).
2. Redis 캐시 조회(키 `portfolio_perf_summary:{portfolio_id}:{today_kst}`, `refresh=False` 시).
3. 보유 종목 0개 → 빈 성과 응답(REQ-PS-005).
4. 해외 종목 존재 시 환율 조회(`get_usd_krw_rate`, 실패 시 fallback).
5. 5개 기간 각각 §5.2 알고리즘 실행(FDR 조회는 기간별 최장 구간 1Y를 한 번만 조회하고 슬라이싱하여 재사용 가능 — 구현 최적화 여지).
6. `PerformanceSummaryResponse` 구성·캐시 적재(TTL 3600s, graceful)·반환.

### 5.4 스키마 (`portfolio/schemas.py`)

- `PeriodPerformance`: `period`(Literal "ytd"/"1m"/"3m"/"6m"/"1y"), `display_label`(str), `total_return_pct`(float|None), `annualized_return_pct`(float|None), `mdd_pct`(float|None), `start_date`(str|None), `end_date`(str|None), `trading_days`(int), `has_data`(bool).
- `PerformanceSummaryResponse`: `portfolio_id`(int), `periods`(list[PeriodPerformance], 5개), `calculated_at`(str), `disclaimer`(str).
- Pydantic v2 패턴: validator 미사용(검증 로직 없음). 특수 직렬화 불필요 시 `model_config` 생략.

### 5.5 라우터 (`portfolio/router.py`)

- `GET /portfolios/{portfolio_id}/performance-summary?refresh={bool}` (async).
- `Depends(get_current_user)` + 소유권 확인, `Depends(get_redis_client)` 주입.
- 응답 `PerformanceSummaryResponse`.

### 5.6 프론트엔드

- `frontend/src/components/PerformanceSummaryPanel.js` — 5개 기간 카드 그리드(BacktestPanel.js 카드 레이아웃 패턴 재사용). 양수 녹색·음수 적색.
- `frontend/src/api/portfolio.js`(+`.ts`) — `apiGetPerformanceSummary(token, portfolioId, refresh)`.
- `frontend/src/pages/Portfolio.js`(+`.tsx`) — PerformanceSummaryPanel 통합(기존 섹션 보존).

### 5.7 재사용 자산

- `portfolio/backtest.py`: `_fetch_price_series_sync()`(시세 조회), `_align_close_series()`(공통 거래일 정렬), `_compute_returns()`(누적 수익률 추출).
- `backtest/metrics.py`: `calculate_max_drawdown`(MDD).
- `portfolio/fx_rate.py`: `get_usd_krw_rate`, `_FALLBACK_RATE`(1350.0).
- `portfolio/service.py`: `get_portfolio_with_holdings`(소유권).

---

## 6. Delta Markers (변경 영향 분석)

브라운필드 프로젝트 변경 영향을 명시한다.

| 마커 | 파일 | 내용 |
|------|------|------|
| [EXISTING] | `backend/src/stock_picker/portfolio/backtest.py` | `_fetch_price_series_sync`·`_align_close_series`·`_compute_returns` 내부 참조용 재사용(아래 주석 참고) |
| [EXISTING] | `backend/src/stock_picker/portfolio/service.py` | `get_portfolio_with_holdings` 재사용(수정 없음) |
| [EXISTING] | `backend/src/stock_picker/portfolio/fx_rate.py` | `get_usd_krw_rate`·`_FALLBACK_RATE` 재사용(수정 없음) |
| [EXISTING] | `backend/src/stock_picker/backtest/metrics.py` | `calculate_max_drawdown` 재사용(수정 없음) |
| [MODIFY] | `backend/src/stock_picker/portfolio/router.py` | `GET /performance-summary` 신규 엔드포인트 추가 |
| [MODIFY] | `backend/src/stock_picker/portfolio/schemas.py` | `PerformanceSummaryResponse`·`PeriodPerformance` 스키마 추가 |
| [NEW] | `backend/src/stock_picker/portfolio/performance_summary.py` | 핵심 성과 계산 서비스 |
| [NEW] | `backend/tests/unit/test_portfolio_performance_summary.py` | 단위 테스트(30개 이상) |
| [NEW] | `backend/tests/integration/test_portfolio_performance_summary_router.py` | 통합 테스트 |
| [NEW] | `frontend/src/components/PerformanceSummaryPanel.js` | 5개 기간 카드 컴포넌트 |
| [MODIFY] | `frontend/src/api/portfolio.js` | `apiGetPerformanceSummary` 추가 |
| [MODIFY] | `frontend/src/pages/Portfolio.js` | PerformanceSummaryPanel 통합 |
| [MODIFY] | `frontend/src/api/portfolio.ts` | TypeScript 인터페이스 추가 |
| [MODIFY] | `frontend/src/pages/Portfolio.tsx` | PerformanceSummaryPanel 통합 |

> **프라이빗 함수 재사용 방침** (D-008 대응): `backtest.py`의 `_fetch_price_series_sync`·`_align_close_series`·`_compute_returns`는 Python 관례상 프라이빗(밑줄 접두사) 함수다. `performance_summary.py`에서 이 함수들을 import하면 강결합이 발생한다. 구현자는 다음 두 전략 중 하나를 선택한다: (A) `performance_summary.py` 내부에 동일 로직을 최소 재구현(DRY 포기 + 결합 회피), (B) 구현 시 `backtest.py`의 해당 함수를 `portfolio/_price_utils.py` 공용 모듈로 추출하고 `[MODIFY] backtest.py` 및 `[NEW] portfolio/_price_utils.py` Delta Marker를 추가. 전략 선택은 Run Phase 구현자 재량이며 선택 결과를 progress.md에 기록한다.

**마이그레이션**: 불필요. 신규 DB 테이블·컬럼을 추가하지 않는다. 성과 요약은 one-shot 계산 + Redis 캐시이며 마이그레이션 최신 버전(0018)은 변경되지 않는다.

---

## 7. 의존성 (Dependencies)

- **SPEC-029**(포트폴리오 백테스트): `_fetch_price_series_sync`·`_align_close_series`·`_compute_returns` 재사용. 본 SPEC은 백테스트 코드를 수정하지 않는다.
- **SPEC-028**(해외 자산 지원): `PortfolioHolding.market`·`currency` 필드, `fx_rate.py` 환율 서비스.
- **SPEC-027**(리스크 분석): Redis 캐싱·numpy 계산·scipy 금지 패턴, 오케스트레이션 구조.
- **SPEC-017**(포트폴리오 성과): `get_portfolio_with_holdings`·비중 데이터.

---

## 8. MX 태그 계획 (MX Tag Plan)

코드 주석 언어는 한국어(`language.yaml` `code_comments: ko`).

- **@MX:ANCHOR** (`performance_summary.py`의 `calculate_performance_summary` 오케스트레이션 진입점):
  - 사유: router.py + 단위 테스트 + 통합 테스트(캐시 경로 포함)에서 fan_in ≥ 3 예상. `@MX:REASON` 필수.
- **@MX:NOTE** (`_compute_period_returns` 순수 함수):
  - 다기간 numpy 수익률 산출 비즈니스 로직(총수익률·연환산·MDD 정의) 설명.
- **@MX:NOTE** (`_compute_period_dates` 기간 시작일 산출):
  - YTD 경계 케이스(1월 1일) 처리 근거 명시.
- **@MX:NOTE** (`performance_summary.py` 모듈 상단):
  - scipy 금지·numpy 전용 원칙 명시(risk_analysis.py·backtest.py 패턴 일관성).
- **@MX:TODO** (RED 단계):
  - 미구현 순수 함수·오케스트레이션에 테스트 작성 전 임시 마커. GREEN 단계에서 제거.

태그 설명은 한국어로 작성하고, 에이전트 생성 태그는 `[AUTO]` 접두사를 포함한다.
