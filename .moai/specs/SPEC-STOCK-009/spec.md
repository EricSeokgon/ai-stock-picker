---
id: SPEC-STOCK-009
version: 0.1.0
status: draft
created: 2026-06-10
updated: 2026-06-10
author: ircp
priority: high
issue_number: null
---

# SPEC-STOCK-009: 추천 품질 개선 — 피드백 기반 가중치 + 스코어 투명성

## HISTORY

- 2026-06-10 (v0.1.0): 최초 초안. SPEC-STOCK-001~008 완료 후 Phase 10으로 작성.
  - 핵심 동기: SPEC-STOCK-007에서 추천 품질 피드백(`recommendation_feedback` 테이블,
    `POST|GET /recommendations/{krx_code}/feedback`)을 도입했으나 **"수집·표시만, 재가중은 제외"**
    로 명시했고, SPEC-STOCK-008은 이를 "별도 SPEC에서 다룰 후보"로 남겨두었다(두 SPEC의 사실).
    즉 **사용자 좋아요/싫어요가 누적되고 있으나 추천 점수에 전혀 반영되지 않는 미활용 데이터**가
    존재한다. 본 SPEC은 이 피드백을 점수에 **경계가 제한된(bounded) 방식으로 반영**하여 추천 품질을
    개선하고, 동시에 추천 점수가 어떻게 산출되는지(요인별 가중 기여도 + 피드백 조정)를 사용자에게
    투명하게 보여주는 화면을 추가한다.

---

## 1. 개요 (Overview)

### 1.1 배경

`ai-stock-picker`는 뉴스 감성·거래량·모멘텀·이상거래 4개 요인의 가중 합산으로 종목 점수를
계산한다(`scoring/engine.py`, 가중치 sentiment 0.40 / volume 0.20 / momentum 0.25 /
anomaly 0.15, 합계 1.0). 추천 파이프라인(`RecommendationService.run()`)은 이 점수로 Top 10을
선정하여 `recommendations` 테이블에 저장하고 Redis 캐시에 적재한다(스케줄러 주도).

SPEC-007에서 사용자가 추천에 좋아요/싫어요를 투표할 수 있는 기능을 추가했으나, 이 피드백은
집계·표시만 되고 추천 점수에는 반영되지 않는다(SPEC-007 §범위, SPEC-008 §6 모두 명시). 따라서:

- `recommendation_feedback` 테이블에 투표가 누적되지만 **추천 품질 개선에 활용되지 않는다.**
- 사용자는 추천 점수가 **왜** 그렇게 나왔는지(어떤 요인이 얼마나 기여했는지) 알 수 없다.
  현재 상세 화면(`StockDetail`, 상세 페이지)은 점수 숫자만 보여주고 요인별 기여도는 보여주지 않는다.

### 1.2 목표

- 종목별 누적 피드백(up/down)을 **경계가 제한된 조정 계수(feedback factor)** 로 변환하여 기본
  점수(base score)에 반영하고, 조정된 최종 점수로 추천 순위를 산정한다.
- 피드백 조정이 기존 4요인 점수 산식(0.40/0.20/0.25/0.15)을 **변경하지 않고**, 기본 점수를
  보존한 채 별도 조정 단계로 적용되도록 한다(하위 호환 + 투명성).
- 추천 상세 화면에 **요인별 가중 기여도(weight × score)** 와 **피드백 조정량**을 시각적으로
  분해하여 표시한다.
- 추천 목록에서 피드백이 반영되었음을 사용자가 인지할 수 있도록 표시한다.

### 1.3 비목표 (Non-Goals)

본 SPEC은 WHAT/WHY를 정의하며 구현 세부(함수명·클래스 구조)는 Run 단계로 위임한다.
자세한 제외 항목은 §6을 참조한다.

---

## 2. 용어 (Glossary)

- **기본 점수(base score)**: 피드백 조정 이전의 4요인 가중 합산 점수(현 `total_score` 산식
  결과). 0.0~1.0.
- **피드백 계수(feedback factor)**: 종목별 누적 up/down 투표를 정규화한 조정 계수. 표본 수
  기반 신뢰도를 반영하며 `[-MAX_ADJ, +MAX_ADJ]` 범위로 클램프된다(경계 제한).
- **조정 점수(adjusted score)**: 기본 점수에 피드백 계수를 적용한 최종 점수. 0.0~1.0으로
  클램프된다. 본 SPEC 이후 `total_score`는 이 조정 점수를 의미한다.
- **요인 기여도(factor contribution)**: 각 요인이 기본 점수에 기여한 양 = 가중치 × 요인 점수.
  4개 기여도의 합 = 기본 점수.
- **스코어 분해(score breakdown)**: 기본 점수의 요인별 기여도 + 피드백 조정량을 합산 구조로
  표현한 데이터/화면.

---

## 3. 요구사항 (Requirements, EARS)

### 3.1 피드백 기반 가중치 (REQ-FW-*)

- **REQ-FW-001 (Ubiquitous)**: The system SHALL 종목별 누적 좋아요(up)·싫어요(down) 수를
  정규화한 피드백 계수(feedback factor)를 산출하며, 그 값을 `[-MAX_ADJ, +MAX_ADJ]` 범위로
  클램프하여 단일 종목의 피드백이 추천을 과도하게 좌우하지 못하도록 한다.

- **REQ-FW-002 (Ubiquitous)**: The system SHALL 피드백 계수 산출 시 표본 수(총 투표 수)가
  적을수록 조정 영향이 작아지도록 신뢰도 가중을 적용한다(소수 투표가 큰 변동을 일으키지 않게 함).

- **REQ-FW-003 (Event-Driven)**: WHEN 추천 파이프라인이 실행되면, THEN the system SHALL 각
  후보 종목의 기본 점수를 계산한 뒤 해당 시점까지 누적된 피드백을 조정 계수로 적용하여 조정
  점수를 산출하고, 조정 점수 기준으로 Top 10 순위를 산정한다.

- **REQ-FW-004 (Ubiquitous)**: The system SHALL 조정 점수를 0.0~1.0 범위로 클램프하여 점수가
  유효 범위를 벗어나지 않도록 한다.

- **REQ-FW-005 (State-Driven)**: WHILE 특정 종목에 피드백이 한 건도 없는 경우, the system SHALL
  피드백 계수를 0으로 처리하여 조정 점수가 기본 점수와 동일하도록 한다(피드백 없음 = 변동 없음).

- **REQ-FW-006 (Ubiquitous)**: The system SHALL 추천 저장 시 기본 점수(base_score)와 피드백
  계수(feedback_score)를 조정 점수(total_score)와 함께 기록하여 조정 내역을 추적 가능하게 한다.

- **REQ-FW-007 (Ubiquitous)**: The system SHALL 여러 후보 종목의 피드백 집계를 한 번의 조회로
  일괄 수행하여 종목 수에 비례한 개별 쿼리(N+1)를 발생시키지 않는다.

### 3.2 스코어 투명성 (REQ-ST-*)

- **REQ-ST-001 (Event-Driven)**: WHEN 클라이언트가 종목 추천 상세를 조회하면, THEN the system
  SHALL 4개 요인 각각의 가중 기여도(가중치 × 요인 점수)와 피드백 조정량을 포함한 스코어 분해
  데이터를 반환한다.

- **REQ-ST-002 (Ubiquitous)**: The system SHALL 스코어 분해 데이터에서 4개 요인 기여도의 합이
  기본 점수와 일치하고, 기본 점수에 피드백 조정량을 더한 값이 조정 점수와 일치하도록 보장한다
  (분해의 산술 일관성).

- **REQ-ST-003 (Event-Driven)**: WHEN 사용자가 종목 상세 화면을 열면, THEN the system SHALL
  요인별 가중 기여도를 막대(또는 동등한 시각 요소)로 표시하고 피드백 조정량을 별도로 표시한다.

- **REQ-ST-004 (Event-Driven)**: WHEN 추천 목록이 표시되고 특정 항목에 피드백 조정이 적용된
  경우, THEN the system SHALL 해당 항목에 피드백이 반영되었음을 나타내는 표시(배지·툴팁 등)를
  보여준다.

- **REQ-ST-005 (Optional)**: WHERE 응답에 base_score·feedback_score 필드가 존재하지 않는 구
  데이터인 경우, the system SHALL 분해 화면을 오류 없이 렌더링하며 피드백 조정 영역을 생략한다
  (하위 호환).

### 3.3 비기능 요구사항 (REQ-NFR-*)

- **REQ-NFR-001 (Ubiquitous)**: The system SHALL 기존 4요인 점수 산식(가중치 0.40/0.20/0.25/
  0.15)과 `scoring/engine.py`의 `calculate_stock_score` 동작을 변경하지 않으며, 피드백 조정을
  기본 점수 산출 이후의 **별도 단계**로 적용한다.

- **REQ-NFR-002 (Ubiquitous)**: The system SHALL 본 SPEC의 모든 API 변경이 기존 응답 스키마와
  하위 호환되도록 신규 필드를 선택(optional)으로 추가한다(`GET /recommendations`,
  `GET /recommendations/{krx_code}`, `GET /recommendations/history`의 기존 필드 불변).

- **REQ-NFR-003 (Ubiquitous)**: The system SHALL 신규 외부 서비스를 도입하지 않으며, 기존
  스택(PostgreSQL, Redis, FastAPI, React, Recharts)만 사용한다.

- **REQ-NFR-004 (Ubiquitous)**: The system SHALL 백엔드 신규/변경 코드에 대해 테스트 커버리지
  85% 이상을 유지하며, 피드백 계수·조정 산출 로직을 순수 함수로 구현하여 단위 테스트 가능하게
  한다.

---

## 4. 데이터 모델 영향 (Data Model Impact)

- **`recommendations` 테이블 (기존, 컬럼 추가)**: 신규 마이그레이션 **0012**로 `base_score`
  (Numeric(6,3), nullable)와 `feedback_score`(Numeric(6,3), nullable) 컬럼을 추가한다.
  `total_score`는 그대로 유지하되 **의미가 조정 점수**로 바뀐다(기존 리더는 `total_score`만
  읽으면 동작 불변 → 하위 호환). 누적 마이그레이션 규칙: 0001~0011 다음 0012.
- **`recommendation_feedback` 테이블 (기존, 변경 없음)**: SPEC-007에서 만든 컬럼(id, krx_code,
  vote, user_id, created_at)을 그대로 읽기 전용으로 사용한다. 스키마 변경 없음.
- **신규 테이블 없음**: 피드백 계수·기여도는 기존 테이블에서 파생하므로 신규 테이블이 불필요하다.

---

## 5. 의존성 및 재사용 (Dependencies & Reuse)

- **재사용**: `recommendation_feedback` 테이블·`feedback/service.py`(집계 패턴),
  `scoring/engine.py`(기본 점수 산식·가중치 상수), `RecommendationService.run()`(파이프라인),
  `RecommendationCache`(Redis), `RecommendationItem`/`RecommendationDetailResponse` 스키마,
  프론트 `StockDetail`·상세 페이지·`RecommendationList`.
- **신규**: 피드백 계수 계산 순수 함수, 피드백 일괄 집계 조회, 조정 적용 순수 함수, 스코어 분해
  계산 유틸, 프론트 스코어 분해 컴포넌트·피드백 반영 표시, 마이그레이션 0012.

---

## 6. Exclusions (What NOT to Build)

- **자동 매매/주문 실행**: 규제·책임 리스크로 **영구 제외**. 본 SPEC은 추천 품질·투명성에 한정한다.
- **A/B 테스트 인프라/실험 플랫폼**: 가중치 실험을 위한 A/B 분기·트래픽 분할·실험 관리 시스템은
  1스프린트 범위를 초과하므로 본 SPEC에서 만들지 않는다(향후 SPEC 후보).
- **4요인 가중치(0.40/0.20/0.25/0.15) 변경·재학습**: 기존 산식은 진실 소스로 보존한다. 피드백은
  요인 가중치를 바꾸지 않고 별도 조정 단계로만 작용한다.
- **머신러닝 기반 추천 모델**: 피드백을 학습 데이터로 쓰는 ML 모델·학습 파이프라인은 범위 밖.
  본 SPEC의 조정은 결정론적 규칙(정규화 + 신뢰도 + 클램프)이다.
- **사용자별 개인화 추천**: 피드백은 종목 단위 전체 집계로만 사용하며, 개인별 맞춤 추천(SPEC
  Option B 후보)은 본 SPEC 범위 밖이다.
- **실시간(요청 시점) 점수 재계산**: 조정은 추천 파이프라인 실행 시점에 일괄 적용한다.
  `GET /recommendations`는 기존대로 캐시에서 읽으며, API 호출마다 점수를 재계산하지 않는다
  (캐시 적재 주체는 스케줄러 — 기존 동작 보존).
- **피드백 어뷰징 방지(중복 투표 차단·레이트 리밋)**: 투표 무결성·봇 방어는 본 SPEC 범위 밖.
  신뢰도 가중·클램프로 영향만 제한한다.

---

## 7. 성공 기준 (Success Criteria)

- 피드백이 누적된 종목의 조정 점수가 기본 점수와 달라지고, 피드백이 없는 종목은 동일하다.
- 단일 종목의 다수 투표가 추천을 과도하게 좌우하지 않는다(클램프·신뢰도 검증).
- 조정 점수가 항상 0.0~1.0 범위를 유지한다.
- 상세 응답의 요인 기여도 합 = 기본 점수, 기본 점수 + 피드백 조정량 = 조정 점수(산술 일관성).
- 프론트 상세 화면에서 요인별 기여도와 피드백 조정을 시각적으로 확인할 수 있다.
- 구 데이터(base_score·feedback_score 없음)에서도 화면이 오류 없이 렌더링된다.
- 기존 4요인 산식·API 응답·추천/뉴스/섹터 화면 회귀 없음(하위 호환).
- 백엔드 신규/변경 코드 테스트 커버리지 85% 이상.
