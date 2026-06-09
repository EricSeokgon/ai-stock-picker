---
name: project-structure
description: ai-stock-picker 백엔드 M1/M2 완료 모듈 구조 및 핵심 설계 결정
metadata:
  type: project
---

M1 완료 모듈: db/models, db/session, analysis/schema, scoring/engine, scoring/normalize, scoring/reasoning, config

M2 완료 모듈 (TASK-008~014):
- collectors/base.py: RawArticle 데이터클래스, BaseCollector ABC (USER_AGENT 포함)
- collectors/rss.py: parse_rss_feed (xml.etree.ElementTree), HankyungCollector, MKCollector
- collectors/naver.py: NaverCollector
- collectors/service.py: CollectorService (ON CONFLICT DO NOTHING 멱등 저장)
- analysis/prompt.py: SYSTEM_PROMPT, build_user_message
- analysis/client.py: ClaudeAnalysisClient (MAX_RETRIES=3, 지수 백오프)
- analysis/worker.py: AnalysisWorker (개별 기사 실패 격리)
- mapping/krx_master.py: load_krx_master (CSV 로딩)
- mapping/mapper.py: StockMapper (긴 종목명 우선 완전 일치 매칭)
- mapping/prices.py: get_stock_price_data (run_in_executor 비동기 래퍼)
- recommendation/aggregator.py: StockAggregator
- recommendation/cache.py: RecommendationCache (TTL 1800초)
- recommendation/service.py: RecommendationService (집계+스코어+저장+캐시)

**Why:** xml.etree.ElementTree (stdlib) 사용 - feedparser 미사용 (의존성 최소화 명시 요구)
**How to apply:** RSS 파싱 시 항상 stdlib ET 사용. feedparser import 금지.

테스트 구조: tests/unit/ (mock 기반), tests/integration/ (mock+AsyncMock 기반, Docker 없이 실행 가능)
픽스처: tests/fixtures/sample_rss.xml, claude_response.json, krx_master.csv

가중치: sentiment=0.40, volume=0.20, momentum=0.25, anomaly=0.15

SPEC-STOCK-002 Phase B~D 완료 (2026-06-09):
- db/models.py: TelegramSubscription, Portfolio, PortfolioHolding, BacktestRun, BacktestDailyResult 추가
- alembic/versions/0003~0005: 마이그레이션 파일 생성
- telegram/: handlers.py, bot.py (별도 스레드 폴링), notifier.py
- portfolio/: service.py (동기 Session), router.py, schemas.py
- backtest/: metrics.py (CAGR/MDD/Sharpe), runner.py (asyncio.create_task), router.py, schemas.py
- api/main.py: portfolio_router, backtest_router 등록, TELEGRAM_BOT_TOKEN 조건부 봇 시작

**핵심 설계 결정:**
- auth와 동일하게 동기 Session 사용 (TestClient 호환, BigInteger → Integer 주의)
- 텔레그램 봇은 threading.Thread(daemon=True)로 FastAPI 이벤트 루프와 격리
- FinanceDataReader 호출은 run_in_executor로 래핑 (동기 블로킹 함수)
- backtest runner: run_in_executor(None, _fetch_price_data, ...) 패턴

테스트 결과: 유닛 31 + 통합 24 = 55개 신규 테스트 모두 통과
기존 auth 테스트 31개 회귀 없음
