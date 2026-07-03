# SPEC-STOCK-030 구현 계획 (Implementation Plan)

> 포트폴리오 기간별 성과 요약(YTD/1M/3M/6M/1Y). TDD(RED-GREEN-REFACTOR) 방법론.

---

## 1. 작업 분해 (Task Decomposition)

| Task | 내용 | 산출물 | 우선순위 |
|------|------|--------|---------|
| **T-001** | `schemas.py`에 `PerformanceSummaryResponse`·`PeriodPerformance` 스키마 추가 | `portfolio/schemas.py` 수정 | High |
| **T-002** | `performance_summary.py` 핵심 서비스 구현(`_compute_period_dates`, `_compute_period_returns`, `calculate_performance_summary`) | `portfolio/performance_summary.py` 신규 | High |
| **T-003** | `router.py`에 `GET /performance-summary` 엔드포인트 추가(`refresh` query param) | `portfolio/router.py` 수정 | High |
| **T-004** | 단위 테스트 작성(30개 이상) | `tests/unit/test_portfolio_performance_summary.py` 신규 | High |
| **T-005** | 통합 테스트 작성 | `tests/integration/test_portfolio_performance_summary_router.py` 신규 | High |
| **T-006** | `PerformanceSummaryPanel.js` 컴포넌트 생성(5개 기간 카드) | `frontend/src/components/PerformanceSummaryPanel.js` 신규 | Medium |
| **T-007** | `portfolio.js` API 클라이언트에 `apiGetPerformanceSummary` 추가 | `frontend/src/api/portfolio.js` 수정 | Medium |
| **T-008** | `Portfolio.js`에 `PerformanceSummaryPanel` 통합 | `frontend/src/pages/Portfolio.js` 수정 | Medium |
| **T-009** | `portfolio.ts` TypeScript 인터페이스 추가(선택적) | `frontend/src/api/portfolio.ts`·`pages/Portfolio.tsx` 수정 | Low |
| **T-010** | MX 태그 검수 및 정리 | 전체 신규/수정 파일 | Low |

### 마일스톤 그룹핑

- **M1 (백엔드 코어)**: T-001 → T-002 → T-003. 스키마 → 서비스 → 라우터 순서(의존성 순).
- **M2 (백엔드 테스트)**: T-004 → T-005. TDD 원칙상 RED 단계는 각 구현(T-002·T-003) 전에 실패 테스트로 선행.
- **M3 (프론트엔드)**: T-006 → T-007 → T-008 → T-009.
- **M4 (마무리)**: T-010.

> TDD 적용: T-002·T-003 구현 전 T-004·T-005의 해당 테스트를 먼저 작성하여 RED 확인 후 GREEN으로 구현.

---

## 2. 기술 스택 (Technology Stack)

| 계층 | 기술 | 비고 |
|------|------|------|
| 언어 | Python 3.11 | `target-version = "py311"` |
| 웹 프레임워크 | FastAPI | 기존 `portfolio/router.py` 확장 |
| 수치 계산 | numpy(>=1.26) | **scipy 금지** — numpy + math만 |
| 시세 데이터 | FinanceDataReader(>=0.9) | 기존 `_fetch_price_series_sync` 재사용 |
| 캐싱 | Redis(redis.asyncio) | 키 `portfolio_perf_summary:{id}:{date}`, TTL 3600s |
| DB | PostgreSQL(asyncpg) | 신규 테이블 없음(0018 유지) |
| 프론트엔드 | React | 5개 기간 카드 |
| 차트 | Recharts | (선택적) 카드 내 미니 트렌드 |
| 테스트 | pytest + pytest-asyncio | 단위 + 통합 |

신규 라이브러리 도입 없음. 모든 의존성은 pyproject.toml에 이미 존재.

---

## 3. 구현 상세 접근 (Reference Implementations)

research.md에서 식별한 재사용 패턴(파일·라인).

### 3.1 시세 조회·정렬 (T-002)

- `_fetch_price_series_sync()` — `backtest.py:149-197`. 동기 FDR 조회, 실패 시 빈 리스트. `run_in_executor`로 격리.
- `_align_close_series()` — `backtest.py:45-73`. 공통 거래일 inner join.
- `_compute_returns()` — `backtest.py:113-144`. 누적 수익률 산출(본 SPEC은 누적값만 추출).

### 3.2 비동기 병렬 (T-002, NFR-002)

- `risk_analysis.py:276-280` / `backtest.py:250-256` — `loop.run_in_executor(None, _fetch_price_series_sync, ...)` + `asyncio.gather`.
- 최적화: 1Y 구간을 1회 조회 후 기간별 슬라이싱 재사용 가능(FDR 호출 최소화).

### 3.3 Redis 캐싱 (T-002, REQ-PS-004·007)

- 캐시 읽기: `risk_analysis.py:263-273` — `redis.get(cache_key)` + `model_validate_json`, 예외 graceful.
- 캐시 쓰기: `risk_analysis.py:395-399` — `redis.setex(cache_key, TTL, model_dump_json())`, 예외 graceful.
- 키 형식: `portfolio_perf_summary:{portfolio_id}:{today_kst}`(일별 갱신, 5개 기간 단일 엔트리).

### 3.4 소유권·라우터 (T-003, REQ-PS-001)

- `get_portfolio_with_holdings()` — `service.py:87-100`.
- 라우터 패턴: `router.py:157-180`(risk-analysis GET 엔드포인트, query param + DI).
- 소유권 불일치(타사용자 포함) 시 404(코드베이스 관례: get_portfolio_with_holdings user_id 필터).

### 3.5 스키마 (T-001, REQ-PS-003)

- `BacktestResult`/`DailyReturn` — `schemas.py:282-305`. Pydantic v2, validator 없는 응답 스키마 패턴.
- `model_validator(mode="after")` 패턴 — `schemas.py:265-279`(검증 필요 시).

### 3.6 환율 (T-002, REQ-PS-006, NFR-005)

- `get_usd_krw_rate(redis)` — `fx_rate.py:47-84`. 실패 시 `_FALLBACK_RATE`(1350.0).

### 3.7 프론트엔드 (T-006·T-007·T-008)

- 카드 레이아웃: `BacktestPanel.js` — `gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))'`.
- async state: `BacktestPanel.js:24-56` — loading/error/result 패턴.
- API 클라이언트: `portfolio.js:79-91`(`apiGetRiskAnalysis`, query params 패턴).

---

## 4. 리스크 분석 (Risk Analysis)

| 리스크 | 영향 | 완화책 |
|--------|------|--------|
| **FDR API 실패** | 시세 조회 불가 → 성과 계산 불가 | NFR-004: 종목/기간 제외 또는 빈 데이터 반환, 예외 비전파(`_fetch_price_series_sync` 빈 리스트 패턴 재사용) |
| **빈 포트폴리오** | 보유 종목 0개 | REQ-PS-005: 200 OK + 5개 기간 빈 데이터(4xx 아님). 보유 종목 0 검사 선행 |
| **YTD 경계 케이스** | 1월 1~2일에는 YTD 거래일이 0~1일 | REQ-PS-008: 유효 거래일 < 2일 시 해당 기간 빈 데이터(`has_data=false`). 추측 단언 금지 |
| **신규 상장 종목** | 1Y 시작일 이전 데이터 없음 | REQ-PS-008: 가용한 가장 이른 거래일 기준 또는 빈 데이터 |
| **환율 조회 실패** | 해외 종목 KRW 환산 불가 | NFR-005: fallback 1350.0 사용, 계산 중단 없음 |
| **캐시 stale(일중 변동)** | 일별 캐시로 당일 가격 변동 미반영 | 의도된 동작(일별 갱신). `refresh=true`로 강제 갱신 제공(REQ-PS-007) |
| **공통 거래일 불일치** | KRX·해외 휴장일 차이 | `_align_close_series` inner join으로 공통일만 사용 |
| **연환산 계산 분모 0** | 거래일수 0 또는 1 | 거래일 < 2일 가드(빈 데이터 처리)로 분모 0 회피 |

---

## 5. 검증 전략 (Test Strategy)

### 5.1 단위 테스트 (T-004, 30개 이상)

- **스키마 검증**: `PeriodPerformance`·`PerformanceSummaryResponse` 필드 직렬화/역직렬화.
- **기간 시작일 산출**(`_compute_period_dates`): YTD(1월 1일)·1M·3M·6M·1Y 각각, YTD 경계(1월 초).
- **수익률 산출**(`_compute_period_returns`): 양수·음수 수익률, 연환산 산식, MDD 산식, 거래일 < 2일 가드.
- **빈 포트폴리오**: 보유 종목 0개 → 빈 응답.
- **혼합 통화**: KRX + 해외 종목 USD→KRW 환산.
- **scipy 미사용 검증**: import 정적 검사 또는 모듈 의존성 점검.

### 5.2 통합 테스트 (T-005)

- `GET /performance-summary` 200(정상 5기간).
- 캐시 히트(refresh=false) → FDR 미호출.
- 캐시 갱신(refresh=true) → 재계산.
- 빈 포트폴리오 → 200 + 빈 데이터.
- 타사용자 포트폴리오(소유권 불일치) → 404.
- 미인증 → 401.
- 존재하지 않는 포트폴리오 → 404.

### 5.3 커버리지 목표 (NFR-003)

`performance_summary.py` 서비스·순수 함수 85% 이상. `router.py` 추가분은 omit 대상 가능(pyproject `omit` 패턴 확인).

---

## 6. 구현 순서 요약

1. **M1**: T-001(스키마) → [RED 테스트] → T-002(서비스) → [RED 테스트] → T-003(라우터).
2. **M2**: T-004·T-005 GREEN 완료 + 커버리지 85% 달성.
3. **M3**: T-006 → T-007 → T-008 → (선택)T-009.
4. **M4**: T-010 MX 태그 검수.

각 단위 완료 후 진행 상황을 `progress.md`에 기록한다.
