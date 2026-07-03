# SPEC-STOCK-026 인수 기준 (Acceptance Criteria)

> Given-When-Then 형식. 모든 시나리오는 `backend/tests/unit/test_portfolio_optimize.py`로 검증한다.

## AC-1: 최적화 API 기본 동작 (REQ-OPT-001, REQ-OPT-DATA-001)

```
Given 보유 종목이 있는 포트폴리오와 인증된 사용자
When  POST /portfolios/{portfolio_id}/optimize 를 호출하면
Then  응답에 score(int), score_breakdown, target_weights(list),
      new_stocks(list), summary(str) 필드가 모두 포함되고
And   HTTP 200으로 10초 이내 반환된다
```

- 테스트: `test_optimize_returns_full_schema`

## AC-2: target_weights 합계 검증 (REQ-OPT-001)

```
Given 최적화 결과 응답
When  target_weights의 모든 target_pct를 합산하면
Then  합계가 약 100%(허용 오차 내)이다
```

- 테스트: `test_optimize_target_weights_sum_100`

## AC-3: action 방향 검증 (REQ-OPT-002, REQ-OPT-003, REQ-OPT-ACTION-001/002)

```
Given 최적화 결과의 각 target_weight 항목
When  target_pct - current_pct 차이를 평가하면
Then  +2%p 초과면 action="buy" 이고 delta_shares > 0
And   -2%p 초과 하회면 action="sell" 이고 delta_shares < 0
And   |차이| <= 2%p 이면 action="hold" 이고 delta_shares == 0
```

- 테스트: `test_optimize_action_direction`

## AC-4: 캐시 동작 검증 (REQ-OPT-004, REQ-OPT-NFR-003)

```
Given 한 번 최적화가 수행되어 Redis에 캐시된 포트폴리오
When  ?refresh=false 로 동일 포트폴리오를 다시 최적화하면
Then  캐시된 결과가 반환되고
And   Claude API 호출 횟수가 0회이다

Given 캐시가 존재하는 포트폴리오
When  ?refresh=true 로 최적화하면
Then  Claude API가 재호출되어 캐시가 갱신된다
```

- 테스트: `test_optimize_redis_cache_hit`

## AC-5: async 클라이언트 검증 (REQ-OPT-005)

```
Given 포트폴리오 최적화 서비스
When  Claude 호출 코드를 검사하면
Then  anthropic.AsyncAnthropic 가 사용되고
And   동기 anthropic.Anthropic 클래스는 사용되지 않는다
```

- 테스트: `test_optimize_async_client`

## AC-6: new_stocks 중복 제외 검증 (REQ-OPT-006, REQ-OPT-CONSTRAINT-002)

```
Given 보유 종목 집합이 있는 포트폴리오
When  new_stocks가 산출되면
Then  new_stocks의 어떤 krx_code도 보유 종목에 포함되지 않고
And   최대 5개까지만 반환된다
```

- 테스트: `test_optimize_new_stocks_not_in_portfolio`

## AC-7: score 범위 검증 (REQ-OPT-001, REQ-OPT-007)

```
Given 최적화 결과 응답
When  score 와 score_breakdown 을 검사하면
Then  score 가 0~100 범위이고
And   score_breakdown.diversification / risk_balance / momentum 각각 0~100 이며
And   세 값의 평균이 score 와 같다
```

- 테스트: `test_optimize_score_range`, `test_optimize_score_breakdown_average`

## AC-8: 기존 AI 분석 async 전환 검증 (REQ-OPT-005, M4)

```
Given 기존 POST /portfolios/{id}/ai-analysis 엔드포인트
When  ai_analysis.py 와 라우터 핸들러를 검사하면
Then  AsyncAnthropic 가 사용되고 핸들러가 async def 이다
And   동기 anthropic.Anthropic 클래스 사용 흔적이 없다
```

- 테스트: `test_existing_ai_analysis_async`

## AC-9: 보유 종목 없음 처리 (REQ-OPT-DATA-002)

```
Given 보유 종목이 없는 빈 포트폴리오
When  optimize 를 호출하면
Then  Claude를 호출하지 않고 빈 결과 또는 안내 메시지를 반환한다
```

- 테스트: `test_optimize_empty_portfolio`

---

## 테스트 매핑 요약

| 테스트 함수 | AC | REQ |
|------------|----|----|
| `test_optimize_score_range` | AC-7 | REQ-OPT-001/007 |
| `test_optimize_target_weights_sum_100` | AC-2 | REQ-OPT-001 |
| `test_optimize_action_direction` | AC-3 | REQ-OPT-002/003/ACTION-001/002 |
| `test_optimize_new_stocks_not_in_portfolio` | AC-6 | REQ-OPT-006/CONSTRAINT-002 |
| `test_optimize_redis_cache_hit` | AC-4 | REQ-OPT-004/NFR-003 |
| `test_optimize_async_client` | AC-5 | REQ-OPT-005 |
| `test_existing_ai_analysis_async` | AC-8 | REQ-OPT-005 (M4) |

> 추가 권장 테스트(스코프 내, 선택): `test_optimize_returns_full_schema`(AC-1), `test_optimize_score_breakdown_average`(AC-7), `test_optimize_empty_portfolio`(AC-9).

## Definition of Done

- [ ] 7개 핵심 테스트 통과 (커버리지 fail_under=85 충족)
- [ ] `POST /portfolios/{id}/optimize` 동작 (score·target_weights·new_stocks·summary)
- [ ] 포트폴리오 모듈에서 동기 `anthropic.Anthropic` 완전 제거
- [ ] Redis 캐싱 적중 시 Claude 호출 0회
- [ ] 프론트 "AI 최적화 분석" 탭 + 3개 컴포넌트 렌더링
- [ ] `ruff check` 통과, 신규 마이그레이션 없음 확인
- [ ] 면책 문구(disclaimer) summary 또는 응답에 포함 (자동매매 권유 아님 명시)
