---
id: SPEC-STOCK-007
version: 0.1.0
status: draft
created: 2026-06-10
updated: 2026-06-10
author: ircp
priority: high
issue_number: null
---

# SPEC-STOCK-007: 한국 주식 & ETF 추천 시스템 — Phase 8 (종목 검색 · 상세 페이지 · 추천 품질 피드백)

## HISTORY

- 2026-06-10 (v0.1.0): 최초 작성. SPEC-STOCK-001(MVP)·002(개인화/인증/텔레그램/백테스팅)·003(실시간)·004(알림)·005(성능·UX)·006(AI 설명·히스토리·감성 상세) 완료 위에 **탐색성(Discoverability)·시각화(Visualization)·신뢰 피드백(Trust Feedback)** 축을 추가한다. 3대 영역 — (A) 종목 검색(Search), (B) 종목 상세 페이지 고도화 + 가격 차트(Stock Detail Page), (C) 추천 품질 피드백(Recommendation Feedback) — 을 단일 SPEC으로 정의한다. 이미 수집되나 미활용 중인 자산(`krx_master.csv` 종목명↔코드 매핑, `prices.py` 30일 OHLCV, 추천 히스토리)을 사용자 가치로 전환한다. 자동 매매/주문은 영구 제외를 유지한다.

---

## 1. 시스템 개요

### 1.1 목적

SPEC-STOCK-001~006으로 추천·개인화·실시간·알림·성능·AI 설명 축을 완성한 위에, **사용자가 원하는 종목을 직접 찾고(탐색성), 가격 흐름으로 추천을 시각적으로 검증하며(시각화), 추천 품질에 의견을 남길 수 있도록(신뢰 피드백) 시스템을 확장한다.** Phase 8은 다음을 추가한다.

1. **종목 검색(Search)**: `GET /stocks/search?q={질의}`로 종목명(부분 일치)·종목코드(접두 일치) 검색을 제공한다. 데이터 소스는 이미 로딩되는 `krx_master`(종목명→코드)와 당일/최근 추천 기록이다. 상위 N건을 반환하고, 각 결과가 현재 추천 목록에 포함되는지 여부를 함께 표시한다.
2. **종목 상세 페이지 + 가격 차트(Stock Detail Page)**: 기존 `StockDetail` 모달에 **30일 가격 라인 차트(Recharts)** 를 추가하고, 딥링크 가능한 라우트 `/stocks/:krxCode`로 동일 상세를 전체 페이지로도 제공한다. 가격 시계열은 신규 엔드포인트 `GET /stocks/{krx_code}/prices?days={n}`이 `prices.py`(FinanceDataReader)를 재사용하여 반환하며, Redis로 캐시한다.
3. **추천 품질 피드백(Recommendation Feedback)**: 신규 테이블 `recommendation_feedback`에 종목별 추천에 대한 좋아요/싫어요(up/down) 투표를 저장한다. `POST /recommendations/{krx_code}/feedback`으로 투표를 기록하고, `GET /recommendations/{krx_code}/feedback`으로 집계(up/down 카운트)를 반환하며, 상세 화면에서 버튼·카운트로 노출한다.

### 1.2 타겟 사용자

| 사용자 그룹 | 특성 | Phase 8에서 추가되는 핵심 니즈 |
|------------|------|------------------------------|
| 능동 탐색 사용자 | Top 10 밖의 특정 종목을 직접 확인하고 싶음 | 종목명/코드로 검색하여 원하는 종목 상세로 즉시 이동 |
| 검증 지향 사용자 | 점수·뉴스만으로는 가격 흐름이 안 보임 | 30일 가격 차트로 추천 점수와 실제 추세를 대조 |
| 참여형 사용자 | 추천이 유용했는지 의견을 남기고 싶음 | 좋아요/싫어요로 추천 품질에 대한 신호 제공 |

### 1.3 핵심 가치 제안

- **탐색성**: Top 10에 없는 종목도 검색으로 찾아 상세를 확인할 수 있다.
- **시각화**: 가격 라인 차트로 추천 점수의 맥락(추세)을 직관적으로 제공한다.
- **신뢰 피드백**: 사용자 의견을 수집·표시하여 추천 시스템에 대한 참여와 신뢰를 높인다.
- **자산 재활용**: 이미 수집·로딩되는 `krx_master`·OHLCV·추천 히스토리를 신규 외부 서비스 없이 가치로 전환한다.
- **하위 호환**: 모든 신규 엔드포인트·테이블·필드는 추가 전용이며, 기존 `StockDetail` 모달과 SPEC-STOCK-001~006 동작을 보존한다.
- **안전한 확장**: 가격 조회(FinanceDataReader) 실패 시에도 화면은 점수·뉴스·설명을 정상 표시한다([HARD], REQ-PRICE-005). 자동 매매/주문은 영구 제외를 유지한다.

### 1.4 기존 시스템과의 관계 (SPEC-STOCK-001~006 재정의 금지)

다음은 이미 구현 완료된 자산이며 **본 SPEC에서 재정의하지 않고 재사용·확장**한다.

- 백엔드: FastAPI + PostgreSQL(SQLAlchemy 2.0 async) + Redis + APScheduler, Alembic 마이그레이션(최신 `0009`). 프론트: React 18 + TypeScript + Vite + Recharts.
- 종목 매핑: `mapping/krx_master.py` `load_krx_master()`(종목명→KRX코드 dict), `mapping/mapper.py`, `mapping/etf_master.py` — 본 SPEC의 검색 데이터 소스로 재사용한다.
- 시세: `mapping/prices.py` `get_stock_price_data()`(executor로 FinanceDataReader 격리, 최신 1건 반환) — 본 SPEC은 동일 모듈에 **30일 시계열 반환 함수를 추가**하고 Redis로 캐시한다(단일 시세 함수는 변경하지 않는다).
- 추천 모델: `db/models.py` `Recommendation`(trade_date, krx_code, rank, total_score, sentiment/volume/momentum/anomaly_score, reasoning, explanation) — 본 SPEC은 검색·피드백에서 **읽기 전용으로 참조**하며 변경하지 않는다.
- 상세 모달: `frontend/src/components/StockDetail.tsx`(점수 분해·추천 이유·기여 뉴스·면책 표시) — 본 SPEC은 여기에 **가격 차트와 피드백 버튼을 추가**하고, 전체 페이지 라우트로도 재사용한다.
- 추천 API: `api/routes/recommendations.py` `GET /recommendations`·`GET /recommendations/history`·`GET /recommendations/{krx_code}` — 본 SPEC은 그 하위에 `POST|GET /recommendations/{krx_code}/feedback`을 **추가**한다(기존 경로 변경 없음).
- 라우터 구성: `api/routes/`(news, recommendations, sectors) — 본 SPEC은 신규 라우터 `stocks`(검색·가격)를 **추가**한다.
- 응답 스키마: `api/schemas.py` — 신규 스키마(검색·가격·피드백)를 **추가**하며 기존 스키마는 변경하지 않는다.
- API 클라이언트: `frontend/src/api/client.ts`, 타입 `frontend/src/types.ts` — 신규 함수·타입만 추가한다.

---

## 2. 핵심 기능 요구사항 (EARS)

표기 규칙: **WHEN**(이벤트 구동), **WHILE**(상태 구동), **WHERE**(선택적 기능), **IF...THEN**(원치 않는 동작), **SHALL**(보편 요구).

### 2.1 종목 검색 (REQ-SRCH) — Priority High

- **REQ-SRCH-001 (Event)**: **WHEN** `GET /stocks/search?q={질의}`가 호출되면, the 시스템 **SHALL** `krx_master`의 종목명에 대한 부분 일치와 종목코드에 대한 접두 일치를 수행하여 일치하는 종목 목록을 반환한다.
- **REQ-SRCH-002 (Ubiquitous)**: the 시스템 **SHALL** 각 검색 결과 항목에 `krx_code`, `name`(종목명), `in_recommendations`(현재/최근 추천 포함 여부, bool)를 포함한다.
- **REQ-SRCH-003 (Ubiquitous)**: the 시스템 **SHALL** 검색 결과를 상한 개수(기본 20건)로 제한하고, 추천 포함 종목을 우선 노출하도록 정렬한다.
- **REQ-SRCH-004 (Unwanted)**: **IF** `q`가 비었거나 공백만 있거나 최소 길이(1자) 미만이면, **THEN** the 시스템 **SHALL** 빈 결과 목록을 정상 응답(200)으로 반환하고 서버 오류(500)를 발생시키지 않는다.
- **REQ-SRCH-005 (Ubiquitous)**: the 시스템 **SHALL** 검색을 인증 없이 접근 가능한 공개 엔드포인트로 제공한다(기존 `GET /recommendations`와 동일한 접근 정책).

### 2.2 종목 상세 페이지 + 가격 차트 (REQ-PRICE) — Priority High

- **REQ-PRICE-001 (Event)**: **WHEN** `GET /stocks/{krx_code}/prices?days={n}`이 호출되면, the 시스템 **SHALL** `prices.py`를 재사용하여 최근 n일(기본 30, 상한 90)의 일별 가격 시계열(날짜·종가 최소 포함)을 반환한다.
- **REQ-PRICE-002 (State)**: **WHILE** 동일 종목·동일 기간의 가격 시계열이 Redis 캐시에 유효하게 존재하는 동안, the 시스템 **SHALL** FinanceDataReader를 재호출하지 않고 캐시 값을 반환한다.
- **REQ-PRICE-003 (Ubiquitous)**: the 시스템 **SHALL** 가격 조회를 `prices.py`의 executor 격리 패턴(동기 라이브러리를 스레드 풀에서 실행)으로 수행하여 비동기 이벤트 루프를 차단하지 않는다.
- **REQ-PRICE-004 (Event)**: **WHEN** 사용자가 종목 상세(모달 또는 `/stocks/:krxCode` 페이지)를 열면, the 시스템 **SHALL** 기존 점수 분해·추천 이유·기여 뉴스에 더해 30일 가격 라인 차트(Recharts)를 표시한다.
- **REQ-PRICE-005 (Unwanted) [HARD]**: **IF** 가격 시계열 조회가 실패하거나(네트워크·라이브러리 오류·데이터 없음) 빈 시계열을 반환하면, **THEN** the 시스템 **SHALL** 오류를 로그한 뒤 차트 영역에 "가격 데이터를 불러올 수 없습니다" 안내를 표시하고, 상세의 나머지 영역(점수·뉴스·설명·피드백)은 정상 동작시킨다(상세 전체를 실패시키지 않는다).

### 2.3 추천 품질 피드백 (REQ-FB) — Priority Medium

- **REQ-FB-001 (Ubiquitous)**: the 시스템 **SHALL** 종목별 추천 피드백을 저장할 `recommendation_feedback` 테이블(id, krx_code, vote('up'|'down'), user_id(nullable), created_at)을 보유한다.
- **REQ-FB-002 (Event)**: **WHEN** `POST /recommendations/{krx_code}/feedback`이 유효한 `vote`('up' 또는 'down')와 함께 호출되면, the 시스템 **SHALL** 피드백 1건을 저장하고 갱신된 집계(up/down 카운트)를 반환한다.
- **REQ-FB-003 (Event)**: **WHEN** `GET /recommendations/{krx_code}/feedback`이 호출되면, the 시스템 **SHALL** 해당 종목의 피드백 집계(up 카운트, down 카운트)를 반환한다.
- **REQ-FB-004 (Ubiquitous)**: the 시스템 **SHALL** 피드백을 인증 없이(익명) 제출 가능하게 하되(user_id nullable), 추후 사용자 연동을 위해 인증 토큰이 있으면 user_id를 함께 저장한다.
- **REQ-FB-005 (Unwanted)**: **IF** `vote` 값이 'up'/'down'이 아니면, **THEN** the 시스템 **SHALL** 422로 거부하고 데이터를 저장하지 않으며 서버 오류(500)를 발생시키지 않는다.
- **REQ-FB-006 (Event)**: **WHEN** 사용자가 종목 상세에서 좋아요/싫어요 버튼을 누르면, the 시스템 **SHALL** 피드백을 제출하고 갱신된 up/down 카운트를 화면에 반영한다.

### 2.4 프론트엔드 (REQ-FE) — Priority Medium

- **REQ-FE-001 (Ubiquitous)**: the 시스템 **SHALL** 대시보드 상단에 종목 검색 입력 요소를 제공하여 사용자가 종목명/코드로 검색하고 결과 목록을 볼 수 있게 한다.
- **REQ-FE-002 (Event)**: **WHEN** 사용자가 검색 결과 항목을 선택하면, the 시스템 **SHALL** 해당 종목의 상세(모달 또는 `/stocks/:krxCode` 페이지)를 표시한다.
- **REQ-FE-003 (Ubiquitous)**: the 시스템 **SHALL** 딥링크 가능한 라우트 `/stocks/:krxCode`를 제공하여 동일 종목 상세를 전체 페이지로 직접 열 수 있게 한다(기존 `StockDetail` 컴포넌트 재사용).
- **REQ-FE-004 (Ubiquitous)**: the 시스템 **SHALL** 종목 상세에 가격 라인 차트와 좋아요/싫어요 버튼·카운트를 렌더링한다.
- **REQ-FE-005 (Unwanted)**: **IF** 검색·가격·피드백 조회 요청이 실패하면, **THEN** the 시스템 **SHALL** 해당 영역에 오류 메시지를 표시하고 직전 표시 상태를 유지하며 페이지 전체를 깨뜨리지 않는다.
- **REQ-FE-006 (Ubiquitous)**: the 시스템 **SHALL** 모바일(<768px)에서도 검색 입력·가격 차트·피드백 버튼이 사용 가능하도록 기존 반응형 패턴을 따른다.

### 2.5 비기능 요구사항 (REQ-NFR)

- **REQ-NFR-001 (Ubiquitous)**: the 시스템 **SHALL** 가격 시계열을 Redis로 캐시하여(종목·기간별 키) FinanceDataReader 호출 빈도를 줄이고, 캐시 만료 정책을 둔다(예: 당일 종가 갱신 주기에 맞춤).
- **REQ-NFR-002 (Ubiquitous) [HARD]**: the 시스템 **SHALL** FinanceDataReader·검색·피드백 기능의 가용성과 무관하게 모든 기존 기능(SPEC-STOCK-001~006)을 동작시킨다.
- **REQ-NFR-003 (Ubiquitous)**: the 시스템 **SHALL** 신규 테이블(`recommendation_feedback`)을 Alembic 마이그레이션 `0010`으로 추가하며, 기존 테이블·데이터에 영향을 주지 않는다.
- **REQ-NFR-004 (Ubiquitous)**: the 시스템 **SHALL** 신규 응답 스키마(검색·가격·피드백)와 신규 엔드포인트를 추가 전용으로 정의하여 기존 프론트·클라이언트 하위 호환을 보장한다.
- **REQ-NFR-005 (Ubiquitous)**: the 시스템 **SHALL** 검색·가격·피드백의 호출·성공·실패를 구조화 로그로 남기되, 시크릿·민감정보를 로그에 포함하지 않는다.

---

## 3. 면책 및 안전 (Disclaimer & Safety)

- **REQ-SAFE-001 (Ubiquitous) [HARD]**: the 시스템 **SHALL** 종목 상세 페이지·가격 차트·피드백을 포함한 모든 추천 표시 영역에 기존 투자 책임 면책 고지(`Disclaimer`)를 유지한다.
- **REQ-SAFE-002 (Unwanted) [HARD]**: **IF** 어떤 기능이 매수/매도 주문, 자동 매매, 수익 보장을 시도하면, **THEN** the 시스템 **SHALL** 이를 거부한다(영구 제외, §4 참조).

---

## 4. Exclusions (What NOT to Build)

본 SPEC 범위에서 **명시적으로 제외**하는 항목이다.

- **자동 매매·주문 실행 (영구 제외)**: 어떤 형태의 실제 매수/매도 주문, 증권사 API 연동, 자동 매매 로직도 구현하지 않는다. 본 시스템은 정보 제공 도구로만 유지된다.
- **피드백 기반 추천 점수 재가중(re-weighting)**: 본 SPEC은 피드백을 **수집·집계·표시**만 한다. 좋아요/싫어요를 추천 점수 산식에 반영하는 가중 로직은 범위 밖이며, 향후 별도 SPEC에서 데이터가 충분히 쌓인 뒤 다룬다.
- **실시간 가격 차트 스트리밍**: 상세 화면 차트는 캐시된 일별 종가 스냅샷을 표시한다. WebSocket 기반 실시간 틱 차트는 범위 밖이다(SPEC-STOCK-003 실시간 배지와 분리).
- **기술적 지표(이동평균·RSI·볼린저밴드 등)**: 차트는 단순 종가 라인만 표시한다. 보조 지표 오버레이는 범위 밖이다.
- **검색 자동완성·퍼지 매칭·랭킹 고도화**: 검색은 종목명 부분 일치 + 코드 접두 일치 + 단순 정렬만 제공한다. 타이핑 자동완성 드롭다운, 오타 보정, 형태소 기반 랭킹은 범위 밖이다.
- **피드백 다중 투표 방지/계정 고유 제약**: 익명 제출을 허용하므로 1인 1표를 강제하지 않는다. 어뷰징 방지(레이트리밋·중복 차단)는 범위 밖이다.
- **종목 마스터 데이터 자동 갱신**: 검색은 기존 `krx_master.csv` 픽스처를 사용한다. 마스터 데이터의 외부 자동 동기화는 범위 밖이다.
- **다국어화**: 검색·차트·피드백 UI는 한국어만 다룬다.

---

## 5. 설계 결정 (Design Decisions)

### 5.1 신규 라우터 분리 (`stocks`)
- 검색·가격은 추천과 의미가 다르므로 신규 라우터 `api/routes/stocks.py`(prefix `/stocks`)에 둔다. 이로써 기존 `/recommendations/{krx_code}` 경로와 충돌하지 않는다.
- 피드백은 추천에 종속되므로 기존 추천 라우터 하위(`/recommendations/{krx_code}/feedback`)에 둔다. 세그먼트가 더 깊어 기존 `/recommendations/{krx_code}` GET과 경로 충돌이 없다.

### 5.2 가격 시계열 함수 추가 (단일 시세 함수 보존)
- `prices.py`에 `get_stock_price_history(krx_code, days)`를 신규 추가한다. 기존 `get_stock_price_data()`(추천 파이프라인이 의존)는 변경하지 않는다. 30일 df를 이미 가져오므로 동일 패턴을 재사용해 시계열로 반환한다.
- Redis 캐시 키: `stock_prices:{krx_code}:{days}`. 만료는 시세 갱신 주기에 맞춘다.

### 5.3 피드백 데이터 모델
- `recommendation_feedback`(id PK, krx_code String(10), vote String(4) — 'up'/'down', user_id Integer nullable FK→users, created_at). 익명 허용을 위해 user_id nullable.
- 집계는 `vote`별 COUNT 쿼리로 산출한다(머티리얼라이즈드 카운터 미사용 — 데이터량 적음).

### 5.4 검색 데이터 소스 및 정렬
- 종목명/코드 매칭은 `load_krx_master()` 결과(메모리 dict)에서 수행한다. `in_recommendations`는 최근 추천(`recommendations` 테이블) 종목 집합 포함 여부로 판단한다.
- 정렬: 추천 포함 종목 우선 → 종목명 사전순. 상한 20건.

### 5.5 신규 마이그레이션
- Alembic `0010_recommendation_feedback`: `recommendation_feedback` 테이블 생성. 다운그레이드는 테이블 drop.

### 5.6 프론트 상세 재사용
- `StockDetail`은 모달/페이지 양쪽에서 재사용한다. 신규 라우트 `/stocks/:krxCode`는 동일 컴포넌트를 전체 페이지 레이아웃으로 감싸 렌더링한다. 모달 사용처(Dashboard)는 변경 없이 동작한다.
- 차트·피드백은 `StockDetail` 내부에 추가하되, 가격 조회 실패는 차트 영역에만 국한한다(REQ-PRICE-005).

---

## 6. 수용 기준 요약

상세 Given-When-Then 시나리오는 `acceptance.md`를 따른다. 핵심 게이트:

- `GET /stocks/search?q=`가 종목명 부분 일치·코드 접두 일치 결과를 추천 포함 여부와 함께 반환하고, 빈/짧은 질의를 안전하게 처리한다.
- `GET /stocks/{krx_code}/prices`가 캐시 우선으로 30일 시계열을 반환하고, 조회 실패 시에도 상세의 나머지 영역은 정상 동작한다.
- `POST|GET /recommendations/{krx_code}/feedback`이 좋아요/싫어요를 저장·집계하며, 잘못된 vote를 422로 거부한다.
- 프론트에서 검색→상세→피드백 흐름이 동작하고, `/stocks/:krxCode` 딥링크가 상세를 전체 페이지로 연다.
- 신규 테이블은 마이그레이션 `0010`으로 추가되고, 신규 엔드포인트·스키마는 추가 전용으로 하위 호환을 유지하며, 자동 매매·피드백 재가중은 제공되지 않는다.
