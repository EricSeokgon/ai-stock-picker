---
id: SPEC-STOCK-008
version: 0.1.0
status: draft
created: 2026-06-10
updated: 2026-06-10
author: ircp
priority: high
issue_number: null
---

# SPEC-STOCK-008: 섹터 분석 대시보드 (Sector Analytics Dashboard)

## HISTORY

- 2026-06-10 (v0.1.0): 최초 초안. SPEC-STOCK-001~007 완료 후 Phase 9로 작성.
  - 핵심 동기: `SectorTrend` 모델·`GET /sectors/trends` API·프론트 `SectorTrendChart`는 이미
    존재하나 **`sector_trends` 테이블에 데이터를 적재하는 생산자(producer)가 없어** 섹터 차트가
    항상 비어 있는 상태(현 코드베이스 사실). 본 SPEC은 누락된 섹터 집계 생산자를 구현하여 기존
    인프라를 실제로 동작시키고, 섹터 단위 분석 화면을 추가한다.

---

## 1. 개요 (Overview)

### 1.1 배경

`ai-stock-picker`는 한국 주식/ETF 추천 대시보드로, 뉴스 감성·거래량·모멘텀 기반 종목 추천을
제공한다(SPEC-001~007). 분석 단계에서 각 기사는 `AnalysisResult.sector_tags`(섹터 태그 배열)와
`sentiment_score`(-1.0~1.0)를 산출하지만, **이 데이터를 섹터 단위로 집계하는 기능은 존재하지
않는다.**

현 코드베이스에는 섹터 분석을 위한 인프라가 부분적으로만 구현되어 있다:

- `SectorTrend` ORM 모델(`db/models.py`) — 존재하나 어떤 코드도 인스턴스를 생성하지 않음
- `GET /sectors/trends` API(`api/routes/sectors.py`) — 존재하나 항상 빈 목록 반환
- 프론트 `SectorTrendChart`(대시보드에 렌더됨) — 데이터가 없어 빈 차트 표시

본 SPEC은 이 "마지막 한 조각"인 **섹터 집계 생산자**를 구현하여 기존 API/차트를 실제로
동작시키고, 그 위에 섹터 단위 비교·상세 분석 화면을 추가하는 것을 목표로 한다.

### 1.2 목표

- 분석 결과(`AnalysisResult.sector_tags` + `sentiment_score` + 기사 수)를 일자별 섹터 단위로
  집계하여 `sector_trends` 테이블에 적재한다.
- 섹터 집계를 일일/장중 파이프라인에 연결하여 자동 갱신한다.
- 섹터 순위(평균 점수 상위 섹터), 섹터 상세(구성 종목·추세) API를 추가한다.
- 섹터 비교 화면을 프론트엔드에 추가하여 섹터 간 성과를 한눈에 비교할 수 있게 한다.

### 1.3 비목표 (Non-Goals)

본 SPEC은 WHAT/WHY를 정의하며 구현 세부(함수명·클래스 구조)는 Run 단계로 위임한다.

---

## 2. 용어 (Glossary)

- **섹터 집계(Sector Aggregation)**: 특정 거래일의 모든 분석 기사를 섹터별로 묶어 뉴스 수,
  평균 감성, 종합 트렌드 점수를 계산하는 작업.
- **트렌드 점수(trend_score)**: 섹터의 종합 매력도. 평균 감성과 뉴스 볼륨을 결합한 파생 지표.
- **섹터 순위(Sector Ranking)**: 거래일 기준 트렌드 점수 또는 평균 감성으로 정렬한 섹터 목록.
- **구성 종목(Constituent Stocks)**: 특정 섹터로 태깅된 기사에서 언급된 종목 집합.

---

## 3. 요구사항 (Requirements, EARS)

### 3.1 섹터 집계 생산자 (REQ-SEC-*)

- **REQ-SEC-001 (Event-Driven)**: WHEN 일일 파이프라인의 분석 단계가 완료되면, THEN the system
  SHALL 해당 거래일의 모든 `AnalysisResult`를 `sector_tags` 기준으로 섹터별 집계하여
  `sector_trends` 테이블에 적재한다.

- **REQ-SEC-002 (Ubiquitous)**: The system SHALL 각 섹터에 대해 뉴스 수(news_volume), 평균
  감성(avg_sentiment, -1.0~1.0), 종합 트렌드 점수(trend_score)를 계산하여 저장한다.

- **REQ-SEC-003 (Event-Driven)**: WHEN 동일 거래일·동일 섹터의 집계가 이미 존재하는 상태에서
  파이프라인이 재실행되면(장중 30분 증분), THEN the system SHALL 기존 행을 갱신(upsert)하고
  중복 행을 생성하지 않는다.

- **REQ-SEC-004 (State-Driven)**: WHILE 특정 거래일에 분석된 기사가 한 건도 없는 경우, the
  system SHALL 해당 거래일에 대해 섹터 집계 행을 생성하지 않으며 파이프라인을 중단하지 않는다.

- **REQ-SEC-005 (Unwanted Behavior)**: IF 섹터 집계 단계에서 예외가 발생하면, THEN the system
  SHALL 오류를 로깅하고 추천 파이프라인의 나머지 단계(추천 생성)를 계속 진행한다(집계 실패가
  추천을 막지 않는다).

- **REQ-SEC-006 (Ubiquitous)**: The system SHALL 섹터 집계 완료 후 섹터 트렌드 Redis 캐시
  (`sector_trends:{days}` 키)를 무효화하여 다음 조회 시 최신 데이터를 반영한다.

### 3.2 섹터 순위·상세 API (REQ-SEC-*)

- **REQ-SEC-010 (Event-Driven)**: WHEN 클라이언트가 `GET /sectors/ranking`을 호출하면, THEN
  the system SHALL 최신 거래일 기준 섹터를 정렬 기준(`sort=score|sentiment|volume`)에 따라
  내림차순 정렬한 목록을 반환한다.

- **REQ-SEC-011 (Optional)**: WHERE `limit` 쿼리 파라미터가 제공되면, the system SHALL 섹터
  순위 결과를 상위 `limit`개로 제한한다(기본값 적용, 미제공 시 전체 반환).

- **REQ-SEC-012 (Event-Driven)**: WHEN 클라이언트가 `GET /sectors/{sector}/detail`을 호출하면,
  THEN the system SHALL 해당 섹터의 최근 N일 트렌드 시계열과 해당 섹터로 태깅된 기사에서 언급된
  구성 종목 목록(종목코드·언급 횟수)을 반환한다.

- **REQ-SEC-013 (Unwanted Behavior)**: IF 존재하지 않는 섹터에 대해 `GET /sectors/{sector}/detail`
  이 호출되면, THEN the system SHALL HTTP 404와 한국어 오류 메시지를 반환한다.

- **REQ-SEC-014 (State-Driven)**: WHILE 섹터 순위/상세 데이터가 Redis 캐시에 존재하는 경우, the
  system SHALL DB 조회 없이 캐시에서 응답한다(기존 `sectors.py`의 캐시 우선 패턴 준수).

### 3.3 섹터 비교 화면 (REQ-SECUI-*)

- **REQ-SECUI-001 (Event-Driven)**: WHEN 사용자가 `/sectors` 경로에 접속하면, THEN the system
  SHALL 섹터 순위 표와 섹터별 트렌드 비교 차트를 표시한다.

- **REQ-SECUI-002 (Event-Driven)**: WHEN 사용자가 순위 표의 특정 섹터를 선택하면, THEN the
  system SHALL 해당 섹터의 상세(추세 시계열 + 구성 종목)를 표시한다.

- **REQ-SECUI-003 (Optional)**: WHERE 섹터 데이터가 아직 적재되지 않은 경우, the system SHALL
  빈 차트 대신 "섹터 데이터 준비 중" 안내 상태를 표시한다.

- **REQ-SECUI-004 (Ubiquitous)**: The system SHALL `/sectors` 페이지로 이동하는 네비게이션
  링크를 NavBar에 추가하고, 768px 미만 화면에서 기존 반응형 동작을 유지한다.

### 3.4 비기능 요구사항 (REQ-NFR-*)

- **REQ-NFR-001 (Ubiquitous)**: The system SHALL 본 SPEC의 모든 변경이 기존 API 응답 스키마와
  하위 호환되도록 유지한다(`GET /sectors/trends`의 기존 응답 형식 불변).

- **REQ-NFR-002 (Ubiquitous)**: The system SHALL 신규 외부 서비스를 도입하지 않으며, 기존
  스택(PostgreSQL, Redis, FinanceDataReader, APScheduler)만 사용한다.

- **REQ-NFR-003 (Ubiquitous)**: The system SHALL 백엔드 신규/변경 코드에 대해 테스트 커버리지
  85% 이상을 유지한다.

- **REQ-NFR-004 (Ubiquitous)**: The system SHALL 섹터 집계가 단일 거래일 분석 결과 전체를
  메모리에 적재하지 않고 집계 가능한 방식으로 처리한다(대량 기사 상황 대비).

---

## 4. 데이터 모델 영향 (Data Model Impact)

- **`sector_trends` 테이블 (기존, 변경 없음)**: 컬럼(sector, trade_date, news_volume,
  avg_sentiment, trend_score, computed_at)을 **그대로 재사용**한다. 본 SPEC은 이 테이블에 데이터를
  적재하는 생산자를 신규 구현할 뿐, 스키마를 변경하지 않는다.
- **upsert 지원을 위한 제약(신규 마이그레이션 0011, 선택적)**: REQ-SEC-003의 upsert를 위해
  `(sector, trade_date)` 복합 UNIQUE 제약이 필요하다. 기존 `sector_trends`에 해당 제약이 없으므로
  마이그레이션 0011로 추가한다. (누적 마이그레이션 규칙: 0001~0010 다음 0011.)
- **신규 테이블 없음**: 구성 종목은 기존 `StockMention` → `Article` → `AnalysisResult` 조인으로
  파생하므로 신규 테이블이 불필요하다.

---

## 5. 의존성 및 재사용 (Dependencies & Reuse)

- **재사용**: `AnalysisResult.sector_tags`(섹터 출처), `AnalysisResult.sentiment_score`(감성),
  `SectorTrend` 모델, `GET /sectors/trends` API, `RecommendationCache`(Redis 캐시 패턴),
  스케줄러 `run_daily_pipeline`/`run_intraday_pipeline`, 프론트 `SectorTrendChart`.
- **신규**: 섹터 집계 생산자 모듈, `GET /sectors/ranking`·`GET /sectors/{sector}/detail` 엔드포인트,
  프론트 `/sectors` 페이지, 마이그레이션 0011.

---

## 6. Exclusions (What NOT to Build)

- **자동 매매/주문 실행**: 규제·책임 리스크로 **영구 제외**. 섹터 분석은 정보 제공에 한정한다.
- **피드백(좋아요/싫어요) 기반 추천 재가중**: 본 SPEC 범위 밖. 피드백 데이터를 섹터 점수나 추천
  점수에 반영하지 않는다(별도 SPEC에서 다룰 후보).
- **섹터 자동 분류(ML/AI 재분류)**: 기존 `AnalysisResult.sector_tags`를 진실 소스로 사용하며,
  섹터 태깅 로직을 새로 만들지 않는다.
- **신규 외부 데이터 소스/서비스**: 섹터 지수·업종 시세 등 외부 섹터 데이터를 도입하지 않는다.
  집계는 내부 분석 결과만 사용한다.
- **사용자별 섹터 알림/구독**: 섹터 도달 알림 등 알림 고도화는 본 SPEC 범위 밖(향후 SPEC 후보).
- **`recommendations` 테이블에 sector 컬럼 추가**: 추천 항목의 섹터 필터(SPEC-005)는 별도 경로로
  유지하며, 본 SPEC에서 추천 스키마를 변경하지 않는다.

---

## 7. 성공 기준 (Success Criteria)

- `GET /sectors/trends`가 실제 데이터를 반환한다(파이프라인 실행 후 빈 목록이 아님).
- `GET /sectors/ranking`·`GET /sectors/{sector}/detail`가 정상 동작한다.
- 프론트 `/sectors` 페이지에서 섹터 순위·비교·상세를 확인할 수 있다.
- 장중 재실행 시 동일 거래일 섹터 행이 중복되지 않는다(upsert 검증).
- 백엔드 신규/변경 코드 테스트 커버리지 85% 이상.
- 기존 API/화면(추천·뉴스·포트폴리오 등) 회귀 없음(하위 호환).
