# SPEC-STOCK-032 Acceptance Criteria — 포트폴리오 리밸런싱 자동화

> EARS 수용 기준 + Given-When-Then BDD 시나리오. 각 REQ는 최소 1개 시나리오로 검증된다. 모든 테스트는 `numpy`+`math`만 사용하며 순수 함수는 DB 없이 검증한다.

---

## 1. EARS 수용 기준 (REQ별)

### AC-RBA-001 (REQ-RBA-001 주문 계산)

- WHEN 리밸런싱 주문 계산 요청이 완료되면 THE 시스템 SHALL 각 종목의 주문 수량을 1주 단위 정수로 반환한다.
- WHEN 매수 조정 금액을 현재가로 나눈 값이 소수이면 THE 시스템 SHALL 매수 수량을 내림(floor) 처리하여 정수로 반환하고, 매도 수량은 보유 수량 한도 내에서 내림 처리하여 반환한다.

### AC-RBA-002 (REQ-RBA-002 예산 제약)

- WHILE 매수 주문을 산출하는 동안 THE 시스템 SHALL 모든 매수 주문 금액 합계가 지정된 예산을 초과하지 않도록 보장한다.
- WHEN 예산이 지정되지 않은 채로 계산이 요청되면 THE 시스템 SHALL 현재 포트폴리오 총 평가액(KRW)을 기본 예산으로 사용한다.

### AC-RBA-003 (REQ-RBA-003 수수료)

- THE 시스템 SHALL 각 주문의 추정 수수료를 주문 금액과 수수료율의 곱으로 산출한다.
- WHEN 종목의 거래 시장이 국내(KRX)이면 THE 시스템 SHALL 기본 국내 수수료율 0.00015를 적용하고, 해외(NYSE/NASDAQ)이면 0.0025를 적용한다.
- THE 시스템 SHALL `action="hold"` 주문의 추정 수수료를 0으로 산출한다.

### AC-RBA-004 (REQ-RBA-004 우선순위)

- WHEN buy·sell 주문이 모두 존재하면 THE 시스템 SHALL 출력 목록을 buy → sell → hold 순으로 정렬하여 반환한다.
- WHEN 예산이 모든 매수를 충족하기에 부족하면 THE 시스템 SHALL 비중 조정 필요량이 큰 언더웨이트 종목부터 우선하여 예산을 배분한다.

### AC-RBA-005 (REQ-RBA-005a/005b dry-run vs 저장)

- WHEN 사용자가 `dry_run=true`(기본)로 계산을 요청하면 THE 시스템 SHALL 영속 저장소에 주문 계획을 기록하지 않고 계획서를 반환한다.
- WHEN 사용자가 `dry_run=false`로 계산을 요청하면 THE 시스템 SHALL 주문 계획서를 영속 저장소에 1건 저장하고 저장된 계획서를 반환한다.

### AC-RBA-006 (REQ-RBA-006 주문 요약)

- THE 시스템 SHALL 각 주문에 대해 krx_code·stock_name·action·quantity·estimated_price·estimated_amount·estimated_commission·current_weight·target_weight·expected_weight_after 필드를 모두 반환한다.
- THE 시스템 SHALL 계획서 수준에서 portfolio_id·budget·total_buy_amount·total_sell_amount·total_commission·orders·created_at을 반환한다.

### AC-NFR (비기능)

- AC-NFR-001: THE 시스템 SHALL 리밸런싱 계산 모듈 내에서 프로젝트 승인 외 외부 최적화 라이브러리를 사용하지 않는다.
- AC-NFR-002: THE 시스템의 핵심 리밸런싱 계산 컴포넌트 SHALL DB·외부 캐시 픽스처 없이 호출 가능하며 결정적 결과를 반환한다.
- AC-NFR-003: WHEN 종목의 거래 시장이 국내(KRX)이면 THE 시스템 SHALL 국내 수수료율을 적용하고, 해외(NYSE/NASDAQ)이면 THE 시스템 SHALL 해외 수수료율을 적용한다.
- AC-NFR-004: WHEN 한 종목의 현재가 조회가 실패하면 THE 시스템 SHALL 해당 종목을 `action="hold"`로 표기하고 나머지 종목 주문을 정상 산출한다.
- AC-NFR-005: WHEN 요청 사용자가 소유하지 않은 포트폴리오로 계산을 요청하면 THE 시스템 SHALL 포트폴리오가 존재하지 않는 경우와 동일한 오류 응답을 반환한다.
- AC-NFR-006: THE 시스템 SHALL 리밸런싱 계산 모듈에 대해 단위 테스트 커버리지 85% 이상을 충족한다.

---

## 2. BDD 시나리오

### 시나리오 1: 기본 매수/매도 주문 산출 (REQ-RBA-001, 006)

```
Given 포트폴리오에 종목 A(100주, 현재가 10,000원, market=KRX)와
      종목 B(50주, 현재가 20,000원, market=KRX)가 있고
  And 총 평가액 = 100×10,000 + 50×20,000 = 2,000,000원
  And A 현재 비중 50%, B 현재 비중 50%
  And 목표 비중 A=70%, B=30%
  And budget = 2,000,000원 (총 평가액)
When calculate_rebalancing_orders가 호출되면
Then A는 action="buy" (목표 1,400,000원 - 현재 1,000,000원 = +400,000원 → floor(400,000/10,000)=40주)
  And B는 action="sell" (목표 600,000원 - 현재 1,000,000원 = -400,000원 → floor(400,000/20,000)=20주)
  And A.expected_weight_after는 70%에 근접
  And 모든 quantity는 정수
```

### 시나리오 2: 예산 제약으로 부분 집행 (REQ-RBA-002, 004)

```
Given 종목 A·B가 모두 언더웨이트이고 총 필요 매수 금액이 1,000,000원이며
  And budget = 600,000원
When calculate_rebalancing_orders가 호출되면
Then total_buy_amount ≤ 600,000원
  And delta_value가 더 큰 언더웨이트 종목부터 예산이 우선 배분된다
  And 예산 소진 후 남은 종목은 quantity가 줄거나 hold가 된다
```

### 시나리오 3: 해외 자산 수수료 차등 (REQ-RBA-003, NFR-003)

```
Given 종목 A(market=KRX)와 종목 C(market=NASDAQ, currency=USD)가 있고
  And C의 현재가는 USD 가격 × 환율로 KRW 환산되어 주입되며
When calculate_rebalancing_orders가 호출되면
Then A 주문의 commission은 estimated_amount × 0.00015
  And C 주문의 commission은 estimated_amount × 0.0025
```

### 시나리오 4: dry-run 미리보기 vs 저장 (REQ-RBA-005)

```
Given 인증된 포트폴리오 소유자가
When POST /portfolios/{id}/rebalance/calculate를 dry_run=true로 호출하면
Then 200 응답으로 RebalancingOrderPlan을 받고
  And rebalancing_plans 테이블 행 수는 변하지 않는다

When 동일 요청을 dry_run=false로 호출하면
Then rebalancing_plans에 1행이 저장되고
  And GET /portfolios/{id}/rebalance/orders가 해당 계획서를 반환한다
```

### 시나리오 5: 현재가 미수신 graceful degradation (NFR-004)

```
Given 종목 A는 현재가 조회 성공, 종목 B는 현재가 조회 실패(None)
When calculate_rebalancing_orders가 호출되면
Then A는 정상 주문(buy/sell)으로 산출되고
  And B는 action="hold", quantity=0으로 표기되며
  And 전체 계산이 예외 없이 완료된다
```

### 시나리오 6: 소유권 위반 404 (NFR-005)

```
Given 사용자 U1이 포트폴리오 P(소유자 U2)에 대해
When POST /portfolios/P/rebalance/calculate를 호출하면
Then 404 Not Found가 반환되고
  And 계획서가 저장되지 않는다
```

### 시나리오 7: 임계값 이하 변동은 hold (REQ-RBA-001)

```
Given 종목 A의 현재 비중과 목표 비중 차이가 1주 가격 미만이고
When calculate_rebalancing_orders가 호출되면
Then A는 action="hold", quantity=0으로 산출된다
```

### 시나리오 8: 정렬 순서 검증 (REQ-RBA-004)

```
Given buy 1건, sell 1건, hold 1건이 산출되는 입력
When calculate_rebalancing_orders가 호출되면
Then 반환 목록의 순서는 [buy, sell, hold]이다
```

---

## 3. 엣지 케이스 (Edge Cases)

| 케이스 | 기대 동작 |
|--------|-----------|
| 보유 종목 0개 | 빈 주문 목록 반환(또는 메시지), 예외 없음 |
| 목표 비중에 보유하지 않은 종목 포함 | 해당 종목은 매수 후보(현재 비중 0%)로 처리하되, 현재가 주입 가능해야 함. 주입 불가 시 hold |
| 단일 종목 포트폴리오 | 매도 상대 없음 → 의미 있는 리밸런싱 제한, hold 또는 빈 주문 |
| budget = 0 | 매수 0주, 매도만 산출 |
| target_weights 합계 ≠ 100% | 입력값 그대로 사용(정규화는 SPEC-026 책임). 비중 차이 기준으로 계산 |
| 보유 수량보다 큰 매도 필요 | 매도 수량은 보유 수량으로 캡 |
| 현재가가 0 또는 음수 | 해당 종목 hold(0 나눗셈 방지) |
| 모든 종목 현재가 미수신 | 전부 hold, total_buy/sell=0 |

---

## 4. Definition of Done

- [ ] REQ-RBA-001~006 전부 구현 및 테스트 통과.
- [ ] 8개 BDD 시나리오 전부 자동화 테스트로 검증.
- [ ] 엣지 케이스 표의 케이스 전부 테스트 또는 방어 코드 존재.
- [ ] `portfolio/rebalancing.py` 커버리지 ≥ 85%(NFR-006).
- [ ] `scipy` import 없음(NFR-001).
- [ ] 순수 함수 DB 없이 테스트 통과(NFR-002).
- [ ] 국내/해외 수수료 차등 적용 검증(NFR-003).
- [ ] 소유권 위반 시 404 응답(NFR-005).
- [ ] 마이그레이션 `0021_rebalancing_plans.py` upgrade/downgrade 동작.
- [ ] 프론트엔드 RebalancingOrderPanel 통합, API 클라이언트 `.js`/`.ts` 동기화.
- [ ] @MX 태그(ANCHOR·NOTE·WARN) 한국어로 부착, RED 단계 TODO 제거.
- [ ] ruff·pytest 통과, TRUST 5 게이트 충족.
