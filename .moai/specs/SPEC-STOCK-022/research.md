# SPEC-STOCK-022 리서치 — Docker 컨테이너화 커밋 및 운영 환경 검증

작성일: 2026-06-15
대상: ai-stock-picker (FastAPI + React + PostgreSQL + Redis + Claude API)

---

## 1. 핵심 발견 — 작업 전제가 현실과 다름

요청서는 "SPEC-010 Docker 구현이 커밋되지 않은 채 남아 있어 커밋이 필요하다"는 전제였으나, **실제 git 상태를 검증한 결과 Docker 산출물은 이미 전부 커밋됨**.

```
backend/Dockerfile                              TRACKED
backend/entrypoint.sh                           TRACKED
backend/src/stock_picker/api/routes/health.py   TRACKED
frontend/Dockerfile                             TRACKED
frontend/nginx.conf                             TRACKED
docker-compose.yml                              TRACKED
backend/.dockerignore                           TRACKED
.env.example                                    TRACKED
```

- 커밋: `b83b054 feat(SPEC-STOCK-010): Phase 11 — Docker 컨테이너화 구현`
- 현재 작업 트리에 위 파일들의 미스테이지/미커밋 변경 **없음** (`git status --short`에 미출현).
- 그 이후 Phase 12~21(SPEC-011~021)이 모두 커밋됨. 최신 커밋 `fdff860 docs(SPEC-STOCK-021)`.

→ 결론: **"커밋" 작업 항목은 이미 완료 상태.** SPEC-022의 실질 가치는 *현재(Phase 21까지 반영된) 코드베이스에 대한 Docker 설정 검증*과 *발견된 운영 결함 수정*에 있다.

---

## 2. 마이그레이션 현황

`backend/alembic/versions/` 최신 = **0017_alerts** (요청서 명시와 일치).

```
0001_initial_tables → ... → 0014_notifications → 0015_ai_advice
→ 0016_screener → 0017_alerts (HEAD)
```

- `entrypoint.sh`는 `alembic upgrade head` 실행 → 0017까지 자동 적용됨. 정상.
- `alembic/env.py`는 `from stock_picker.db import models` 임포트로 메타데이터 등록. Dockerfile이 `alembic/`·`alembic.ini`·`src/`를 모두 복사하므로 컨테이너 내 마이그레이션 가능. 정상.

---

## 3. 환경변수 — 코드베이스 실사용 vs .env.example

`grep`으로 추출한 백엔드 src의 실제 참조 env(코드 기준):

| env 변수 | 코드 사용처 | .env.example 존재 | 비고 |
|----------|-------------|-------------------|------|
| `ANTHROPIC_API_KEY` | config.py 필수 | O | Claude API (필수) |
| `DATABASE_URL` | config.py 필수 | O | `postgresql+asyncpg://` |
| `REDIS_URL` | deps/jobs 다수 | O | 기본 localhost |
| `SECRET_KEY` | auth | O | JWT 서명 |
| `CORS_ORIGINS` | main.py | O | 쉼표 구분 |
| `TELEGRAM_BOT_TOKEN` | main.py/telegram | O | 선택 |
| `SMTP_HOST/PORT/USER/PASSWORD/FROM` | email_service | O | 선택 |
| `LOG_LEVEL` | config | O | 기본 INFO |
| `REALTIME_POLL_INTERVAL` | realtime | **X** | 누락 — 선택값(기본값 코드 내 존재) |
| `REALTIME_PRICE_MOCK` | realtime | **X** | 누락 — 선택값(기본값 코드 내 존재) |

→ 요청서가 요구한 5개 필수 변수(ANTHROPIC_API_KEY, DATABASE_URL, REDIS_URL, SECRET_KEY, CORS_ORIGINS)는 **모두 .env.example에 존재**. 추가로 `REALTIME_POLL_INTERVAL`·`REALTIME_PRICE_MOCK` 2개가 문서화 누락(둘 다 기본값이 코드에 있어 동작에는 무해, 문서 완전성 차원의 갭).

---

## 4. ⚠️ 운영 결함 — 스케줄러가 컨테이너에서 절대 실행되지 않음

가장 중요한 발견.

- `scheduler/jobs.py`에 `setup_scheduler()`가 정의되어 5개 잡 등록:
  - `daily_collection` (06:00 KST) — 일일 수집·분석·섹터집계·추천 파이프라인
  - `intraday_collection` (09–15시, 30분) — 장중 증분
  - `check_price_alerts` (5분) — 관심목록 가격 알림
  - `weekly_email_summary` (월 07:00) — 주간 이메일 요약
  - `check_alerts` (10분) — 일반 알림(목표가·급등락, SPEC-020)
- **그러나 `setup_scheduler()`를 호출하거나 `.start()`를 실행하는 코드가 앱 기동 경로에 전무.**
  - `grep "setup_scheduler\|.start()"` → `telegram/bot.py`의 텔레그램 스레드 start만 검출.
  - `api/main.py`의 `_lifespan`은 **가격 브로드캐스트 루프(`price_broadcast_loop`)만** 백그라운드로 시작. 스케줄러는 시작하지 않음.

→ **결과: `docker compose up`으로 기동하면 모든 배치/주기 잡이 영구히 실행되지 않는다.** 뉴스 수집·분석·추천 갱신·알림 점검이 전부 멈춤. 추천 캐시는 스케줄러가 적재 주체이므로(메모 참조), 스케줄러 미실행 시 `GET /recommendations`는 영구 `preparing` 응답만 반환할 수 있음.

이것은 단순 검증을 넘어선 **실질 운영 결함**으로, 컨테이너 환경 검증 SPEC이라면 반드시 다루어야 함.

### 설계 고려사항 (RUN 단계에서 결정)
- 스케줄러를 `_lifespan`에서 시작하면 **모든 워커 레플리카가 스케줄러를 중복 실행** → 다중 인스턴스 시 잡 중복. 단, 현재 docker-compose는 backend 단일 인스턴스이므로 즉시 문제는 없음.
- 안전한 기본: 단일 backend 컨테이너 가정하에 lifespan에서 `setup_scheduler().start()` 후 종료 시 `shutdown()`. 환경변수(예: `ENABLE_SCHEDULER`, 기본 true)로 토글 가능하게 하여 향후 워커 분리에 대비.
- `check_price_alerts`·`_run_general_alert_check` 등은 `SyncSessionLocal`/`AsyncSessionLocal`을 사용하므로 DB 세션 팩토리가 컨테이너 내에서 정상 동작해야 함(DATABASE_URL 주입 필요 — 이미 충족).

---

## 5. Dockerfile / compose 검증 결과

### backend/Dockerfile (정상, 경미한 주의)
- 멀티스테이지(python:3.11-slim builder → runtime), uv, non-root `appuser`, HEALTHCHECK(`/health`). 양호.
- builder가 `COPY . .` 후 runtime이 `src`·`alembic`·`alembic.ini`·`entrypoint.sh`만 선택 복사. `pyproject.toml`은 런타임에 복사 안 됨 → `stock_picker` 패키지가 editable install이 아니라 venv site-packages에 설치되었는지 확인 필요(현재 `uv pip install -r pyproject.toml`은 deps만 설치, 패키지 자체는 `PYTHONPATH=/app/src`로 해결). 동작하나 검증 대상.
- ⚠️ `apscheduler`·`structlog`는 pyproject deps에 존재(확인됨) → 이미지에 포함됨. 정상.

### frontend/Dockerfile + nginx.conf (정상)
- node:20-alpine → nginx:alpine. `VITE_API_BASE_URL=/api` 빌드타임 주입.
- nginx: `/api/` → `http://backend:8000/`, SPA `try_files` 폴백, gzip, 정적 캐시, WebSocket 업그레이드 헤더(실시간 기능용). 양호.

### docker-compose.yml (정상, 경미한 갭)
- db(postgres:16) + redis(7) + backend + frontend. backend `env_file: .env`, `depends_on` db(healthy)/redis. frontend `depends_on` backend.
- ⚠️ frontend `depends_on: backend`에 `condition` 없음 → backend healthy 대기 안 함(빌드/기동 순서만 보장). 운영상 무해(nginx는 런타임 프록시).
- ⚠️ `.env` 파일이 repo에 커밋되어 있음(루트 `.env` 존재, 170B). `.dockerignore`/`.gitignore` 점검 필요 — 시크릿 유출 리스크.

---

## 6. SPEC-022 권장 스코프 (재정의)

1. **커밋**: 이미 완료 → SPEC에서는 "검증 및 문서화"로 전환(없는 작업을 만들지 않음).
2. **스케줄러 기동 결함 수정**: lifespan에 스케줄러 시작/종료 연동(토글 env 포함). ← SPEC-022의 핵심 가치.
3. **마이그레이션 검증**: entrypoint가 0017까지 적용함을 컨테이너 기동으로 확인.
4. **환경변수 완전성**: .env.example에 `REALTIME_POLL_INTERVAL`·`REALTIME_PRICE_MOCK` 추가(선택값임을 주석 명시).
5. **시크릿 위생**: 루트 `.env`가 git에 추적되지 않도록 `.gitignore` 점검(추적 중이면 제거 권고는 RUN에서 사용자 확인).
6. **전체 스택 기동 검증**: `docker compose up` 후 `/health`가 `{status, db, redis}` 정상 응답, 프론트가 nginx 경유 백엔드 프록시 동작.

## 7. 범위 밖 (영구/이번)
- 자동 매매(영구 제외)
- 원격 push, CI/CD(SPEC-011 영역), Kubernetes, TLS
- 신규 마이그레이션 생성(0017 유지)
- `POST /portfolios/{id}/ai-analysis` 수정
