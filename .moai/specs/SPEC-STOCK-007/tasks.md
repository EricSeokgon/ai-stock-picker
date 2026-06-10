# SPEC-STOCK-007 — 작업 분해 (Tasks)

Phase 8: 종목 검색 · 상세 페이지 · 추천 품질 피드백

작업 ID 규칙: TASK-001 ~ TASK-014. 의존성은 "선행" 컬럼으로 표기한다. 백엔드 → 프론트 순으로 진행하되, 도메인이 독립적인 작업은 병렬 가능하다.

---

## 백엔드 — 데이터 모델 & 마이그레이션

### TASK-001: 피드백 모델 + 마이그레이션 0010
- 대상: `backend/src/stock_picker/db/models.py`, `backend/alembic/versions/0010_recommendation_feedback.py`
- 내용: `RecommendationFeedback` ORM 모델(id PK, krx_code String(10), vote String(4), user_id Integer nullable FK→users, created_at) 추가. Alembic `0010` 업/다운 마이그레이션 작성(업: 테이블 생성, 다운: drop).
- 충족 요구사항: REQ-FB-001, REQ-NFR-003
- 선행: 없음

## 백엔드 — 검색 (REQ-SRCH)

### TASK-002: 검색 서비스 로직
- 대상: `backend/src/stock_picker/search/service.py`(신규 모듈)
- 내용: `load_krx_master()` 결과 dict에서 종목명 부분 일치 + 코드 접두 일치 매칭. 최근 추천 종목 집합 조회 후 `in_recommendations` 부여. 추천 포함 우선 → 종목명 사전순 정렬, 상한 20건. 빈/짧은 질의는 빈 목록 반환.
- 충족 요구사항: REQ-SRCH-001, REQ-SRCH-002, REQ-SRCH-003, REQ-SRCH-004
- 선행: 없음

### TASK-003: stocks 라우터 + 검색 엔드포인트 + 스키마
- 대상: `backend/src/stock_picker/api/routes/stocks.py`(신규), `backend/src/stock_picker/api/schemas.py`, `backend/src/stock_picker/api/main.py`(라우터 등록)
- 내용: `GET /stocks/search?q=` 엔드포인트(공개). `StockSearchItem`, `StockSearchResponse` 스키마 추가. main.py에 `stocks` 라우터 include.
- 충족 요구사항: REQ-SRCH-001, REQ-SRCH-005, REQ-NFR-004
- 선행: TASK-002

## 백엔드 — 가격 시계열 (REQ-PRICE)

### TASK-004: 가격 시계열 함수 + 캐시
- 대상: `backend/src/stock_picker/mapping/prices.py`
- 내용: `get_stock_price_history(krx_code, days)` 신규 추가(기존 `get_stock_price_data()` 변경 금지). executor 격리로 FinanceDataReader 30일 df → 일별 (date, close) 시계열 반환. Redis 캐시 키 `stock_prices:{krx_code}:{days}`. 실패 시 빈 시계열/None 반환(예외 전파 금지).
- 충족 요구사항: REQ-PRICE-001, REQ-PRICE-002, REQ-PRICE-003, REQ-PRICE-005, REQ-NFR-001
- 선행: 없음

### TASK-005: 가격 엔드포인트 + 스키마
- 대상: `backend/src/stock_picker/api/routes/stocks.py`, `backend/src/stock_picker/api/schemas.py`
- 내용: `GET /stocks/{krx_code}/prices?days=30`(상한 90) 엔드포인트. `PricePoint`, `StockPricesResponse` 스키마. 조회 실패 시 빈 시계열 + 안내 가능한 플래그/메시지 반환(200 유지).
- 충족 요구사항: REQ-PRICE-001, REQ-PRICE-005, REQ-NFR-004
- 선행: TASK-004, TASK-003(라우터 존재)

## 백엔드 — 피드백 (REQ-FB)

### TASK-006: 피드백 서비스 로직
- 대상: `backend/src/stock_picker/feedback/service.py`(신규 모듈)
- 내용: 피드백 1건 저장(krx_code, vote, optional user_id), 종목별 up/down 집계 COUNT 쿼리. vote 검증('up'/'down').
- 충족 요구사항: REQ-FB-002, REQ-FB-003, REQ-FB-004, REQ-FB-005
- 선행: TASK-001

### TASK-007: 피드백 엔드포인트 + 스키마
- 대상: `backend/src/stock_picker/api/routes/recommendations.py`, `backend/src/stock_picker/api/schemas.py`
- 내용: `POST /recommendations/{krx_code}/feedback`(body: vote), `GET /recommendations/{krx_code}/feedback`(집계 반환). `FeedbackVoteRequest`, `FeedbackSummaryResponse` 스키마. 인증 선택적(토큰 있으면 user_id 추출). 잘못된 vote는 422.
- 충족 요구사항: REQ-FB-002, REQ-FB-003, REQ-FB-005, REQ-FB-006, REQ-NFR-004
- 선행: TASK-006

## 백엔드 — 테스트

### TASK-008: 검색 테스트
- 대상: `backend/tests/unit/test_search_service.py`, `backend/tests/integration/test_stocks_router.py`(검색 부분)
- 내용: 부분/접두 일치, in_recommendations 부여, 정렬·상한, 빈/짧은 질의 안전 처리.
- 충족 요구사항: REQ-SRCH-001~005
- 선행: TASK-003

### TASK-009: 가격 시계열 테스트
- 대상: `backend/tests/unit/test_prices_history.py`, `backend/tests/integration/test_stocks_router.py`(가격 부분)
- 내용: FinanceDataReader mock으로 시계열 반환, 캐시 히트 시 재호출 없음, 조회 실패 시 200 + 빈 시계열, days 상한 보정.
- 충족 요구사항: REQ-PRICE-001~005, REQ-NFR-001
- 선행: TASK-005

### TASK-010: 피드백 테스트
- 대상: `backend/tests/unit/test_feedback_service.py`, `backend/tests/integration/test_feedback_router.py`
- 내용: up/down 저장·집계, 익명/인증 케이스, 잘못된 vote 422, 빈 집계 0/0 반환.
- 충족 요구사항: REQ-FB-001~006
- 선행: TASK-007

## 프론트엔드

### TASK-011: 검색 컴포넌트 + API 클라이언트/타입
- 대상: `frontend/src/components/StockSearchBar.tsx`(신규), `frontend/src/api/client.ts`, `frontend/src/types.ts`, `frontend/src/App.tsx`(대시보드 상단 배치)
- 내용: 검색 입력 + 결과 목록. `searchStocks(q)` 클라이언트 함수, `StockSearchItem` 타입. 결과 선택 시 상세(모달 또는 라우트) 열기. 모바일 반응형. 조회 실패 시 영역 내 오류 표시.
- 충족 요구사항: REQ-FE-001, REQ-FE-002, REQ-FE-005, REQ-FE-006
- 선행: TASK-003

### TASK-012: 가격 차트 (Recharts) + StockDetail 통합
- 대상: `frontend/src/components/PriceChart.tsx`(신규), `frontend/src/components/StockDetail.tsx`, `frontend/src/api/client.ts`, `frontend/src/types.ts`
- 내용: `fetchStockPrices(krxCode, days)` 클라이언트 함수 + 타입. Recharts LineChart로 30일 종가 표시. `StockDetail`에 차트 영역 추가. 가격 실패 시 차트 영역에만 안내, 나머지 영역 보존(REQ-PRICE-005).
- 충족 요구사항: REQ-PRICE-004, REQ-PRICE-005, REQ-FE-004, REQ-FE-005, REQ-FE-006
- 선행: TASK-005

### TASK-013: 피드백 버튼 + 종목 상세 라우트 페이지
- 대상: `frontend/src/components/FeedbackButtons.tsx`(신규), `frontend/src/pages/StockDetailPage.tsx`(신규), `frontend/src/components/StockDetail.tsx`, `frontend/src/api/client.ts`, `frontend/src/types.ts`, `frontend/src/App.tsx`(라우트 `/stocks/:krxCode` 추가)
- 내용: 좋아요/싫어요 버튼 + 카운트. `submitFeedback`, `fetchFeedbackSummary` 클라이언트 함수 + 타입. `StockDetail`에 피드백 영역 추가. `/stocks/:krxCode` 라우트가 `StockDetail`을 전체 페이지로 렌더링(기존 모달 사용처 보존). 면책 고지 유지.
- 충족 요구사항: REQ-FB-006, REQ-FE-003, REQ-FE-004, REQ-FE-005, REQ-SAFE-001
- 선행: TASK-007, TASK-012

### TASK-014: 프론트 테스트
- 대상: `frontend/src/components/__tests__/`(검색·차트·피드백·상세 페이지)
- 내용: 검색 입력→결과→선택, 차트 렌더 및 실패 시 안내, 피드백 제출→카운트 갱신, `/stocks/:krxCode` 라우트 렌더, 면책 고지 표시.
- 충족 요구사항: REQ-FE-001~006, REQ-SAFE-001
- 선행: TASK-011, TASK-012, TASK-013

---

## 요구사항 ↔ 작업 추적 매트릭스

| 요구사항 | 작업 |
|---------|------|
| REQ-SRCH-001~005 | TASK-002, TASK-003, TASK-008 |
| REQ-PRICE-001~005 | TASK-004, TASK-005, TASK-009, TASK-012 |
| REQ-FB-001~006 | TASK-001, TASK-006, TASK-007, TASK-010, TASK-013 |
| REQ-FE-001~006 | TASK-011, TASK-012, TASK-013, TASK-014 |
| REQ-NFR-001~005 | TASK-003, TASK-004, TASK-005, TASK-007, TASK-009 |
| REQ-SAFE-001~002 | TASK-013, TASK-014 (영구 제외 — 신규 구현 없음) |
