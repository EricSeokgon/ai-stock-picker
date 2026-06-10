# SPEC-STOCK-010 인수 기준 (Acceptance Criteria)

EARS 기반·테스트 가능한 인수 기준. 각 AC는 Given-When-Then으로 검증 시나리오를 제공한다.

## AC 테이블

| AC | EARS 유형 | 기준 (검증 가능) | 연결 REQ |
|----|----------|------------------|----------|
| AC-1 | Event-Driven | `docker build -f backend/Dockerfile`가 오류 없이 완료되고 멀티스테이지 이미지가 생성된다 | REQ-DKR-001, REQ-DKR-002 |
| AC-2 | Event-Driven | 프로젝트 루트에서 `docker compose up`이 `db`/`redis`/`backend`/`frontend` 4개 서비스를 모두 기동한다 | REQ-DKR-005 |
| AC-3 | Event-Driven | 인증 없이 `GET /health` 호출 시 `{"status","db","redis"}` 필드를 포함한 JSON이 응답된다 | REQ-HC-001 |
| AC-4 | Event-Driven | nginx가 임의의 존재하지 않는 경로(예: `/portfolio`) 요청에 `index.html`을 반환하여 SPA 라우팅이 동작한다 | REQ-NGX-001 |
| AC-5 | Event-Driven | 프론트엔드 `/api/...` 요청이 nginx 프록시를 거쳐 backend(8000)에서 응답된다 | REQ-NGX-002 |
| AC-6 | Event-Driven | 호스트 `http://localhost:3000`에서 프론트가 로드되고 backend API 데이터가 화면에 표시된다 | REQ-DKR-007, REQ-DKR-010 |
| AC-7 | State-Driven | `backend`는 `db`가 healthy가 된 후에만 기동되며, 기동 시 `alembic upgrade head`가 선행된다 | REQ-DKR-006 |
| AC-8 | State-Driven | Redis 중단 상태에서도 backend가 기동되고 `/health`의 `redis`가 `"unavailable"`로 표시된다(`/health` 자체는 성공) | REQ-HC-004 |
| AC-9 | Ubiquitous | `backend`/`frontend` 런타임 컨테이너 내 주 프로세스가 root가 아닌 사용자로 실행된다 | REQ-DKR-003 |
| AC-10 | Ubiquitous | 멀티스테이지 빌드로 런타임 이미지에 빌드 전용 도구가 포함되지 않는다 | REQ-NFR-001, REQ-DKR-004 |
| AC-11 | Event-Driven | `.env`의 환경변수가 `docker compose up` 시 `backend` 서비스에 주입된다 | REQ-ENV-002 |
| AC-12 | State-Driven | DB·Redis named volume에 의해 컨테이너 재시작 후에도 적재된 데이터가 보존된다 | REQ-DKR-008, REQ-DKR-009 |
| AC-13 | Ubiquitous | `.env.example`이 모든 필수/선택 환경변수를 플레이스홀더·기본값과 함께 문서화한다 | REQ-ENV-001, REQ-ENV-004 |
| AC-14 | Ubiquitous | `.dockerignore`가 `.venv`/`node_modules`/`.git`/`.env`를 빌드 컨텍스트에서 제외하고 `.env`는 VCS에 커밋되지 않는다 | REQ-NFR-002, REQ-NFR-003 |
| AC-15 | Unwanted Behavior | IF DB 연결이 실패하면 `/health`가 `"db":"error"`를 반환하고 backend healthcheck가 비정상을 감지한다 | REQ-HC-003, REQ-HC-005 |

---

## Given-When-Then 시나리오

### AC-1: 백엔드 이미지 빌드
- **Given** `backend/Dockerfile`과 소스가 존재한다
- **When** `docker build -f backend/Dockerfile backend/`를 실행한다
- **Then** 빌드가 오류 없이 완료되고 `builder`/`runtime` 두 스테이지로 구성된 이미지가 생성된다

### AC-2: 단일 명령 전체 스택 기동
- **Given** `docker-compose.yml`과 유효한 `.env`(필수 키 설정)가 루트에 존재한다
- **When** `docker compose up`을 실행한다
- **Then** `db`, `redis`, `backend`, `frontend` 4개 서비스가 추가 수동 단계 없이 모두 기동되고 healthy/running 상태가 된다

### AC-3: 헬스 체크 응답
- **Given** backend 컨테이너가 기동되어 있고 DB·Redis가 정상이다
- **When** 인증 헤더 없이 `GET http://localhost:8000/health`를 호출한다
- **Then** HTTP 200과 `{"status":"ok","db":"ok","redis":"ok"}` 형태의 JSON이 반환된다

### AC-4: SPA 라우팅 폴백
- **Given** frontend(nginx) 컨테이너가 기동되어 있다
- **When** 브라우저로 `http://localhost:3000/portfolio`(정적 파일 없는 경로)를 직접 요청한다
- **Then** nginx가 `index.html`을 반환하고 React Router가 해당 화면을 렌더한다(404 아님)

### AC-5: API 리버스 프록시
- **Given** frontend·backend 컨테이너가 기동되어 있다
- **When** 프론트가 `GET http://localhost:3000/api/recommendations`(또는 동등 경로)를 호출한다
- **Then** nginx가 요청을 `backend:8000`으로 프록시하고 backend의 응답이 그대로 전달된다

### AC-6: 프론트 통합 로드
- **Given** 전체 스택이 `docker compose up`으로 기동되어 있다
- **When** 브라우저로 `http://localhost:3000`에 접속한다
- **Then** 대시보드가 로드되고 backend API로부터 받은 추천 데이터가 화면에 표시된다

### AC-7: 의존성 순서 + 마이그레이션
- **Given** `backend`가 `db`에 `condition: service_healthy`로 의존한다
- **When** `docker compose up`을 처음(빈 볼륨) 실행한다
- **Then** `db`가 healthy가 된 후 `backend`가 기동되며, uvicorn 시작 전에 `alembic upgrade head`가 성공적으로 수행된다

### AC-8: Redis graceful degradation
- **Given** 전체 스택이 기동된 상태에서 `redis` 컨테이너를 중지한다(`docker compose stop redis`)
- **When** `GET /health`를 호출한다
- **Then** backend는 계속 실행 중이고 응답의 `redis`가 `"unavailable"`이며, `/health` 호출 자체는 실패하지 않는다

### AC-9: non-root 실행
- **Given** backend/frontend 컨테이너가 실행 중이다
- **When** `docker compose exec backend whoami`(및 frontend 동등 확인)를 실행한다
- **Then** 반환된 사용자가 `root`가 아니다

### AC-10: 멀티스테이지 이미지 슬림화
- **Given** backend·frontend 이미지가 빌드되어 있다
- **When** `docker history`/`docker image inspect`로 런타임 레이어를 확인한다
- **Then** 런타임 이미지에 `uv`/빌드 도구(backend)·`node`/`npm`(frontend) 빌드 전용 도구가 포함되지 않는다(런타임은 슬림 Python / nginx 기반)

### AC-11: 환경변수 주입
- **Given** `.env`에 `ANTHROPIC_API_KEY`, `SECRET_KEY` 등이 설정되어 있다
- **When** `docker compose up` 후 `docker compose exec backend env`로 확인한다
- **Then** `.env`에 정의된 변수가 backend 컨테이너 환경에 주입되어 있다

### AC-12: 볼륨 영속성
- **Given** backend가 기동되고 DB에 데이터가 적재되어 있다
- **When** `docker compose down`(볼륨 미삭제) 후 다시 `docker compose up`을 실행한다
- **Then** 이전에 적재된 DB 데이터가 보존되어 있다(named volume `postgres_data` 영속)

### AC-13: 환경변수 문서화
- **Given** `.env.example`이 루트에 존재한다
- **When** 파일을 검토한다
- **Then** `DATABASE_URL`, `REDIS_URL`, `ANTHROPIC_API_KEY`, `SECRET_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `SMTP_HOST/PORT/USER/PASSWORD`, `CORS_ORIGINS`, `LOG_LEVEL`이 모두 플레이스홀더 또는 기본값과 함께 존재하고, `DATABASE_URL`·`REDIS_URL` 기본값 호스트가 `db`/`redis`이다

### AC-14: 빌드 컨텍스트 제외 + 비밀값 보호
- **Given** `backend/.dockerignore`, `frontend/.dockerignore`, `.gitignore`가 존재한다
- **When** 빌드 컨텍스트와 git 추적 상태를 확인한다
- **Then** `.venv`/`__pycache__`/`node_modules`/`dist`/`.git`/`.env`가 빌드 컨텍스트에서 제외되고, `.env`는 git에 추적되지 않으며 `.env.example`만 커밋된다

### AC-15: DB 장애 감지
- **Given** 전체 스택이 기동된 상태에서 `db` 컨테이너를 중지한다(`docker compose stop db`)
- **When** `GET /health`를 호출한다
- **Then** 응답의 `db`가 `"error"`이고 전체 `status`가 비정상으로 표시되며, backend healthcheck가 비정상을 감지한다

---

## Definition of Done

- [ ] 신규 6개 파일 생성: `backend/Dockerfile`, `backend/.dockerignore`,
      `backend/src/stock_picker/api/routes/health.py`, `frontend/Dockerfile`,
      `frontend/.dockerignore`, `frontend/nginx.conf`
- [ ] 수정 파일: `docker-compose.yml`, `.env.example`, `api/main.py`(+필요 시 `routes/__init__.py`, `.gitignore`)
- [ ] AC-1 ~ AC-15 전부 충족
- [ ] `docker compose up` 단일 명령으로 전체 스택 기동 확인
- [ ] 기존 테스트 베이스라인(516 backend / 136 frontend) 회귀 없음
- [ ] 기존 Python/프론트 소스 비변경(허용 파일 외)
- [ ] `.env`가 VCS에 커밋되지 않음(비밀값 누출 없음)
