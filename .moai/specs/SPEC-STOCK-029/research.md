# SPEC-STOCK-029 연구 문서 — 포트폴리오 백테스팅 (Portfolio Backtesting)

작성일: 2026-06-22
대상: 보유 포트폴리오(종목 + 비중)를 특정 기간 보유했다면의 수익률을 실제 시세로 시뮬레이션

---

## 0. 핵심 발견 (Critical Findings)

### 0.1 "백테스팅"이라는 이름의 두 가지 서로 다른 기능 — 중복 방지 필수

코드베이스에는 이미 `backend/src/stock_picker/backtest/` 패키지가 **완전히 존재**한다(SPEC-STOCK-012 = Phase 13 "백테스트 엔진 완성"의 산출물).

| 구분 | 기존 `backtest/` (SPEC-012) | SPEC-STOCK-029 (본 SPEC) |
|------|---------------------------|------------------------|
| 본질 | **전략 백테스트**(strategy backtest) | **포트폴리오 백테스트**(portfolio backtest) |
| 입력 | `strategy`(momentum/volume) + 날짜 + universe_size/top_n | 사용자의 **보유 포트폴리오**(종목+비중) + 날짜 |
| 동작 | KRX 유니버스에서 전략으로 종목을 선별·매수 시뮬레이션 | 사용자가 **이미 가진** 종목 구성을 그대로 보유했다고 가정하고 시뮬레이션 |
| 실행 모델 | **비동기 잡**(`backtest_runs` 테이블, run_id, pending→running→done/failed, `asyncio.create_task`) | **동기 1회 계산**(요청-응답, 잡 테이블 불필요) — 리스크 분석(SPEC-027)과 동일 패턴 |
| 거래소 | **KRX 전용**(`_get_krx_universe` 하드코딩 20종목) | **KRX + NYSE/NASDAQ**(SPEC-028 exchange 필드 활용) |
| 엔드포인트 | `POST /backtest/run`, `GET /backtest/runs`, `GET /backtest/runs/{id}`, `GET /backtest/runs/{id}/results` | `POST /portfolios/{portfolio_id}/backtest` (신규, portfolio 도메인) |
| 위치 | `backtest/` 별도 도메인 | `portfolio/backtest.py` (portfolio 도메인 내부) |

**결론**: 두 기능은 다른 기능이다. SPEC-029는 **portfolio 도메인**에 속하며, `risk_analysis.py`·`ai_analysis.py`와 형제인 `portfolio/backtest.py`로 구현해야 한다. 기존 `backtest/` 패키지를 재정의·수정하지 않는다.

### 0.2 기존 `backtest/metrics.py` 순수 함수는 재사용 가능

`backend/src/stock_picker/backtest/metrics.py`에 검증된 순수 함수가 존재한다:
- `calculate_max_drawdown(cumulative_returns: list[float]) -> float` — peak 대비 최대 낙폭(음수)
- `calculate_sharpe_ratio(daily_returns: list[float], risk_free_rate: float = 0.02) -> float` — 일별 무위험 변환 후 `× √252` 연환산
- `calculate_cagr`, `calculate_total_return`, `calculate_win_rate`, `build_portfolio_value_series`

이 함수들은 통화·전략에 무관한 순수 수치 계산이므로 SPEC-029의 포트폴리오 백테스트에서 **import 재사용**할 수 있다. 단, 무위험수익률 기본값이 SPEC-029 요구(한국 3.5%)와 다르다(기존 2%) — 호출 시 명시적으로 `risk_free_rate=0.035`를 전달하면 충돌 없이 재사용 가능.

---

## 1. 백엔드 portfolio 도메인 구조

### 1.1 `portfolio/service.py` — PortfolioService
- CRUD: `create_portfolio`, `list_portfolios`, `get_portfolio_with_holdings`(소유권 검증 포함), `add_holding`, `remove_holding`
- `calculate_performance(db, portfolio_id, user_id, redis)` — KRX/해외 자산 현재가 기반 성과(SPEC-017·028). 해외 종목은 `_fetch_foreign_price`(USD) × USD/KRW 환율 → KRW 환산.
- `optimize_portfolio(...)` — AI 최적화(SPEC-026)
- 해외 가격 조회 헬퍼: `_fetch_foreign_price_sync`/`_fetch_foreign_price`(Redis 캐시 키 `foreign_price:{ticker}`, TTL 86400s)
- 핵심 패턴: `getattr(h, "market", "KRX")`, `getattr(h, "currency", "KRW")`로 하위호환 안전 접근

### 1.2 `portfolio/risk_analysis.py` — 가장 가까운 참조 모델 (SPEC-027)
SPEC-029가 모방해야 할 **표준 패턴**을 모두 담고 있다:
- **FDR 시계열 조회**: `_fetch_stock_prices(krx_code, period) -> list[dict]` — 동기 함수, `loop.run_in_executor(None, ...)`로 격리. `fdr.DataReader(code, start=...)`, Close 컬럼 탐색(`Close`/`close`/`종가`), NaN 제거, `[{"date": str, "close": float}]` 반환
- **순수 함수 레이어**: `_daily_returns`(arr[1:]/arr[:-1] - 1), `_align_returns`(공통 거래일 inner join) 등 numpy 기반
- **오케스트레이션**: `calculate_risk_analysis(portfolio_id, user_id, db, redis, period=90, refresh=False)`
  1. 소유권 확인(404) → 2. Redis 캐시 조회(refresh 시 건너뜀) → 3. FDR 병렬 조회(`asyncio.gather`) → 4. 실패 종목 제외 → 5. 순수 함수 계산 → 6. 결과 구성 → 7. `redis.setex(TTL=3600)` graceful
- **환율 처리**: USD 보유 종목 있으면 `fx_rate_module.get_usd_krw_rate(redis)` 1회 조회, 실패 시 `_FALLBACK_RATE`(1350.0). 가중치는 KRW 환산(`avg_buy_price × quantity × fx_rate_if_usd`)
- **scipy 금지**: numpy만 사용(`# @MX:NOTE: scipy 의존성 금지`)

### 1.3 `portfolio/ai_analysis.py` — Claude 호출 패턴
- 본 SPEC은 Claude 호출 불필요(순수 수치 계산). 단 면책 문구 패턴(`_DISCLAIMER = "본 분석은 투자 권유가 아닌 정보 제공 목적입니다."`)은 응답 summary에 참고 가능.

### 1.4 `portfolio/router.py` — 엔드포인트 패턴
- prefix `/portfolios`(복수), 모든 엔드포인트 `Depends(get_current_user)` + 소유권 확인(404)
- 예시: `GET /{portfolio_id}/risk-analysis`(period 화이트리스트 검증→422), `GET /{portfolio_id}/performance`, `POST /{portfolio_id}/optimize`
- `redis: aioredis.Redis = Depends(get_redis_client)` 주입
- **router.py는 커버리지 제외**: `pyproject.toml` `omit = ["*/router.py", "*/dividends.py"]`

### 1.5 `portfolio/schemas.py` — Pydantic v2 패턴
- `HoldingCreate`: `market: Literal["KRX","NYSE","NASDAQ"] = "KRX"`, `currency: Literal["KRW","USD"] = "KRW"`, `model_validator(mode="after")`로 market-currency 정합성 검증
- `field_validator`로 입력 검증(수량>0, 가격>0, 코드 비어있지 않음)
- 응답 스키마는 `ConfigDict(from_attributes=True)`

---

## 2. DB 모델 (`db/models.py`)

### 2.1 `PortfolioHolding` (line 246~) — SPEC-029 입력 소스
```
id, portfolio_id(FK), krx_code, quantity, avg_buy_price(Numeric),
market(String(10), default "KRX"),   # SPEC-028
currency(String(3), default "KRW"),  # SPEC-028
added_at
UNIQUE(portfolio_id, krx_code, market)  # uq_holding_portfolio_ticker_market
```
→ SPEC-029는 이 보유 종목을 읽어 비중을 산출하거나, 요청 본문으로 종목+비중을 직접 받는다. **신규 컬럼·테이블·마이그레이션 불필요**.

### 2.2 `BacktestRun` / `BacktestDailyResult` (line 357~) — 기존 전략 백테스트 전용
→ SPEC-029는 이 테이블을 사용하지 않는다. 동기 1회 계산이므로 영속화 불필요.

---

## 3. FDR(FinanceDataReader) 기간 시세 조회

### 3.1 검증된 사용 패턴 (risk_analysis.py / backtest/runner.py 공통)
```python
import FinanceDataReader as fdr
df = fdr.DataReader(ticker, start="YYYY-MM-DD", end="YYYY-MM-DD")
# df.index = 거래일(DatetimeIndex), df["Close"] = 종가
```
- 동기 함수 → 반드시 `loop.run_in_executor(None, fn, ...)`로 이벤트 루프 격리
- Close 컬럼은 `Close`/`close`/`종가` 순으로 탐색(해외는 `Close`)
- 실패/빈 데이터 시 graceful(빈 리스트 또는 None 반환, 경고 로그)
- 해외 종목(AAPL 등)도 동일 API로 조회 가능(`fdr.DataReader("AAPL", start, end)`)

### 3.2 거래소별 처리
- KRX: `fdr.DataReader("005930", start, end)` → KRW 종가
- NYSE/NASDAQ: `fdr.DataReader("AAPL", start, end)` → USD 종가. KRW 통일을 위해 USD/KRW 환율 적용 필요(`fx_rate_module.get_usd_krw_rate`)
- **상관계수와 달리, 포트폴리오 가치는 통화에 의존** → 해외 종목은 KRW 환산 후 합산해야 정확

### 3.3 의존성 (pyproject.toml 확인)
- `finance-datareader>=0.9` — 이미 존재
- `numpy>=1.26` — 이미 존재
- → **신규 라이브러리 도입 없음**

---

## 4. 테스트 패턴 (`backend/tests/`)

### 4.1 디렉터리 구조 (실제 경로)
- `backend/tests/unit/` — `test_portfolio_risk.py`, `test_ai_analysis.py`, `test_portfolio_optimize.py`, `test_backtest_metrics.py`, `test_backtest_runner.py`
- `backend/tests/integration/` — `test_backtest_router.py`
- `conftest.py`, `fixtures/` 존재
- **주의: 작업 지시의 `backend/tests/unit/test_backtest.py`는 기존 `test_backtest_metrics.py`/`test_backtest_runner.py`와 이름이 겹칠 수 있음** → SPEC-029 테스트는 `test_portfolio_backtest.py`로 명명하여 충돌 회피 권장

### 4.2 테스트 스타일 (test_portfolio_risk.py 기준)
- `asyncio_mode = "auto"` → `@pytest.mark.asyncio` 불필요
- 순수 함수는 직접 단위 테스트(`pytest.approx`로 부동소수 비교)
- 오케스트레이션은 `MagicMock`(db) + `AsyncMock`(redis) + `patch("...._fetch_stock_prices", side_effect=...)` 로 FDR 모킹
- `_make_portfolio`, `_make_holding`, `_make_price_history` 헬퍼 팩토리 패턴
- 캐시 히트/미스/refresh/Redis 장애/FDR 실패/유효 종목 부족(400) 시나리오 커버
- 해외 자산: `_make_holding_with_market(code, qty, price, market, currency)` + `patch("....fx_rate_module.get_usd_krw_rate", new=AsyncMock(return_value=1350.0))`

### 4.3 커버리지
- `pyproject.toml` `fail_under = 75`, `omit = ["*/router.py", "*/dividends.py"]`
- → `portfolio/backtest.py`(서비스·순수 함수)는 커버리지 대상, `router.py` 추가분은 제외

---

## 5. 프론트엔드

### 5.1 기존 자산
- `frontend/src/api/portfolio.ts` — `authHeaders(token)` 공통 헤더, `apiGetPerformance`/`apiGetRiskAnalysis`/`apiOptimizePortfolio` 패턴. `Market`/`Currency` 타입 export. (`.js`는 빌드 산출물 — 둘 다 갱신 필요)
- `frontend/src/api/backtest.ts` — **기존 전략 백테스트 API**(`runBacktest`, `BacktestRunRequest{strategy,...}`). SPEC-029와 별개. 혼동 주의.
- `frontend/src/pages/Portfolio.tsx` — 포트폴리오 페이지. `PortfolioScoreCard`/`RebalancingTable`/`NewStockSuggestions`/`RiskAnalysisPanel` 컴포넌트 렌더. SPEC-029 패널은 여기에 추가.
- `frontend/src/pages/Backtest.tsx` — 기존 전략 백테스트 페이지(별개)
- 차트: Recharts 사용(메모리: 기술 스택 확정)

### 5.2 SPEC-029 프론트 신규
- `frontend/src/components/BacktestChart.js` — 일별/누적 수익률 라인 차트(Recharts)
- `frontend/src/components/BacktestPanel.js` — 기간 입력 + 실행 + MDD/Sharpe/누적수익률 요약 표시
- `portfolio.ts`(+`.js`)에 `apiRunPortfolioBacktest` + 타입 추가
- `Portfolio.tsx`(+`.js`)에 BacktestPanel 통합
- **주의: 파일명이 `Backtest*`와 유사**. `BacktestChart`/`BacktestPanel`은 portfolio 도메인 컴포넌트임을 주석으로 명시. 기존 `Backtest.tsx`(전략)와 구분.

---

## 6. 알고리즘 설계 (작업 지시 + 코드 검증 반영)

```
입력: holdings[{ticker, weight, market, currency}], start_date, end_date, risk_free_rate(기본 0.035)

1. 각 종목 FDR.DataReader(ticker, start, end) → 일별 종가 시계열 (run_in_executor 격리, 병렬 gather)
   - 해외 종목: USD 종가 × USD/KRW 환율 → KRW 환산 (포트폴리오 가치는 통화 의존)
2. 공통 거래일 정렬 (inner join, risk_analysis._align_returns 패턴 재사용 가능)
3. 각 종목 초기 투자금 = weight (비중) — 시작일 가치를 1.0(또는 100)으로 정규화
   일별 종목 가치 = weight × (종가[t] / 종가[0])
4. 일별 포트폴리오 가치 = Σ(종목별 일별 가치)
5. 일별 수익률 = (가치[t] - 가치[t-1]) / 가치[t-1]
6. 누적 수익률 = (가치[t] / 가치[0]) - 1
7. MDD = min((가치[t] - 이전최고가치) / 이전최고가치)   # backtest/metrics.calculate_max_drawdown 재사용
8. 샤프 비율 = (mean(일별수익률) - 무위험일률) / std(일별수익률) × √252
   # backtest/metrics.calculate_sharpe_ratio(daily_returns, risk_free_rate=0.035) 재사용
   # 무위험수익률 기본값 3.5%(한국 기준) — 기존 metrics 기본값 2%를 명시적으로 오버라이드
출력: {daily[{date, value, daily_return, cumulative_return}], mdd, sharpe, total_return, period_days}
```

### 6.1 비중 정규화 주의점
- 입력 비중 합이 100%가 아닐 수 있음 → 정규화(`weight_i / Σweight`) 필요
- 또는 보유 종목의 `avg_buy_price × quantity`(KRW 환산)로 비중을 서버에서 산출하는 방식도 가능 → SPEC에서 입력 방식을 명확히 정의해야 함

### 6.2 무위험수익률
- 작업 지시: 기본값 3.5%(한국 기준). 기존 `metrics.calculate_sharpe_ratio`는 0.02 기본값이므로 호출 시 `risk_free_rate=0.035` 명시 전달.

---

## 7. 설계 결정 요약 (SPEC 반영)

1. **도메인 위치**: `portfolio/backtest.py` (portfolio 도메인 내부, risk_analysis.py 형제). 기존 `backtest/` 패키지(전략 백테스트, SPEC-012)와 명확히 분리.
2. **실행 모델**: 동기 1회 요청-응답(risk_analysis 패턴). `backtest_runs` 잡 테이블 미사용. 영속화 없음(one-shot).
3. **엔드포인트**: `POST /portfolios/{portfolio_id}/backtest` (신규). 인증·소유권 404.
4. **순수 함수 재사용**: `backtest/metrics.py`의 `calculate_max_drawdown`, `calculate_sharpe_ratio`를 import. 무위험수익률은 0.035 전달.
5. **해외 자산**: KRW 환산 후 합산. USD 종목은 fx_rate 적용. 환율 실패 시 fallback 1350.0.
6. **신규 DB/마이그레이션 없음**: 마이그레이션 최신(0018) 유지.
7. **테스트 파일명**: `test_portfolio_backtest.py` (기존 `test_backtest_*.py`와 충돌 회피).
8. **프론트 컴포넌트**: `BacktestChart.js` + `BacktestPanel.js` (portfolio 도메인, 기존 전략 Backtest와 구분 주석).
9. **REQ 접두사**: `REQ-PBT-*` (Portfolio BackTest — 기존 SPEC-012의 `REQ-BT-*`와 충돌 회피).
10. **영구 제외 준수**: 자동 매매/주문 실행 영구 제외. 거래 비용·실시간 스트리밍 제외.
