# SPEC-STOCK-033 구현 계획 (Implementation Plan)

> 작업 분해(T-001~T-007). 시간 추정 금지 — 우선순위 라벨·단계 순서로 표기.

## 0. 전제 (Preconditions)

- 브랜치: `feature/SPEC-STOCK-033`.
- 개발 방법론: quality.yaml `development_mode` 기준(TDD 기본). 브라운필드 — 기존 동작 보존.
- **SPEC-019 재사용 원칙**: 배당 데이터 조회는 `dividends.get_dividend_info`에 위임. 019 코드 수정 금지(날짜 추출 확장만 예외적 허용).
- 신규 DB 테이블·마이그레이션 없음.

## 1. 작업 분해

### T-001 — 스키마 정의 (Priority: High)

- `portfolio/schemas.py`에 6종 추가: `HoldingDividendYield`, `DividendSummary`, `DividendEvent`, `DividendCalendar`, `DRIPYearData`, `DRIPProjection`.
- Pydantic v2, `date`/`Optional` import 확인(이미 존재).
- 019 스키마와 이름 충돌 없음 검증.
- @MX:ANCHOR on `DividendSummary`·`DRIPProjection`(fan_in ≥ 3 예상).

### T-002 — 순수 함수 구현 (Priority: High) [핵심]

- 신규 모듈 `portfolio/dividend_yield.py`.
- `calculate_dividend_summary(holdings, prices) -> DividendSummary` — 종목별 수익률·가중 평균(spec §5.1.1).
- `calculate_dividend_calendar(holdings, dividend_history, year) -> DividendCalendar` — 날짜 정밀 월별 그룹(§5.1.2).
- `calculate_drip_projection(initial_value, dividend_yield_pct, years, reinvest_rate) -> DRIPProjection` — 단순 복리(§5.1.3). **핵심 신규.**
- 모듈 상단 @MX:NOTE: scipy 금지·numpy/math 전용, DRIP 단순 복리 모델 명시.
- @MX:ANCHOR on `calculate_drip_projection`.
- DB·Redis·외부 API 의존 없음(REQ-DVY-NFR-002).
- 의존: T-001.

### T-003 — 순수 함수 단위 테스트 (Priority: High)

- `backend/tests/unit/test_dividend_yield.py`.
- BDD 시나리오 1·3·4·5·7 + 엣지 E1~E8, E10 커버.
- DRIP reinvest_rate=1.0/0.0/부분값, yield=0 경계.
- 가중 평균·미확보 종목 0 처리.
- 커버리지 85% 이상(REQ-DVY-NFR-005).
- 의존: T-002.

### T-004 — 서비스 오케스트레이션 (Priority: High)

- `portfolio/dividend_yield.py`에 서비스 함수 3종 추가(또는 동일 모듈):
  - 배당 요약: 소유권 확인 → `get_dividend_info` 배당 조회 → 현재가 KRW 환산 → `calculate_dividend_summary`.
  - 배당 캘린더: 소유권 확인 → 배당기준일 조회 → `calculate_dividend_calendar`.
  - DRIP: 소유권 확인 → 요약 재사용(yield·평가액) → `calculate_drip_projection`.
- 소유권 None → 404(REQ-DVY-005). 현재가/배당 미확보 graceful degradation.
- SPEC-019 `get_dividend_info` 재사용(신규 FDR 로직 금지).
- @MX:WARN on KRW 환산·부동소수 누적부.
- 의존: T-002, (필요 시) T-005.

### T-005 — 배당기준일 날짜 추출 확장 (Priority: Medium)

- `portfolio/dividends.py` `_extract_ex_month`를 전체 날짜(`ex_dividend_date: date`) 추출로 확장하거나, `dividend_yield.py`에 보조 추출 함수 신설.
- **019 기존 동작 보존**: `get_dividend_info` 반환 구조에 `ex_dividend_date` 추가 시 기존 `ex_dividend_month` 유지(하위 호환).
- 미확보 시 None(REQ-DVY-NFR-003).
- 의존: 없음(T-004와 병행 가능).

### T-006 — 라우터 엔드포인트 (Priority: High)

- `portfolio/router.py`에 3종 추가:
  - `GET /portfolios/{portfolio_id}/dividend/summary`.
  - `GET /portfolios/{portfolio_id}/dividend/calendar?year=`(기본 당해연도).
  - `GET /portfolios/{portfolio_id}/dividend/drip?years=&reinvest_rate=`(기본 10/1.0).
- `years`/`reinvest_rate` 입력 검증(엣지 E4/E5).
- 소유권 불일치 404.
- 기존 `Depends` 패턴 재사용. 019 `/dividends` 경로 미충돌 확인.
- 서비스 단위 테스트(소유권 404, 정상 응답, 빈 포트폴리오).
- 의존: T-001, T-004.

### T-007 — 프론트엔드 (Priority: Medium)

- `frontend/src/components/DividendSummaryPanel.js` — 배당 요약 표.
- `frontend/src/components/DividendCalendarView.js` — 월별 캘린더.
- `frontend/src/components/DRIPSimulator.js` — years/reinvest_rate 입력 + 연도별 투영.
- `frontend/src/api/portfolio.js`(+`.ts`) — `apiGetDividendSummary`·`apiGetDividendCalendar`·`apiGetDRIPProjection`.
- `frontend/src/pages/Portfolio.js`(+`.tsx`) — 배당 분석 섹션 통합(기존 보존).
- `.js`/`.ts` 쌍 동시 수정.
- 의존: T-006.

## 2. 작업 순서 (Milestones)

| 단계 | 작업 | 산출물 |
|------|------|--------|
| M1 | T-001 → T-002 → T-003 | 스키마 + 순수 함수 + 테스트(핵심 로직 검증) |
| M2 | T-005 → T-004 | 날짜 추출 + 서비스 오케스트레이션 |
| M3 | T-006 | 엔드포인트 3종 + 서비스 테스트 |
| M4 | T-007 | 프론트 UI |

M1 완료 시 핵심 가치(DRIP·요약 계산)가 테스트로 검증된다. M2~M3에서 통합, M4에서 UI.

## 3. 검증 게이트

- 각 작업 후 `ruff check` 통과.
- T-003·T-006 후 `pytest --cov` 85% 이상.
- scipy import 부재 확인(grep).
- 019 회귀 없음 — 기존 `test` 배당 테스트 통과 유지.
- @MX 태그 한국어 + [AUTO] 접두사.

## 4. 위험·완화 (요약)

- SPEC-019 중복 → 데이터 레이어 재사용으로 회피(연구 §0·spec §2.2).
- 배당기준일 날짜 미확보 → Optional[date] None 처리.
- DRIP 비현실성 → 면책 문구·보수적 단순 복리.
- 자세한 위험은 research.md §6 참조.
