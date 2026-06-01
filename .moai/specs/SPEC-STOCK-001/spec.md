---
id: SPEC-STOCK-001
version: 0.1.0
status: draft
created: 2026-06-01
updated: 2026-06-01
author: ircp
priority: high
issue_number: null
---

# SPEC-STOCK-001: 한국 주식 & ETF 추천 시스템

## HISTORY

- 2026-06-01 (v0.1.0): 최초 작성. 뉴스 수집 → Claude 감성 분석 → 트렌드 집계 → 추천 엔진 → 웹 대시보드 전체 파이프라인 요구사항 정의.

---

## 1. 시스템 개요

### 1.1 목적

국내 금융 뉴스와 실시간 시세 데이터를 결합하여 매일 자동으로 한국 주식 및 ETF 추천 리스트를 생성하고, 그 근거를 함께 제시하는 웹 대시보드 서비스를 구축한다. 사람이 수십 개의 뉴스를 일일이 읽고 종목과 연결하는 수작업을 AI 파이프라인으로 대체한다.

### 1.2 타겟 사용자

| 사용자 그룹 | 특성 | 핵심 니즈 |
|------------|------|----------|
| 개인 투자자 (입문~중급) | 정보 탐색 시간이 부족하고 종목 발굴 채널이 제한적 | 매일 아침 "오늘 주목할 종목"을 근거와 함께 확인 |
| 액티브 트레이더 | 장중 뉴스 흐름과 섹터 로테이션에 민감 | 장중 30분 단위 트렌드 갱신과 거래량 이상 신호 |
| 테마/섹터 투자자 | 개별 종목보다 섹터·테마 단위로 접근 | 섹터별 뉴스 볼륨·감성 트렌드 차트와 ETF 추천 |

### 1.3 핵심 가치 제안

- **시간 절약**: 매일 수백 건의 금융 뉴스를 자동 수집·분석하여 핵심만 요약 제공
- **근거 기반 추천**: 단순 시세가 아니라 뉴스 감성 + 가격 모멘텀 + 거래량 이상을 종합한 설명 가능한(explainable) 추천
- **트렌드 가시화**: 섹터·테마 단위 뉴스 흐름을 차트로 시각화하여 시장의 관심 이동을 직관적으로 파악
- **자동화**: 오전 배치 + 장중 갱신으로 사람 개입 없이 매일 최신 추천 유지

---

## 2. 핵심 기능 요구사항 (EARS)

표기 규칙: **WHEN**(이벤트 구동), **WHILE**(상태 구동), **WHERE**(선택적 기능), **IF...THEN**(원치 않는 동작), **SHALL**(보편 요구).

### 2.1 뉴스 수집 엔진 (REQ-NEWS)

- **REQ-NEWS-001 (Event)**: **WHEN** 매일 오전 6시 스케줄이 트리거되면, the 시스템 **SHALL** 네이버 금융, 한국경제, 매일경제, 연합뉴스 금융 RSS 소스에서 신규 기사를 수집한다.
- **REQ-NEWS-002 (Event)**: **WHEN** 장중(09:00~15:30) 30분 간격 스케줄이 트리거되면, the 시스템 **SHALL** 동일 소스에서 신규 기사만 증분 수집한다.
- **REQ-NEWS-003 (Ubiquitous)**: the 시스템 **SHALL** 수집한 모든 기사의 원문, URL, 출처, 발행시각, 수집시각을 `articles` 테이블에 저장한다.
- **REQ-NEWS-004 (Unwanted)**: **IF** 이미 수집된 URL과 동일한 기사가 다시 수집되면, **THEN** the 시스템 **SHALL** 중복 저장하지 않고 스킵한다 (URL 기준 멱등성).
- **REQ-NEWS-005 (Unwanted)**: **IF** 특정 소스 요청이 차단(HTTP 403/429)되거나 타임아웃되면, **THEN** the 시스템 **SHALL** 해당 소스를 스킵하고 나머지 소스 수집을 계속하며 실패를 로그로 남긴다.
- **REQ-NEWS-006 (Ubiquitous)**: the 시스템 **SHALL** 크롤링 시 User-Agent 헤더를 설정하고 요청 간 최소 지연(throttle)을 적용한다.

### 2.2 AI 감성 분석 (REQ-AI)

- **REQ-AI-001 (Event)**: **WHEN** 미분석 기사가 존재하면, the 시스템 **SHALL** Claude API(claude-sonnet-4-6)를 호출하여 기사별 감성(positive/negative/neutral)을 분류한다.
- **REQ-AI-002 (Ubiquitous)**: the 시스템 **SHALL** 각 기사에 대해 섹터 태그(배열), 핵심 키워드(배열), 1문장 요약을 추출한다.
- **REQ-AI-003 (Ubiquitous)**: the 시스템 **SHALL** Claude API 응답을 정해진 JSON 스키마로 강제하고, 스키마를 만족하지 못한 응답은 분석 실패로 처리한다.
- **REQ-AI-004 (State)**: **WHILE** 미분석 기사가 다수 존재하는 동안, the 시스템 **SHALL** 기사를 배치 단위로 묶어 처리하여 API 호출 횟수를 최소화한다.
- **REQ-AI-005 (Unwanted)**: **IF** Claude API 호출이 실패(rate limit/네트워크/스키마 위반)하면, **THEN** the 시스템 **SHALL** 최대 3회까지 지수 백오프로 재시도하고, 최종 실패 시 기사를 `analysis_failed` 상태로 표시한 뒤 다음 기사로 진행한다.
- **REQ-AI-006 (Ubiquitous)**: the 시스템 **SHALL** 분석 결과(감성, 섹터 태그, 키워드, 요약, 사용 토큰 수)를 `analysis_results` 테이블에 저장한다.

### 2.3 트렌드 집계 (REQ-TREND)

- **REQ-TREND-001 (Event)**: **WHEN** 분석 결과가 갱신되면, the 시스템 **SHALL** 섹터별/테마별로 뉴스 볼륨(건수)과 평균 감성 점수를 집계한다.
- **REQ-TREND-002 (Ubiquitous)**: the 시스템 **SHALL** 섹터별 트렌드 스코어 = f(뉴스 볼륨, 평균 감성, 최근성 가중치)를 산출하여 `sector_trends` 테이블에 저장한다.
- **REQ-TREND-003 (Ubiquitous)**: the 시스템 **SHALL** 트렌드 집계 시 최근 기사에 더 높은 시간 감쇠(time-decay) 가중치를 부여한다.

### 2.4 주식/ETF 매핑 (REQ-MAP)

- **REQ-MAP-001 (Event)**: **WHEN** 기사 분석 결과가 저장되면, the 시스템 **SHALL** 기사 본문에서 언급된 종목명을 KRX 종목 코드로 매핑하여 `stock_mentions` 테이블에 저장한다.
- **REQ-MAP-002 (Ubiquitous)**: the 시스템 **SHALL** FinanceDataReader를 통해 매핑된 종목의 시세(종가, 등락률, 거래량)를 조회한다.
- **REQ-MAP-003 (Unwanted)**: **IF** 종목명이 KRX 코드와 매핑되지 않으면, **THEN** the 시스템 **SHALL** 해당 언급을 `unmapped`로 기록하고 추천 후보에서 제외한다.

### 2.5 추천 엔진 (REQ-REC)

- **REQ-REC-001 (Event)**: **WHEN** 트렌드 집계와 시세 조회가 완료되면, the 시스템 **SHALL** 종목별 종합 추천 점수를 산출한다 (점수 구성: 섹션 5 참조).
- **REQ-REC-002 (Ubiquitous)**: the 시스템 **SHALL** 종합 점수 상위 10개 종목을 일일 주식 추천 리스트로 생성한다.
- **REQ-REC-003 (Ubiquitous)**: the 시스템 **SHALL** 섹터 트렌드 스코어를 기반으로 ETF 추천 리스트를 별도로 생성한다.
- **REQ-REC-004 (Ubiquitous)**: the 시스템 **SHALL** 각 추천 항목에 대해 사람이 읽을 수 있는 근거 설명(어떤 뉴스/섹터/모멘텀이 기여했는지)을 함께 저장한다.
- **REQ-REC-005 (Ubiquitous)**: the 시스템 **SHALL** 추천 결과를 `recommendations` 테이블에 저장하고, 조회 성능을 위해 Redis에 캐싱한다.
- **REQ-REC-006 (State)**: **WHILE** 당일 추천이 이미 생성된 상태에서 장중 갱신이 발생하면, the 시스템 **SHALL** 추천을 재계산하고 캐시를 갱신한다.

### 2.6 웹 대시보드 (REQ-WEB)

- **REQ-WEB-001 (Event)**: **WHEN** 사용자가 대시보드에 접속하면, the 시스템 **SHALL** 당일 Top 10 주식 추천과 ETF 추천 리스트를 표시한다.
- **REQ-WEB-002 (Event)**: **WHEN** 사용자가 추천 종목을 선택하면, the 시스템 **SHALL** 해당 종목의 추천 근거(기여 뉴스, 감성, 모멘텀 지표)를 상세 표시한다.
- **REQ-WEB-003 (Ubiquitous)**: the 시스템 **SHALL** 섹터별 트렌드(뉴스 볼륨·감성)를 시계열 차트(Recharts)로 시각화한다.
- **REQ-WEB-004 (Ubiquitous)**: the 시스템 **SHALL** 최신 뉴스 피드(요약, 감성, 출처 링크)를 표시한다.
- **REQ-WEB-005 (Ubiquitous)**: the 시스템 **SHALL** 모든 추천 화면에 투자 책임 면책 고지를 명시한다.
- **REQ-WEB-006 (Unwanted)**: **IF** 추천 데이터가 아직 생성되지 않았거나 조회에 실패하면, **THEN** the 시스템 **SHALL** 오류 대신 "데이터 준비 중" 상태와 마지막 갱신 시각을 표시한다.

### 2.7 비기능 요구사항 (REQ-NFR)

- **REQ-NFR-001 (Ubiquitous)**: the 시스템 **SHALL** 대시보드 추천 리스트 API 응답을 캐시 히트 시 500ms 이내(P95)에 반환한다.
- **REQ-NFR-002 (Ubiquitous)**: the 시스템 **SHALL** Claude API 키 등 모든 시크릿을 환경 변수로 관리하고 버전 관리에 포함하지 않는다.
- **REQ-NFR-003 (Ubiquitous)**: the 시스템 **SHALL** 일일 Claude API 토큰 사용량을 기록하여 비용을 추적 가능하게 한다.
- **REQ-NFR-004 (Ubiquitous)**: the 시스템 **SHALL** 수집·분석·추천 각 단계의 실행 결과와 실패를 구조화 로그로 남긴다.

---

## 3. Exclusions (What NOT to Build)

본 SPEC 범위에서 명시적으로 **제외**되는 항목 (Phase 2/3 또는 영구 제외):

- **자동 매매/주문 실행**: 증권사 API 연동을 통한 실제 매수/매도 주문 기능은 구현하지 않는다 (영구 제외, 규제·책임 리스크).
- **백테스팅 엔진**: 과거 데이터로 추천 알고리즘 성과를 검증하는 백테스팅은 Phase 3로 연기한다.
- **포트폴리오 시뮬레이터**: 가상 포트폴리오 구성·수익률 추적 기능은 Phase 3로 연기한다.
- **푸시/이메일 알림**: 추천 변경 알림 기능은 Phase 3로 연기한다.
- **사용자 인증/계정 시스템**: MVP는 단일 공개 대시보드이며, 로그인·개인화·즐겨찾기는 본 SPEC 범위 밖이다.
- **해외 주식/암호화폐**: 한국 주식(KRX)과 국내 상장 ETF만 대상으로 하며, 해외 자산은 제외한다.
- **실시간 틱 데이터 스트리밍**: 30분 간격 갱신을 채택하며, 초/틱 단위 실시간 스트리밍은 구현하지 않는다.
- **모바일 네이티브 앱**: 반응형 웹 대시보드만 제공하며, iOS/Android 네이티브 앱은 제외한다.

---

## 4. 가정 및 제약 (Assumptions & Constraints)

ASSUMPTIONS I'M MAKING:
1. RSS 피드와 네이버 금융 페이지 구조는 안정적이며, 크롤링이 robots.txt 및 각 사이트 이용약관 범위 내에서 허용된다고 가정한다.
2. Claude API claude-sonnet-4-6 모델에 안정적으로 접근 가능하고 일일 호출 한도가 예상 기사량을 처리할 수 있다고 가정한다.
3. FinanceDataReader가 제공하는 KRX 시세 데이터의 지연/정확도가 일/장중 추천 목적에 충분하다고 가정한다.
4. MVP는 단일 서버(또는 단일 컨테이너 세트)에서 운영되며 대규모 동시 접속은 가정하지 않는다.

- 본 시스템은 **투자 정보 제공 도구**이며 투자 권유·자문이 아니다. 모든 화면에 면책 고지를 포함한다 (REQ-WEB-005).
- 기술 스택은 확정: Python(FastAPI) 백엔드, React 프론트엔드, PostgreSQL 저장소, Redis 캐시, APScheduler 스케줄러.
