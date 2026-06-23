---
name: project-stock-spec-conventions
description: Brownfield SPEC-authoring conventions for ai-stock-picker portfolio domain — ownership status, migrations, JSON storage, scipy ban, frontend file pairing
metadata:
  type: project
---

ai-stock-picker SPEC 작성 시 따라야 하는 브라운필드 관례 (SPEC-026~032 portfolio 계열에서 확인).

**Why:** 이 프로젝트는 SPEC-STOCK-NNN 계열로 portfolio 기능을 점진 확장 중이며, 신규 SPEC은 기존 코드 관례와 충돌하지 않아야 한다. 사용자가 매 SPEC마다 동일 제약을 carry-over로 명시한다.

**How to apply:** portfolio 도메인 신규 SPEC을 작성할 때 아래를 기본 전제로 삼는다.

- **패키지**: `backend/src/stock_picker/portfolio/`. `backtest/` 아님(backtest는 별도 함수).
- **소유권 위반 상태코드**: 신규 코드는 `404 Not Found`(403 아님). `get_portfolio_with_holdings()`가 None 반환 → 404. 단 레거시 `ai_analysis.analyze_portfolio`·`optimize_portfolio`는 예외적으로 403 사용 — 신규 코드는 404 관례 따름.
- **Alembic**: `backend/alembic/versions/NNNN_name.py`(`src/.../migrations/` 아님). `revision`/`down_revision` 문자열. 리비전 순차 증가 — 최신 확인 후 +1. (0020=SPEC-031, 0021=SPEC-032).
- **JSON 컬럼 저장**: SQLite 테스트 호환을 위해 JSONB 대신 `Text` + JSON 직렬화 문자열 사용(기존 `ai_advice.payload`·`screener_presets.criteria` 패턴). 요청서가 JSONB라 해도 Text로 구현.
- **scipy 금지** (반복 NFR-001): 수치 계산은 `numpy` + `math`만. `risk_analysis.py`가 모범 — 순수 함수 레이어 + 오케스트레이션 함수 분리, 모듈 상단 @MX:NOTE로 금지 명시.
- **순수 함수 분리**: 핵심 계산은 DB·Redis 없이 테스트 가능한 순수 함수로(`calculate_*`), 서비스가 가격/소유권/저장을 주입.
- **가격 조회 재사용**: KRX `realtime/price_feed.get_current_price(code)["price"]`, 해외 `portfolio/service._fetch_foreign_price(ticker, redis)` × `fx_rate.get_usd_krw_rate(redis)`. USD→KRW 환산 후 예산/금액 비교(`calculate_performance` 패턴).
- **시장/통화 메타**: `PortfolioHolding.market`(KRX|NYSE|NASDAQ)·`currency`(KRW|USD), server_default KRX/KRW (SPEC-028). 국내/해외 분기 기준.
- **프론트 .js/.ts 쌍**: `frontend/src/api/portfolio.js`와 `.ts`, `pages/Portfolio.js`와 `.tsx`를 항상 동시 수정. 컴포넌트는 컴파일된 .js 형태로 커밋됨.
- **언어**: `code_comments: ko`, `git_commit_messages: ko`. 커밋 끝에 `🗿 MoAI <email@mo.ai.kr>`.
- **환경**: gh CLI 미설치.

**SPEC 문서 5종 세트**: research.md, spec.md(YAML frontmatter 8필드 + HISTORY 표 + EARS REQ + §제외(What NOT to Build) + Delta Markers 표 + MX Tag Plan), acceptance.md(EARS AC + Given-When-Then BDD + 엣지 케이스 표 + DoD), plan.md(T-001~ 작업분해, 시간추정 금지), spec-compact.md(run-phase 압축 참조). REQ 접두사는 기능별 고유(충돌 회피): OPT(026)·RISK(027)·FA(028)·PBT(029)·PS(030)·PAL(031)·RBA(032).
