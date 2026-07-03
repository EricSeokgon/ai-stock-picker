# SPEC-STOCK-037 구현 계획 (Implementation Plan)

> 본 문서는 구현 방법(HOW)을 다룬다. 요구사항(WHAT/WHY)은 spec.md, 검증은 acceptance.md 참조.

---

## 기술 접근 (Technical Approach)

### 데이터 저장소 (마이그레이션 0024, down_rev=0023)

신규 테이블 2종(동일 마이그레이션 0024):

1. **`recommendation_preferences`** — 사용자별 종목 선호.
   - id PK, user_id FK(CASCADE), krx_code String(10), sector String(50) nullable, preference String(10) ('liked'|'disliked'), created_at, updated_at.
   - **UNIQUE(user_id, krx_code)** — 종목당 1선호, 갱신은 upsert(SELECT-then-write, NFR-005).
2. **`personalized_recommendations`** — 개인화 추천 히스토리 스냅샷.
   - id PK, user_id FK(CASCADE), portfolio_id FK(CASCADE), krx_code String(10), name String(100) nullable, fit_score Numeric(4,3), reason Text nullable, risk_factors Text nullable, generated_at.
   - 인덱스 (user_id, generated_at) — 히스토리 최신순 조회.

> 신규 테이블만 추가하며 기존 `recommendation_feedback`(전역) 의미는 변경하지 않는다.

### 백엔드 모듈

- **`portfolio/ai_analysis.py` 확장**(재작성 금지): 신규 함수 `recommend_for_portfolio_with_claude(holdings_context, exclude_codes)` 추가.
  보유 종목·섹터 노출을 Claude 컨텍스트로 전달, 종목별 reason/risk_factors/fit_score JSON 반환.
  실패 시 오류 딕셔너리 반환(기존 격리 패턴, NFR-004). 모델 claude-haiku-4-5, AsyncAnthropic.
- **신규 순수 함수 모듈 `portfolio/recommendation_personalize.py`**(NFR-002):
  - `compute_fit_score(candidate, portfolio_context) -> float` — 섹터 분산 기여·과집중 회피 기반 0~1 적합도(numpy/math만, scipy 금지 NFR-001).
  - `apply_preferences(candidates, preferences) -> ranked` — 싫어요 종목 제외/후순위, 동일 섹터 유사 종목 하향, 좋아요 유사 상향(REQ-AIEX-APPLY).
  - 둘 다 DB 미의존 순수 함수.
- **신규 서비스 `portfolio/personalized_rec_service.py`**:
  - `generate_personalized_recommendations(portfolio_id, user_id, db, redis)` — 소유권 검증(get_portfolio_with_holdings, 미소유 None→404), 빈 포트폴리오 안내, Claude 호출, fit_score·선호 적용, 히스토리 영속화.
  - `save_preference(portfolio_id, user_id, krx_code, preference, db)` — upsert(SELECT-then-write), 잘못된 값 거부(ValueError→422/거부).
  - `get_recommendation_history(portfolio_id, user_id, db)` — 사용자별 히스토리 최신순.

### 엔드포인트 (portfolio router, prefix `/portfolios`)

- `POST /portfolios/{portfolio_id}/recommendations` — 개인화 추천 산출.
- `POST /portfolios/{portfolio_id}/recommendations/{krx_code}/preference` — 좋아요/싫어요 저장.
- `GET /portfolios/{portfolio_id}/recommendations/history` — 히스토리 조회.
- 전 엔드포인트 `get_current_user` 보호 + 소유권 불일치 시 **404**(NFR-003).

### 프론트엔드

- `frontend/src/components/PersonalizedRecommendations.js`(신규) — 추천 카드(근거·위험·적합도·좋아요/싫어요 버튼). `NewStockSuggestions.js` 패턴 참고.
- `frontend/src/api/portfolio.ts` 확장 — 개인화 추천·선호·히스토리 클라이언트 함수.
- `frontend/src/pages/Portfolio.tsx` — 개인화 추천 섹션/탭 통합.

---

## 마일스톤 (Milestones, 우선순위 기반)

### M1 (우선순위 High): 데이터 계층
- T-001: 마이그레이션 0024 작성 — `recommendation_preferences` + `personalized_recommendations` 테이블, 모델 추가.

### M2 (우선순위 High): 순수 로직
- T-002: `recommendation_personalize.py` — `compute_fit_score` 순수 함수 + 단위 테스트(scipy 미사용).
- T-003: `recommendation_personalize.py` — `apply_preferences` 재순위 순수 함수 + 단위 테스트.

### M3 (우선순위 High): Claude 연동·서비스
- T-004: `ai_analysis.py` 확장 — `recommend_for_portfolio_with_claude`(보유 종목 제외·근거 JSON·실패 격리).
- T-005: `personalized_rec_service.py` — 추천 산출(빈 포트폴리오 안내·히스토리 영속화·Claude 폴백) + 선호 upsert + 히스토리 조회.

### M4 (우선순위 Medium): API
- T-006: `portfolio/router.py` 엔드포인트 3종 추가(소유권 404·잘못된 선호 값 거부) + 스키마 + 통합 테스트.

### M5 (우선순위 Medium): 프론트엔드
- T-007: `PersonalizedRecommendations.js` + `api/portfolio.ts` 확장 + `Portfolio.tsx` 통합.

### M6 (우선순위 Low): 검증·문서
- T-008: 전체 테스트·커버리지(≥75%)·ruff·마이그레이션 롤백 검증, progress 갱신.

---

## 리스크 (Risks)

- **Claude 응답 비결정성**: fit_score·근거 JSON 파싱 실패 가능 → 폴백(전역 추천 또는 빈 근거)으로 격리(NFR-004). 기존 `optimize_portfolio_with_claude` JSON 추출 패턴 재사용.
- **선호 의미 충돌**: 기존 전역 `recommendation_feedback`와 신규 per-user 선호 혼동 위험 → 별도 테이블·별도 엔드포인트로 명확히 분리.
- **"outcome" 해석**: 히스토리의 "결과(outcome)"는 본 SPEC에서 추천 시점·항목 스냅샷으로 한정(실현 수익률 추적은 범위 밖).
- **테스트 디렉터리**: `backend/tests/unit/`·`backend/tests/integration/` 사용(관행 일치).
