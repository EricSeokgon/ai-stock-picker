# SPEC-STOCK-040 연구 노트 — AI 포트폴리오 코멘터리

작성일: 2026-06-25
작성자: ircp

본 문서는 SPEC-STOCK-040(AI 포트폴리오 코멘터리) 작성 전 기존 코드베이스를 분석한 결과다.
신규 기능이 기존 관례와 충돌하지 않도록 브라운필드 제약을 정리한다.

---

## 1. 기능 개요

AI가 포트폴리오의 현황·성과·리스크를 분석해 한국어 자연어 코멘터리(요약)를 생성한다.

- 입력: 포트폴리오 현재 상태(보유 종목, 수익률, 섹터 배분, 리스크 지표)
- 출력: 자연어 코멘터리(성과 요약·리스크 경고·섹터 코멘트·추천 문구)
- 백엔드: 신규 엔드포인트 `GET /portfolios/{id}/ai-commentary`
- 프론트엔드: `AICommentaryPanel` 컴포넌트(Portfolio 페이지 통합)

---

## 2. 기존 AI 분석 구조 (`portfolio/ai_analysis.py`)

기존 `ai_analysis.py`는 Claude API 연동의 모범 패턴을 보유한다. SPEC-040은 이를 **확장**한다.

핵심 함수:

- `analyze_portfolio(portfolio_id, user_id, db)` — 비동기 진입점. 소유권 확인 → holdings 조회 → 보유 종목 없으면 Claude 미호출 → `_build_portfolio_data` 변환 → `_call_claude_async` 호출 → 면책 문구 추가.
- `_build_portfolio_data(holdings, fx_rate=1.0)` — 보유 종목을 분석용 데이터 구조로 변환. **사용자 식별 정보(user_id, portfolio_id) 미포함**. USD 종목은 fx_rate로 KRW 환산하여 비중 계산.
- `_call_claude_async(portfolio_data)` — `anthropic.AsyncAnthropic` 사용. 모델 `claude-haiku-4-5`, max_tokens=512. JSON 형식 강제 프롬프트 + JSON 파싱 fallback(중괄호 추출).
- `optimize_portfolio_with_claude(...)` — 최적화 분석. max_tokens=1024.

관찰된 관례 (SPEC-040 재사용 대상):

1. **API 키 조회**: `os.environ.get("ANTHROPIC_API_KEY", "")`. 키 없으면 `RuntimeError` 또는 `AsyncAnthropic(api_key=None)`(테스트 환경).
2. **모델**: `claude-haiku-4-5` 일관 사용. SPEC-040도 동일 모델 재사용(신규 의존성 없음).
3. **JSON 파싱 fallback**: 응답 텍스트에서 `{`/`}` 추출 후 재파싱. SPEC-040은 코멘터리가 자연어이므로 JSON 강제 대신 평문 또는 섹션 구분 응답을 받을 수 있다 — 단 구조화된 응답(요약/리스크/섹터/추천)이면 기존 JSON 파싱 패턴 재사용 가능.
4. **실패 처리**: `try/except Exception` + `logger.exception` + 오류 딕셔너리 반환(500 대신). SPEC-040은 대체(fallback) 코멘터리 반환으로 강화.
5. **면책 문구**: `_DISCLAIMER = "본 분석은 투자 권유가 아닌 정보 제공 목적입니다."` 모든 응답에 부착.
6. **소유권 위반**: 기존 `analyze_portfolio`는 **예외적으로 403** 사용. 단 메모리 관례상 **신규 코드는 404**(get_portfolio_with_holdings None → 404). SPEC-040은 신규 코드이므로 **404 채택**.

---

## 3. 데이터 소스 — 성과·리스크·섹터

코멘터리 입력으로 쓸 포트폴리오 상태 데이터는 기존 서비스에서 조달한다(신규 계산 없음).

### 3.1 성과 (`service.calculate_performance`)

- `service.calculate_performance(db, portfolio_id, user_id, redis)` — KRX + 해외 자산 현재가 기반 성과 계산. `PortfolioPerformance` 반환.
- 가격 조회: KRX `realtime.price_feed.get_current_price(code)["price"]`, 해외 `service._fetch_foreign_price(ticker, redis)` + `fx_rate.get_usd_krw_rate(redis)`.

### 3.2 기간별 성과 (`performance_summary.calculate_performance_summary`)

- YTD/1M/3M/6M/1Y 수익률 + MDD. `PerformanceSummaryResponse` 반환.
- 기간 레이블 `PERIOD_DISPLAY_LABELS`(한국어), 면책 문구 보유.

### 3.3 리스크 (`risk_analysis.calculate_risk_analysis`)

- 상관관계·변동성·분산 효과. `RiskAnalysisResult` 반환.
- **유효 보유 종목 2개 미만이면 400** — 코멘터리 입력으로 사용 시 이 제약을 흡수해 베스트에포트로 처리해야 함(리스크 데이터 없어도 코멘터리 생성).
- scipy 금지, numpy만 사용.

### 3.4 섹터 (`portfolio/utils.get_sector`)

- `get_sector(krx_code)` — 코드 프리픽스 기반 섹터 분류, fallback "기타". `_build_portfolio_data`에서 이미 사용.

설계 결정: SPEC-040 코멘터리는 **베스트에포트 집계** — 일부 데이터 소스(리스크 등)가 실패해도 가용 데이터만으로 코멘터리를 생성한다. 모든 소스가 필수는 아니다.

---

## 4. 라우터 패턴 (`portfolio/router.py`)

- prefix `/portfolios`, `tags=["portfolios"]`.
- 인증: `current_user: User = Depends(get_current_user)`, `db: Session = Depends(get_db_session)`, `redis: aioredis.Redis = Depends(get_redis_client)`.
- 소유권 위반 → 404(신규 엔드포인트 일관). 예: SPEC-037 `post_recommendations`, SPEC-035 report 엔드포인트.
- AI 실패 fallback 패턴: SPEC-037 `post_recommendations`는 Claude 실패 시 **빈 추천 + 면책 문구** 반환(500 아님).
- 경로 순서 주의: `/{portfolio_id}/...` 동적 경로보다 정적 경로(`/market-status`)를 먼저 정의. SPEC-040의 `/{id}/ai-commentary`는 동적 경로이므로 기존 동적 경로 블록에 추가하면 충돌 없음.

SPEC-040 신규 엔드포인트: `GET /portfolios/{portfolio_id}/ai-commentary` — 기존 `POST /{id}/ai-analysis`(SPEC-026)와 경로 충돌 없음(`ai-commentary` ≠ `ai-analysis`).

---

## 5. 스키마 패턴 (`portfolio/schemas.py`)

- Pydantic v2, `model_validate` / `model_validate_json` 사용.
- 응답 스키마는 `*Response` 또는 도메인명 접미사(`RiskAnalysisResult`, `PerformanceSummaryResponse`).
- SPEC-040 신규 스키마: `AICommentaryResponse`(코멘터리 본문 섹션 + 면책 + 생성 시각 + 캐시 여부 등). REQ 본문에는 스키마명 미기재(EARS 금지어 회피).

---

## 6. 캐싱 — in-memory TTL

요청서 제약: **in-memory only(Redis 금지) — 간단한 TTL dict**.

- 기존 도메인은 Redis 캐시(`risk_analysis` TTL 3600s, `service._fetch_foreign_price` TTL 86400s)를 쓰지만, SPEC-040은 명시적으로 in-memory TTL dict를 사용한다.
- 키: 포트폴리오 id + 포트폴리오 데이터 지문(holdings 구성 해시) 조합. 동일 포트폴리오·동일 데이터면 캐시 히트.
- TTL 만료 또는 데이터 변경 시 재생성. 생성 간격 제한(호출 제한)으로 Claude 과호출 방지.
- 모듈 레벨 dict는 CLAUDE.md "전역 상태 금지"와 상충 가능 → 캐시 전용 모듈 단일 책임 구조(스레드 안전 고려 또는 단일 워커 가정 명시)로 격리.

---

## 7. 마이그레이션 — 신규 테이블 없음

- 최신 리비전: **0024** (`0024_ai_recommendation_037.py`).
- SPEC-040은 코멘터리를 영속화하지 않고 in-memory 캐시만 사용 → **신규 마이그레이션 미도입**(0024 유지).
- 요청서 제약 일치: "No new DB tables/migrations".

---

## 8. 프론트엔드 패턴

- `frontend/src/api/portfolio.ts` + `.js` 쌍, `frontend/src/pages/Portfolio.tsx` + `.js` 쌍 **동시 수정**.
- 컴포넌트는 컴파일된 `.js` 형태로 커밋(예: `RiskAnalysisPanel.js`, `PortfolioScoreCard.js`).
- Portfolio.tsx는 패널 컴포넌트들을 import하여 통합(예: `RiskAnalysisPanel`, `PerformanceSummaryPanel`, `BenchmarkComparisonPanel`).
- SPEC-040 신규: `AICommentaryPanel`(.tsx + .js), `portfolio.ts/.js`에 `getAICommentary` API 래퍼 추가.
- API 래퍼: `API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'`, Bearer 토큰 헤더.

---

## 9. 테스트 패턴 (`tests/unit/test_ai_analysis.py`)

- `asyncio_mode = "auto"` — `@pytest.mark.asyncio` 불필요.
- DB는 `MagicMock`, Claude는 `AsyncMock`/`patch`로 모킹.
- 순수 함수(`_build_portfolio_data`)는 DB 없이 단위 테스트.
- 빈 포트폴리오 → Claude 미호출 검증, 사용자 식별 정보 미포함 검증.

SPEC-040 테스트: 코멘터리 조립 순수 함수(데이터 → 프롬프트 입력) 단위 테스트 + Claude 모킹 통합 테스트 + 캐시 히트/미스 + fallback + 소유권 404.

---

## 10. 브라운필드 제약 요약 (SPEC-040 적용)

| 제약 | 적용 |
|------|------|
| 패키지 | `backend/src/stock_picker/portfolio/` |
| 소유권 위반 | 404 (신규 코드 관례) |
| 마이그레이션 | 미도입 (0024 유지) |
| scipy | 금지 (수치 필요 시 numpy/math) |
| Claude 모델 | `claude-haiku-4-5` 재사용 (기존 키) |
| 캐싱 | in-memory TTL dict (Redis 금지) |
| 코멘터리 언어 | 한국어 |
| 면책 문구 | 모든 응답 부착 |
| AI 실패 | 대체 코멘터리 반환 (500 금지) |
| 프론트 | `.tsx` + `.js` 쌍 동시 생성 |
| 코드 주석 | 한국어 |
| REQ 접두사 | `REQ-CMNT-*` / `REQ-CMNT-NFR-*` (기존 접두사와 충돌 없음) |

### 기존 기능 중복 확인

- `POST /{id}/ai-analysis`(SPEC-026): 분산/리스크/개선 제안 **구조화 JSON** 반환. SPEC-040은 **자연어 코멘터리**(서술형 요약)로 목적·출력 형태가 다름. 026 데이터 빌더(`_build_portfolio_data`) 재사용하되 026을 대체하지 않음.
- `POST /{id}/recommendations`(SPEC-037): 종목 추천. 코멘터리와 무관.
- 경로·스키마명·REQ 접두사 모두 분리 → 충돌 없음.
