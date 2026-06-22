---
id: "SPEC-STOCK-029"
version: "0.2.0"
status: "draft"
created_at: "2026-06-22"
updated: "2026-06-23"
author: "ircp"
priority: "medium"
labels: ["portfolio", "backtesting", "finance", "numpy", "fdr"]
issue_number: 0
---

# SPEC-STOCK-029: 포트폴리오 백테스팅 (Portfolio Backtesting)

## HISTORY

- 2026-06-22 (v0.1.0): 최초 초안 작성. 사용자 보유 포트폴리오(종목+비중)를 특정 기간 보유했다면의 수익률을 실제 FDR 시세로 시뮬레이션. MDD·샤프 비율·일별/누적 수익률 산출. KRX + NYSE/NASDAQ 지원(SPEC-028 exchange 필드 활용). **기존 `backtest/` 패키지(전략 백테스트, SPEC-012)와 별개의 portfolio 도메인 기능**임을 명시.
- 2026-06-23 (v0.2.0): plan-auditor v1 지적사항 반영 — 프론트매터 수정, AC EARS 형식 재작성, REQ-024 통합, 알고리즘 출력 필드명 통일.
- 2026-06-23 (v0.2.0): REQ-PBT-024 삭제: REQ-PBT-022로 통합 (v0.2.0).

> **REQ 접두사 설계 원칙**: 본 SPEC은 `REQ-PBT-*`(Portfolio BackTest) 접두사를 사용한다. 기존 SPEC-STOCK-012(전략 백테스트)가 `REQ-BT-*`를 점유하므로 충돌을 회피한다.

> **번호 체계**: 본 SPEC은 10단위 그룹 구조를 사용한다(REQ-PBT-001~005: 계산, 010~015: 시세 조회, 020~023: 입력 검증, 030~031: 인증, 040~042: 응답, 050~053: 프론트엔드, NFR-001~004: 비기능). 그룹 내 미사용 번호는 향후 확장 예약 슬롯이다. 이 체계는 의도적이며 번호 공백이 아니다.

---

## 1. 개요

### 1.1 목표

사용자가 보유한 포트폴리오(종목 + 비중)를 시작일부터 종료일까지 **그대로 보유했다고 가정**했을 때의 수익률을 실제 과거 시세 데이터로 시뮬레이션한다. 일별·누적 수익률, 최대 낙폭(MDD), 샤프 비율(Sharpe Ratio)을 산출하여 JSON으로 반환하고, 프론트엔드에서 차트로 시각화한다. KRX 종목과 해외 자산(NYSE/NASDAQ)을 함께 지원하며, 모든 가치를 KRW 기준으로 통일하여 계산한다.

### 1.2 배경 (코드베이스 사실)

- **⚠️ 이름 충돌 주의**: 코드베이스에 이미 `backend/src/stock_picker/backtest/` 패키지가 존재한다(SPEC-STOCK-012 산출물). 이는 **전략 백테스트**(momentum/volume 전략으로 KRX 유니버스에서 종목을 선별)이며, 비동기 잡 모델(`backtest_runs` 테이블, run_id)을 사용한다. **본 SPEC-029는 이와 다른 기능**이다 — 사용자가 **이미 보유한** 포트폴리오 구성을 그대로 시뮬레이션하는 **포트폴리오 백테스트**이다.
- 따라서 본 SPEC은 `portfolio` 도메인에 속하며, `portfolio/risk_analysis.py`(SPEC-027)·`portfolio/ai_analysis.py`(SPEC-026)와 형제인 신규 모듈 `portfolio/backtest.py`로 구현한다. 기존 `backtest/` 패키지를 수정·재정의하지 않는다.
- `PortfolioHolding` 모델(`db/models.py:246`)은 SPEC-028에서 추가된 `market`·`currency` 컬럼을 보유하여 해외 자산을 식별할 수 있다.
- `backend/src/stock_picker/backtest/metrics.py`에 검증된 순수 함수 `calculate_max_drawdown`·`calculate_sharpe_ratio`가 존재하며, 통화·전략에 무관한 순수 수치 계산이므로 본 SPEC에서 import 재사용한다.

### 1.3 범위

- IN:
  - 신규 서비스 `portfolio/backtest.py`(포트폴리오 백테스트 계산)
  - 신규 엔드포인트 `POST /portfolios/{portfolio_id}/backtest`(인증·소유권)
  - `BacktestRequest`·`BacktestResult`·`DailyReturn` Pydantic 스키마 추가(`portfolio/schemas.py`)
  - FDR 기간 시세 조회(KRX: KRW, NYSE/NASDAQ: USD→KRW 환산)
  - 일별/누적 수익률, MDD, 샤프 비율 산출
  - 프론트엔드 `BacktestChart`·`BacktestPanel` 컴포넌트 + API 클라이언트 확장
  - 통합 테스트 `backend/tests/integration/test_portfolio_backtest_router.py`
- OUT: §5 제외 사항 참조.

### 1.4 기술 스택 (확정·재사용)

FastAPI + PostgreSQL(asyncpg) + Redis + React + TypeScript + Recharts + FinanceDataReader(FDR) + numpy. 신규 라이브러리는 도입하지 않는다(`finance-datareader>=0.9`·`numpy>=1.26`는 pyproject.toml에 이미 존재). 무위험수익률 기본값은 한국 기준 3.5%(0.035)를 사용한다.

---

## 2. 기능 요구사항 (EARS)

> **번호 체계**: 본 SPEC은 10단위 그룹 구조를 사용한다(REQ-PBT-001~005: 계산, 010~015: 시세 조회, 020~023: 입력 검증, 030~031: 인증, 040~042: 응답, 050~053: 프론트엔드, NFR-001~004: 비기능). 그룹 내 미사용 번호는 향후 확장 예약 슬롯이다. 이 체계는 의도적이며 번호 공백이 아니다.

### 2.1 백테스트 계산 (REQ-PBT-001 ~ 005)

- **REQ-PBT-001** (Ubiquitous): THE 백테스팅 서비스 SHALL 입력된 포트폴리오 구성에 대해 시작일부터 종료일까지의 일별 포트폴리오 가치를 산출한다.
- **REQ-PBT-002** (Ubiquitous): THE 백테스팅 서비스 SHALL 일별 포트폴리오 가치로부터 일별 수익률과 시작일 대비 누적 수익률을 산출한다.
- **REQ-PBT-003** (Ubiquitous): THE 백테스팅 서비스 SHALL 포트폴리오 가치 시계열로부터 최대 낙폭(MDD, 이전 최고점 대비 최대 하락폭)을 산출한다.
- **REQ-PBT-004** (Ubiquitous): THE 백테스팅 서비스 SHALL 일별 수익률과 무위험수익률로부터 연환산 샤프 비율을 산출한다. 무위험수익률 기본값은 `0.035`(한국 기준)이다.
- **REQ-PBT-005** (Ubiquitous): THE 백테스팅 서비스 SHALL 모든 종목의 가치를 KRW 단위로 통일하여 포트폴리오 가치를 합산한다.

### 2.2 시세 데이터 조회 (REQ-PBT-010 ~ 015)

- **REQ-PBT-010** (Event-driven): WHEN 사용자가 백테스트 요청을 제출하면 THE 시스템 SHALL 요청된 각 종목의 시작일~종료일 구간 과거 시세 데이터를 외부 데이터 공급자(FDR)를 통해 조회한다.
- **REQ-PBT-011** (Ubiquitous): THE 시스템 SHALL FDR 시세 조회 시 동기 I/O 작업을 이벤트 루프 블로킹 없이 비동기 컨텍스트에서 격리 실행한다.
- **REQ-PBT-012** (Ubiquitous): THE 시스템 SHALL 백테스트 계산 시 모든 종목 시계열을 공통 거래일 기준으로 정렬한다.
- **REQ-PBT-013** (State-driven): WHILE NYSE/NASDAQ 종목이 포트폴리오에 포함된 경우 THE 시스템 SHALL 해당 종목의 USD 종가에 USD/KRW 환율을 적용하여 KRW 환산 가치를 산출한다.
- **REQ-PBT-014** (Unwanted): IF 특정 종목의 시세 데이터 조회가 실패하거나 공통 거래일이 2일 미만인 경우, THEN THE 시스템 SHALL 해당 종목을 백테스트 대상에서 제외하고 응답에 제외 사실을 표시한다.
- **REQ-PBT-015** (Unwanted): IF 환율 조회가 실패한 경우, THEN THE 시스템 SHALL fallback 기본값(`1350.0`)을 사용하여 계산을 중단하지 않고 완료한다.

### 2.3 입력 검증 (REQ-PBT-020 ~ 023)

- **REQ-PBT-020** (Unwanted): IF 백테스트 요청의 날짜 구간이 유효하지 않은 경우(시작일 ≥ 종료일), THEN THE 시스템 SHALL `400 Bad Request`로 응답한다.
- **REQ-PBT-021** (Unwanted): IF 백테스트 요청에 종목이 하나도 포함되지 않은 경우, THEN THE 시스템 SHALL `400 Bad Request`로 응답한다.
- **REQ-PBT-022** (Unwanted): IF 백테스트 대상 유효 종목(시세 조회 성공)이 0개인 경우(일부 종목 제외 후 유효 종목 0개, 또는 FDR 데이터 공급이 일시적으로 불가능하여 전 종목 조회 실패), THEN THE 시스템 SHALL `422 Unprocessable Entity`와 메시지로 응답하고 예외를 전파하지 않는다.
- **REQ-PBT-023** (Ubiquitous): THE 시스템 SHALL 입력된 종목 비중의 합이 1(100%)이 아닌 경우 비중을 정규화(`weight_i / Σweight`)하여 계산한다.

### 2.4 인증·소유권 (REQ-PBT-030 ~ 031)

- **REQ-PBT-030** (Ubiquitous): THE 백테스트 엔드포인트 SHALL 인증된 사용자만 접근을 허용한다.
- **REQ-PBT-031** (Unwanted): IF 요청한 포트폴리오가 존재하지 않거나 요청 사용자의 소유가 아닌 경우, THEN THE 시스템 SHALL `404 Not Found`로 응답한다.

### 2.5 응답 구조 (REQ-PBT-040 ~ 045)

- **REQ-PBT-040** (Ubiquitous): THE 백테스트 응답 SHALL 일별 결과 목록(각 항목: 날짜·포트폴리오 가치·일별 수익률·누적 수익률)을 포함한다.
- **REQ-PBT-041** (Ubiquitous): THE 백테스트 응답 SHALL MDD·샤프 비율·총 수익률·백테스트 거래일 수를 포함한다.
- **REQ-PBT-042** (Optional): WHERE 일부 종목이 시세 부족으로 제외된 경우 THE 응답 SHALL 제외된 종목 목록과 실제 백테스트에 사용된 종목 목록을 포함한다.

### 2.6 프론트엔드 (REQ-PBT-050 ~ 055)

- **REQ-PBT-050** (Event-driven): WHEN 사용자가 백테스트 패널에서 시작일·종료일을 입력하고 실행을 요청하면 THE 프론트엔드 SHALL 백테스트 API를 호출하고 결과를 표시한다.
- **REQ-PBT-051** (Ubiquitous): THE 프론트엔드 SHALL 일별/누적 수익률을 라인 차트로 시각화한다.
- **REQ-PBT-052** (Ubiquitous): THE 프론트엔드 SHALL MDD·샤프 비율·총 수익률을 요약 지표로 표시한다.
- **REQ-PBT-053** (Unwanted): IF 백테스트 API가 오류(400/404/422)를 반환한 경우, THEN THE 프론트엔드 SHALL 사용자에게 오류 메시지를 표시하고 차트를 렌더링하지 않는다.

---

## 3. 비기능 요구사항 (REQ-PBT-NFR)

- **REQ-PBT-NFR-001**: THE 시스템 SHALL 모든 통계 계산에서 `scipy`를 사용하지 않는다. numpy 및 표준 라이브러리만 사용한다(SPEC-027·028과의 일관성).
- **REQ-PBT-NFR-002**: THE 해외 종목 가격 데이터 및 환율 조회 SHALL 기존 Redis 캐시(SPEC-028 `foreign_price:{ticker}` TTL ≥ 86400s, USD/KRW TTL ≥ 3600s)를 재사용하여 FDR 레이트 리밋을 회피한다.
- **REQ-PBT-NFR-003**: THE 백테스트 응답 SHALL 면책 정보를 포함하여 본 시뮬레이션이 투자 권유가 아닌 정보 제공 목적임을 명시한다. `disclaimer` 필드 내용은 최소한 "투자 권유가 아니며 정보 제공 목적" 문구를 포함한다.
- **REQ-PBT-NFR-004**: THE `portfolio/backtest.py` 서비스·순수 함수 코드 SHALL 단위 테스트 커버리지 75% 이상을 충족한다(`router.py` 추가분은 커버리지 제외 대상).

---

## 4. 구현 계획 (기술적 접근)

### 4.1 백테스팅 알고리즘

```
입력: holdings[{ticker, weight, market, currency}], start_date, end_date, risk_free_rate(기본 0.035)

1. 각 종목 FDR 시세 조회: 시작일~종료일 일별 종가 시계열
   (동기 호출을 run_in_executor로 격리, asyncio.gather로 병렬)
2. 해외(NYSE/NASDAQ) 종목: USD 종가 × USD/KRW 환율 → KRW 환산 종가
3. 공통 거래일 기준 정렬(inner join)
4. 비중 정규화: w_i = weight_i / Σweight
5. 일별 종목 가치 = w_i × (종가[t] / 종가[0])   # 시작일 정규화 기준
6. 일별 포트폴리오 가치 = Σ(종목별 일별 가치)
7. 일별 수익률 = (가치[t] - 가치[t-1]) / 가치[t-1]
8. 누적 수익률 = (가치[t] / 가치[0]) - 1
9. MDD = min((가치[t] - 이전 최고가치) / 이전 최고가치)
   → backtest/metrics.calculate_max_drawdown 재사용
10. 샤프 비율 = (mean(일별수익률) - 무위험일률) / std(일별수익률) × √252
   → backtest/metrics.calculate_sharpe_ratio(daily_returns, risk_free_rate=0.035) 재사용
   (무위험수익률 기본값 3.5%(한국 기준)를 명시적으로 전달; 기존 metrics 기본값 2%를 오버라이드)

출력: {daily[{date, portfolio_value, daily_return, cumulative_return}], mdd, sharpe_ratio,
       total_return, period_days, excluded_tickers, used_tickers, disclaimer}
```

### 4.2 BacktestService (`portfolio/backtest.py`)

- `risk_analysis.py` 오케스트레이션 패턴을 모방한다:
  1. 소유권 확인(404). holdings는 DB에서 전적으로 로드한다(요청 본문으로 직접 수신하지 않음).
  2. 입력 검증(날짜 구간·종목 존재) → 400
  3. FDR 병렬 조회(`run_in_executor` + `asyncio.gather`)
  4. 실패/부족 종목 제외, 유효 종목 0개 시 422
  5. 환율 조회(해외 종목 존재 시 `fx_rate_module.get_usd_krw_rate`, 실패 시 fallback)
  6. 순수 함수 계산(numpy)
  7. `BacktestResult` 구성·반환
- 순수 함수 레이어 분리(`_daily_portfolio_values`, `_daily_returns`, `_cumulative_returns` 등) — 단위 테스트 용이성 확보. 공통 거래일 정렬은 `risk_analysis._align_returns` 패턴 참고.

### 4.3 API 엔드포인트 (`portfolio/router.py`)

- `POST /portfolios/{portfolio_id}/backtest` (async)
- `Depends(get_current_user)` + 소유권 확인(404), `redis: aioredis.Redis = Depends(get_redis_client)` 주입
- 요청 본문 `BacktestRequest`(start_date, end_date). holdings는 DB에서 전적으로 로드한다.
- 응답 `BacktestResult`

### 4.4 스키마 (`portfolio/schemas.py`)

- `BacktestRequest`: `start_date: date`, `end_date: date`, `field_validator`로 날짜 구간 검증(end > start)
- `DailyReturn`: `date: str`, `portfolio_value: float`, `daily_return: float`, `cumulative_return: float`
- `BacktestResult`: `daily: list[DailyReturn]`, `mdd: float`, `sharpe_ratio: float`, `total_return: float`, `period_days: int`, `excluded_tickers: list[str]`, `used_tickers: list[str]`, `disclaimer: str`

### 4.5 프론트엔드

- `frontend/src/components/BacktestChart.js` — Recharts 라인 차트(일별/누적 수익률). (portfolio 도메인 컴포넌트 — 기존 전략 `Backtest.tsx`와 구분 주석 명시)
- `frontend/src/components/BacktestPanel.js` — 기간 입력 + 실행 버튼 + MDD/Sharpe/총수익률 요약 + 차트 렌더
- `frontend/src/api/portfolio.ts`(+`.js`) — `apiRunPortfolioBacktest(token, portfolioId, body)` + 타입 추가
- `frontend/src/pages/Portfolio.tsx`(+`.js`) — BacktestPanel 통합

### 4.6 재사용 자산

- `backend/src/stock_picker/backtest/metrics.py`: `calculate_max_drawdown`, `calculate_sharpe_ratio`(risk_free_rate=0.035 전달)
- `portfolio/fx_rate.py`: `get_usd_krw_rate`, `_FALLBACK_RATE`
- `portfolio/service.py`: `get_portfolio_with_holdings`(소유권), 해외 가격 캐시 패턴

---

## 5. 제외 사항 (What NOT to Build)

- **자동 매매/주문 실행**: 규제·책임 리스크로 프로젝트 전체에서 **영구 제외**.
- **실시간 백테스팅 스트리밍**: 실시간 틱 기반 스트리밍 백테스트는 미지원. 일별 종가 기준 1회 계산만 지원.
- **거래 비용(수수료·세금·슬리피지) 시뮬레이션**: 매매 수수료·증권거래세·슬리피지를 반영하지 않는다. 단순 보유 가정(buy-and-hold) 수익률만 계산.
- **리밸런싱 시뮬레이션**: 기간 중 비중 재조정(주기적 리밸런싱)은 미지원. 초기 비중을 만기까지 유지하는 정적 보유 가정만 지원.
- **백테스트 결과 영속화·히스토리**: 동기 1회 계산(one-shot). `backtest_runs` 같은 잡 테이블에 저장하지 않으며 결과 조회 히스토리 API도 제공하지 않는다. (기존 전략 백테스트의 잡 모델과 구분)
- **전략 백테스트 통합**: 기존 `backtest/` 패키지(momentum/volume 전략, SPEC-012)와의 통합·재정의는 범위 밖. 두 기능은 독립적으로 유지한다.
- **다중 통화(EUR/JPY 등)**: USD/KRW 단일 통화쌍만 지원.
- **벤치마크 비교(KOSPI 대비 초과수익)**: 본 SPEC은 포트폴리오 자체 수익률만 계산. 벤치마크 대비 비교는 향후 SPEC.
- **신규 DB 테이블·마이그레이션**: 마이그레이션 최신(0018) 유지. 신규 테이블·컬럼·마이그레이션을 추가하지 않는다.

---

## 6. 의존성

- **SPEC-017**: `get_portfolio_with_holdings`·비중 산정 로직.
- **SPEC-027**: `portfolio/risk_analysis.py` FDR 조회·numpy 계산·scipy 금지 패턴, 오케스트레이션 구조.
- **SPEC-028**: `PortfolioHolding.market`·`currency` 필드, `fx_rate.py` 환율 서비스, 해외 가격 캐시.
- **SPEC-012**(참조·비충돌): 기존 `backtest/metrics.py` 순수 함수 재사용. 기존 `backtest/` 도메인은 수정하지 않음.

---

## 7. MX 태그 계획

코드 주석 언어는 한국어(`language.yaml` `code_comments: ko`).

- **@MX:ANCHOR** (`portfolio/backtest.py`의 `run_portfolio_backtest` 오케스트레이션 진입점):
  - 사유: router.py + 단위 테스트 + (잠재적) 통합 테스트에서 fan_in ≥ 3 예상. `@MX:REASON` 필수.
- **@MX:NOTE** (`portfolio/backtest.py` 모듈 상단):
  - scipy 금지·numpy 전용 원칙 명시(risk_analysis.py 패턴 일관성).
  - 무위험수익률 0.035(한국 기준) 기본값 근거.
- **@MX:WARN** (FDR 동기 조회 헬퍼):
  - 사유: 동기 블로킹 호출 — `run_in_executor`에서만 호출. `@MX:REASON` 필수(이벤트 루프 블로킹 방지).
- **@MX:TODO** (RED 단계):
  - 미구현 순수 함수·오케스트레이션에 테스트 작성 전 임시 마커. GREEN 단계에서 제거.
- **@MX:ANCHOR** (`frontend/src/api/portfolio.ts` `apiRunPortfolioBacktest`):
  - 사유: BacktestPanel·테스트에서 참조하는 공개 API 계약. `@MX:REASON` 필수.

태그 설명은 한국어로 작성하고, 에이전트 생성 태그는 `[AUTO]` 접두사를 포함한다.
