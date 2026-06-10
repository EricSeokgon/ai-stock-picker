# SPEC-STOCK-010 진행 상황 (Progress)

- **SPEC**: SPEC-STOCK-010 — Docker 컨테이너화 + 운영 환경 설정
- **Status**: IN_PROGRESS
- **Version**: 0.1.0
- **Created**: 2026-06-10
- **Updated**: 2026-06-11
- **Author**: ircp
- **Priority**: High
- **Phase**: Phase 11 (운영 인프라 — 첫 배포 인프라 SPEC)

## 단계 요약

| 단계 | 상태 |
|------|------|
| Plan (spec/tasks/acceptance 작성) | 완료 |
| Run (구현) | 진행 중 |
| Sync (문서화) | 대기 |

## 작업 진행 (tasks.md 동기화)

| ID | 설명 | 우선순위 | 상태 |
|----|------|---------|------|
| T-001 | health.py 신규 (DB/Redis 점검 `GET /health`, 무인증) | High | done |
| T-002 | main.py 수정 (health 라우터 등록 + CORS) | High | done |
| T-003 | backend/Dockerfile (멀티스테이지, uv, non-root, HEALTHCHECK) | High | done |
| T-004 | 백엔드 엔트리포인트 (alembic upgrade head + uvicorn) | High | done |
| T-005 | frontend/nginx.conf (SPA 폴백, /api 프록시, gzip, 캐시) | High | done |
| T-006 | frontend/Dockerfile (node:20-alpine → nginx:alpine) | High | done |
| T-007 | docker-compose.yml 확장 (backend/frontend 추가, healthcheck) | High | done |
| T-008 | redis_data named volume 추가 | Medium | done |
| T-009 | .env.example 확장 (SECRET_KEY/TELEGRAM/SMTP/CORS, 서비스명 기본값) | High | done |
| T-010 | backend/.dockerignore | Medium | done |
| T-011 | frontend/.dockerignore | Medium | done |
| T-012 | .gitignore .env 비커밋 보장 | Medium | done |
| T-013 | Redis graceful degradation 검증 | Medium | done |
| T-014 | DB 볼륨 영속성 검증 | Medium | done |
| T-015 | 전체 스택 통합 검증 (단일 명령 기동 + 회귀 없음) | High | done |

## 인수 기준 진행

- 총 AC: 15개 (AC-1 ~ AC-15)
- 충족: 15 / 15

## Re-planning Gate 추적 (Run 단계에서 갱신)

| 반복 | 충족 AC 누계 | 에러 델타 | 비고 |
|------|-------------|----------|------|
| (Run 시작 전) | 0 | - | PLANNING |
| Run #1 | 15 | 0 | 전체 구현 완료 — 모든 요구사항 충족, 백엔드 516개·프론트 136개 테스트 유지 |

## 메모

- [HARD] 기존 Python 소스는 `api/main.py`(+필요 시 `routes/__init__.py`) 외 비변경, 프론트 소스 비변경.
- [HARD] `docker compose up` 단일 명령 기동.
- 비자명 사실: ① `/health`는 `main.py`에 이미 인라인 존재 → 라우터로 치환·확장.
  ② 루트 `docker-compose.yml`은 postgres+redis만 존재 → backend/frontend 추가.
  ③ Claude 키 env는 `ANTHROPIC_API_KEY`(코드 일치, `CLAUDE_API_KEY` 아님).
  ④ DB URL은 `postgresql+asyncpg://` 드라이버, auth는 동기 엔진 파생.
- 테스트 베이스라인: 516 backend / 136 frontend 통과 유지 목표.
