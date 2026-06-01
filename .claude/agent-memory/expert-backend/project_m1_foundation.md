---
name: project-m1-foundation
description: SPEC-STOCK-001 M1 Foundation 구현 완료 상태 및 핵심 결정사항
metadata:
  type: project
---

M1 Foundation + Core Logic 구현 완료 (2026-06-01).

**Why:** SPEC-STOCK-001 Phase 1 - 한국 주식/ETF 추천 시스템 기반 레이어

**How to apply:** M2 이후 구현 시 이 결정사항을 참고할 것.

## 핵심 결정사항

- Python 3.11 (uv 관리, `/home/sklee/.local/bin/uv`)
- 가상환경: `backend/.venv/`
- 패키지 설치: `uv pip install -e ".[dev]"` (editable 모드)
- config.py에서 module-level `settings = Settings()` 제거 — 테스트 격리를 위해 Settings 클래스만 export
- scoring/normalize.py: time_decay_weights에서 timezone-naive/aware 혼합 케이스 처리 포함
- testcontainers는 Docker 없이 pytest.skip으로 건너뜀 (conftest.py)

## 파일 목록 (M1)

- `backend/pyproject.toml` — 프로젝트 의존성 정의
- `backend/.venv/` — Python 3.11 가상환경
- `backend/alembic.ini` — Alembic 설정
- `backend/alembic/env.py` — 비동기 마이그레이션 환경
- `backend/alembic/versions/0001_initial_tables.py` — 초기 5개 테이블 생성
- `backend/src/stock_picker/config.py` — pydantic-settings 환경변수 설정
- `backend/src/stock_picker/db/base.py` — SQLAlchemy DeclarativeBase
- `backend/src/stock_picker/db/models.py` — 5개 ORM 모델
- `backend/src/stock_picker/db/session.py` — 비동기 세션 관리
- `backend/src/stock_picker/scoring/normalize.py` — minmax_normalize, time_decay_weights
- `backend/src/stock_picker/scoring/engine.py` — calculate_stock_score, rank_stocks
- `backend/src/stock_picker/scoring/reasoning.py` — generate_reasoning (한국어)
- `backend/src/stock_picker/analysis/schema.py` — ClaudeAnalysisOutput Pydantic v2 모델
- `docker-compose.yml`, `.env.example` — 인프라 설정
- `backend/tests/conftest.py` — DB 픽스처 (Docker 선택적)
- `backend/tests/unit/test_config.py` — 6개 테스트
- `backend/tests/unit/test_models.py` — 22개 테스트
- `backend/tests/unit/test_normalize.py` — 14개 테스트
- `backend/tests/unit/test_engine.py` — 16개 테스트
- `backend/tests/unit/test_reasoning.py` — 9개 테스트
- `backend/tests/unit/test_schema.py` — 13개 테스트

## 커버리지

M1 대상 모듈 커버리지: 96.51% (목표 85% 초과)
