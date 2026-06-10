# SPEC-STOCK-007 — 수용 기준 (Acceptance Criteria)

Phase 8: 종목 검색 · 상세 페이지 · 추천 품질 피드백

형식: Given-When-Then. 각 시나리오는 대응 요구사항(REQ-*)을 명시한다. AC 번호는 테스트·추적에 사용한다.

---

## A. 종목 검색 (REQ-SRCH)

### AC-1: 종목명 부분 일치 검색
- **Given** `krx_master`에 "삼성전자"(005930), "삼성SDI"(006400)가 존재하고
- **When** `GET /stocks/search?q=삼성`을 호출하면
- **Then** 응답 200이며 결과 목록에 005930·006400이 포함되고, 각 항목에 `krx_code`·`name`·`in_recommendations`(bool)가 존재한다.

### AC-2: 종목코드 접두 일치 검색
- **Given** "005930" 종목이 존재하고
- **When** `GET /stocks/search?q=0059`를 호출하면
- **Then** 응답 200이며 결과에 005930이 포함된다.

### AC-3: 추천 포함 종목 우선 정렬 + 상한
- **Given** 매칭 종목 중 일부가 최근 추천 목록에 포함되어 있고 매칭 종목이 20건을 초과하며
- **When** 검색을 호출하면
- **Then** `in_recommendations=true` 종목이 먼저 정렬되어 나오고, 결과는 최대 20건으로 제한된다.

### AC-4: 빈/짧은 질의 안전 처리
- **Given** 시스템이 정상 동작 중이고
- **When** `GET /stocks/search?q=`(빈 값) 또는 `q=`(공백만)으로 호출하면
- **Then** 응답 200이며 결과 목록은 빈 배열(`[]`)이고 서버 오류(500)가 발생하지 않는다.

### AC-5: 공개 접근
- **Given** 인증 토큰이 없는 클라이언트가
- **When** `GET /stocks/search?q=삼성`을 호출하면
- **Then** 401/403 없이 정상 200 응답을 받는다. (REQ-SRCH-005)

---

## B. 가격 시계열 + 상세 차트 (REQ-PRICE)

### AC-6: 30일 가격 시계열 반환
- **Given** FinanceDataReader가 005930의 30일 데이터를 제공하고
- **When** `GET /stocks/005930/prices?days=30`을 호출하면
- **Then** 응답 200이며 날짜·종가를 포함한 일별 시계열 목록이 반환된다.

### AC-7: 캐시 히트 시 재호출 없음
- **Given** 동일 종목·기간의 가격 시계열이 직전 호출로 Redis에 캐시되어 있고
- **When** 동일 `GET /stocks/005930/prices?days=30`을 다시 호출하면
- **Then** FinanceDataReader를 재호출하지 않고(캐시된 값 사용) 동일 결과를 반환한다. (REQ-PRICE-002)

### AC-8: days 상한 보정
- **Given** 시스템이 정상 동작 중이고
- **When** `GET /stocks/005930/prices?days=9999`을 호출하면
- **Then** 응답 200이며 기간이 상한(90일)으로 보정되어 처리되고 서버 오류가 발생하지 않는다.

### AC-9: 가격 조회 실패 시 상세 보존 [HARD]
- **Given** FinanceDataReader 조회가 실패하거나 빈 데이터를 반환하고
- **When** 사용자가 종목 상세를 열면
- **Then** 가격 차트 영역에는 "가격 데이터를 불러올 수 없습니다" 안내가 표시되지만, 점수 분해·추천 이유·기여 뉴스·피드백 영역은 정상 표시되고 상세 전체가 깨지지 않는다. (REQ-PRICE-005)

### AC-10: 상세에 가격 차트 렌더
- **Given** 가격 시계열 조회가 성공하고
- **When** 사용자가 종목 상세(모달 또는 `/stocks/:krxCode` 페이지)를 열면
- **Then** 30일 종가 라인 차트(Recharts)가 점수·뉴스·설명과 함께 렌더링된다. (REQ-PRICE-004, REQ-FE-004)

---

## C. 추천 품질 피드백 (REQ-FB)

### AC-11: 좋아요/싫어요 저장 및 집계 반환
- **Given** 005930에 대한 기존 피드백이 up=0, down=0이고
- **When** `POST /recommendations/005930/feedback` body `{"vote":"up"}`을 호출하면
- **Then** 응답이 성공이며 갱신된 집계 `{up:1, down:0}`을 반환하고, `recommendation_feedback`에 1건이 저장된다.

### AC-12: 피드백 집계 조회
- **Given** 005930에 up=2, down=1 피드백이 저장되어 있고
- **When** `GET /recommendations/005930/feedback`을 호출하면
- **Then** 응답 200이며 `{up:2, down:1}`을 반환한다.

### AC-13: 잘못된 vote 거부
- **Given** 시스템이 정상 동작 중이고
- **When** `POST /recommendations/005930/feedback` body `{"vote":"maybe"}`을 호출하면
- **Then** 응답 422이며 데이터가 저장되지 않고 서버 오류(500)가 발생하지 않는다. (REQ-FB-005)

### AC-14: 익명 제출 허용
- **Given** 인증 토큰이 없는 클라이언트가
- **When** `POST /recommendations/005930/feedback` body `{"vote":"down"}`을 호출하면
- **Then** 피드백이 user_id=NULL로 저장되고 집계가 갱신된다. (REQ-FB-004)

### AC-15: 빈 집계 기본값
- **Given** 005930에 대한 피드백이 한 건도 없고
- **When** `GET /recommendations/005930/feedback`을 호출하면
- **Then** 응답 200이며 `{up:0, down:0}`을 반환한다.

---

## D. 프론트엔드 흐름 (REQ-FE)

### AC-16: 대시보드 검색 입력
- **Given** 사용자가 대시보드를 열고
- **When** 검색 입력에 "삼성"을 입력하면
- **Then** 일치하는 종목 결과 목록이 표시된다. (REQ-FE-001)

### AC-17: 검색 결과 선택 → 상세 표시
- **Given** 검색 결과 목록이 표시되어 있고
- **When** 사용자가 한 항목을 선택하면
- **Then** 해당 종목의 상세(모달 또는 `/stocks/:krxCode` 페이지)가 열린다. (REQ-FE-002)

### AC-18: 딥링크 라우트
- **Given** 사용자가 브라우저에서 `/stocks/005930` URL로 직접 접근하고
- **When** 페이지가 로드되면
- **Then** 005930 종목 상세가 전체 페이지로 렌더링되며 기존 `StockDetail` 영역(점수·뉴스·설명·차트·피드백·면책)이 표시된다. (REQ-FE-003)

### AC-19: 피드백 버튼 상호작용
- **Given** 종목 상세에 좋아요/싫어요 버튼과 현재 카운트가 표시되어 있고
- **When** 사용자가 좋아요를 누르면
- **Then** 피드백이 제출되고 좋아요 카운트가 1 증가하여 화면에 반영된다. (REQ-FB-006, REQ-FE-004)

### AC-20: 조회 실패 시 영역 격리
- **Given** 검색·가격·피드백 중 한 요청이 실패하고
- **When** 사용자가 해당 기능을 사용하면
- **Then** 해당 영역에만 오류 메시지가 표시되고 직전 표시 상태와 페이지의 나머지 영역은 유지된다. (REQ-FE-005)

### AC-21: 모바일 반응형
- **Given** 화면 폭이 768px 미만이고
- **When** 사용자가 검색·상세·피드백을 사용하면
- **Then** 검색 입력·가격 차트·피드백 버튼이 모바일 레이아웃에서 사용 가능하게 표시된다. (REQ-FE-006)

---

## E. 면책 · 안전 · 하위 호환 (REQ-SAFE / REQ-NFR)

### AC-22: 면책 고지 유지 [HARD]
- **Given** 종목 상세 페이지·차트·피드백이 표시되고
- **When** 사용자가 화면을 보면
- **Then** 기존 투자 책임 면책 고지(`Disclaimer`)가 표시된다. (REQ-SAFE-001)

### AC-23: 자동 매매 부재 [HARD]
- **Given** 본 SPEC의 모든 신규 기능이 구현된 상태에서
- **When** UI·API 전반을 점검하면
- **Then** 어떤 매수/매도 주문·자동 매매·수익 보장 기능도 존재하지 않는다. (REQ-SAFE-002, spec.md §4)

### AC-24: 하위 호환 — 기존 동작 보존
- **Given** SPEC-STOCK-001~006의 기존 엔드포인트·화면(추천 목록·히스토리·상세 모달·뉴스·섹터·포트폴리오 등)이 있고
- **When** 본 SPEC 구현 후 기존 기능을 호출/사용하면
- **Then** 기존 동작이 변경 없이 정상 작동하며, `prices.py`의 `get_stock_price_data()`도 그대로 동작한다. (REQ-NFR-002, REQ-NFR-004)

### AC-25: 마이그레이션 적용
- **Given** 마이그레이션 `0009`까지 적용된 DB에서
- **When** Alembic `upgrade head`를 실행하면
- **Then** `recommendation_feedback` 테이블이 생성되고 기존 테이블·데이터에 영향이 없으며, `downgrade`로 해당 테이블만 제거된다. (REQ-NFR-003)

---

## Definition of Done

- [ ] AC-1~AC-25 전부 통과
- [ ] 신규 백엔드 코드 테스트 커버리지 ≥ 85% (검색·가격·피드백 서비스/라우터)
- [ ] 신규 프론트 컴포넌트(검색·차트·피드백·상세 페이지) 테스트 통과
- [ ] 기존 SPEC-STOCK-001~006 테스트 전부 그린(회귀 없음)
- [ ] Alembic `0010` 업/다운 마이그레이션 검증
- [ ] 자동 매매·피드백 재가중 미구현 확인(spec.md §4 Exclusions 준수)
- [ ] 모든 추천 표시 영역에 면책 고지 유지
