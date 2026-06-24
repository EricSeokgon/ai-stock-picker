# SPEC-STOCK-034 연구 노트 (Research) — 포트폴리오 벤치마크 비교

> Plan 단계 사전 코드베이스 분석. 본 문서는 SPEC 작성의 근거이며, run 단계 구현자가 재사용할 패턴·재사용 지점·충돌 회피 전략을 기록한다.

작성일: 2026-06-24 / 브랜치: `feature/SPEC-STOCK-034`

---

## 1. 목표 요약

기존 포트폴리오의 기간별 수익률(SPEC-030)을 **시장 벤치마크 지수**(KOSPI/KOSDAQ/S&P500/NASDAQ)와 비교한다.

- 기간별 포트폴리오 수익률 vs 벤치마크 수익률 + 초과수익(excess return)
- 알파(연환산 초과수익) + 베타(공분산/분산 비율, 최소 20개 일별 데이터)
- 차트 데이터: 포트폴리오/벤치마크 가치를 기간 시작 100으로 재기준화(rebase)한 시계열

신규 DB 테이블·마이그레이션 없음. 벤치마크 데이터는 yfinance(FDR 경유) 온디맨드 조회.

---

## 2. 핵심 재사용 지점 (기존 코드 분석)

### 2.1 기간 정의 (SPEC-030 `performance_summary.py`)

- `_compute_period_dates(today)` → `{ytd, 1m, 3m, 6m, 1y}` 시작일 딕셔너리 반환 (L62~81).
  - ytd=당해 1/1, 1m=−30일, 3m=−90일, 6m=−180일, 1y=−365일.
- `PERIOD_DISPLAY_LABELS` (L26~32): 기간 코드→한국어 라벨.
- `_TRADING_DAYS_PER_YEAR = 252` (L35): 연환산 계수.
- **재사용 전략**: 034는 SPEC-030의 기간 시작일 산정 로직을 **재사용**한다(재구현 금지). 다만 034 입력 파라미터는 요청서 표기 그대로 대문자(`YTD`,`1M`,`3M`,`6M`,`1Y`)를 받고, 내부에서 소문자 코드로 정규화하여 030 헬퍼와 연결한다.
- `_compute_period_returns(values)` (L203~247): 가치 시계열→총수익률·연환산수익률·MDD. 포트폴리오/벤치마크 기간 수익률 계산에 동일 공식(`values[-1]/values[0]-1`) 적용 가능.

### 2.2 가격 시계열 조회 (FDR 동기 → run_in_executor)

세 곳에서 동일 패턴 확인:

| 파일 | 함수 | 비고 |
|------|------|------|
| `performance_summary.py` | `_fetch_price_series_sync(ticker, start, end)` L252 | `fdr.DataReader(ticker, start=, end=)` → `[{date, close}]` |
| `backtest.py` | `_fetch_price_series_sync(ticker, start, end)` L149 | `@MX:WARN` 동기 FDR 격리 명시 |
| `risk_analysis.py` | `_fetch_stock_prices(krx_code, period)` L182 | period일치 tail |

- 모두 동기 FDR을 `loop.run_in_executor(None, ...)` 또는 전용 `ThreadPoolExecutor`로 격리.
- **벤치마크 지수 조회**: `fdr.DataReader("^KS11", start, end)` 형태로 yfinance 지수 심볼을 직접 조회 가능(FDR이 yfinance 백엔드로 `^` 심볼 지원). 동일 `_fetch_price_series_sync` 패턴을 신규 모듈에 재구현(전략 A: 030이 backtest 함수를 재구현한 것과 동일 관행).
- FDR 실패 시 빈 리스트 반환 → 해당 기간 벤치마크 메트릭 None 처리(graceful degradation, REQ-BMK-005).

### 2.3 포트폴리오 가치 시계열 (SPEC-030)

- `_align_close_series(price_data)` L86: 여러 종목 공통 거래일 inner join.
- `_compute_portfolio_values(aligned_closes, weights, tickers)` L163: 첫날 1.0 정규화 가중 가치 시계열.
- `_apply_fx_rate` L126 / `_normalize_weights` L145: USD→KRW 환산·비중 정규화.
- **재사용 전략**: 034 차트의 포트폴리오 인덱스 산출에 030의 가치 시계열 산출을 재사용한다. 다만 차트는 일별 시계열을 그대로 반환해야 하므로(030은 최종 수익률만 반환), 034는 일별 정렬된 포트폴리오 가치 + 벤치마크 종가를 함께 100 기준 재기준화하는 신규 순수 함수가 필요하다.

### 2.4 베타 계산 — numpy 전용 (SPEC-027 `risk_analysis.py` 패턴)

- 모듈 상단 `@MX:NOTE: scipy 의존성 금지 — np.corrcoef, np.cov, np.std만 허용` (L4).
- `_daily_returns(closes)` L28: `(arr[1:]/arr[:-1]) - 1.0`.
- `np.cov(returns_matrix)` 사용 패턴 확인 (L146). **베타 = cov(port, bench) / var(bench)**는 `np.cov(port_returns, bench_returns)[0,1] / np.var(bench_returns, ddof=1)`로 scipy 없이 산출 가능.
- NaN/Inf 가드 + `math.isnan`/`math.isinf` 패턴(L100) 재사용.
- **20개 데이터 미만 시 None**: `risk_analysis._correlation_matrix`가 데이터 부족 시 0.0 반환하는 패턴과 유사하나, 034는 명시적으로 None 반환(REQ-BMK-005 / NFR-004).

### 2.5 소유권 검증 (404)

- `get_portfolio_with_holdings(db, portfolio_id, user_id)` (`service.py` L87) → None 시 신규 코드 관례상 `HTTP 404`.
- `performance_summary.calculate_performance_summary` L350~352, `dividend_yield.get_dividend_summary` L237~243 동일.
- **재사용 전략**: 034 서비스도 None → `HTTPException(status_code=404)`. 비소유 = 비존재 동일 응답(REQ-BMK-005, 소유권 정보 비노출).

### 2.6 라우터 엔드포인트 패턴

- 의존성: `Depends(get_current_user)` + `get_db_session` + `get_redis_client`.
- Query 파라미터: `Query(default=..., description="...")` (예: `performance-summary?refresh=`, `dividend/calendar?year=`).
- 응답: `response_model=` Pydantic 모델.
- **신규 경로**: `GET /{portfolio_id}/benchmark`, `GET /{portfolio_id}/benchmark/chart`. 기존 경로와 충돌 없음(접두사 `benchmark` 신규).

### 2.7 스키마 패턴

- `schemas.py`: Pydantic v2, `BaseModel`, `ConfigDict(from_attributes=True)`, `Optional`, `date`/`datetime` import 존재(L2~11).
- 기능별 스키마를 파일 하단에 SPEC 주석과 함께 append하는 관행(L6).

---

## 3. 마이그레이션 현황

- 최신 리비전: `0021_rebalancing_plans.py` (`revision="0021"`, `down_revision="0020"`).
- 0019=해외자산(SPEC-028), 0020=포트폴리오 알림(SPEC-031), 0021=리밸런싱(SPEC-032).
- SPEC-033(배당 수익률)은 **마이그레이션 미도입**(Redis 캐시). SPEC-034도 동일하게 **신규 테이블·마이그레이션 없음** — 벤치마크 데이터는 yfinance 온디맨드 조회 + (선택) Redis 캐시.

---

## 4. 벤치마크 심볼 매핑

| 입력 코드 | yfinance 심볼 | 설명 |
|-----------|---------------|------|
| `KOSPI` | `^KS11` | 코스피 종합지수 |
| `KOSDAQ` | `^KQ11` | 코스닥 종합지수 |
| `SP500` | `^GSPC` | S&P 500 |
| `NASDAQ` | `^IXIC` | 나스닥 종합지수 |

- 통화: KOSPI/KOSDAQ은 KRW 환산 불필요(지수는 포인트). 포트폴리오 수익률·벤치마크 수익률은 모두 **수익률(%)**로 비교하므로 통화 환산 불필요(비율 비교). 차트 인덱스도 100 기준 재기준화이므로 통화 무관.
- **설계 노트**: 포트폴리오 가치 시계열은 USD 종목을 KRW 환산(SPEC-030 관행)하여 산출하지만, 최종 비교 지표는 수익률·인덱스이므로 벤치마크와 통화 단위가 달라도 비교 가능(둘 다 무차원 비율).

---

## 5. scipy 금지 확인 (NFR-001)

- `risk_analysis.py`·`performance_summary.py`·`backtest.py` 모두 `import numpy as np` + `import math`만 사용. scipy import 없음(grep 확인).
- 베타·알파·수익률 모두 numpy(`np.cov`, `np.var`) + math(`math.pow`)로 충족 가능. **scipy.stats 불필요**.

---

## 6. 알파·베타 산출식 (설계 확정)

### 기간 수익률
```
return_pct = (value_end / value_start - 1) × 100
```
- 포트폴리오: 030 가치 시계열의 첫날/마지막날.
- 벤치마크: 지수 종가의 기간 시작/종료.

### 초과수익 (excess return)
```
excess_return_pct = portfolio_return_pct - benchmark_return_pct
```

### 알파 (연환산 초과수익)
```
ann_port = (1 + total_port/100)^(252/n_days) - 1
ann_bench = (1 + total_bench/100)^(252/n_days) - 1
alpha = (ann_port - ann_bench) × 100    # %p
```
- 단순화 알파(CAPM 무위험수익률 미반영). 요청서 명시: "annualized portfolio return - annualized benchmark return".

### 베타 (numpy)
```
beta = cov(port_daily_returns, bench_daily_returns) / var(bench_daily_returns)
     = np.cov(p, b)[0,1] / np.var(b, ddof=1)
```
- 일별 수익률 시리즈 길이 < 20 → None.
- `var(bench)=0`(벤치마크 무변동) → None(0 나눗셈 가드).

---

## 7. 차트 재기준화 (rebase to 100)

```
portfolio_index[t] = portfolio_value[t] / portfolio_value[0] × 100
benchmark_index[t] = benchmark_close[t] / benchmark_close[0] × 100
```
- 공통 거래일 inner join 후 각각 첫날 종가/가치를 100으로 정규화.
- 벤치마크 데이터 없는 날짜/기간 → `benchmark_index = None`(REQ-BMK-005).

---

## 8. 순수 함수 분리 전략 (NFR-002)

| 순수 함수 | 입력 | 출력 | DB/네트워크 |
|-----------|------|------|-------------|
| `calculate_benchmark_comparison(portfolio_history, benchmark_history, period)` | 가치/종가 시계열 + 기간 | `BenchmarkComparison` | 없음 |
| `calculate_benchmark_chart(portfolio_history, benchmark_history, period)` | 가치/종가 시계열 + 기간 | `list[BenchmarkChartPoint]` | 없음 |
| `calculate_beta(portfolio_daily_returns, benchmark_daily_returns)` | 일별 수익률 두 시리즈 | `Optional[float]` | 없음 |

- 서비스 오케스트레이션이 소유권·가격·FDR 조회를 담당하고, 시계열을 파라미터로 주입(030/027 패턴 일관).

---

## 9. 리스크·주의사항

- **포트폴리오 가치 시계열 일별 보존**: 030의 `_compute_portfolio_values`는 일별 시계열을 반환하지만, 030 서비스는 첫/마지막만 사용한다. 034 차트·베타는 일별 전체가 필요하므로 서비스에서 일별 시계열을 그대로 전달해야 한다.
- **포트폴리오 vs 벤치마크 거래일 정렬**: 한국/미국 휴장일이 달라 공통 거래일이 줄 수 있다. inner join 후 길이로 베타 20개 임계 판정.
- **빈 포트폴리오**: holdings 없음 → 포트폴리오 수익률 None, 벤치마크만 반환하거나 전체 None(acceptance에서 정의).
- **FDR 지수 심볼 지원**: `^KS11` 등은 FDR이 yfinance로 위임. 실패 가능성 있으므로 None graceful degradation 필수.
- **프론트 .js/.ts 쌍**: `portfolio.js`+`.ts`, `Portfolio.js`+`.tsx` 동시 수정 관례.

---

## 10. 결론 — SPEC 설계 방향

1. 신규 모듈 `portfolio/benchmark.py`: 순수 함수 3종 + 서비스 오케스트레이션 2종(comparison/chart).
2. SPEC-030 기간 헬퍼·가치 시계열, SPEC-027 numpy 패턴, SPEC-028 환산 재사용.
3. 신규 스키마 4종: `BenchmarkPeriodReturn`(요청서 명시, 다기간 확장 여지)·`BenchmarkComparison`·`BenchmarkChartPoint`·`BenchmarkChartData`.
4. 신규 엔드포인트 2종: `/benchmark`, `/benchmark/chart`.
5. REQ 접두사 `REQ-BMK-*`(BenchMarK) — 기존 접두사(OPT/RISK/FA/PBT/PS/PAL/RBA/DVY)와 충돌 없음.
6. 마이그레이션·DB 테이블 없음. scipy 없음. 소유권 404.
