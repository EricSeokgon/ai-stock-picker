# SPEC-STOCK-028 구현 계획 (Tasks) — 해외 자산 지원

> 작성: 2026-06-18 · 개발 모드: TDD (RED-GREEN-REFACTOR, 브라운필드 확장) · 브랜치: feature/SPEC-STOCK-028

---

## Plan Summary (계획 요약)

기존 KRX 전용 포트폴리오 도메인을 미국 주식(NYSE/NASDAQ)·해외 ETF까지 확장한다. 핵심 전략은 **하위호환 우선 + 점진적 확장**이다.

- **DB 전략**: `krx_code` 컬럼명은 유지(ticker 식별자로 재해석)하고 `market`·`currency` 2개 컬럼만 추가(옵션 A). rename 없이 마이그레이션을 단순화한다. 기존 행은 `market='KRX'`·`currency='KRW'` 기본값으로 의미를 보존한다.
- **신규 모듈**: 환율 서비스(`fx_rate.py`)를 신설하되, 기존 `dividends.py`/`risk_analysis.py`의 검증된 패턴(`run_in_executor` 동기 FDR 격리 + Redis TTL 캐시 + graceful fallback)을 그대로 차용한다.
- **계산 통일**: 모든 평가금액·비중을 KRW 단위로 통일한다. USD 종목은 성과 계산 시점에만 실시간 환율로 환산한다(매수단가는 원통화 그대로 저장하여 환율 왜곡 방지).
- **TDD 순서**: DB/스키마 기반(컬럼·검증) → 환율 서비스(독립, 의존 없음) → 성과 계산 → 리스크 분석 → AI 최적화 → 프론트엔드 순으로 의존성 역방향 차단 없이 진행한다.

**중요한 발견(SPEC 가정 검증)**: 현재 `portfolio_holdings` 테이블에는 **기존 유니크 제약이 존재하지 않는다**(models.py 확인 완료). 따라서 REQ-FOREX-082("기존 유니크 제약이 존재하는 경우")의 전제는 충족되지 않으며, 마이그레이션은 **제약 변경(drop+create)이 아니라 신규 유니크 제약 생성**으로 처리해야 한다. AC-11의 "고유 제약을 원래대로 복원"은 "downgrade 시 신규 제약 제거"로 해석한다. 이 차이는 구현 시 manager-tdd에 반드시 전달해야 한다.

---

## Implementation Phases (의존성 순서)

### Phase 1: DB 모델 + 마이그레이션 (기반)
- **Files**:
  - `backend/src/stock_picker/db/models.py` (PortfolioHolding 확장)
  - `backend/alembic/versions/0019_portfolio_foreign_asset.py` (신규)
- **Requirements**: REQ-FOREX-001, 002, 003, 004, 080, 081, 082, 084
- **TDD 접근**:
  - RED: `tests/unit/test_migration_0019.py`(또는 모델 속성 테스트) — `PortfolioHolding`에 `market`·`currency` 속성이 존재하고 기본값이 `'KRX'`/`'KRW'`인지 확인하는 실패 테스트.
  - GREEN: models.py에 `market: Mapped[str] = mapped_column(String(10), nullable=False, server_default="KRX")`, `currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="KRW")` 추가. `__table_args__`에 `UniqueConstraint("portfolio_id", "krx_code", "market", name="uq_holding_portfolio_ticker_market")` 추가. 마이그레이션 0019에서 `op.add_column` 2개(server_default 포함) + `op.create_unique_constraint`. downgrade에서 역순 제거.
  - REFACTOR: server_default를 통한 기존 행 backfill 확인, @MX:NOTE 추가.

### Phase 2: 환율 서비스 (독립 신규 모듈)
- **Files**: `backend/src/stock_picker/portfolio/fx_rate.py` (신규)
- **Requirements**: REQ-FOREX-020, 021, 022, 023, 024, 025, NFR-002, NFR-003, 084
- **TDD 접근**:
  - RED: `tests/unit/test_fx_rate.py` — (a) 캐시 미스 시 FDR 조회 후 Redis setex 호출(TTL≥3600) 검증, (b) 캐시 히트 시 외부 조회 안 함, (c) FDR·캐시 모두 실패 시 `1350.0` 반환 + WARNING 로그, (d) 키가 KST 일 단위(`fx:USD:KRW:{today}`)인지.
  - GREEN: `async def get_usd_krw_rate(redis) -> float` 구현. `dividends.py` 패턴 차용 — `_fetch_usd_krw_sync()` 동기 FDR(`fdr.DataReader("USD/KRW")`) + `loop.run_in_executor(None, ...)`. Redis get/setex. 예외는 모두 try/except로 잡아 fallback `_FALLBACK_RATE = 1350.0` 반환.
  - REFACTOR: 상수 정리(`_FX_TTL = 3600`, `_FALLBACK_RATE`), @MX:ANCHOR(fan_in≥3 예상: service·risk·관련 테스트) + @MX:REASON.

### Phase 3: 스키마 확장 + 서버 측 검증
- **Files**: `backend/src/stock_picker/portfolio/schemas.py`
- **Requirements**: REQ-FOREX-010, 011, 012, 013, 014, 015, 005, 039
- **TDD 접근**:
  - RED: `test_portfolio_service.py`(또는 `test_portfolio_router.py`)에 — (a) `HoldingCreate(market="NASDAQ", currency="USD")` 통과, (b) 생략 시 기본값 `KRX`/`KRW`, (c) `market="KRX", currency="USD"` 조합 거부(ValidationError → 422), (d) 허용 외 값 422.
  - GREEN: `HoldingCreate`에 `market: Literal["KRX","NYSE","NASDAQ"] = "KRX"`, `currency: Literal["KRW","USD"] = "KRW"` 추가. `@model_validator(mode="after")`로 시장-통화 조합 일관성 검증(KRX↔KRW, NYSE/NASDAQ↔USD). `HoldingResponse`에 `market`·`currency` 추가. `HoldingPerformance`에 `market`·`currency`·`current_price_krw`(또는 KRW 환산 평가금액)·`fx_rate_used` 필드 추가.
  - REFACTOR: validator 메시지 한국어화, model_config 정리.

### Phase 4: 성과 계산 해외 종목 지원
- **Files**:
  - `backend/src/stock_picker/portfolio/service.py` (add_holding, calculate_performance)
  - `backend/src/stock_picker/portfolio/router.py` (add_holding 파라미터 통과 + 409 처리)
- **Requirements**: REQ-FOREX-016, 030~040, 083, NFR-001, NFR-003
- **TDD 접근**:
  - RED: `test_portfolio_service.py` 확장 — (a) NASDAQ 종목 USD 현재가 → KRW 환산 검증(환율 mock), (b) USD avg_buy_price도 KRW 환산하여 수익률 계산, (c) 전체 평가금액 KRW 통일 집계, (d) 응답에 `fx_rate_used` 포함, (e) 환율 fallback 시에도 계산 완료(1350.0), (f) 해외 종목 가격 조회 실패 시 `price_unavailable` graceful 제외, (g) 해외 종목 섹터 `null`/`""` 반환 + 예외 없음, (h) KRX 경로 무변경(회귀). 라우터: (i) 중복 `(portfolio_id, krx_code, market)` 등록 시 409.
  - GREEN: `add_holding`에 `market`/`currency` 파라미터 추가. `calculate_performance`를 async로 전환(또는 내부에서 환율·해외가 조회) — `market != 'KRX'`이면 해외 USD 종가 조회(신규 `_fetch_foreign_price` 동기 FDR + run_in_executor, Redis TTL≥86400) 후 `fx_rate` 곱셈. KRX 경로는 기존 `get_current_price` 유지. 라우터 `add_holding`에서 IntegrityError → `409 Conflict` 변환.
  - REFACTOR: 통화 환산 로직을 헬퍼로 추출, @MX 갱신.
  - **주의**: `calculate_performance`가 동기→비동기 전환되면 `router.get_performance`도 async + `await`로 수정 필요(연쇄 변경). risk_analysis.py가 `portfolio_service.get_portfolio_with_holdings`만 사용하므로 영향 없음.

### Phase 5: 리스크 분석 해외 종목 지원
- **Files**: `backend/src/stock_picker/portfolio/risk_analysis.py`
- **Requirements**: REQ-FOREX-050, 051, 052, 053, 054, 055, NFR-004
- **TDD 접근**:
  - RED: `test_portfolio_risk.py`(기존) 확장 — (a) KRX+NASDAQ 혼합 시 해외 종가 시계열 조회되어 corr/vol에 포함, (b) USD 종가는 변환 없이 사용(상관계수 통화 불변), (c) 비중은 KRW 환산 평가금액 기준, (d) 해외 데이터 부족 시 기존처럼 제외, (e) 응답 스키마 구조 무변경.
  - GREEN: `_fetch_stock_prices`는 FDR `DataReader`를 이미 사용하므로 ticker가 해외여도 동작(검증 필요). 변경 핵심은 **비중 산정** — `weights_raw` 계산 시 `market=='USD'` 종목은 KRW 환산 평가금액 사용(환율 1회 조회 후 곱셈). corr/vol은 USD 종가 그대로.
  - REFACTOR: 비중 계산 헬퍼 공유 검토, @MX 갱신.

### Phase 6: AI 최적화 + AI 분석 market 정보 포함
- **Files**:
  - `backend/src/stock_picker/portfolio/service.py` (optimize_portfolio)
  - `backend/src/stock_picker/portfolio/ai_analysis.py` (_build_portfolio_data, optimize_portfolio_with_claude)
- **Requirements**: REQ-FOREX-060, 061, 062, 063, 064, 065
- **TDD 접근**:
  - RED: `test_ai_analysis.py`(기존) 확장 + `test_portfolio_optimize.py` — (a) 프롬프트/holdings_data에 `market`·`currency` 포함, (b) weight_pct·평가금액 KRW 환산 통일, (c) `new_stocks`가 KRX `recommendations` 범위로 한정(기존 필터 유지·검증), (d) Claude 실패 시 예외 미전파·오류 dict 반환(기존 동작 보존).
  - GREEN: `_build_portfolio_data`·`optimize_portfolio`의 `holdings_data`에 `"market"`, `"currency"` 키 추가. KRW 환산 평가금액으로 `total_value`·`weight_pct` 계산(환율 1회 조회). Claude 모델·호출 패턴은 무변경.
  - REFACTOR: 환산 로직 중복 제거, @MX 갱신.

### Phase 7: 프론트엔드 market 선택 UI
- **Files**:
  - `frontend/src/api/portfolio.ts` (Holding·HoldingCreate 타입, apiAddHolding 시그니처)
  - `frontend/src/pages/Portfolio.tsx` (PortfolioDetail 폼 + 목록 표시)
- **Requirements**: REQ-FOREX-070, 071, 072, 073, 074, 075
- **TDD 접근**:
  - RED: 프론트 단위 테스트 환경이 없으면 타입 컴파일(tsc) + 수동 시나리오로 대체. 가능 시 컴포넌트 테스트(market 선택 시 currency 자동 설정).
  - GREEN: `Holding`·`HoldingPerformance` 인터페이스에 `market`·`currency`(+ KRW 환산 필드) 추가. `apiAddHolding`에 `market`/`currency` 인자 추가(기본값 `'KRX'`/`'KRW'`로 하위호환). `PortfolioDetail`에 `market` select(KRX/NYSE/NASDAQ) 추가, 선택 시 currency 자동 설정(useState). 목록에 market 배지 + KRW 환산 평가금액 표시.
  - REFACTOR: 배지 스타일 정리, KRX 종목 기존 표시 무변경 확인.

---

## Task Decomposition Table

| Task ID | Description | Files | REQ Coverage | Dependencies | Priority |
|---------|-------------|-------|--------------|--------------|----------|
| T-001 | PortfolioHolding에 market·currency 컬럼 + 유니크 제약 추가 | models.py | REQ-001,002,003,082 | - | High |
| T-002 | Alembic 0019 마이그레이션 (add_column×2 + 신규 unique constraint, downgrade 복원) | alembic/versions/0019_portfolio_foreign_asset.py | REQ-004,080,081,082 | T-001 | High |
| T-003 | 환율 서비스 fx_rate.py (FDR+Redis 캐시+fallback 1350.0) | fx_rate.py, test_fx_rate.py | REQ-020~025,084,NFR-002,NFR-003 | - | High |
| T-004 | HoldingCreate/Response/Performance 스키마 확장 + 시장-통화 조합 검증 | schemas.py | REQ-010~016,005,015,039 | T-001 | High |
| T-005 | add_holding market/currency 파라미터 + 라우터 409 처리 | service.py, router.py | REQ-083 | T-001,T-004 | High |
| T-006 | calculate_performance 해외 USD→KRW 환산·집계·섹터 null·graceful·fx_rate_used | service.py, router.py, test_portfolio_service.py | REQ-016,030~040,NFR-001,NFR-003 | T-003,T-004 | High |
| T-007 | risk_analysis 해외 ticker 포함 + KRW 환산 비중 산정 | risk_analysis.py, test_portfolio_risk.py | REQ-050~055,NFR-004 | T-003 | Medium |
| T-008 | AI 최적화/분석 프롬프트에 market·currency + KRW 환산 비중 + new_stocks KRX 한정 | service.py, ai_analysis.py, test_ai_analysis.py, test_portfolio_optimize.py | REQ-060~065 | T-003 | Medium |
| T-009 | 프론트 타입 확장 + market 선택 UI + currency 자동설정 + KRW 배지 | portfolio.ts, Portfolio.tsx | REQ-070~075 | T-004,T-006 | Medium |
| T-010 | scipy 미사용 검증 + 회귀 테스트 전체 통과 + 커버리지 ≥85% | (전체) | NFR-004,AC-12 | T-001~T-009 | Medium |

> 최대 10개 태스크 준수. 각 태스크는 1 TDD 사이클(RED-GREEN-REFACTOR) 내 완료 단위.

---

## Critical Implementation Notes (핵심 구현 노트)

### DB 마이그레이션 순서
- T-002(마이그레이션)는 **T-006/T-007/T-008(서비스 변경)보다 반드시 먼저** 적용·검증되어야 한다. 컬럼이 없으면 ORM 매핑·조회가 실패한다.
- 기존 행 backfill은 `server_default="KRX"`/`"KRW"`로 자동 적용된다(REQ-004). 별도 UPDATE 문 불필요.
- **유니크 제약은 신규 생성**: 현재 테이블에 제약이 없으므로 `op.create_unique_constraint("uq_holding_portfolio_ticker_market", "portfolio_holdings", ["portfolio_id","krx_code","market"])`. downgrade는 `op.drop_constraint(...)` + `op.drop_column` ×2.
- `krx_code` 컬럼명 절대 rename 금지(REQ-003, AC-11).

### FDR 비동기 패턴 (run_in_executor)
- 신규 동기 FDR 호출(`_fetch_usd_krw_sync`, `_fetch_foreign_price`)은 `dividends.py`·`risk_analysis.py`와 동일하게 모듈 함수로 작성하고 `loop.run_in_executor(None, fn, *args)`로 격리한다. 이벤트 루프 블로킹 금지(REQ-022, 032).
- 환율 조회는 `fdr.DataReader("USD/KRW")`, 해외 가격은 `fdr.DataReader(ticker)` 사용. Close 컬럼 추출 패턴은 risk_analysis._fetch_stock_prices 재사용.

### Redis 캐시 패턴
- 환율: 키 `fx:USD:KRW:{today_kst}`, TTL≥3600s(NFR-002). 동시 쓰기 race condition 허용(REQ-084) — last-write-wins, 동일 날짜 값이므로 일관성 무해. 락 불필요.
- 해외 가격: TTL≥86400s(NFR-001) — FDR(Yahoo) 레이트 리밋 회피.
- 캐시/조회 실패는 모두 graceful — 성과 조회 전체를 실패시키지 않음(NFR-003).

### 유니크 제약 변경
- 조합: `(portfolio_id, krx_code, market)`. KRX `000020`과 동명 해외 ticker 충돌 방지(REQ-082).
- 위반 시 라우터에서 `IntegrityError` → `409 Conflict` 변환(REQ-083, AC-14).

### 하위호환
- 기존 KRX 보유 종목은 `market='KRX'`·`currency='KRW'` 기본값 적용(REQ-004, AC-2).
- 프론트 `apiAddHolding`·`HoldingCreate`의 market/currency는 기본값을 가져 기존 호출부 무변경(REQ-012, 071).
- KRX 성과 계산 경로(`get_current_price`)·표시 동작 무변경(REQ-030, 075).

### 연쇄 변경 주의 (Scope)
- `calculate_performance` 동기→비동기 전환 시 `router.get_performance`도 async/await로 동반 수정 필요. 이는 의도된 범위 내 변경.
- `dividends.py`는 본 SPEC에서 `market != 'KRX'` 방어(dividend_available=False)가 요구되나, SPEC §5는 데이터 수집은 Out-of-Scope로 명시. 방어 로직 자체는 구현 대상이나 명시적 태스크로 분리하지 않고 T-006 인접 작업 또는 별도 미세 변경으로 처리(현재 dividends 엔트리는 holdings 전체를 순회하므로 해외 ticker 유입 시 KRX StockListing 미스로 자동 False 반환됨 — 추가 가드는 선택적).

---

## Risk Assessment (상위 3 리스크 + 완화)

1. **FDR 해외 가격/환율 API 불안정·레이트 리밋** (High)
   - 영향: Yahoo Finance 기반 FDR이 해외 종목·환율 조회 시 차단·지연·스키마 변동 가능.
   - 완화: Redis TTL(가격 86400s, 환율 3600s)로 호출 최소화. 모든 조회 try/except + fallback(환율 1350.0, 가격 price_unavailable). 테스트는 FDR을 mock하여 외부 의존 제거.

2. **`calculate_performance` 동기→비동기 전환의 회귀 위험** (High)
   - 영향: 기존 KRX 전용 성과 계산·라우터·테스트가 시그니처 변경으로 깨질 수 있음.
   - 완화: KRX 경로 회귀 테스트를 RED 단계에 먼저 작성(AC-2, REQ-030). 라우터 get_performance 동반 수정. T-010에서 전체 회귀 검증.

3. **유니크 제약 전제 불일치 (SPEC 가정 vs 실제 스키마)** (Medium)
   - 영향: REQ-082/AC-11이 "기존 제약 변경/복원"을 전제하나 실제로는 제약이 없어 마이그레이션 로직 오작성 가능.
   - 완화: 마이그레이션을 "신규 제약 생성/제거"로 구현. tasks.md에 명시(상단 Plan Summary). manager-tdd 핸드오프 시 강조. downgrade는 제약·컬럼 제거로 정의.

---

## File Checklist

### CREATE (신규)
- `backend/src/stock_picker/portfolio/fx_rate.py` — USD/KRW 환율 서비스(FDR+Redis 캐시+fallback)
- `backend/alembic/versions/0019_portfolio_foreign_asset.py` — market·currency 컬럼 + 유니크 제약 마이그레이션
- `backend/tests/unit/test_fx_rate.py` — 환율 서비스 TDD 테스트(캐시·fallback·race)
- (선택) `backend/tests/unit/test_migration_0019.py` 또는 모델 속성 테스트

### MODIFY (기존)
- `backend/src/stock_picker/db/models.py` — PortfolioHolding에 market·currency 컬럼 + UniqueConstraint
- `backend/src/stock_picker/portfolio/schemas.py` — HoldingCreate/Response/Performance 확장 + 시장-통화 조합 validator
- `backend/src/stock_picker/portfolio/service.py` — add_holding 파라미터 추가, calculate_performance 해외 환산(async), optimize_portfolio market·KRW 환산
- `backend/src/stock_picker/portfolio/router.py` — add_holding market/currency 통과 + 409, get_performance async 전환
- `backend/src/stock_picker/portfolio/risk_analysis.py` — 해외 ticker 포함 비중 KRW 환산
- `backend/src/stock_picker/portfolio/ai_analysis.py` — 프롬프트 market·currency + KRW 환산 비중
- `backend/tests/unit/test_portfolio_service.py` — 해외 성과 계산 테스트 확장
- `backend/tests/unit/test_portfolio_risk.py` — 해외 종목 리스크 분석 테스트 확장
- `backend/tests/unit/test_ai_analysis.py` — AI market 정보·Claude 실패 처리 테스트 확장
- `backend/tests/unit/test_portfolio_optimize.py` — 최적화 KRW 환산·new_stocks KRX 한정 테스트
- `frontend/src/api/portfolio.ts` — Holding·HoldingCreate·HoldingPerformance 타입 + apiAddHolding 시그니처
- `frontend/src/pages/Portfolio.tsx` — PortfolioDetail 폼 market 선택 UI + currency 자동설정 + KRW 배지

---

## Acceptance Criteria 매핑 요약

| AC | 검증 태스크 |
|----|------------|
| AC-1 해외 종목 등록 | T-004, T-005 |
| AC-2 기본값 하위호환 | T-004, T-005 |
| AC-3 시장/통화 조합 거부 | T-004 |
| AC-4 환율 캐시 동작 | T-003 |
| AC-5 환율 fallback | T-003 |
| AC-6 해외 성과 KRW 환산 + fallback 계산 | T-006 |
| AC-6b 해외 섹터 null | T-006 |
| AC-7 가격 조회 실패 graceful | T-006 |
| AC-8 리스크 해외 포함 | T-007 |
| AC-9 AI market 포함 | T-008 |
| AC-10 프론트 UI | T-009 |
| AC-11 마이그레이션 0019 | T-002 |
| AC-12 scipy 미사용 | T-010 |
| AC-13 Claude 실패 graceful | T-008 |
| AC-14 중복 등록 409 | T-005 |
| AC-15 환율 캐시 race | T-003 |
