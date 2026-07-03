# SPEC-STOCK-037 사전 조사 — AI 종목 추천 고도화

조사일: 2026-06-25
조사 대상: 기존 추천 시스템, 포트폴리오 컨텍스트, 피드백 인프라

---

## 1. 기존 추천 시스템 구조 (재사용·확장 대상)

### 1.1 추천 파이프라인 (`recommendation/service.py`)
- `RecommendationService.run()`이 일일 Top-10 추천 생성 → DB(`recommendations` 테이블) 저장 → Redis 캐시.
- **전역(global) 추천**: 모든 사용자에게 동일. 포트폴리오·사용자별 개인화 없음.
- 4요인 산식(`scoring/engine.py` `calculate_stock_score`): 0.40 감성 + 0.20 거래량 + 0.25 모멘텀 + 0.15 이상거래. **변경 금지**.
- 피드백 가중치(`feedback/weighting.py`)는 전역 up/down 집계를 점수에 반영(SPEC-009). 사용자별 아님.

### 1.2 추천 조회 API (`api/routes/recommendations.py`)
- `GET /recommendations` — 캐시 읽기 전용. 미스 시 `PreparingResponse` 반환(스케줄러가 캐시 적재). **인라인 스코어링 안 함**.
- `GET /recommendations/history` — `recommendations` 테이블 직접 조회(최근 N일, 전역).
- `GET /recommendations/{krx_code}` — 추천 근거 상세 + 기여 뉴스 + 점수 분해.
- `POST|GET /recommendations/{krx_code}/feedback` — 전역 up/down 투표(`RecommendationFeedback`).
- **결론: `router.py`에 `/recommend` 라우트는 없음**. 작업지시의 "추천 엔드포인트가 router.py에 존재할 것" 전제는 portfolio router 기준 부정확. 추천은 `recommendation/` 패키지 + `recommendations.py` 라우터에 분산.

### 1.3 포트폴리오 AI Claude 연동 (`portfolio/ai_analysis.py`) — **확장 대상**
- `analyze_portfolio()` — 분산/리스크/제안 정성 분석(claude-haiku-4-5, AsyncAnthropic).
- `optimize_portfolio_with_claude()` — **이미 포트폴리오 컨텍스트 기반 `new_stocks` 추천을 반환**(krx_code/name/sector/reason). 포트폴리오 보유 종목 제외 필터 포함.
- 두 함수 모두 Claude 실패 시 예외 전파 없이 오류 딕셔너리 반환(격리 패턴 확립).
- **SPEC-037은 이 모듈을 확장**(재작성 아님): 포트폴리오 컨텍스트를 입력으로 받아 종목별 구조화 근거(reason/risk_factors/fit_score)를 산출하는 신규 함수 추가.

### 1.4 포트폴리오 서비스 (`portfolio/service.py`)
- `get_portfolio_with_holdings(db, portfolio_id, user_id)` — 소유권 검증 포함, 미소유 시 `None` 반환(라우터에서 404 변환). **재사용**.
- 보유 종목에서 티커·수량·매수가 획득. 섹터는 `portfolio/utils.py` `get_sector(krx_code)`로 파생. 비중은 평가액 합계 대비 계산.

---

## 2. 피드백·선호 인프라 현황

### 2.1 기존 `RecommendationFeedback`(테이블 `recommendation_feedback`, 마이그 0010)
- 컬럼: id, krx_code, vote('up'/'down'), user_id(nullable FK), created_at.
- **익명·전역 투표**: 비로그인 허용, 종목 단위 집계로 전역 추천 점수 조정에만 사용.
- **사용자별 개인화 학습 용도 아님**: user_id가 nullable이고, "이 사용자가 이 종목을 좋아함/싫어함 → 향후 추천 개인화"라는 의미 모델이 없음.
- **결론: SPEC-037의 사용자 선호 학습은 신규 저장소 필요**. 기존 테이블 재사용 시 의미 충돌(전역 vs 개인화).

### 2.2 신규 필요 저장소
- **사용자 선호(liked/disliked)**: (user_id, krx_code) 단위 좋아요/싫어요. 향후 추천 개인화에 사용.
- **추천 히스토리**: 사용자에게 제공된 개인화 추천 결과 스냅샷(나중에 결과 조회용). 전역 `recommendations` 테이블은 개인화 결과를 담지 못함.

---

## 3. 마이그레이션 현황
- 최신 마이그레이션 = **0023**(`0023_portfolio_alerts_036.py`, SPEC-036).
- SPEC-037 신규 마이그레이션 = **0024**(down_rev=0023).

## 4. 기술 스택·제약 사실
- `pyproject.toml`: `finance-datareader>=0.9`, `numpy>=1.26` 존재. **scipy 없음**(NFR-001 준수 가능).
- 커버리지 `fail_under = 75`.
- Claude 모델 = `claude-haiku-4-5`(전 모듈 통일). `ANTHROPIC_API_KEY` env. AsyncAnthropic 패턴.
- 라우터 관행: 동기 `Session`(get_db_session) + 내부 서비스 async 혼용 가능. 소유권 불일치 → **404**(NFR-003, get_portfolio_with_holdings 관행 일치).

## 5. 프론트엔드 현황
- `frontend/src/pages/Portfolio.tsx`(+ .js 빌드 산출물) — AI 최적화 탭(SPEC-026), 리스크 패널(SPEC-027) 등 존재.
- `frontend/src/components/NewStockSuggestions.js` 존재(SPEC-026 신규 종목 제안 UI). SPEC-037 개인화 추천 UI는 별도 컴포넌트로 추가하되 이 패턴 참고.
- `frontend/src/api/portfolio.ts`(+ .js) — 포트폴리오 API 클라이언트. 확장 대상.

## 6. 설계 결론 (plan.md 상세화)
1. **포트폴리오 인식 추천**: `ai_analysis.py` 확장 — 보유 종목(티커·섹터·비중)을 Claude 컨텍스트로 전달, 과집중 회피·분산 지향 추천.
2. **구조화 근거**: 추천 항목별 reason(근거)·risk_factors(위험 요인)·fit_score(0.0~1.0 적합도). fit_score는 순수 함수로 산출(NFR-002).
3. **사용자 선호 저장**: 신규 테이블(마이그 0024) — liked/disliked. SELECT-then-write(NFR-005).
4. **선호 적용**: 싫어요 종목·유사(동일 섹터) 종목을 후순위화하는 순수 재랭킹 함수.
5. **히스토리**: 개인화 추천 결과 스냅샷 영속화 → 사용자별 과거 추천 조회.
6. **격리**: Claude 실패 시 폴백(전역 추천 또는 빈 근거) 반환, 엔드포인트 비충돌(NFR-004).
