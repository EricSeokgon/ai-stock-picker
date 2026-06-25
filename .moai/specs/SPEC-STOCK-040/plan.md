# SPEC-STOCK-040 구현 계획 (Implementation Plan)

작성일: 2026-06-25
대상: AI 포트폴리오 코멘터리

시간 추정은 사용하지 않으며, 작업 순서·우선순위로 표현한다.

---

## 1. 작업 분해 (Tasks)

### Priority High — 백엔드 핵심

- T-001: `portfolio/schemas.py`에 `AICommentaryResponse` 추가 (코멘터리 섹션·면책·생성 시각·캐시 여부·대체 응답 여부). REQ-CMNT-002~007, 010.
- T-002: `portfolio/ai_commentary.py` 신규 — 코멘터리 입력 조립 순수 함수. SPEC-026 `_build_portfolio_data` 재사용, 성과·섹터·리스크(베스트에포트) 집계. 사용자 식별 정보 미포함. REQ-CMNT-008, 009.
- T-003: `ai_commentary.py`에 Claude 호출 함수 추가. 모델 `claude-haiku-4-5`, 기존 `ANTHROPIC_API_KEY` 재사용, max_tokens 상한·타임아웃 상한. JSON/평문 파싱 fallback. REQ-CMNT-001~005, NFR-003, NFR-004.
- T-004: `ai_commentary.py`에 인메모리 TTL 캐시 구현. 키 = portfolio_id + 보유 구성 지문. 보관 기간·최소 생성 간격. REQ-CMNT-011~015, NFR-002, NFR-005.
- T-005: `ai_commentary.py`에 오류 복구·대체 코멘터리. 실패·타임아웃·비정형·자격 증명 없음 → 대체 응답 + 로깅. REQ-CMNT-030~035, 034.
- T-006: 서비스 진입점 — 소유권 확인(404), 빈 포트폴리오 안내, 면책 부착. REQ-CMNT-006, 007, 022~025.

### Priority High — 라우터

- T-007: `portfolio/router.py`에 `GET /{portfolio_id}/ai-commentary` 엔드포인트. 인증 의존성, 소유권 404, 미인증 401. REQ-CMNT-020~024.

### Priority Medium — 프론트엔드

- T-008: `frontend/src/api/portfolio.ts` + `.js`에 `getAICommentary` 래퍼 추가 (Bearer 토큰).
- T-009: `frontend/src/components/AICommentaryPanel.tsx` + `.js` 신규 — 코멘터리 섹션 표시, 로딩·오류·대체 응답 상태, 면책 문구.
- T-010: `frontend/src/pages/Portfolio.tsx` + `.js`에 패널 통합.

### Priority High — 테스트

- T-011: `backend/tests/unit/test_ai_commentary.py` — 순수 함수 단위 테스트(입력 조립, 사용자 식별 정보 미포함).
- T-012: Claude 모킹 통합 테스트 — 정상·실패·타임아웃·비정형·자격 증명 없음.
- T-013: 캐시 테스트 — 히트·미스·만료·구성 변경 재생성·최소 간격.
- T-014: 소유권 404·미인증 401·빈 포트폴리오·면책 부착 테스트.

---

## 2. 기술 접근 (Technical Approach)

- 데이터 조달: `service.calculate_performance`(성과), `performance_summary.calculate_performance_summary`(기간별), `risk_analysis.calculate_risk_analysis`(리스크, 베스트에포트), `utils.get_sector`(섹터) 결과를 집계. 리스크 실패(2종목 미만 400) 흡수.
- 입력 빌더: `ai_analysis._build_portfolio_data` 재사용(수정 없음).
- AI 호출: `anthropic.AsyncAnthropic` + `claude-haiku-4-5`. 기존 키 재사용. asyncio 타임아웃으로 NFR-004 강제.
- 캐시: 모듈 레벨 TTL dict(`portfolio/ai_commentary.py`). 단일 책임 격리, 단일 워커 가정 또는 스레드 안전 가드 명시(@MX:WARN).
- 소유권: `get_portfolio_with_holdings()` None → 404.

---

## 3. 리스크 및 완화

| 리스크 | 영향 | 완화 |
|--------|------|------|
| 인메모리 캐시가 다중 워커에서 비공유 | 워커별 캐시 불일치 | 단일 워커 가정 명시 또는 캐시 한계 @MX:WARN 문서화. 영속화는 범위 밖(제외 항목) |
| 리스크 서비스 400(2종목 미만) | 코멘터리 실패 위험 | 베스트에포트 — 리스크 없어도 성과·섹터로 생성 (REQ-CMNT-008) |
| Claude 응답 지연 | 응답 시간 초과 | 타임아웃 상한 + 대체 응답 (REQ-CMNT-031) |
| 전역 가변 dict (CLAUDE.md 전역 상태 금지) | 코드 규범 위반 우려 | 캐시 전용 모듈로 격리, 명시적 가드, 대안 부재 근거 문서화 |

---

## 4. 마일스톤 순서

1. 백엔드 스키마·서비스·캐시·오류 복구 (T-001~T-006) 완료
2. 라우터 엔드포인트 (T-007) 연결
3. 백엔드 테스트 (T-011~T-014) 통과 (커버리지 85%+)
4. 프론트엔드 API·패널·통합 (T-008~T-010)
5. 전체 검증 — 마이그레이션 없음·scipy 미사용·한국어 출력 확인
