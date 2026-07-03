# SPEC-STOCK-029 인수 조건 — 포트폴리오 백테스팅

대상 SPEC: SPEC-STOCK-029
형식: EARS (각 AC는 관련 REQ의 EARS 유형과 일치)

---

## AC-1: 정상 경로 — 유효 포트폴리오 + 날짜 구간 (REQ-PBT-001~005, 040, 041)

WHEN 인증된 사용자가 KRX 종목으로 구성된 포트폴리오(예: `005930` 60%, `000660` 40%)에 대해 유효한 날짜 구간(시작일 `2025-01-02` < 종료일 `2025-06-30`)으로 백테스트 요청을 제출하고 FDR이 해당 구간의 일별 종가 시계열을 정상 반환하면, THE 시스템 SHALL `200 OK`와 함께 BacktestResult를 반환한다. BacktestResult SHALL `daily`(각 항목 `date`·`portfolio_value`·`daily_return`·`cumulative_return`), `mdd`(≤ 0), `sharpe_ratio`, `total_return`, `period_days`, `excluded_tickers`, `used_tickers`, `disclaimer` 필드를 포함하며, 마지막 거래일의 `cumulative_return`은 `total_return`과 일치한다.

---

## AC-2: 유효하지 않은 날짜 구간 거부 (REQ-PBT-020)

IF 인증된 사용자가 보유 포트폴리오에 대해 유효하지 않은 날짜 구간(시작일 `2025-06-30` ≥ 종료일 `2025-01-02`)으로 백테스트를 요청하는 경우, THEN THE 시스템 SHALL `400 Bad Request`로 응답하고 FDR 시세 조회를 수행하지 않는다.

---

## AC-3: 단일 자산 (비중 100%) 계산 정확성 (REQ-PBT-001, 002, 023)

WHEN 인증된 사용자가 단일 종목(`005930` 100% 비중)만 보유하고 FDR이 해당 종목의 종가 시계열을 반환하는 상태에서 백테스트를 실행하면, THE 시스템 SHALL 일별 포트폴리오 가치를 해당 종목의 종가 비율(`종가[t] / 종가[0]`)과 동일하게 산출하고, 누적 수익률을 `(종가[마지막] / 종가[0]) - 1`과 일치하게 산출한다.

---

## AC-4: 해외 자산(NYSE/NASDAQ) 포함 KRW 환산 (REQ-PBT-013, 005)

WHILE 포트폴리오가 KRX 종목(`005930`, KRW)과 해외 종목(`AAPL`, NASDAQ, USD)을 함께 포함하고 FDR이 `AAPL`의 USD 종가 시계열을 반환하며 USD/KRW 환율 조회가 정상(예: 1350.0)인 상태에서, THE 시스템 SHALL `AAPL`의 USD 종가에 환율을 적용하여 KRW 환산 가치로 계산에 포함하고, 포트폴리오 가치를 KRW 단위로 통일하여 합산하며, 응답 `used_tickers`에 `005930`과 `AAPL`을 모두 포함한다.

---

## AC-5: 일부 종목 시세 조회 실패 시 graceful 제외 (REQ-PBT-014, 042)

IF 인증된 사용자가 3개 종목을 보유한 상태에서 그중 1개 종목의 FDR 시세 조회가 실패(빈 데이터)하는 경우, THEN THE 시스템 SHALL 실패 종목을 백테스트 대상에서 제외하고 나머지 유효 종목으로 계산을 계속 진행하며, 응답 `excluded_tickers`에 실패 종목을, `used_tickers`에 나머지 2개 종목을 포함한다.

---

## AC-6: 유효 종목 0개 시 422 (REQ-PBT-022)

IF 인증된 사용자가 보유 포트폴리오에 대해 백테스트를 요청했으나 모든 종목의 FDR 시세 조회가 실패하여 유효 종목이 0개인 경우, THEN THE 시스템 SHALL `422 Unprocessable Entity`와 메시지로 응답하고 예외를 전파하지 않는다.

---

## AC-7: 환율 조회 실패 시 fallback (REQ-PBT-015)

IF 인증된 사용자가 해외 종목(`AAPL`, NASDAQ, USD)을 포함한 포트폴리오에 대해 백테스트를 실행했으나 USD/KRW 환율 조회가 실패하는 경우, THEN THE 시스템 SHALL fallback 환율(`1350.0`)을 사용하여 계산을 중단하지 않고 완료하며 `200 OK`로 백테스트 결과를 반환한다.

---

## AC-8: 소유권 없는 포트폴리오 거부 (REQ-PBT-030, 031)

IF 인증된 사용자 A가 사용자 B 소유의 포트폴리오 ID로 `POST /portfolios/{portfolio_id}/backtest`를 호출하는 경우, THEN THE 시스템 SHALL `404 Not Found`로 응답한다.

---

## AC-9: MDD·샤프 비율 산출 (REQ-PBT-003, 004)

WHEN 백테스트 일별 포트폴리오 가치 시계열이 산출되면, THE 시스템 SHALL MDD를 이전 최고가치 대비 최대 하락폭(음수 또는 0)으로 산출하고, 샤프 비율을 무위험수익률 `0.035`(한국 기준)를 적용하여 `(평균 일별수익률 - 무위험일률) / 표준편차 × √252`로 연환산 산출한다.

---

## AC-10: 프론트엔드 차트·요약 렌더 (REQ-PBT-050, 051, 052)

WHEN 사용자가 포트폴리오 페이지의 백테스트 패널에서 시작일·종료일을 입력하고 실행 버튼을 클릭하면, THE 프론트엔드 SHALL 백테스트 API를 호출하고 일별/누적 수익률을 라인 차트로 시각화하며 MDD·샤프 비율·총 수익률을 요약 지표로 표시한다.

---

## AC-11: 프론트엔드 오류 처리 (REQ-PBT-053)

IF 백테스트 API가 오류(`400`/`404`/`422`)를 반환하는 경우, THEN THE 프론트엔드 SHALL 사용자에게 오류 메시지를 표시하고 차트를 렌더링하지 않는다.

---

## AC-12: scipy 미사용 (REQ-PBT-NFR-001)

THE 시스템 SHALL `portfolio/backtest.py` 및 관련 소스에서 `scipy`를 import하지 않으며 numpy 및 표준 라이브러리만 사용한다.

---

## AC-13: 빈 포트폴리오 시 400 (REQ-PBT-021)

IF 백테스트 요청의 포트폴리오 종목이 0개인 경우, THEN THE 시스템 SHALL 400 Bad Request로 응답하고 FDR 시세 조회를 수행하지 않는다.

---

## AC-14: 면책 문구 포함 (REQ-PBT-NFR-003)

THE 시스템 SHALL 모든 백테스트 응답의 `disclaimer` 필드에 '투자 권유가 아니며 정보 제공 목적' 문구를 포함한다.

---

## 엣지 케이스 체크리스트

- [ ] 비중 합이 100%가 아닌 경우 정규화 후 계산 (REQ-PBT-023)
- [ ] 공통 거래일이 2일 미만인 종목 graceful 제외 (REQ-PBT-014)
- [ ] 종목이 하나도 없는 빈 포트폴리오 → 400 (REQ-PBT-021)
- [ ] 단일 거래일만 존재(수익률 계산 불가) → 빈/0 수익률 안전 처리
- [ ] Redis 캐시 장애 시에도 FDR 조회로 계산 완료 (graceful degradation)
- [ ] 기존 `backtest/` 전략 백테스트 테스트 무회귀

---

## 품질 게이트 (Quality Gates / Definition of Done)

- [ ] AC-1 ~ AC-13 전부 통과
- [ ] `test_portfolio_backtest.py` 단위 테스트 전부 통과
- [ ] `portfolio/backtest.py` 커버리지 ≥ 75% (`pyproject.toml` `fail_under`)
- [ ] ruff check 통과 (PEP 준수)
- [ ] scipy import 없음 (NFR-001)
- [ ] 응답에 면책 정보 포함 (NFR-003)
- [ ] MX 태그(ANCHOR·NOTE·WARN, REASON 포함) 부여
- [ ] 기존 `backtest/`·`risk_analysis.py`·`ai_analysis.py` 회귀 없음
- [ ] 신규 DB 마이그레이션 없음(0018 유지)
