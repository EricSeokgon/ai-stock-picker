---
id: "SPEC-STOCK-033"
version: "0.2.0"
status: "draft"
created_at: "2026-06-24"
updated_at: "2026-06-24"
author: "ircp"
priority: "medium"
issue_number: 0
labels: ["portfolio", "dividend", "drip", "backend", "frontend"]
---

# SPEC-STOCK-033: 배당 수익률 분석 (Dividend Yield Analysis)

> Roadmap 인컴 투자(income investing) 계열 SPEC. 기존 SPEC-019(배당 포트폴리오 분석)가 제공하는 종목별 배당·가중 평균 수익률·월별 캘린더 위에, **날짜 정밀 배당 캘린더**와 **배당 재투자(DRIP) 복리 시뮬레이션**을 추가하는 **강화 레이어**다. 자동 매매·실제 배당 지급 추적은 하지 않는다(영구 제외).

## HISTORY

| 버전 | 날짜 | 변경 내용 |
|------|------|-----------|
| 0.1.0 | 2026-06-24 | 최초 작성. SPEC-019 중복 평가 반영 — 033을 강화 레이어로 정의. 신규 핵심: DRIP 재투자 시뮬레이션. 신규 보조: 날짜 정밀 배당 캘린더. 신규 엔드포인트 3종(`/dividend/summary`·`/dividend/calendar`·`/dividend/drip`). DB 테이블·마이그레이션 미도입(019 데이터 레이어 재사용). |
| 0.2.0 | 2026-06-24 | plan-auditor v1 지적사항 반영(9건). NFR 번호 범위 정정(001~004→001~005). REQ-DVY-NFR-002 비격식 어미 제거. REQ-DVY-NFR-005·acceptance.md SHALL 진술에서 파일 경로·변수명·라이브러리명·자료구조 리터럴을 행동 서술(자연어)로 치환. |

> **REQ 접두사 설계 원칙**: 본 SPEC은 `REQ-DVY-*`(DiVidend Yield) 접두사를 사용한다. SPEC-019가 `REQ-DIV-*`를 점유하므로 충돌을 회피한다.

> **번호 체계**: REQ-DVY-001~005 연속 번호. NFR은 REQ-DVY-NFR-001~005.

---

## 1. 개요 (Overview)

### 1.1 기능 설명

SPEC-019는 보유 종목별 DPS·배당수익률, 포트폴리오 가중 평균 수익률, **월(month) 단위** 배당 캘린더를 `GET /portfolios/{id}/dividends`로 제공한다. 그러나 두 가지 인컴 투자자 핵심 질문에 답하지 못한다.

1. **"배당이 정확히 며칠에 들어오는가?"** — 019는 "몇 월"(1~12)만 알려준다. 배당기준일·지급일의 정밀한 날짜가 없다.
2. **"배당을 재투자하면 N년 후 내 자산은 얼마가 되는가?"** — 019에 재투자(DRIP) 복리 시뮬레이션이 전혀 없다.

SPEC-033은 이 두 간극을 메운다. SPEC-019의 배당 데이터 조회 레이어(`get_dividend_info`)를 **재사용**하여 다음을 추가한다.

- **배당 요약**(`DividendSummary`) — 종목별 배당·포트폴리오 가중 평균 수익률을 신규 응답 형태로 재포장(019 데이터 위임).
- **날짜 정밀 배당 캘린더**(`DividendCalendar`) — 배당기준일(date)·지급일(date) 기반 월별 그룹 이벤트.
- **DRIP 시뮬레이션**(`DRIPProjection`) — 배당 재투자 시 N년간 포트폴리오 가치 복리 성장 투영. **본 SPEC의 핵심 신규 가치.**

### 1.2 동기 (Motivation)

배당주 투자자는 단순히 "지금 배당수익률이 몇 %인가"를 넘어, **시간 축**에서 배당을 본다.

- **현금 흐름 계획**: 매달 며칠에 얼마가 들어오는지 알아야 생활비·재투자 계획을 세운다.
- **복리의 힘**: 배당을 재투자하면 장기적으로 자산이 얼마나 빠르게 불어나는지 보여주면, "배당 재투자가 왜 중요한가"를 직관적으로 이해할 수 있다.

본 SPEC은 정보 제공·의사결정 지원이며, 실제 배당 지급을 추적하거나 자동 재투자를 집행하지 않는다.

### 1.3 목표 (Goals)

- SPEC-019 배당 데이터 레이어를 재사용하여 종목별 연 배당 추정·포트폴리오 가중 평균 수익률을 신규 요약 응답으로 제공한다.
- 배당기준일·지급일(가능 시) 기반 날짜 정밀 캘린더를 월별로 그룹화하여 제공한다.
- 배당 재투자(DRIP) 복리 시뮬레이션을 순수 함수로 구현하여 N년간 가치 투영을 제공한다.
- 핵심 계산(요약 집계·DRIP)을 DB·외부 API 없이 테스트 가능한 순수 함수로 분리한다.
- 프론트엔드에 배당 요약·캘린더·DRIP 투영 UI를 추가한다.

### 1.4 기술 스택 (확정·재사용)

FastAPI + PostgreSQL(asyncpg) + SQLAlchemy + Redis + React + JavaScript/TypeScript. 신규 라이브러리·신규 DB 테이블·신규 마이그레이션을 도입하지 않는다. 배당 데이터는 SPEC-019 `get_dividend_info`(FDR best-effort + Redis 캐시)를 재사용한다. 수치 계산은 `numpy` + `math`만 사용한다(scipy 미사용).

---

## 2. 범위 (Scope)

### 2.1 포함 (In Scope)

- 신규 순수 함수 모듈 `portfolio/dividend_yield.py`:
  - `calculate_dividend_summary(holdings, prices)` — 종목별 배당·포트폴리오 가중 평균 수익률 집계(순수 함수).
  - `calculate_dividend_calendar(holdings, dividend_history, year)` — 날짜 정밀 월별 이벤트 그룹(순수 함수).
  - `calculate_drip_projection(initial_value, dividend_yield_pct, years, reinvest_rate)` — DRIP 복리 투영(순수 함수, 핵심 신규).
- 신규 서비스 오케스트레이션 — 소유권 확인, SPEC-019 `get_dividend_info`로 배당 데이터 조회, 순수 함수 호출.
- 신규 Pydantic 스키마(`portfolio/schemas.py`): `HoldingDividendYield`, `DividendSummary`, `DividendEvent`, `DividendCalendar`, `DRIPYearData`, `DRIPProjection`.
- 신규 엔드포인트 3개(`portfolio/router.py`):
  - `GET /portfolios/{portfolio_id}/dividend/summary`
  - `GET /portfolios/{portfolio_id}/dividend/calendar?year=`
  - `GET /portfolios/{portfolio_id}/dividend/drip?years=&reinvest_rate=`
- 배당기준일 전체 날짜 추출 확장(`portfolio/dividends.py`의 best-effort 추출 로직 재사용/확장 — 월→날짜).
- 프론트엔드 배당 분석 컴포넌트 + API 클라이언트 확장(`.js`/`.ts` 쌍).
- 단위 테스트(커버리지 85% 이상).

### 2.2 제외 (What NOT to Build)

> [HARD] 본 SPEC은 다음을 **빌드하지 않는다**.

- **SPEC-019 재구현/대체**: 종목별 DPS·배당수익률 *데이터 조회*는 SPEC-019 `get_dividend_info`를 재사용한다. 033은 조회 로직을 새로 구현하지 않으며, 기존 `GET /portfolios/{id}/dividends` 엔드포인트·`PortfolioDividends` 스키마·`dividends.py` 집계 함수를 수정하거나 제거하지 않는다.
- **실제 배당 지급 추적**: 실제 입금 내역·배당 수령 이력 저장은 하지 않는다. 모든 값은 *추정*이다.
- **자동 배당 재투자 집행**: DRIP는 *시뮬레이션*이며, 실제 매수 주문·증권사 연동은 영구 제외.
- **가격 성장 예측**: DRIP 투영은 **배당 재투자 효과만** 복리로 계산한다. 주가 상승/하락 예측(가격 성장률 가정)은 하지 않는다(보수적·투명).
- **Monte Carlo / 확률 시뮬레이션**: DRIP는 단일 단순 복리 공식만 사용한다(REQ-DVY-NFR-004). 확률 분포·시나리오 분기는 제외.
- **신규 DB 테이블·마이그레이션**: SPEC-019처럼 실시간 조회 + Redis 캐시로 동작한다. `dividend_cache` 등 신규 테이블·마이그레이션(0022)을 도입하지 않는다.
- **세금·원천징수 계산**: 배당소득세·원천징수 차감은 하지 않는다. 모든 배당은 세전(gross) 기준이다.
- **다중 통화 정산**: 모든 금액은 KRW 단일 통화 기준으로 표기한다.
- **배당 데이터 미확보 종목의 추측**: 배당 데이터(DPS/yield/기준일)가 없으면 0.0/None으로 처리하고 단언하지 않는다.

---

## 3. 기능 요구사항 (EARS Requirements)

### REQ-DVY-001 (Event-driven) — 종목별 연 배당 추정

WHEN 시스템이 포트폴리오의 배당 수익률을 계산하면 THE 시스템 SHALL 보유 종목별로 가용한 배당 이력 데이터로부터 주당 연 배당금을 추정하며, 데이터가 없는 종목은 0으로 처리한다.

### REQ-DVY-002 (Event-driven) — 포트폴리오 가중 평균 배당수익률

WHEN 종목별 배당 추정값이 가용하면 THE 시스템 SHALL 포트폴리오 수준의 가중 평균 배당수익률을 산출하되, 각 종목의 평가액과 배당수익률의 곱을 합산하여 포트폴리오 총 평가액으로 나눈 값으로 계산한다.

### REQ-DVY-003 (Event-driven) — 날짜 정밀 배당 캘린더

WHEN 사용자가 포트폴리오의 배당 캘린더를 요청하면 THE 시스템 SHALL 월별로 그룹화된 예상 배당 이벤트를 반환하며, 각 이벤트는 배당기준일, 지급일(확인되는 경우), 주당 추정 배당금, 추정 총 배당액(보유 수량 × 주당 배당금)을 포함한다.

### REQ-DVY-004 (Event-driven) — DRIP 재투자 시뮬레이션

WHEN 사용자가 배당 재투자 시뮬레이션을 요청하면 THE 시스템 SHALL 현재 가중 평균 배당수익률로 배당이 지정된 재투자 비율만큼 재투자된다고 가정하여 N년간 포트폴리오 가치를 투영한다.

### REQ-DVY-005 (Unwanted) — 소유권 확인

IF 요청 사용자가 소유하지 않은 포트폴리오에 대해 배당 분석을 요청하면 THEN THE 시스템 SHALL 존재하지 않는 포트폴리오에 대한 요청과 동일하게 응답하여 소유권 정보를 노출하지 않는다.

---

## 4. 비기능 요구사항 (NFR)

- **REQ-DVY-NFR-001 (외부 최적화 라이브러리 비도입)**: THE 시스템 SHALL 본 SPEC 신규 수치 계산 코드를 표준 수학 연산 및 프로젝트 승인 라이브러리만으로 구현하며, 새로운 외부 수치 라이브러리를 도입하지 않는다.
- **REQ-DVY-NFR-002 (순수 함수 테스트성)**: THE 시스템의 핵심 배당 집계·DRIP 계산 컴포넌트 SHALL DB·외부 캐시·외부 API에 대한 의존 없이 입력값만으로 결정적 결과를 반환한다.
- **REQ-DVY-NFR-003 (배당 데이터 미확보 graceful degradation)**: IF 종목의 배당 데이터를 확보할 수 없으면 THEN THE 시스템 SHALL 해당 종목의 배당을 0으로 처리하고 오류를 발생시키지 않으며, 미확보 날짜는 단언하지 않고 비워 둔다.
- **REQ-DVY-NFR-004 (단순 복리 모델)**: THE DRIP 시뮬레이션 SHALL 단일 단순 복리 공식을 사용하며 확률 시뮬레이션을 사용하지 않는다.
- **REQ-DVY-NFR-005 (테스트 커버리지)**: THE 시스템의 배당 수익률 계산 컴포넌트 SHALL 단위 테스트 커버리지 85% 이상을 충족한다.

---

## 5. 기술 접근 방식 (Technical Approach)

### 5.1 순수 함수 (`portfolio/dividend_yield.py`)

```python
def calculate_dividend_summary(
    holdings: list[HoldingDividendInput],   # krx_code, stock_name, shares, annual_dps
    prices: dict[str, float],               # {krx_code: current_price_krw}
) -> DividendSummary:
    ...

def calculate_dividend_calendar(
    holdings: list[HoldingDividendInput],
    dividend_history: dict[str, DividendMeta],  # {krx_code: {ex_dividend_date, payment_date, dps}}
    year: int,
) -> DividendCalendar:
    ...

def calculate_drip_projection(
    initial_value: float,
    dividend_yield_pct: float,
    years: int,
    reinvest_rate: float = 1.0,
) -> DRIPProjection:
    ...
```

`HoldingDividendInput`(내부 dataclass 또는 dict): `krx_code`, `stock_name`, `shares`, `annual_dps`.

#### 5.1.1 `calculate_dividend_summary` 알고리즘

1. 종목별 `dividend_yield_pct = annual_dps / current_price × 100` (현재가 0 또는 미확보 시 0.0).
2. 종목별 `estimated_annual_dividend = shares × annual_dps`.
3. `total_annual_dividend = Σ estimated_annual_dividend`.
4. `total_portfolio_value = Σ (shares × current_price)`.
5. `portfolio_dividend_yield_pct` = 평가액 가중 평균 = `Σ(holding_value × dividend_yield_pct) / total_portfolio_value` (총 평가액 0이면 0.0).

#### 5.1.2 `calculate_dividend_calendar` 알고리즘

1. 종목별 배당기준일(`ex_dividend_date`)을 입력 `dividend_history`에서 조회.
2. 기준일의 연도가 요청 `year`와 일치(또는 월만 확인 가능 시 해당 연도로 정규화)하는 이벤트만 포함.
3. `estimated_total = shares × dps`.
4. `payment_date`는 확인되는 경우만 설정, 미확보 시 None(REQ-DVY-NFR-003).
5. 월(`ex_dividend_date.month`) 기준으로 그룹화 → `months: dict[int, list[DividendEvent]]`.

#### 5.1.3 `calculate_drip_projection` 알고리즘 (핵심 신규)

배당 재투자만 복리로 계산(가격 성장 미반영):

```
value[0] = initial_value
for t in 1..years:
    annual_dividend[t]      = value[t-1] × dividend_yield_pct/100
    reinvested[t]           = annual_dividend[t] × reinvest_rate
    value[t]                = value[t-1] + reinvested[t]
    cumulative_return_pct[t] = (value[t] / initial_value - 1) × 100
```

- `reinvest_rate=1.0`: 완전 복리. `reinvest_rate=0.0`: value 불변, 누적 수익률 0(현금 인출 가정).
- `years` 입력 검증: 1 이상 정수(상한 합리값, 예 50). `reinvest_rate`: 0.0~1.0.

순수 함수는 DB·가격 조회를 하지 않는다(REQ-DVY-NFR-002). scipy 미사용, math만으로 충분.

> **설계 결정 노트(라이브러리)**: REQ-DVY-NFR-001 구현 시 `numpy`+`math`만 사용하고 `scipy`는 import하지 않는다(`risk_analysis.py` 패턴 일관성).
> **설계 결정 노트(보수적 DRIP)**: 가격 성장률을 가정하지 않는 것은 의도된 단순화다. 미래 주가 예측 불확실성을 배제하고 "배당 재투자 효과"만 투명하게 보여 준다(§2.2 제외).

### 5.2 서비스 오케스트레이션

```
배당 요약 서비스(portfolio_id, user_id, db, redis):
  1. get_portfolio_with_holdings(db, portfolio_id, user_id)  # None → 404 (REQ-DVY-005)
  2. 보유 종목별 SPEC-019 get_dividend_info(krx_code, redis)로 배당 데이터 조회 (재사용)
     - annual_dps = div["dps"] (없으면 0.0)
  3. 종목별 현재가 조회 → KRW 환산:
     - KRX: get_current_price(krx_code)["price"]
     - 해외: _fetch_foreign_price(ticker, redis) × get_usd_krw_rate(redis)
     - 실패 시 price 0.0 (수익률 0 처리, REQ-DVY-NFR-003)
  4. calculate_dividend_summary(holdings, prices) 순수 함수 호출
  5. RETURN DividendSummary

배당 캘린더 서비스(portfolio_id, user_id, db, redis, year):
  1. 소유권 확인 (404)
  2. get_dividend_info로 배당기준일·DPS 조회 (날짜 추출 확장)
  3. calculate_dividend_calendar(holdings, dividend_history, year)
  4. RETURN DividendCalendar

DRIP 서비스(portfolio_id, user_id, db, redis, years, reinvest_rate):
  1. 소유권 확인 (404)
  2. 배당 요약 재사용 → portfolio_dividend_yield_pct, total_portfolio_value 획득
  3. calculate_drip_projection(initial_value=total_portfolio_value,
                               dividend_yield_pct=..., years=..., reinvest_rate=...)
  4. RETURN DRIPProjection
```

> **설계 결정 노트(데이터 재사용)**: 배당 데이터 *조회*는 SPEC-019 `get_dividend_info`에 위임한다. 033은 신규 FDR 조회 로직을 작성하지 않는다(중복 회피, §2.2 제외).
> **설계 결정 노트(소유권 응답)**: REQ-DVY-005 구현 시 `get_portfolio_with_holdings()` None → `404 Not Found`(코드베이스 관례, 403 아님).
> **설계 결정 노트(DRIP 초기값)**: `initial_value`는 배당 요약의 `total_portfolio_value`(현재가 기반 평가액)를 재사용한다. 현재가 미확보 시 `avg_buy_price × quantity`로 fallback.

### 5.3 스키마 (`portfolio/schemas.py`)

```python
class HoldingDividendYield(BaseModel):
    krx_code: str
    stock_name: str
    shares: int
    annual_dps: float                  # 주당 연 배당금 (KRW)
    dividend_yield_pct: float          # annual_dps / current_price × 100
    estimated_annual_dividend: float   # shares × annual_dps

class DividendSummary(BaseModel):
    portfolio_id: int
    total_portfolio_value: float
    total_annual_dividend: float
    portfolio_dividend_yield_pct: float  # 가중 평균
    holdings: list[HoldingDividendYield]

class DividendEvent(BaseModel):
    krx_code: str
    stock_name: str
    ex_dividend_date: date
    payment_date: Optional[date]
    dps: float
    shares: int
    estimated_total: float             # shares × dps

class DividendCalendar(BaseModel):
    portfolio_id: int
    year: int
    months: dict[int, list[DividendEvent]]   # {month: [events]}

class DRIPYearData(BaseModel):
    year: int
    portfolio_value: float
    annual_dividend: float
    cumulative_return_pct: float

class DRIPProjection(BaseModel):
    portfolio_id: int
    initial_value: float
    dividend_yield_pct: float
    reinvest_rate: float
    years: list[DRIPYearData]
    disclaimer: str                    # 면책 문구 (단순 복리·미래 보장 아님)
```

> **명명 충돌 회피**: 033 스키마(`DividendSummary`/`DividendEvent`/`DividendCalendar`/`DRIPProjection`)는 019의 `PortfolioDividends`/`HoldingDividend`/`DividendCalendarMonth`와 이름이 분리되어 충돌하지 않는다.

### 5.4 라우터 (`portfolio/router.py`)

```
GET /portfolios/{portfolio_id}/dividend/summary
  소유권 불일치 → 404 (REQ-DVY-005)
  Response: DividendSummary

GET /portfolios/{portfolio_id}/dividend/calendar?year=<int, 기본 당해연도>
  소유권 불일치 → 404
  Response: DividendCalendar

GET /portfolios/{portfolio_id}/dividend/drip?years=<int, 기본 10>&reinvest_rate=<float, 기본 1.0>
  소유권 불일치 → 404
  Response: DRIPProjection
```

기존 `Depends(get_current_user)` + `get_db_session` + `get_redis_client` 패턴 재사용. `/dividend/*`(단수)는 019의 `/dividends`(복수)와 경로 충돌 없음.

### 5.5 프론트엔드

- `frontend/src/components/DividendSummaryPanel.js` — 배당 요약 표(종목·DPS·수익률·연 배당) + 포트폴리오 가중 평균.
- `frontend/src/components/DividendCalendarView.js` — 월별 배당 이벤트 캘린더.
- `frontend/src/components/DRIPSimulator.js` — years/reinvest_rate 입력 + 연도별 가치 투영 표/차트.
- `frontend/src/api/portfolio.js`(+`.ts`) — `apiGetDividendSummary`·`apiGetDividendCalendar`·`apiGetDRIPProjection`.
- `frontend/src/pages/Portfolio.js`(+`.tsx`) — 배당 분석 섹션 통합(기존 섹션 보존).

---

## 6. Delta Markers (변경 영향 분석)

| 마커 | 파일 | 내용 |
|------|------|------|
| [EXISTING] | `backend/src/stock_picker/portfolio/dividends.py` | `get_dividend_info`(배당 데이터 조회) 재사용. 날짜 추출 확장 시 [MODIFY]로 승격 가능 |
| [EXISTING] | `backend/src/stock_picker/portfolio/service.py` | `get_portfolio_with_holdings`·`_fetch_foreign_price` 재사용(수정 없음) |
| [EXISTING] | `backend/src/stock_picker/portfolio/fx_rate.py` | `get_usd_krw_rate` 재사용(수정 없음) |
| [EXISTING] | `backend/src/stock_picker/realtime/price_feed.py` | `get_current_price` 재사용(수정 없음) |
| [NEW] | `backend/src/stock_picker/portfolio/dividend_yield.py` | 순수 함수 3종 + 서비스 오케스트레이션 |
| [MODIFY] | `backend/src/stock_picker/portfolio/schemas.py` | `HoldingDividendYield`·`DividendSummary`·`DividendEvent`·`DividendCalendar`·`DRIPYearData`·`DRIPProjection` 추가 |
| [MODIFY] | `backend/src/stock_picker/portfolio/router.py` | dividend/summary·calendar·drip 엔드포인트 3종 추가 |
| [NEW] | `backend/tests/unit/test_dividend_yield.py` | 순수 함수·서비스 단위 테스트(커버리지 85%+) |
| [NEW] | `frontend/src/components/DividendSummaryPanel.js` | 배당 요약 패널 |
| [NEW] | `frontend/src/components/DividendCalendarView.js` | 배당 캘린더 뷰 |
| [NEW] | `frontend/src/components/DRIPSimulator.js` | DRIP 시뮬레이터 |
| [MODIFY] | `frontend/src/api/portfolio.js` | 배당 분석 API 클라이언트 추가 |
| [MODIFY] | `frontend/src/api/portfolio.ts` | 배당 분석 API 클라이언트 추가 |
| [MODIFY] | `frontend/src/pages/Portfolio.js` | 배당 분석 섹션 통합 |
| [MODIFY] | `frontend/src/pages/Portfolio.tsx` | 배당 분석 섹션 통합 |

> **DB 테이블·마이그레이션 미도입**: SPEC-019처럼 실시간 FDR 조회 + Redis 캐시로 동작하므로 신규 테이블·마이그레이션(0022)이 **불필요**하다. 요청서가 언급한 `0022_dividend_cache.py`는 채택하지 않는다(§2.2 제외).

---

## 7. 의존성 (Dependencies)

- **SPEC-019**(배당 포트폴리오 분석): `get_dividend_info` 데이터 레이어 재사용. 019 코드(엔드포인트·스키마·집계 함수)는 수정·제거하지 않는다.
- **SPEC-028**(해외 자산 지원): `PortfolioHolding.market`/`currency`, `_fetch_foreign_price`, `fx_rate` — KRW 환산.
- **SPEC-017**(포트폴리오 성과): `get_portfolio_with_holdings` 소유권, `get_current_price` KRX 가격.
- **SPEC-027**(리스크 분석): 순수 함수 + numpy 전용 구조 패턴(`risk_analysis.py`) 모방.
- **SPEC-030**(성과 요약): 면책 문구 패턴 재사용.

---

## 8. MX 태그 계획 (MX Tag Plan)

코드 주석 언어는 한국어(`language.yaml` `code_comments: ko`).

- **@MX:ANCHOR** (`dividend_yield.py`의 `calculate_drip_projection` 순수 함수 진입점):
  - 사유: 서비스 오케스트레이션 + 단위 테스트에서 fan_in ≥ 3 예상. `@MX:REASON` 필수.
- **@MX:ANCHOR** (`DividendSummary`·`DRIPProjection` 응답 스키마):
  - 사유: router·service·프론트 API 래퍼·테스트 3곳 이상 참조. `@MX:REASON` 필수.
- **@MX:NOTE** (`dividend_yield.py` 모듈 상단):
  - scipy 금지·numpy/math 전용, DRIP 단순 복리 모델(가격 성장 미반영) 명시.
- **@MX:NOTE** (DRIP 초기값 분기):
  - 현재가 미확보 시 avg_buy_price fallback 사유.
- **@MX:WARN** (KRW 환산·가중 평균 부동소수 누적 처리부):
  - USD 환산·round 일관성 주의. `@MX:REASON` 필수.
- **@MX:TODO** (RED 단계):
  - 미구현 순수 함수·오케스트레이션 임시 마커. GREEN 단계에서 제거.

태그 설명은 한국어로 작성하고, 에이전트 생성 태그는 `[AUTO]` 접두사를 포함한다.

---

## 9. 수용 기준 (Acceptance Criteria)

상세 BDD 시나리오·EARS 수용 기준은 [acceptance.md](acceptance.md) 참조. 작업 분해는 [plan.md](plan.md), 압축 참조는 [spec-compact.md](spec-compact.md) 참조.
