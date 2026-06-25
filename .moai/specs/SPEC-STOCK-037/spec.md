---
id: SPEC-STOCK-037
version: 0.2.0
status: draft
created_at: 2026-06-25
updated: 2026-06-25
author: ircp
priority: high
issue_number: 0
labels: [ai, recommendation, portfolio]
---

# SPEC-STOCK-037: AI 종목 추천 고도화 (Advanced AI Stock Recommendation)

## HISTORY

- v0.2.0 (2026-06-25): plan-auditor v1 지적사항 반영 — ACs GWT→EARS 전환(17건), YAML 수정(created_at·labels), NFR 접두사 REQ-AIEX-NFR-* 통일, APPLY-003 무조건 SHALL화, NFR-001 행위 기술화.
- v0.1.0 (2026-06-25): 초안 작성. 포트폴리오 인식 추천·구조화 근거·사용자 선호 학습 3대 축 정의.

---

## 개요 (Overview)

기존 전역 AI 추천 시스템(SPEC-001·006·009)은 모든 사용자에게 동일한 일일 Top-10을 제공한다.
본 SPEC은 추천을 **사용자 포트폴리오 맥락에 맞춰 개인화**하고, **추천 근거를 구조화**하며,
**사용자 선호(좋아요/싫어요)를 학습**하여 향후 추천에 반영하는 고도화 계층을 추가한다.

기존 자산(`recommendation/service.py` 전역 파이프라인, `portfolio/ai_analysis.py` Claude 연동,
`get_portfolio_with_holdings` 소유권 검증)은 재사용·확장하며, 4요인 스코어 산식은 변경하지 않는다.

---

## 용어 (Glossary)

- **포트폴리오 컨텍스트(portfolio context)**: 사용자 보유 종목의 티커·섹터·비중·섹터 노출 집합.
- **적합도(fit_score)**: 추천 종목이 사용자 포트폴리오에 부합하는 정도. 0.0~1.0 실수.
- **추천 근거(rationale)**: 추천 사유(reason)·위험 요인(risk_factors)·적합도(fit_score)로 구성된 구조.
- **선호(preference)**: 사용자가 특정 추천 종목에 표시한 좋아요(liked)/싫어요(disliked) 신호.
- **개인화 추천(personalized recommendation)**: 포트폴리오 컨텍스트와 선호를 반영해 산출된 추천 결과.

---

## 요구사항 (Requirements, EARS)

### 포트폴리오 인식 추천 (REQ-AIEX-PORT)

- **REQ-AIEX-PORT-001** (Event-Driven): WHEN 사용자가 특정 포트폴리오에 대한 개인화 추천을 요청하면, THE 시스템 SHALL 해당 포트폴리오의 현재 보유 종목과 섹터 노출을 추천 산출의 입력 맥락으로 사용한다.
- **REQ-AIEX-PORT-002** (Ubiquitous): THE 시스템 SHALL 보유 종목과 동일한 종목을 개인화 추천 결과에서 제외한다.
- **REQ-AIEX-PORT-003** (State-Driven): WHILE 포트폴리오의 특정 섹터 노출이 과도하게 집중된 상태이면, THE 시스템 SHALL 해당 섹터 외 종목을 우선하는 분산 지향 추천을 제시한다.
- **REQ-AIEX-PORT-004** (Unwanted): IF 요청된 포트폴리오에 보유 종목이 없으면, THEN THE 시스템 SHALL 추천 산출을 시도하지 않고 보유 종목이 없음을 알리는 안내 응답을 반환한다.

### 추천 근거 (REQ-AIEX-RAT)

- **REQ-AIEX-RAT-001** (Ubiquitous): THE 시스템 SHALL 개인화 추천 각 항목에 대해 추천 사유, 위험 요인, 적합도를 포함한 구조화 근거를 제공한다.
- **REQ-AIEX-RAT-002** (Ubiquitous): THE 시스템 SHALL 각 추천 항목의 적합도를 0.0 이상 1.0 이하의 값으로 제공한다.
- **REQ-AIEX-RAT-003** (Ubiquitous): THE 시스템 SHALL 추천 근거 텍스트에 투자 권유나 수익 보장 표현 대신 분석 관점의 설명과 면책 안내를 포함한다.

### 사용자 선호 저장 (REQ-AIEX-PREF)

- **REQ-AIEX-PREF-001** (Event-Driven): WHEN 사용자가 추천 종목에 좋아요 또는 싫어요를 표시하면, THE 시스템 SHALL 해당 사용자와 종목에 대한 선호를 영속적으로 저장한다.
- **REQ-AIEX-PREF-002** (Event-Driven): WHEN 사용자가 이미 선호를 표시한 종목에 다른 선호를 다시 표시하면, THE 시스템 SHALL 기존 선호를 새 선호로 갱신한다.
- **REQ-AIEX-PREF-003** (Unwanted): IF 좋아요·싫어요 외의 선호 값이 전달되면, THEN THE 시스템 SHALL 해당 요청을 거부하고 선호를 저장하지 않는다.

### 선호 적용 (REQ-AIEX-APPLY)

- **REQ-AIEX-APPLY-001** (State-Driven): WHILE 사용자가 특정 종목을 싫어요로 표시한 상태이면, THE 시스템 SHALL 이후 개인화 추천에서 해당 종목을 후순위로 조정하거나 제외한다.
- **REQ-AIEX-APPLY-002** (State-Driven): WHILE 사용자가 특정 종목을 싫어요로 표시한 상태이면, THE 시스템 SHALL 이후 개인화 추천에서 그 종목과 유사한 종목의 우선순위를 낮춘다.
- **REQ-AIEX-APPLY-003** (Optional): WHERE 사용자가 좋아요로 표시한 종목과 유사한 종목이 존재하면, THE 시스템 SHALL 해당 종목의 우선순위를 높인다.

### 추천 히스토리 (REQ-AIEX-HIST)

- **REQ-AIEX-HIST-001** (Event-Driven): WHEN 사용자가 개인화 추천 히스토리를 요청하면, THE 시스템 SHALL 해당 사용자에게 과거 제공된 추천 항목과 그 시점을 반환한다.
- **REQ-AIEX-HIST-002** (Ubiquitous): THE 시스템 SHALL 개인화 추천을 산출할 때 그 결과를 사용자별 히스토리로 영속화한다.

### 소유권 보호 (REQ-AIEX-OWN)

- **REQ-AIEX-OWN-001** (Unwanted): IF 사용자가 자신이 소유하지 않은 포트폴리오에 대해 추천·선호·히스토리 기능에 접근하면, THEN THE 시스템 SHALL 해당 자원을 찾을 수 없음으로 응답한다.

### 비기능 요구사항 (REQ-AIEX-NFR)

- **REQ-AIEX-NFR-001**: THE 시스템 SHALL 점수·순위 계산을 표준 산술 연산만으로 수행하며, 외부 과학 계산 라이브러리에 의존하지 않는다.
- **REQ-AIEX-NFR-002**: THE 시스템 SHALL 적합도 산출과 선호 기반 재순위 로직을 데이터베이스 의존 없이 검증 가능한 순수 함수로 제공한다.
- **REQ-AIEX-NFR-003**: THE 시스템 SHALL 소유권 위반 접근에 대해 접근 거부가 아닌 자원 없음 의미의 응답을 반환한다.
- **REQ-AIEX-NFR-004**: IF 외부 AI 분석 호출이 실패하면, THEN THE 시스템 SHALL 폴백 결과를 반환하고 추천 요청 처리를 중단하지 않는다.
- **REQ-AIEX-NFR-005**: THE 시스템 SHALL 선호 저장을 조회 후 기록(SELECT-then-write) 방식으로 데이터베이스 종류에 중립적으로 수행한다.

---

## Exclusions (What NOT to Build)

- **자동 매매·주문 실행**: 규제·책임 리스크로 영구 제외.
- **실시간 시세 피드 기반 추천**: 추천은 일일/배치 데이터 기준. 실시간 틱 추천 미포함.
- **ML 모델 학습**: 선호 학습은 규칙 기반(선호 신호 → 재순위)이며, Claude API가 유일한 AI 계층. 자체 모델 학습 없음.
- **소셜·뉴스 감성 신규 수집**: 감성 분석은 SPEC-019·020 자산 재사용, 본 SPEC에서 신규 수집 안 함.
- **4요인 스코어 산식 변경**: `scoring/engine.py` 0.40/0.20/0.25/0.15 가중치 불변.
- **전역 추천 파이프라인 재작성**: `recommendation/service.py`는 재사용. 개인화 계층만 추가.
- **기존 전역 피드백(`recommendation_feedback`) 의미 변경**: 전역 up/down 집계는 그대로 두고, 개인화 선호는 별도 저장소 사용.

---

## 의존성 (Dependencies)

- SPEC-STOCK-017: `get_portfolio_with_holdings`·소유권·섹터 파생.
- SPEC-STOCK-026: `portfolio/ai_analysis.py` Claude 연동 패턴(`optimize_portfolio_with_claude` new_stocks).
- SPEC-STOCK-006·009: 전역 추천·근거·피드백 인프라.

## 영향 범위 (Impact)

- 신규 마이그레이션 0024(down_rev=0023): 사용자 선호 + 개인화 추천 히스토리 저장소.
- `portfolio/ai_analysis.py` 확장(신규 함수), 신규 순수 함수 모듈(적합도·재순위).
- `portfolio/router.py`에 개인화 추천·선호·히스토리 엔드포인트 추가.
- 프론트엔드 Portfolio 페이지에 개인화 추천 UI 추가.
