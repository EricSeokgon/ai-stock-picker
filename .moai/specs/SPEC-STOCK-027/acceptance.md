# SPEC-STOCK-027 인수 기준 (Acceptance Criteria)

> Given-When-Then 형식. 백엔드 단위 시나리오는 `backend/tests/unit/test_portfolio_risk.py`, 통합은 `backend/tests/integration/test_portfolio_router.py`로 검증한다.

## AC-1: 리스크 분석 API 기본 동작 (REQ-RISK-001, REQ-RISK-006)

```
Given 보유 종목이 2개 이상이고 가격 데이터가 확보된 포트폴리오와 인증된 사용자
When  GET /portfolios/{portfolio_id}/risk-analysis 를 호출하면
Then  응답에 correlation_matrix(dict[str, dict[str, float]]),
      holdings_volatility(list), portfolio_volatility_pct(float),
      diversification_benefit_pct(float), period_days(int),
      calculated_at 필드가 모두 포함되고
And   HTTP 200으로 반환된다
```

- 테스트: `test_risk_analysis_returns_full_schema`(unit), `test_risk_analysis_endpoint_200`(integration)

## AC-2: 상관관계 매트릭스 검증 (REQ-RISK-002)

```
Given mock 가격 시계열을 가진 2개 이상 종목
When  상관관계 매트릭스를 계산하면
Then  모든 상관계수가 -1.0~1.0 범위이고
And   대각 원소(동일 종목 쌍)는 1.0 이다
```

- 테스트: `test_correlation_matrix_calculation`

## AC-3: 종목별 변동성 검증 (REQ-RISK-003, REQ-RISK-DATA-003)

```
Given 일간 종가 시계열을 가진 종목
When  연환산 변동성을 계산하면
Then  값이 (일간 수익률 표준편차 × √252 × 100)과 일치하고
And   각 항목에 price_data_days 가 함께 반환된다
```

- 테스트: `test_volatility_calculation`

## AC-4: 포트폴리오 변동성(가중치) 검증 (REQ-RISK-004)

```
Given 보유 비중(weights)과 종목별 가격 시계열
When  포트폴리오 변동성을 계산하면
Then  값이 sqrt(wᵀ · 공분산 · w) × √252 × 100 과 일치한다
```

- 테스트: `test_portfolio_volatility_with_weights`

## AC-5: 분산투자 효익 검증 (REQ-RISK-005)

```
Given 포트폴리오 변동성과 비중가중평균 변동성
When  분산투자 효익을 계산하면
Then  (1 - port_vol / weighted_avg_vol) × 100 으로 산출되고
And   결과가 음수이면 0으로 클램프된다
```

- 테스트: `test_diversification_benefit`

## AC-6: 캐시 동작 검증 (REQ-RISK-CACHE-001/002/003)

```
Given 한 번 분석되어 Redis에 캐시된 포트폴리오
When  ?refresh=false 로 동일 포트폴리오·동일 period 를 다시 분석하면
Then  캐시된 결과가 반환되고
And   FinanceDataReader 호출 횟수가 0회이다

Given 캐시가 존재하는 포트폴리오
When  ?refresh=true 로 분석하면
Then  재계산되어 캐시가 갱신된다
```

- 테스트: `test_risk_analysis_redis_cache_hit`

## AC-7: 2종목 미만 처리 (REQ-RISK-CONSTRAINT-001)

```
Given 유효한 가격 데이터를 가진 보유 종목이 1개 이하인 포트폴리오
When  risk-analysis 를 호출하면
Then  HTTP 400과 "최소 2개 종목 필요" 안내가 반환되고
And   계산이 수행되지 않는다
```

- 테스트: `test_risk_analysis_min_two_holdings`(unit), `test_risk_analysis_endpoint_400_min_holdings`(integration)

## AC-8: 인증·소유권 검증 (REQ-RISK-AUTH-001/002/003)

```
Given 존재하지 않는 portfolio_id
When  risk-analysis 를 호출하면
Then  HTTP 404 가 반환된다

Given 다른 사용자가 소유한 포트폴리오
When  risk-analysis 를 호출하면
Then  HTTP 403(또는 코드베이스 관례상 404)이 반환된다
```

- 테스트: `test_risk_analysis_portfolio_not_found`, `test_risk_analysis_wrong_owner`

## AC-9: FDR 실패 graceful 처리 (REQ-RISK-DATA-002)

```
Given 보유 종목 중 일부의 FinanceDataReader 호출이 실패하거나 빈 데이터를 반환
When  risk-analysis 를 호출하면
Then  예외가 전파되지 않고 실패 종목은 분석에서 제외되며
And   나머지 종목으로 결과가 산출된다 (유효 종목 2개 이상일 때)
```

- 테스트: `test_risk_analysis_fdr_failure_graceful`

## AC-10: period 파라미터 검증 (REQ-RISK-PERIOD-001/002)

```
Given risk-analysis 엔드포인트
When  period 파라미터를 생략하면
Then  기본값 90이 사용된다

When  period 가 {30,60,90,180,252} 이외의 값이면
Then  HTTP 422 가 반환된다
```

- 테스트: `test_risk_analysis_endpoint_422_invalid_period`(integration)

## AC-11: 프론트엔드 RiskAnalysisPanel (REQ-RISK-FE-001/002/003/004)

```
Given Portfolio 페이지의 RiskAnalysisPanel
When  분석 결과가 로드되면
Then  상관관계 히트맵(색상 그라데이션)·변동성 테이블·포트폴리오 요약이 렌더링되고
And   기간 선택기(30/60/90/180/252일) 변경 시 재조회된다
```

- 테스트: 프론트 컴포넌트 테스트(렌더, 기간 선택기 변경)

---

## 테스트 매핑 요약

| 테스트 함수 | AC | REQ | 종류 |
|------------|----|----|------|
| `test_correlation_matrix_calculation` | AC-2 | REQ-RISK-002 | unit |
| `test_volatility_calculation` | AC-3 | REQ-RISK-003/DATA-003 | unit |
| `test_portfolio_volatility_with_weights` | AC-4 | REQ-RISK-004 | unit |
| `test_diversification_benefit` | AC-5 | REQ-RISK-005 | unit |
| `test_risk_analysis_redis_cache_hit` | AC-6 | REQ-RISK-CACHE-001/002/003 | unit |
| `test_risk_analysis_min_two_holdings` | AC-7 | REQ-RISK-CONSTRAINT-001 | unit |
| `test_risk_analysis_portfolio_not_found` | AC-8 | REQ-RISK-AUTH-002 | unit |
| `test_risk_analysis_wrong_owner` | AC-8 | REQ-RISK-AUTH-003 | unit |
| `test_risk_analysis_fdr_failure_graceful` | AC-9 | REQ-RISK-DATA-002 | unit |
| `test_risk_analysis_endpoint_200` | AC-1 | REQ-RISK-001 | integration |
| `test_risk_analysis_endpoint_400_min_holdings` | AC-7 | REQ-RISK-CONSTRAINT-001 | integration |
| `test_risk_analysis_endpoint_422_invalid_period` | AC-10 | REQ-RISK-PERIOD-002 | integration |

> 백엔드 단위 8개 + 통합 3개 = 11개. `test_risk_analysis_returns_full_schema`(AC-1, unit)는 권장 추가 테스트.

## Definition of Done

- [ ] 백엔드 단위 8개 + 통합 3개 테스트 통과 (커버리지 fail_under=85 충족)
- [ ] `GET /portfolios/{id}/risk-analysis` 동작 (correlation_matrix·holdings_volatility·portfolio_volatility_pct·diversification_benefit_pct·period_days·calculated_at)
- [ ] numpy 직접 의존성 추가, scipy 미추가 확인
- [ ] Redis 캐싱 적중 시 FinanceDataReader 호출 0회
- [ ] 프론트 `RiskAnalysisPanel`(히트맵 + 변동성 테이블 + 요약 + 기간 선택기) + Portfolio.tsx 렌더링
- [ ] `ruff check` 통과, 신규 마이그레이션 없음 확인 (0018 유지)
- [ ] 과거 데이터 기반 통계 정보(미래 예측 아님) 면책 응답/UI 명시
