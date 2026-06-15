# SPEC-STOCK-021 진행 상황 (Progress)

- **SPEC**: SPEC-STOCK-021 — 뉴스피드·AI 시장 템포 (News Feed & AI Market Sentiment, Phase 21)
- **상태(status)**: DONE
- **작성일**: 2026-06-15
- **작성자**: ircp
- **우선순위**: medium
- **개발 방법론**: TDD (RED-GREEN-REFACTOR, quality.yaml 기준)

---

## 핵심 결정 요약

- **신규 테이블/마이그레이션 없음** (마이그 0017 유지) — 기존 `articles`·`analysis_results`·
  `stock_mentions` 재사용. 요청서의 `news_articles`(마이그 0018) 거부(파괴적 중복).
- **신규 Claude 호출/수집기/feedparser 없음** — 기존 `ClaudeAnalysisClient`(haiku-4-5)·`CollectorService`
  (stdlib RSS) 재사용.
- **진짜 신규** = `GET /news/market-sentiment`(시장 템포 집계) · `GET /news?krx_code`(종목 필터) ·
  `POST /news/fetch`(무인증 수동 트리거) · Redis 캐시 · 프론트 `MarketSentimentWidget`.
- REQ 접두사: 기존 `REQ-NEWS-004~006`과 충돌 회피 위해 하위 스코프 사용
  (`REQ-NEWS-FEED/SENT/FETCH/CACHE/API/FE/NFR-*`).

---

## 마일스톤 체크리스트

- [x] M1 — 시장 감성 집계 `GET /news/market-sentiment` + 스키마 (REQ-NEWS-SENT-*)
- [x] M2 — `GET /news` 종목 필터 `?krx_code` (REQ-NEWS-FEED-*)
- [x] M3 — `POST /news/fetch` 무인증 수동 트리거 (REQ-NEWS-FETCH-*)
- [x] M4 — Redis 캐시 + 장애 폴백 (REQ-NEWS-CACHE-*)
- [x] M5 — 프론트 `MarketSentimentWidget` + `api/news.ts` + 종목별 뉴스 연동 (REQ-NEWS-FE-*)
- [x] M6 — 테스트 & 품질 게이트 (커버리지 달성, 기존 `GET /news` 회귀 없음)

---

## 반복 로그 (Iteration Log)

| 일시 | 단계 | 충족 AC 수 | 에러 델타 | 비고 |
|------|------|-----------|-----------|------|
| 2026-06-15 | PLANNING | 0 | 0 | SPEC 초안 작성. 브라운필드 분석 완료(뉴스/감성 인프라 기존 존재 확인). |
| 2026-06-15 | RED | 14 | +14 | test_news_feed.py 작성. 14개 테스트 실패 확인 (ModuleNotFoundError, ImportError). |
| 2026-06-15 | GREEN | 14 | 0 | sentiment_service.py, schemas.py 구현. 14/14 통과. 기존 565개 통과(5 pre-existing 제외). |
| 2026-06-15 | REFACTOR | 14 | 0 | news.py 라우터 확장(market-sentiment, krx_code 필터, /fetch). types.ts·api/news.ts·MarketSentimentWidget.tsx·MarketSentimentWidget.test.tsx 작성. 프론트 223개 통과. History.tsx에 위젯 통합. |

---

## 구현 산출물

### 백엔드 신규 파일
- `backend/src/stock_picker/news/__init__.py`
- `backend/src/stock_picker/news/sentiment_service.py` — 감성 집계, 종목 뉴스, 트리거 서비스
- `backend/tests/unit/test_news_feed.py` — 14개 단위 테스트

### 백엔드 수정 파일
- `backend/src/stock_picker/api/schemas.py` — `MarketSentimentResponse`, `NewsFetchResult`, `StockNewsItem` 추가
- `backend/src/stock_picker/api/routes/news.py` — `/market-sentiment`, `?krx_code`, `/fetch` 엔드포인트 추가

### 프론트엔드 신규 파일
- `frontend/src/api/news.ts` — `fetchMarketSentiment`, `fetchNewsByStock`, `triggerNewsFetch`
- `frontend/src/components/MarketSentimentWidget.tsx` — 시장 감성 위젯 컴포넌트
- `frontend/src/__tests__/MarketSentimentWidget.test.tsx` — 6개 Vitest 테스트

### 프론트엔드 수정 파일
- `frontend/src/types.ts` — `MarketSentimentResponse`, `NewsFetchResult` 타입 추가
- `frontend/src/pages/History.tsx` — MarketSentimentWidget 통합

---

## 다음 단계

구현 완료. /moai sync SPEC-STOCK-021로 문서 동기화 진행 가능.
