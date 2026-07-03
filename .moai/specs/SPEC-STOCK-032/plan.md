# SPEC-STOCK-032 Implementation Plan — 포트폴리오 리밸런싱 자동화

> 작업 분해(T-001~T-007). 시간 추정 없이 우선순위·의존 순서로 정렬한다. 개발 방법론은 quality.yaml에 따른다(TDD 기본).

---

## 작업 의존 그래프

```
T-001 (마이그레이션 + ORM 모델)
   │
T-002 (스키마)  ── 독립, T-001과 병렬 가능
   │
T-003 (순수 함수 rebalancing.py) ── T-002 의존 (RebalancingOrder 타입)
   │
T-004 (서비스 오케스트레이션) ── T-001·T-002·T-003 의존
   │
T-005 (라우터 엔드포인트) ── T-004 의존
   │
T-006 (프론트엔드 패널 + API 클라이언트) ── T-005 의존 (응답 계약)
   │
T-007 (테스트 + 커버리지 검증) ── 전 작업 의존, 일부는 TDD로 선행
```

---

## T-001 — 마이그레이션 + ORM 모델 (Priority: High)

**대상**: `backend/alembic/versions/0021_rebalancing_plans.py`(NEW), `backend/src/stock_picker/db/models.py`(MODIFY)

- `0020_portfolio_alerts.py` 형식을 따라 `0021_rebalancing_plans.py` 작성.
  - `revision="0021"`, `down_revision="0020"`.
  - 컬럼: id, portfolio_id(FK CASCADE), user_id(FK CASCADE), budget(Float), total_buy_amount(Float), total_sell_amount(Float), total_commission(Float), orders(Text), created_at(TIMESTAMPTZ default now()).
  - 인덱스 `ix_rebalancing_plans_portfolio_created` on (portfolio_id, created_at).
  - upgrade/downgrade 구현.
- `models.py`에 `RebalancingPlan` ORM 모델 추가(Phase 섹션 신규 추가).
  - `orders`는 `Mapped[str]`(Text, JSON 직렬화 문자열).
  - @MX:ANCHOR + @MX:REASON(service·router·테스트 3곳 이상 참조), @MX:SPEC.

**완료 기준**: 마이그레이션 upgrade/downgrade가 SQLite·PostgreSQL에서 동작, 모델 import 에러 없음.

---

## T-002 — Pydantic 스키마 (Priority: High)

**대상**: `backend/src/stock_picker/portfolio/schemas.py`(MODIFY)

- `RebalancingOrder` — krx_code, stock_name, action(Literal buy/sell/hold), quantity(int), estimated_price, estimated_amount, estimated_commission, current_weight, target_weight, expected_weight_after.
- `RebalancingOrderPlan` — portfolio_id, budget, total_buy_amount, total_sell_amount, total_commission, orders(list[RebalancingOrder]), created_at(datetime). `ConfigDict(from_attributes=True)`.
- `RebalancingCalculateRequest` — budget(float|None=None), commission_rate(float|None=None), dry_run(bool=True).
- @MX:ANCHOR(RebalancingOrderPlan) + @MX:REASON.

**완료 기준**: 스키마 import·검증 동작, 기존 스키마 영향 없음.

---

## T-003 — 순수 함수 `rebalancing.py` (Priority: High)

**대상**: `backend/src/stock_picker/portfolio/rebalancing.py`(NEW)

- 모듈 상단 @MX:NOTE(scipy 금지·numpy/math 전용·1주 단위·예산 우선순위 정책) + @MX:SPEC.
- `calculate_rebalancing_orders(holdings, target_weights, budget, commission_rate_domestic=0.00015, commission_rate_foreign=0.0025) -> list[RebalancingOrder]`.
  - 입력 holdings: krx_code·stock_name·quantity·current_price_krw·market·price_unavailable 포함 구조.
  - 알고리즘(spec.md §5.1): 총 평가액 → 현재/목표 비중 → delta_value → buy(예산 우선) / sell(보유 캡) / hold → 수수료(market별) → expected_weight_after → 정렬(buy→sell→hold).
  - 방어: price ≤ 0, price_unavailable, 보유 0개, budget 0.
  - @MX:ANCHOR(calculate_rebalancing_orders) + @MX:REASON.
  - @MX:WARN(KRW 환산·부동소수 round 처리부) + @MX:REASON.

**완료 기준**: DB 없이 호출 가능(NFR-002), scipy 미사용(NFR-001), 8개 BDD 시나리오 중 순수 함수 대상(1,2,3,5,7,8) 통과.

---

## T-004 — 서비스 오케스트레이션 (Priority: High)

**대상**: `backend/src/stock_picker/portfolio/rebalancing.py`(동일 파일에 서비스 함수 추가) 또는 `service.py`

- `calculate_rebalancing_plan(portfolio_id, user_id, db, redis, budget=None, commission_rate=None, dry_run=True) -> RebalancingOrderPlan`.
  - `get_portfolio_with_holdings` → None이면 404(NFR-005).
  - `optimize_portfolio` 결과 target_weights에서 `{krx_code: target_pct}` 추출(SPEC-026 캐시 재사용).
  - 종목별 현재가 조회·KRW 환산(KRX: get_current_price, 해외: _fetch_foreign_price × fx_rate). 실패 시 price_unavailable=True(NFR-004).
  - budget 기본값 = 총 평가액(KRW). @MX:NOTE(현금 잔고 컬럼 부재 사유).
  - `calculate_rebalancing_orders` 호출 → orders.
  - 요약 집계(total_buy/sell/commission).
  - `dry_run=False`면 `RebalancingPlan` INSERT(orders JSON 직렬화) + commit.
  - RebalancingOrderPlan 반환.

**완료 기준**: dry-run 미저장·저장 분기 동작, 소유권 404, graceful degradation.

---

## T-005 — 라우터 엔드포인트 (Priority: Medium)

**대상**: `backend/src/stock_picker/portfolio/router.py`(MODIFY)

- `POST /portfolios/{portfolio_id}/rebalance/calculate` — Body RebalancingCalculateRequest, 소유권 404, RebalancingOrderPlan 반환.
- `GET /portfolios/{portfolio_id}/rebalance/orders` — 저장된 계획서 목록(created_at 내림차순), 소유권 404.
- `Depends(get_current_user)`·`get_db_session`·`get_redis_client` 재사용.
- 스키마 import 추가.

**완료 기준**: 두 엔드포인트 응답 계약(spec.md §5.5) 충족, 소유권 위반 404.

---

## T-006 — 프론트엔드 (Priority: Medium)

**대상**: `frontend/src/components/RebalancingOrderPanel.js`(NEW), `frontend/src/api/portfolio.js`·`portfolio.ts`(MODIFY), `frontend/src/pages/Portfolio.js`·`Portfolio.tsx`(MODIFY)

- `apiCalculateRebalancingOrders(token, portfolioId, body)` — POST calculate.
- `apiListRebalancingOrders(token, portfolioId)` — GET orders.
- `RebalancingOrderPanel.js` — 예산·수수료율 입력 + dry-run 토글 + 계산 버튼 + 결과 표(종목·액션·수량·금액·수수료·현재/목표/예상비중). `RebalancingTable.js` 표 스타일 재사용.
- Portfolio 페이지에 패널 통합(기존 섹션 보존).
- `.js`/`.ts` 쌍 동기화.

**완료 기준**: 패널이 API를 호출하고 주문 결과를 렌더링, 기존 UI 회귀 없음.

---

## T-007 — 테스트 + 커버리지 (Priority: High, TDD 선행)

**대상**: `backend/tests/unit/test_rebalancing.py`(NEW)

- 순수 함수 테스트(DB 없이): 시나리오 1,2,3,5,7,8 + 엣지 케이스 표.
- 서비스 테스트(픽스처): 시나리오 4(dry-run/저장), 6(404), NFR-004.
- 라우터 테스트: calculate·orders 엔드포인트, 소유권 404.
- 커버리지 ≥ 85%(NFR-006), scipy 미사용 grep 검증(NFR-001).

**완료 기준**: 전 테스트 통과, 커버리지 게이트 충족, ruff 통과.

---

## 마일스톤

| 마일스톤 | 포함 작업 | 산출물 |
|----------|-----------|--------|
| M1 백엔드 데이터 계층 | T-001, T-002 | 마이그레이션·모델·스키마 |
| M2 백엔드 로직 | T-003, T-004, T-007(순수함수) | 순수 함수·서비스·단위 테스트 |
| M3 백엔드 API | T-005, T-007(라우터) | 엔드포인트·통합 테스트 |
| M4 프론트엔드 | T-006 | 패널·API 클라이언트 |

순서: M1 → M2 → M3 → M4. T-007은 TDD로 M2·M3에 선행/병행.

---

## 리스크 및 완화

| 리스크 | 완화 |
|--------|------|
| 부동소수 누적 오차로 예산 초과 | 매수 합계를 예산과 비교 시 보수적 내림, round 일관성 |
| SPEC-026 캐시 미스 시 Claude 호출 비용 | optimize_portfolio 캐시(TTL 3600s) 재사용, refresh=False |
| 가격 조회 지연(해외) | 기존 Redis 캐시(TTL 86400s) 재사용, run_in_executor 격리 |
| SQLite JSONB 미지원 | orders를 Text+JSON 직렬화로 구현(research.md §3) |
| 단일 종목·빈 포트폴리오 | 방어 코드 + 엣지 케이스 테스트 |
