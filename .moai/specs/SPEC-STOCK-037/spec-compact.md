# SPEC-STOCK-037 압축 (RUN 참조용)

**목표**: AI 추천 고도화 — (1)포트폴리오 인식 (2)구조화 근거 (3)사용자 선호 학습.

## 재사용 (재작성 금지)
- `recommendation/service.py` 전역 파이프라인·4요인 산식(0.40/0.20/0.25/0.15) 불변.
- `portfolio/ai_analysis.py` Claude 패턴 확장(`optimize_portfolio_with_claude` 참고). AsyncAnthropic·claude-haiku-4-5·실패 시 오류딕셔너리.
- `get_portfolio_with_holdings`(소유권→None→404). 섹터=`portfolio/utils.get_sector`.
- 기존 전역 `recommendation_feedback`(마이그0010) 의미 변경 금지 — 개인화 선호는 별도 테이블.

## 신규 (마이그 0024, down_rev=0023)
- `recommendation_preferences`: user_id FK, krx_code, sector?, preference('liked'|'disliked'), UNIQUE(user_id,krx_code), upsert(SELECT-then-write).
- `personalized_recommendations`: user_id FK, portfolio_id FK, krx_code, name?, fit_score Numeric(4,3), reason?, risk_factors?, generated_at, idx(user_id,generated_at).

## 신규 백엔드
- `ai_analysis.py`+`recommend_for_portfolio_with_claude(holdings_context, exclude_codes)` — 보유 제외·reason/risk_factors/fit_score JSON·실패 격리.
- `portfolio/recommendation_personalize.py`(순수, scipy금지 numpy/math): `compute_fit_score`, `apply_preferences`(싫어요 제외/후순위·동일섹터 하향·좋아요 상향).
- `portfolio/personalized_rec_service.py`: `generate_personalized_recommendations`(빈포트폴리오 안내·히스토리 영속화·폴백)·`save_preference`(upsert·잘못된값 거부)·`get_recommendation_history`.

## 엔드포인트 (router prefix `/portfolios`, get_current_user, 소유권404)
- POST `/{id}/recommendations` 산출
- POST `/{id}/recommendations/{krx_code}/preference` 좋아요/싫어요
- GET `/{id}/recommendations/history`

## 프론트
- `components/PersonalizedRecommendations.js`(근거·위험·fit_score·선호버튼, NewStockSuggestions 패턴)
- `api/portfolio.ts` 확장 + `pages/Portfolio.tsx` 통합

## NFR
- 001 scipy금지(numpy/math) · 002 순수함수(fit_score·재순위) · 003 소유권→404 · 004 Claude실패→폴백·비중단 · 005 SELECT-then-write

## REQ 맵
- PORT-001~004(포트폴리오 인식·보유제외·분산·빈포트폴리오) · RAT-001~003(근거·fit_score 0~1·면책) · PREF-001~003(저장·갱신·값거부) · APPLY-001~003(싫어요 후순위·유사하향·좋아요상향) · HIST-001~002(조회·영속화) · OWN-001(소유권404) · NFR-001~005.
- AC-1~17.

## 태스크
- T-001 마이그0024+모델 / T-002 fit_score / T-003 apply_preferences / T-004 Claude함수 / T-005 서비스3종 / T-006 라우터3+통합테스트 / T-007 프론트 / T-008 검증

## 제외 (영구/범위밖)
자동매매(영구)·실시간시세추천·ML학습·신규감성수집·4요인산식변경·전역파이프라인재작성·전역피드백의미변경.

## 사실
- 마이그 최신=0023 → 신규 0024. 커버리지 fail_under=75. 테스트=backend/tests/{unit,integration}/. 코드주석·커밋 한국어. portfolio router 동기 Session+내부 async 혼용 관행.
