---
name: project-m2-phase2-backend
description: SPEC-STOCK-001 Phase 2 Backend (TASK-019~025) 구현 완료 — 섹터 트렌드, ETF 추천기, 배치 최적화, 장중 잡, 섹터/상세 API
metadata:
  type: project
---

## Phase 2 Backend 구현 완료 (TASK-019~025)

**Why:** 뉴스 기반 섹터 트렌드 집계 + ETF 추천 + 배치 최적화 + 장중 파이프라인 요구사항 충족.

**How to apply:** 이 SPEC의 다음 단계 작업 시 이미 구현된 모듈을 재사용할 것.

### 새로 생성된 파일

- `src/stock_picker/recommendation/trend_aggregator.py` — `compute_trend_score()`, `aggregate_by_articles()`
- `src/stock_picker/mapping/etf_master.py` — `load_etf_master(path)`
- `src/stock_picker/recommendation/etf.py` — `EtfRecommender.recommend(sector_trends)`
- `src/stock_picker/api/routes/sectors.py` — `GET /sectors/trends`
- `tests/fixtures/etf_master.json` — ETF 마스터 데이터 (8개 ETF)

### 수정된 파일

- `src/stock_picker/analysis/worker.py` — `BATCH_SIZE=5`, `run_batch()` 추가
- `src/stock_picker/analysis/prompt.py` — `BATCH_SYSTEM_PROMPT`, `build_batch_user_message()` 추가
- `src/stock_picker/scheduler/jobs.py` — `run_intraday_pipeline()`, `setup_scheduler()` 2잡으로 확장
- `src/stock_picker/api/main.py` — `sectors.router` 등록
- `src/stock_picker/api/schemas.py` — `SectorTrendItem`, `SectorTrendsResponse`, `ContributingNewsItem`, `RecommendationDetailResponse` 추가
- `src/stock_picker/api/routes/recommendations.py` — `GET /recommendations/{krx_code}` 추가

### 설계 결정

- 시간 감쇠 반감기 24시간: `weight = exp(-ln(2) * hours_elapsed / 24)`
- 트렌드 스코어 공식: `0.70 * normalized_sentiment + 0.30 * normalized_volume * time_decay`
- ETF 스코어: 커버하는 섹터 트렌드 스코어 평균
- 배치 실패 시 개별 폴백 (격리 계약 유지)
- 장중 잡: `hour="9-15", minute="*/30", timezone="Asia/Seoul"`

### 테스트 현황

- 전체 195개 테스트 통과 (195/195)
- ruff lint 0 오류
