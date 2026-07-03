---
name: project-stock-037
description: SPEC-STOCK-037 AI 종목 추천 고도화 — 포트폴리오 인식·구조화 근거·사용자 선호 학습, 신규 마이그 0024
metadata:
  type: project
---

SPEC-STOCK-037 = AI 종목 추천 고도화 (Advanced AI Stock Recommendation). **개인화 계층 추가 SPEC, 신규 마이그 0024(2종 테이블)**.

**3대 축**: (1)포트폴리오 인식 추천 (2)구조화 근거(reason/risk_factors/fit_score 0~1) (3)사용자 선호(liked/disliked) 학습→재순위.

**⚠️ 핵심 비자명 사실**:
- 작업지시 "추천 엔드포인트가 portfolio router.py에 존재할 것" 전제 **부정확** — 추천 시스템은 `recommendation/` 패키지 + `api/routes/recommendations.py`에 있고 portfolio router엔 `/recommend` 없음. 추천은 스케줄러 배치→캐시→읽기전용(`GET /recommendations` 미스 시 PreparingResponse).
- 기존 `recommendation_feedback`(마이그0010: krx_code,vote up/down,user_id nullable)는 **익명·전역 투표**(전역 점수 조정용, SPEC-009 weighting). **사용자별 개인화 학습 아님** → SPEC-037은 신규 per-user 선호 테이블 필요(의미 충돌 회피).
- `portfolio/ai_analysis.py` `optimize_portfolio_with_claude`가 **이미 포트폴리오 컨텍스트 기반 new_stocks(krx_code/name/sector/reason) 반환** → 이 모듈 확장(재작성 금지). AsyncAnthropic·claude-haiku-4-5·실패 시 오류딕셔너리 격리 패턴.
- 4요인 산식(scoring/engine.py 0.40감성/0.20거래량/0.25모멘텀/0.15이상거래) 변경 금지.

**신규 (마이그 0024, down_rev=0023)**:
- `recommendation_preferences`: id, user_id FK CASCADE, krx_code, sector?, preference('liked'|'disliked'), created/updated_at, **UNIQUE(user_id,krx_code)** upsert(SELECT-then-write, NFR-005).
- `personalized_recommendations`: id, user_id FK, portfolio_id FK, krx_code, name?, fit_score Numeric(4,3), reason?, risk_factors?, generated_at, idx(user_id,generated_at). 히스토리 스냅샷.

**신규 백엔드**: `ai_analysis.py`+`recommend_for_portfolio_with_claude`(보유제외·근거JSON·격리) · `portfolio/recommendation_personalize.py`(순수함수 scipy금지: `compute_fit_score`·`apply_preferences`) · `portfolio/personalized_rec_service.py`(산출·선호upsert·히스토리).

**엔드포인트**(portfolio router prefix `/portfolios`, get_current_user, 소유권→404 NFR-003): POST `/{id}/recommendations` · POST `/{id}/recommendations/{krx_code}/preference` · GET `/{id}/recommendations/history`.

**REQ 접두사**: REQ-AIEX-PORT-*·REQ-AIEX-RAT-*·REQ-AIEX-PREF-*·REQ-AIEX-APPLY-*·REQ-AIEX-HIST-*·REQ-AIEX-OWN-* + NFR-001~005. **AC-1~17**. T-001~T-008(M1~M6).

**NFR**: 001 scipy금지(numpy/math) · 002 순수함수(fit_score·재순위 DB미의존) · 003 소유권→404 · 004 Claude실패→폴백·비중단 · 005 SELECT-then-write.

**제외**: 자동매매(영구)·실시간시세추천·ML모델학습(Claude만 AI계층)·신규감성수집·4요인산식변경·전역파이프라인재작성·전역피드백의미변경.

**파일**: research/spec/acceptance/plan/spec-compact 5파일. frontmatter 8필드(id/version/status/created/updated/author=ircp/priority/issue_number). 커버리지 fail_under=75. 테스트=backend/tests/{unit,integration}/.

**커밋**: da89a5f (브랜치 feature/SPEC-STOCK-036에서 작업). **마이그레이션 최신=0023(0024는 037 RUN에서 생성 예정).**
