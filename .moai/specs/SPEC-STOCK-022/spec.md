---
id: SPEC-STOCK-022
version: 0.1.0
status: draft
created: 2026-06-15
updated: 2026-06-15
author: ircp
priority: high
issue_number: null
---

# SPEC-STOCK-022 — Docker 컨테이너화 커밋 및 운영 환경 검증 (Phase 22)

## HISTORY

- 2026-06-15: 초안 작성. 리서치 결과 SPEC-010 Docker 산출물이 **이미 커밋됨**(commit `b83b054`)을 확인하여 스코프를 "커밋"에서 "현재 코드베이스(Phase 21까지) 대상 검증 + 발견된 운영 결함 수정"으로 재정의. 핵심 결함: APScheduler가 앱 lifespan에 연동되지 않아 컨테이너에서 모든 배치/주기 잡이 실행되지 않음.

---

## 개요 (Overview)

SPEC-010(Phase 11)에서 작성된 Docker 컨테이너화 산출물을 **현재 코드베이스 상태(Phase 12~21 반영)**에 대해 검증하고, 검증 과정에서 발견된 운영 결함을 수정한다.

리서치(research.md)에서 확인된 사실:

1. Docker 산출물(`backend/Dockerfile`, `frontend/Dockerfile`, `nginx.conf`, `docker-compose.yml`, `entrypoint.sh`, `health.py`, `.dockerignore`, `.env.example`)은 **이미 git에 커밋됨**. 별도 커밋 작업 불필요.
2. 마이그레이션 최신 = `0017_alerts`. `entrypoint.sh`의 `alembic upgrade head`가 0017까지 적용함.
3. 요청된 5개 필수 환경변수(`ANTHROPIC_API_KEY`, `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `CORS_ORIGINS`)는 `.env.example`에 모두 존재.
4. **⚠️ 운영 결함**: `scheduler/jobs.py`의 `setup_scheduler()`가 앱 기동 경로에서 호출되지 않음. `api/main.py`의 `_lifespan`은 가격 브로드캐스트 루프만 시작하고 스케줄러는 시작하지 않음 → 컨테이너 기동 시 일일/장중 파이프라인·알림 점검·주간 요약·일반 알림 잡이 **전부 실행되지 않음**.

이 SPEC은 운영 인프라 SPEC이며 신규 기능을 추가하지 않는다.

---

## 환경 및 가정 (Environment & Assumptions)

- 백엔드: FastAPI + uvicorn, Python 3.11, 패키지 매니저 `uv`, 진입점 `stock_picker.api.main:app`
- 프론트엔드: React + Vite, nginx:alpine 서빙
- 데이터: PostgreSQL 16(`postgresql+asyncpg://`) + Redis 7
- 배포 범위: **로컬 Docker(`docker compose up`)만**. 클라우드/K8s/CI-CD 제외
- 단일 backend 컨테이너 인스턴스를 가정(스케줄러 중복 실행 방지 전제)
- 작업 트리는 깨끗하며, Docker 산출물은 이미 커밋되어 있음

---

## 요구사항 (Requirements — EARS)

### 커밋 및 상태 검증 (REQ-022-COMMIT-*)

- **REQ-022-COMMIT-001**: 시스템은 SPEC-010 Docker 산출물 8개 파일이 git에 추적·커밋된 상태임을 검증 결과로 기록 SHALL 한다. (이미 충족 — 재커밋 금지)
- **REQ-022-COMMIT-002**: IF Docker 관련 파일에 미커밋 변경이 존재하면, THEN 시스템은 해당 변경만 SPEC-022 단위로 커밋 SHALL 한다. (현재 미발생)

### 스케줄러 기동 결함 수정 (REQ-022-SCHED-*)

- **REQ-022-SCHED-001**: WHEN FastAPI 앱이 기동되면, 시스템은 `setup_scheduler()`로 생성한 스케줄러를 시작(`.start()`) SHALL 한다.
- **REQ-022-SCHED-002**: WHEN FastAPI 앱이 종료되면, 시스템은 스케줄러를 안전하게 종료(`shutdown()`) SHALL 한다.
- **REQ-022-SCHED-003**: 시스템은 환경변수 `ENABLE_SCHEDULER`(기본 `true`)로 스케줄러 기동 여부를 제어 SHALL 한다. WHERE 값이 `false`이면 스케줄러를 시작하지 않는다. (다중 워커/테스트 환경 대비)
- **REQ-022-SCHED-004**: 스케줄러 시작은 기존 가격 브로드캐스트 루프 시작과 **공존** SHALL 하며, 어느 한쪽 실패가 다른 쪽 기동을 막지 않도록 예외를 격리 SHALL 한다.
- **REQ-022-SCHED-005**: IF 스케줄러 시작에 실패하면, THEN 시스템은 오류를 로그로 남기고 앱 기동은 계속 SHALL 한다. (graceful degradation)

### 마이그레이션 검증 (REQ-022-MIG-*)

- **REQ-022-MIG-001**: WHEN backend 컨테이너가 기동되면, `entrypoint.sh`는 `alembic upgrade head`로 마이그레이션을 `0017_alerts`까지 적용 SHALL 한다.
- **REQ-022-MIG-002**: 시스템은 이 SPEC에서 신규 마이그레이션을 생성하지 않 SHALL 는다. (최신 = 0017 유지)

### 환경변수 검증 (REQ-022-ENV-*)

- **REQ-022-ENV-001**: 시스템은 `.env.example`에 5개 필수 변수(`ANTHROPIC_API_KEY`, `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `CORS_ORIGINS`)를 포함 SHALL 한다. (이미 충족)
- **REQ-022-ENV-002**: 시스템은 `.env.example`에 `REALTIME_POLL_INTERVAL`·`REALTIME_PRICE_MOCK`·`ENABLE_SCHEDULER`를 선택 변수로 추가하고, 각 기본값을 주석으로 명시 SHALL 한다.
- **REQ-022-ENV-003**: IF 루트 `.env` 파일이 git에 추적 중이면, THEN 시스템은 이를 `.gitignore`에 포함하여 향후 추적되지 않도록 SHALL 한다. (시크릿 위생 — 기존 추적 파일 제거는 사용자 확인 후 수행)

### 운영 검증 (REQ-022-VERIFY-*)

- **REQ-022-VERIFY-001**: WHEN `docker compose up`이 실행되면, 시스템은 db·redis·backend·frontend 4개 서비스를 기동 SHALL 한다.
- **REQ-022-VERIFY-002**: WHEN `GET /health` 요청 시, 시스템은 `{"status","db","redis"}` 형식 응답을 반환 SHALL 하며, DB 정상 시 `status=ok` SHALL 한다.
- **REQ-022-VERIFY-003**: WHEN 프론트엔드(`:3000`)에서 `/api/*` 요청 시, nginx는 이를 `backend:8000`으로 프록시 SHALL 한다.

### 비기능 요구사항 (REQ-022-NFR-*)

- **REQ-022-NFR-001**: 백엔드 테스트 스위트는 변경 후에도 통과(`pytest`, `--cov-fail-under=85`) SHALL 한다.
- **REQ-022-NFR-002**: 스케줄러 lifespan 연동 변경은 `ruff check` 통과 SHALL 한다.
- **REQ-022-NFR-003**: 변경은 기존 라우터·엔드포인트 동작을 회귀시키지 않 SHALL 는다.

---

## 인수 기준 (Acceptance Criteria)

- **AC-1**: `git ls-files`로 8개 Docker 산출물이 모두 추적됨을 확인할 수 있다. (이미 충족)
- **AC-2**: `docker compose up` 후 4개 서비스(db, redis, backend, frontend)가 모두 기동한다.
- **AC-3**: backend 컨테이너 로그에 `alembic upgrade head` 실행 후 0017까지 적용된 흔적이 있고, uvicorn이 정상 기동한다.
- **AC-4**: `curl http://localhost:8000/health`가 `{"status":"ok","db":"ok","redis":...}`를 반환한다.
- **AC-5**: 앱 기동 로그에 스케줄러 시작 메시지가 출력되고, `setup_scheduler()`가 등록한 5개 잡(daily/intraday/check_price_alerts/weekly_email/check_alerts)이 스케줄러에 등록된다.
- **AC-6**: `ENABLE_SCHEDULER=false`로 기동 시 스케줄러가 시작되지 않고, 앱은 정상 기동한다.
- **AC-7**: 앱 종료(SIGTERM) 시 스케줄러가 `shutdown()`되어 종료 예외가 로그를 오염시키지 않는다.
- **AC-8**: 가격 브로드캐스트 루프와 스케줄러가 동시에 정상 시작한다(둘 다 로그 확인).
- **AC-9**: `frontend:3000`에서 페이지 로드 후 `/api/health` 호출이 백엔드로 프록시되어 200을 반환한다.
- **AC-10**: `.env.example`에 `REALTIME_POLL_INTERVAL`, `REALTIME_PRICE_MOCK`, `ENABLE_SCHEDULER`가 기본값 주석과 함께 존재한다.
- **AC-11**: 루트 `.env`가 `.gitignore`에 포함되어 신규 추적되지 않는다.
- **AC-12**: `pytest`가 통과하고 커버리지가 85% 이상이다.
- **AC-13**: `ruff check`가 변경 파일에서 오류 없이 통과한다.

---

## 작업 목록 (Task List)

### M1 — 상태 검증 및 문서화
- [ ] T1-1: `git ls-files`로 8개 Docker 산출물 추적 상태 확인 (AC-1)
- [ ] T1-2: Docker 관련 파일에 미커밋 변경이 없음을 `git status`로 확인 (REQ-022-COMMIT-002)

### M2 — 스케줄러 lifespan 연동 (핵심)
- [ ] T2-1: `backend/src/stock_picker/api/main.py` `_lifespan`에 `setup_scheduler()` 시작/종료 로직 추가 (REQ-022-SCHED-001, 002, 004, 005)
- [ ] T2-2: `ENABLE_SCHEDULER` 환경변수 토글 구현(기본 true) (REQ-022-SCHED-003)
- [ ] T2-3: 스케줄러 시작/실패/종료 로그 추가 + 예외 격리
- [ ] T2-4: `backend/tests/`에 스케줄러 lifespan 동작 테스트 추가(시작/토글 off) (AC-5, AC-6)

### M3 — 환경변수 완전성 및 시크릿 위생
- [ ] T3-1: `.env.example`에 `REALTIME_POLL_INTERVAL`·`REALTIME_PRICE_MOCK`·`ENABLE_SCHEDULER` 추가(기본값 주석) (REQ-022-ENV-002)
- [ ] T3-2: 루트 `.env`가 `.gitignore`에 포함되는지 점검·추가 (REQ-022-ENV-003, AC-11)

### M4 — 운영 검증
- [ ] T4-1: `docker compose up` 전체 스택 기동 검증 (AC-2, AC-3)
- [ ] T4-2: `GET /health` 응답 검증 (AC-4)
- [ ] T4-3: frontend → `/api` 프록시 검증 (AC-9)
- [ ] T4-4: 스케줄러 잡 등록·시작 로그 검증 (AC-5, AC-8)

### M5 — 품질 게이트
- [ ] T5-1: `pytest --cov-fail-under=85` 통과 확인 (AC-12)
- [ ] T5-2: `ruff check` 통과 확인 (AC-13)

---

## Exclusions (What NOT to Build)

- **자동 매매/주문 실행** — 규제·책임 리스크로 영구 제외
- **원격 저장소 push** — 이 SPEC은 로컬 커밋·검증까지만
- **CI/CD 파이프라인** — SPEC-011(Phase 12) 영역, 본 SPEC 스코프 아님
- **Kubernetes / Helm / 클라우드 배포** — 로컬 Docker 한정
- **TLS / 시크릿 매니저 / 모니터링 스택** — 운영 고도화는 별도 SPEC
- **신규 데이터베이스 마이그레이션 생성** — 최신 0017 유지
- **`POST /portfolios/{id}/ai-analysis` 엔드포인트 수정** — 불변
- **신규 스케줄러 잡 추가** — 기존 5개 잡을 *기동*만 시킬 뿐, 새 잡 정의 금지
- **다중 워커 분산 스케줄러(리더 선출 등)** — 단일 인스턴스 가정, 토글 env로만 대비
