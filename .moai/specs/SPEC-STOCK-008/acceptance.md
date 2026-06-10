# SPEC-STOCK-008 인수 기준 (Acceptance Criteria)

Given-When-Then 형식. 각 시나리오는 관련 REQ 및 TASK와 연결된다.

---

## AC-1: 분석 완료 시 섹터 집계 적재 (REQ-SEC-001, REQ-SEC-002)

- **Given** 특정 거래일에 `sector_tags`와 `sentiment_score`를 가진 `AnalysisResult` 행이 여러 건
  존재하고
- **When** 일일 파이프라인의 분석 단계가 완료되어 섹터 집계가 실행되면
- **Then** `sector_trends` 테이블에 해당 거래일의 각 섹터별로 `news_volume`, `avg_sentiment`,
  `trend_score`가 채워진 행이 생성된다.

---

## AC-2: 다중 섹터 태깅 처리 (REQ-SEC-002)

- **Given** 한 기사의 `AnalysisResult.sector_tags`가 2개 이상의 섹터를 포함하고
- **When** 섹터 집계가 실행되면
- **Then** 해당 기사는 각 섹터의 `news_volume`에 모두 카운트되고, 각 섹터의 `avg_sentiment`
  계산에 반영된다.

---

## AC-3: 장중 재실행 시 upsert (중복 방지) (REQ-SEC-003)

- **Given** 특정 거래일·특정 섹터의 집계 행이 이미 존재하고
- **When** 장중 30분 증분 파이프라인이 같은 거래일에 대해 섹터 집계를 재실행하면
- **Then** 기존 행이 최신 값으로 갱신되며, 동일 `(sector, trade_date)` 조합의 중복 행이 생성되지
  않는다.

---

## AC-4: 분석 결과 없음 처리 (REQ-SEC-004)

- **Given** 특정 거래일에 분석된 기사가 한 건도 없고
- **When** 섹터 집계가 실행되면
- **Then** 해당 거래일에 대한 `sector_trends` 행이 생성되지 않으며, 파이프라인은 오류 없이
  다음 단계로 진행한다.

---

## AC-5: 집계 실패가 추천을 막지 않음 (REQ-SEC-005)

- **Given** 섹터 집계 단계에서 예외가 발생하는 상황
- **When** 일일/장중 파이프라인이 실행되면
- **Then** 오류가 로깅되고, 추천 생성 단계는 정상적으로 계속 실행되어 추천 결과가 산출된다.

---

## AC-6: 집계 후 캐시 무효화 (REQ-SEC-006)

- **Given** `sector_trends:{days}` Redis 캐시에 이전(구) 데이터가 존재하고
- **When** 섹터 집계가 완료되면
- **Then** 해당 캐시가 무효화되어, 다음 `GET /sectors/trends` 호출이 최신 DB 데이터를 반영한다.

---

## AC-7: 섹터 순위 조회 (REQ-SEC-010, REQ-SEC-011)

- **Given** 최신 거래일의 섹터 집계 데이터가 존재하고
- **When** 클라이언트가 `GET /sectors/ranking?sort=score&limit=5`를 호출하면
- **Then** 트렌드 점수 내림차순으로 정렬된 상위 5개 섹터 목록이 반환되며, `sort=sentiment`/
  `sort=volume`도 각 기준으로 정렬된 결과를 반환한다.

---

## AC-8: 섹터 상세 조회 (REQ-SEC-012)

- **Given** 구성 종목이 언급된 특정 섹터의 데이터가 존재하고
- **When** 클라이언트가 `GET /sectors/{sector}/detail`을 호출하면
- **Then** 해당 섹터의 최근 N일 트렌드 시계열과 구성 종목 목록(종목코드·언급 횟수)이 반환된다.

---

## AC-9: 존재하지 않는 섹터 (REQ-SEC-013)

- **Given** 집계 데이터에 존재하지 않는 섹터명
- **When** 클라이언트가 `GET /sectors/{없는섹터}/detail`을 호출하면
- **Then** HTTP 404와 한국어 오류 메시지가 반환된다.

---

## AC-10: 섹터 비교 화면 표시 (REQ-SECUI-001, REQ-SECUI-002)

- **Given** 섹터 집계 데이터가 적재된 상태에서 사용자가 `/sectors`에 접속하고
- **When** 페이지가 로드된 후 순위 표의 특정 섹터를 선택하면
- **Then** 섹터 순위 표와 비교 차트가 표시되고, 선택한 섹터의 상세(추세 + 구성 종목)가 표시된다.

---

## AC-11: 데이터 미적재 안내 상태 (REQ-SECUI-003)

- **Given** 섹터 집계 데이터가 아직 적재되지 않은 상태(빈 목록)
- **When** 사용자가 `/sectors`에 접속하면
- **Then** 빈 차트 대신 "섹터 데이터 준비 중" 안내 상태가 표시된다.

---

## AC-12: 네비게이션 + 반응형 (REQ-SECUI-004)

- **Given** 데스크톱(>=768px)과 모바일(<768px) 화면
- **When** 사용자가 NavBar를 보면
- **Then** "섹터 분석" 링크가 표시되어 `/sectors`로 이동 가능하며, 모바일에서는 기존 햄버거
  메뉴 동작이 유지된다.

---

## AC-13: 하위 호환 (회귀 없음) (REQ-NFR-001)

- **Given** SPEC-008 변경이 적용된 상태
- **When** 기존 엔드포인트(`GET /sectors/trends`, `GET /recommendations`, `GET /news` 등)를
  호출하면
- **Then** 기존 응답 스키마가 그대로 유지되고, 기존 화면(추천·뉴스·포트폴리오·관심목록)이 회귀
  없이 동작한다.

---

## 품질 게이트 (Quality Gate) — Definition of Done

- [ ] AC-1 ~ AC-13 전 시나리오 통과
- [ ] 백엔드 신규/변경 코드 테스트 커버리지 85% 이상
- [ ] 마이그레이션 0011 정상 적용/롤백 검증
- [ ] 장중 재실행 upsert 멱등성 테스트 통과
- [ ] 기존 테스트 스위트 전체 통과(회귀 없음)
- [ ] 신규 외부 서비스 미도입(REQ-NFR-002 준수)
- [ ] 한국어 문서(README/CHANGELOG) 갱신
- [ ] 자동 매매 관련 기능 부재 확인(영구 제외 준수)
