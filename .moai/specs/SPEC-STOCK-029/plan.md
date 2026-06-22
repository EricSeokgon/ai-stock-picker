# SPEC-STOCK-029 구현 계획 — 포트폴리오 백테스팅

대상 SPEC: SPEC-STOCK-029
개발 방법론: TDD (RED-GREEN-REFACTOR, `quality.yaml` 기준)
커버리지 기준: 75% (`pyproject.toml` `fail_under = 75`)

---

## 1. 개요

사용자 보유 포트폴리오를 특정 기간 보유했다고 가정한 수익률 시뮬레이션. portfolio 도메인 신규 모듈 `portfolio/backtest.py`로 구현하며, 기존 전략 백테스트(`backtest/` 패키지, SPEC-012)와 독립적으로 유지한다. 기존 `backtest/metrics.py` 순수 함수와 SPEC-028 환율·해외 가격 인프라를 재사용한다.

---

## 2. 작업 분해 (Task Decomposition)

TDD 순서: 각 백엔드 태스크는 RED(실패 테스트) → GREEN(최소 구현) → REFACTOR.

### T-001: 백테스트 스키마 정의 (RED 선행)
- 파일: `backend/src/stock_picker/portfolio/schemas.py` (추가)
- `BacktestRequest`(start_date, end_date, `field_validator`로 end > start 검증)
- `DailyReturn`(date, portfolio_value, daily_return, cumulative_return)
- `BacktestResult`(daily, mdd, sharpe_ratio, total_return, period_days, excluded_tickers, used_tickers, disclaimer)
- 테스트: `test_portfolio_backtest.py`에 스키마 검증 단위 테스트(날짜 역전 시 ValidationError)
- 커버: REQ-PBT-020, REQ-PBT-040, REQ-PBT-041, REQ-PBT-042

### T-002: 순수 함수 레이어 (RED → GREEN)
- 파일: `backend/src/stock_picker/portfolio/backtest.py` (신규)
- 순수 함수: `_normalize_weights`, `_daily_portfolio_values`(공통 거래일 정렬·비중 적용), `_daily_returns`, `_cumulative_returns`
- 공통 거래일 정렬은 `risk_analysis._align_returns` 패턴 참고
- 테스트: 단일 종목(가치 = 종가 비율), 다종목 가중합, 비중 정규화, 빈 입력 가드
- 커버: REQ-PBT-001, REQ-PBT-002, REQ-PBT-005, REQ-PBT-012, REQ-PBT-023

### T-003: 지표 계산 재사용 검증 (RED → GREEN)
- `backtest/metrics.calculate_max_drawdown`·`calculate_sharpe_ratio(risk_free_rate=0.035)` import 재사용
- 테스트: MDD 음수 검증, 샤프 비율 무위험 0.035 전달 시 결과 검증
- 커버: REQ-PBT-003, REQ-PBT-004

### T-004: FDR 기간 시세 조회 헬퍼 (RED → GREEN)
- 파일: `backend/src/stock_picker/portfolio/backtest.py`
- `_fetch_price_series_sync(ticker, start, end) -> list[dict]`(동기, `run_in_executor` 전용, `@MX:WARN`)
- KRX/해외 공통 FDR 조회, Close 컬럼 탐색, NaN 제거
- 테스트: FDR mock으로 시계열 반환·빈 데이터 graceful
- 커버: REQ-PBT-010, REQ-PBT-011, REQ-PBT-014

### T-005: 오케스트레이션 함수 (RED → GREEN → REFACTOR)
- 파일: `backend/src/stock_picker/portfolio/backtest.py`
- `run_portfolio_backtest(portfolio_id, user_id, db, redis, start_date, end_date)` (`@MX:ANCHOR`)
  1. 소유권 확인(404) → 2. 입력 검증(400) → 3. FDR 병렬 조회(`asyncio.gather`) → 4. 실패 종목 제외, 유효 0개 시 422 → 5. 환율(해외 시, fallback) → 6. 순수 함수 계산 → 7. `BacktestResult` 구성
- 테스트: happy path, 날짜 역전(400), 종목 없음(400), 유효 종목 0개(422), 종목 일부 제외, 해외 자산 KRW 환산, 환율 실패 fallback, 소유권 없음(404)
- 커버: REQ-PBT-005, 013, 014, 015, 021, 022, 024, 030, 031, NFR-002

### T-006: API 엔드포인트 (커버리지 제외)
- 파일: `backend/src/stock_picker/portfolio/router.py` (추가)
- `POST /portfolios/{portfolio_id}/backtest` (async, 인증·소유권·redis 주입)
- 통합 테스트: `tests/integration/`에 200/400/404/422 시나리오
- 커버: REQ-PBT-030, REQ-PBT-031, REQ-PBT-040, REQ-PBT-NFR-003

### T-007: 프론트엔드 API 클라이언트
- 파일: `frontend/src/api/portfolio.ts` (+ 빌드 산출물 `.js`)
- `apiRunPortfolioBacktest(token, portfolioId, body)` + `BacktestRequest`/`BacktestResult`/`DailyReturn` 타입 (`@MX:ANCHOR`)
- 커버: REQ-PBT-050

### T-008: 프론트엔드 컴포넌트
- 파일: `frontend/src/components/BacktestChart.js`(Recharts 라인 차트), `frontend/src/components/BacktestPanel.js`(기간 입력·실행·요약)
- 파일: `frontend/src/pages/Portfolio.tsx` (+ `.js`) — BacktestPanel 통합
- 기존 전략 `Backtest.tsx`와 구분 주석 명시
- 커버: REQ-PBT-050, 051, 052, 053

---

## 3. 마일스톤 (우선순위 기반)

- **M1 (우선순위 High)**: T-001 ~ T-003 — 스키마 + 순수 함수 + 지표 재사용. 백테스트 계산 핵심 로직 완성.
- **M2 (우선순위 High)**: T-004 ~ T-005 — FDR 조회 + 오케스트레이션. 해외 자산·예외 처리 포함.
- **M3 (우선순위 Medium)**: T-006 — API 엔드포인트 + 통합 테스트.
- **M4 (우선순위 Medium)**: T-007 ~ T-008 — 프론트엔드 API + 차트/패널.

순서: M1 완료 후 M2, M2 완료 후 M3, M3 완료 후 M4.

---

## 4. 파일 소유권 맵 (File Ownership)

### Backend
| 파일 | 작업 | 소유 태스크 |
|------|------|-----------|
| `portfolio/schemas.py` | 추가(BacktestRequest/Result/DailyReturn) | T-001 |
| `portfolio/backtest.py` | 신규(순수 함수 + FDR + 오케스트레이션) | T-002,003,004,005 |
| `portfolio/router.py` | 추가(POST /backtest 엔드포인트) | T-006 |

### Frontend
| 파일 | 작업 | 소유 태스크 |
|------|------|-----------|
| `frontend/src/api/portfolio.ts` (+`.js`) | 추가(apiRunPortfolioBacktest·타입) | T-007 |
| `frontend/src/components/BacktestChart.js` | 신규 | T-008 |
| `frontend/src/components/BacktestPanel.js` | 신규 | T-008 |
| `frontend/src/pages/Portfolio.tsx` (+`.js`) | 추가(패널 통합) | T-008 |

### Tests (TDD)
| 파일 | 작업 | 소유 태스크 |
|------|------|-----------|
| `backend/tests/unit/test_portfolio_backtest.py` | 신규(순수 함수·오케스트레이션) | T-001~T-005 |
| `backend/tests/integration/test_portfolio_backtest_router.py` | 신규(API 200/400/404/422) | T-006 |

> **명명 주의**: 테스트 파일은 `test_portfolio_backtest.py`(기존 `test_backtest_metrics.py`/`test_backtest_runner.py`와 충돌 회피). 컴포넌트는 `BacktestChart`/`BacktestPanel`(portfolio 도메인 — 기존 전략 `Backtest.tsx`와 구분 주석).

---

## 5. 리스크 분석

| 리스크 | 영향 | 완화 방안 |
|--------|------|----------|
| **이름·기능 혼동**(기존 backtest/ 전략 백테스트 vs 포트폴리오 백테스트) | 높음 | portfolio 도메인 분리, `REQ-PBT-*` 접두사, `test_portfolio_backtest.py`, 구분 주석. 기존 `backtest/` 미수정. |
| **FDR 레이트 리밋·차단** | 중간 | SPEC-028 Redis 캐시 재사용(NFR-002), `run_in_executor` 격리, `asyncio.gather` 병렬이되 종목 수 제한 고려 |
| **numpy 부동소수 정밀도** | 낮음 | `pytest.approx`로 테스트, MDD/Sharpe는 기존 검증된 `metrics.py` 재사용 |
| **긴 날짜 구간**(다년치 시세) | 중간 | 거래일 단위 계산은 선형 복잡도. 응답 크기는 daily 배열에 비례 — 필요 시 향후 다운샘플링(본 SPEC 범위 밖) |
| **공통 거래일 부족**(KRX·해외 휴장일 불일치) | 중간 | inner join으로 공통 거래일만 사용, 부족 시 종목 제외(REQ-PBT-014) |
| **환율 변동에 의한 해외 가치 왜곡** | 낮음 | 일별 종가 비율 기반 정규화이므로 단일 환율 스냅샷으로 KRW 환산 시 비율 보존(상대 수익률 왜곡 최소). fallback 1350.0 사용 |
| **비중 합 ≠ 100%** | 낮음 | 정규화(REQ-PBT-023)로 처리 |

---

## 6. 완료 정의 (Definition of Done)

- 모든 REQ-PBT-* 요구사항 구현
- TDD 사이클(RED-GREEN-REFACTOR) 완료, `test_portfolio_backtest.py` 전부 통과
- `portfolio/backtest.py` 커버리지 75% 이상
- ruff check 통과, scipy import 없음(NFR-001)
- MX 태그 부여(ANCHOR·NOTE·WARN, REASON 포함)
- 기존 `backtest/` 패키지·기존 테스트 무영향(회귀 없음)
- 프론트엔드 차트·패널 정상 렌더, 오류 처리 동작
