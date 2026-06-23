# SPEC-STOCK-033 연구 노트 — 배당 수익률 분석 (Dividend Yield Analysis)

> Plan Phase 연구 산출물. 코드베이스 심층 분석 + 기존 SPEC-019 중복 평가 + 설계 결정 근거.

## 0. 핵심 발견 — SPEC-019와의 중복 (반드시 먼저 읽을 것)

이 프로젝트에는 **이미 배당 분석 기능이 SPEC-STOCK-019로 구현되어 있다.** 요청서의 REQ-DVY-001/002/003은 대부분 SPEC-019가 이미 충족한다. SPEC-033을 그대로 신규 구현하면 중복·충돌이 발생한다.

| 요청서 요구 | SPEC-019 기존 구현 | 중복 여부 |
|------------|-------------------|----------|
| REQ-DVY-001 종목별 연 배당 추정 | `dividends._fetch_dividend_info` → DPS, `HoldingDividend.annual_income = quantity × dps` | **이미 존재** |
| REQ-DVY-002 포트폴리오 가중 평균 수익률 | `PortfolioDividends.weighted_avg_yield` (투자금 가중) | **이미 존재** |
| REQ-DVY-003 배당 캘린더 | `DividendCalendarMonth` (월별 그룹, `ex_dividend_month` 1~12) | **부분 중복** (월 단위만, 날짜·지급일 없음) |
| REQ-DVY-004 DRIP 재투자 시뮬레이션 | **없음** | **완전 신규** |
| REQ-DVY-005 소유권 확인 | `get_portfolio_with_holdings` None → 404 | **이미 존재(패턴 재사용)** |

### 기존 SPEC-019 자산 (재사용 대상)

- 모듈: `backend/src/stock_picker/portfolio/dividends.py`
  - `get_dividend_info(krx_code, redis)` — 종목 배당 단일 진입점(@MX:ANCHOR). Redis 캐시(`dividends:{code}`, TTL 86400s) + FDR `StockListing("KRX")`에서 DPS·DividendYield·배당기준일 best-effort 추출. 실패 시 `dividend_available=False` graceful degradation.
  - `calculate_portfolio_dividends(portfolio_id, user_id, db, redis) -> PortfolioDividends | None` — 집계 오케스트레이션.
- 스키마(`portfolio/schemas.py`): `HoldingDividend`, `DividendCalendarMonth`, `PortfolioDividends`.
- 엔드포인트(`portfolio/router.py`): `GET /portfolios/{portfolio_id}/dividends` → `PortfolioDividends`.
- DB 테이블·마이그레이션 **없음** (실시간 FDR + Redis).

### SPEC-019 한계 (033이 메우는 간극)

1. **캘린더가 "월"만 제공** — `ex_dividend_month`(1~12) 정수만 있고, **정확한 배당기준일(date)·지급일(date)이 없다.** 인컴 투자자는 "몇 월"이 아니라 "며칠에 들어오는지" 알고 싶어 한다.
2. **DRIP(배당 재투자) 시뮬레이션 부재** — 배당을 재투자하면 N년 후 포트폴리오 가치가 어떻게 복리 성장하는지 보여주는 기능이 전무하다. 이것이 033의 핵심 신규 가치다.
3. **요약 응답(DividendSummary) 형태 차이** — 019의 `PortfolioDividends`는 캘린더·커버리지까지 한 응답에 섞여 있다. 요청서는 요약/캘린더/DRIP를 3개 엔드포인트로 분리한다(관심사 분리).

## 1. 결론 — SPEC-033 권장 범위

**SPEC-033은 "배당 수익률 분석 강화 레이어"로 정의한다.** SPEC-019를 대체하지 않고, 019의 데이터 조회 레이어(`get_dividend_info`)를 재사용하여 다음 신규 가치를 추가한다.

- **신규 1 (핵심)**: DRIP 재투자 시뮬레이션 — 완전 신규, 019에 없음.
- **신규 2**: 날짜 정밀 배당 캘린더 — 배당기준일(date)·지급일(date) 기반 이벤트, 019의 월 단위 캘린더를 정밀화.
- **재구성**: 요약/캘린더/DRIP 3개 엔드포인트로 관심사 분리(`/dividend/summary`, `/dividend/calendar`, `/dividend/drip`).
- **재사용**: 종목별 DPS/yield 추정(REQ-DVY-001), 가중 평균 수익률(REQ-DVY-002), 소유권 404(REQ-DVY-005)는 019 데이터 레이어·패턴 재사용. 033은 이를 신규 응답 스키마로 재포장하되 데이터 조회는 019 함수에 위임한다.

이 접근은 브라운필드 관례(중복 회피, 기존 코드 재사용)와 일치한다.

## 2. 코드베이스 분석

### 2.1 포트폴리오 도메인 구조

- `portfolio/service.py` — CRUD + 성과(`calculate_performance`) + AI 최적화(`optimize_portfolio`).
  - `get_portfolio_with_holdings(db, portfolio_id, user_id) -> Portfolio | None` — 소유권 확인 + holdings 명시적 로드(`lazy="noload"`이므로 직접 쿼리). **None 반환 시 라우터에서 404.** 033 소유권 확인의 단일 진입점.
- `portfolio/dividends.py` — SPEC-019 배당(위 0장 참조).
- `portfolio/performance_summary.py` — SPEC-030 기간별 성과. **재사용 포인트**: `_normalize_weights`, `_apply_fx_rate`, `_DISCLAIMER` 면책 문구 패턴, ThreadPoolExecutor + FDR 패턴.
- `portfolio/risk_analysis.py` — SPEC-027. **순수 함수 + numpy 전용 모범 사례.**

### 2.2 ORM 모델 (`db/models.py`)

- `Portfolio` (id, user_id, name, created_at) — `holdings` cascade.
- `PortfolioHolding` (id, portfolio_id, krx_code, quantity, avg_buy_price `Numeric(10,2)`, **market** `KRX|NYSE|NASDAQ` server_default KRX, **currency** `KRW|USD` server_default KRW, added_at). SPEC-028 해외 자산 필드.
- `StockFundamental` (SPEC-018) — `dividend_yield Numeric(8,4)` 컬럼 존재하나 **적재 생산자 없음**(SPEC-019 연구가 확인). 033도 이 빈 테이블에 의존하지 않는다.

### 2.3 가격·환율 조회 재사용

- KRX 현재가: `realtime/price_feed.get_current_price(code)` → `{"price": ...}` 또는 None.
- 해외 현재가: `portfolio/service._fetch_foreign_price(ticker, redis)` (USD) × `portfolio/fx_rate.get_usd_krw_rate(redis)` → KRW 환산.
- DRIP는 **현재 평가액 기준**으로만 시뮬레이션하므로, 정밀 현재가가 필요하면 위 패턴 재사용. (단, DRIP 초기값은 단순화를 위해 `avg_buy_price × quantity` 또는 성과 API의 `total_current` 재사용 검토 — 5장 설계 결정.)

### 2.4 마이그레이션 현황

- 최신 리비전: `0021_rebalancing_plans.py` (SPEC-032, down_revision="0020").
- 요청서는 `0022_dividend_cache.py`(down_revision="0021")를 언급하나 **선택적**이다. SPEC-019가 DB 없이 Redis 캐시로 동작하므로, 033도 신규 테이블 없이 구현 가능하다. → **5장에서 "DB 테이블 미도입"으로 결정.** 신규 마이그레이션 불필요.

## 3. 제약 조건 (브라운필드 관례 carry-over)

memory `project-stock-spec-conventions` 기준:

- **패키지**: `backend/src/stock_picker/portfolio/`.
- **소유권 위반**: 404 (403 아님). `get_portfolio_with_holdings` None → 404.
- **scipy 금지**: numpy + math만. DRIP 복리 공식은 순수 Python/math로 충분.
- **순수 함수 분리**: `calculate_*`는 DB·Redis 없이 테스트 가능. 가격/배당 데이터는 호출자가 주입.
- **프론트 .js/.ts 쌍**: `api/portfolio.js`+`.ts`, `pages/Portfolio.js`+`.tsx` 동시 수정.
- **언어**: code_comments ko, git_commit_messages ko.
- **환경**: gh CLI 미설치.

## 4. DRIP 시뮬레이션 수학 (신규 핵심)

배당 재투자(DRIP) = 매년 받은 배당을 다시 같은 수익률 자산에 투자하여 복리 성장.

단순 복리 모델(NFR-004, Monte Carlo 미사용):

```
연간 총 수익률 = 가격 성장률(미반영, 보수적으로 0 가정 가능) + 배당수익률 × reinvest_rate
```

요청서 단순화: **가격 성장은 가정하지 않고, 배당 재투자 효과만** 복리로 계산한다(보수적·투명).

```
value[0]   = initial_value
value[t]   = value[t-1] × (1 + dividend_yield_pct/100 × reinvest_rate)
annual_dividend[t] = value[t-1] × dividend_yield_pct/100
cumulative_return_pct[t] = (value[t] / initial_value - 1) × 100
```

- `reinvest_rate=1.0` → 100% 재투자(완전 복리).
- `reinvest_rate=0.0` → 재투자 안 함(value 불변, 배당은 현금 인출 — cumulative_return=0).
- `reinvest_rate` 부분값(0~1) → 부분 재투자.

이는 순수 함수 `calculate_drip_projection(initial_value, dividend_yield_pct, years, reinvest_rate)`로 구현. DB·Redis·외부 API 의존 없음.

## 5. 날짜 정밀 캘린더 (신규)

SPEC-019는 `ex_dividend_month`(월 정수)만 제공. 033은 가능하면 배당기준일(`ex_dividend_date: date`)을 제공한다.

- FDR `StockListing("KRX")`의 배당기준일 컬럼(`RecordDate`/`ExDividendDate`/`배당기준일`)을 `_extract_ex_month`가 이미 파싱 중 — 이를 월이 아닌 **전체 날짜**로 확장 추출.
- 지급일(`payment_date`)은 FDR에 통상 없음 → **`Optional[date]`, 미확보 시 None**(추측 단언 금지, REQ-DVY-NFR-003).
- 캘린더 응답은 `months: dict[int, list[DividendEvent]]` 구조로 월별 그룹 + 이벤트 상세(종목·날짜·DPS·수량·예상 총액).

## 6. 위험 및 완화

| 위험 | 완화 |
|------|------|
| SPEC-019와 기능 중복으로 코드 이중화 | 033은 019 `get_dividend_info` 데이터 레이어 재사용. 신규 스키마는 응답 재포장만. §제외에 명시. |
| FDR 배당기준일 정밀 날짜 미확보 | `Optional[date]`, None 허용. 월(`ex_dividend_month`)로 fallback 가능. |
| DRIP가 가격 성장 미반영으로 비현실적 | 면책 문구 명시(과거 배당률 기준 단순 복리, 미래 보장 아님). 투명성 우선. |
| 신규 스키마명이 019와 충돌 | 033은 `DividendSummary`/`DividendEvent`/`DividendCalendar`/`DRIPProjection` 사용 — 019의 `PortfolioDividends`/`HoldingDividend`/`DividendCalendarMonth`와 이름 분리. |
| 엔드포인트 경로 충돌 | 033은 `/dividend/*`(단수), 019는 `/dividends`(복수) — 충돌 없음. |

## 7. 의존성 SPEC

- **SPEC-019**(배당 포트폴리오 분석): `get_dividend_info` 데이터 레이어 재사용. 019 코드 수정 없음.
- **SPEC-017/028**(성과·해외 자산): `get_portfolio_with_holdings` 소유권, market/currency 메타, 가격/환율 조회.
- **SPEC-027**(리스크): 순수 함수 + numpy 전용 구조 패턴.
- **SPEC-030**(성과 요약): 면책 문구·ThreadPoolExecutor 패턴.
