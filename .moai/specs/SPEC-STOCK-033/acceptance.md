# SPEC-STOCK-033 수용 기준 (Acceptance Criteria)

> EARS 형식 수용 기준 + Given-When-Then BDD 시나리오 + 엣지 케이스 + Definition of Done.

## 1. EARS 수용 기준 (SHALL 진술)

각 기능 요구사항이 충족되었는지 검증하는 관찰 가능한 SHALL 진술.

### AC-DVY-001 — 종목별 연 배당 추정

- THE 시스템 SHALL 보유 종목별로 가용 배당 이력에서 주당 연 배당금(`annual_dps`)을 추정한다.
- THE 시스템 SHALL 배당 데이터가 없는 종목의 `annual_dps`를 0으로 설정한다.
- THE 시스템 SHALL 종목별 `estimated_annual_dividend`를 `shares × annual_dps`로 산출한다.
- THE 시스템 SHALL 종목별 `dividend_yield_pct`를 `annual_dps / current_price × 100`으로 산출하되, 현재가가 0 또는 미확보면 0.0으로 설정한다.

### AC-DVY-002 — 포트폴리오 가중 평균 배당수익률

- THE 시스템 SHALL `portfolio_dividend_yield_pct`를 각 종목 평가액과 배당수익률의 곱의 합을 총 평가액으로 나눈 값으로 산출한다.
- THE 시스템 SHALL 총 평가액이 0이면 `portfolio_dividend_yield_pct`를 0.0으로 설정한다.
- THE 시스템 SHALL `total_annual_dividend`를 모든 종목 `estimated_annual_dividend`의 합으로 산출한다.

### AC-DVY-003 — 날짜 정밀 배당 캘린더

- THE 시스템 SHALL 요청 연도(`year`)의 예상 배당 이벤트를 월별로 그룹화하여 `months: {month: [events]}` 형태로 반환한다.
- THE 시스템 SHALL 각 이벤트에 `ex_dividend_date`, `dps`, `shares`, `estimated_total`(= shares × dps)을 포함한다.
- THE 시스템 SHALL `payment_date`가 확인되지 않으면 None으로 설정하고 추측하지 않는다.
- THE 시스템 SHALL 배당기준일이 확인되지 않는 종목을 캘린더에서 제외한다.

### AC-DVY-004 — DRIP 재투자 시뮬레이션

- THE 시스템 SHALL `years` 길이의 연도별 투영(`DRIPYearData` 목록)을 반환한다.
- THE 시스템 SHALL 각 연도 `portfolio_value`를 직전 연도 가치에 재투자 배당(`직전가치 × yield/100 × reinvest_rate`)을 더한 값으로 산출한다.
- THE 시스템 SHALL `cumulative_return_pct`를 `(portfolio_value / initial_value - 1) × 100`으로 산출한다.
- WHEN `reinvest_rate=0.0`이면 THE 시스템 SHALL 모든 연도 `portfolio_value`를 `initial_value`와 동일하게, 누적 수익률을 0으로 유지한다.
- THE 시스템 SHALL 응답에 면책 문구(`disclaimer`)를 포함한다.

### AC-DVY-005 — 소유권 확인

- IF 요청 사용자가 포트폴리오를 소유하지 않으면 THEN THE 시스템 SHALL 미존재 포트폴리오와 동일한 오류 응답을 반환한다.
- THE 시스템 SHALL 소유권 위반과 미존재를 구별 가능한 정보를 응답에 노출하지 않는다.

### AC-DVY-NFR — 비기능

- THE `dividend_yield.py` 순수 함수 SHALL DB·Redis·외부 API 호출 없이 입력값만으로 결정적 결과를 반환한다.
- THE DRIP 계산 SHALL 단일 단순 복리 공식만 사용하고 확률 시뮬레이션을 사용하지 않는다.
- THE 신규 코드 SHALL `scipy`를 import하지 않는다.
- THE `dividend_yield.py` SHALL 단위 테스트 커버리지 85% 이상을 충족한다.

---

## 2. BDD 시나리오 (Given-When-Then)

### 시나리오 1 — 배당 요약 (정상)

```
Given 사용자가 소유한 포트폴리오에 삼성전자(현재가 70,000원, 100주, DPS 1,500원),
      현대차(현재가 200,000원, 10주, DPS 11,000원)가 있고
When  GET /portfolios/{id}/dividend/summary 를 호출하면
Then  삼성전자 estimated_annual_dividend = 150,000원,
      dividend_yield_pct ≈ 2.14%
And   현대차 estimated_annual_dividend = 110,000원,
      dividend_yield_pct = 5.5%
And   total_annual_dividend = 260,000원
And   total_portfolio_value = 9,000,000원 (700만 + 200만)
And   portfolio_dividend_yield_pct = 가중평균 ≈ (700만×2.14 + 200만×5.5)/900만 ≈ 2.89%
```

### 시나리오 2 — 배당 데이터 미확보 종목

```
Given 포트폴리오에 배당 데이터가 없는 종목 A(50주)가 포함되어 있고
When  배당 요약을 요청하면
Then  종목 A의 annual_dps = 0.0, dividend_yield_pct = 0.0,
      estimated_annual_dividend = 0.0 으로 처리되고
And   오류가 발생하지 않으며 다른 종목 집계는 정상 산출된다
```

### 시나리오 3 — DRIP 완전 재투자 (reinvest_rate=1.0)

```
Given 초기 평가액 10,000,000원, 가중 평균 배당수익률 4.0%, years=3
When  GET /portfolios/{id}/dividend/drip?years=3&reinvest_rate=1.0 을 호출하면
Then  year1 portfolio_value = 10,400,000 (10,000,000 × 1.04)
And   year2 portfolio_value = 10,816,000 (10,400,000 × 1.04)
And   year3 portfolio_value = 11,248,640 (10,816,000 × 1.04)
And   year3 cumulative_return_pct ≈ 12.49%
And   disclaimer 문구가 포함된다
```

### 시나리오 4 — DRIP 재투자 안 함 (reinvest_rate=0.0)

```
Given 초기 평가액 10,000,000원, 배당수익률 4.0%, years=5, reinvest_rate=0.0
When  DRIP 시뮬레이션을 요청하면
Then  모든 연도 portfolio_value = 10,000,000원 (불변)
And   모든 연도 cumulative_return_pct = 0.0
And   annual_dividend = 400,000원 (매년 동일, 현금 인출)
```

### 시나리오 5 — 날짜 정밀 캘린더

```
Given 포트폴리오에 12월 배당기준일이 확인된 종목(DPS 1,500원, 100주)이 있고
When  GET /portfolios/{id}/dividend/calendar?year=2026 을 호출하면
Then  months[12] 에 해당 종목 이벤트가 포함되고
And   이벤트의 estimated_total = 150,000원 (100 × 1,500)
And   payment_date 가 FDR에서 확인되지 않으면 None 이다
```

### 시나리오 6 — 소유권 위반

```
Given 사용자 B가 사용자 A의 포트폴리오 ID로 배당 분석을 요청하고
When  GET /portfolios/{A의_id}/dividend/summary 를 호출하면
Then  미존재 포트폴리오와 동일한 404 응답을 받고
And   소유권 위반임을 식별할 수 있는 정보가 노출되지 않는다
```

### 시나리오 7 — 빈 포트폴리오

```
Given 보유 종목이 없는 포트폴리오를 소유한 사용자가
When  배당 요약을 요청하면
Then  holdings = [], total_annual_dividend = 0.0,
      total_portfolio_value = 0.0, portfolio_dividend_yield_pct = 0.0 을 받는다
```

---

## 3. 엣지 케이스

| # | 엣지 케이스 | 기대 동작 |
|---|------------|----------|
| E1 | 현재가 0 또는 미확보 종목 | dividend_yield_pct = 0.0, 오류 없음 |
| E2 | 총 평가액 0 (전 종목 현재가 미확보) | portfolio_dividend_yield_pct = 0.0 |
| E3 | DPS는 있으나 현재가 미확보 | estimated_annual_dividend는 산출, yield_pct = 0.0 |
| E4 | `years=0` 또는 음수 | 검증 오류(422) 또는 빈 years 목록 (구현 시 1 이상 강제) |
| E5 | `reinvest_rate` > 1.0 또는 음수 | 0.0~1.0 범위 밖 입력 거부(422) 또는 클램핑 |
| E6 | 배당기준일 연도 ≠ 요청 year | 해당 이벤트 캘린더에서 제외 |
| E7 | 해외(USD) 종목 배당 | 현재가 KRW 환산 후 일관 산출 (DPS는 best-effort, 미확보 시 0) |
| E8 | DRIP yield = 0.0% | 모든 연도 value 불변, 누적 수익률 0 (배당 없음) |
| E9 | Redis 장애 | get_dividend_info FDR fallback(019 동작), 요약 정상 산출 |
| E10 | 동일 종목 KRX·해외 중복 보유 | 각 보유 단위로 독립 집계 |

---

## 4. Definition of Done (DoD)

- [ ] `portfolio/dividend_yield.py` 순수 함수 3종 구현 (`calculate_dividend_summary`·`calculate_dividend_calendar`·`calculate_drip_projection`).
- [ ] 서비스 오케스트레이션 3종 구현 — SPEC-019 `get_dividend_info` 재사용, 소유권 404.
- [ ] 신규 스키마 6종 추가(`schemas.py`), 019 스키마와 이름 충돌 없음.
- [ ] 신규 엔드포인트 3종 추가(`router.py`), 019 `/dividends`와 경로 충돌 없음.
- [ ] 기존 SPEC-019 코드(엔드포인트·스키마·`dividends.py` 집계)를 수정·제거하지 않음.
- [ ] 신규 DB 테이블·마이그레이션 없음(실시간 + Redis).
- [ ] scipy import 없음, numpy + math만 사용.
- [ ] 프론트 `.js`/`.ts` 쌍 동시 수정, 배당 분석 컴포넌트 3종 추가.
- [ ] 단위 테스트 커버리지 85% 이상.
- [ ] BDD 시나리오 1~7 + 엣지 케이스 E1~E10 테스트 통과.
- [ ] @MX 태그 계획(spec.md §8) 반영, 한국어 + [AUTO] 접두사.
- [ ] DRIP 응답에 면책 문구 포함.
- [ ] ruff check 통과, 코드 주석 한국어.
