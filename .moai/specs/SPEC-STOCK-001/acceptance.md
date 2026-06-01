---
id: SPEC-STOCK-001
version: 0.1.0
status: draft
created: 2026-06-01
updated: 2026-06-01
author: ircp
priority: high
---

# SPEC-STOCK-001: 인수 기준 (Acceptance Criteria)

## 1. Given-When-Then 시나리오

### AC-1: 오전 배치 뉴스 수집 (REQ-NEWS-001,003,004)

- **Given** 오전 6시 스케줄이 등록되어 있고 4개 소스(네이버·한경·매경·연합)가 정상 응답하며
- **When** 06:00 스케줄이 트리거되면
- **Then** 4개 소스의 신규 기사가 `articles` 테이블에 원문·URL·출처·발행시각·수집시각과 함께 저장되고, 이미 존재하는 URL은 중복 저장되지 않는다.

### AC-2: 소스 장애 시 부분 수집 (REQ-NEWS-005)

- **Given** 한 소스가 HTTP 429를 반환하는 상태에서
- **When** 수집 배치가 실행되면
- **Then** 해당 소스는 스킵되고 나머지 3개 소스 수집은 정상 완료되며, 실패가 로그에 기록된다 (전체 배치 실패 없음).

### AC-3: Claude 감성 분석 + JSON 스키마 강제 (REQ-AI-001~003,006)

- **Given** `status='collected'`인 미분석 기사가 존재하고
- **When** 분석 워커가 Claude API(claude-sonnet-4-6)를 호출하면
- **Then** 각 기사에 대해 `sentiment ∈ {positive, negative, neutral}`, `sector_tags`(배열), `keywords`(배열), `summary`(1문장), `tokens_used`가 `analysis_results`에 저장되고 기사 상태가 `analyzed`로 변경된다.

### AC-4: Claude API 실패 재시도 및 격리 (REQ-AI-005)

- **Given** Claude API가 rate limit 또는 스키마 위반 응답을 반환하는 상황에서
- **When** 분석 워커가 한 기사를 처리하면
- **Then** 최대 3회 지수 백오프로 재시도하고, 최종 실패 시 해당 기사는 `analysis_failed`로 표시되며 워커는 다음 기사로 진행한다 (파이프라인 중단 없음).

### AC-5: 종합 추천 점수 산출 및 Top 10 생성 (REQ-REC-001,002,004,005)

- **Given** 트렌드 집계와 FinanceDataReader 시세 조회가 완료된 상태에서
- **When** 추천 엔진이 실행되면
- **Then** 각 종목의 `total_score = 0.40·sentiment + 0.20·volume + 0.25·momentum + 0.15·anomaly`가 계산되고, 상위 10개가 `rank` 1~10으로 `recommendations`에 저장되며, 각 항목에 `reasoning` 근거 설명이 포함되고 Redis에 캐싱된다.

### AC-6: ETF 섹터 기반 추천 (REQ-REC-003)

- **Given** `sector_trends`에 당일 섹터 트렌드 스코어가 산출된 상태에서
- **When** ETF 추천이 실행되면
- **Then** 상위 트렌드 섹터를 추종하는 국내 상장 ETF가 `asset_type='etf'`로 추천 리스트에 저장된다.

### AC-7: 대시보드 추천 표시 + 면책 고지 (REQ-WEB-001,005)

- **Given** 당일 추천이 생성·캐싱된 상태에서
- **When** 사용자가 대시보드에 접속하면
- **Then** Top 10 주식 추천과 ETF 추천 리스트가 표시되고, 화면에 투자 책임 면책 고지가 명시된다.

### AC-8: 추천 근거 상세 조회 (REQ-WEB-002)

- **Given** 추천 리스트가 표시된 상태에서
- **When** 사용자가 특정 종목을 선택하면
- **Then** 기여 뉴스 요약, 감성 점수, 가격 모멘텀·거래량 이상 지표를 포함한 근거 상세가 표시된다.

### AC-9: 섹터 트렌드 차트 (REQ-WEB-003)

- **Given** `sector_trends` 시계열 데이터가 존재할 때
- **When** 사용자가 섹터 트렌드 영역을 보면
- **Then** 섹터별 뉴스 볼륨·감성 추이가 Recharts 시계열 차트로 시각화된다.

### AC-10: 데이터 미준비 시 graceful 처리 (REQ-WEB-006)

- **Given** 당일 추천이 아직 생성되지 않은 상태에서
- **When** 사용자가 대시보드에 접속하면
- **Then** 오류 화면 대신 "데이터 준비 중" 상태와 마지막 갱신 시각이 표시된다.

---

## 2. 엣지 케이스

| # | 케이스 | 기대 동작 |
|---|--------|----------|
| E-1 | 종목명이 KRX 코드와 매핑 안 됨 | `unmapped`로 기록, 추천 후보 제외 (REQ-MAP-003) |
| E-2 | 동일 기사가 여러 소스에 중복 게재 | URL 멱등으로 중복 저장 방지 (REQ-NEWS-004) |
| E-3 | 본문이 비어 있거나 매우 짧은 기사 | 분석 시도하되 스키마 미충족 시 `analysis_failed` |
| E-4 | 장중 갱신 시 추천이 이미 존재 | 재계산 후 캐시 갱신 (REQ-REC-006) |
| E-5 | FinanceDataReader 시세 조회 실패 | 해당 종목 momentum/anomaly 점수 0 처리, 로그 기록 |
| E-6 | Claude API 응답이 유효 JSON이나 score 범위 이탈 | 범위(-1.0~1.0) 검증 실패로 재시도/격리 |
| E-7 | 휴장일 배치 실행 | 신규 시세 없음 → 직전 영업일 기준 표기, 추천 스킵 또는 유지 |

---

## 3. 품질 게이트 (TRUST 5)

- **Tested**: 핵심 로직(수집 멱등, 스코어링 공식, JSON 스키마 검증) 단위 테스트 + 파이프라인 통합 테스트. 커버리지 85% 이상.
- **Readable**: 명확한 네이밍, 한국어 주석(code_comments=ko), 레이어별 모듈 분리.
- **Unified**: Python ruff 포맷, 일관된 import 스타일.
- **Secured**: API 키 환경 변수화(REQ-NFR-002), 외부 입력(뉴스 본문) 검증, OWASP 준수, 면책 고지.
- **Trackable**: Conventional Commits, SPEC-STOCK-001 참조.

---

## 4. Definition of Done

- [ ] 5개 테이블 마이그레이션 적용 완료
- [ ] 4개 소스 수집기 + APScheduler 오전 배치 동작 (AC-1, AC-2)
- [ ] Claude API 분석 워커 + JSON 스키마 강제 + 재시도 (AC-3, AC-4)
- [ ] 종목 매핑 + FinanceDataReader 시세 조회 (E-1, E-5)
- [ ] 종합 스코어링 + Top 10 주식 추천 + 근거 생성 (AC-5)
- [ ] FastAPI 추천/뉴스 API + Redis 캐시
- [ ] React 대시보드: 추천 리스트 + 뉴스 피드 + 면책 고지 (AC-7, AC-10)
- [ ] (Phase 2) 장중 갱신, 섹터 트렌드 차트, 근거 상세, ETF 추천 (AC-6, AC-8, AC-9)
- [ ] 단위/통합 테스트 통과, 커버리지 85%+
- [ ] 일일 토큰 사용량 로깅 동작 (REQ-NFR-003)

---

## 5. 핵심 성공 지표 (KPI)

| KPI | 정의 | 측정 방법 | 목표 |
|-----|------|----------|------|
| 추천 적중률 | 추천 종목의 익일/N일 수익률이 양(+)인 비율 | 추천일 대비 후속 시세 추적 | 운영 후 베이스라인 수립 → 시장(KOSPI) 대비 초과 |
| 대시보드 응답속도 | 추천 리스트 API P95 | APM/로그 측정 | 캐시 히트 시 500ms 이내 (REQ-NFR-001) |
| 일일 처리 기사 수 | 하루 수집·분석 완료 기사 건수 | `articles.status='analyzed'` 집계 | 4개 소스 일일 신규 기사 100% 처리 |
| 분석 성공률 | `analyzed / (analyzed + analysis_failed)` | 상태 집계 | 95% 이상 |
| 일일 API 토큰 비용 | `SUM(tokens_used)` 기반 추정 비용 | `analysis_results.tokens_used` 집계 | 일일 예산 한도 내 유지 |
