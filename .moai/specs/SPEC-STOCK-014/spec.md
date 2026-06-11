---
id: SPEC-STOCK-014
version: 0.1.0
status: draft
created: 2026-06-11
updated: 2026-06-11
author: ircp
priority: medium
issue_number: null
---

# SPEC-STOCK-014 — AI 투자 조언 고도화 (Phase 15)

## HISTORY

- 2026-06-11 (v0.1.0): 최초 작성. 기존 일회성 AI 기능(포트폴리오 AI 분석·추천 근거)을
  영속·맥락형 투자 조언으로 확장. 리밸런싱 제안·리스크 프로파일·시장 브리핑·조언 이력·품질 피드백.

---

## 1. 개요 (Overview)

### 1.1 문제 정의

현재 ai-stock-picker는 두 가지 AI 기능을 제공하지만 모두 **일회성(one-shot)**이며 사용자 맥락이 얕다.

- `POST /portfolios/{id}/ai-analysis` (SPEC-STOCK-003): 보유 종목 구성을 Claude에 보내
  `{diversification, risk, suggestions}` 텍스트를 받지만 **결과를 저장하지 않아** 사용자가 과거 조언을
  되돌아볼 수 없다. 매 요청마다 Claude를 호출해 비용·레이트리밋 부담이 있다.
- 추천 근거(`explanation`, SPEC-STOCK-006): 종목별 2~3문장 근거를 생성하지만 개별 종목 단위이며,
  사용자 포트폴리오 전체에 대한 실행 가능한 조언(무엇을 더 사고/줄이고/유지할지)은 없다.

즉, "분석"은 있으나 **"조언"과 "이력"과 "개선 루프"**가 없다.

### 1.2 본 SPEC이 추가하는 것

1. **포트폴리오 리밸런싱 제안** — 보유 종목(`WatchlistItem`/`PortfolioHolding`)과 최신 추천
   유니버스(`Recommendation`)를 종합해 Claude가 종목별 구체 액션(`buy_more`/`reduce`/`hold`)과 근거를 제시.
2. **리스크 프로파일 분석** — 섹터 집중도·단일 종목 노출도를 계산해 리스크 점수(0~100) + 한국어 설명 생성.
3. **맞춤형 시장 브리핑** — 일일 아침 브리핑: 시장 상황 + 그것이 사용자 보유 종목에 미치는 영향을 Claude가 서술.
4. **투자 조언 이력 저장** — 모든 AI 조언을 `ai_advice` 테이블에 영속화해 사용자가 과거 조언을 조회.
5. **조언 품질 피드백** — 사용자가 조언에 `helpful`/`not_helpful` 평가를 남기고, 향후 프롬프트 개선에 활용.

### 1.3 목표가 아닌 것 (요약)

자동 매매·실시간 데이터·신규 외부 데이터 소스 도입은 본 SPEC의 범위가 아니다. 상세는 §7 참조.

---

## 2. 기존 자산 재사용 (Existing Assets)

[HARD] 본 SPEC은 아래 자산을 **재정의하지 않고 재사용·확장**한다.

| 자산 | 위치 | 재사용 방식 |
|------|------|-------------|
| `WatchlistItem` 모델 | `db/models.py` (user_id, krx_code) | 리밸런싱·리스크 대상 종목 집합 조회 |
| `PortfolioHolding` 모델 | `db/models.py` (krx_code, quantity, avg_buy_price) | 보유 비중·평가액 산출 |
| `Recommendation` 모델 | `db/models.py` (trade_date, krx_code, rank, total_score, explanation) | 리밸런싱 시 최신 추천 유니버스 참조 |
| `AnalysisResult` 모델 | `db/models.py` (sector_tags, sentiment_score, sentiment_label) | 리스크 섹터 분류·시장 브리핑 감성 근거 |
| `analyze_portfolio()` | `portfolio/ai_analysis.py` | Claude 호출·면책·예외 격리 패턴을 신규 조언 생성에 재사용 |
| 추천 근거 생성 패턴 | `recommendation/explanation.py` | 실패 시 `None`·예외 비전파 패턴을 신규 Claude 호출에 적용 |
| Claude 클라이언트 | `anthropic.Anthropic` + `claude-haiku-4-5` | 동일 모델·동일 호출 패턴 유지 |
| 인증 의존성 | `auth/dependencies.py` `get_current_user`, `get_db_session` | 모든 신규 엔드포인트 보호 |
| Redis 캐시 의존성 | `api/deps.py` `get_redis_client`/`get_cache` | 시장 브리핑·리스크 결과 일일 캐시 |
| 섹터 분류 | `portfolio/ai_analysis.py` `_get_sector()` 또는 `AnalysisResult.sector_tags` | 리스크 섹터 집중도 계산에 활용 |

[HARD] 기존 `POST /portfolios/{id}/ai-analysis`는 **제거·변경하지 않는다**. 본 SPEC의 조언은 신규 엔드포인트로 추가한다.

---

## 3. 환경 및 가정 (Environment & Assumptions)

### 3.1 환경

- 백엔드: FastAPI + SQLAlchemy 2.0 (async 엔진 + auth용 동기 엔진), PostgreSQL, Redis
- AI: `anthropic.Anthropic` 동기 클라이언트, 모델 `claude-haiku-4-5`, env `ANTHROPIC_API_KEY`
- 프론트: React + TypeScript + Vite, 기존 `api/portfolio.ts`·`api/recommendations.ts` 확장
- 스케줄러: APScheduler (`scheduler/jobs.py`) — 일일 파이프라인 06:00, 장중 30분, 가격알림 5분
- 마이그레이션: 누적 0001~0014 존재 → 본 SPEC 신규 마이그레이션 = **0015** (down_revision=`0014`)

### 3.2 가정

- 가정 1: 사용자는 인증된 상태이며 `WatchlistItem` 또는 `PortfolioHolding` 데이터가 1건 이상 존재한다.
  보유 종목이 없으면 조언 생성 대신 안내 메시지를 반환한다 (기존 `analyze_portfolio` 패턴 동일).
- 가정 2: 최신 추천 유니버스(`Recommendation`, 최근 `trade_date`)가 DB에 존재한다. 없으면 리밸런싱은
  "추천 데이터 준비 중" 메시지를 반환한다 (Claude 미호출).
- 가정 3: Claude 호출은 비용·레이트리밋을 고려해 **캐시·1일 1회 생성**을 원칙으로 한다.
  시장 브리핑은 사용자당 1일 1회만 생성·재사용한다.
- 가정 4: Claude 응답 실패는 파이프라인·요청을 중단시키지 않고 오류 딕셔너리/None으로 격리한다.
- 가정 5: 모든 조언에는 "투자 권유 아님" 면책 문구를 포함한다 (`_DISCLAIMER` 패턴 재사용).

### 3.3 레이트리밋·캐싱 정책

- 시장 브리핑: 사용자당 1일 1회 생성. 캐시 키 `ai_advice:briefing:{user_id}:{date}` (TTL = 당일 자정까지 또는 86400s).
  동일 날짜 재요청은 `ai_advice` 테이블 또는 캐시에서 재조회 (Claude 미호출).
- 리밸런싱·리스크: 명시적 사용자 요청 시 생성하되, 동일 입력(보유 구성 해시 + 추천 trade_date) 기준 캐시.
  캐시 미스 시에만 Claude 호출. 캐시 TTL 1800s.
- [HARD] 단일 사용자가 분당 무제한 호출(spam)하지 못하도록, 캐시 적중을 우선하고 미스 시에만 생성한다.

---

## 4. 데이터 모델 (Data Model)

### 4.1 `ai_advice` 테이블 (마이그레이션 0015, down_revision=`0014`)

조언 레코드와 피드백을 단일 테이블에 영속화한다.

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| `id` | Integer | PK, autoincrement | 기본 키 |
| `user_id` | Integer | FK→users.id (ON DELETE CASCADE), NOT NULL | 조언 수신 사용자 |
| `advice_type` | String(20) | NOT NULL | `rebalance` \| `risk_profile` \| `market_briefing` |
| `ref_date` | Date | NOT NULL | 조언 기준일 (당일 날짜, 중복 방지·이력 정렬용) |
| `title` | String(200) | NOT NULL | 조언 요약 제목 (한국어) |
| `body` | Text | NULL | 조언 본문 (서술형 한국어) |
| `payload` | JSON / Text | NULL | 구조화 데이터 (리밸런싱 액션 목록·리스크 점수 등 JSON 직렬화) |
| `risk_score` | Integer | NULL | 리스크 프로파일 점수 0~100 (`risk_profile` 타입만 사용) |
| `feedback` | String(20) | NULL | `helpful` \| `not_helpful` \| NULL (미평가) |
| `feedback_at` | TIMESTAMPTZ | NULL | 피드백 시각 |
| `created_at` | TIMESTAMPTZ | server_default=now(), NOT NULL | 생성 시각 |

제약·인덱스:

- `UniqueConstraint(user_id, advice_type, ref_date)` 이름 `uq_ai_advice_user_type_date`
  — 동일 사용자·타입·기준일 조언은 1회만 생성 (캐싱·멱등성 보장).
- `Index(user_id, advice_type, created_at)` — 사용자별 타입별 최신 이력 조회 최적화.

[HARD] `ai_advice`는 본 SPEC의 **유일한 신규 테이블**이다. 기존 테이블 컬럼은 추가·변경하지 않는다.

---

## 5. EARS 요구사항 (Requirements)

### 5.1 조언 공통·이력 (REQ-AIV-*)

- REQ-AIV-001 (Ubiquitous): The system shall persist every generated AI advice as a row in the
  `ai_advice` table with `user_id`, `advice_type`, `ref_date`, `title`, and `created_at`.
- REQ-AIV-002 (Ubiquitous): The system shall include a non-investment-solicitation disclaimer
  ("본 분석은 투자 권유가 아닌 정보 제공 목적입니다.") in every advice body or response.
- REQ-AIV-003 (Event-Driven): When a user requests advice and a row with the same
  `(user_id, advice_type, ref_date)` already exists, the system shall return the persisted advice
  without calling the Claude API.
- REQ-AIV-004 (Event-Driven): When a user requests their advice history, the system shall return
  past `ai_advice` rows for that user ordered by `created_at` descending, scoped to the authenticated user.
- REQ-AIV-005 (Unwanted): If a Claude API call fails during advice generation, then the system shall
  return an error message dictionary and shall not propagate the exception or interrupt other requests.
- REQ-AIV-006 (State-Driven): While the authenticated user has no `WatchlistItem` and no
  `PortfolioHolding`, the system shall return an informational message instead of calling the Claude API.
- REQ-AIV-007 (Unwanted): If a user requests advice for another user's data, then the system shall
  respond with HTTP 403 or 404 and shall not disclose the other user's advice.

### 5.2 포트폴리오 리밸런싱 제안 (REQ-RB-*)

- REQ-RB-001 (Event-Driven): When a user requests rebalancing advice, the system shall collect the
  user's holdings (`PortfolioHolding`/`WatchlistItem`) and the latest `Recommendation` universe
  (most recent `trade_date`) as Claude input.
- REQ-RB-002 (Event-Driven): When generating rebalancing advice, the system shall produce a list of
  per-holding actions where each action has a `krx_code`, an `action` of `buy_more`/`reduce`/`hold`,
  and a Korean `reason`.
- REQ-RB-003 (State-Driven): While no `Recommendation` rows exist for any recent `trade_date`, the
  system shall return a "추천 데이터 준비 중" message and shall not call the Claude API.
- REQ-RB-004 (Unwanted): If the Claude rebalancing response is not valid JSON, then the system shall
  attempt to extract the JSON block, and on failure shall return an error message dictionary.
- REQ-RB-005 (Ubiquitous): The system shall store rebalancing actions in the `ai_advice.payload`
  field as serialized JSON.

### 5.3 리스크 프로파일 분석 (REQ-RM-*)

- REQ-RM-001 (Event-Driven): When a user requests a risk profile, the system shall compute sector
  concentration and single-stock exposure from the user's holdings using `AnalysisResult.sector_tags`
  or the existing sector classification helper.
- REQ-RM-002 (Event-Driven): When computing a risk profile, the system shall produce a `risk_score`
  integer in the range 0 to 100 where higher means higher concentration risk.
- REQ-RM-003 (Event-Driven): When a risk profile is generated, the system shall produce a Korean
  explanation describing the dominant concentration factors and store it in `ai_advice.body`.
- REQ-RM-004 (State-Driven): While a single holding represents more than 50 percent of total invested
  value, the system shall flag single-stock concentration in the risk explanation.
- REQ-RM-005 (Ubiquitous): The system shall store the computed `risk_score` in the
  `ai_advice.risk_score` column for `risk_profile` advice rows.

### 5.4 맞춤형 시장 브리핑 (REQ-MB-*)

- REQ-MB-001 (Event-Driven): When a user requests the daily market briefing, the system shall generate
  a Korean briefing combining overall market conditions and their impact on the user's specific holdings.
- REQ-MB-002 (State-Driven): While a briefing for the current date already exists for the user, the
  system shall return the cached or persisted briefing without calling the Claude API.
- REQ-MB-003 (Ubiquitous): The system shall cache the daily briefing under key
  `ai_advice:briefing:{user_id}:{date}` and limit briefing generation to once per user per day.
- REQ-MB-004 (Event-Driven): When building briefing input, the system shall use recent
  `AnalysisResult.sentiment_score`/`sentiment_label` and `Recommendation` data as market context.
- REQ-MB-005 (Unwanted): If the market briefing generation fails, then the system shall return an
  informational fallback message and shall not interrupt the user's session.

### 5.5 조언 품질 피드백 (REQ-FB-*)

- REQ-FB-001 (Event-Driven): When a user submits feedback (`helpful` or `not_helpful`) for an advice
  row, the system shall update the `feedback` and `feedback_at` columns of that `ai_advice` row.
- REQ-FB-002 (Unwanted): If a user submits feedback for an advice row they do not own, then the system
  shall respond with HTTP 403 or 404 and shall not modify the row.
- REQ-FB-003 (Unwanted): If feedback value is not `helpful` or `not_helpful`, then the system shall
  respond with HTTP 422 and shall not modify the row.
- REQ-FB-004 (Optional): Where feedback data exists, the system shall expose an aggregate count of
  helpful/not_helpful per `advice_type` for future prompt refinement.

### 5.6 프론트엔드 (REQ-FE-*)

- REQ-FE-001 (Event-Driven): When a user opens the portfolio page, the frontend shall provide controls
  to request rebalancing advice, risk profile, and market briefing.
- REQ-FE-002 (Event-Driven): When rebalancing advice is returned, the frontend shall render each action
  with its `krx_code`, action label (`buy_more`/`reduce`/`hold`), and Korean reason.
- REQ-FE-003 (Event-Driven): When a risk profile is returned, the frontend shall render the `risk_score`
  as a visual indicator (0 to 100) alongside the Korean explanation.
- REQ-FE-004 (Ubiquitous): The frontend shall display an advice history view showing past advice with
  type, date, and a helpful/not-helpful feedback control.
- REQ-FE-005 (Event-Driven): When a user clicks a feedback control, the frontend shall submit feedback
  and reflect the updated state without a full page reload.

### 5.7 비기능 (REQ-NFR-*)

- REQ-NFR-001 (Ubiquitous): The system shall keep advice generation Claude calls on `claude-haiku-4-5`
  consistent with existing AI features.
- REQ-NFR-002 (Ubiquitous): The system shall reuse the existing `get_current_user` dependency to
  protect every new advice endpoint.
- REQ-NFR-003 (Ubiquitous): The system shall not include user identifiers (user_id) in any payload
  sent to the Claude API.
- REQ-NFR-004 (Ubiquitous): The system shall achieve backend test coverage of at least 85 percent for
  new advice modules.

---

## 6. API 계약 (API Contract)

[HARD] 모든 엔드포인트는 `get_current_user`로 보호되며 타사용자 데이터 접근 시 403/404를 반환한다.
신규 라우터 prefix는 기존 `/notifications` 충돌 사례를 고려해 **`/advice`**로 분리한다.

| 메서드 | 경로 | 설명 | 주요 요구사항 |
|--------|------|------|----------------|
| `POST` | `/advice/rebalance` | 리밸런싱 제안 생성·조회 (캐시 우선) | REQ-RB-001~005 |
| `POST` | `/advice/risk-profile` | 리스크 프로파일 생성·조회 | REQ-RM-001~005 |
| `GET` | `/advice/market-briefing` | 당일 시장 브리핑 조회 (1일 1회 생성) | REQ-MB-001~005 |
| `GET` | `/advice/history` | 조언 이력 조회 (타입 필터·limit≤100) | REQ-AIV-004 |
| `POST` | `/advice/{advice_id}/feedback` | 조언 품질 피드백 등록 | REQ-FB-001~003 |
| `GET` | `/advice/feedback-summary` | 타입별 helpful/not_helpful 집계 (선택) | REQ-FB-004 |

### 6.1 응답 형식 예시 (참고)

```
POST /advice/rebalance
{
  "advice_id": 12,
  "ref_date": "2026-06-11",
  "actions": [
    {"krx_code": "005930", "action": "hold", "reason": "..."},
    {"krx_code": "000660", "action": "reduce", "reason": "..."}
  ],
  "disclaimer": "본 분석은 투자 권유가 아닌 정보 제공 목적입니다."
}
```

```
POST /advice/risk-profile
{
  "advice_id": 13,
  "ref_date": "2026-06-11",
  "risk_score": 72,
  "explanation": "...",
  "disclaimer": "..."
}
```

[HARD] 응답 스키마의 정확한 필드명·Pydantic 모델 구조는 Run 단계에서 확정한다 (본 SPEC은 관찰 가능한 동작만 정의).

---

## 7. 제외 사항 (Exclusions — What NOT to Build)

[HARD] 아래 항목은 본 SPEC 범위에서 명시적으로 제외한다.

1. **자동 매매·주문 실행** — 프로젝트 영구 제외 (규제·책임 리스크). 조언은 정보 제공만 한다.
2. **실시간 데이터** — 폴링/배치만 사용. 실시간 시세 스트리밍 기반 조언 없음.
3. **신규 외부 데이터 소스 도입** — 기존 `WatchlistItem`/`Recommendation`/`AnalysisResult`/
   `PortfolioHolding`만 활용. 새 시장 데이터 공급자·뉴스 소스 추가 없음.
4. **기존 `POST /portfolios/{id}/ai-analysis` 변경·제거** — 그대로 유지하며 신규 엔드포인트만 추가.
5. **ML 기반 개인화·추천 재가중** — 피드백은 수집·집계만 하며, 본 SPEC에서 점수 모델이나 프롬프트를
   자동 학습·재가중하지 않는다 (수동 프롬프트 개선 참고용).
6. **신규 알림 채널** — 조언을 텔레그램/이메일/웹푸시로 발송하지 않는다 (조회 기반).
7. **시장 브리핑 자동 스케줄 푸시** — 사용자 요청 시 생성·캐시. 전용 스케줄러 잡으로 일괄 발송하지 않는다.
8. **다국어 조언** — 한국어 조언만 생성한다.
9. **조언 보존 기간·아카이빙 정책** — 이력 무한 보존. 만료·삭제 정책은 별도 SPEC.

---

## 8. 관련 SPEC

- SPEC-STOCK-003 (Phase 4): 포트폴리오 AI 분석 — 본 SPEC이 패턴 재사용·확장.
- SPEC-STOCK-006 (Phase 7): 추천 근거(`explanation`) — Claude 호출·예외 격리 패턴 재사용.
- SPEC-STOCK-013 (Phase 14): 알림 인박스 — `ai_advice` 멱등 UNIQUE 제약 설계 패턴 참조.
