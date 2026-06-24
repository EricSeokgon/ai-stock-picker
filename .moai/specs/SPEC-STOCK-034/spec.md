---
id: "SPEC-STOCK-034"
version: "0.1.0"
status: "draft"
created_at: "2026-06-24"
updated_at: "2026-06-24"
author: "ircp"
priority: "medium"
issue_number: 0
labels: ["portfolio", "benchmark", "alpha", "beta", "backend", "frontend"]
---

# SPEC-STOCK-034: 포트폴리오 벤치마크 비교 (Portfolio Benchmark Comparison)

> Roadmap 성과 평가(performance evaluation) 계열 SPEC. SPEC-030(기간별 성과 요약)이 제공하는 포트폴리오 자체 수익률 위에, **시장 벤치마크 지수**(KOSPI/KOSDAQ/S&P500/NASDAQ)와의 **상대 성과**를 추가한다. 기간별 초과수익, 알파(연환산 초과수익), 베타(시장 민감도), 그리고 100 기준 재기준화 차트를 제공한다. 자동 매매·실시간 추적은 하지 않는다(영구 제외).

## HISTORY

| 버전 | 날짜 | 변경 내용 |
|------|------|-----------|
| 0.1.0 | 2026-06-24 | 최초 작성. SPEC-030 기간 헬퍼·가치 시계열 재사용 + SPEC-027 numpy 전용 베타 패턴 모방. 신규 핵심: 벤치마크 기간 수익률 비교·알파·베타·재기준화 차트. 신규 엔드포인트 2종(`/benchmark`·`/benchmark/chart`). DB 테이블·마이그레이션 미도입(yfinance 온디맨드 조회). |

> **REQ 접두사 설계 원칙**: 본 SPEC은 `REQ-BMK-*`(BenchMarK) 접두사를 사용한다. 기존 SPEC 접두사(OPT/RISK/FA/PBT/PS/PAL/RBA/DVY)와 충돌하지 않는다.

> **번호 체계**: REQ-BMK-001~005 연속 번호. NFR은 REQ-BMK-NFR-001~005.

---

## 1. 개요 (Overview)

### 1.1 기능 설명

SPEC-030은 포트폴리오의 5개 표준 기간(YTD/1M/3M/6M/1Y) **자체 수익률**과 MDD를 `GET /portfolios/{id}/performance-summary`로 제공한다. 그러나 투자자의 핵심 질문에 답하지 못한다.

- **"내 포트폴리오가 시장보다 잘했나, 못했나?"** — 030은 절대 수익률만 알려준다. 시장 대비 상대 성과(초과수익)가 없다.
- **"내 초과수익이 진짜 실력(알파)인가, 시장 변동에 따라간 것(베타)인가?"** — 030에 알파·베타 분해가 없다.

SPEC-034는 이 간극을 메운다. SPEC-030의 기간 정의·가치 시계열 산출을 **재사용**하여 다음을 추가한다.

- **벤치마크 기간 비교**(`BenchmarkComparison`) — 요청 기간의 포트폴리오 수익률·벤치마크 수익률·초과수익을 제공.
- **알파·베타**(`alpha`/`beta`) — 연환산 초과수익(알파)과 시장 민감도(베타, 공분산/분산 비율).
- **재기준화 차트**(`BenchmarkChartData`) — 포트폴리오/벤치마크 가치를 기간 시작 100으로 맞춘 시계열. **시각적 상대 비교의 핵심 가치.**

### 1.2 동기 (Motivation)

포트폴리오 평가의 황금 질문은 "시장을 이겼는가(beat the market)"이다.

- **상대 성과**: +10% 수익이라도 시장이 +15%였다면 사실상 손해(−5%p 초과수익)다. 절대값만으로는 운용 품질을 판단할 수 없다.
- **알파·베타 분해**: 초과수익이 실력(알파)인지 단순 고베타 노출인지 구분해야 리스크 조정 성과를 이해할 수 있다.
- **시각적 직관**: 100 기준 재기준화 차트는 두 곡선의 벌어짐으로 상대 성과를 한눈에 보여 준다.

본 SPEC은 정보 제공·의사결정 지원이며, 실제 매매를 집행하거나 실시간 추적을 하지 않는다.

### 1.3 목표 (Goals)

- 요청 기간에 대해 포트폴리오 수익률·벤치마크 수익률·초과수익을 산출하여 제공한다.
- 충분한 일별 데이터가 있을 때 연환산 알파와 베타(공분산/분산 비율)를 산출한다.
- 포트폴리오·벤치마크 가치를 기간 시작 100으로 재기준화한 차트 시계열을 제공한다.
- 핵심 계산(비교·차트·베타)을 DB·외부 API 없이 테스트 가능한 순수 함수로 분리한다.
- 프론트엔드에 벤치마크 비교 카드·재기준화 차트 UI를 추가한다.

### 1.4 기술 스택 (확정·재사용)

FastAPI + PostgreSQL(asyncpg) + SQLAlchemy + Redis + React + JavaScript/TypeScript. 신규 라이브러리·신규 DB 테이블·신규 마이그레이션을 도입하지 않는다. 벤치마크 지수 가격은 기존 가격 조회 인프라(FDR/yfinance best-effort)를 통해 온디맨드로 조회한다. 수치 계산은 `numpy` + `math`만 사용한다(scipy 미사용).

---

## 2. 범위 (Scope)

### 2.1 포함 (In Scope)

- 신규 순수 함수 모듈 `portfolio/benchmark.py`:
  - 벤치마크 기간 비교 산출(순수 함수) — 포트폴리오·벤치마크 시계열로부터 기간 수익률·초과수익·알파·베타를 계산.
  - 재기준화 차트 산출(순수 함수) — 두 시계열을 기간 시작 100으로 정규화.
  - 베타 산출(순수 함수) — 일별 수익률 두 시리즈의 공분산/분산 비율, 데이터 부족 시 미산정.
- 신규 서비스 오케스트레이션 — 소유권 확인, 포트폴리오 가치 시계열 산출(SPEC-030 재사용), 벤치마크 지수 가격 온디맨드 조회, 순수 함수 호출.
- 신규 Pydantic 스키마(`portfolio/schemas.py`): `BenchmarkPeriodReturn`, `BenchmarkComparison`, `BenchmarkChartPoint`, `BenchmarkChartData`.
- 신규 엔드포인트 2개(`portfolio/router.py`):
  - `GET /portfolios/{portfolio_id}/benchmark`
  - `GET /portfolios/{portfolio_id}/benchmark/chart`
- 지원 벤치마크 4종(코스피·코스닥·S&P500·나스닥)의 코드→지수 심볼 매핑.
- 프론트엔드 벤치마크 비교 컴포넌트 + API 클라이언트 확장(`.js`/`.ts` 쌍).
- 단위 테스트(커버리지 85% 이상).

### 2.2 제외 (What NOT to Build)

> [HARD] 본 SPEC은 다음을 **빌드하지 않는다**.

- **SPEC-030 재구현/대체**: 포트폴리오 자체 기간 수익률·MDD *조회* 기능은 SPEC-030을 수정·제거하지 않는다. 034는 030의 기간 정의·가치 시계열 산출을 *재사용*하며, 기존 `/performance-summary` 엔드포인트·`PerformanceSummaryResponse` 스키마를 변경하지 않는다.
- **위험조정 정밀 알파(Jensen's Alpha)**: 알파는 연환산 포트폴리오 수익률과 연환산 벤치마크 수익률의 단순 차이로 산출한다. 무위험수익률을 반영한 CAPM 정밀 알파는 제외한다(단순·투명).
- **사용자 정의 벤치마크**: 벤치마크는 명시된 4종(코스피·코스닥·S&P500·나스닥)으로 한정한다. 임의 종목·혼합 지수·사용자 작성 벤치마크는 제외한다.
- **실시간 추적·자동 알림**: 벤치마크 대비 성과를 실시간으로 추적하거나 초과수익 임계 알림을 발송하지 않는다. 모든 값은 요청 시점 스냅샷이다.
- **다요인 모델(Fama-French 등)**: 베타는 단일 시장 베타(공분산/분산)만 산출한다. 규모·가치·모멘텀 등 다요인 회귀는 제외한다.
- **미래 수익 예측**: 모든 지표는 과거 데이터 기반 산출이며, 미래 알파·베타를 예측하지 않는다.
- **신규 DB 테이블·마이그레이션**: 벤치마크 데이터는 온디맨드 조회(+선택적 캐시)로 동작한다. `benchmark_cache` 등 신규 테이블·마이그레이션(0022)을 도입하지 않는다.
- **통화 환전 정산**: 벤치마크 비교 지표는 모두 무차원 비율(수익률·인덱스)이므로 통화 환산이 불필요하다. 절대 금액 환전 정산은 하지 않는다.
- **벤치마크 데이터 미확보 시 추측**: 벤치마크 가격을 확보할 수 없으면 해당 기간의 벤치마크 지표를 미산정(없음)으로 처리하고 단언하지 않는다.

---

## 3. 기능 요구사항 (EARS Requirements)

### REQ-BMK-001 (Event-driven) — 벤치마크 수익률 조회

WHEN 시스템이 포트폴리오에 대한 벤치마크 비교를 계산하면 THE 시스템 SHALL 요청된 벤치마크 지수의 과거 가격 데이터를 비교 기간에 대해 조회하고, 해당 기간의 벤치마크 수익률을 도출한다.

### REQ-BMK-002 (Event-driven) — 기간 수익률 비교

WHEN 특정 기간에 대해 벤치마크 수익률 데이터가 가용하면 THE 시스템 SHALL 해당 기간의 포트폴리오 수익률과 벤치마크 수익률을 함께 반환하며, 초과수익(포트폴리오 수익률에서 벤치마크 수익률을 뺀 값)을 함께 제공한다.

### REQ-BMK-003 (Event-driven) — 알파·베타 산출

WHEN 충분한 일별 수익률 시계열 데이터가 가용하면 THE 시스템 SHALL 연환산 알파를 연환산 포트폴리오 수익률과 연환산 벤치마크 수익률의 차이로 산출하고, 베타를 일별 포트폴리오 수익률과 일별 벤치마크 수익률의 공분산을 일별 벤치마크 수익률의 분산으로 나눈 값으로 산출한다.

### REQ-BMK-004 (Event-driven) — 차트 인덱스 데이터

WHEN 사용자가 벤치마크 비교의 차트 데이터를 요청하면 THE 시스템 SHALL 포트폴리오 값과 벤치마크 값을 모두 비교 기간 시작 시점에 100의 지수로 재기준화한 시계열 데이터를 반환한다.

### REQ-BMK-005 (Unwanted) — 소유권 확인 및 graceful degradation

IF 요청 사용자가 소유하지 않은 포트폴리오에 대해 벤치마크 비교를 요청하면 THEN THE 시스템 SHALL 존재하지 않는 포트폴리오에 대한 요청과 동일하게 응답하여 소유권 정보를 노출하지 않는다. IF 특정 기간에 대한 벤치마크 데이터를 확보할 수 없으면 THEN THE 시스템 SHALL 오류를 발생시키지 않고 해당 기간의 벤치마크 지표를 미산정 값으로 반환한다.

---

## 4. 비기능 요구사항 (NFR)

- **REQ-BMK-NFR-001 (외부 최적화 라이브러리 비도입)**: THE 시스템 SHALL 본 SPEC 신규 수치 계산 코드를 표준 수학 연산 및 프로젝트 승인 수치 라이브러리만으로 구현하며, 새로운 외부 통계·최적화 라이브러리를 도입하지 않는다.
- **REQ-BMK-NFR-002 (순수 함수 테스트성)**: THE 시스템의 핵심 벤치마크 비교·차트·베타 계산 컴포넌트 SHALL 데이터베이스·외부 캐시·외부 네트워크 호출에 대한 의존 없이 입력값만으로 결정적 결과를 반환한다.
- **REQ-BMK-NFR-003 (벤치마크 데이터 미확보 graceful degradation)**: IF 특정 기간의 벤치마크 데이터를 확보할 수 없으면 THEN THE 시스템 SHALL 해당 기간의 벤치마크 관련 지표를 미산정 값으로 처리하고 오류를 발생시키지 않는다.
- **REQ-BMK-NFR-004 (베타 최소 데이터 요건)**: THE 베타 산출 컴포넌트 SHALL 일별 수익률 데이터가 최소 20개 미만이면 베타를 미산정 값으로 반환한다.
- **REQ-BMK-NFR-005 (테스트 커버리지)**: THE 시스템의 벤치마크 비교 계산 컴포넌트 SHALL 단위 테스트 커버리지 85% 이상을 충족한다.

---

## 5. 기술 접근 방식 (Technical Approach)

### 5.1 순수 함수 (`portfolio/benchmark.py`)

```python
def calculate_benchmark_comparison(
    portfolio_history: list[dict],   # [{date, portfolio_value}, ...]
    benchmark_history: list[dict],   # [{date, close_price}, ...]
    period: str,                     # "YTD"|"1M"|"3M"|"6M"|"1Y"
) -> BenchmarkComparison: ...

def calculate_benchmark_chart(
    portfolio_history: list[dict],
    benchmark_history: list[dict],
    period: str,
) -> list[BenchmarkChartPoint]: ...

def calculate_beta(
    portfolio_daily_returns: list[float],
    benchmark_daily_returns: list[float],
) -> Optional[float]: ...           # 데이터 20개 미만 → None
```

#### 5.1.1 `calculate_benchmark_comparison` 알고리즘

1. 포트폴리오·벤치마크 시계열을 공통 거래일 기준으로 inner join.
2. 포트폴리오 기간 수익률 = `(port_value[-1] / port_value[0] - 1) × 100`.
3. 벤치마크 기간 수익률 = `(bench_close[-1] / bench_close[0] - 1) × 100`. 벤치마크 데이터 없으면 None.
4. 초과수익 = `portfolio_return_pct - benchmark_return_pct` (벤치마크 None이면 None).
5. 연환산: `ann = (1 + total/100)^(252/n_days) - 1`. 알파 = `(ann_port - ann_bench) × 100`(%p).
6. 일별 수익률로 베타 산출(`calculate_beta`). 데이터 < 20 → None.

#### 5.1.2 `calculate_benchmark_chart` 알고리즘

1. 공통 거래일 inner join.
2. `portfolio_index[t] = port_value[t] / port_value[0] × 100`.
3. `benchmark_index[t] = bench_close[t] / bench_close[0] × 100` (벤치마크 결측 → None).
4. 날짜별 `BenchmarkChartPoint` 리스트 반환.

#### 5.1.3 `calculate_beta` 알고리즘 (numpy 전용)

```
if len(p) != len(b) or len(b) < 20: return None
var_b = np.var(b, ddof=1)
if var_b == 0: return None              # 벤치마크 무변동 가드
cov_pb = np.cov(p, b)[0, 1]
beta = cov_pb / var_b
NaN/Inf 가드 → None
```

순수 함수는 DB·가격 조회를 하지 않는다(REQ-BMK-NFR-002). scipy 미사용, numpy+math만으로 충분.

> **설계 결정 노트(라이브러리)**: REQ-BMK-NFR-001 구현 시 `numpy`+`math`만 사용하고 `scipy`는 import하지 않는다(`risk_analysis.py` 패턴 일관성).
> **설계 결정 노트(단순 알파)**: 무위험수익률을 반영하지 않는 단순 알파는 의도된 단순화다. 연환산 초과수익만 투명하게 보여 준다(§2.2 제외).
> **설계 결정 노트(통화)**: 비교 지표는 모두 무차원 비율(수익률·인덱스)이므로 벤치마크와 포트폴리오의 통화 단위가 달라도 비교 가능하다. 포트폴리오 가치 시계열은 SPEC-030 관행대로 USD 종목을 KRW 환산하되, 최종 비율 비교에는 통화가 상쇄된다.

### 5.2 벤치마크 심볼 매핑

| 입력 코드 | 지수 심볼 | 설명 |
|-----------|-----------|------|
| `KOSPI` | `^KS11` | 코스피 종합지수 |
| `KOSDAQ` | `^KQ11` | 코스닥 종합지수 |
| `SP500` | `^GSPC` | S&P 500 |
| `NASDAQ` | `^IXIC` | 나스닥 종합지수 |

### 5.3 서비스 오케스트레이션

```
벤치마크 비교 서비스(portfolio_id, user_id, db, redis, benchmark, period):
  1. get_portfolio_with_holdings(db, portfolio_id, user_id)  # None → 404 (REQ-BMK-005)
  2. 기간 시작일 산정 (SPEC-030 기간 헬퍼 재사용)
  3. 보유 종목별 가격 시계열 조회 → 가중 포트폴리오 가치 시계열 산출 (SPEC-030 재사용)
     - USD 종목 KRW 환산(SPEC-028 fx_rate)
  4. 벤치마크 지수 심볼 가격 시계열 온디맨드 조회 (실패 → None, REQ-BMK-005)
  5. calculate_benchmark_comparison(portfolio_history, benchmark_history, period)
  6. RETURN BenchmarkComparison

벤치마크 차트 서비스(portfolio_id, user_id, db, redis, benchmark, period):
  1. 소유권 확인 (404)
  2. 포트폴리오 가치 시계열 + 벤치마크 종가 시계열 조회 (위와 동일)
  3. calculate_benchmark_chart(portfolio_history, benchmark_history, period)
  4. RETURN BenchmarkChartData
```

> **설계 결정 노트(가치 시계열 재사용)**: 포트폴리오 일별 가치 시계열은 SPEC-030의 가치 산출 로직(공통 거래일 정렬·비중 정규화·첫날 정규화)을 재사용한다. 034는 신규 가치 산출 로직을 작성하지 않는다(중복 회피, §2.2 제외).
> **설계 결정 노트(소유권 응답)**: REQ-BMK-005 구현 시 `get_portfolio_with_holdings()` None → `404 Not Found`(코드베이스 관례, 403 아님).
> **설계 결정 노트(벤치마크 조회)**: 벤치마크 지수 가격은 기존 동기 FDR 조회 패턴(`_fetch_price_series_sync`)을 `run_in_executor`로 격리하여 재구현한다(전략 A, SPEC-030 관행).

### 5.4 스키마 (`portfolio/schemas.py`)

```python
class BenchmarkPeriodReturn(BaseModel):
    period: str                            # "YTD"|"1M"|"3M"|"6M"|"1Y"
    portfolio_return_pct: float
    benchmark_return_pct: Optional[float]  # 미확보 시 None
    excess_return_pct: Optional[float]     # portfolio - benchmark

class BenchmarkComparison(BaseModel):
    portfolio_id: int
    benchmark: str                         # "KOSPI"|"KOSDAQ"|"SP500"|"NASDAQ"
    period: str
    portfolio_return_pct: float
    benchmark_return_pct: Optional[float]
    excess_return_pct: Optional[float]
    alpha: Optional[float]                 # 연환산 초과수익(%p)
    beta: Optional[float]                  # 공분산/분산; 데이터 20개 미만 None
    calculated_at: datetime

class BenchmarkChartPoint(BaseModel):
    date: date
    portfolio_index: float                 # 기간 시작 100 기준
    benchmark_index: Optional[float]

class BenchmarkChartData(BaseModel):
    portfolio_id: int
    benchmark: str
    period: str
    chart: list[BenchmarkChartPoint]
```

> **명명 충돌 회피**: 034 스키마(`BenchmarkPeriodReturn`/`BenchmarkComparison`/`BenchmarkChartPoint`/`BenchmarkChartData`)는 030의 `PerformanceSummaryResponse`/`PeriodPerformance`와 이름이 분리되어 충돌하지 않는다.
> **`BenchmarkPeriodReturn` 용도**: 단일 기간 응답(`BenchmarkComparison`)을 다기간 확장할 때를 위한 재사용 단위. 본 SPEC 엔드포인트는 단일 기간을 받으며, 향후 전체 기간 일괄 응답 확장 시 `list[BenchmarkPeriodReturn]`을 사용할 수 있다.

### 5.5 라우터 (`portfolio/router.py`)

```
GET /portfolios/{portfolio_id}/benchmark?benchmark=<KOSPI|KOSDAQ|SP500|NASDAQ, 기본 KOSPI>&period=<YTD|1M|3M|6M|1Y, 기본 YTD>
  소유권 불일치 → 404 (REQ-BMK-005)
  Response: BenchmarkComparison

GET /portfolios/{portfolio_id}/benchmark/chart?benchmark=<...>&period=<...>
  소유권 불일치 → 404
  Response: BenchmarkChartData
```

기존 `Depends(get_current_user)` + `get_db_session` + `get_redis_client` 패턴 재사용. `benchmark` 접두사 경로는 기존 엔드포인트와 충돌 없음.

### 5.6 프론트엔드

- `frontend/src/components/BenchmarkComparisonCard.js` — 벤치마크 선택 + 기간별 포트폴리오·벤치마크·초과수익·알파·베타 카드.
- `frontend/src/components/BenchmarkChart.js` — 100 기준 재기준화 라인 차트(포트폴리오 vs 벤치마크).
- `frontend/src/api/portfolio.js`(+`.ts`) — `apiGetBenchmarkComparison`·`apiGetBenchmarkChart`.
- `frontend/src/pages/Portfolio.js`(+`.tsx`) — 벤치마크 비교 섹션 통합(기존 섹션 보존).

---

## 6. Delta Markers (변경 영향 분석)

| 마커 | 파일 | 내용 |
|------|------|------|
| [EXISTING] | `backend/src/stock_picker/portfolio/performance_summary.py` | 기간 정의·가치 시계열 산출 로직 재사용(수정 없음 권장) |
| [EXISTING] | `backend/src/stock_picker/portfolio/service.py` | `get_portfolio_with_holdings`·`_fetch_foreign_price` 재사용(수정 없음) |
| [EXISTING] | `backend/src/stock_picker/portfolio/fx_rate.py` | `get_usd_krw_rate` 재사용(수정 없음) |
| [EXISTING] | `backend/src/stock_picker/portfolio/risk_analysis.py` | numpy 전용 베타 계산 패턴 모방(수정 없음) |
| [NEW] | `backend/src/stock_picker/portfolio/benchmark.py` | 순수 함수 3종 + 서비스 오케스트레이션 2종 |
| [MODIFY] | `backend/src/stock_picker/portfolio/schemas.py` | `BenchmarkPeriodReturn`·`BenchmarkComparison`·`BenchmarkChartPoint`·`BenchmarkChartData` 추가 |
| [MODIFY] | `backend/src/stock_picker/portfolio/router.py` | benchmark·benchmark/chart 엔드포인트 2종 추가 |
| [NEW] | `backend/tests/unit/test_benchmark.py` | 순수 함수·서비스 단위 테스트(커버리지 85%+) |
| [NEW] | `frontend/src/components/BenchmarkComparisonCard.js` | 벤치마크 비교 카드 |
| [NEW] | `frontend/src/components/BenchmarkChart.js` | 재기준화 차트 |
| [MODIFY] | `frontend/src/api/portfolio.js` | 벤치마크 API 클라이언트 추가 |
| [MODIFY] | `frontend/src/api/portfolio.ts` | 벤치마크 API 클라이언트 추가 |
| [MODIFY] | `frontend/src/pages/Portfolio.js` | 벤치마크 비교 섹션 통합 |
| [MODIFY] | `frontend/src/pages/Portfolio.tsx` | 벤치마크 비교 섹션 통합 |

> **DB 테이블·마이그레이션 미도입**: 벤치마크 지수 가격을 온디맨드 조회(+선택적 Redis 캐시)로 처리하므로 신규 테이블·마이그레이션(0022)이 **불필요**하다. 최신 리비전 `0021_rebalancing_plans.py`(SPEC-032)는 그대로 둔다.

---

## 7. 의존성 (Dependencies)

- **SPEC-030**(성과 요약): 기간 정의(`_compute_period_dates`)·가치 시계열 산출(`_compute_portfolio_values`·`_align_close_series`)·연환산 공식 재사용. 030 코드(엔드포인트·스키마)는 수정·제거하지 않는다.
- **SPEC-027**(리스크 분석): 순수 함수 + numpy 전용 구조 패턴(`risk_analysis.py`)·일별 수익률 산출·NaN 가드 모방.
- **SPEC-028**(해외 자산 지원): `PortfolioHolding.market`/`currency`, `_fetch_foreign_price`, `fx_rate` — KRW 환산.
- **SPEC-017**(포트폴리오 성과): `get_portfolio_with_holdings` 소유권, `get_current_price` KRX 가격.
- **SPEC-029**(백테스팅): 동기 FDR 가격 시계열 조회 패턴(`_fetch_price_series_sync`) 모방(벤치마크 지수 조회).

---

## 8. MX 태그 계획 (MX Tag Plan)

코드 주석 언어는 한국어(`language.yaml` `code_comments: ko`).

- **@MX:ANCHOR** (`benchmark.py`의 벤치마크 비교 순수 함수 진입점):
  - 사유: 서비스 오케스트레이션 2종 + 단위 테스트에서 fan_in ≥ 3 예상. `@MX:REASON` 필수.
- **@MX:ANCHOR** (`BenchmarkComparison`·`BenchmarkChartData` 응답 스키마):
  - 사유: router·service·프론트 API 래퍼·테스트 3곳 이상 참조. `@MX:REASON` 필수.
- **@MX:NOTE** (`benchmark.py` 모듈 상단):
  - scipy 금지·numpy/math 전용, 단순 알파(무위험수익률 미반영)·통화 무차원 비교 명시.
- **@MX:NOTE** (베타 최소 데이터 분기):
  - 일별 수익률 20개 미만·벤치마크 무변동(var=0) 시 None 반환 사유.
- **@MX:WARN** (동기 FDR 벤치마크 지수 조회부):
  - `run_in_executor` 격리 필수·블로킹 호출 주의. `@MX:REASON` 필수.
- **@MX:TODO** (RED 단계):
  - 미구현 순수 함수·오케스트레이션 임시 마커. GREEN 단계에서 제거.

태그 설명은 한국어로 작성하고, 에이전트 생성 태그는 `[AUTO]` 접두사를 포함한다.

---

## 9. 수용 기준 (Acceptance Criteria)

상세 BDD 시나리오·EARS 수용 기준은 [acceptance.md](acceptance.md) 참조. 작업 분해는 [plan.md](plan.md), 압축 참조는 [spec-compact.md](spec-compact.md) 참조.
