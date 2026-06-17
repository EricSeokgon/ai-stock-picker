---
id: SPEC-STOCK-021
version: 0.1.0
status: draft
created: 2026-06-15
updated: 2026-06-15
author: ircp
priority: medium
issue_number: null
---

# SPEC-STOCK-021 — 뉴스피드·AI 시장 템포 (News Feed & AI Market Sentiment, Phase 21)

## HISTORY

- 2026-06-15 (v0.1.0): 최초 작성. 한국 금융 뉴스를 수집·AI 감성분석하여 (1) 종목별 뉴스피드,
  (2) 전체 시장 감성(템포) 점수를 제공한다.
  **⚠️ 핵심 비자명 사실: 뉴스 수집·Claude 감성분석·종목 매핑·뉴스피드 인프라가 이미 대부분 존재한다.**
  본 SPEC은 이를 **재사용**하며, 요청서가 명시한 **신규 `news_articles` 테이블을 만들지 않는다**
  (이미 `articles`·`analysis_results`·`stock_mentions` 테이블이 존재). 따라서 **신규 마이그레이션이 없다**
  (마이그 0017 유지). 진짜 신규는 시장 감성 집계 엔드포인트·종목 필터·수동 트리거·프론트 위젯이다.
  충돌 정리는 §1.3·§2 참조.

---

## 1. 개요 (Overview)

### 1.1 문제 정의

사용자는 보유/관심 종목과 시장 전반에 대한 **뉴스 흐름과 분위기(템포)**를 빠르게 파악하고 싶어 한다.
요청된 산출물은 둘이다:

1. **종목별 뉴스피드** — 특정 종목(krx_code)을 언급한 최신 뉴스 목록(제목·출처·게시시각·감성 배지).
2. **AI 시장 감성(템포) 점수** — 최근 24시간 분석 기사의 평균 감성 점수 + 긍정/부정/중립 분포.

### 1.2 목표

기존 뉴스 수집·감성분석 파이프라인 위에 (a) 시장 감성 집계 엔드포인트, (b) 뉴스피드 종목 필터,
(c) 무인증 수동 수집/분석 트리거, (d) 프론트 시장 감성 게이지 위젯 + 종목별 뉴스 표시를 추가한다.

### 1.3 비자명 코드베이스 사실 (설계 근거) — **반드시 먼저 읽을 것**

이 기능은 **이미 구현된 뉴스/감성 인프라와 크게 중복**된다. 중복 재구축은 금지하고 재사용한다.

**이미 존재하므로 재구축 금지:**

- **뉴스 기사 테이블이 이미 존재한다 — `articles`(Article 모델).** 컬럼: `id`(Integer PK),
  `url`(String(2048) **UNIQUE** — URL 중복 수집 방지), `source`(String(100)), `title`(String(500)),
  `content`(Text nullable), `published_at`(DateTime tz nullable), `collected_at`(server_default now()),
  `status`(String(50) default 'collected' → 'analyzed' → 'done').
  → **본 SPEC은 신규 `news_articles` 테이블을 만들지 않는다.** 요청서의 "news_articles 테이블(마이그 0018)"은
    기존 `articles` 테이블로 충족된다. 신규 생성 시 **파괴적 중복**이 된다. 또한 요청서의 `url_hash`(sha256)
    중복 방지는 기존 `articles.url` UNIQUE 제약으로 이미 달성된다(별도 해시 컬럼 불필요).
- **AI 감성분석 결과 테이블이 이미 존재한다 — `analysis_results`(AnalysisResult 모델).** 컬럼:
  `article_id`(FK articles CASCADE), `sentiment`(String(20): positive/negative/neutral),
  `sentiment_score`(Numeric(4,3), **-1.0~1.0**), `sentiment_label`(String(20), 한국어 5단계 — SPEC-006),
  `sector_tags`(ARRAY), `keywords`(ARRAY), `summary`(Text), `tokens_used`, `analyzed_at`.
  → 요청서의 `sentiment`·`sentiment_score`·`ai_summary` 필드는 모두 기존 컬럼으로 충족. **신규 컬럼/테이블 없음.**
- **종목 언급 매핑이 이미 존재한다 — `stock_mentions`(StockMention 모델).** 컬럼: `article_id`(FK),
  `stock_name`, `krx_code`(String(10) nullable), `mention_status`. → 요청서의 `krx_codes`(콤마구분 문자열)
  대신 **정규화된 stock_mentions 조인으로 종목별 필터**를 구현(코드베이스 정합). 별도 문자열 컬럼 불필요.
- **Claude 감성분석 클라이언트가 이미 존재한다 — `analysis/client.py` `ClaudeAnalysisClient`.**
  `anthropic.AsyncAnthropic` + 모델 **`claude-haiku-4-5`** + 3회 재시도(지수 백오프) + 스키마 검증
  + 실패 시 None 반환(파이프라인 무중단). 시스템/유저 프롬프트는 `analysis/prompt.py`,
  출력 스키마는 `analysis/schema.py`. → **본 SPEC은 신규 Claude 호출 코드를 만들지 않고 재사용한다.**
  요청서의 인라인 `claude_client.messages.create(...)` 예시는 이 클라이언트로 충족(중복 호출 코드 금지).
- **뉴스 수집기가 이미 존재한다 — `collectors/`.** `CollectorService.collect_all(session)`이 3개 소스
  (`hankyung`·`mk` RSS, `naver`=연합뉴스 경제 RSS)를 **httpx 비동기 + stdlib `xml.etree`**로 수집,
  URL UNIQUE 멱등 저장, 소스별 실패 격리. → **요청서의 `feedparser` 의존성을 추가하지 않는다**
  (코드는 의도적으로 stdlib만 사용, `feedparser` 미설치). 신규 수집기/소스를 만들지 않고 재사용한다.
- **뉴스피드 엔드포인트가 이미 존재한다 — `api/routes/news.py` `GET /news`.** `limit`(기본 20)으로
  분석/수집 기사 최신순 반환, `NewsItem`(title·summary·sentiment·sentiment_label·source·url·published_at).
  → **본 SPEC은 `GET /news`를 재구축하지 않고 `krx_code` 필터만 확장한다.**
- **스케줄러 파이프라인이 이미 존재한다 — `scheduler/jobs.py`.** `collect_all`·`run_analysis`·
  `run_daily_pipeline`(06:00)·`run_intraday_pipeline`(09–15시 30분)이 수집→분석→추천을 구동한다.
  → **신규 수집/분석 잡을 만들지 않는다.** 30분 주기 수집·분석은 `run_intraday_pipeline`으로 이미 충족.

**진짜 신규 (본 SPEC 범위):**

- **시장 감성(템포) 집계 — `GET /news/market-sentiment`.** 최근 24시간 `analysis_results`의 평균
  `sentiment_score` + positive/negative/neutral 건수 분포 + 전체 라벨(예: 긍정/중립/부정 톤). 코드에 없다.
- **뉴스피드 종목 필터 — `GET /news?krx_code=...`.** 현재 `GET /news`는 `limit`만 지원하고 종목 필터가
  없다. `stock_mentions` 조인으로 특정 종목 언급 기사만 반환하는 분기를 추가.
- **무인증 수동 트리거 — `POST /news/fetch`.** 현재 수집/분석은 스케줄러 전용. 테스트/수동 갱신용으로
  `CollectorService.collect_all` + 분석을 1회 구동하는 무인증 엔드포인트를 추가.
- **종목별 뉴스 Redis 캐시** — `news:{krx_code}` TTL 1800s(요청서 지침). 기존 `api/deps.py` `get_cache`/
  `redis.asyncio` 패턴 재사용. 캐시 부재/장애 시 DB 직접 조회로 graceful degradation.
- **프론트 시장 감성 게이지 위젯 + 뉴스 리스트 + 종목별 뉴스** — 프론트에 뉴스 위젯/`api/news.ts`가
  **전무**(현재 news 프론트 코드 없음, Dashboard.tsx 없음). 신규.

### 1.4 코드베이스 정합 사실 (재사용 패턴)

- Redis: `config.py`에 `redis_url` 기본값, `api/deps.py`에 `get_redis_client`(redis.asyncio, REDIS_URL env)·
  `get_cache` 의존성 존재. 캐시 패턴은 prices.py/추천 캐시(`recommendations:{date}` TTL 1800s)와 동일하게 적용.
- Claude 모델은 `claude-haiku-4-5`로 통일(분석·추천 AI 동일). 신규 호출은 `ClaudeAnalysisClient` 재사용.
- 감성 5단계 라벨은 `analysis/sentiment_label.py` `score_to_label(score)` 재사용
  (매우긍정≥0.6/긍정≥0.2/중립>-0.2/부정>-0.6/매우부정). 시장 템포 라벨도 평균점수에 이 함수 적용 가능.
- 종목 필터 조인 경로: `StockMention(krx_code=...)` → `Article` → `AnalysisResult`
  (SPEC-008 섹터 상세와 동일한 조인 패턴). `krx_code`가 nullable이므로 NULL 매핑 기사는 제외.
- 무인증 엔드포인트 패턴: `GET /health`(health.py)·`POST /alerts/check`(general_alert)와 동일하게 인증 없음.
- 비동기 세션 주입: `get_session`(news.py·sectors.py 패턴). 수동 트리거는 `CollectorService` + `get_session`.

---

## 2. 설계 결정 (Design Decisions)

### 2.1 영속화 전략 — 신규 테이블·마이그레이션 없음

- 요청서의 `news_articles` 테이블(마이그 0018)은 **만들지 않는다.** 기존 `articles`(기사) +
  `analysis_results`(감성) + `stock_mentions`(종목 매핑) 3테이블이 요청서 스키마의 모든 필드를 충족한다.
- 따라서 **본 SPEC은 신규 마이그레이션을 추가하지 않는다(마이그 0017 유지).** SPEC-019(배당) 패턴과 동일.
- 모든 신규 기능(시장 감성 집계·종목 필터·수동 트리거)은 **기존 테이블에 대한 읽기/오케스트레이션**이다.

### 2.2 시장 감성(템포) 집계

- `GET /news/market-sentiment`는 최근 24시간(`analysis_results.analyzed_at >= now()-24h`) 분석 기사를 대상으로:
  - `avg_score`: 평균 `sentiment_score`(-1.0~1.0). 대상 기사 0건이면 `avg_score=null`, `label="데이터없음"`.
  - `breakdown`: positive/negative/neutral 각 건수 + 총 건수.
  - `label`: `score_to_label(avg_score)` 기반 시장 톤(예: "긍정"/"중립"/"부정"). 점수 None이면 라벨도 None.
  - `as_of`: 집계 기준 시각.
- 결과 Redis 캐시 `market_sentiment:24h` TTL 1800s(반복 호출 비용 절감). 캐시 장애 시 DB 직접 집계.

### 2.3 종목별 뉴스피드

- `GET /news?krx_code=XXXXXX&limit=N`: `krx_code` 제공 시 `stock_mentions.krx_code == krx_code` 인 기사만
  `Article`·`AnalysisResult` 조인하여 최신순 반환. 미제공 시 기존 전체 피드 동작 유지(하위호환).
- 종목별 결과는 Redis 캐시 `news:{krx_code}` TTL 1800s. 캐시 미스/장애 시 DB 조회.
- 응답 스키마는 기존 `NewsItem`/`NewsResponse` 재사용(필요 시 `krx_code` 필드만 추가).

### 2.4 수동 트리거

- `POST /news/fetch`(무인증)는 `CollectorService.collect_all` + 분석(`run_analysis` 경로) 1회 구동 후
  `{collected: int, analyzed: int}` 요약 반환. 수집/분석 실패는 graceful degradation(요약에 반영, 500 미발생).
- 스케줄러 `run_intraday_pipeline`/`run_analysis`와 **동일 서비스 함수**를 호출(중복 로직 금지).

### 2.5 감성 분석 호출

- 신규 Claude 호출 코드를 작성하지 않는다. 수집된 기사 분석은 기존 `analysis/` 워커·`ClaudeAnalysisClient`
  (`claude-haiku-4-5`) 경로를 재사용한다. 요청서의 `mentioned_stocks` JSON 항목은 기존 `stock_mentions`
  적재 경로로 충족(분석 워커가 이미 종목 매핑 생성).

---

## 3. 데이터 모델 (Data Model)

**신규 ORM 모델 없음. 신규 마이그레이션 없음(0017 유지).** 기존 테이블 재사용:

```
Article (articles)            — 기사: id, url(UNIQUE), source, title, content?, published_at?, collected_at, status
AnalysisResult (analysis_results) — 감성: article_id(FK), sentiment, sentiment_score(-1..1),
                                    sentiment_label?(5단계), sector_tags[], keywords[], summary?, analyzed_at
StockMention (stock_mentions) — 종목매핑: article_id(FK), stock_name, krx_code?(String(10)), mention_status
```

신규 응답 Pydantic v2 스키마(`api/schemas.py` 확장):

```
MarketSentimentResponse :
  avg_score: float | None           # 최근 24h 평균 감성 점수(-1.0~1.0), 대상 0건이면 None
  label: str | None                 # score_to_label(avg_score) 기반 시장 톤
  positive: int                     # 24h positive 기사 수
  negative: int
  neutral: int
  total: int
  as_of: datetime

# 종목 필터·수동 트리거는 기존 NewsResponse/NewsItem 재사용(필요 시 krx_code 필드만 추가).
NewsFetchResult :
  collected: int                    # 수집된 신규 기사 수
  analyzed: int                     # 분석 완료 기사 수
```

---

## 4. 요구사항 (EARS Requirements)

> REQ 접두사는 기존 수집 코드의 `REQ-NEWS-004~006`과 충돌을 피하기 위해 하위 스코프 접두사를 사용한다:
> `REQ-NEWS-FEED-*`(피드)·`REQ-NEWS-SENT-*`(시장감성)·`REQ-NEWS-FETCH-*`(트리거)·`REQ-NEWS-API-*`(API 계약)·
> `REQ-NEWS-FE-*`(프론트)·`REQ-NEWS-NFR-*`(비기능).

### 4.1 종목별 뉴스피드 (REQ-NEWS-FEED-*)

- REQ-NEWS-FEED-001 (Ubiquitous): The system shall expose news articles through the existing `GET /news`
  endpoint and shall not create a new news articles table.
- REQ-NEWS-FEED-002 (Event-Driven): WHEN a client requests `GET /news` with a `krx_code` query parameter,
  the system shall return only articles that mention that stock code (via the existing `stock_mentions`
  join), ordered by published time descending.
- REQ-NEWS-FEED-003 (Event-Driven): WHEN a client requests `GET /news` without a `krx_code`, the system
  shall preserve the existing latest-feed behavior (limit-only).
- REQ-NEWS-FEED-004 (Ubiquitous): The system shall include, for each news item, its title, source, published
  time, sentiment, and 5-level sentiment label when available.
- REQ-NEWS-FEED-005 (State-Driven): WHILE an article has no mapped `krx_code` in `stock_mentions`, the system
  shall exclude it from per-stock (`krx_code`-filtered) results.

### 4.2 시장 감성/템포 (REQ-NEWS-SENT-*)

- REQ-NEWS-SENT-001 (Event-Driven): WHEN a client requests `GET /news/market-sentiment`, the system shall
  compute the average `sentiment_score` over `analysis_results` analyzed within the last 24 hours.
- REQ-NEWS-SENT-002 (Ubiquitous): The system shall return the breakdown counts of positive, negative, and
  neutral analyzed articles for the last 24 hours together with the total count and an `as_of` timestamp.
- REQ-NEWS-SENT-003 (Event-Driven): WHEN an average score is available, the system shall derive a market
  tone label from it using the existing `score_to_label` mapping.
- REQ-NEWS-SENT-004 (State-Driven): WHILE there are no analyzed articles in the last 24 hours, the system
  shall return a null average score and a null/"데이터없음" label rather than failing.

### 4.3 수동 트리거 (REQ-NEWS-FETCH-*)

- REQ-NEWS-FETCH-001 (Event-Driven): WHEN a client sends `POST /news/fetch`, the system shall run the
  existing collector and analysis path once and return a summary of how many articles were collected and
  analyzed, without requiring authentication.
- REQ-NEWS-FETCH-002 (Ubiquitous): The system shall reuse the existing `CollectorService` and analysis
  worker and shall not add a new collector, news source, or duplicate Claude call code.
- REQ-NEWS-FETCH-003 (Unwanted): IF collection or analysis partially fails, THEN the system shall reflect
  the partial result in the summary and shall not return a server error.

### 4.4 캐싱 (REQ-NEWS-CACHE-*)

- REQ-NEWS-CACHE-001 (Ubiquitous): The system shall cache per-stock news results in Redis under
  `news:{krx_code}` with a TTL of 1800 seconds, reusing the existing cache dependency.
- REQ-NEWS-CACHE-002 (Ubiquitous): The system shall cache the market-sentiment aggregation in Redis with a
  TTL of 1800 seconds.
- REQ-NEWS-CACHE-003 (Unwanted): IF Redis is unavailable, THEN the system shall fall back to direct database
  queries without failing the request.

### 4.5 API 계약 (REQ-NEWS-API-*)

- REQ-NEWS-API-001 (Event-Driven): WHEN `GET /news`, `GET /news/market-sentiment`, or `POST /news/fetch` is
  called, the system shall respond without requiring authentication (read/utility endpoints).
- REQ-NEWS-API-002 (Ubiquitous): The system shall keep the existing `NewsResponse`/`NewsItem` response shape
  for `GET /news` and add only the per-stock filter and (if needed) a `krx_code` field.

### 4.6 프론트엔드 (REQ-NEWS-FE-*)

- REQ-NEWS-FE-001 (Ubiquitous): The system shall provide a market-sentiment widget that displays a
  color-coded gauge (positive/green, negative/red, neutral/gray) based on the market-sentiment score.
- REQ-NEWS-FE-002 (Ubiquitous): The system shall provide a recent-news list showing title, source, published
  time, and a sentiment badge.
- REQ-NEWS-FE-003 (Event-Driven): WHEN a user views a holding/watchlist stock's detail, the system shall
  show that stock's recent news via the `krx_code`-filtered feed.
- REQ-NEWS-FE-004 (State-Driven): WHILE news or sentiment data is loading, the UI shall show a loading state.
- REQ-NEWS-FE-005 (State-Driven): WHILE no news is available for a stock or the market, the UI shall show an
  empty-state message rather than an error.

### 4.7 비기능 (REQ-NEWS-NFR-*)

- REQ-NEWS-NFR-001 (Unwanted): IF any feature would execute or schedule trades or orders, THEN it shall NOT
  be built — automated trading is permanently excluded.
- REQ-NEWS-NFR-002 (Ubiquitous): The system shall not create a new `news_articles` table and shall not add a
  new database migration; it shall reuse `articles`, `analysis_results`, and `stock_mentions`.
- REQ-NEWS-NFR-003 (Ubiquitous): The system shall reuse the existing `ClaudeAnalysisClient`
  (`claude-haiku-4-5`) and shall not add a new Claude API call path or a new sentiment model.
- REQ-NEWS-NFR-004 (Ubiquitous): The system shall not add the `feedparser` dependency; RSS parsing reuses the
  existing stdlib-based collectors.
- REQ-NEWS-NFR-005 (State-Driven): WHILE market data, Claude, or Redis is unavailable, the system shall
  degrade gracefully (skip/empty) rather than failing the request.

---

## 5. Exclusions (What NOT to Build)

- **자동 매매·주문 실행** — 규제·책임 리스크로 영구 제외 (REQ-NEWS-NFR-001).
- **신규 `news_articles` 테이블** — 이미 `articles` 테이블 존재. 재생성 금지(파괴적 중복). 기존 재사용.
- **신규 마이그레이션(0018)** — 신규 테이블/컬럼이 없으므로 추가하지 않음(마이그 0017 유지, SPEC-019 패턴).
- **`url_hash`(sha256) 중복 방지 컬럼** — 기존 `articles.url` UNIQUE 제약으로 이미 달성. 별도 해시 불필요.
- **`krx_codes` 콤마구분 문자열 컬럼** — 정규화된 기존 `stock_mentions` 조인으로 종목 필터 구현. 비정규화 거부.
- **신규 Claude 호출 코드** — 기존 `ClaudeAnalysisClient`(haiku-4-5) 재사용. 인라인 messages.create 중복 금지.
- **`feedparser` 의존성** — 기존 collectors는 의도적으로 stdlib(`xml.etree`)만 사용. 추가 금지.
- **신규 수집기/뉴스 소스** — 기존 3개 RSS 소스(hankyung·mk·yonhap) 재사용. 신규 소스 추가는 범위 밖.
- **신규 수집/분석 스케줄러 잡** — `run_intraday_pipeline`(30분)·`run_analysis`가 이미 30분 주기 수집·분석을
  수행. 신규 타이머/잡 미도입(요청서의 "30분마다 수집" 백그라운드 잡은 기존 잡으로 충족).
- **`GET /news` 재구축** — 기존 엔드포인트에 `krx_code` 필터만 확장.
- **인증/소유권 기반 개인화 뉴스** — 뉴스/감성은 공개 읽기. 사용자별 뉴스 구독/필터는 범위 밖.
- **실시간 뉴스 푸시(WebSocket/웹푸시/알림 연동)** — 본 SPEC은 조회/집계만. 알림 연동은 범위 밖.
- **감성 시계열 차트·섹터별 감성·뉴스 검색·페이지네이션·번역·키워드 트렌드** — 범위 밖.

---

## 6. 영향 범위 (Affected Files)

### 신규
- `backend/src/stock_picker/api/routes/news.py` — `GET /news/market-sentiment`·`POST /news/fetch` 추가
  (동일 파일 확장이므로 엄밀히는 수정이나, 신규 엔드포인트). 시장 감성 집계 헬퍼 포함.
- `backend/tests/unit/test_news_feed.py` — 종목 필터·시장 감성 집계(0건 포함)·수동 트리거·캐시 폴백·
  무인증·graceful degradation 테스트.
- `frontend/src/api/news.ts` — 뉴스/시장감성 API 래퍼 + 타입.
- `frontend/src/components/MarketSentimentWidget.tsx` — 시장 감성 게이지 + 최근 뉴스 리스트 위젯.
- `frontend/src/__tests__/MarketSentimentWidget.test.tsx` — 프론트 테스트.

### 수정
- `backend/src/stock_picker/api/routes/news.py` — `GET /news`에 `krx_code` 필터 분기 추가.
- `backend/src/stock_picker/api/schemas.py` — `MarketSentimentResponse`·`NewsFetchResult` 스키마 추가
  (필요 시 `NewsItem`에 `krx_code` 필드).
- 종목별 뉴스 표시 연동: `frontend/src/pages/StockDetailPage.tsx`(종목 상세) 또는 Portfolio 상세에
  종목별 뉴스 섹션 추가, 메인 화면에 `MarketSentimentWidget` 배치(RUN에서 기존 라우팅과 정합 결정).

### 불변 (절대 수정 금지)
- `articles`·`analysis_results`·`stock_mentions` 테이블 스키마.
- `analysis/client.py`(ClaudeAnalysisClient)·`analysis/prompt.py`·`analysis/schema.py`·`sentiment_label.py`.
- `collectors/`(CollectorService·RSS·naver) — 수집기 일체.
- `scheduler/jobs.py` 기존 잡(`collect_all`·`run_analysis`·`run_*_pipeline`) — 신규 잡 미도입.
- 추천 산식·포트폴리오·알림 엔드포인트.

---

## 7. 마일스톤 (Milestones)

| 마일스톤 | 설명 | 우선순위 |
|----------|------|----------|
| M1 | 시장 감성 집계 `GET /news/market-sentiment`(24h 평균·분포·라벨·0건 처리) + `MarketSentimentResponse` 스키마 (REQ-NEWS-SENT-*) | High |
| M2 | `GET /news` 종목 필터(`?krx_code`, stock_mentions 조인, NULL 제외, 하위호환) (REQ-NEWS-FEED-*) | High |
| M3 | `POST /news/fetch` 무인증 수동 트리거(CollectorService + 분석 재사용, partial graceful) (REQ-NEWS-FETCH-*) | Medium |
| M4 | Redis 캐시(`news:{krx_code}`·`market_sentiment:24h` TTL 1800s, 장애 폴백) (REQ-NEWS-CACHE-*) | Medium |
| M5 | 프론트 `MarketSentimentWidget`(게이지+뉴스 리스트) + `api/news.ts` + 종목별 뉴스 연동 (REQ-NEWS-FE-*) | Medium |
| M6 | 테스트 & 품질 게이트 (커버리지 ≥85%, 0건·캐시 폴백·무인증·기존 `GET /news` 회귀·종목 NULL 제외) | High |

---

## 8. 위험 (Risks)

- **인프라 중복으로 인한 혼동/회귀** (최대 위험): 뉴스 수집·감성분석·뉴스피드가 이미 존재한다. 신규 코드가
  `news_articles` 테이블을 새로 만들거나 새 Claude 호출/수집기를 중복 정의하면 파괴적 중복·회귀가 발생.
  완화: §1.3·§5에서 재사용/불변 대상을 명시, M6 회귀 테스트로 기존 `GET /news` 보호.
- **REQ 접두사 충돌**: 기존 수집 코드가 `REQ-NEWS-004~006`을 사용. 본 SPEC은 하위 스코프 접두사
  (`REQ-NEWS-FEED-*` 등)로 분리하여 추적성 혼선 방지.
- **종목 매핑 빈약**: `stock_mentions.krx_code`는 매핑 실패 시 NULL. 인기 종목 외에는 뉴스가 적거나 없을 수
  있음. 완화: NULL 제외 + 종목 빈 결과는 empty-state로 정직 노출.
- **시장 감성 표본 편향**: 24h 분석 기사 수가 적으면 평균이 불안정. 완화: total 건수를 함께 노출하여
  사용자가 신뢰도를 판단하게 함. 0건 시 "데이터없음".
- **수동 트리거 비용**: `POST /news/fetch`가 수집+Claude 분석을 동기적으로 구동 → 응답 지연·토큰 비용.
  완화: 무인증이나 테스트/수동 용도임을 명시, 기존 잡과 동일 서비스 재사용으로 중복 호출 방지.
- **캐시-DB 정합**: 캐시 TTL 1800s 동안 신규 기사 미반영 가능. 완화: 읽기 캐시 특성으로 수용,
  `POST /news/fetch` 후 즉시성은 보장 대상 아님(비목표).
