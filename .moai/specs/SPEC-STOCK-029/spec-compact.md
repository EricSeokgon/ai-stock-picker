# SPEC-STOCK-029 압축본 (Run 단계용) — 포트폴리오 백테스팅 (v0.2.0)

> 사용자 보유 포트폴리오(종목+비중)를 특정 기간 보유했다고 가정한 수익률 시뮬레이션. **portfolio 도메인** 신규 기능. 기존 `backtest/` 패키지(전략 백테스트, SPEC-012)와 **별개** — REQ 접두사 `REQ-PBT-*`, 테스트 `test_portfolio_backtest.py`, 컴포넌트 `BacktestChart`/`BacktestPanel`로 충돌 회피.

---

## EARS 요구사항

### 백테스트 계산
- **REQ-PBT-001**: THE 백테스팅 서비스 SHALL 일별 포트폴리오 가치를 산출한다.
- **REQ-PBT-002**: THE 백테스팅 서비스 SHALL 일별 수익률·누적 수익률을 산출한다.
- **REQ-PBT-003**: THE 백테스팅 서비스 SHALL MDD(이전 최고점 대비 최대 하락폭)를 산출한다.
- **REQ-PBT-004**: THE 백테스팅 서비스 SHALL 연환산 샤프 비율을 산출한다(무위험수익률 기본 `0.035`).
- **REQ-PBT-005**: THE 백테스팅 서비스 SHALL 모든 종목 가치를 KRW로 통일하여 합산한다.

### 시세 조회
- **REQ-PBT-010**: WHEN 백테스트 요청 제출 시 THE 시스템 SHALL FDR로 기간 시세를 조회한다.
- **REQ-PBT-011**: THE 시스템 SHALL 동기 FDR 조회를 이벤트 루프 블로킹 없이 격리 실행한다.
- **REQ-PBT-012**: THE 시스템 SHALL 모든 종목 시계열을 공통 거래일 기준 정렬한다.
- **REQ-PBT-013**: WHILE NYSE/NASDAQ 종목 포함 시 THE 시스템 SHALL USD 종가에 USD/KRW 환율을 적용해 KRW 환산한다.
- **REQ-PBT-014**: IF 종목 시세 조회 실패/부족 시 THEN THE 시스템 SHALL 해당 종목을 제외하고 응답에 표시한다.
- **REQ-PBT-015**: IF 환율 조회 실패 시 THEN THE 시스템 SHALL fallback(`1350.0`)으로 계산을 완료한다.

### 입력 검증
- **REQ-PBT-020**: IF 날짜 구간 무효(시작일 ≥ 종료일) 시 THEN `400 Bad Request`.
- **REQ-PBT-021**: IF 종목 0개 시 THEN `400 Bad Request`.
- **REQ-PBT-022**: IF 유효 종목 0개 시(일부 제외 후 0개 또는 전 종목 조회 실패) THEN `422 Unprocessable Entity`와 메시지 반환, 예외 비전파.
- **REQ-PBT-023**: THE 시스템 SHALL 비중 합 ≠ 100% 시 정규화(`weight_i / Σweight`)한다.

### 인증·소유권
- **REQ-PBT-030**: THE 엔드포인트 SHALL 인증된 사용자만 허용한다.
- **REQ-PBT-031**: IF 포트폴리오 부재/타사용자 소유 시 THEN `404 Not Found`.

### 응답 구조
- **REQ-PBT-040**: THE 응답 SHALL 일별 결과(날짜·가치·일별수익률·누적수익률) 목록을 포함한다.
- **REQ-PBT-041**: THE 응답 SHALL MDD·샤프 비율·총 수익률·거래일 수를 포함한다.
- **REQ-PBT-042**: WHERE 종목 제외 시 THE 응답 SHALL excluded_tickers·used_tickers를 포함한다.

### 프론트엔드
- **REQ-PBT-050**: WHEN 기간 입력·실행 시 THE 프론트엔드 SHALL 백테스트 API를 호출하고 결과를 표시한다.
- **REQ-PBT-051**: THE 프론트엔드 SHALL 일별/누적 수익률을 라인 차트로 시각화한다.
- **REQ-PBT-052**: THE 프론트엔드 SHALL MDD·샤프 비율·총 수익률을 요약 표시한다.
- **REQ-PBT-053**: IF API 오류(400/404/422) 시 THEN 오류 메시지 표시·차트 미렌더.

### 비기능
- **REQ-PBT-NFR-001**: scipy 금지, numpy·표준 라이브러리만 사용.
- **REQ-PBT-NFR-002**: SPEC-028 Redis 캐시 재사용(해외가 TTL≥86400s, 환율 TTL≥3600s).
- **REQ-PBT-NFR-003**: 응답에 면책 정보 포함.
- **REQ-PBT-NFR-004**: `portfolio/backtest.py` 커버리지 ≥ 75%.

---

## 인수 조건 (Given-When-Then 요약)

- **AC-1**: 유효 포트폴리오+날짜 → 200, daily/mdd/sharpe/total_return 반환, 마지막 cumulative=total_return.
- **AC-2**: 날짜 역전 → 400, FDR 미조회.
- **AC-3**: 단일 자산 100% → 가치=종가 비율, 누적=종가[末]/종가[初]-1.
- **AC-4**: KRX+AAPL(NASDAQ) → USD×환율 KRW 환산, used_tickers에 둘 다.
- **AC-5**: 일부 종목 실패 → 제외 후 계속, excluded/used_tickers 표시.
- **AC-6**: 유효 종목 0개(전 종목 실패) → 422, 예외 비전파.
- **AC-13**: 빈 포트폴리오(종목 0개) → 400, FDR 미조회.
- **AC-7**: 환율 실패 → fallback 1350.0, 200 반환.
- **AC-8**: 타사용자 포트폴리오 → 404.
- **AC-9**: MDD 음수≤0, 샤프 무위험 0.035 적용 ×√252 연환산.
- **AC-10**: 프론트 기간 입력·실행 → 차트+요약 렌더.
- **AC-11**: API 오류 → 메시지 표시·차트 미렌더.
- **AC-12**: scipy import 없음.

---

## 수정·신규 파일 목록

### Backend
- `portfolio/schemas.py` — 추가: `BacktestRequest`·`DailyReturn`·`BacktestResult`
- `portfolio/backtest.py` — **신규**: 순수 함수(`_normalize_weights`·`_daily_portfolio_values`·`_daily_returns`·`_cumulative_returns`) + FDR 헬퍼(`_fetch_price_series_sync`) + 오케스트레이션(`run_portfolio_backtest`)
- `portfolio/router.py` — 추가: `POST /portfolios/{portfolio_id}/backtest`(커버리지 제외)

### Frontend
- `frontend/src/api/portfolio.ts` (+`.js`) — 추가: `apiRunPortfolioBacktest`·타입
- `frontend/src/components/BacktestChart.js` — **신규**(Recharts 라인 차트)
- `frontend/src/components/BacktestPanel.js` — **신규**(기간 입력·실행·요약)
- `frontend/src/pages/Portfolio.tsx` (+`.js`) — 추가: BacktestPanel 통합

### Tests (TDD)
- `backend/tests/unit/test_portfolio_backtest.py` — **신규**(순수 함수·오케스트레이션)
- `backend/tests/integration/test_portfolio_backtest_router.py` — **신규**(200/400/404/422)

### 재사용 (수정 금지)
- `backend/src/stock_picker/backtest/metrics.py` — `calculate_max_drawdown`·`calculate_sharpe_ratio(risk_free_rate=0.035)` import
- `portfolio/fx_rate.py` — `get_usd_krw_rate`·`_FALLBACK_RATE`
- `portfolio/service.py` — `get_portfolio_with_holdings`

---

## 제외 사항 (Exclusions)

- **자동 매매/주문 실행** — 규제·책임 리스크로 영구 제외.
- **실시간 백테스팅 스트리밍** — 일별 종가 1회 계산만.
- **거래 비용(수수료·세금·슬리피지) 시뮬레이션** — buy-and-hold 단순 수익률만.
- **리밸런싱 시뮬레이션** — 초기 비중 정적 유지만.
- **백테스트 결과 영속화·히스토리** — 동기 one-shot, 잡 테이블 미사용.
- **전략 백테스트 통합** — 기존 `backtest/`(SPEC-012) 재정의·통합 제외.
- **다중 통화(EUR/JPY 등)** — USD/KRW만.
- **벤치마크 비교(KOSPI 대비 초과수익)** — 포트폴리오 자체 수익률만.
- **신규 DB 테이블·마이그레이션** — 마이그레이션 0018 유지.
