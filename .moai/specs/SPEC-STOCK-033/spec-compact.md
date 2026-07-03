# SPEC-STOCK-033 압축 참조 (Run-phase Compact)

> Run 단계 구현용 압축 요약. 전체는 spec.md/acceptance.md/plan.md 참조.

## 목표

SPEC-019(배당 분석) **강화 레이어**. 신규 핵심 = DRIP 재투자 복리 시뮬레이션. 신규 보조 = 날짜 정밀 배당 캘린더. 데이터 조회는 019 `get_dividend_info` 재사용.

## REQ 요약

- REQ-DVY-001: 종목별 연 배당 추정(데이터 없으면 0).
- REQ-DVY-002: 포트폴리오 가중 평균 수익률 = Σ(평가액×yield)/총평가액.
- REQ-DVY-003: 날짜 정밀 배당 캘린더(월별 그룹, ex_dividend_date·payment_date).
- REQ-DVY-004: DRIP 시뮬레이션(N년 복리 투영).
- REQ-DVY-005: 소유권 위반 = 미존재와 동일 응답(404).
- NFR: scipy 금지(numpy+math), 순수 함수 테스트성, graceful degradation, 단순 복리(Monte Carlo 금지), 커버리지 85%+.

## 파일

- [NEW] `backend/src/stock_picker/portfolio/dividend_yield.py` — 순수 함수 3종 + 서비스.
- [MODIFY] `portfolio/schemas.py` — 6종 스키마.
- [MODIFY] `portfolio/router.py` — 엔드포인트 3종.
- [EXISTING 재사용] `portfolio/dividends.py` `get_dividend_info`, `portfolio/service.py` `get_portfolio_with_holdings`·`_fetch_foreign_price`, `fx_rate.get_usd_krw_rate`, `realtime/price_feed.get_current_price`.
- [MODIFY/T-005] `portfolio/dividends.py` — 배당기준일 날짜 추출 확장(하위 호환).
- [NEW] `backend/tests/unit/test_dividend_yield.py`.
- [NEW] 프론트 `DividendSummaryPanel.js`·`DividendCalendarView.js`·`DRIPSimulator.js`.
- [MODIFY] `api/portfolio.js`(+`.ts`), `pages/Portfolio.js`(+`.tsx`).
- **DB 테이블·마이그레이션 없음.**

## 순수 함수 시그니처

```python
def calculate_dividend_summary(holdings, prices) -> DividendSummary: ...
def calculate_dividend_calendar(holdings, dividend_history, year) -> DividendCalendar: ...
def calculate_drip_projection(initial_value, dividend_yield_pct, years, reinvest_rate=1.0) -> DRIPProjection: ...
```

## DRIP 공식 (핵심)

```
value[0] = initial_value
value[t] = value[t-1] × (1 + dividend_yield_pct/100 × reinvest_rate)
annual_dividend[t] = value[t-1] × dividend_yield_pct/100
cumulative_return_pct[t] = (value[t]/initial_value - 1) × 100
```
가격 성장 미반영. reinvest_rate 0.0~1.0. 면책 문구 포함.

## 엔드포인트

```
GET /portfolios/{id}/dividend/summary           → DividendSummary
GET /portfolios/{id}/dividend/calendar?year=     → DividendCalendar
GET /portfolios/{id}/dividend/drip?years=10&reinvest_rate=1.0 → DRIPProjection
소유권 불일치 → 404. /dividend/*(단수) ≠ 019 /dividends(복수).
```

## 제약 (carry-over)

- 패키지 `portfolio/`. 소유권 404(403 아님). scipy 금지.
- 순수 함수 = DB/Redis 없이 테스트 가능, 가격·배당은 호출자 주입.
- 019 코드 수정/제거 금지(데이터 레이어만 재사용).
- 프론트 .js/.ts 쌍 동시. code_comments ko. gh CLI 미설치.
- @MX 한국어 + [AUTO]. ANCHOR: `calculate_drip_projection`·`DividendSummary`·`DRIPProjection`.

## 작업 순서

M1 스키마+순수함수+테스트(T-001~003) → M2 날짜추출+서비스(T-005,T-004) → M3 라우터(T-006) → M4 프론트(T-007).
