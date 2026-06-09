---
id: SPEC-STOCK-006
version: 0.1.0
status: draft
created: 2026-06-10
updated: 2026-06-10
author: ircp
priority: high
issue_number: null
---

# SPEC-STOCK-006: 한국 주식 & ETF 추천 시스템 — Phase 7 (AI 분석 고도화 및 추천 근거 투명성)

## HISTORY

- 2026-06-10 (v0.1.0): 최초 작성. SPEC-STOCK-001(MVP)·002(개인화)·003(실시간)·004(알림)·005(성능·UX) 완료 위에 **AI 분석 고도화 및 추천 근거 투명성** 축을 추가한다. 3대 영역 — (A) Claude 기반 추천 근거 설명(Explainability), (B) 추천 히스토리 조회(History Tracking), (C) 뉴스 감성 상세화(Sentiment Detail) — 을 단일 SPEC으로 정의. 기존 규칙 기반 `Recommendation.reasoning`은 보존하고, Claude가 생성하는 한국어 자연어 설명을 **별도 컬럼 `explanation`**으로 추가한다. 자동 매매/주문 기능은 영구 제외를 유지한다.

---

## 1. 시스템 개요

### 1.1 목적

SPEC-STOCK-001~005로 추천·개인화·실시간·알림·성능 축을 완성한 위에, **사용자가 추천을 신뢰하고 과거 추천을 검증할 수 있도록(투명성) 시스템을 고도화한다.** Phase 7은 다음을 추가한다.

1. **추천 근거 설명(Recommendation Explainability)**: 추천 산출 시 각 종목에 대해 Claude가 한국어 2~3문장의 자연어 근거 텍스트를 생성하여 `recommendations.explanation` 컬럼에 저장하고, 추천 API 응답·프론트 종목 카드에 노출한다. 기존 규칙 기반 점수 분해 텍스트(`reasoning`)는 그대로 유지한다.
2. **추천 히스토리 조회(History Tracking)**: `GET /recommendations/history?days=N`으로 최근 N일치 추천 기록을 날짜별로 그룹화하여 반환하고, 프론트에 히스토리 페이지를 제공한다.
3. **뉴스 감성 상세화(Sentiment Detail)**: 현재 단순 라벨(`positive/negative/neutral`)과 점수에 더해, **한국어 5단계 감성 라벨**(매우긍정/긍정/중립/부정/매우부정)을 `analysis_results.sentiment_label` 컬럼에 저장하고 뉴스 API에 노출한다.

### 1.2 타겟 사용자

| 사용자 그룹 | 특성 | Phase 7에서 추가되는 핵심 니즈 |
|------------|------|------------------------------|
| 신규/일반 사용자 | 추천 점수만으로는 이유를 이해하기 어려움 | 종목별 자연어 근거로 "왜 추천되었는지" 즉시 이해 |
| 검증 지향 사용자 | 추천이 시간이 지나며 어떻게 변했는지 확인하고 싶음 | 과거 N일치 추천 히스토리를 날짜별로 조회 |
| 뉴스 탐색 사용자 | 단순 긍정/부정으로는 강도 구분이 안 됨 | 매우긍정~매우부정 5단계로 감성 강도 파악 |

### 1.3 핵심 가치 제안

- **설명 가능성**: 점수·기여 뉴스에 더해 사람이 읽는 자연어 근거를 제공하여 추천에 대한 신뢰를 높인다.
- **검증 가능성**: 과거 추천 기록을 보존·조회하여 사용자가 추천의 일관성을 스스로 검증한다.
- **표현력**: 감성을 5단계로 세분화하여 뉴스 강도를 직관적으로 전달한다.
- **하위 호환**: 기존 `reasoning`·`sentiment` 필드와 모든 SPEC-STOCK-001~005 동작을 보존하며 신규 컬럼·엔드포인트만 추가한다.
- **안전한 확장**: Claude 설명 생성이 실패해도 추천 파이프라인은 중단되지 않는다([HARD], REQ-EXPL-005). 자동 매매/주문은 영구 제외를 유지한다.

### 1.4 기존 시스템과의 관계 (SPEC-STOCK-001~005 재정의 금지)

다음은 이미 구현 완료된 자산이며 **본 SPEC에서 재정의하지 않고 재사용·확장**한다.

- 백엔드: FastAPI + PostgreSQL(SQLAlchemy 2.0 async) + Redis, Alembic 마이그레이션(최신 `0008`). 프론트: React 18 + TypeScript.
- 추천 모델: `db/models.py` `Recommendation`(trade_date, asset_type, krx_code, rank, total_score, sentiment_score, volume_score, momentum_score, anomaly_score, **reasoning**(규칙 기반, 보존), computed_at) — 본 SPEC은 여기에 **`explanation` 컬럼을 추가**한다.
- 분석 모델: `db/models.py` `AnalysisResult`(sentiment(`positive/negative/neutral`), sentiment_score(-1.0~1.0), sector_tags, keywords, summary) — 본 SPEC은 여기에 **`sentiment_label` 컬럼을 추가**한다.
- 추천 파이프라인: `recommendation/service.py`·`recommendation/aggregator.py`(종목별 `avg_sentiment`·`news_count`·`top_summary` 집계)·`scoring/reasoning.py` `generate_reasoning()`(규칙 기반 텍스트) — 본 SPEC은 이 파이프라인의 추천 적재 직전 단계에 Claude 설명 생성을 **추가**한다.
- Claude 클라이언트: `analysis/client.py` `ClaudeAnalysisClient`(`anthropic.AsyncAnthropic`, 모델 `claude-haiku-4-5`) — 설명 생성 시 동일 클라이언트/모델 패턴을 재사용한다.
- 추천 API: `api/routes/recommendations.py` `GET /recommendations`(캐시 기반, 필터/정렬)·`GET /recommendations/{krx_code}`(DB 기반 상세) — 본 SPEC은 `GET /recommendations/history`를 **추가**하고, 응답 스키마에 `explanation`을 **추가**한다.
- 뉴스 API: `api/routes/news.py` `GET /news`·스키마 `NewsItem`(title, summary, sentiment, source, url, published_at) — 본 SPEC은 `NewsItem`에 `sentiment_label`을 **추가**한다.
- 응답 스키마: `api/schemas.py` `RecommendationItem`·`RecommendationDetailResponse`·`NewsItem` — 신규 필드는 Optional로 추가하여 하위 호환을 보장한다.

---

## 2. 핵심 기능 요구사항 (EARS)

표기 규칙: **WHEN**(이벤트 구동), **WHILE**(상태 구동), **WHERE**(선택적 기능), **IF...THEN**(원치 않는 동작), **SHALL**(보편 요구).

### 2.1 추천 근거 설명 (REQ-EXPL) — Priority High

- **REQ-EXPL-001 (Ubiquitous)**: the 시스템 **SHALL** `recommendations` 테이블에 한국어 자연어 근거를 저장할 `explanation` 컬럼(Text, nullable)을 보유하며, 기존 `reasoning`(규칙 기반) 컬럼과 별개로 관리한다.
- **REQ-EXPL-002 (Event)**: **WHEN** 추천 파이프라인이 특정 종목의 추천을 산출하면, the 시스템 **SHALL** 해당 종목의 점수 분해(감성·거래량·모멘텀·이상)와 집계된 대표 뉴스 요약을 입력으로 Claude에 전달하여 한국어 2~3문장의 근거 텍스트를 생성하고 `explanation`에 저장한다.
- **REQ-EXPL-003 (Event)**: **WHEN** `GET /recommendations` 또는 `GET /recommendations/{krx_code}`가 호출되면, the 시스템 **SHALL** 응답 항목에 `explanation` 필드를 포함하여 반환한다(값이 없으면 null 또는 빈 문자열).
- **REQ-EXPL-004 (Ubiquitous)**: the 시스템 **SHALL** Claude 설명 생성에 기존 `ClaudeAnalysisClient` 패턴(`anthropic.AsyncAnthropic`, 모델 `claude-haiku-4-5`)을 재사용하고, API 키는 환경 변수 `ANTHROPIC_API_KEY`에서 읽는다.
- **REQ-EXPL-005 (Unwanted) [HARD]**: **IF** Claude 설명 생성이 실패하거나(네트워크·한도·타임아웃) 빈 응답을 반환하면, **THEN** the 시스템 **SHALL** 오류를 로그한 뒤 `explanation`을 비워 두거나 규칙 기반 `reasoning`으로 대체하고, 추천 파이프라인(점수 계산·적재)을 중단·실패시키지 않는다.
- **REQ-EXPL-006 (Unwanted)**: **IF** Claude가 투자 권유·매수/매도 지시·수익 보장성 표현을 포함한 설명을 생성하려 하면, **THEN** the 시스템 **SHALL** 프롬프트로 이를 금지하여 "정보 제공·근거 설명" 범위의 중립적 서술만 생성한다.

### 2.2 추천 히스토리 조회 (REQ-HIST) — Priority High

- **REQ-HIST-001 (Event)**: **WHEN** `GET /recommendations/history?days={n}`가 호출되면, the 시스템 **SHALL** 오늘로부터 최근 n일(기본 7일) 범위의 추천 기록을 `recommendations` 테이블에서 조회하여 반환한다.
- **REQ-HIST-002 (Ubiquitous)**: the 시스템 **SHALL** 히스토리 응답을 `trade_date` 기준으로 그룹화하여 날짜별 추천 목록(종목·순위·총점·explanation 포함)을 최신 날짜 우선으로 정렬해 반환한다.
- **REQ-HIST-003 (Unwanted)**: **IF** `days` 파라미터가 유효하지 않으면(음수·0·비숫자·과도한 값), **THEN** the 시스템 **SHALL** 422로 거부하거나 안전한 기본/상한값(예: 1~90일)으로 보정하되, 서버 오류(500)를 발생시키지 않는다.
- **REQ-HIST-004 (Unwanted)**: **IF** 해당 기간에 추천 기록이 없으면, **THEN** the 시스템 **SHALL** 빈 그룹 목록(`history: []`)을 정상 응답으로 반환하고 오류로 처리하지 않는다.
- **REQ-HIST-005 (Ubiquitous)**: the 시스템 **SHALL** 히스토리 조회를 인증 없이 접근 가능한 공개 엔드포인트로 제공한다(기존 `GET /recommendations`와 동일한 접근 정책).

### 2.3 뉴스 감성 상세화 (REQ-SENT) — Priority Medium

- **REQ-SENT-001 (Ubiquitous)**: the 시스템 **SHALL** `analysis_results` 테이블에 한국어 5단계 감성 라벨을 저장할 `sentiment_label` 컬럼(String, nullable)을 보유하며, 허용 값은 {매우긍정, 긍정, 중립, 부정, 매우부정}이다.
- **REQ-SENT-002 (Event)**: **WHEN** 뉴스 감성 분석 결과가 저장되면, the 시스템 **SHALL** 기존 `sentiment_score`(-1.0~1.0)를 5단계 라벨로 매핑하여 `sentiment_label`에 저장한다(매핑 경계는 §5.4에서 확정).
- **REQ-SENT-003 (Event)**: **WHEN** `GET /news`가 호출되면, the 시스템 **SHALL** 각 뉴스 항목에 `sentiment_label` 필드를 포함하여 반환한다(값이 없으면 null).
- **REQ-SENT-004 (Ubiquitous)**: the 시스템 **SHALL** 기존 `sentiment`(`positive/negative/neutral`) 필드를 보존하며, `sentiment_label`은 이를 대체하지 않고 보완한다.
- **REQ-SENT-005 (Unwanted)**: **IF** `sentiment_score`가 없거나(null) 매핑 불가하면, **THEN** the 시스템 **SHALL** `sentiment_label`을 null로 두고 오류로 처리하지 않으며, 기존 `sentiment` 표시 동작을 유지한다.

### 2.4 프론트엔드 (REQ-FE) — Priority Medium

- **REQ-FE-001 (Ubiquitous)**: the 시스템 **SHALL** 추천 종목 카드(`RecommendationList`/`StockDetail`)에 `explanation`(자연어 근거)을 표시하며, 값이 없으면 해당 영역을 생략하거나 기존 `reasoning` 표시로 대체한다.
- **REQ-FE-002 (Ubiquitous)**: the 시스템 **SHALL** 추천 히스토리를 조회·표시하는 페이지(또는 탭)를 제공하여 날짜별로 그룹화된 과거 추천 목록을 보여준다.
- **REQ-FE-003 (Event)**: **WHEN** 사용자가 히스토리 조회 기간(예: 7일/14일/30일)을 변경하면, the 시스템 **SHALL** `days` 파라미터를 `GET /recommendations/history`에 반영하여 목록을 갱신한다.
- **REQ-FE-004 (Ubiquitous)**: the 시스템 **SHALL** 뉴스 피드(`NewsFeed`)에 `sentiment_label`을 배지/텍스트로 표시하며, 값이 없으면 기존 `sentiment` 배지 표시를 유지한다.
- **REQ-FE-005 (Unwanted)**: **IF** 히스토리·추천·뉴스 조회 요청이 실패하면, **THEN** the 시스템 **SHALL** 사용자에게 오류 메시지를 표시하고 직전 표시 상태를 유지한다.

### 2.5 비기능 요구사항 (REQ-NFR)

- **REQ-NFR-001 (Ubiquitous)**: the 시스템 **SHALL** Claude 설명 생성의 호출·성공·실패·폴백을 구조화 로그로 남기되, API 키 등 시크릿을 로그에 포함하지 않는다.
- **REQ-NFR-002 (Ubiquitous) [HARD]**: the 시스템 **SHALL** Claude·뉴스 API 가용성과 무관하게 모든 기존 기능(SPEC-STOCK-001~005)을 동작시킨다.
- **REQ-NFR-003 (Ubiquitous)**: the 시스템 **SHALL** 신규 컬럼(`explanation`, `sentiment_label`)을 Alembic 마이그레이션 `0009`로 추가하며, 둘 다 nullable로 정의하여 기존 행에 영향을 주지 않는다.
- **REQ-NFR-004 (Ubiquitous)**: the 시스템 **SHALL** 신규 응답 필드(`explanation`, `sentiment_label`, history 응답)를 Optional로 정의하여 기존 프론트·클라이언트 하위 호환을 보장한다.
- **REQ-NFR-005 (Ubiquitous)**: the 시스템 **SHALL** 추천당 Claude 설명 생성을 추천 산출 1회당 1회로 제한하고(불필요한 재호출 금지), 호출 실패 시 재시도 정책을 기존 `ClaudeAnalysisClient` 패턴 범위로 한정한다.

---

## 3. 면책 및 안전 (Disclaimer & Safety)

- **REQ-SAFE-001 (Ubiquitous) [HARD]**: the 시스템 **SHALL** `explanation` 및 히스토리 화면을 포함한 모든 추천 표시 영역에 기존 투자 책임 면책 고지(`Disclaimer`)를 유지한다.
- **REQ-SAFE-002 (Unwanted) [HARD]**: **IF** 어떤 기능이 매수/매도 주문, 자동 매매, 수익 보장을 시도하면, **THEN** the 시스템 **SHALL** 이를 거부한다(영구 제외, §4 참조).

---

## 4. Exclusions (What NOT to Build)

본 SPEC 범위에서 **명시적으로 제외**하는 항목이다.

- **자동 매매·주문 실행 (영구 제외)**: 어떤 형태의 실제 매수/매도 주문, 증권사 API 연동, 자동 매매 로직도 구현하지 않는다. 본 시스템은 정보 제공 도구로만 유지된다.
- **Claude 설명의 실시간 스트리밍**: 설명은 추천 산출 시점에 1회 생성·저장하며, 조회 시점에 LLM을 재호출하지 않는다.
- **설명·감성 라벨 다국어화**: 본 SPEC은 한국어 설명·한국어 5단계 라벨만 다룬다. 영어 등 다국어 생성은 범위 밖이다.
- **추천 히스토리 기반 성과/수익률 분석**: 히스토리는 조회·표시만 제공한다. 과거 추천의 실제 주가 성과·백테스트 연계는 범위 밖이다(기존 SPEC-STOCK-002 백테스팅과 분리).
- **감성 라벨 기준의 사용자 정의화**: 5단계 경계값을 사용자가 조정하는 설정 기능은 제공하지 않는다(고정 매핑).
- **기존 `reasoning` 제거·치환**: 규칙 기반 `reasoning`을 삭제하거나 `explanation`으로 대체하지 않는다(둘 다 보존).
- **과거 데이터 일괄 백필(backfill)**: 기존 추천·분석 행에 대한 `explanation`/`sentiment_label` 소급 생성은 범위 밖이다(신규 산출분부터 적용). 단, `sentiment_label`은 `sentiment_score` 기반 단순 매핑이므로 선택적으로 백필 가능하나 필수는 아니다.

---

## 5. 설계 결정 (Design Decisions)

### 5.1 explanation vs reasoning 분리
- `reasoning`: 기존 규칙 기반 점수 분해 텍스트(`scoring/reasoning.py`), 변경·제거 금지.
- `explanation`: Claude 생성 한국어 자연어 근거, 신규 컬럼. 두 필드는 독립적으로 응답에 포함된다.

### 5.2 설명 생성 위치
- 추천 파이프라인(`recommendation/service.py`)에서 종목 추천 객체 적재 직전, 점수 분해 + 집계 대표 뉴스 요약(`aggregator`의 `top_summary`)을 입력으로 Claude 호출. 실패 시 폴백(REQ-EXPL-005).

### 5.3 히스토리 데이터 소스
- `recommendations` 테이블 직접 조회(DB 기반, 캐시 비사용). `trade_date >= today - days` 필터 후 `trade_date desc, rank asc` 정렬, 응답에서 날짜별 그룹화. (캐시는 당일 추천만 보관하므로 히스토리는 DB가 진실 소스.)

### 5.4 감성 5단계 매핑 (잠정, run 단계 확정)
- `sentiment_score` ∈ [-1.0, 1.0] → 라벨 경계(잠정): `>= 0.6` 매우긍정, `>= 0.2` 긍정, `> -0.2` 중립, `> -0.6` 부정, `<= -0.6` 매우부정. 경계값은 run 단계에서 실데이터로 미세 조정 가능.

### 5.5 신규 마이그레이션
- Alembic `0009_explanation_sentiment_label`: `recommendations.explanation`(Text, nullable), `analysis_results.sentiment_label`(String(20), nullable) 추가. 다운그레이드는 두 컬럼 drop.

### 5.6 스키마 하위 호환
- `RecommendationItem`·`RecommendationDetailResponse`에 `explanation: str | None = None`, `NewsItem`에 `sentiment_label: str | None = None` 추가. 히스토리 응답은 신규 스키마(`RecommendationHistoryResponse`)로 정의.

---

## 6. 수용 기준 요약

상세 Given-When-Then 시나리오는 `acceptance.md`를 따른다. 핵심 게이트:

- 추천 산출 시 종목별 `explanation`이 생성·저장되고 API 응답에 노출되며, Claude 실패 시에도 파이프라인이 중단되지 않는다.
- `GET /recommendations/history?days=N`이 날짜별 그룹화된 과거 추천을 반환하고, 빈 기간·잘못된 파라미터를 안전하게 처리한다.
- 뉴스 분석 결과에 `sentiment_label`(5단계)이 저장·노출되고, 기존 `sentiment`는 보존된다.
- 신규 컬럼은 nullable, 신규 필드는 Optional로 하위 호환을 유지하며, 자동 매매는 제공되지 않는다.
