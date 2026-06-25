---
id: SPEC-STOCK-040
version: 0.1.0
status: draft
created_at: 2026-06-25
updated_at: 2026-06-25
author: ircp
priority: medium
issue_number: null
labels: [portfolio, ai, commentary, claude-api, backend, frontend]
---

# SPEC-STOCK-040 — AI 포트폴리오 코멘터리 (AI Portfolio Commentary)

## HISTORY

| 버전 | 일자 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 0.1.0 | 2026-06-25 | ircp | 최초 초안 — EARS REQ 5개 영역 + 제외 항목 + Delta Markers + MX Tag Plan |

---

## 1. 개요 (Overview)

AI가 포트폴리오의 현황·성과·리스크를 분석해 한국어 자연어 코멘터리(요약)를 생성한다.
사용자는 포트폴리오 페이지에서 보유 종목 구성·수익률·섹터 배분·리스크 상태를 서술형으로 한눈에 이해할 수 있다.

- 기존 AI 분석 레이어(SPEC-STOCK-026)를 확장하여 Claude API로 코멘터리를 생성한다.
- 포트폴리오 현재 상태를 입력으로 받아 성과 요약·리스크 경고·섹터 코멘트·추천 문구를 자연어로 반환한다.
- 동일 포트폴리오·동일 데이터 재호출 시 인메모리 캐시로 Claude 과호출을 방지한다.

### 1.1 목표 (Goals)

- 포트폴리오 상태를 한국어 자연어로 요약하는 코멘터리 제공
- Claude API 실패·지연 시에도 사용자 경험이 끊기지 않는 대체 응답
- 동일 데이터 반복 요청에 대한 호출 비용 절감

### 1.2 대상 사용자 (Audience)

- 자신의 포트폴리오 성과·리스크를 빠르게 파악하고자 하는 인증된 개인 투자자

---

## 2. 용어 (Glossary)

| 용어 | 정의 |
|------|------|
| 코멘터리 | AI가 생성한 포트폴리오 상태 자연어 요약(성과·리스크·섹터·추천 문구 포함) |
| 포트폴리오 데이터 지문 | 보유 종목 구성·수량·평단가로부터 산출한 캐시 식별 값 |
| 대체 응답 | AI 호출 실패 시 반환하는 사전 정의 코멘터리 |
| 생성 간격 제한 | 동일 포트폴리오에 대한 코멘터리 재생성 최소 간격 |

---

## 3. 기능 요구사항 (EARS Requirements)

작성 규칙: 모든 정규 진술의 주어는 "THE 시스템"이며, 정규 진술 본문에는 함수명·HTTP 코드·라이브러리명·SQL·변수명·파일경로를 포함하지 않는다.

### 3.1 코멘터리 생성 (REQ-CMNT-001 ~ REQ-CMNT-010)

- REQ-CMNT-001: WHEN 인증된 사용자가 본인 포트폴리오의 코멘터리를 요청하면, THE 시스템 SHALL 해당 포트폴리오의 현재 상태를 분석하여 한국어 자연어 코멘터리를 생성한다.
- REQ-CMNT-002: THE 시스템 SHALL 코멘터리에 포트폴리오 전체 성과 요약을 포함한다.
- REQ-CMNT-003: THE 시스템 SHALL 코멘터리에 보유 구성의 리스크에 대한 코멘트를 포함한다.
- REQ-CMNT-004: THE 시스템 SHALL 코멘터리에 섹터 배분에 대한 코멘트를 포함한다.
- REQ-CMNT-005: THE 시스템 SHALL 코멘터리에 사용자가 참고할 수 있는 추천 문구를 포함한다.
- REQ-CMNT-006: WHILE 포트폴리오에 보유 종목이 하나도 없으면, THE 시스템 SHALL 분석을 수행하지 않고 보유 종목이 없음을 안내하는 코멘터리를 반환한다.
- REQ-CMNT-007: THE 시스템 SHALL 모든 코멘터리 응답에 투자 권유가 아님을 명시하는 면책 문구를 포함한다.
- REQ-CMNT-008: IF 포트폴리오 상태 분석에 필요한 일부 데이터가 가용하지 않으면, THEN THE 시스템 SHALL 가용한 데이터만으로 코멘터리를 생성한다.
- REQ-CMNT-009: THE 시스템 SHALL 코멘터리 생성 시 사용자 식별 정보를 분석 입력에 포함하지 않는다.
- REQ-CMNT-010: THE 시스템 SHALL 코멘터리에 분석 기준 시점 정보를 포함한다.

### 3.2 캐싱·호출 제한 (REQ-CMNT-011 ~ REQ-CMNT-015)

- REQ-CMNT-011: WHEN 동일 포트폴리오에 대해 직전 코멘터리 생성 이후 보유 구성이 변경되지 않은 상태로 재요청이 들어오면, THE 시스템 SHALL 새로 생성하지 않고 캐시된 코멘터리를 반환한다.
- REQ-CMNT-012: THE 시스템 SHALL 캐시된 코멘터리를 정해진 보관 기간 동안만 유효한 것으로 취급한다.
- REQ-CMNT-013: WHEN 캐시된 코멘터리의 보관 기간이 만료되면, THE 시스템 SHALL 다음 요청 시 코멘터리를 새로 생성한다.
- REQ-CMNT-014: WHEN 포트폴리오의 보유 구성이 변경된 후 코멘터리가 요청되면, THE 시스템 SHALL 변경된 상태를 반영하여 코멘터리를 새로 생성한다.
- REQ-CMNT-015: IF 동일 포트폴리오에 대해 정해진 최소 생성 간격 이내에 재생성 요청이 들어오면, THEN THE 시스템 SHALL 새로 생성하지 않고 가장 최근 코멘터리를 반환한다.

### 3.3 소유권·접근 (REQ-CMNT-020 ~ REQ-CMNT-025)

- REQ-CMNT-020: THE 시스템 SHALL 코멘터리 요청에 대해 사용자 인증을 요구한다.
- REQ-CMNT-021: IF 인증되지 않은 요청이 들어오면, THEN THE 시스템 SHALL 코멘터리를 제공하지 않고 인증이 필요함을 알린다.
- REQ-CMNT-022: THE 시스템 SHALL 요청자가 소유한 포트폴리오에 대해서만 코멘터리를 제공한다.
- REQ-CMNT-023: IF 요청자가 소유하지 않은 포트폴리오의 코멘터리를 요청하면, THEN THE 시스템 SHALL 해당 포트폴리오를 찾을 수 없음을 알린다.
- REQ-CMNT-024: IF 존재하지 않는 포트폴리오의 코멘터리를 요청하면, THEN THE 시스템 SHALL 해당 포트폴리오를 찾을 수 없음을 알린다.
- REQ-CMNT-025: THE 시스템 SHALL 코멘터리 응답에 다른 사용자의 포트폴리오 정보를 노출하지 않는다.

### 3.4 오류 복구 (REQ-CMNT-030 ~ REQ-CMNT-035)

- REQ-CMNT-030: IF AI 코멘터리 생성이 실패하면, THEN THE 시스템 SHALL 사전 정의된 대체 코멘터리를 반환한다.
- REQ-CMNT-031: IF AI 응답 대기 시간이 허용 한도를 초과하면, THEN THE 시스템 SHALL 대기를 중단하고 대체 코멘터리를 반환한다.
- REQ-CMNT-032: WHEN AI 코멘터리 생성이 실패하면, THE 시스템 SHALL 실패 사실을 기록한다.
- REQ-CMNT-033: IF AI 응답이 기대한 형태로 해석되지 않으면, THEN THE 시스템 SHALL 응답에서 유효한 부분만 추출하거나 대체 코멘터리를 반환한다.
- REQ-CMNT-034: THE 시스템 SHALL AI 코멘터리 생성 실패 시에도 정상 응답 형식을 유지한다.
- REQ-CMNT-035: IF AI 자격 증명이 설정되지 않은 환경에서 코멘터리가 요청되면, THEN THE 시스템 SHALL 대체 코멘터리를 반환한다.

---

## 4. 비기능 요구사항 (NFR)

- REQ-CMNT-NFR-001: THE 시스템 SHALL 코멘터리를 한국어로 출력한다.
- REQ-CMNT-NFR-002: THE 시스템 SHALL 캐시 적중 시 AI 호출 없이 응답한다.
- REQ-CMNT-NFR-003: THE 시스템 SHALL 단일 코멘터리 생성에 사용하는 AI 응답 분량을 상한 이내로 제한한다.
- REQ-CMNT-NFR-004: THE 시스템 SHALL AI 응답을 기다리는 시간을 상한 이내로 제한한다.
- REQ-CMNT-NFR-005: THE 시스템 SHALL 코멘터리 기능을 위해 신규 데이터베이스 테이블을 도입하지 않는다.

---

## 5. 제외 항목 (Exclusions — What NOT to Build)

본 SPEC의 범위에 포함되지 않는 항목:

- **코멘터리 영속화**: 코멘터리는 인메모리 캐시에만 보관하며, 데이터베이스에 저장하거나 이력을 조회하는 기능은 만들지 않는다.
- **신규 마이그레이션·테이블**: 최신 리비전 0024를 유지하며 신규 테이블을 추가하지 않는다.
- **분산 캐시(Redis)**: 코멘터리 캐시는 인메모리 TTL 구조만 사용하며 Redis 등 외부 캐시는 도입하지 않는다.
- **신규 수치 분석 라이브러리**: scipy 등 신규 수치 계산 의존성을 추가하지 않는다. 필요한 지표는 기존 성과·리스크 서비스 결과를 재사용한다.
- **신규 성과·리스크 계산 로직**: 코멘터리는 기존 성과·기간별 성과·리스크 서비스의 결과를 집계하여 서술할 뿐, 새로운 지표를 계산하지 않는다.
- **SPEC-026 AI 분석 대체**: 기존 구조화 JSON AI 분석(`/ai-analysis`)을 변경하거나 대체하지 않는다. 코멘터리는 별도 엔드포인트로 공존한다.
- **종목 추천 생성**: 신규 매수 종목 추천(SPEC-037)은 본 SPEC 범위가 아니다. 추천 문구는 보유 구성에 대한 일반적 참고 문구로 한정한다.
- **다국어 출력**: 한국어 외 언어 출력은 범위 밖이다.
- **실시간 스트리밍 코멘터리**: 토큰 단위 스트리밍 응답은 만들지 않는다.

---

## 6. 설계 결정 노트 (기술 접근)

REQ 정규 진술과 분리된 구현 참고. 함수명·심볼 명시 가능.

- 엔드포인트: `GET /portfolios/{portfolio_id}/ai-commentary` (인증 필요, 동적 경로). 기존 `POST /{id}/ai-analysis`와 경로 충돌 없음.
- 소유권 위반: `get_portfolio_with_holdings()` None → 404(신규 코드 관례). 인증 누락 → 401(`get_current_user` 의존성).
- 데이터 조달: `service.calculate_performance`, `performance_summary.calculate_performance_summary`, `risk_analysis`(베스트에포트), `utils.get_sector` 결과를 집계. 리스크 데이터가 2종목 미만으로 실패해도 코멘터리 생성 진행.
- 입력 빌더: SPEC-026 `_build_portfolio_data` 재사용(사용자 식별 정보 미포함).
- Claude 호출: `anthropic.AsyncAnthropic`, 모델 `claude-haiku-4-5`, 기존 `ANTHROPIC_API_KEY` 재사용. max_tokens 상한(NFR-003), 타임아웃 상한(NFR-004).
- 캐시: 신규 모듈 `portfolio/ai_commentary.py` 내 인메모리 TTL dict. 키 = `portfolio_id` + 보유 구성 지문. 단일 워커 가정 또는 스레드 안전 가드 명시.
- 면책 문구: 기존 `_DISCLAIMER` 패턴 재사용.
- 응답 스키마: `AICommentaryResponse`(코멘터리 섹션 + 면책 + 생성 시각 + 캐시 여부 + 대체 응답 여부).

---

## 7. Delta Markers (변경 영향 범위)

| 구분 | 파일 | 변경 유형 | 비고 |
|------|------|-----------|------|
| 신규 | `backend/src/stock_picker/portfolio/ai_commentary.py` | CREATE | 코멘터리 조립 순수 함수 + 캐시 + 서비스 진입점 |
| 수정 | `backend/src/stock_picker/portfolio/router.py` | MODIFY | `GET /{id}/ai-commentary` 엔드포인트 추가 |
| 수정 | `backend/src/stock_picker/portfolio/schemas.py` | MODIFY | `AICommentaryResponse` 추가 |
| 재사용 | `backend/src/stock_picker/portfolio/ai_analysis.py` | REUSE | `_build_portfolio_data` 활용 (수정 없음) |
| 재사용 | `backend/src/stock_picker/portfolio/service.py` | REUSE | `calculate_performance`, `get_portfolio_with_holdings` (수정 없음) |
| 신규 | `frontend/src/components/AICommentaryPanel.tsx` + `.js` | CREATE | 코멘터리 패널 |
| 수정 | `frontend/src/api/portfolio.ts` + `.js` | MODIFY | `getAICommentary` 래퍼 추가 |
| 수정 | `frontend/src/pages/Portfolio.tsx` + `.js` | MODIFY | 패널 통합 |
| 신규 | `backend/tests/unit/test_ai_commentary.py` | CREATE | 단위·통합 테스트 |

마이그레이션: 없음 (0024 유지).

---

## 8. MX Tag Plan

- `ai_commentary.py` 모듈 상단 `@MX:NOTE`: scipy 금지·신규 마이그레이션 없음·Redis 미사용(인메모리 캐시) 명시.
- 코멘터리 서비스 진입점 `@MX:ANCHOR` + `@MX:REASON`: router·테스트 다중 참조.
- 인메모리 캐시 전역 dict `@MX:WARN` + `@MX:REASON`: 전역 가변 상태 — 단일 워커 가정 또는 스레드 안전 한계 명시.
- 신규 공개 함수 미구현 단계 `@MX:TODO`: 구현 완료(GREEN) 시 제거.

---

## 9. 참조 (References)

- 연구 노트: `.moai/specs/SPEC-STOCK-040/research.md`
- 수용 기준: `.moai/specs/SPEC-STOCK-040/acceptance.md`
- 선행 SPEC: SPEC-STOCK-026 (AI 분석), SPEC-STOCK-030 (기간별 성과), SPEC-STOCK-027 (리스크), SPEC-STOCK-037 (AI 추천 fallback 패턴)
