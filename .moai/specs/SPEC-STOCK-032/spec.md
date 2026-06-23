---
id: "SPEC-STOCK-032"
version: "0.1.0"
status: "draft"
created_at: "2026-06-23"
updated_at: "2026-06-23"
author: "ircp"
priority: "high"
issue_number: 0
labels: ["portfolio", "rebalancing", "orders", "backend", "frontend"]
---

# SPEC-STOCK-032: 포트폴리오 리밸런싱 자동화 (Portfolio Rebalancing Automation)

> Roadmap Phase 3 "포트폴리오 AI 최적화" 계열 SPEC. SPEC-026(AI 리밸런싱 제안)이 산출한 **목표 비중**을 입력으로 받아, 현재가·예산·수수료·1주 단위 제약을 반영한 **실행 가능한 매수/매도 주문 계획서**를 산출한다. 자동 매매·주문 집행은 하지 않으며(영구 제외), 계획서를 미리보기(dry-run)하거나 선택적으로 DB에 저장한다.

## HISTORY

| 버전 | 날짜 | 변경 내용 |
|------|------|-----------|
| 0.1.0 | 2026-06-23 | 최초 작성 |

> **REQ 접두사 설계 원칙**: 본 SPEC은 `REQ-RBA-*`(ReBalancing Automation) 접두사를 사용한다. SPEC-026(AI 최적화)이 `REQ-OPT-*`를 점유하므로 충돌을 회피한다.

> **번호 체계**: REQ-RBA-001~006 연속 번호를 사용한다.

---

## 1. 개요 (Overview)

### 1.1 기능 설명

SPEC-026은 포트폴리오 AI 최적화를 통해 종목별 **목표 비중**(`target_pct`)과 임계값 기반 `action`(buy/sell/hold)을 제안한다. 그러나 이 제안은 추상적 비중 조정일 뿐, 사용자가 실제로 주문창에 입력할 **구체적인 주수·금액·수수료**를 제공하지 않는다.

SPEC-032는 이 간극을 메운다. 목표 비중을 입력받아 다음을 고려한 실행 가능한 주문을 계산한다.

1. **1주 단위(whole share lot)** — 분수 주식 미지원, 내림 처리.
2. **현재가** — KRX/해외 자산 모두 현재가 조회 후 KRW 기준 통일.
3. **예산 제약** — 사용자 지정 예산(미지정 시 현재 포트폴리오 총 평가액) 내에서만 매수 집행.
4. **수수료 추정** — 국내/해외 차등 수수료율(기본 국내 0.015%, 해외 0.25%).
5. **우선순위** — 언더웨이트 종목 매수를 오버웨이트 종목 매도보다 우선(세금 고려).

결과는 `RebalancingOrderPlan`(주문 목록 + 요약)으로 반환한다. `dry_run=true`(기본)면 DB 미저장 미리보기, `dry_run=false`면 `rebalancing_plans` 테이블에 저장한다.

### 1.2 동기 (Motivation)

SPEC-026 `RebalancingTable` UI는 "현재 50% → 목표 45%, 매도"처럼 비중 변화만 보여준다. 사용자는 "그래서 몇 주를 팔아야 하지? 수수료는 얼마지? 내 예산 100만 원으로 가능한가?"를 직접 손계산해야 한다.

본 SPEC은 AI 제안을 즉시 실행 가능한 주문 명세로 변환하여, 사용자가 증권사 주문창에 그대로 입력할 수 있는 수량·금액·수수료를 제공한다. 자동 매매가 아닌 **의사결정 지원**(decision support)이다.

### 1.3 목표 (Goals)

- SPEC-026 목표 비중을 입력으로 실행 가능한 매수/매도 주문(주수)을 계산한다.
- 1주 단위·예산·수수료·우선순위 제약을 모두 반영한다.
- 국내/해외 자산을 KRW 기준으로 통일하여 예산 비교를 일관되게 수행한다.
- dry-run 미리보기와 DB 저장(주문 계획서 영속화)을 분리 지원한다.
- 순수 함수(`calculate_rebalancing_orders`)로 핵심 계산을 분리하여 DB 없이 테스트 가능하게 한다.
- 프론트엔드에 주문 계획 미리보기 UI를 추가한다.

### 1.4 기술 스택 (확정·재사용)

FastAPI + PostgreSQL(asyncpg) + SQLAlchemy + Alembic + Redis + React + JavaScript/TypeScript. 신규 라이브러리는 도입하지 않는다. 수치 계산은 `numpy` + `math`만 사용한다(NFR-001, scipy 금지). 가격 조회는 기존 `get_current_price`(KRX)·`_fetch_foreign_price`(해외)·`fx_rate`를 재사용한다.

---

## 2. 범위 (Scope)

### 2.1 포함 (In Scope)

- 신규 순수 함수 모듈 `portfolio/rebalancing.py` — `calculate_rebalancing_orders` 및 보조 함수.
- 신규 서비스 오케스트레이션 — 소유권 확인, SPEC-026 목표 비중 획득, 가격 조회(KRW 환산), 순수 함수 호출, dry-run/저장 분기.
- `RebalancingOrder`·`RebalancingOrderPlan`·`RebalancingCalculateRequest` Pydantic 스키마 추가(`portfolio/schemas.py`).
- 신규 엔드포인트 2개(`portfolio/router.py`):
  - `POST /portfolios/{portfolio_id}/rebalance/calculate`
  - `GET  /portfolios/{portfolio_id}/rebalance/orders`
- `RebalancingPlan` ORM 모델 추가(`db/models.py`).
- 신규 마이그레이션 `0021_rebalancing_plans.py`(down_revision="0020").
- 프론트엔드 주문 계획 미리보기 컴포넌트 + API 클라이언트 확장(`.js`/`.ts` 쌍).
- 단위 테스트(커버리지 85% 이상).

### 2.2 제외 (What NOT to Build)

> [HARD] 본 SPEC은 다음을 **빌드하지 않는다**.

- **자동 매매/주문 집행**: 증권사 API 연동·실제 매수/매도 주문 전송은 규제·책임 리스크로 프로젝트 전체에서 **영구 제외**. 본 SPEC은 주문 *계획서* 산출까지만 수행한다.
- **현금 잔고 추적**: `Portfolio`/`PortfolioHolding`에 현금 잔고 컬럼을 추가하지 않는다. 예산은 사용자 입력 또는 포트폴리오 총 평가액으로 대체한다.
- **목표 비중 재산출(AI 재호출)**: 목표 비중은 SPEC-026 `optimize_portfolio` 결과 또는 호출자 입력을 사용한다. 본 SPEC에서 Claude를 재호출하여 새 목표 비중을 생성하지 않는다.
- **세금 정밀 계산**: 양도소득세·거래세 실제 금액 계산은 제외한다. "우선순위" 정책(매수 우선)만 세금을 고려하며, 세액 산출은 하지 않는다.
- **분수 주식(fractional shares)**: 모든 주문은 1주 단위 정수로 산출한다.
- **주문 이력 대시보드·차트**: 저장된 계획서 목록 조회(GET)는 제공하나, 통계·차트·비교 분석은 제공하지 않는다.
- **실시간 가격 스트리밍**: 계산 시점의 최신 종가/현재가 1회 조회만 사용한다.
- **다중 통화 정산**: 모든 금액은 KRW 단일 통화로 환산하여 표기한다.

---

## 3. 기능 요구사항 (EARS Requirements)

### REQ-RBA-001 (Event-driven) — 리밸런싱 주문 계산

WHEN 사용자가 포트폴리오에 대해 리밸런싱 주문 계산을 요청하면 THEN THE 시스템 SHALL 현재 비중을 목표 비중으로 이동시키는 매수/매도 수량을 **1주 단위 정수**로 계산하되, 주어진 예산 한도 내에서 산출한다.

### REQ-RBA-002 (State-driven) — 예산 제약

WHILE 리밸런싱 주문을 계산하는 동안 THE 시스템 SHALL 총 매수 금액(수수료 포함 전 매수 원금 합계)이 예산을 초과하지 않도록 보장한다. 예산이 명시되지 않으면 현재 포트폴리오 총 평가액(KRW)을 기본 예산으로 사용한다.

### REQ-RBA-003 (Ubiquitous) — 수수료 추정

THE 시스템 SHALL 각 매수/매도 주문에 대해 추정 수수료를 산출한다 — `수수료 = 주문 금액 × 수수료율`. 수수료율은 설정 가능하며, 미지정 시 국내(KRX) 0.00015, 해외(NYSE/NASDAQ) 0.0025를 적용한다. `action="hold"` 주문의 수수료는 0이다.

### REQ-RBA-004 (Event-driven) — 우선순위 정렬

WHEN 복수 종목이 리밸런싱 대상이면 THEN THE 시스템 SHALL 언더웨이트(매수) 종목을 오버웨이트(매도) 종목보다 우선하여 예산을 배분하고, 출력 주문 목록을 buy → sell → hold 순으로 정렬한다(세금 고려: 매도 차익 실현 최소화).

### REQ-RBA-005 (Event-driven) — Dry-Run vs 저장

WHEN 사용자가 `dry_run=true`(기본)로 주문을 미리보기하면 THEN THE 시스템 SHALL DB에 기록하지 않고 계획서를 반환한다. IF 사용자가 `dry_run=false`로 확정하면 THEN THE 시스템 SHALL 주문 계획서를 `rebalancing_plans` 테이블에 저장하고 저장된 계획서를 반환한다.

### REQ-RBA-006 (Ubiquitous) — 주문 요약

THE 시스템 SHALL 각 주문에 대해 다음을 반환한다 — `krx_code`, `stock_name`, `action`(buy/sell/hold), `quantity`(주수), `estimated_price`(현재가, KRW), `estimated_amount`(추정 금액), `estimated_commission`(추정 수수료), `current_weight`(현재 비중 %), `target_weight`(목표 비중 %), `expected_weight_after`(주문 반영 후 예상 비중 %). 또한 계획서 수준에서 `total_buy_amount`·`total_sell_amount`·`total_commission`·`budget`을 반환한다.

---

## 4. 비기능 요구사항 (NFR)

- **NFR-001 (scipy 금지)**: THE 시스템 SHALL 본 SPEC 신규 코드에서 `scipy`를 import하지 않는다. 수치 계산은 `numpy` + `math`만 사용한다(`risk_analysis.py` 패턴 일관성).
- **NFR-002 (순수 함수 테스트성)**: THE `calculate_rebalancing_orders` 순수 함수 SHALL DB·Redis·외부 API 의존 없이 입력(holdings + 가격 + 목표 비중 + 예산 + 수수료율)만으로 결정적 결과를 산출하여 단위 테스트가 가능해야 한다.
- **NFR-003 (국내/해외 수수료 구분)**: THE 시스템 SHALL `PortfolioHolding.market`(KRX|NYSE|NASDAQ)을 기준으로 국내/해외 수수료율을 자동 구분 적용한다(SPEC-028 시장 판별 재사용).
- **NFR-004 (graceful degradation)**: IF 특정 종목의 현재가 조회가 실패하면 THEN THE 시스템 SHALL 해당 종목을 `action="hold"`, `quantity=0`으로 처리하고 사유를 표기하여, 다른 종목의 주문 계산을 차단하지 않는다.
- **NFR-005 (소유권 일관성)**: THE 시스템 SHALL 포트폴리오 소유권 확인에 `get_portfolio_with_holdings()`(소유권 불일치 시 None)를 사용하고, 소유권 위반 시 `404 Not Found`로 응답한다(코드베이스 관례, 403 아님).
- **NFR-006 (테스트 커버리지)**: THE `portfolio/rebalancing.py` SHALL 단위 테스트 커버리지 85% 이상을 충족한다.

---

## 5. 기술 접근 방식 (Technical Approach)

### 5.1 순수 함수 (`portfolio/rebalancing.py`)

```python
def calculate_rebalancing_orders(
    holdings: list[HoldingWithPrice],     # 현재 보유 (현재가 포함, KRW 환산)
    target_weights: dict[str, float],     # {krx_code: target_weight_pct}
    budget: float,                        # 매수 예산 상한 (KRW)
    commission_rate_domestic: float = 0.00015,
    commission_rate_foreign: float = 0.0025,
) -> list[RebalancingOrder]:
    ...
```

`HoldingWithPrice`(내부 dataclass 또는 dict): `krx_code`, `stock_name`, `quantity`, `current_price_krw`, `market`, `price_unavailable`.

알고리즘 개요:
1. 현재 총 평가액 = Σ(quantity × current_price_krw). 종목별 현재 비중 산출.
2. 종목별 목표 평가액 = target_weight_pct/100 × (총 평가액 기준값). 목표 - 현재 = 조정 금액(delta_value).
3. **delta_value > 0(언더웨이트 → 매수)**: 우선순위 그룹. 예산 한도 내에서 `quantity = floor(delta_value / price)`. 예산 차감.
4. **delta_value < 0(오버웨이트 → 매도)**: `quantity = min(floor(|delta_value| / price), 보유수량)`.
5. `|delta_value|`가 1주 미만이거나 임계값 이하면 `action="hold"`, `quantity=0`.
6. `price_unavailable`이면 `action="hold"`, 사유 표기.
7. 수수료 = estimated_amount × (market별 rate).
8. `expected_weight_after` = 주문 반영 후 (quantity ± order_qty) × price / 총 평가액.
9. 정렬: buy → sell → hold. 매수 그룹 내 delta_value 큰 순.

순수 함수는 DB·가격 조회를 하지 않는다. 가격·KRW 환산은 호출자(서비스)가 주입한다(NFR-002).

### 5.2 서비스 오케스트레이션

```
calculate_rebalancing_plan(portfolio_id, user_id, db, redis, budget?, commission_rate?, dry_run=True):
  1. get_portfolio_with_holdings(db, portfolio_id, user_id)  # None → 404 (NFR-005)
  2. 목표 비중 획득:
       optimize_portfolio(portfolio_id, user_id, db, redis) 결과의 target_weights에서
       {krx_code: target_pct} 추출. (SPEC-026 재사용, AI 재호출 안 함 — 캐시 활용)
  3. 종목별 현재가 조회 → KRW 환산:
       KRX: get_current_price(krx_code)["price"]
       해외: _fetch_foreign_price(ticker, redis) × get_usd_krw_rate(redis)
       실패 시 price_unavailable=True
  4. budget 기본값: 미지정 시 현재 총 평가액(KRW)
  5. orders = calculate_rebalancing_orders(holdings_with_price, target_weights, budget, rates)
  6. plan 요약 집계 (total_buy/sell/commission)
  7. IF not dry_run: rebalancing_plans 테이블에 INSERT (orders는 JSON 직렬화), commit
  8. RETURN RebalancingOrderPlan
```

예외 처리: 종목별 가격 조회 try-except, 실패 종목 hold 처리(NFR-004).

### 5.3 `rebalancing_plans` 테이블 스키마

```
rebalancing_plans
  id                 INTEGER PK AUTOINCREMENT
  portfolio_id       INTEGER NOT NULL  FK(portfolios.id, ondelete=CASCADE)
  user_id            INTEGER NOT NULL  FK(users.id, ondelete=CASCADE)
  budget             FLOAT NOT NULL
  total_buy_amount   FLOAT NOT NULL
  total_sell_amount  FLOAT NOT NULL
  total_commission   FLOAT NOT NULL
  orders             TEXT NOT NULL     -- list[RebalancingOrder] JSON 직렬화
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now()

  INDEX (portfolio_id, created_at)   -- ix_rebalancing_plans_portfolio_created
```

> **JSONB 정정**: 요청서의 `orders JSONB`는 PostgreSQL 의도이나, 본 프로젝트 테스트는 SQLite이며 기존 JSON 영속화(`ai_advice.payload`, `screener_presets.criteria`)는 모두 `Text` + JSON 직렬화 문자열을 사용한다. SQLite 호환을 위해 `orders`를 `Text`로 구현한다(JSON 직렬화 문자열). 도메인 의미는 JSONB와 동일.

### 5.4 스키마 (`portfolio/schemas.py`)

```python
class RebalancingOrder(BaseModel):
    krx_code: str
    stock_name: str
    action: Literal["buy", "sell", "hold"]
    quantity: int
    estimated_price: float        # 현재가 (KRW)
    estimated_amount: float
    estimated_commission: float
    current_weight: float
    target_weight: float
    expected_weight_after: float

class RebalancingOrderPlan(BaseModel):
    portfolio_id: int
    budget: float
    total_buy_amount: float
    total_sell_amount: float
    total_commission: float
    orders: list[RebalancingOrder]
    created_at: datetime

class RebalancingCalculateRequest(BaseModel):
    budget: float | None = None
    commission_rate: float | None = None   # 지정 시 국내/해외 공통 적용 override
    dry_run: bool = True
```

Pydantic v2(`model_config = ConfigDict(from_attributes=True)` 저장 응답용).

### 5.5 라우터 (`portfolio/router.py`)

```
POST /portfolios/{portfolio_id}/rebalance/calculate
  Body: RebalancingCalculateRequest
  소유권 불일치 → 404 (NFR-005)
  Response: RebalancingOrderPlan

GET /portfolios/{portfolio_id}/rebalance/orders
  소유권 불일치 → 404
  Response: list[RebalancingOrderPlan]  (created_at 내림차순)
```

기존 `Depends(get_current_user)` + `get_db_session` + `get_redis_client` 패턴 재사용.

### 5.6 프론트엔드

- `frontend/src/components/RebalancingOrderPanel.js` — calculate 호출 폼(예산·수수료율 입력, dry-run 토글) + 주문 결과 표(종목·액션·수량·금액·수수료·예상비중). 기존 `RebalancingTable.js` 표 스타일 재사용.
- `frontend/src/api/portfolio.js`(+`.ts`) — `apiCalculateRebalancingOrders(token, portfolioId, body)`·`apiListRebalancingOrders(token, portfolioId)`.
- `frontend/src/pages/Portfolio.js`(+`.tsx`) — RebalancingOrderPanel 통합(기존 섹션 보존).

---

## 6. Delta Markers (변경 영향 분석)

| 마커 | 파일 | 내용 |
|------|------|------|
| [EXISTING] | `backend/src/stock_picker/portfolio/service.py` | `optimize_portfolio`(목표 비중 소스), `get_portfolio_with_holdings`(소유권), `_fetch_foreign_price`, `get_current_price` 재사용(수정 없음) |
| [EXISTING] | `backend/src/stock_picker/portfolio/fx_rate.py` | `get_usd_krw_rate` 재사용(수정 없음) |
| [EXISTING] | `backend/src/stock_picker/realtime/price_feed.py` | `get_current_price` 재사용(수정 없음) |
| [NEW] | `backend/src/stock_picker/portfolio/rebalancing.py` | 순수 함수 + 서비스 오케스트레이션 |
| [MODIFY] | `backend/src/stock_picker/portfolio/schemas.py` | `RebalancingOrder`·`RebalancingOrderPlan`·`RebalancingCalculateRequest` 추가 |
| [MODIFY] | `backend/src/stock_picker/portfolio/router.py` | rebalance/calculate·rebalance/orders 엔드포인트 추가 |
| [MODIFY] | `backend/src/stock_picker/db/models.py` | `RebalancingPlan` ORM 모델 추가 |
| [NEW] | `backend/alembic/versions/0021_rebalancing_plans.py` | `rebalancing_plans` 테이블 마이그레이션(down_revision="0020") |
| [NEW] | `backend/tests/unit/test_rebalancing.py` | 순수 함수·서비스 단위 테스트(커버리지 85%+) |
| [NEW] | `frontend/src/components/RebalancingOrderPanel.js` | 주문 계획 미리보기 패널 |
| [MODIFY] | `frontend/src/api/portfolio.js` | 리밸런싱 주문 API 클라이언트 추가 |
| [MODIFY] | `frontend/src/api/portfolio.ts` | 리밸런싱 주문 API 클라이언트 추가 |
| [MODIFY] | `frontend/src/pages/Portfolio.js` | RebalancingOrderPanel 통합 |
| [MODIFY] | `frontend/src/pages/Portfolio.tsx` | RebalancingOrderPanel 통합 |

> **마이그레이션 경로**: `backend/alembic/versions/NNNN_name.py` 형식. 최신 리비전은 `0020`(SPEC-031)이므로 신규는 `0021_rebalancing_plans.py`(revision="0021", down_revision="0020").

---

## 7. 의존성 (Dependencies)

- **SPEC-026**(포트폴리오 AI 최적화): `optimize_portfolio` → `target_weights` 데이터 소스. 본 SPEC은 SPEC-026 코드를 수정하지 않는다.
- **SPEC-028**(해외 자산 지원): `PortfolioHolding.market`/`currency`, `_fetch_foreign_price`, `fx_rate` — 국내/해외 수수료 구분·KRW 환산.
- **SPEC-017**(포트폴리오 성과): `get_portfolio_with_holdings` 소유권 확인, `get_current_price` KRX 가격 조회.
- **SPEC-027**(리스크 분석): 순수 함수 + numpy 전용 구조 패턴(`risk_analysis.py`) 모방.

---

## 8. MX 태그 계획 (MX Tag Plan)

코드 주석 언어는 한국어(`language.yaml` `code_comments: ko`).

- **@MX:ANCHOR** (`rebalancing.py`의 `calculate_rebalancing_orders` 순수 함수 진입점):
  - 사유: 서비스 오케스트레이션 + 단위 테스트에서 fan_in ≥ 3 예상. `@MX:REASON` 필수.
- **@MX:NOTE** (`rebalancing.py` 모듈 상단):
  - scipy 금지·numpy/math 전용 원칙, 1주 단위 내림·예산 우선순위 정책 명시.
- **@MX:NOTE** (예산 기본값 분기):
  - 현금 잔고 컬럼 부재 → 미지정 시 총 평가액 사용 사유.
- **@MX:WARN** (KRW 환산·부동소수 누적 처리부):
  - USD 환산·round 일관성 주의. `@MX:REASON` 필수.
- **@MX:ANCHOR** (`RebalancingOrderPlan` 응답 스키마):
  - 사유: router·service·프론트 API 래퍼·테스트에서 3곳 이상 참조. `@MX:REASON` 필수.
- **@MX:TODO** (RED 단계):
  - 미구현 순수 함수·오케스트레이션 임시 마커. GREEN 단계에서 제거.

태그 설명은 한국어로 작성하고, 에이전트 생성 태그는 `[AUTO]` 접두사를 포함한다.

---

## 9. 수용 기준 (Acceptance Criteria)

상세 BDD 시나리오·EARS 수용 기준은 [acceptance.md](acceptance.md) 참조. 작업 분해는 [plan.md](plan.md), 압축 참조는 [spec-compact.md](spec-compact.md) 참조.
