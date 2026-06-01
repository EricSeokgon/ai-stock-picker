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
