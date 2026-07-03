# SPEC-STOCK-032 Compact — 리밸런싱 자동화 (Run-phase 참조)

**목표**: SPEC-026 목표 비중 → 실행 가능한 매수/매도 주문(주수·금액·수수료) 변환. 자동 매매 없음.

## REQ 요약

| REQ | 패턴 | 내용 |
|-----|------|------|
| RBA-001 | Event | 1주 단위 정수 매수/매도 수량 산출(매수 floor, 매도 보유 캡) |
| RBA-002 | State | total_buy_amount ≤ budget. budget None → 총 평가액(KRW) |
| RBA-003 | Ubiq | commission = amount × rate. KRX 0.00015 / 해외 0.0025. hold=0 |
| RBA-004 | Event | buy 우선 예산 배분, 정렬 buy→sell→hold |
| RBA-005 | Event | dry_run=true(기본) 미저장 / false 저장 |
| RBA-006 | Ubiq | order: krx_code·stock_name·action·quantity·estimated_price·estimated_amount·estimated_commission·current_weight·target_weight·expected_weight_after |

## NFR

- 001 scipy 금지(numpy+math) · 002 순수함수 DB無 테스트 · 003 market별 수수료 · 004 가격None→hold · 005 소유권 404 · 006 커버리지 85%

## 파일 (Delta)

| 마커 | 파일 |
|------|------|
| NEW | `portfolio/rebalancing.py` (순수함수+서비스) |
| NEW | `alembic/versions/0021_rebalancing_plans.py` (rev=0021, down=0020) |
| NEW | `tests/unit/test_rebalancing.py` |
| NEW | `frontend/src/components/RebalancingOrderPanel.js` |
| MOD | `portfolio/schemas.py` (RebalancingOrder/Plan/CalculateRequest) |
| MOD | `portfolio/router.py` (calculate·orders 엔드포인트) |
| MOD | `db/models.py` (RebalancingPlan) |
| MOD | `frontend/src/api/portfolio.{js,ts}` |
| MOD | `frontend/src/pages/Portfolio.{js,tsx}` |

## 순수 함수 시그니처

```python
def calculate_rebalancing_orders(
    holdings: list,                  # krx_code·stock_name·quantity·current_price_krw·market·price_unavailable
    target_weights: dict[str, float],# {krx_code: target_pct}
    budget: float,
    commission_rate_domestic: float = 0.00015,
    commission_rate_foreign: float = 0.0025,
) -> list[RebalancingOrder]: ...
```

알고리즘: 총평가액 → 현재/목표비중 → delta_value → buy(예산우선,floor) / sell(보유캡,floor) / hold(임계이하·price無·price≤0) → 수수료(market) → expected_weight_after → 정렬(buy→sell→hold, 매수 delta 큰 순).

## 서비스

```
calculate_rebalancing_plan(portfolio_id,user_id,db,redis,budget=None,commission_rate=None,dry_run=True):
  get_portfolio_with_holdings → None→404
  optimize_portfolio → target_weights{krx_code:target_pct}  # SPEC-026 캐시
  현재가: KRX get_current_price / 해외 _fetch_foreign_price × fx_rate → KRW
  budget None → 총평가액
  calculate_rebalancing_orders(...) → orders → 집계
  not dry_run → RebalancingPlan INSERT(orders JSON) + commit
  → RebalancingOrderPlan
```

## API

```
POST /portfolios/{id}/rebalance/calculate  Body:{budget?,commission_rate?,dry_run?}  → RebalancingOrderPlan  (404 소유권)
GET  /portfolios/{id}/rebalance/orders     → list[RebalancingOrderPlan] (created_at desc)  (404 소유권)
```

## DB

`rebalancing_plans(id PK, portfolio_id FK CASCADE, user_id FK CASCADE, budget Float, total_buy_amount Float, total_sell_amount Float, total_commission Float, orders Text(JSON), created_at TIMESTAMPTZ default now())` + INDEX(portfolio_id, created_at). **orders는 SQLite 호환 위해 Text+JSON(JSONB 아님)**.

## 제약 (carry-over)

- scipy 금지 / 404(403 아님) / package=portfolio/ / migration backend/alembic/versions/ next=0021 down=0020 / git_commit ko / code_comments ko / gh 미설치

## MX 태그

- ANCHOR: calculate_rebalancing_orders, RebalancingOrderPlan 스키마, RebalancingPlan 모델 (+REASON)
- NOTE: 모듈 상단(scipy금지·1주단위·우선순위), budget 기본값 분기
- WARN: KRW환산·부동소수 round (+REASON)
- TODO: RED 단계, GREEN 제거
