---
id: SPEC-STOCK-026
version: 0.1.0
status: completed
created: 2026-06-17
updated: 2026-06-17
author: ircp
priority: High
issue_number: null
---

# SPEC-STOCK-026 — 포트폴리오 AI 최적화 (Portfolio AI Optimization)

> Roadmap Phase 3 "포트폴리오 AI 최적화"의 첫 번째 SPEC.
> 기존 서술형(descriptive) 포트폴리오 AI 분석을 처방형(prescriptive)으로 업그레이드한다.

## HISTORY

- 2026-06-17 (v0.1.0): 최초 작성. M1~M5 정의. AsyncAnthropic 전환 + `POST /portfolios/{portfolio_id}/optimize` 신규 엔드포인트 + 포트폴리오 점수(0-100)·목표비중·리밸런싱 액션·신규 추천 종목 + Redis 캐싱 + 프론트 AI 최적화 탭.

---

## 배경 및 동기

현재 포트폴리오 AI 분석(`backend/src/stock_picker/portfolio/ai_analysis.py`)은 다음 한계를 가진다.

1. **서술형에 머무름**: `diversification`·`risk`·`suggestions` 3개 필드만 반환하며, 각각 2~3문장의 정성적 설명일 뿐 사용자가 바로 실행할 수 있는 액션이 없다.
2. **점수 부재**: 포트폴리오의 종합 품질을 한눈에 보여주는 정량 지표(점수)가 없다.
3. **목표 비중·리밸런싱 액션 부재**: "이 종목을 몇 주 사고 팔아야 하는가"에 대한 구체적 처방이 없다.
4. **추천 엔진과 단절**: 일일 추천(`recommendations` 테이블)과 포트폴리오 최적화가 연결되어 있지 않아, 보유하지 않은 우량 추천 종목을 제안하지 못한다.
5. **동기 호출 결함**: `anthropic.Anthropic()`(동기 클라이언트)를 사용하여 FastAPI 이벤트 루프를 블로킹한다. 코드에 이미 `@MX:WARN`으로 플래그되어 있다.

본 SPEC은 위 한계를 해소하여, 사용자가 **점수 → 목표 비중 → 구체적 매수/매도 주수 → 신규 추천 종목**까지 확인할 수 있는 처방형 최적화 기능을 제공한다.

> ⚠️ **영구 제외 원칙 준수**: 본 SPEC은 자동 매매/주문 실행을 포함하지 않는다. 모든 산출물은 "권고"이며, 면책 문구(disclaimer)를 포함한다.

---

## 구현 노트 (Implementation Notes)

- **완료일**: 2026-06-17
- **개발 방법론**: TDD Brownfield Enhancement (RED→GREEN→REFACTOR)
- **테스트 결과**: 16/16 통과
- **주요 변경 사항**:
  - `anthropic.Anthropic()` 동기 클라이언트 → `AsyncAnthropic()` 비동기 전환 (FastAPI 이벤트 루프 블로킹 버그 수정)
  - `POST /portfolios/{id}/optimize` 엔드포인트 신규 구현
  - 프론트엔드 "AI 최적화 분석" 탭 추가 (3개 신규 컴포넌트)
- **비고**: `daily_recommendations` 테이블 없음 → `recommendations` 테이블 사용

---

## 범위 (Scope)

### 포함 (In Scope)

| 마일스톤 | 내용 |
|---------|------|
| **M1** | 포트폴리오 최적화 API — `POST /portfolios/{portfolio_id}/optimize` (AsyncAnthropic 전환 + optimize 함수 + schemas + service + router) |
| **M2** | Redis 캐싱 — 최적화 결과 캐시(TTL 3600s), `?refresh=true` 강제 갱신 |
| **M3** | 프론트엔드 최적화 결과 UI — PortfolioScoreCard / RebalancingTable / NewStockSuggestions 컴포넌트 + Portfolio.tsx "AI 최적화 분석" 탭 + api 함수 |
| **M4** | 기존 AI 분석 async 전환 — `POST /portfolios/{id}/ai-analysis`의 동기 `anthropic.Anthropic()` → `anthropic.AsyncAnthropic()` 버그 수정 |
| **M5** | 단위 테스트 — 7개 테스트 케이스 |

### 제외 (Out of Scope)

> [HARD] 본 SPEC은 다음을 **빌드하지 않는다**.

- **scipy/MPT 수학적 최적화** (Modern Portfolio Theory) — 복잡도 과도, 별도 검토.
- **Monte Carlo 시뮬레이션**.
- **VaR / Sharpe ratio 계산**.
- **세금·거래비용 모델링**.
- **해외 자산 지원** — 별도 SPEC-STOCK-028 예정.
- **리스크 상관관계 매트릭스** — 별도 SPEC-STOCK-027 예정.
- **포트폴리오 버전 히스토리** (최적화 결과 영속 저장·이력 관리).
- **실시간 스트리밍 최적화** (WebSocket 등).
- **자동 매매/주문 실행** — 프로젝트 영구 제외 원칙.
- **신규 DB 테이블·마이그레이션** — 본 SPEC은 신규 테이블이 필요 없다.

---

## 요구사항 (EARS Requirements)

### REQ-OPT-* (최적화 핵심)

- **REQ-OPT-001**: WHEN 사용자가 `POST /portfolios/{portfolio_id}/optimize`를 호출하면 THEN the system SHALL `score`(0-100)·`score_breakdown`·`target_weights`·`new_stocks`·`summary`를 포함한 결과를 10초 이내에 반환한다.
- **REQ-OPT-002**: WHERE 보유 종목의 `target_pct`가 `current_pct`를 2%p 초과하여 상회하면 THEN the system SHALL 해당 종목의 `action`을 `"buy"`로 설정한다.
- **REQ-OPT-003**: WHERE 보유 종목의 `target_pct`가 `current_pct`를 2%p 초과하여 하회하면 THEN the system SHALL 해당 종목의 `action`을 `"sell"`로 설정한다.
- **REQ-OPT-004**: WHEN optimize가 호출되고 AND 캐시가 존재하고 AND `?refresh=false`(기본값)이면 THEN the system SHALL Claude API 호출 없이 캐시된 결과를 반환한다.
- **REQ-OPT-005**: WHERE 포트폴리오 모듈이 Anthropic 클라이언트를 사용하면 THEN the system SHALL `anthropic.AsyncAnthropic`를 사용한다 (동기 `anthropic.Anthropic` 클래스를 절대 사용하지 않는다).
- **REQ-OPT-006**: WHEN `new_stocks`가 산출되면 THEN the system SHALL 이미 포트폴리오 보유 종목에 포함된 종목을 제외한다.
- **REQ-OPT-007**: WHEN `score_breakdown`이 산출되면 THEN the system SHALL `diversification`·`risk_balance`·`momentum`을 각각 0-100 범위로 산출하고 AND 세 값의 평균이 `score`와 같도록 한다.

### REQ-OPT-ACTION-* (액션·중립 영역)

- **REQ-OPT-ACTION-001**: WHERE 보유 종목의 `target_pct`와 `current_pct` 차이의 절댓값이 2%p 이하이면 THEN the system SHALL 해당 종목의 `action`을 `"hold"`로 설정한다.
- **REQ-OPT-ACTION-002**: WHEN `delta_shares`가 산출되면 THEN the system SHALL `action`이 `"buy"`이면 양의 정수, `"sell"`이면 음의 정수, `"hold"`이면 0을 반환한다.

### REQ-OPT-CONSTRAINT-* (제약 조건)

- **REQ-OPT-CONSTRAINT-001**: WHEN Claude에 최적화를 요청할 때 THEN the system SHALL 제약 조건(단일 종목 최대 30%, 단일 섹터 최대 40%)을 프롬프트에 포함한다.
- **REQ-OPT-CONSTRAINT-002**: WHEN `new_stocks`가 산출되면 THEN the system SHALL 추천 유니버스(`recommendations` 테이블) 상위 종목 중 미보유 종목을 최대 5개까지 반환한다.

### REQ-OPT-DATA-* (입력 데이터)

- **REQ-OPT-DATA-001**: WHEN optimize 서비스가 Claude 입력을 구성할 때 THEN the system SHALL 보유 종목별 `sector`·`weight_pct`·`current_price`·최신 추천 점수(`recommendations` 조인)를 포함한다.
- **REQ-OPT-DATA-002**: WHERE 포트폴리오에 보유 종목이 없으면 THEN the system SHALL Claude를 호출하지 않고 빈 결과 또는 안내 메시지를 반환한다.

### REQ-OPT-NFR-* (비기능)

- **REQ-OPT-NFR-001**: WHERE 모델을 선택할 때 THEN the system SHALL `claude-haiku-4-5`를 사용하고 AND `max_tokens`를 1024로 설정한다.
- **REQ-OPT-NFR-002**: IF Claude 응답 JSON 파싱이 실패하면 THEN the system SHALL 예외를 전파하지 않고 오류 마커가 포함된 안전한 응답을 반환한다.
- **REQ-OPT-NFR-003**: WHEN 캐시가 적중되면 THEN the system SHALL Claude API 호출 횟수가 0이 되도록 한다.

### REQ-OPT-FE-* (프론트엔드)

- **REQ-OPT-FE-001**: WHEN 사용자가 Portfolio 페이지의 "AI 최적화 분석" 탭을 열면 THEN the system SHALL `optimizePortfolio()`로 결과를 조회하여 점수·목표비중·신규추천을 렌더링한다.
- **REQ-OPT-FE-002**: WHEN 최적화 결과가 표시되면 THEN the system SHALL `PortfolioScoreCard`(원형 점수 + 분해 막대)·`RebalancingTable`(현재비중/목표비중/액션/주수)·`NewStockSuggestions`(최대 5개)를 표시한다.

---

## 기술 접근 방식 (Technical Approach)

### 백엔드 (M1·M2·M4)

1. **AsyncAnthropic 전환 (M1·M4)**
   - `ai_analysis.py`의 `import anthropic` 패턴은 유지하되, 클라이언트 생성을 `anthropic.AsyncAnthropic(api_key=...)`로 변경하고 호출부를 `await client.messages.create(...)`로 변환한다.
   - 기존 `analyze_portfolio()`(동기, `POST /ai-analysis` 백킹)도 async로 전환하여 `@MX:WARN` 결함을 해소한다 (M4).
   - 라우터의 `def ai_analysis(...)`는 `async def`로 변경한다.

2. **optimize 서비스 함수 (M1)**
   - `portfolio/service.py`에 `optimize_portfolio(portfolio_id, user_id, db, refresh=False)` 추가.
   - 보유 종목 + `sector` + `weight_pct` + `current_price`를 수집(기존 성과 계산 인프라 재사용, SPEC-STOCK-017).
   - 보유 종목별 최신 추천 점수를 `recommendations` 테이블(최신 `trade_date`)에서 조인 조회.
   - 미보유 추천 상위 종목 후보(최대 5개)를 `recommendations`에서 추출.
   - 제약 조건(단일 종목 30%, 단일 섹터 40%)을 Claude 프롬프트에 포함.
   - `claude-haiku-4-5`, `max_tokens=1024`, AsyncAnthropic로 호출. JSON 응답 파싱(엄격 모드 권장).
   - 응답 후 `action`/`delta_shares` 사후 검증·보정(2%p 임계 규칙 서버 측 재확인).

3. **스키마 (M1)** — `portfolio/schemas.py`에 추가:
   - `TargetWeightItem`: `krx_code`, `current_pct`, `target_pct`, `action`(`"buy"|"sell"|"hold"`), `delta_shares`(int).
   - `NewStockItem`: `krx_code`, `name`, `sector`, `reason`.
   - `ScoreBreakdown`: `diversification`, `risk_balance`, `momentum` (각 int 0-100).
   - `OptimizeResult`: `score`(int), `score_breakdown`, `target_weights`(list), `new_stocks`(list), `summary`(str).

4. **라우터 (M1)** — `portfolio/router.py`에 추가:
   - `POST /portfolios/{portfolio_id}/optimize?refresh={bool}` (인증·소유권 404). `async def`.

5. **Redis 캐싱 (M2)**
   - 캐시 키: `portfolio_optimize:{portfolio_id}:{date}` (date = 오늘, KST 기준).
   - TTL 3600s (1시간). `?refresh=true` 시 캐시 무시·재계산·재적재.
   - 기존 `get_redis_client`/`get_cache`(api/deps.py, redis.asyncio) 패턴 재사용. graceful degradation(Redis 미가용 시 직접 계산).

> **⚠️ 데이터 출처 정정**: 요청서의 "daily_recommendations" 테이블은 코드베이스에 존재하지 않는다. 실제 추천 진실 소스는 **`recommendations` 테이블**(`db/models.py`의 `Recommendation`, `total_score`·`trade_date` 보유)이다. 최적화는 이 테이블을 최신 `trade_date` 기준으로 조회한다.

### 프론트엔드 (M3)

- `frontend/src/api/portfolio.ts`: `optimizePortfolio(portfolioId, refresh?)` 함수 추가.
- `frontend/src/pages/Portfolio.tsx`: "AI 최적화 분석" 탭 추가(기존 요약·성과 보존).
- 신규 컴포넌트:
  - `PortfolioScoreCard.tsx`: 원형 점수(0-100) + 분해 막대(diversification/risk_balance/momentum).
  - `RebalancingTable.tsx`: krx_code · 현재비중% · 목표비중% · 액션(매수/매도/유지) · 주수.
  - `NewStockSuggestions.tsx`: 추가 추천 종목(최대 5개).

### 테스트 (M5)

`backend/tests/unit/test_portfolio_optimize.py` 신규 작성 (7개 케이스, acceptance.md 참조).

---

## 의존성 (Dependencies)

- **SPEC-STOCK-017** (포트폴리오 성과 계산) — `sector`·비중·현재가 데이터 제공. 재사용.
- **SPEC-STOCK-009** (추천 품질 개선) — `recommendations` 테이블의 추천 점수가 `new_stocks` 제안·보유 종목 점수 조인의 소스.
- 기존 인프라 재사용: `api/deps.py`(Redis), `portfolio/ai_analysis.py`(Claude 호출 패턴), `claude-haiku-4-5` 모델.

---

## 마이그레이션 (Migration)

**불필요.** 본 SPEC은 신규 DB 테이블·컬럼을 추가하지 않는다. 최적화 결과는 영속 저장하지 않고(one-shot + Redis 캐시) 매 요청 시 계산·캐시한다. 마이그레이션 최신 버전(0018, SPEC-STOCK-025)은 변경되지 않는다.
