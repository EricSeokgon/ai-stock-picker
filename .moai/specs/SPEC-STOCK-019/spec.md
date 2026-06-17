---
id: SPEC-STOCK-019
version: 0.1.0
status: draft
created: 2026-06-15
updated: 2026-06-15
author: ircp
priority: medium
issue_number: null
---

# SPEC-STOCK-019 — 배당 포트폴리오 분석 (Phase 19)

## HISTORY

- 2026-06-15 (v0.1.0): 최초 작성. 사용자 포트폴리오를 배당 투자 관점에서 분석.
  보유 종목별 배당 지표(DPS·배당수익률·배당기준일)·연간 예상 배당 수익·가중 평균 수익률·
  배당 캘린더(월별 지급 예상)·전년 대비 DPS 성장 추세 제공. 신규 엔드포인트
  `GET /portfolios/{portfolio_id}/dividends`. 신규 백엔드 모듈 `portfolio/dividends.py`.
  **신규 DB 테이블·마이그레이션 없음** — 배당 데이터는 보유 종목 단위로 실시간 조회 후
  Redis 캐시(TTL 86400s). 데이터 출처 = FinanceDataReader 베스트에포트.

---

## 1. 개요 (Overview)

### 1.1 문제 정의

현재 ai-stock-picker의 포트폴리오 기능은 성과 분석(SPEC-STOCK-017, `GET /portfolios/{id}/performance`:
수익률·분류·섹터)과 AI 분석(`POST /portfolios/{id}/ai-analysis`: 분산투자·리스크·제안)만 제공한다.
**배당 투자(income investing) 관점의 분석이 전무하다.** 인컴 중심 투자자는 다음을 알고 싶어 한다:

- 보유 종목 각각이 얼마의 배당을 주는가 (주당 배당금 DPS, 배당수익률)
- 포트폴리오 전체에서 연간 예상으로 받게 될 배당 수익 (보유 수량 × DPS 합계)
- 어느 달에 배당이 들어오는가 (배당 캘린더)
- 보유 종목의 배당이 늘고 있는가, 줄고 있는가 (DPS 성장 추세)

### 1.2 목표

보유 포트폴리오를 배당 관점에서 한눈에 보여 주는 분석 API와 프론트 UI를 추가한다.

### 1.3 비자명 코드베이스 사실 (설계 근거)

- **`stock_fundamentals.dividend_yield`(%) 컬럼은 존재하나(SPEC-018, 마이그 0016) 적재 생산자가
  코드베이스에 없다.** SPEC-018의 일일 펀더멘털 수집 잡(M2)은 `progress.md`에서 `DEFERRED` 상태이며,
  "별도 SPEC(SPEC-STOCK-019) 또는 운영 환경 연동 시 구현 예정"으로 명시되어 있다.
  → 본 SPEC은 이 비어 있는 테이블에 의존하지 않는다. SPEC-018 M2(전체 KRX 유니버스 일일 수집 잡)는
    **본 SPEC 범위 밖**이며, 본 SPEC은 보유 종목(통상 수십 개)에 한해 **실시간 조회**한다.
- **DPS(주당 배당금, 원 단위)·배당기준일·지급월 데이터를 저장하는 곳이 코드베이스에 전혀 없다.**
  `stock_fundamentals`에는 `dividend_yield`(%)만 있고 DPS/기준일/지급월은 없다.
- 의존성은 `finance-datareader>=0.9`만 존재한다. **`pykrx`는 의존성에 없다.** 본 SPEC은
  신규 데이터 공급자를 추가하지 않는다.
- 시세/히스토리 조회 패턴(`mapping/prices.py`)은 `run_in_executor`로 동기 FDR 격리 +
  `redis.asyncio` 캐시 + 장애 시 빈 결과 graceful degradation을 사용한다. 배당 조회도 이 패턴을 재사용한다.
- 포트폴리오 소유권 확인은 `service.get_portfolio_with_holdings(db, portfolio_id, user_id)`로 수행하며
  타 사용자/미존재 시 404를 반환한다(`GET /performance`와 동일 패턴).

---

## 2. 설계 결정 (Design Decisions)

### 2.1 데이터 출처와 가용성 (핵심)

배당 데이터의 한국 시장 구조적 한계를 정직하게 반영한다:

| 지표 | 출처 | 가용성 |
|------|------|--------|
| 배당수익률 (배당수익률, %) | FinanceDataReader 베스트에포트 | 부분적 — 없으면 N/A |
| 주당 배당금 (DPS, 원) | FinanceDataReader 베스트에포트 (직전 회계연도) | 부분적 — 없으면 N/A |
| 배당기준일 (배당기준일) | FinanceDataReader 베스트에포트 | 흔히 없음 — 없으면 N/A |
| 지급 예상 월 (배당 캘린더) | 배당기준일에서 파생, 미상 시 한국 일반 가정 | **베스트에포트 / 미상 다수** |
| DPS 성장 추세 (전년 대비) | FDR 다년 DPS 확보 시 | 다년 데이터 없으면 N/A |

- **한국 배당 일반 가정**: 대부분의 국내 종목은 12월 결산 → 연 1회 배당, 익년 4월 전후 실지급.
  일부 종목은 분기/반기 배당. 본 SPEC은 배당기준일을 확보하면 그 월을 사용하고, 확보하지 못하면
  지급월을 "미상"으로 표기한다. **추정 지급월을 단정적으로 단언하지 않는다.**

### 2.2 영속화 전략

- **신규 DB 테이블·마이그레이션 없음.** 마이그레이션은 0016에 머문다.
- 배당 데이터는 종목 코드별로 Redis 캐시한다: 키 `dividends:{krx_code}`, TTL 86400s(1일).
- 캐시 미스 시 FDR 베스트에포트 조회 → 결과(또는 N/A 마커)를 캐시에 저장.
- 조회 범위는 포트폴리오 보유 종목으로 한정(통상 < 50 코드)되어 실시간 조회가 현실적이다.

### 2.3 엔드포인트

- 신규: `GET /portfolios/{portfolio_id}/dividends` (인증 필요, 소유권 404).
- **기존 `POST /portfolios/{portfolio_id}/ai-analysis`는 일절 수정하지 않는다.**
- 신규 서비스 모듈 `portfolio/dividends.py`(기존 `portfolio/ai_analysis.py`와 형제).
- 응답 스키마는 `portfolio/schemas.py`에 추가.

---

## 3. 데이터 모델 (Data Model)

신규 ORM 모델 없음. 응답 전용 Pydantic v2 스키마만 추가한다(`portfolio/schemas.py`).

```
HoldingDividend
- krx_code: str
- name: str | None
- quantity: int
- dps: float | None              # 주당 배당금(원), 직전 회계연도
- dividend_yield: float | None   # 배당수익률(%)
- ex_dividend_date: str | None   # 배당기준일 "YYYY-MM-DD", 없으면 None
- payment_month: int | None      # 지급 예상 월(1~12), 미상 시 None
- annual_income: float           # quantity × dps (dps 없으면 0.0)
- yoy_dps_change_pct: float | None  # 전년 대비 DPS 증감률(%), 다년 미확보 시 None
- dividend_available: bool        # dps 또는 yield 중 하나라도 있으면 true

DividendCalendarMonth
- month: int                      # 1~12
- holdings: list[str]             # 해당 월 지급 예상 종목명(또는 코드)
- total_income: float             # 해당 월 예상 배당 수익 합계

PortfolioDividends
- holdings: list[HoldingDividend]
- total_annual_income: float      # 모든 보유의 annual_income 합계
- weighted_avg_yield: float       # 투자금 가중 평균 배당수익률(%)
- calendar: list[DividendCalendarMonth]  # 12개월 그리드(지급월 미상 종목은 캘린더 제외)
- coverage_count: int             # dividend_available=true 인 보유 수
- total_holdings: int             # 전체 보유 수
```

---

## 4. 요구사항 (EARS Requirements)

### 4.1 보유 종목별 배당 데이터 (REQ-DIV-*)

- REQ-DIV-001 (Ubiquitous): The system shall provide, for each holding in a portfolio, its annual
  dividend per share (DPS, in KRW), dividend yield (%), and ex-dividend date when available.
- REQ-DIV-002 (Event-Driven): WHEN dividend data for a holding is requested, the system shall return
  per-share dividend (DPS), dividend yield, and ex-dividend date sourced from FinanceDataReader on a
  best-effort basis.
- REQ-DIV-003 (State-Driven): WHILE a holding has no available dividend data, the system shall set its
  DPS, dividend yield, ex-dividend date, and payment month to N/A (null) and mark
  `dividend_available = false`.
- REQ-DIV-004 (Ubiquitous): The system shall compute each holding's estimated annual dividend income as
  `quantity × DPS`, and shall treat a holding with no DPS as contributing 0 to annual income.

### 4.2 포트폴리오 배당 요약 (REQ-DIV-*)

- REQ-DIV-010 (Ubiquitous): The system shall compute the portfolio's total estimated annual dividend
  income as the sum of all holdings' estimated annual income.
- REQ-DIV-011 (Ubiquitous): The system shall compute a weighted average dividend yield across holdings,
  weighted by each holding's invested amount (`quantity × avg_buy_price`).
- REQ-DIV-012 (State-Driven): WHILE no holding has available dividend data, the system shall return a
  total annual income of 0 and a weighted average yield of 0.
- REQ-DIV-013 (Ubiquitous): The system shall report dividend data coverage as the count of holdings with
  `dividend_available = true` against the total holding count.

### 4.3 배당 캘린더 (REQ-DIV-*)

- REQ-DIV-020 (Ubiquitous): The system shall produce a monthly dividend calendar (12 months) indicating
  in which months distributions are expected for the portfolio's holdings.
- REQ-DIV-021 (Event-Driven): WHEN a holding's ex-dividend date is available, the system shall derive its
  expected payment month from that date.
- REQ-DIV-022 (State-Driven): WHILE a holding's payment month cannot be determined, the system shall
  exclude that holding from the monthly calendar and shall not assert a guessed payment month.
- REQ-DIV-023 (Ubiquitous): The system shall, for each calendar month, list the contributing holdings and
  the sum of their estimated income in that month.

### 4.4 배당 성장 추세 (REQ-DIV-*)

- REQ-DIV-030 (Event-Driven): WHEN multi-year DPS history is available for a holding, the system shall
  compute its year-over-year DPS change as a percentage.
- REQ-DIV-031 (State-Driven): WHILE multi-year DPS data is unavailable for a holding, the system shall set
  its year-over-year DPS change to N/A (null).

### 4.5 API (REQ-DIV-API-*)

- REQ-DIV-API-001 (Event-Driven): WHEN a client sends `GET /portfolios/{portfolio_id}/dividends` with a
  valid bearer token, the system shall return the dividend analysis for all holdings of that portfolio.
- REQ-DIV-API-002 (Unwanted): IF the requested portfolio does not exist or is not owned by the
  authenticated user, THEN the system shall respond with HTTP 404.
- REQ-DIV-API-003 (Unwanted): IF the request has no valid authentication, THEN the system shall respond
  with HTTP 401.
- REQ-DIV-API-004 (Event-Driven): WHEN dividend data for a holding is fetched, the system shall cache the
  result in Redis under key `dividends:{krx_code}` with a TTL of 86400 seconds and serve subsequent
  requests within the TTL from cache.
- REQ-DIV-API-005 (Unwanted): IF Redis is unavailable, THEN the system shall fall back to a fresh
  FinanceDataReader fetch and shall not fail the request.
- REQ-DIV-API-006 (State-Driven): WHILE a portfolio has no holdings, the system shall return an empty
  holdings list, zero totals, and an empty calendar.

### 4.6 프론트엔드 (REQ-DIV-FE-*)

- REQ-DIV-FE-001 (Ubiquitous): The Portfolio page shall present a dividend section alongside the existing
  performance panel (SPEC-STOCK-017), without removing or altering the performance panel.
- REQ-DIV-FE-002 (Ubiquitous): The dividend section shall display a summary card with the estimated annual
  income and the weighted average yield.
- REQ-DIV-FE-003 (Ubiquitous): The dividend section shall display a 12-month dividend calendar grid showing
  contributing holdings and expected income per month.
- REQ-DIV-FE-004 (Ubiquitous): The dividend section shall display a per-holding table with columns: name,
  DPS, dividend yield, ex-dividend date, and annual income contribution.
- REQ-DIV-FE-005 (State-Driven): WHILE a holding has no dividend data, the table shall render N/A for its
  dividend fields.
- REQ-DIV-FE-006 (Event-Driven): WHEN dividend data is loading, the section shall show a loading state.

### 4.7 비기능 (REQ-DIV-NFR-*)

- REQ-DIV-NFR-001 (Unwanted): IF any feature would execute or schedule trades or orders, THEN it shall NOT
  be built — automated trading is permanently excluded.
- REQ-DIV-NFR-002 (Ubiquitous): The system shall use FinanceDataReader as its sole dividend data source,
  consistent with the screener data pattern, and shall not add a new data provider (e.g., pykrx).
- REQ-DIV-NFR-003 (Ubiquitous): The system shall cache dividend data in Redis with a 86400-second TTL,
  treating daily freshness as sufficient.
- REQ-DIV-NFR-004 (State-Driven): WHILE dividend data is unavailable for a stock, the system shall degrade
  gracefully by showing N/A rather than failing.
- REQ-DIV-NFR-005 (Ubiquitous): The dividend analysis response shall complete within 5 seconds for a
  portfolio of up to 50 holdings (cache-warm path).

---

## 5. Exclusions (What NOT to Build)

- **자동 매매·주문 실행** — 규제·책임 리스크로 영구 제외 (REQ-DIV-NFR-001).
- **전체 KRX 유니버스 일일 배당/펀더멘털 수집 잡** — SPEC-018 M2(DEFERRED)의 작업이며 본 SPEC 범위 밖.
  본 SPEC은 보유 종목 단위 실시간 조회만 한다.
- **신규 DB 테이블·마이그레이션** — 영속화 불필요(실시간 조회 + Redis 캐시). 마이그레이션 0016 유지.
- **신규 데이터 공급자(pykrx 등) 추가** — FDR 베스트에포트만 사용.
- **세후/원천징수 배당 계산** — 세전 기준만 제공.
- **배당 재투자(DRIP) 모델링·배당 재투자 백테스트.**
- **배당 기반 추천 재가중·스코어 반영** — 추천 산식(4요인)은 불변.
- **배당락/배당기준일 알림·인박스 연동** — Phase H 알림 시스템과 연동하지 않음.
- **`POST /portfolios/{portfolio_id}/ai-analysis` 수정** — 기존 AI 분석 엔드포인트는 손대지 않음.
- **지급월 단정** — 배당기준일 미확보 종목의 지급월을 추측해 단언하지 않음(캘린더에서 제외).

---

## 6. 영향 범위 (Affected Files)

### 신규
- `backend/src/stock_picker/portfolio/dividends.py` — 배당 분석 서비스(FDR 조회·Redis 캐시·집계).
- `backend/tests/unit/test_portfolio_dividends.py` — 서비스·라우터 테스트.
- `frontend/src/api/dividends.ts` — 배당 API 래퍼 + 타입.
- `frontend/src/__tests__/Dividends.test.tsx` — 프론트 테스트.

### 수정
- `backend/src/stock_picker/portfolio/router.py` — `GET /{portfolio_id}/dividends` 라우트 1개 추가.
- `backend/src/stock_picker/portfolio/schemas.py` — `HoldingDividend`·`DividendCalendarMonth`·
  `PortfolioDividends` 스키마 추가.
- `frontend/src/pages/Portfolio.tsx` — 성과 패널 옆 배당 섹션(요약 카드·캘린더·테이블) 추가.

### 불변
- `backend/src/stock_picker/portfolio/ai_analysis.py` 및 `POST /ai-analysis`.
- `backend/src/stock_picker/portfolio/service.py` `calculate_performance` 및 `/performance`.
- DB 스키마(마이그레이션 0016 유지).

---

## 7. 마일스톤 (Milestones)

| 마일스톤 | 설명 | 우선순위 |
|----------|------|----------|
| M1 | 배당 응답 스키마 추가 (`HoldingDividend`·`DividendCalendarMonth`·`PortfolioDividends`) | High |
| M2 | 배당 데이터 조회 (FDR 베스트에포트 + Redis 캐시 `dividends:{krx_code}` TTL 86400, prices.py 패턴 재사용, REQ-DIV-002·API-004·API-005) | High |
| M3 | 배당 집계 서비스 (`portfolio/dividends.py`: 종목별 income·가중평균 yield·캘린더·YoY, REQ-DIV-004·010~031) | High |
| M4 | 라우터 (`GET /portfolios/{id}/dividends`, 인증·소유권 404, REQ-DIV-API-001~003·006) | High |
| M5 | 프론트 배당 섹션 (요약 카드·캘린더 그리드·종목 테이블·N/A·로딩, REQ-DIV-FE-*) | Medium |
| M6 | 테스트 & 품질 게이트 (커버리지 ≥85%, graceful degradation·소유권·빈 포트폴리오 케이스) | High |

---

## 8. 위험 (Risks)

- **데이터 빈약**: FDR이 국내 종목 DPS/배당기준일을 안정적으로 주지 못할 수 있음 → 다수 종목이 N/A로
  표시될 수 있다. 완화: 모든 필드 nullable·`dividend_available` 마커·coverage 표시로 정직하게 노출.
- **지급월 부정확**: 배당기준일에서 파생한 지급월이 실제 지급월과 다를 수 있음 → 미상 종목은 캘린더에서
  제외(추측 단언 금지)로 완화.
- **SPEC-018 의존 혼동**: `stock_fundamentals.dividend_yield`가 비어 있음. 본 SPEC은 그 테이블을
  읽지 않고 독립적으로 실시간 조회하므로 018 M2 완료 여부와 무관하게 동작한다.
