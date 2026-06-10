---
id: SPEC-STOCK-010
version: 0.1.0
status: draft
created: 2026-06-10
updated: 2026-06-10
author: ircp
priority: high
issue_number: null
---

# SPEC-STOCK-010: Docker 컨테이너화 + 운영 환경 설정

## HISTORY

- 2026-06-10 (v0.1.0): 최초 초안. SPEC-STOCK-001~009(Phase 1~10) 기능 구현 완료 후
  배포 인프라가 전무한 상태에서 작성한 첫 운영 인프라 SPEC.
  - 핵심 동기: 9개 기능 SPEC이 모두 완료되었으나 시스템 전체를 일관되게 기동할 수 있는
    배포 수단이 없다. 백엔드는 로컬 `uv`/`uvicorn`, 프론트는 `npm run dev`, DB·Redis는
    `docker-compose.yml`(postgres+redis만 존재)로 따로따로 기동해야 하며, 운영 환경에서
    동작하는 프론트 정적 빌드·리버스 프록시·헬스 체크가 없다. 본 SPEC은 `docker compose up`
    단일 명령으로 DB·Redis·백엔드·프론트(nginx) 전체 스택을 기동할 수 있도록
    컨테이너화 및 운영 환경 설정을 제공한다.
  - 비자명 사실 반영: ① `api/main.py`에 `GET /health`가 이미 존재(`{"status": "ok"}`만 반환)
    → 본 SPEC은 이를 **DB·Redis 점검을 포함하도록 확장**(라우터 분리)한다.
    ② 루트 `docker-compose.yml`은 **postgres+redis 개발용 서비스만** 정의 → backend·frontend
    서비스를 **추가**한다(재정의 아님). ③ Claude API 키 환경변수는 코드상 **`ANTHROPIC_API_KEY`**
    (`config.py` `anthropic_api_key` 필수 필드)이며 `.env.example`도 이를 사용 →
    `CLAUDE_API_KEY`가 아니라 **`ANTHROPIC_API_KEY`로 통일**한다.

---

## 1. 개요 (Overview)

### 1.1 배경

`ai-stock-picker`는 다음 스택으로 구성된 한국 주식/ETF AI 추천 시스템이다.

- **백엔드**: Python 3.11 + FastAPI + SQLAlchemy 2.0(async, `+asyncpg`) + Alembic + APScheduler,
  패키지 매니저 `uv`, 진입점 `stock_picker.api.main:app`.
- **프론트엔드**: React 18 + TypeScript + Vite + Recharts, 패키지 매니저 `npm`.
- **인프라**: PostgreSQL 16 + Redis 7(선택적 캐시, 장애 시 graceful degradation).
- **AI**: Claude API(`anthropic` SDK, haiku 모델).

SPEC-001~009로 기능은 완성되었으나, 배포·운영을 위한 인프라가 없다. 현재 루트
`docker-compose.yml`은 `postgres`(16-alpine)·`redis`(7-alpine) **개발용 백킹 서비스만** 정의하고,
백엔드·프론트엔드는 컨테이너화되어 있지 않다. 프론트엔드는 운영용 정적 빌드/리버스 프록시 구성이 없다.

### 1.2 목표

- 백엔드(FastAPI)와 프론트엔드(React/Vite)를 각각 멀티스테이지 Docker 이미지로 빌드한다.
- `docker compose up` **단일 명령**으로 `db` + `redis` + `backend` + `frontend` 전체 스택을
  기동할 수 있도록 `docker-compose.yml`을 확장한다.
- 컨테이너 오케스트레이션이 의존성 순서(`db`/`redis` 준비 후 `backend`, `backend` 후 `frontend`)를
  `healthcheck` 조건으로 보장한다.
- DB·Redis 연결 상태를 점검하는 `GET /health` 엔드포인트로 컨테이너 헬스 체크를 지원한다.
- 운영 환경에 필요한 모든 환경변수를 `.env.example`에 문서화한다.
- nginx로 SPA 라우팅(모든 경로 → `index.html`)과 `/api` → 백엔드 리버스 프록시를 제공한다.

### 1.3 비목표 (Non-Goals)

본 SPEC은 WHAT/WHY를 정의하며 구현 세부(정확한 베이스 이미지 태그·레이어 분할 방식 등)는
Run 단계에 위임한다. 자세한 제외 항목은 §6을 참조한다.

---

## 2. 용어 (Glossary)

| 용어 | 정의 |
|------|------|
| 멀티스테이지 빌드 | `builder`(의존성 설치/컴파일)와 `runtime`(최종 실행) 스테이지를 분리해 최종 이미지 크기를 줄이는 Docker 빌드 기법 |
| graceful degradation | Redis 등 선택적 의존성이 실패해도 서비스가 중단되지 않고 축소된 기능으로 계속 동작하는 것 |
| SPA 라우팅 | 클라이언트 사이드 라우팅. 알 수 없는 경로 요청을 `index.html`로 폴백시켜 React Router가 처리하게 하는 방식 |
| 헬스 체크 | 컨테이너/오케스트레이터가 서비스의 정상 동작 여부를 주기적으로 확인하는 메커니즘 |
| 리버스 프록시 | nginx가 `/api` 요청을 백엔드 컨테이너로 전달하는 구성 |

---

## 3. 범위 (Scope)

### 3.1 In Scope

1. **백엔드 Dockerfile** (`backend/Dockerfile`) — 멀티스테이지, `uv` 의존성 설치, non-root 사용자, 헬스 체크.
2. **프론트엔드 Dockerfile** (`frontend/Dockerfile`) — `node:20-alpine` 빌더 → `nginx:alpine` 런타임.
3. **docker-compose.yml 확장**(프로젝트 루트) — `backend`·`frontend` 서비스 추가, `depends_on` healthcheck 조건, 볼륨·포트·env 주입.
4. **`.env.example` 확장**(프로젝트 루트) — 운영에 필요한 모든 환경변수와 플레이스홀더·기본값 문서화.
5. **헬스 체크 라우터** (`backend/src/stock_picker/api/routes/health.py`) — DB·Redis 점검 포함 `GET /health`.
6. **nginx 설정** (`frontend/nginx.conf`) — SPA 폴백, `/api` 프록시, gzip, 정적 자산 캐시 헤더.
7. **`.dockerignore`** — 백엔드·프론트엔드 각각.
8. `api/main.py` 수정 — 기존 인라인 `GET /health`를 신규 health 라우터로 치환 등록(무인증).

### 3.2 Out of Scope (§6 상세)

- 클라우드/오케스트레이터(Kubernetes, ECS, Swarm) 배포 매니페스트.
- CI/CD 파이프라인(GitHub Actions 등) 및 이미지 레지스트리 푸시.
- TLS/HTTPS 인증서·도메인·로드밸런서 구성.
- 시크릿 매니저(Vault 등) 연동, 운영 비밀값 실제 주입.
- 기존 Python/프론트 소스 비즈니스 로직 변경(§5 제약 참조).

---

## 4. 기술 접근 (Technical Approach) — 파일별

### 4.1 `backend/Dockerfile` (신규)

- **멀티스테이지**: `builder` 스테이지에서 `uv`로 의존성을 설치(`uv sync` 또는 `uv pip install`),
  `runtime` 스테이지(슬림 Python 3.11 베이스)에 가상환경/소스만 복사.
- **non-root 사용자**: 런타임 스테이지에서 전용 사용자(예: `appuser`)를 생성하고 `USER`로 전환.
- **헬스 체크**: `HEALTHCHECK` 지시어로 `GET /health`(또는 동등 명령) 점검.
- **실행**: `uvicorn stock_picker.api.main:app --host 0.0.0.0 --port 8000`.
- **Alembic**: 컨테이너 기동 시 마이그레이션(`alembic upgrade head`)을 엔트리포인트에서 선행 수행
  (구현 방식은 Run 단계 결정; DB healthcheck 통과 후 실행되도록 보장).

### 4.2 `frontend/Dockerfile` (신규)

- **빌더 스테이지**: `node:20-alpine`에서 `npm ci` → `npm run build`(Vite),
  운영 API URL은 빌드 시 주입(Vite 환경변수, 기본값은 `/api`로 nginx 프록시 경유).
- **런타임 스테이지**: `nginx:alpine`에 `dist/` 정적 산출물과 `nginx.conf` 복사.

### 4.3 `docker-compose.yml` (확장)

- **기존 보존**: `postgres`(16-alpine)·`redis`(7-alpine) 서비스 정의를 유지/정리.
  서비스 식별자는 본 SPEC에서 논리적으로 `db`(postgres)·`redis`로 참조한다(실제 키 명명은 Run 단계 확정,
  단 backend의 `DATABASE_URL`/`REDIS_URL` 호스트명과 일치해야 함).
- **신규 서비스**:
  - `backend`: `backend/Dockerfile` 빌드, `.env` 주입, `depends_on`에 `db`(`condition: service_healthy`)
    + `redis`(`condition: service_started` 또는 healthy), 포트 `8000:8000`.
  - `frontend`: `frontend/Dockerfile` 빌드, `depends_on: backend`, 포트 `3000:80`(컨테이너 nginx 80 → 호스트 3000).
- **healthcheck**: `db`(`pg_isready`)·`redis`(`redis-cli ping`)·`backend`(`/health`)에 healthcheck 정의.
- **볼륨**: `postgres_data`(DB 영속), `redis_data`(Redis 영속) named volume.
- **포트 매핑**: 5432(db), 6379(redis), 8000(backend), 3000(frontend).

### 4.4 `.env.example` (확장)

기존 키(`ANTHROPIC_API_KEY`, `DATABASE_URL`, `REDIS_URL`, `LOG_LEVEL`)를 유지하고 운영용 키를 추가한다.
모든 키는 플레이스홀더 또는 명확한 기본값/주석을 포함한다.

- `DATABASE_URL` — 기본 `postgresql+asyncpg://stock_picker:stock_picker@db:5432/stock_picker`
  (compose 내부에서는 호스트명 `db` 사용).
- `REDIS_URL` — 기본 `redis://redis:6379/0`.
- `ANTHROPIC_API_KEY` — 플레이스홀더(필수, 미설정 시 백엔드 기동 실패).
- `SECRET_KEY` — JWT 서명용(SPEC-002 auth). 플레이스홀더.
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` — 선택(미설정 시 텔레그램 비활성, 기존 동작 보존).
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` — 선택(이메일 알림용).
- `CORS_ORIGINS` — 프론트 오리진 허용 목록(기본 `http://localhost:3000`).
- `LOG_LEVEL` — 기본 `INFO`.

> [HARD] Claude API 키는 코드(`config.py`)와 일치하도록 **`ANTHROPIC_API_KEY`** 로 표기한다.
> 작업 지시의 `CLAUDE_API_KEY`는 사용하지 않는다(코드와 모순 방지).

### 4.5 `backend/src/stock_picker/api/routes/health.py` (신규)

- `GET /health` → `{"status": "ok", "db": "ok"|"error", "redis": "ok"|"unavailable"}`.
- **DB 점검**: `SELECT 1`을 실행하여 성공 시 `"ok"`, 실패 시 `"error"`.
- **Redis 점검**: `PING` 성공 시 `"ok"`, 실패/미연결 시 `"unavailable"`(에러 아님 — graceful).
- **인증 없음**: 헬스 체크는 무인증으로 호출 가능해야 한다.
- `db`가 `"error"`이면 전체 `status`는 비정상으로 간주(HTTP 상태 코드 처리 방식은 Run 단계 결정,
  단 컨테이너 healthcheck가 DB 장애를 감지할 수 있어야 함). Redis `"unavailable"`은 정상 기동을 막지 않는다.

### 4.6 `api/main.py` (수정 — 최소)

- 기존 인라인 `@app.get("/health")`(현재 `{"status": "ok"}` 반환)를 제거하고 신규 health 라우터를
  `app.include_router(...)`로 등록한다.
- CORS `allow_origins`는 `CORS_ORIGINS` 환경변수를 반영하도록 조정(운영 프론트 오리진 허용).
- 그 외 라우터 등록·텔레그램 기동 로직은 변경하지 않는다.

### 4.7 `frontend/nginx.conf` (신규)

- SPA 폴백: `location / { try_files $uri $uri/ /index.html; }`.
- API 프록시: `location /api/ { proxy_pass http://backend:8000/; }`(compose 내부 서비스명 `backend`).
- gzip 압축 활성화.
- 정적 자산(`.js`, `.css`, 이미지 등) 캐시 헤더(`Cache-Control`) 설정.

### 4.8 `.dockerignore` (신규 × 2)

- `backend/.dockerignore` — `.venv`, `__pycache__`, `*.pyc`, `tests/`, `.pytest_cache`, `.env`, `.git` 등 제외.
- `frontend/.dockerignore` — `node_modules`, `dist`, `.env`, `.git`, 빌드 캐시 제외.

---

## 5. 제약 (Constraints)

- [HARD] 기존 Python 소스 파일은 `api/main.py`(health 라우터 등록·CORS 조정)와
  필요 시 `api/routes/__init__.py`(라우터 export) **외에는 변경하지 않는다.**
- [HARD] 기존 프론트엔드 소스 파일은 변경하지 않는다(nginx 프록시 설정으로 API 경유를 처리).
- [HARD] `docker compose up` 단일 명령으로 전체 스택이 깨끗하게 기동되어야 한다(수동 추가 단계 없음).
- Redis 장애가 백엔드 기동을 막아서는 안 된다(기존 graceful degradation 보존 — `config.py`에서
  `redis_url`은 기본값이 있고, `/health`의 redis는 `"unavailable"`로만 표기).
- 모든 환경변수는 `.env.example`에 문서화된 기본값 또는 명확한 안내를 가진다.
- Claude API 키 환경변수명은 `ANTHROPIC_API_KEY`로 통일(코드 일치).
- compose 내부 `DATABASE_URL`/`REDIS_URL`의 호스트명은 compose 서비스명(`db`/`redis`)과 일치해야 한다.

---

## 6. 제외 항목 (Exclusions / What NOT to Build)

- **자동 매매/주문 실행** — 규제·책임 리스크로 본 프로젝트 전체에서 영구 제외(인프라 SPEC도 예외 없음).
- **Kubernetes/ECS/Swarm 매니페스트** — 단일 호스트 `docker compose` 범위로 한정.
- **CI/CD 파이프라인·이미지 레지스트리 푸시** — 본 SPEC은 로컬/단일 호스트 빌드·기동만 다룬다.
- **TLS/HTTPS·도메인·로드밸런서** — nginx는 평문 HTTP만 제공(운영 TLS는 별도 SPEC 후보).
- **시크릿 매니저 연동 및 실제 비밀값 주입** — `.env.example`은 플레이스홀더만 제공.
- **비즈니스 로직 변경** — 추천/스코어링/스케줄러/인증 등 기존 기능 동작은 변경하지 않는다.
- **모니터링/로깅 스택**(Prometheus, Grafana, ELK 등) — 헬스 체크 엔드포인트 외 관측성 인프라는 제외.

---

## 7. EARS 요구사항 (Requirements)

REQ 접두사: `REQ-DKR-*`(Docker 이미지/compose), `REQ-HC-*`(헬스 체크), `REQ-ENV-*`(환경변수),
`REQ-NGX-*`(nginx), `REQ-NFR-*`(비기능).

### 7.1 Docker 이미지 / Compose (REQ-DKR-*)

- **REQ-DKR-001** (Ubiquitous): 백엔드 Dockerfile은 멀티스테이지(builder + runtime) 구조로
  최종 런타임 이미지를 빌드 의존성과 분리하여 구성해야 한다(SHALL).
- **REQ-DKR-002** (Event-Driven): WHEN `docker build`로 `backend/Dockerfile`을 빌드할 때,
  시스템은 `uv`로 의존성을 설치하고 오류 없이 이미지를 생성해야 한다(SHALL).
- **REQ-DKR-003** (Ubiquitous): 백엔드·프론트엔드 런타임 컨테이너는 root가 아닌
  비특권 사용자(non-root)로 프로세스를 실행해야 한다(SHALL).
- **REQ-DKR-004** (Event-Driven): WHEN `docker build`로 `frontend/Dockerfile`을 빌드할 때,
  시스템은 `node:20-alpine`에서 Vite 운영 빌드를 수행하고 `nginx:alpine` 런타임에
  정적 산출물을 복사하여 이미지를 생성해야 한다(SHALL).
- **REQ-DKR-005** (Event-Driven): WHEN 사용자가 프로젝트 루트에서 `docker compose up`을 실행할 때,
  시스템은 `db`, `redis`, `backend`, `frontend` 네 서비스를 모두 기동해야 한다(SHALL).
- **REQ-DKR-006** (State-Driven): WHILE `backend` 서비스가 시작 중일 때,
  시스템은 `db` 서비스가 healthy 상태(`condition: service_healthy`)가 된 후에만
  `backend`를 기동해야 한다(SHALL).
- **REQ-DKR-007** (State-Driven): WHILE `frontend` 서비스가 시작 중일 때,
  시스템은 `backend` 서비스가 기동된 후에 `frontend`를 기동해야 한다(SHALL).
- **REQ-DKR-008** (Ubiquitous): 시스템은 PostgreSQL 데이터를 named volume(`postgres_data`)으로
  영속화하여 컨테이너 재시작 후에도 데이터가 보존되어야 한다(SHALL).
- **REQ-DKR-009** (Ubiquitous): 시스템은 Redis 데이터를 named volume(`redis_data`)으로
  영속화해야 한다(SHALL).
- **REQ-DKR-010** (Ubiquitous): docker-compose는 포트 5432(db), 6379(redis),
  8000(backend), 3000(frontend)을 호스트에 매핑해야 한다(SHALL).

### 7.2 헬스 체크 (REQ-HC-*)

- **REQ-HC-001** (Event-Driven): WHEN 클라이언트가 인증 없이 `GET /health`를 호출할 때,
  시스템은 `{"status", "db", "redis"}` 필드를 포함한 JSON을 응답해야 한다(SHALL).
- **REQ-HC-002** (Event-Driven): WHEN `/health`가 호출되어 DB 연결이 정상일 때,
  시스템은 `SELECT 1`을 실행하여 `"db": "ok"`를 반환해야 한다(SHALL).
- **REQ-HC-003** (Unwanted Behavior): IF DB 연결이 실패하면,
  THEN 시스템은 `"db": "error"`를 반환하고 전체 상태를 비정상으로 표시해야 한다(SHALL).
- **REQ-HC-004** (State-Driven): WHILE Redis가 연결 불가 상태일 때,
  시스템은 `"redis": "unavailable"`을 반환하되 `/health` 호출 자체는 실패시키지 않아야 한다(SHALL).
- **REQ-HC-005** (Event-Driven): WHEN compose의 `backend` healthcheck가 `/health`를 점검할 때,
  시스템은 DB 정상 시 컨테이너를 healthy로 표시할 수 있어야 한다(SHALL).

### 7.3 환경변수 (REQ-ENV-*)

- **REQ-ENV-001** (Ubiquitous): `.env.example`은 `DATABASE_URL`, `REDIS_URL`,
  `ANTHROPIC_API_KEY`, `SECRET_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`,
  `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `CORS_ORIGINS`, `LOG_LEVEL`을
  플레이스홀더 또는 기본값과 함께 문서화해야 한다(SHALL).
- **REQ-ENV-002** (Event-Driven): WHEN `docker compose up`이 실행될 때,
  시스템은 `.env` 파일의 환경변수를 `backend` 서비스에 주입해야 한다(SHALL).
- **REQ-ENV-003** (Unwanted Behavior): IF `ANTHROPIC_API_KEY`가 미설정이면,
  THEN 백엔드는 기동에 실패해야 한다(`config.py` 필수 필드 — 의도된 동작)(SHALL).
- **REQ-ENV-004** (Ubiquitous): `.env.example`의 `DATABASE_URL`·`REDIS_URL` 기본값은
  compose 내부 서비스명(`db`/`redis`)을 호스트로 사용해야 한다(SHALL).

### 7.4 nginx (REQ-NGX-*)

- **REQ-NGX-001** (Event-Driven): WHEN nginx가 정적 파일이 없는 경로 요청을 받을 때,
  시스템은 `try_files`로 `/index.html`을 반환하여 SPA 클라이언트 라우팅을 지원해야 한다(SHALL).
- **REQ-NGX-002** (Event-Driven): WHEN nginx가 `/api`로 시작하는 요청을 받을 때,
  시스템은 해당 요청을 `backend` 서비스(8000)로 프록시해야 한다(SHALL).
- **REQ-NGX-003** (Ubiquitous): nginx는 응답에 gzip 압축과 정적 자산 캐시 헤더를 적용해야 한다(SHALL).

### 7.5 비기능 (REQ-NFR-*)

- **REQ-NFR-001** (Ubiquitous): 멀티스테이지 빌드를 통해 런타임 이미지에서 빌드 전용 도구를 제외하여
  이미지 크기를 단일 스테이지 대비 축소해야 한다(SHALL).
- **REQ-NFR-002** (Ubiquitous): `.dockerignore`는 빌드 컨텍스트에서 `.venv`/`node_modules`/`.git`/`.env`
  등 불필요·민감 파일을 제외해야 한다(SHALL).
- **REQ-NFR-003** (Unwanted Behavior): IF 비밀값이 이미지 레이어나 VCS에 포함될 위험이 있으면,
  THEN 시스템은 `.env`를 `.dockerignore`·`.gitignore`로 제외하고 `.env.example`만 커밋해야 한다(SHALL).
- **REQ-NFR-004** (Ubiquitous): 기존 기능 동작(추천/스코어링/스케줄러/인증/텔레그램)은
  컨테이너화 후에도 변경 없이 보존되어야 한다(SHALL).

---

## 8. 비기능 요구 요약 (NFR Summary)

| 항목 | 기준 |
|------|------|
| 이미지 크기 | 멀티스테이지로 빌드 도구 제외, 런타임 이미지 최소화 |
| 보안 | non-root 실행, `.env` 비커밋, 비밀값 플레이스홀더화 |
| 기동성 | `docker compose up` 단일 명령, healthcheck 기반 순서 보장 |
| 회복성 | Redis 장애 시 graceful degradation 유지 |
| 영속성 | DB·Redis named volume, 재시작 후 데이터 보존 |
| 회귀 안전 | 기존 소스 비변경(허용 파일 외), 테스트 베이스라인(516 backend / 136 frontend) 유지 |

---

## 9. 의존성 및 참조

- SPEC-STOCK-001~009: 컨테이너화 대상 기능 전체(추천/인증/실시간/알림/캐시/탐색/섹터/피드백).
- `backend/src/stock_picker/config.py`: `anthropic_api_key`(필수)·`database_url`(필수)·`redis_url`·`log_level`.
- `backend/src/stock_picker/db/session.py`: `DATABASE_URL`(`+asyncpg`), auth용 동기 엔진 파생.
- `backend/src/stock_picker/api/deps.py`: `REDIS_URL`, `get_redis_client`/`get_cache`.
- 기존 `docker-compose.yml`(postgres+redis)·`.env.example`(ANTHROPIC_API_KEY 등) — 확장 대상.
