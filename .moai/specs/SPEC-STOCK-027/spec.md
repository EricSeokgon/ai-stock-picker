---
id: SPEC-STOCK-027
version: 0.1.0
status: draft
created: 2026-06-17
updated: 2026-06-17
author: ircp
priority: High
issue_number: null
---

# SPEC-STOCK-027 — 리스크 분석 및 상관관계 매트릭스 (Risk Analysis and Correlation Matrix)

> Roadmap Phase 3 "포트폴리오 AI 최적화"의 두 번째 SPEC.
> SPEC-STOCK-026이 명시적으로 연기한 "리스크 상관관계 매트릭스"를 구현한다.

## HISTORY

- 2026-06-17 (v0.1.0): 최초 작성. M1~M5 정의. `GET /portfolios/{portfolio_id}/risk-analysis` 신규 엔드포인트 + 종목 쌍 상관관계 매트릭스 + 종목별 연환산 변동성 + 포트폴리오 변동성 + 분산투자 효익(diversification benefit) + Redis 캐싱 + 프론트 상관관계 히트맵·변동성 테이블(`RiskAnalysisPanel`).

---

## 배경 및 동기

SPEC-STOCK-026(포트폴리오 AI 최적화)은 점수·목표비중·리밸런싱 액션을 제공하지만, 다음을 **제외(Out of Scope)**로 명시하고 본 SPEC으로 연기했다.

> SPEC-STOCK-026/spec.md §제외: "리스크 상관관계 매트릭스 — 별도 SPEC-STOCK-027 예정."

현재 포트폴리오 도메인은 다음 통계적 리스크 지표가 전무하다.

1. **상관관계 부재**: 보유 종목 간 가격 동조성(상관계수)을 보여주지 못한다. 사용자는 자신의 포트폴리오가 실제로 분산되어 있는지(서로 다르게 움직이는지) 판단할 수 없다.
2. **변동성 부재**: 종목별 연환산 변동성(annualized volatility)이 없어, 어떤 종목이 위험한지 정량적으로 알 수 없다.
3. **포트폴리오 위험도 부재**: 비중·공분산을 반영한 포트폴리오 전체 변동성과, 분산투자로 줄어든 위험(분산투자 효익)을 제시하지 못한다.
4. **시각화 부재**: 상관관계를 한눈에 보는 히트맵이 없다.

본 SPEC은 과거 가격 데이터(FinanceDataReader) 기반으로 **상관관계 매트릭스 → 종목별 변동성 → 포트폴리오 변동성 → 분산투자 효익**까지 통계적 리스크 프로필을 계산·시각화한다.

> ⚠️ **영구 제외 원칙 준수**: 본 SPEC은 자동 매매/주문 실행을 포함하지 않는다. 모든 산출물은 통계적 정보 제공이며, 미래 수익률 예측이 아니다. 변동성·상관관계는 과거 데이터 기반임을 명시한다.

---

## 범위 (Scope)

### 포함 (In Scope)

| 마일스톤 | 내용 |
|---------|------|
| **M1** | numpy 의존성 추가 + 리스크 분석 서비스(`risk_analysis.py`) — 상관관계 매트릭스 + 종목별 연환산 변동성 + 포트폴리오 변동성 + 분산투자 효익 계산 |
| **M2** | 스키마(`HoldingVolatility`·`RiskAnalysisResult`) + 라우터 엔드포인트 `GET /portfolios/{portfolio_id}/risk-analysis?period={int}&refresh={bool}` |
| **M3** | Redis 캐싱 — 키 `portfolio_risk:{portfolio_id}:{period}:{date}`, TTL 3600s, `?refresh=true` 강제 갱신 |
| **M4** | 프론트엔드 `RiskAnalysisPanel`(상관관계 히트맵 + 변동성 테이블 + 포트폴리오 요약 + 기간 선택기) + `Portfolio.tsx` 연동 + `api/portfolio.ts` 함수 |
| **M5** | 테스트 — 백엔드 단위 8개 + 통합 3개 + 프론트 컴포넌트 테스트 |

### 제외 (Out of Scope)

> [HARD] 본 SPEC은 다음을 **빌드하지 않는다**.

- **scipy/MPT 수학적 최적화** (Modern Portfolio Theory, 효율적 프론티어) — SPEC-026과 동일하게 제외. 본 SPEC은 numpy 통계 계산만 사용한다(scipy 미추가).
- **Monte Carlo 시뮬레이션**.
- **VaR (Value at Risk) / CVaR 계산**.
- **Sharpe / Sortino / Beta 등 위험조정수익 지표** — 변동성·상관관계만 제공.
- **미래 수익률·가격 예측**.
- **세금·거래비용 모델링**.
- **해외 자산 지원** — 별도 SPEC-STOCK-028 예정(SPEC-026과 동일).
- **상관관계·변동성 시계열 추이**(rolling correlation 등) — 단일 기간 스냅샷만 제공.
- **위험 한도 알림·경고**(특정 상관관계·변동성 초과 시 알림) — 알림 시스템 연동 제외.
- **포트폴리오 최적화 권고와의 통합**(SPEC-026 optimize 엔드포인트 수정) — 본 SPEC은 별도 엔드포인트만 추가, optimize 불변.
- **자동 매매/주문 실행** — 프로젝트 영구 제외 원칙.
- **신규 DB 테이블·마이그레이션** — 본 SPEC은 신규 테이블이 필요 없다. 리스크 분석 결과는 영속 저장하지 않고(one-shot + Redis 캐시) 매 요청 시 계산·캐시한다.

---

## 요구사항 (EARS Requirements)

### REQ-RISK-* (리스크 분석 핵심)

- **REQ-RISK-001**: WHEN 사용자가 `GET /portfolios/{portfolio_id}/risk-analysis`를 호출하면 THEN the system SHALL `correlation_matrix`·`holdings_volatility`·`portfolio_volatility_pct`·`diversification_benefit_pct`·`period_days`·`calculated_at`를 포함한 결과를 반환한다.
- **REQ-RISK-002**: WHEN 상관관계 매트릭스가 산출되면 THEN the system SHALL 보유 종목 쌍별 피어슨 상관계수를 -1.0~1.0 범위로 산출하고 AND 대각 원소(자기 자신과의 상관)는 1.0으로 설정한다.
- **REQ-RISK-003**: WHEN 종목별 변동성이 산출되면 THEN the system SHALL 일간 수익률 표준편차에 √252를 곱한 연환산 변동성(%)을 산출한다.
- **REQ-RISK-004**: WHEN 포트폴리오 변동성이 산출되면 THEN the system SHALL 보유 비중(weights)과 공분산 행렬을 사용하여 `sqrt(wᵀ · Σ · w) × √252`를 연환산 변동성(%)으로 산출한다.
- **REQ-RISK-005**: WHEN 분산투자 효익이 산출되면 THEN the system SHALL `diversification_benefit_pct = (1 - 포트폴리오변동성 / 비중가중평균변동성) × 100`을 산출하고 AND 결과가 음수이면 0으로 클램프한다.
- **REQ-RISK-006**: WHEN 상관관계 매트릭스가 직렬화되면 THEN the system SHALL `dict[str, dict[str, float]]`(외부 키·내부 키 모두 krx_code) 형태로 반환한다.

### REQ-RISK-PERIOD-* (기간 파라미터)

- **REQ-RISK-PERIOD-001**: WHERE `period` 쿼리 파라미터가 제공되지 않으면 THEN the system SHALL 기본값 90(일)을 사용한다.
- **REQ-RISK-PERIOD-002**: WHEN `period`가 {30, 60, 90, 180, 252} 이외의 값이면 THEN the system SHALL HTTP 422를 반환한다.
- **REQ-RISK-PERIOD-003**: WHEN 과거 가격을 조회할 때 THEN the system SHALL `period`일 이내의 데이터를 사용하여 상관관계·변동성을 계산한다.

### REQ-RISK-DATA-* (입력 데이터·예외)

- **REQ-RISK-DATA-001**: WHEN 리스크 분석 서비스가 과거 가격을 수집할 때 THEN the system SHALL 보유 종목별 krx_code로 FinanceDataReader를 호출하여 종가 시계열을 수집한다.
- **REQ-RISK-DATA-002**: IF FinanceDataReader 호출이 특정 종목에서 실패하거나 빈 데이터를 반환하면 THEN the system SHALL 예외를 전파하지 않고 해당 종목을 분석에서 제외하고 AND 나머지 종목으로 계속 진행한다.
- **REQ-RISK-DATA-003**: WHEN 종목별 변동성 항목이 반환되면 THEN the system SHALL 사용된 가격 데이터 일수(`price_data_days`)를 함께 반환한다.

### REQ-RISK-CONSTRAINT-* (제약·경계 조건)

- **REQ-RISK-CONSTRAINT-001**: IF 유효한(가격 데이터가 확보된) 보유 종목이 2개 미만이면 THEN the system SHALL HTTP 400과 "최소 2개 종목 필요" 안내를 반환하고 AND Claude·계산을 수행하지 않는다.
- **REQ-RISK-CONSTRAINT-002**: WHERE 두 종목의 공통 거래일이 상관계수 계산에 부족하면 THEN the system SHALL 해당 쌍의 상관계수를 0.0(중립)으로 설정한다(추측 단언 금지).

### REQ-RISK-AUTH-* (인증·소유권)

- **REQ-RISK-AUTH-001**: WHEN 인증되지 않은 요청이 들어오면 THEN the system SHALL HTTP 401을 반환한다.
- **REQ-RISK-AUTH-002**: IF 포트폴리오가 존재하지 않으면 THEN the system SHALL HTTP 404를 반환한다.
- **REQ-RISK-AUTH-003**: IF 포트폴리오 소유자가 요청 사용자가 아니면 THEN the system SHALL HTTP 403(또는 코드베이스 관례상 404)을 반환한다.

### REQ-RISK-CACHE-* (캐싱)

- **REQ-RISK-CACHE-001**: WHEN risk-analysis가 호출되고 AND 캐시가 존재하고 AND `?refresh=false`(기본값)이면 THEN the system SHALL FinanceDataReader·계산 없이 캐시된 결과를 반환한다.
- **REQ-RISK-CACHE-002**: WHEN `?refresh=true`이면 THEN the system SHALL 캐시를 무시하고 재계산하여 캐시를 갱신한다.
- **REQ-RISK-CACHE-003**: WHERE 캐시 키를 구성할 때 THEN the system SHALL `portfolio_risk:{portfolio_id}:{period}:{date}` 형식과 TTL 3600s를 사용한다.
- **REQ-RISK-CACHE-004**: IF Redis가 가용하지 않으면 THEN the system SHALL 예외 없이 직접 계산하여 결과를 반환한다(graceful degradation).

### REQ-RISK-NFR-* (비기능)

- **REQ-RISK-NFR-001**: WHERE 통계 계산을 수행할 때 THEN the system SHALL numpy를 사용하고 AND scipy를 사용하지 않는다.
- **REQ-RISK-NFR-002**: WHERE FinanceDataReader 호출이 블로킹 I/O이면 THEN the system SHALL `run_in_executor`로 비동기 이벤트 루프를 블로킹하지 않도록 한다(기존 prices.py 패턴 재사용).
- **REQ-RISK-NFR-003**: WHEN 변동성·상관관계가 산출되면 THEN the system SHALL 결과가 과거 데이터 기반 통계 정보임을 응답·UI에 명시한다(미래 예측 아님).

### REQ-RISK-FE-* (프론트엔드)

- **REQ-RISK-FE-001**: WHEN 사용자가 Portfolio 페이지에서 `RiskAnalysisPanel`을 보면 THEN the system SHALL `apiGetRiskAnalysis()`로 결과를 조회하여 상관관계 히트맵·변동성 테이블·포트폴리오 요약을 렌더링한다.
- **REQ-RISK-FE-002**: WHEN 상관관계 히트맵이 표시되면 THEN the system SHALL 색상 그라데이션(상관 높음=적색, 0=흰색, 음의 상관=청색)으로 셀을 표현한다.
- **REQ-RISK-FE-003**: WHEN 사용자가 기간 선택기(30/60/90/180/252일)를 변경하면 THEN the system SHALL 선택된 기간으로 risk-analysis를 재조회하여 패널을 갱신한다.
- **REQ-RISK-FE-004**: WHEN 변동성 테이블이 표시되면 THEN the system SHALL 종목별 이름·연환산 변동성(%)을 표시하고 AND 포트폴리오 변동성·분산투자 효익 요약을 표시한다.

---

## 기술 접근 방식 (Technical Approach)

### 백엔드 (M1·M2·M3)

1. **numpy 의존성 추가 (M1)**
   - `backend/pyproject.toml`의 `dependencies`에 `numpy>=1.26` 추가. (numpy는 FinanceDataReader를 통해 전이 설치되나, 직접 사용하므로 직접 의존성으로 명시한다.)
   - **scipy는 추가하지 않는다**(REQ-RISK-NFR-001). 상관·공분산·표준편차 모두 numpy로 충분하다.

2. **리스크 분석 서비스 (M1)** — `portfolio/risk_analysis.py` 신규(ai_analysis.py·service.py 형제):
   - `calculate_risk_analysis(portfolio_id, user_id, db, redis, period=90, refresh=False) -> RiskAnalysisResult`.
   - 보유 종목을 `get_portfolio_with_holdings`(기존)로 조회·소유권 검증.
   - 종목별 krx_code로 FinanceDataReader 종가 시계열 수집(`run_in_executor`, prices.py 패턴 재사용). 실패 종목은 제외(REQ-RISK-DATA-002).
   - 일간 수익률(pct_change) 계산 → numpy로:
     - 상관관계 매트릭스: `np.corrcoef`(또는 pandas `.corr()`), 대각 1.0.
     - 종목별 연환산 변동성: `std(daily_returns) × sqrt(252) × 100`.
     - 공분산 행렬: `np.cov`. 포트폴리오 변동성: `sqrt(wᵀ Σ w) × sqrt(252) × 100`.
     - 분산투자 효익: `(1 - port_vol / weighted_avg_vol) × 100`, 음수 클램프 0.
   - 유효 종목 < 2개면 400(REQ-RISK-CONSTRAINT-001).

3. **스키마 (M2)** — `portfolio/schemas.py`에 추가:
   - `HoldingVolatility`: `krx_code`(str), `name`(str), `annualized_volatility_pct`(float), `price_data_days`(int).
   - `RiskAnalysisResult`: `correlation_matrix`(dict[str, dict[str, float]]), `holdings_volatility`(list[HoldingVolatility]), `portfolio_volatility_pct`(float), `diversification_benefit_pct`(float), `period_days`(int), `calculated_at`(str/datetime).

4. **라우터 (M2)** — `portfolio/router.py`에 추가:
   - `GET /portfolios/{portfolio_id}/risk-analysis?period={int}&refresh={bool}` (async, 인증·소유권). `period` 검증(REQ-RISK-PERIOD-002).

5. **Redis 캐싱 (M3)**
   - 캐시 키: `portfolio_risk:{portfolio_id}:{period}:{date}`(date = 오늘, KST 기준).
   - TTL 3600s. `?refresh=true` 시 무시·재계산·재적재.
   - `get_redis_client`/`get_cache`(api/deps.py, redis.asyncio) 패턴 재사용. graceful degradation(REQ-RISK-CACHE-004).

### 프론트엔드 (M4)

- `frontend/src/api/portfolio.ts`: `apiGetRiskAnalysis(portfolioId, period?)` 함수 + 타입 추가.
- `frontend/src/components/RiskAnalysisPanel.tsx` 신규:
  - 상관관계 히트맵(색상 그라데이션: 적색 ↔ 흰색 ↔ 청색).
  - 변동성 테이블(종목명 · 연환산 변동성%).
  - 포트폴리오 변동성 · 분산투자 효익 요약.
  - 기간 선택기(30/60/90/180/252일).
- `frontend/src/pages/Portfolio.tsx`: `PortfolioScoreCard` 아래에 `RiskAnalysisPanel` 렌더(기존 섹션 보존).

### 테스트 (M5)

- `backend/tests/unit/test_portfolio_risk.py` 신규(8개 이상).
- `backend/tests/integration/test_portfolio_router.py`에 통합 3개 추가.
- 프론트: `RiskAnalysisPanel` 컴포넌트 테스트(렌더, 기간 선택기).

---

## 의존성 (Dependencies)

- **SPEC-STOCK-026** (포트폴리오 AI 최적화) — `Portfolio.tsx`·`PortfolioScoreCard`·`api/portfolio.ts` 구조 재사용. RiskAnalysisPanel은 ScoreCard 아래에 추가.
- **SPEC-STOCK-017** (포트폴리오 성과 계산) — `get_portfolio_with_holdings`·보유 종목 비중 데이터 재사용.
- 기존 인프라 재사용: `mapping/prices.py`(FinanceDataReader + `run_in_executor` + Redis graceful 패턴), `api/deps.py`(Redis), `portfolio/service.py`.
- **신규 직접 의존성**: `numpy>=1.26`(`backend/pyproject.toml`).

---

## 마이그레이션 (Migration)

**불필요.** 본 SPEC은 신규 DB 테이블·컬럼을 추가하지 않는다. 리스크 분석 결과는 영속 저장하지 않고(one-shot + Redis 캐시) 매 요청 시 계산·캐시한다. 마이그레이션 최신 버전(0018, SPEC-STOCK-025)은 변경되지 않는다.
