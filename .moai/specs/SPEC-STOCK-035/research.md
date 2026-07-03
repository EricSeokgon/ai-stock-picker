# SPEC-STOCK-035 연구 노트 — 포트폴리오 성과 리포트 자동 생성

> 코드베이스 분석 산출물. 신규 구현 전 기존 구조·재사용 지점·충돌 회피 지점을 정리한다.

## 1. 목표 요약

SPEC-035는 포트폴리오 성과를 **다운로드 가능한 리포트**(CSV/JSON)로 자동 생성한다. SPEC-030(기간별 성과)·033(배당 수익률)·034(벤치마크 비교)가 산출하는 데이터를 **집계·직렬화**하는 통합 레이어이며, 신규 지표를 계산하지 않는다. 추가로 월별 스냅샷을 DB에 영속화한다(신규 테이블 0022).

## 2. 재사용 대상 (기존 자산)

### 2.1 성과 요약 — `portfolio/performance_summary.py` (SPEC-030)

- `calculate_performance_summary(portfolio_id, user_id, db, redis, refresh)` → `PerformanceSummaryResponse`.
  - 5개 표준 기간(ytd/1m/3m/6m/1y) `PeriodPerformance` 목록 반환. 필드: `total_return_pct`, `annualized_return_pct`, `mdd_pct`, `trading_days`, `has_data`.
  - 소유권 미일치 시 `HTTPException(404)`.
- 재사용 헬퍼: `_compute_period_dates(today)`, `_align_close_series`, `_compute_portfolio_values`, `_normalize_weights`, `_compute_period_returns`.
- 커스텀 날짜 범위 산출에 `_fetch_price_series_for_period`(asyncio executor 래핑) + `_compute_period_returns` 조합 재사용 가능.

### 2.2 배당 요약 — `portfolio/dividend_yield.py` (SPEC-033)

- `get_dividend_summary(portfolio_id, user_id, db, redis)` → `DividendSummary`(스키마 line 439).
  - 필드: `total_portfolio_value`, `total_annual_dividend`, `portfolio_dividend_yield_pct`, `holdings: list[DividendHolding]`.
- 리포트 JSON 요약에 `Optional[DividendSummary]`로 임베드. 소유권 404는 035 서비스가 먼저 검증하므로 035 호출 시점엔 이미 통과 상태.

### 2.3 벤치마크 비교 — `portfolio/benchmark.py` (SPEC-034)

- `get_benchmark_comparison_service(portfolio_id, benchmark, period, user_id, db)` → `BenchmarkComparison`(스키마 line 515).
  - 필드: `portfolio_return_pct`, `benchmark_return_pct`, `excess_return_pct`, `alpha`, `beta`.
- 리포트 JSON 요약에 `Optional[BenchmarkComparison]`로 임베드. `benchmark` 미지정 시 생략(None) 가능.

### 2.4 보유 종목 + 가격 — `portfolio/service.py`

- `get_portfolio_with_holdings(db, portfolio_id, user_id)` → 소유권 확인 + holdings 로드. None → 404 관례.
- `calculate_performance(db, portfolio_id, user_id, redis)` → holdings별 `current_price`(KRW), `return_pct`, `market`, `currency`, `fx_rate_used`, `total_invested`, `total_current` 산출.
  - **이 함수가 HoldingReportRow의 거의 모든 입력을 이미 제공**한다: `avg_buy_price`, `current_price`(KRW 환산), `quantity`, `krx_code`. P&L 금액·비중은 단순 파생.
- 해외 자산: `_fetch_foreign_price(ticker, redis)`(USD) × `fx_rate.get_usd_krw_rate(redis)` → KRW.

### 2.5 라우터 패턴 — `portfolio/router.py`

- `router = APIRouter(prefix="/portfolios", tags=["portfolios"])`.
- 의존성: `Depends(get_db_session)`(동기 Session), `Depends(get_current_user)`, `Depends(get_redis_client)`(aioredis).
- 쿼리 파라미터: `Query(...)` 사용(예: `period`, `benchmark` 기본값 패턴은 034 참조).
- 동기 Session 패턴 유지, 내부 서비스는 async. 엔드포인트는 `async def`.

## 3. CSV 스트리밍 (신규 패턴)

- 표준 라이브러리만 사용(NFR-002): `io.StringIO` + `csv` 모듈. 외부 CSV 라이브러리 미도입.
- FastAPI `StreamingResponse`(`fastapi.responses`) + `media_type="text/csv"` + `Content-Disposition: attachment; filename=...`.
- CSV 헤더(한국어): `종목코드,종목명,수량,평균단가(KRW),현재가(KRW),평가손익(KRW),수익률(%),비중(%)`.
- BOM 고려: 한국어 Excel 호환을 위해 UTF-8 BOM(`﻿`) 프리픽스 권장(접근 방식 노트로 명시).

## 4. DB 마이그레이션 (0022 — 신규)

- 최신 리비전 확인: `0021_rebalancing_plans.py`(SPEC-032). 035는 **0022**.
- 신규 테이블 `portfolio_monthly_snapshots`:
  - `id`(PK, autoincrement), `portfolio_id`(FK → portfolios.id, CASCADE), `month` VARCHAR(7) "YYYY-MM", `total_value_krw` FLOAT, `total_return_pct` FLOAT nullable, `holding_count` INT, `created_at` TIMESTAMPTZ server_default now().
  - **Unique 제약**: `(portfolio_id, month)` — 동일 월 중복 방지(NFR-004 upsert).
- 모델 패턴: `db/models.py`의 `RebalancingPlan`(line 744)·`PortfolioAlert`(UniqueConstraint line 688) 참조. `Base` 상속, `__table_args__`에 `UniqueConstraint(...)`.
- **JSON 컬럼 불필요**: 스냅샷은 평탄 스칼라 필드만 — Text+JSON 직렬화 관례 무관(단, 마이그레이션은 SQLite 테스트 호환 위해 `sa.Float`/`sa.Integer`/`sa.String(7)` 사용).
- Upsert 전략: SQLite 테스트 호환을 위해 `(portfolio_id, month)`로 SELECT 후 존재 시 UPDATE, 없으면 INSERT(DB-중립 upsert). `ON CONFLICT` 방언 의존 회피.

## 5. 스키마 (신규 — `portfolio/schemas.py` 추가)

- `HoldingReportRow`: ticker, name, quantity(float), avg_cost, current_price, pnl_amount, pnl_pct, weight_pct.
- `PortfolioReportSummary`: portfolio_id, generated_at(datetime), period, total_value_krw, total_return_pct, mdd_pct(Optional), holdings(list[HoldingReportRow]), dividend_summary(Optional[DividendSummary]), benchmark(Optional[BenchmarkComparison]).
- `MonthlySnapshot`: id, portfolio_id, month, total_value_krw, total_return_pct(Optional), holding_count, created_at. `ConfigDict(from_attributes=True)`(ORM 직렬화).
- 명명 충돌 없음: 030/033/034 스키마와 분리(`Report*`/`MonthlySnapshot` 접두).

## 6. 순수 함수 분리 (NFR-003)

- `generate_holding_report_rows(holdings, prices, fx_rates, total_value_krw)` → `list[HoldingReportRow]`. DB/네트워크 없이 입력만으로 결정적.
- `generate_csv_content(rows)` → `str`. `io.StringIO` + `csv.writer`.
- 서비스가 소유권·가격·DB 저장을 주입하고 순수 함수를 호출(risk_analysis.py 모범 패턴).

## 7. 충돌·중복 회피 점검 (브라운필드)

- **기존 리포트 기능 없음**: `grep`으로 CSV/StreamingResponse/report 엔드포인트 부재 확인 — 035가 최초 도입.
- **performance 데이터 중복 산출 회피**: 035는 030/033/034 서비스를 **호출**해 결과를 집계하며, 수익률·MDD·알파·베타를 재계산하지 않는다(§제외).
- **엔드포인트 경로 충돌 없음**: `/report`, `/report/summary`, `/report/snapshot`, `/report/snapshots` — 기존 경로(`/performance`, `/performance-summary`, `/benchmark`, `/dividends`)와 분리.
- **REQ 접두사**: `REQ-RPT-*`(RePorT) — 기존(OPT/RISK/FA/PBT/PS/PAL/RBA/DVY/BMK)과 충돌 없음.

## 8. 프론트엔드 (`.js`/`.ts` 쌍 관례)

- `frontend/src/api/portfolio.js`(+`.ts`): `apiDownloadReport`(blob), `apiGetReportSummary`, `apiCreateSnapshot`, `apiGetSnapshots`.
- `frontend/src/components/PortfolioReportPanel.js`: 리포트 다운로드 버튼(CSV) + JSON 요약 카드 + 스냅샷 목록.
- `frontend/src/pages/Portfolio.js`(+`.tsx`): 리포트 섹션 통합(기존 섹션 보존).

## 9. NFR-005 (성능 — 5초 이내, 50종목)

- CSV 생성 자체는 순수 함수로 마이크로초 단위. 병목은 가격 조회(FDR/현재가). 030/034 서비스가 이미 asyncio.gather 병렬 조회를 사용하므로 50종목도 5초 이내 가능.
- 리포트 JSON 요약은 030/033/034 서비스 결과 집계 — 각 서비스의 Redis 캐시 재사용으로 반복 호출 비용 절감.

## 10. MX 태그 계획 후보

- `@MX:ANCHOR`: `generate_holding_report_rows`·`PortfolioReportSummary`(서비스·router·테스트 fan_in ≥ 3).
- `@MX:NOTE`: CSV 표준 라이브러리 전용(외부 CSV 라이브러리 금지)·UTF-8 BOM 사유.
- `@MX:WARN`: 월별 스냅샷 upsert(DB-중립 SELECT-then-write, 동시성 주의).
