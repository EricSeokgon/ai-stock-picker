---
name: stock-picker-spec-conventions
description: SPEC conventions for the ai-stock-picker (Korean Stock & ETF Recommendation System) project
metadata:
  type: project
---

ai-stock-picker 프로젝트(한국 주식 & ETF 추천 시스템)의 SPEC 작성 규약.

**Facts:**
- SPEC ID 체계: `SPEC-STOCK-NNN` (001 = MVP/Phase 1·2, 002 = Phase 3 인증·텔레그램·포트폴리오·백테스팅, 003 = Phase 4 WebSocket 실시간 시세·관심목록·포트폴리오 AI 분석, 004 = Phase 5 알림 고도화 — 관심목록 가격 알림(텔레그램)·이메일 알림(SMTP), 005 = Phase 6 성능·UX 고도화 — Redis 캐싱(추천/현재가)·추천 필터·정렬 API·모바일 반응형, 006 = Phase 7 AI 분석 고도화·추천 근거 투명성 — Claude explanation 컬럼·추천 히스토리 API·뉴스 감성 5단계 라벨).
- spec/plan/acceptance 본문은 **한국어**로 작성. EARS 키워드(WHEN/WHILE/WHERE/IF...THEN/SHALL)와 코드·식별자만 영어.
- spec.md frontmatter 8필드: id, version, status, created, updated, author(=ircp), priority, issue_number.
- REQ 네이밍은 기능 도메인별 접두사 사용: REQ-NEWS-*, REQ-AI-*, REQ-AUTH-*, REQ-TG-*, REQ-PORT-*, REQ-BT-*, REQ-WS-*, REQ-WL-*, REQ-PAI-*, REQ-FE-*, REQ-NFR-*.
- 002까지는 spec/plan/acceptance 3파일 구조였으나, 003·004·005는 spec/tasks/progress 3파일로 작성됨. 006은 spec/tasks/acceptance/progress 4파일(acceptance.md = Given-When-Then). DB 마이그레이션은 누적: 0001~0006 존재(003 watchlist_items=0006), 004 watchlist_alerts=0007·email_subscriptions=0008. 005는 신규 마이그레이션 없음. 006은 0009(컬럼 추가: recommendations.explanation Text nullable, analysis_results.sentiment_label String(20) nullable — 신규 테이블 아님).
- 기술 스택은 확정·재사용: FastAPI + PostgreSQL + Redis + React + Recharts + FinanceDataReader + APScheduler + Claude API. 신규 SPEC은 기존 테이블·API를 재정의하지 말고 추가만 할 것.

**Why:** 사용자가 단일 일관된 SPEC 스타일과 한국어 본문을 명시적으로 요구함. Phase별로 SPEC을 나누되 번호는 연속.

**How to apply:** 이 프로젝트의 새 SPEC 작성 시 위 ID 체계·한국어 본문·REQ 접두사·frontmatter 형식을 따르고, SPEC-STOCK-001의 자산은 재사용 대상으로 명시.

**영구 제외 (절대 SPEC에 포함 금지):** 자동 매매/주문 실행 — 규제·책임 리스크로 영구 제외. (이메일 알림·소셜 로그인은 Phase 4 연기이지 영구 제외 아님.)

**비자명 코드베이스 사실 (SPEC 작성 시 주의):**
- `GET /recommendations`(api/routes/recommendations.py)는 이미 Redis 캐시(`RecommendationCache`, recommendation/cache.py, TTL 1800s, 키 `recommendations:{date}`)에서만 읽고, 미스 시 scoring을 인라인 실행하지 않고 `PreparingResponse`(preparing)를 반환. 캐시 적재 주체는 스케줄러. → 캐싱 관련 SPEC은 이 동작을 확장으로 정의(인라인 scoring-on-miss를 새로 만든다고 쓰면 코드와 모순).
- `RecommendationItem` 스키마·`recommendations` 테이블에 **섹터 컬럼 없음**. 섹터는 `AnalysisResult.sector_tags`(기사별)·`sector_trends` 테이블에만 존재. 섹터 필터는 추천 적재 시 파생하거나 StockMention→Article→AnalysisResult 조인 필요(SPEC-005 §5.5 방안 A 권장).
- `realtime/price_feed.py` `get_current_price(krx_code)`는 **동기** 함수(FinanceDataReader 직접 호출) + 모듈 내 in-memory `_price_cache` dict 사용(Redis 아님). 호출처: ws_router.py, scheduler/jobs.py(알림 점검), portfolio/service.py(자체 `_get_current_price`). Redis 캐시 추가 시 동기 호환 필요.
- `config.py`에 `redis_url` 기본값 존재, `api/deps.py`에 `get_redis_client`(redis.asyncio, REDIS_URL env)·`get_cache` 의존성 존재.
- 프론트 NavBar(App.tsx)에 이미 `/settings`·`/watchlist`·`/portfolio`·`/backtest` 라우트 존재. Dashboard가 추천을 stock/etf로 분리해 `RecommendationList`/`EtfRecommendationList`에 전달.
- `Recommendation` 테이블에 `reasoning`(Text, nullable, 규칙 기반 `scoring/reasoning.py` `generate_reasoning()` 산출) 컬럼이 이미 존재. SPEC-006은 이를 **제거·치환하지 않고** Claude 자연어 근거를 **별도 `explanation` 컬럼**으로 추가. 두 필드 공존.
- `AnalysisResult.sentiment`는 `Literal["positive","negative","neutral"]`(`analysis/schema.py`), `sentiment_score`는 -1.0~1.0(Numeric(4,3)). SPEC-006의 `sentiment_label`(한국어 5단계)은 점수 기반 파생이며 기존 `sentiment` 보존.
- `ClaudeAnalysisClient`(analysis/client.py)는 `anthropic.AsyncAnthropic` + 모델 `claude-haiku-4-5` 사용. 추천 AI 분석(portfolio/ai_analysis.py)도 haiku-4-5. 새 Claude 호출은 이 패턴 재사용.
- 추천 히스토리는 `recommendations` 테이블이 진실 소스(캐시는 당일만 보관). `GET /recommendations/history`는 DB 직접 조회로 설계(SPEC-006).
