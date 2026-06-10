# SPEC-STOCK-010 작업 목록 (Tasks)

Docker 컨테이너화 + 운영 환경 설정. 모든 작업 초기 상태는 `pending`.

우선순위: High = 단일 명령 기동의 핵심 경로, Medium = 품질·운영 보강, Low = 최적화.

## 작업 테이블

| ID | 설명 | 우선순위 | 상태 | 연결 AC |
|----|------|---------|------|---------|
| T-001 | `backend/src/stock_picker/api/routes/health.py` 신규 — DB(`SELECT 1`)·Redis(`PING`) 점검 포함 `GET /health`, 무인증 | High | pending | AC-3, AC-8 |
| T-002 | `api/main.py` 수정 — 기존 인라인 `/health` 제거, health 라우터 등록, CORS를 `CORS_ORIGINS` 반영 (필요 시 `routes/__init__.py` export) | High | pending | AC-3, AC-5 |
| T-003 | `backend/Dockerfile` 신규 — 멀티스테이지(builder+runtime), `uv` 의존성 설치, non-root 사용자, `HEALTHCHECK`, uvicorn 실행 | High | pending | AC-1, AC-9, AC-10 |
| T-004 | 백엔드 엔트리포인트 — 기동 시 `alembic upgrade head` 선행(DB healthy 후), 그 후 uvicorn 기동 | High | pending | AC-2, AC-7 |
| T-005 | `frontend/nginx.conf` 신규 — SPA `try_files` 폴백, `/api` → backend 프록시, gzip, 정적 자산 캐시 헤더 | High | pending | AC-4, AC-6 |
| T-006 | `frontend/Dockerfile` 신규 — `node:20-alpine` 빌더(`npm ci`+`npm run build`) → `nginx:alpine` 런타임(`dist/`+`nginx.conf` 복사) | High | pending | AC-4, AC-10 |
| T-007 | `docker-compose.yml` 확장 — `db`/`redis` healthcheck 추가, `backend`·`frontend` 서비스 추가, `depends_on` 조건, 볼륨·포트·`.env` 주입 | High | pending | AC-2, AC-6, AC-7, AC-11 |
| T-008 | `redis_data` named volume 추가 — Redis 영속화 | Medium | pending | AC-12 |
| T-009 | `.env.example` 확장 — `SECRET_KEY`/`TELEGRAM_*`/`SMTP_*`/`CORS_ORIGINS` 추가, `DATABASE_URL`·`REDIS_URL` 기본값을 compose 서비스명(`db`/`redis`)으로, `ANTHROPIC_API_KEY` 유지 | High | pending | AC-13 |
| T-010 | `backend/.dockerignore` 신규 — `.venv`/`__pycache__`/`tests`/`.env`/`.git` 제외 | Medium | pending | AC-14 |
| T-011 | `frontend/.dockerignore` 신규 — `node_modules`/`dist`/`.env`/`.git` 제외 | Medium | pending | AC-14 |
| T-012 | `.gitignore` 확인 — `.env` 비커밋 보장(없으면 추가) | Medium | pending | AC-14 |
| T-013 | Redis graceful degradation 검증 — Redis 중단 상태에서 backend 기동·`/health` `"unavailable"` 확인 | Medium | pending | AC-8 |
| T-014 | DB 볼륨 영속성 검증 — 데이터 적재 후 컨테이너 재시작 시 데이터 보존 확인 | Medium | pending | AC-12 |
| T-015 | 전체 스택 통합 검증 — `docker compose up` 단일 명령 기동, 프론트→nginx→backend 경로·SPA 라우팅 확인, 기존 테스트 베이스라인 회귀 없음 | High | pending | AC-2, AC-5, AC-6, AC-15 |

## 파일 영향 요약

신규:
- `backend/Dockerfile`, `backend/.dockerignore`
- `backend/src/stock_picker/api/routes/health.py`
- `frontend/Dockerfile`, `frontend/.dockerignore`, `frontend/nginx.conf`

수정:
- `docker-compose.yml`(확장), `.env.example`(확장)
- `backend/src/stock_picker/api/main.py`(health 라우터 등록 + CORS)
- `backend/src/stock_picker/api/routes/__init__.py`(필요 시 export)
- `.gitignore`(필요 시 `.env` 추가)

[HARD] 위 목록 외 기존 Python/프론트 소스 비변경.
