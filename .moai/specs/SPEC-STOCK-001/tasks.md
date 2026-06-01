# Task Decomposition
SPEC: SPEC-STOCK-001

## 마일스톤 구성

- **M1** (TASK-001~007): Foundation + Core Logic — 완료
- **M2** (TASK-008~014): I/O Layer + Integration — 완료
- **M3** (TASK-015~018): API + Frontend — 완료
- **M4** (TASK-019~025): Phase 2 Backend (섹터·ETF·배치·장중갱신·상세API)
- **M5** (TASK-026~028): Phase 2 Frontend (차트·상세모달·ETF섹션)

## Phase 2 설계 상수 (사용자 확정)
- 시간 감쇠 반감기: 24시간 (exp decay, half_life_hours=24)

---

- **M1** (TASK-001~007): Foundation + Core Logic (순수 함수 우선)
- **M2** (TASK-008~014): I/O Layer + Integration (외부 의존 mock)
- **M3** (TASK-015~018): API + Frontend

---

## M1: Foundation + Core Logic

| Task ID | Description | Requirement | Dependencies | Planned Files | Status |
|---------|-------------|-------------|--------------|---------------|--------|
| TASK-001 | 프로젝트 셋업 (pyproject.toml, docker-compose, .env.example, frontend/package.json) | 인프라 | - | backend/pyproject.toml, docker-compose.yml, .env.example, frontend/package.json, frontend/vite.config.ts | pending |
| TASK-002 | DB ORM 모델 5개 + Alembic 마이그레이션 | plan §2 | TASK-001 | backend/src/stock_picker/db/base.py, db/models.py, alembic/versions/0001_initial.py, alembic/env.py, alembic.ini | pending |
| TASK-003 | DB 비동기 세션 관리 + pytest fixtures | REQ-NFR | TASK-002 | backend/src/stock_picker/db/session.py, backend/tests/conftest.py | pending |
| TASK-004 | 정규화 유틸 (min-max, time-decay, 0~1 범위) | plan §3.1 | TASK-001 | backend/src/stock_picker/scoring/normalize.py, backend/tests/unit/test_normalize.py | pending |
| TASK-005 | 스코어링 엔진 (가중 합산 공식, 순수 함수) | AC-5, REQ-REC-001 | TASK-004 | backend/src/stock_picker/scoring/engine.py, backend/tests/unit/test_engine.py | pending |
| TASK-006 | 근거 설명 생성 | REQ-REC-004 | TASK-005 | backend/src/stock_picker/scoring/reasoning.py, backend/tests/unit/test_reasoning.py | pending |
| TASK-007 | Claude 출력 JSON 스키마 (pydantic 검증) | REQ-AI-003, E-6 | TASK-001 | backend/src/stock_picker/analysis/schema.py, backend/tests/unit/test_schema.py | pending |

## M2: I/O Layer + Integration

| Task ID | Description | Requirement | Dependencies | Planned Files | Status |
|---------|-------------|-------------|--------------|---------------|--------|
| TASK-008 | RSS/네이버 수집기 | REQ-NEWS-001,003,006 | TASK-002 | backend/src/stock_picker/collectors/base.py, collectors/rss.py, collectors/naver.py, tests/fixtures/sample_rss.xml | pending |
| TASK-009 | 수집 오케스트레이션 (멱등 + 부분실패) | AC-1, AC-2 | TASK-008, TASK-003 | backend/src/stock_picker/collectors/service.py, tests/integration/test_collector_service.py | pending |
| TASK-010 | Claude 분석 클라이언트 (재시도/백오프) | AC-4, REQ-AI-005 | TASK-007 | backend/src/stock_picker/analysis/client.py, analysis/prompt.py, tests/unit/test_client.py, tests/fixtures/claude_response.json | pending |
| TASK-011 | 분석 배치 워커 | AC-3, REQ-AI-001,006 | TASK-010, TASK-003 | backend/src/stock_picker/analysis/worker.py, tests/integration/test_worker.py | pending |
| TASK-012 | KRX 종목 매핑 | REQ-MAP-001,003, E-1 | TASK-002 | backend/src/stock_picker/mapping/krx_master.py, mapping/mapper.py, tests/unit/test_mapper.py, tests/fixtures/krx_master.csv | pending |
| TASK-013 | FinanceDataReader 시세 래퍼 | REQ-MAP-002, E-5 | TASK-001 | backend/src/stock_picker/mapping/prices.py, tests/unit/test_prices.py | pending |
| TASK-014 | 추천 서비스 (집계+저장+Redis 캐시) | AC-5, REQ-REC-002,005 | TASK-005, TASK-011, TASK-012, TASK-013 | backend/src/stock_picker/recommendation/aggregator.py, recommendation/service.py, recommendation/cache.py, tests/integration/test_recommendation.py | pending |

## M3: API + Frontend

| Task ID | Description | Requirement | Dependencies | Planned Files | Status |
|---------|-------------|-------------|--------------|---------------|--------|
| TASK-015 | FastAPI 엔드포인트 (/recommendations, /news) | AC-7, AC-10, REQ-WEB-001,004,006 | TASK-014 | backend/src/stock_picker/api/main.py, api/deps.py, api/schemas.py, api/routes/recommendations.py, api/routes/news.py, tests/integration/test_api.py | pending |
| TASK-016 | APScheduler 배치 (06:00 트리거) | AC-1, REQ-NEWS-001 | TASK-009, TASK-011, TASK-014 | backend/src/stock_picker/scheduler/jobs.py, tests/integration/test_scheduler.py | pending |
| TASK-017 | React API 클라이언트 + TypeScript 타입 | REQ-WEB-001 | TASK-015 | frontend/src/api/client.ts, frontend/src/types.ts, frontend/src/__tests__/client.test.ts | pending |
| TASK-018 | 대시보드 컴포넌트 (리스트+뉴스+면책고지+준비중) | AC-7, AC-10, REQ-WEB-004,005 | TASK-017 | frontend/src/components/RecommendationList.tsx, NewsFeed.tsx, Disclaimer.tsx, DataPreparingState.tsx, frontend/src/App.tsx, tests | pending |
