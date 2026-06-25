# SPEC-STOCK-038 코드베이스 사전 조사 (Research)

> 작성일: 2026-06-25 · 대상 기능: 시장 시각화 대시보드 (Market Visualization Dashboard)
> 목적: 신규 SPEC이 기존 자산을 **재사용**하고 중복 구현을 피하도록 현행 코드 상태를 정리한다.

---

## 1. 결론 요약 (TL;DR)

- **Recharts ^2.14.1** 이미 `frontend/package.json`에 존재 → 신규 차트 라이브러리 추가 불필요.
- **벤치마크 비교 차트**는 SPEC-034가 이미 완전 구현 (`GET /portfolios/{id}/benchmark/chart`, 100 기준 재기준화 시계열) → **재사용**, 신규 백엔드 불필요.
- **포트폴리오 가치 시계열**의 원천은 SPEC-035의 `portfolio_monthly_snapshots` 테이블(**월별** 단위) → 신규 테이블 불필요. 단, **월별 granularity** 한계를 정직하게 노출해야 함.
- **섹터/자산유형 집계**의 원천은 `portfolio/service.py`의 보유 종목 상세(`get_sector`·`market`·`currency`·`return_pct`·평가액) → 신규 집계 엔드포인트가 이 데이터를 조합.
- **신규 DB 테이블·마이그레이션 없음**. 최신 마이그레이션 **0024** 유지.

---

## 2. 프론트엔드 현황

### 2.1 차트 라이브러리

`frontend/package.json` (line 17): `"recharts": "^2.14.1"`. React ^18.3.1. **Recharts 사용 가능 확정.**

### 2.2 기존 차트/시각화 컴포넌트 (`frontend/src/components/`)

| 컴포넌트 | 출처 | 시각화 |
|----------|------|--------|
| `PerformanceDonutChart.{js,tsx}` | 포트폴리오 | 도넛(파이) 차트 — 자산 구성 |
| `BenchmarkChartView.{js,tsx}` | SPEC-034 | 벤치마크 재기준화 라인 차트 |
| `BenchmarkComparisonPanel.{js,tsx}` | SPEC-034 | 벤치마크 수치 비교 패널 |
| `SectorTrendChart.{js,tsx}` | SPEC-008 | 섹터 트렌드(뉴스 기반, 포트폴리오 아님) |
| `RiskAnalysisPanel.{js,tsx}` | SPEC-027 | 상관관계 히트맵 |
| `BacktestChart.{js,tsx}` | 백테스트 | 시계열 라인 |
| `PriceChart.{js,tsx}` | 종목 상세 | 30일 가격 차트 |

> **재사용 가능**: `PerformanceDonutChart`(자산 배분 파이), `BenchmarkChartView`(성과 비교). 신규 컴포넌트는 가치 라인 차트·섹터 히트맵 중심.

### 2.3 포트폴리오 페이지 구조

- `frontend/src/pages/Portfolio.{js,tsx}` — 메인 포트폴리오 페이지. 다수 패널을 탭/섹션으로 렌더(점수카드·리밸런싱·리스크·백테스트·배당·벤치마크·리포트).
- **빌드 산출물 규약**: `.tsx`(소스) + `.js`(컴파일됨) **쌍으로 존재**. 신규 컴포넌트도 양쪽 파일을 생성/유지해야 한다.
- API 래퍼: `frontend/src/api/portfolio.{js,ts}`. 이미 존재하는 관련 함수:
  - `apiGetBenchmarkChart(token, portfolioId, benchmark, period)` (line 248)
  - `apiListMonthlySnapshots(token, portfolioId, limit)` (line 318)
  - `apiGetPerformanceSummary`, `apiGetRiskAnalysis` 등.

---

## 3. 백엔드 현황 (`backend/src/stock_picker/portfolio/`)

### 3.1 포트폴리오 가치 시계열 원천 — 월별 스냅샷 (SPEC-035)

- 테이블 `portfolio_monthly_snapshots` (마이그레이션 **0022**). 모델 `PortfolioMonthlySnapshot` (`db/models.py:783`).
  - 컬럼: `id`, `portfolio_id`(FK CASCADE), `month`(`String(7)` "YYYY-MM"), `total_value_krw`(Float), `total_return_pct`(Float nullable), `holding_count`(Int), `created_at`.
  - `(portfolio_id, month)` 사실상 UNIQUE — upsert는 SELECT-then-write.
- 엔드포인트:
  - `POST /portfolios/{id}/report/snapshot` — 현재 시점 스냅샷 upsert.
  - `GET /portfolios/{id}/report/snapshots?limit≤60` — 최신 월 우선 목록.
- **⚠️ 비자명 한계**: 스냅샷은 **월별**이다. 요청서의 가치 차트 기간(7d/30d/90d/365d)을 월별 데이터에 매핑하면 짧은 기간(7d/30d)은 데이터 포인트가 0~2개에 불과할 수 있다. SPEC은 "기존 스냅샷 데이터만 사용"을 준수하되, 가치 차트의 시간 해상도가 **월 단위**임을 정직하게 노출하고 빈/희소 상태를 명세한다. (일별 시계열 적재 잡은 본 SPEC 범위 밖 — 향후 별도 SPEC.)

### 3.2 벤치마크 비교 — SPEC-034 (재사용)

- `GET /portfolios/{id}/benchmark` → `BenchmarkComparison`(알파/베타/기간 수익률 비교).
- `GET /portfolios/{id}/benchmark/chart?benchmark=&period=` → `BenchmarkChartData{portfolio_id, benchmark, period, chart:[BenchmarkChartPoint{date, portfolio_index, benchmark_index}]}`.
  - **이미 100 기준 재기준화된 포트폴리오·벤치마크 시계열 제공.** period ∈ {YTD,1M,3M,6M,1Y}. benchmark ∈ {KOSPI,KOSDAQ,SP500,NASDAQ}.
- → **성과 비교 차트는 이 엔드포인트를 그대로 소비.** 신규 백엔드 불필요. 프론트는 `apiGetBenchmarkChart` 재사용.

### 3.3 보유 종목 상세 — 섹터/자산유형 집계 원천 (`service.py`)

- `get_portfolio_with_holdings(db, portfolio_id, user_id)` — 소유권 확인 + 보유 조회. **None 반환 시 라우터가 404로 변환**(403 아님).
- 보유 종목 성과 산출 루프(`service.py:240~285`)가 종목별로 다음을 생성:
  - `krx_code`, `quantity`, `avg_buy_price`, `current_price`, `return_pct`(%), `classification`, `sector`(`get_sector(krx_code)`), `price_unavailable`, `market`(KRX/NYSE/NASDAQ), `currency`(KRW/USD), `fx_rate_used`.
  - **섹터 집계 맵(`sector_map`)** 이미 존재: 섹터별 `invested`·`current` 합산. 섹터 미상 종목은 "해외" 키로 집계.
- `market` 필드(`PortfolioHolding.market`, SPEC-028): KRX(국내) / NYSE / NASDAQ(해외) → **자산유형(국내/해외) 분류 원천**.
- `get_sector(krx_code)` (`portfolio/utils.py:31`) — KRX 코드 앞 2자리 간이 섹터 매핑. ai_analysis·advice·service 3곳에서 호출 중인 공용 헬퍼.

### 3.4 라우터·인증 패턴 (`router.py`)

- prefix `/portfolios`(복수). 모든 보호 엔드포인트가 `Depends(get_current_user)`.
- **소유권 위반 시 404 반환**(`get_portfolio_with_holdings` None → `HTTPException(status_code=404)`). 403 사용 금지 — 본 SPEC도 404 패턴 준수.
- 캐싱: `api/deps.py`의 `get_redis_client`(redis.asyncio), 키 예: `portfolio_risk:{id}:{period}:{date}` TTL3600. 대시보드 집계도 동일 패턴 적용 가능.

---

## 4. 계산 제약 (프로젝트 공통)

- **scipy 금지** (REQ-RISK-NFR-001 등 선례). numpy + math만 허용. `numpy>=1.26`·`finance-datareader>=0.9`는 이미 `pyproject.toml`에 존재.
- 순수 함수 분리 선례: `risk_analysis.py`·`backtest.py`·`performance_summary.py` 모두 DB/외부 API 없이 테스트 가능한 핵심 계산 함수를 분리.
- 코드 주석·커밋 메시지: **한국어**.

---

## 5. SPEC-038 설계 결정 (조사 기반)

| 요청 기능 | 데이터 원천 | 신규 여부 |
|-----------|-------------|-----------|
| (1) 가치 시계열 차트 | `portfolio_monthly_snapshots` (월별) | 집계 엔드포인트 신규(테이블 재사용). **월 단위 해상도 한계 명세.** |
| (2) 섹터 히트맵 | `service.py` 보유 상세 sector_map + return_pct | 집계 엔드포인트 신규 |
| (3) 자산유형 배분 | 보유 `market`/`currency` | 집계 엔드포인트 신규 |
| (4) 벤치마크 비교 | `GET /benchmark/chart` (SPEC-034) | **재사용** — 신규 백엔드 없음 |
| (5) 대시보드 UI | 위 4종 + Recharts | 신규 프론트(페이지+컴포넌트) |
| (6) 기간 선택 7d/30d/90d/365d | 서버측 검증 | 신규(파라미터 검증) |
| (7) 빈 상태 | — | 신규 UI/응답 명세 |
| (8) 로딩 상태 | — | 신규 UI |
| (9) 소유권 404 | `get_portfolio_with_holdings` | **재사용 패턴** |

- **신규 DB 테이블·마이그레이션 없음** (최신 0024 유지).
- REQ 접두사 `REQ-DASH-*` — 기존 접두사(OPT/RISK/FA/PBT/PS/PAL/RBA/DVY/BMK/RPT)와 충돌 없음.
