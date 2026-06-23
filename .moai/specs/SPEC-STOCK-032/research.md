# SPEC-STOCK-032 Research — 포트폴리오 리밸런싱 자동화

> 코드베이스 조사 결과. 기존 시스템과 SPEC-032 통합 지점을 정리한다.

## 1. 조사 범위

SPEC-032는 SPEC-026이 산출한 **AI 리밸런싱 제안**(목표 비중)을 받아, 실제 **실행 가능한 매수/매도 주문**(주수)으로 변환한다. 자동 매매는 하지 않으며, 주문 계획서를 산출·선택적으로 저장한다.

조사 대상 파일:
- `portfolio/router.py` — 기존 엔드포인트 패턴, 소유권 확인 관례
- `portfolio/service.py` — 가격 조회, 비중 계산, optimize_portfolio
- `portfolio/schemas.py` — 기존 스키마(`OptimizeResult`, `TargetWeightItem`)
- `portfolio/ai_analysis.py` — Claude 호출(SPEC-032는 재호출 안 함)
- `portfolio/risk_analysis.py` — 순수 함수 + numpy 전용 패턴(재사용 모델)
- `db/models.py` — `Portfolio`, `PortfolioHolding`(market/currency 포함)
- `frontend/src/components/RebalancingTable.js` — 현재 리밸런싱 UI
- `frontend/src/api/portfolio.js` — API 클라이언트 패턴
- `.moai/specs/SPEC-STOCK-031/spec.md` — 직전 SPEC 형식 참조

## 2. 핵심 발견 (Existing Building Blocks)

### 2.1 SPEC-026 리밸런싱 제안 (재사용 입력)

`portfolio/service.py::optimize_portfolio` → `OptimizeResult.target_weights: list[TargetWeightItem]`.

`TargetWeightItem`(schemas.py L194):
```
krx_code, current_pct(%), target_pct(%), action(buy/sell/hold), delta_shares
```

- `target_pct`가 SPEC-032의 입력 `target_weights[krx_code]` 소스다.
- 기존 `delta_shares`는 `avg_buy_price` 기준 단순 비중 차이로 산출 — **현재가·예산·수수료를 고려하지 않음**. SPEC-032가 이 한계를 보완한다.
- `action` 임계값(±2%) 재계산은 SPEC-026이 이미 수행. SPEC-032는 주문 실행 관점(주수·금액·수수료)에 집중한다.

### 2.2 가격 조회

- **KRX**: `realtime/price_feed.py::get_current_price(krx_code) -> dict|None` (`{"price": ...}`). service.py L243에서 사용.
- **해외(NYSE/NASDAQ)**: `service.py::_fetch_foreign_price(ticker, redis) -> float|None` (USD). Redis 캐시 TTL 86400s.
- **환율**: `fx_rate.get_usd_krw_rate(redis)`, 폴백 `fx_rate._FALLBACK_RATE`.
- **KRW 환산 패턴**: `calculate_performance`(service.py L196~)가 USD 종목을 `usd_price × fx_rate`로 KRW 환산하는 검증된 코드 경로. SPEC-032도 동일 패턴으로 예산 비교를 KRW 기준으로 통일한다.

### 2.3 시장/통화 메타데이터 (SPEC-028)

`PortfolioHolding` 모델(models.py L246):
```
krx_code(String10, KRX코드 또는 해외 티커), quantity, avg_buy_price(Numeric10,2),
market(KRX|NYSE|NASDAQ, server_default KRX), currency(KRW|USD, server_default KRW)
```
→ 시장 판별이 이미 존재(NFR-003 충족 기반). 국내/해외 수수료율 구분에 `market`/`currency` 사용 가능.

### 2.4 소유권 확인 관례

- `service.get_portfolio_with_holdings(db, portfolio_id, user_id)` → 소유권 불일치 시 `None`.
- router.py 패턴: `None`이면 `HTTPException(404)`. (SPEC-031 NFR-005: **403 아님 404**.)
- 단, `ai_analysis.analyze_portfolio`·`optimize_portfolio`는 예외적으로 403 사용 → SPEC-032는 **신규 코드이므로 404 관례**를 따른다(SPEC-031 일관성).

### 2.5 순수 함수 + numpy 패턴 (재사용 모델)

`risk_analysis.py`:
- 상단 주석으로 `scipy 금지` 명시(`@MX:NOTE` + `@MX:SPEC`).
- 순수 함수 레이어(`_daily_returns`, `_correlation_matrix` 등)와 오케스트레이션 함수(`calculate_risk_analysis`) 분리.
- 순수 함수는 DB·Redis 없이 테스트 가능 → SPEC-032 `calculate_rebalancing_orders`가 따를 모델.

### 2.6 Redis 캐시 패턴

`portfolio_optimize:{portfolio_id}:{today}` (TTL 3600s), `foreign_price:{ticker}` (TTL 86400s), `portfolio_risk:{...}`. SPEC-032 dry-run 결과는 캐시 불필요(매번 최신 가격 기준 계산이 바람직). 가격 조회는 기존 캐시를 그대로 재사용한다.

## 3. 마이그레이션 현황

`backend/alembic/versions/` 최신:
```
0019_portfolio_foreign_asset.py
0020_portfolio_alerts.py   ← SPEC-031 (이미 존재, revision="0020", down_revision="0019")
```
→ **SPEC-032 신규 마이그레이션: `0021_rebalancing_plans.py`, revision="0021", down_revision="0020"**.

마이그레이션 형식(0020 참조): `revision`/`down_revision` 문자열, `op.create_table` + `op.create_index`, FK ondelete CASCADE, `server_default=sa.text(...)`.

JSONB 컬럼: 기존 모델에 JSONB 직접 사용 사례 없음. `ai_advice.payload`·`screener_presets.criteria`는 **Text에 JSON 직렬화 문자열** 저장. SQLite 테스트 호환을 위해 SPEC-032 `orders`도 **Text(JSON 직렬화)** 채택(요청서의 JSONB 의도를 SQLite 호환 형태로 구현). PostgreSQL 전용이면 JSONB 가능하나 테스트가 SQLite이므로 Text가 안전.

## 4. 프론트엔드 현황

- `RebalancingTable.js`: 컴파일된 JS(.tsx 원본 존재 추정). `items` prop은 `{krx_code, current_pct, target_pct, action, delta_shares}` 구조 — SPEC-026 `TargetWeightItem` 표시 전용. SPEC-032는 주문 실행 정보(수량·금액·수수료)를 표시할 **신규 컴포넌트**가 필요.
- `api/portfolio.js`: `apiOptimizePortfolio` 등 fetch 래퍼 패턴. SPEC-032는 `apiCalculateRebalancingOrders`·`apiListRebalancingOrders` 추가.
- `.ts`/`.js` 쌍 유지 관례(SPEC-031에서 portfolio.ts·portfolio.js 동시 수정).

## 5. 설계 결정 (Design Decisions)

### 5.1 입력 target_weights 출처

**결정**: SPEC-032 서비스는 SPEC-026 `optimize_portfolio`를 내부 호출하여 `target_weights`(`{krx_code: target_pct}`)를 얻거나, 호출자가 명시적으로 전달한다. SPEC-032 순수 함수 `calculate_rebalancing_orders`는 `target_weights` dict를 **파라미터로 받아** DB·Claude 의존 없이 테스트 가능하다(NFR-002).

근거: SPEC-026이 이미 AI 제안을 산출·캐싱한다. SPEC-032가 Claude를 재호출하면 비용·중복. 서비스 레이어가 SPEC-026 결과를 어댑터로 변환한다.

### 5.2 예산 기본값

`Portfolio` 모델에 **현금 잔고 컬럼이 없다**. 따라서:
- `budget` 미지정 시 기본값 = **현재 포트폴리오 총 평가액(KRW)** → 자기조달(self-financing) 리밸런싱(매도 대금으로 매수 충당).
- `budget` 지정 시 = 총 매수 금액 상한(KRW). 매도 대금은 예산에 추가되지 않고, 매수는 예산 한도 내에서만 집행.

근거: 현금 잔고 추적은 본 SPEC 범위 밖(제외 항목). 예산은 "이만큼 신규 투입 가능"의 상한으로 해석한다.

### 5.3 우선순위(REQ-RBA-004)

언더웨이트(매수) 종목을 먼저 예산 배분 → 오버웨이트(매도) 종목은 나중에 처리(세금 고려: 매도 차익 실현 최소화 의도). 출력 `orders`는 buy → sell → hold 순으로 정렬한다.

### 5.4 1주 단위 반올림

`quantity = floor(target_amount_delta / price)`. 매수는 내림(예산 초과 방지), 매도는 보유 수량 한도 내 내림. 분수 주식 미지원(한국·미국 일반 계좌 기준).

### 5.5 수수료

`estimated_commission = estimated_amount × rate`. 국내 기본 0.00015(0.015%), 해외 기본 0.0025(0.25%). market 기반 자동 선택. hold는 수수료 0.

## 6. 위험 요소 (Risks)

- **가격 일시 미수신**: KRX/해외 현재가 None → 해당 종목 주문 `action="hold"`, 사유 표기, 계산에서 제외(graceful degradation).
- **부동소수 누적 오차**: 비중·금액 계산에서 round 일관성 필요. `expected_weight_after`는 주문 반영 후 재계산.
- **예산 부족**: 모든 매수를 충족 못 하면 우선순위 높은(언더웨이트 큰) 종목부터 부분 집행.
- **단일 종목 포트폴리오**: target_weights 1개 → 매도 없음, 의미 있는 리밸런싱 제한. 정상 처리(빈 주문 또는 hold).

## 7. 결론

기존 시스템은 SPEC-032 구현에 필요한 모든 기반(가격 조회, 시장 판별, 비중 계산, 소유권 확인, 마이그레이션/순수함수/Redis 패턴)을 제공한다. SPEC-032는 신규 순수 함수 1개(`rebalancing.py`), 서비스 오케스트레이션, 스키마 4종, 엔드포인트 2개, 마이그레이션 1개(0021), 프론트 컴포넌트·API 클라이언트를 추가한다. 기존 코드는 수정 최소화(라우터 import, 스키마 추가, 프론트 페이지 통합).
