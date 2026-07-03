# SPEC-STOCK-034 압축 참조 (Compact) — 포트폴리오 벤치마크 비교

> run 단계 토큰 절약용 압축본. 전체는 [spec.md](spec.md)·[acceptance.md](acceptance.md)·[plan.md](plan.md) 참조.

## 목표
포트폴리오 기간 수익률(SPEC-030)을 시장 벤치마크(KOSPI/KOSDAQ/SP500/NASDAQ)와 비교 → 초과수익·알파·베타·재기준화 차트.

## REQ 요약 (REQ-BMK-*)
- 001: 벤치마크 지수 기간 가격 조회 → 벤치마크 수익률.
- 002: 포트폴리오·벤치마크 수익률 + 초과수익(port − bench).
- 003: 알파=연환산(port−bench), 베타=cov(p,b)/var(b).
- 004: 차트 = 기간 시작 100 재기준화 시계열(포트폴리오·벤치마크).
- 005: 비소유 → 비존재 동일(404). 벤치마크 데이터 없으면 None graceful.

## NFR
- 001 scipy 금지(numpy+math). 002 순수 함수(DB/네트워크 무). 003 graceful None. 004 베타 일별 ≥20개(미만 None). 005 커버리지 85%+.

## 벤치마크 심볼
KOSPI→^KS11 / KOSDAQ→^KQ11 / SP500→^GSPC / NASDAQ→^IXIC

## 신규 모듈 `portfolio/benchmark.py`
순수 함수:
- `calculate_benchmark_comparison(portfolio_history, benchmark_history, period) -> BenchmarkComparison`
- `calculate_benchmark_chart(portfolio_history, benchmark_history, period) -> list[BenchmarkChartPoint]`
- `calculate_beta(portfolio_daily_returns, benchmark_daily_returns) -> Optional[float]` # <20 또는 var=0 → None
서비스 2종: 소유권 404 → 030 기간헬퍼·가치시계열 재사용 → 벤치마크 FDR(`^심볼`) run_in_executor 조회 → 순수 함수 호출.

## 산출식
- 기간수익률 = (v[-1]/v[0]−1)×100
- excess = port − bench (bench None → None)
- 연환산 ann = (1+total/100)^(252/n)−1; alpha=(ann_p−ann_b)×100
- beta = np.cov(p,b)[0,1] / np.var(b,ddof=1); NaN/Inf/<20/var0 → None
- index[t] = series[t]/series[0]×100 (첫 시점 100)

## 스키마 (schemas.py 하단 추가)
`BenchmarkPeriodReturn`, `BenchmarkComparison`(portfolio_id/benchmark/period/portfolio_return_pct/benchmark_return_pct?/excess_return_pct?/alpha?/beta?/calculated_at), `BenchmarkChartPoint`(date/portfolio_index/benchmark_index?), `BenchmarkChartData`(portfolio_id/benchmark/period/chart).

## 엔드포인트 (router.py)
- `GET /{portfolio_id}/benchmark?benchmark=KOSPI&period=YTD` → BenchmarkComparison
- `GET /{portfolio_id}/benchmark/chart?benchmark=KOSPI&period=YTD` → BenchmarkChartData
- Depends: get_current_user/get_db_session/get_redis_client. 소유권 404.

## 재사용 (수정 금지)
- 030 `_compute_period_dates`·`_compute_portfolio_values`·`_align_close_series`·연환산.
- 027 numpy 일별 수익률·NaN 가드. 028 `_fetch_foreign_price`·`fx_rate`. 029 `_fetch_price_series_sync`.

## 제약
scipy 금지 / 404(403 아님) / 마이그레이션 없음(최신 0021) / 패키지 portfolio/ / 주석·커밋 한국어 / .js+.ts 쌍 / EARS REQ에 함수명·HTTP코드·SQL·변수명 금지.

## 작업 (plan.md)
T-001 스키마 → T-002 베타 / T-004 차트 → T-003 비교 → T-005 서비스 → T-006 라우터 → T-007 프론트.

## MX 태그
ANCHOR(비교 순수함수·응답 스키마) / NOTE(모듈 상단 scipy금지·단순알파·통화무차원, 베타 분기) / WARN(동기 FDR run_in_executor) / TODO(RED). 한국어·[AUTO].
