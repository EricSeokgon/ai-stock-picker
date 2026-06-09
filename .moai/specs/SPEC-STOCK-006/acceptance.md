# Acceptance Criteria
SPEC: SPEC-STOCK-006

표기: Given(전제) / When(행위) / Then(기대 결과). 각 시나리오는 §2 EARS 요구사항에 매핑된다.

---

## Phase A — 추천 근거 설명 (REQ-EXPL)

### AC-A1 (REQ-EXPL-001, REQ-NFR-003): explanation 컬럼 추가
- **Given** Alembic 마이그레이션 `0009`가 적용된 데이터베이스에서
- **When** `recommendations` 테이블 스키마를 조회하면
- **Then** `explanation` 컬럼(Text, nullable)이 존재하고, 기존 `reasoning` 컬럼은 그대로 보존되며, 기존 행은 `explanation`이 null이다.

### AC-A2 (REQ-EXPL-002, REQ-EXPL-004): explanation 생성·저장
- **Given** 특정 종목의 점수 분해와 집계된 대표 뉴스 요약이 있을 때
- **When** 추천 파이프라인이 해당 종목 추천을 산출하면
- **Then** Claude(`claude-haiku-4-5`)가 한국어 2~3문장의 근거 텍스트를 생성하여 `explanation`에 저장한다.

### AC-A3 (REQ-EXPL-003): API 응답 노출
- **Given** `explanation`이 채워진 추천이 캐시/DB에 존재할 때
- **When** `GET /recommendations` 또는 `GET /recommendations/{krx_code}`를 호출하면
- **Then** 응답 항목에 `explanation` 필드가 포함되어 반환된다(미생성 시 null/빈 문자열).

### AC-A4 (REQ-EXPL-005) [HARD]: Claude 실패 폴백
- **Given** Claude 호출이 실패(네트워크/한도/타임아웃)하거나 빈 응답을 반환하는 상황에서
- **When** 추천 파이프라인이 실행되면
- **Then** 오류가 로그되고 `explanation`은 비워지거나 `reasoning`으로 대체되며, 점수 계산·추천 적재는 정상 완료되어 파이프라인이 중단되지 않는다.

### AC-A5 (REQ-EXPL-006): 권유성 표현 금지
- **Given** 설명 생성 프롬프트에 매수/매도 지시·수익 보장 금지 지침이 포함된 상태에서
- **When** explanation을 생성하면
- **Then** 생성된 텍스트는 "정보 제공·근거 설명" 범위의 중립적 서술이며, 매수/매도 권유나 수익 보장 표현을 포함하지 않는다.

---

## Phase B — 추천 히스토리 조회 (REQ-HIST)

### AC-B1 (REQ-HIST-001, REQ-HIST-002): 날짜별 그룹화 조회
- **Given** 최근 여러 날짜에 걸친 추천 기록이 `recommendations`에 존재할 때
- **When** `GET /recommendations/history?days=7`을 호출하면
- **Then** 최근 7일치 추천이 `trade_date` 기준으로 그룹화되어 최신 날짜 우선으로 반환되며, 각 날짜 그룹은 종목·rank·total_score·explanation을 포함한다.

### AC-B2 (REQ-HIST-001): 기본값 동작
- **Given** `days` 파라미터 없이
- **When** `GET /recommendations/history`를 호출하면
- **Then** 기본값 7일이 적용되어 최근 7일치 히스토리가 반환된다.

### AC-B3 (REQ-HIST-003): 잘못된 파라미터 처리
- **Given** `days=-1`, `days=0`, `days=abc`, `days=99999` 같은 유효하지 않은 값이 전달될 때
- **When** 히스토리를 조회하면
- **Then** 422로 거부되거나 안전한 기본/상한값(1~90)으로 보정되며, 서버 오류(500)는 발생하지 않는다.

### AC-B4 (REQ-HIST-004): 빈 기간
- **Given** 해당 기간에 추천 기록이 없을 때
- **When** 히스토리를 조회하면
- **Then** `history: []`(빈 그룹 목록)이 정상 응답(200)으로 반환된다.

### AC-B5 (REQ-HIST-005, REQ-FE-002, REQ-FE-003): 프론트 히스토리 페이지
- **Given** 히스토리 페이지가 렌더링된 상태에서
- **When** 사용자가 기간(7/14/30일)을 변경하면
- **Then** `days` 파라미터가 반영되어 목록이 재조회·갱신되고, 날짜별 그룹으로 표시되며, 면책 고지가 노출된다.

---

## Phase C — 뉴스 감성 상세화 (REQ-SENT)

### AC-C1 (REQ-SENT-001, REQ-NFR-003): sentiment_label 컬럼 추가
- **Given** 마이그레이션 `0009`가 적용된 데이터베이스에서
- **When** `analysis_results` 테이블 스키마를 조회하면
- **Then** `sentiment_label` 컬럼(String(20), nullable)이 존재하고, 기존 `sentiment`·`sentiment_score`는 보존된다.

### AC-C2 (REQ-SENT-002): 5단계 매핑·저장
- **Given** `sentiment_score`가 각각 0.7 / 0.3 / 0.0 / -0.3 / -0.7인 분석 결과가 저장될 때
- **When** 감성 라벨 매핑이 적용되면
- **Then** `sentiment_label`이 각각 매우긍정 / 긍정 / 중립 / 부정 / 매우부정으로 저장된다(경계값은 §5.4 기준).

### AC-C3 (REQ-SENT-003): 뉴스 API 노출
- **Given** `sentiment_label`이 채워진 분석 결과가 있을 때
- **When** `GET /news`를 호출하면
- **Then** 각 뉴스 항목에 `sentiment_label` 필드가 포함되어 반환된다(미생성 시 null).

### AC-C4 (REQ-SENT-004, REQ-SENT-005): 기존 sentiment 보존·null 처리
- **Given** `sentiment_score`가 null이거나 매핑 불가한 분석 결과에서
- **When** 뉴스를 조회하면
- **Then** `sentiment_label`은 null로 반환되고, 기존 `sentiment`(`positive/negative/neutral`) 필드와 표시 동작은 그대로 유지된다.

### AC-C5 (REQ-FE-004): 프론트 감성 배지
- **Given** 뉴스 피드가 렌더링된 상태에서
- **When** `sentiment_label`이 있는 뉴스를 표시하면
- **Then** 5단계 라벨 배지가 표시되고, 라벨이 없으면 기존 `sentiment` 배지가 표시된다.

---

## 횡단 — 하위 호환·안전 (REQ-NFR, REQ-SAFE)

### AC-X1 (REQ-NFR-002, REQ-NFR-004) [HARD]: 하위 호환
- **Given** 신규 필드(`explanation`, `sentiment_label`)를 사용하지 않는 기존 클라이언트가
- **When** `GET /recommendations`·`GET /news`를 호출하면
- **Then** 기존 응답 구조가 유지되어 정상 동작하며, SPEC-STOCK-001~005의 모든 기능이 영향받지 않는다.

### AC-X2 (REQ-NFR-001): 구조화 로그
- **Given** explanation 생성이 호출·성공·실패·폴백되는 상황에서
- **When** 로그를 확인하면
- **Then** 각 단계가 구조화 로그로 기록되며, API 키 등 시크릿은 로그에 포함되지 않는다.

### AC-X3 (REQ-SAFE-001, REQ-SAFE-002) [HARD]: 면책·자동매매 제외
- **Given** explanation·히스토리·뉴스 화면에서
- **When** 추천/근거가 표시되면
- **Then** 투자 책임 면책 고지가 유지되고, 어떤 화면에서도 매수/매도 주문·자동 매매·수익 보장 기능이 제공되지 않는다.

---

## Definition of Done

- [ ] 마이그레이션 `0009` 적용·롤백 검증, ORM 모델 동기화
- [ ] explanation 생성·저장·노출, Claude 실패 폴백 무중단(AC-A4) 검증
- [ ] `GET /recommendations/history` 정상/빈/잘못된 days 처리(AC-B1~B4)
- [ ] sentiment_label 5단계 매핑·노출·null 처리(AC-C2~C4)
- [ ] 프론트: 종목 카드 explanation, 히스토리 페이지, 뉴스 감성 배지
- [ ] 하위 호환(AC-X1)·면책 유지(AC-X3) 검증
- [ ] 신규 코드 단위·통합 테스트, 커버리지 ≥ 85% (quality.yaml 기준)
- [ ] TRUST 5 게이트 통과, 자동 매매 영구 제외 확인
