# Changelog

모든 주목할만한 변경 사항이 이 파일에 기록됩니다.

형식은 [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)를 따르며,
버전 관리는 [Semantic Versioning](https://semver.org/lang/ko/)을 따릅니다.

---

## [0.17.0] - 2026-06-12

### Added
- 포트폴리오 성과 분석 대시보드 (Phase 17, SPEC-STOCK-017)
- 섹터별 수익률 집계 (SectorPerformance)
- 수익률 분류: 고수익(≥+5%), 일반, 저수익(≤-5%)
- recharts 도넛 차트 (고수익/일반/저수익 비율 시각화)

### Changed
- `get_sector()` 유틸리티 함수 공통 모듈로 통합 (portfolio/utils.py)
- 포트폴리오 성과 API: 프론트엔드 타입 드리프트 수정 (current_value, total_return)
- 가격 조회 Redis 캐시 통합 (realtime/price_feed.get_current_price)

---

## [0.16.0] - 2026-06-12

### Added (Phase 16: 실시간 주가 스트리밍 — SPEC-STOCK-016)

#### 백엔드: 멀티플렉스 WebSocket 실시간 주가 스트리밍

- **ConnectionManager** (`connection_manager.py`)
  - 인메모리 구독 레지스트리: connection → symbols, symbol → connections 맵핑
  - `subscribe(connection_id, symbol)`: 종목 구독 추가
  - `unsubscribe(connection_id, symbol)`: 종목 구독 해지
  - `broadcast_price(symbol, price_data)`: 심볼별 팬아웃 브로드캐스트
  - `cleanup(connection_id)`: 연결 종료 시 정리

- **Price Broadcast Loop** (`price_broadcast.py`)
  - 10초 주기 폴링 및 가격 업데이트 전파
  - `REALTIME_PRICE_MOCK` 환경변수로 개발 모킹 모드 지원 (true: 시뮬레이션, false: 실제 데이터)
  - `WatchlistAlert` 임계값 체크 → `notifications` 테이블에 `price_alert` 자동 생성
  - Graceful degradation: WS 실패 시 마지막 알려진 값 유지

- **멀티플렉스 WebSocket 엔드포인트** (`ws_router.py`)
  - `ws /ws/prices` — 단일 WebSocket 연결로 다수 종목 구독/해지
  - 메시지 포맷:
    - `{"action": "subscribe", "symbol": "KRX_CODE"}` — 종목 구독 추가
    - `{"action": "unsubscribe", "symbol": "KRX_CODE"}` — 종목 구독 해지
  - 응답: `{"symbol": "KRX_CODE", "price": float, "change_percent": float, "timestamp": ISO8601}`
  - 기존 단일 종목 엔드포인트 `/ws/prices/{krx_code}` 무중단 유지
  - Lifespan context manager: 앱 시작 시 `price_broadcast_loop` 태스크 자동 생성, 종료 시 정리

#### 백엔드 테스트

- **ConnectionManager 단위 테스트** (`test_connection_manager.py`, 14개)
  - subscribe/unsubscribe, broadcast, cleanup 기본 동작
  - 중복 구독, 중복 구독 해지, 비존재 연결 에러 핸들링
  - 심볼별 팬아웃 정확성 검증

- **Price Broadcast 단위 테스트** (`test_price_broadcast.py`, 13개)
  - 10초 주기 동작, REALTIME_PRICE_MOCK 모드
  - WatchlistAlert 임계값 체크 및 notification 생성
  - 에러 복구, 시뮬레이션 데이터 생성

- **멀티플렉스 WebSocket 통합 테스트** (`test_ws_prices_multiplex.py`, 7개)
  - subscribe/unsubscribe 메시지 처리
  - 가격 브로드캐스트 수신 검증
  - 연결 종료 시 정리 확인

- **전체**: 백엔드 테스트 650개 통과

#### 프론트엔드: 실시간 주가 및 Watchlist 마이그레이션

- **useLivePrices 훅** (`useLivePrices.ts`)
  - 단일 WebSocket 연결로 다수 종목 실시간 가격 관리
  - `useLivePrices(symbols: string[])` → `{ prices: Record<string, PriceData>, isConnected: boolean, error: string | null }`
  - 자동 재연결, 구독 추가/제거 처리

- **Watchlist 마이그레이션** (`Watchlist.tsx`)
  - N개 WebSocket 연결 → `useLivePrices` 단일 멀티플렉스 연결로 변경
  - 가격 업데이트 성능 개선 (연결 수 감소, 브로드캐스트 효율 증대)

- **Dashboard 실시간 주가** (`App.tsx`)
  - AI 조언의 추천 종목 목록에 실시간 시세 표시
  - `useLivePrices` 훅으로 다중 종목 가격 업데이트

- **프론트엔드 테스트** (`useLivePrices.test.ts`, 9개)
  - subscribe/unsubscribe 동작 검증
  - 재연결 로직, 에러 핸들링

- **전체**: 프론트엔드 테스트 179개 통과

#### 데이터베이스

- DB 마이그레이션 없음 (ConnectionManager는 인메모리)

---

## [0.15.0] - 2026-06-11

### Added (Phase 15: AI 투자 조언 고도화 — SPEC-STOCK-014)

#### 백엔드: AI 투자 조언 시스템

- **Alembic 마이그레이션 0015**
  - `ai_advice` 테이블 신규 생성
  - 컬럼: id, user_id(FK→users, CASCADE), advice_type(enum: rebalance/risk_profile/market_briefing), content(JSON), ref_date(DATE), risk_score(nullable, 0~100), feedback(nullable: helpful/not_helpful), created_at
  - 멱등성 보장 UNIQUE 제약: `(user_id, advice_type, ref_date)` — 일일 1회 갱신

- **AI 조언 라우터** (`advice_router.py`, prefix `/advice`, JWT 인증 필수)
  - `POST /advice/rebalance` — 포트폴리오 리밸런싱 제안 (보유 주식 vs 추천 비교, Claude Haiku 기반)
  - `POST /advice/risk-profile` — 리스크 프로파일 분석 (섹터 집중도, risk_score 0~100 산출)
  - `GET /advice/market-briefing` — 일일 시장 브리핑 (Redis 캐시 1회/일/사용자, 키: `ai_advice:briefing:{user_id}:{date}`)
  - `GET /advice/history` — 조언 이력 조회 (페이지네이션, 정렬)
  - `POST /advice/{advice_id}/feedback` — 조언 피드백 (helpful/not_helpful 품질 데이터 수집)

- **AI 조언 서비스** (`advice/service.py`)
  - `generate_rebalance_advice()`: 보유 종목 포트폴리오 vs 추천 종목 비교 후 리밸런싱 제안
  - `generate_risk_profile()`: 섹터별 보유량 분석 → risk_score 계산 (집중도 높음 = 고위험)
  - `generate_market_briefing()`: Claude Haiku로 시장 요약 (1일 1회 캐시)
  - `save_advice_safe()`: UNIQUE 제약 위배 시 UPDATE (멱등성)
  - 모든 응답에 "투자 면책 문구" 포함, 자동 매매·실시간 데이터 스코프 외

#### 프론트엔드: AI 조언 UI

- **포트폴리오 페이지 AI 조언 패널**
  - 3개 탭: 리밸런싱, 리스크 분석, 시장 브리핑
  - 각 탭별 로딩 상태, 에러 표시, 재요청 버튼

- **조언 이력 페이지** (`/advice/history` 라우트)
  - 조언 목록 (최신순, 페이지네이션)
  - 각 조언별 조언 타입, 날짜, helpful/not_helpful 피드백 버튼
  - 피드백 저장 후 UI 즉시 갱신

- **API 함수** (`api/advice.ts`)
  - `rebalanceAdvice()`, `riskProfileAdvice()`, `marketBriefing()`, `getAdviceHistory()`, `submitAdviceFeedback()`

#### 테스트 및 품질 보증

- **백엔드 테스트**: 47개 통과
  - `test_ai_advice_model.py` (19개): AIAdvice ORM 모델, 제약, 직렬화
  - `test_advice_service.py` (18개): 리밸런싱, 리스크 분석, 시장 브리핑 서비스 단위
  - `test_advice_router.py` (10개): 5개 엔드포인트 통합 테스트
  - 백엔드 커버리지: 87.30%

- **프론트엔드 테스트**: 170개 통과
  - 기존 모든 컴포넌트 테스트 유지
  - 새 조언 컴포넌트 테스트 추가 예정

---

## [0.14.0] - 2026-06-11

### Added (Phase 14: 알림·인박스 시스템 — SPEC-STOCK-013)

#### 백엔드: 알림 인박스 시스템
- **Alembic 마이그레이션 0014**
  - `notifications` 테이블 신규 생성
  - 컬럼: id, user_id(FK→users, CASCADE), type, krx_code, title, body, is_read(기본 false), ref_date(nullable), related_alert_id(FK→watchlist_alerts, nullable), created_at, read_at
  - 중복 방지 UNIQUE 제약: `(user_id, type, krx_code, ref_date)` — 장중 30분 재실행 멱등성 보장

- **인박스 라우터** (`inbox_router.py`, prefix `/notifications/inbox`, JWT 인증 필수)
  - `GET /notifications/inbox` — 알림 목록 조회 (`unread_only`, `limit` 파라미터)
  - `GET /notifications/inbox/unread-count` — 미읽음 개수
  - `PATCH /notifications/inbox/{id}/read` — 단건 읽음 처리
  - `PATCH /notifications/inbox/read-all` — 전체 읽음 처리

- **추천 변경 감지** (`rec_change.py`)
  - `check_rec_changes()`: 현재 `trade_date` 추천 유니버스 vs 직전 `trade_date` 비교
  - 관심 종목이 추천에 신규 진입 → `rec_new` 알림 생성
  - 관심 종목이 추천에서 이탈 → `rec_dropped` 알림 생성
  - UNIQUE 제약으로 중복 알림 방지 (멱등성)

- **스케줄러 연동** (`scheduler/jobs.py`)
  - `_trigger_alert`: 텔레그램/이메일 발송 외 인박스 레코드 추가 생성
  - `run_daily_pipeline` / `run_intraday_pipeline`: 추천 파이프라인 직후 `check_rec_changes()` 호출 (신규 타이머 없음, graceful degradation)

#### 프론트엔드: 알림 인박스 UI
- **NavBar 알림 종 아이콘**: 미읽음 배지 표시, 비로그인 시 숨김
- **알림 인박스 페이지** (`/notifications` 라우트)
  - 최신 순 목록, 읽음/미읽음 시각 구분
  - 단건·전체 읽음 처리, 배지 즉시 갱신
- **인박스 API 함수** (`notifications.ts`)
  - `fetchNotifications`, `fetchUnreadCount`, `markNotificationRead`, `markAllNotificationsRead`

#### 테스트 및 품질 보증
- **백엔드 테스트**: 18/18 통과
  - `test_rec_change.py` (8개): `check_rec_changes()`, `_insert_notification_safe()` 단위 테스트
  - `test_inbox_router.py` (10개): 인박스 HTTP 엔드포인트 통합 테스트
- **프론트엔드 테스트**: 170/170 통과
  - `notifications_inbox.test.ts` (11개): 인박스 API 함수 단위 테스트
  - `Settings.test.tsx` (`importOriginal` 패턴 적용)

### Fixed

- **스테일 컴파일 아티팩트 제거**: `frontend/src/api/*.js` 9개 삭제 — vitest가 `.ts` 대신 `.js`를 로드하던 문제 해결

---

## [0.13.0] - 2026-06-11

### Added (Phase 13: 백테스트 엔진 완성 — SPEC-STOCK-012)

#### 백엔드: 백테스트 시스템 완성
- **Alembic 마이그레이션 0013**
  - `backtest_runs` 테이블에 `universe_size`, `top_n` 컬럼(nullable, 정수) 추가
  - 실행 시점의 파라미터 영속화

- **POST /backtest/run 스키마 정합**
  - 요청: `{strategy, start_date, end_date, universe_size?, top_n?}` (선택 파라미터)
  - 응답: HTTP 202 + `{run_id, message}` (백엔드-프론트 계약 통일)
  - start_date >= end_date 검증 (HTTP 422)
  - universe_size/top_n 1 이상 검증

- **상태 값 통일**
  - `error` → `failed` 상태값 일원화
  - pending/running/done/failed 4가지 상태로 통일

- **성과 지표 확장**
  - `calculate_total_return()`: 포트폴리오 누적 수익률 (최종/초기-1)
  - `calculate_win_rate()`: 수익 양수 거래일 / 전체 거래일 (0~1 범위)
  - `build_portfolio_value_series()`: 날짜별 포트폴리오 가치 시계열
  - 거래일 데이터 부재 시 안전한 기본값(0.0) 반환 (0 나누기 방지)

- **벤치마크 수집·정규화**
  - `_fetch_benchmark_data()`: FinanceDataReader로 KS11(KOSPI), KQ11(KOSDAQ) 지수 수집
  - 벤치마크 실패 시 run 중단 없이 `benchmark_value=null` 처리 (graceful degradation)
  - `_normalize_series()`: 동일 기준(시작값) 기반 정규화

- **일별 결과 응답 스키마 변경**
  - 기존: `PaginatedDailyResults`(거래 단위: trade_date, krx_code, signal, price, return_pct)
  - 신규: flat array `[{date, portfolio_value, benchmark_value, daily_return}]` (날짜 단위)

- **GET /backtest/runs/{id} 응답 확장**
  - cagr, max_drawdown, sharpe_ratio, total_return, win_rate, total_trades 포함

- **러너 파라미터 통합**
  - 하드코딩된 `_TOP_N` 제거 → `top_n`, `universe_size` 파라미터 사용
  - FinanceDataReader 동기 호출을 `run_in_executor`로 래핑 (asyncio 논블로킹)

#### 프론트엔드: 프론트-백 계약 정합
- **backtest.ts 타입 정합**
  - `BacktestStartResponse`: `{run_id: string, message: string}` (HTTP 202)
  - `BacktestRun`: `{id: string, win_rate, total_trades, completed_at, ...}` 추가 필드
  - `BacktestDailyResult`: `{benchmark_value: null|number}` 허용 (null-safe)

- **Backtest.tsx 강화**
  - universe_size, top_n 선택 입력 필드 추가
  - POST 응답 run_id로 자동 상세 페이지 확장
  - win_rate, total_return 퍼센트 표시
  - benchmark null 처리 (차트 렌더링 안 함)
  - pending/running 상태 배지 + 진행 중 메시지 표시

#### 테스트 및 품질 보증
- **백엔드 테스트**: 신규 테스트 추가
  - test_backtest_metrics.py: total_return, win_rate, portfolio_series 신규 케이스 29개
  - test_backtest_runner.py: 신규 파일 (상태전환, 벤치마크실패, universe 파라미터) 다수
  - test_backtest_router.py: POST 202 구조, universe_size/top_n 검증, flat array 결과
  - **전체 테스트**: 551/556 통과 (5개 사전 존재 collector HTTP 테스트 실패, 이번 구현 무관)

- **프론트엔드 테스트**: 신규 테스트
  - src/__tests__/backtest.test.ts: 23개 테스트 작성·통과

- **테스트 커버리지**: 85%+ 유지

### Changed

- 백테스트 응답: POST `/backtest/run` 이제 HTTP 202 + `{run_id, message}` 반환
- 상태 enum: `error` → `failed` 통일
- 결과 형식: 거래 단위 → 날짜 단위 시계열로 변경
- 벤치마크: KOSPI/KOSDAQ 자동 수집 및 정규화

### Fixed

- 프론트-백 계약 불일치: 응답 형식·status enum·결과 시계열 일원화
- 벤치마크 데이터 미수집 시에도 백테스트 계속 진행 (graceful degradation)
- 거래일 데이터 부재 시 0 나누기 오류 방지

### Non-Goals (제외 항목)

- 거래 비용·슬리피지·세금 모델링
- 신규 전략 추가 (momentum/volume 외)
- 결과 캐싱/Redis
- 포트폴리오 리밸런싱 정교화
- CSV/PDF 내보내기·결과 공유
- 다중 벤치마크 사용자 선택

---

## [0.12.0] - 2026-06-11

### Added (Phase 12: GitHub Actions CI/CD 파이프라인 — SPEC-STOCK-011)

#### CI 파이프라인 (`.github/workflows/ci.yml`)
- **트리거**: `push` + `pull_request` → branches: master
- **병렬 잡 3개**:
  1. **백엔드 CI**: ruff lint + compileall + pytest (85% 커버리지 필수)
  2. **프론트엔드 CI**: eslint (새 flat config) + vitest + Vite 빌드
  3. **Docker 빌드 검증**: backend + frontend Dockerfile 빌드 (GHA cache 활용)
- **캐싱**: uv 패키지 (pyproject.toml 해시) + npm 의존성 + Docker 레이어

#### CD 파이프라인 (`.github/workflows/cd.yml`)
- **트리거**: CI 워크플로 성공 + master 브랜치 (workflow_run 이벤트)
- **자동 배포**: ghcr.io로 이미지 푸시
  - `ghcr.io/{owner}/ai-stock-picker-backend:latest` + `:sha:{SHA}`
  - `ghcr.io/{owner}/ai-stock-picker-frontend:latest` + `:sha:{SHA}`
- **인증**: GitHub 기본 GITHUB_TOKEN 사용 (별도 시크릿 불필요)

#### 프론트엔드: ESLint 선행 구성
- **frontend/eslint.config.js**: ESLint 9 flat config 신규
  - `@eslint/js` recommended
  - `typescript-eslint` v8+
  - `eslint-plugin-react-hooks` v5+
- **frontend/package.json**: `lint` 스크립트 추가 (`eslint src`)

#### API 개선
- `api/main.py`: 기존 `/health` 인라인 엔드포인트 → 신규 health 라우터로 통합
- CORS `allow_origins` 환경변수(`CORS_ORIGINS`) 반영

#### 테스트 및 품질 보증
- **백엔드 테스트**: 526개 (+10 health 라우터 테스트)
- **프론트엔드 테스트**: 136개 (변경 없음)
- **테스트 통과율**: 100%
- **회귀 안전성**: 기존 기능 모두 검증

### Changed

- 프론트엔드: ESLint 9 도입으로 현대적 linting 확보
- CI 워크플로: 모든 프로젝트 언어 병렬 검증으로 피드백 속도 개선
- CD 배포: GitHub Actions 자동화로 수동 배포 제거

### Fixed

- CI 실패 시 master 브랜치에 자동 배포되는 버그 방지 (workflow_run 조건)
- Docker 캐시 미스로 인한 느린 빌드 개선 (GHA cache 적용)

---

## [0.11.0] - 2026-06-11

### Added (Phase 11: Docker 컨테이너화 + 운영 환경 설정 — SPEC-STOCK-010)

#### 백엔드: Docker 컨테이너화
- **backend/Dockerfile** (신규)
  - 멀티스테이지 빌드 (builder + runtime)
  - `uv`로 의존성 설치
  - non-root 사용자(`appuser`)로 실행
  - `HEALTHCHECK` 지시어로 `/health` 점검
  - 엔트리포인트: `alembic upgrade head` → `uvicorn`

- **backend/entrypoint.sh** (신규)
  - DB 마이그레이션 자동 실행
  - uvicorn 서버 기동

- **backend/.dockerignore** (신규)
  - `.venv`, `__pycache__`, `.pytest_cache`, `tests/`, `.env` 등 제외

- **헬스 체크 라우터** (`backend/src/stock_picker/api/routes/health.py`)
  - `GET /health` → `{"status": "ok"|"error", "db": "ok"|"error", "redis": "ok"|"unavailable"}`
  - DB/Redis 점검 포함, 무인증 접근 가능
  - Redis 장애 시 graceful degradation

#### 프론트엔드: Docker 컨테이너화
- **frontend/Dockerfile** (신규)
  - 빌더 스테이지: `node:20-alpine`에서 Vite 운영 빌드
  - 런타임 스테이지: `nginx:alpine`에 정적 산출물 배포

- **frontend/nginx.conf** (신규)
  - SPA 폴백: `try_files $uri $uri/ /index.html`
  - API 리버스 프록시: `/api/` → `http://backend:8000/`
  - gzip 압축 활성화
  - 정적 자산 캐시 헤더 설정

- **frontend/.dockerignore** (신규)
  - `node_modules`, `dist`, `.env`, `.git` 등 제외

#### docker-compose.yml 확장
- **신규 서비스**: `backend`, `frontend` 추가
  - `backend`: 포트 8000, `db` healthcheck 대기, `.env` 환경변수 주입
  - `frontend`: 포트 3000, `backend` 기동 후 시작

- **기존 서비스**: `db` (PostgreSQL), `redis` 유지/정리
  - `db`: healthcheck 추가 (`pg_isready`)
  - `redis`: healthcheck 추가 (`redis-cli ping`)

- **볼륨**: `postgres_data`, `redis_data` named volume으로 영속화

- **포트 매핑**: 5432 (db), 6379 (redis), 8000 (backend), 3000 (frontend)

#### 환경변수 확장 (`.env.example`)
- **기존 키** (유지): `ANTHROPIC_API_KEY`, `DATABASE_URL`, `REDIS_URL`, `LOG_LEVEL`
- **신규 키** (추가):
  - `SECRET_KEY`: JWT 토큰 서명 (Phase 2 auth)
  - `CORS_ORIGINS`: 프론트엔드 오리진 (기본: `http://localhost:3000`)
  - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`: 텔레그램 알림 (선택)
  - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`: 이메일 알림 (선택)
- **기본값 설정**: compose 내부 서비스명(`db`, `redis`) 호스트명으로 `DATABASE_URL`, `REDIS_URL` 기본값 설정

#### API 변경
- **api/main.py** 수정
  - 기존 인라인 `/health`를 신규 health 라우터로 치환·등록
  - CORS `allow_origins` 환경변수(`CORS_ORIGINS`) 반영

#### 운영 인프라
- `.gitignore` 보강: `.env` 파일 비커밋 보장
- 비밀값 플레이스홀더화: `.env.example`은 안전한 예시만 제공

#### 테스트 및 품질 보증
- **백엔드 테스트**: 526개 (이전 516개에서 +10 health 라우터 테스트)
- **프론트엔드 테스트**: 136개 (변경 없음)
- **테스트 통과율**: 100%
- **회귀 안전성**: 기존 기능(추천/인증/실시간/알림) 동작 변경 없음

### Changed

- 백엔드: `/health` 엔드포인트 확장 (DB/Redis 점검 포함)
- 프론트엔드: nginx 리버스 프록시로 API 경유 처리
- docker-compose: 전체 스택 통합 기동 (단일 명령)

### Fixed

- 운영 환경에서 필요한 모든 환경변수 명확화 (`.env.example`)
- 컨테이너 초기화 순서 보장 (healthcheck 기반 `depends_on`)
- Redis 장애가 백엔드 기동을 막지 않음 (graceful degradation 유지)

### Non-Goals (제외 항목)

- Kubernetes/ECS/Swarm 매니페스트
- CI/CD 파이프라인·이미지 레지스트리
- TLS/HTTPS·도메인·로드밸런서
- 시크릿 매니저 연동

---

## [0.10.0] - 2026-06-10

### Added (Phase 10: 피드백 기반 가중치 + 스코어 투명성 — SPEC-STOCK-009)

#### 백엔드: 피드백 기반 점수 조정
- **Alembic 마이그레이션 0012**
  - `recommendations` 테이블에 `base_score` (Numeric 6,3, nullable)와 `feedback_score` (Numeric 6,3, nullable) 컬럼 추가

- **피드백 가중치 계산** (`feedback/weighting.py` 신규)
  - `calculate_feedback_coefficient()`: 신뢰도 가중 계산 (feedback_count 기반, MAX_ADJ=0.15)
  - `apply_feedback_adjustment()`: 조정 적용 함수 (0~1 클램프)

- **피드백 일괄 집계** (`feedback/service.py` 개선)
  - `get_bulk_feedback()`: GROUP BY 쿼리로 N+1 회피

- **스코어 분해** (`scoring/engine.py` 개선)
  - `decompose_score()`: 4요인(감성, 거래량, 모멘텀, 이상거래량) 기여도 분석

#### 백엔드: 파이프라인 통합
- **추천 엔진 변경** (`recommendation/service.py`)
  - base_score 계산 후 피드백 조정 일괄 적용
  - 기존 4요인 산식 유지 (하위 호환성)
  - base_score / feedback_score 분리 저장

#### 백엔드: API 확장
- **응답 스키마** (`api/schemas.py`)
  - `ScoreFactorContribution`: {factor, weight, factor_score, contribution}
  - `ScoreBreakdown`: {factors[], feedback_delta}
  - `RecommendationItem` / `RecommendationDetail`에 선택 필드 추가

- **상세 응답** (`api/routes/recommendations.py`)
  - `GET /recommendations` list: base_score, feedback_score 포함
  - `GET /recommendations/{krx_code}` detail: score_breakdown 포함

#### 프론트엔드: 스코어 시각화
- **ScoreBreakdown.tsx** (신규)
  - 요인별 기여도 막대 그래프
  - 피드백 조정값(delta) 표시

- **RecommendationList.tsx** 개선
  - 피드백 조정 시 배지 표시 (feedback_score != 0)

- **StockDetail.tsx** 개선
  - ScoreBreakdown 섹션 통합

#### 테스트 및 품질 보증
- **백엔드 테스트**: 35건 (신규)
  - weighting.py: 계수 계산, 조정 적용 (15개)
  - scoring.py: 스코어 분해 (10개)
  - integration: 파이프라인 + API 하위호환 (10개)
  - **총 테스트**: 516건 (이전 481건)

- **프론트엔드 테스트**: 10건 (신규)
  - ScoreBreakdown: 렌더링, 요인 표시 (5개)
  - RecommendationList: 피드백 배지 (3개)
  - StockDetail: 분해 표시 (2개)
  - **총 테스트**: 136건 (이전 126건)

- **테스트 커버리지: 92.3%**

### Changed

- 추천 응답: base_score 와 feedback_score 분리 저장
- 점수 투명성: 요인별 기여도 상세 제시
- 피드백 영향도: 신뢰도 기반 가중 (과도한 조정 방지)

### Fixed

- 피드백 과다 영향: MAX_ADJ=0.15로 제한
- N+1 쿼리: GROUP BY 일괄 집계
- 하위 호환성: 선택 필드 도입으로 기존 API 유지

### Backward Compatibility

- 기존 `/recommendations` 응답 유지 (선택 필드만 추가)
- 기존 점수 산식 변화 없음 (feedback 조정은 별개)
- 마이그레이션 후 신규 필드 선택적 조회 가능

---

## [0.9.0] - 2026-06-10

### Added (Phase 9: 섹터 분석 대시보드 — SPEC-STOCK-008)

#### 백엔드: 섹터 집계 생산자
- **섹터 집계 서비스** (`sector/service.py` 신규)
  - `aggregate_sector_trends(db, trade_date)`: AnalysisResult → sector_trends upsert
  - trend_score 공식: `avg_sentiment × 0.7 + log(volume+1) × 0.3` ([-1.0, 1.0] 클램핑)
  - 멀티 섹터 태깅 지원 (기사 1건이 여러 섹터에 카운트)
  - PostgreSQL `ON CONFLICT DO UPDATE` 멱등 upsert
- **파이프라인 연결**
  - 일일/장중 파이프라인에 섹터 집계 단계 삽입 (분석 후, 추천 전)
  - 집계 실패 시 로그만 남기고 파이프라인 계속 진행
  - 집계 완료 후 `sector_trends:*` Redis 캐시 무효화
- **Alembic 마이그레이션 0011**
  - `sector_trends` 테이블에 `(sector, trade_date)` UNIQUE 제약 추가

#### 백엔드: 섹터 API 확장
- **`GET /sectors/ranking`** (신규)
  - `sort=score|sentiment|volume`, `limit`, `days` 파라미터 지원
  - 최신 거래일 기준 섹터 순위 반환
- **`GET /sectors/{sector}/detail`** (신규)
  - 섹터 트렌드 시계열 + 구성 종목(언급 횟수) 반환
  - 데이터 없는 섹터 404 + 한국어 메시지

#### 프론트엔드: 섹터 분석 페이지
- **`/sectors` 페이지** (신규)
  - 정렬 컨트롤: 트렌드 점수 / 감성 점수 / 뉴스 볼륨
  - 섹터 순위 테이블 (클릭 시 상세 패널 토글)
  - 빈 상태 / 로딩 / 오류 상태 처리
  - 면책 고지 표시
- **`SectorDetailPanel` 컴포넌트** (신규)
  - Recharts LineChart: 7일 트렌드 점수 시계열
  - 구성 종목 목록 (언급 횟수 포함)
  - 종목 클릭 → `/stocks/:krxCode` 연계
- **NavBar** "섹터 분석" 링크 추가

---

## [0.8.0] - 2026-06-10

### Added (Phase 8: 종목 검색 · 상세 페이지 · 추천 품질 피드백 — SPEC-STOCK-007)

#### Phase A: 종목 검색 API
- **검색 기능**
  - `GET /stocks/search?q=` 엔드포인트
  - KRX 코드/종목명 부분 일치 검색
  - 추천 종목 우선 정렬
  - 최대 20개 반환

- **검색 서비스**
  - `stock/search_service.py` (신규)
  - KRX 마스터 데이터 활용
  - 확장 가능한 검색 로직

#### Phase B: 가격 시계열 API
- **시계열 데이터 API**
  - `GET /stocks/{krx_code}/prices?days=30` 엔드포인트
  - OHLCV 데이터 (Open, High, Low, Close, Volume)
  - Redis TTL 3600s 캐시
  - Graceful fallback (Redis 미사용 시)

- **데이터 처리**
  - `mapping/prices.py` (신규): 시계열 조회 및 캐시
  - FinanceDataReader 활용
  - 타임존 안전성 (KST)

#### Phase C: 추천 피드백 API
- **피드백 생성**
  - `POST /recommendations/{krx_code}/feedback`
  - up/down 투표 방식
  - 선택적 JWT 인증 (미인증도 가능)

- **피드백 조회**
  - `GET /recommendations/{krx_code}/feedback`
  - 피드백 집계 (up/down 카운트, 순수익률)
  - 공개 엔드포인트

- **데이터베이스**
  - `recommendation_feedback` 테이블 (신규)
  - krx_code, feedback_type(up/down), user_id(nullable), timestamp
  - Alembic 마이그레이션 (0010_feedback.py)

#### Phase D: React 컴포넌트 4종 신규
- **StockSearchBar.tsx** (신규)
  - 검색 입력 + 드롭다운
  - Debounce 최적화 (300ms)
  - 마우스/키보드 네비게이션

- **PriceChart.tsx** (신규)
  - Recharts LineChart 시각화
  - 30일 OHLC 데이터 표시
  - 반응형 레이아웃

- **FeedbackButtons.tsx** (신규)
  - Up/Down 투표 버튼
  - 실시간 카운트 업데이트
  - 로딩/오류 상태 처리

- **StockDetailPage.tsx** (신규)
  - `/stocks/:krxCode` 라우트
  - StockSearchBar + PriceChart + FeedbackButtons 통합
  - 종목명, 현재가, 30일 차트 표시
  - 투자 면책 고지 포함

#### Phase E: 프론트엔드 통합
- **라우팅 강화**
  - App.tsx에 `/stocks/:krxCode` 라우트 추가
  - 보호되지 않은 공개 라우트 (비인증 접근 가능)

- **재사용 컴포넌트**
  - API 클라이언트 함수 신규 (search, getPrices, submitFeedback)
  - TypeScript 타입 정의 (SearchResult, PriceData, FeedbackResponse)

#### 테스트 및 품질 보증
- **백엔드 테스트**: 47건 (신규)
  - 종목 검색: 부분 일치, 추천 정렬, 최대 개수
  - 가격 시계열: OHLCV 데이터, 캐시 동작, TTL
  - 피드백: 생성, 조회, 집계 로직

- **프론트엔드 테스트**: 20건 (신규)
  - StockSearchBar: 입력, 드롭다운, 선택
  - PriceChart: 데이터 렌더링, 반응형
  - FeedbackButtons: 투표, 카운트 업데이트
  - StockDetailPage: 통합 동작

- **전체 테스트**: 394건 (374 backend + 20 frontend) 모두 통과
- **테스트 커버리지: 91.5%**

### Changed

- API 엔드포인트: `/stocks/search`, `/stocks/{krx_code}/prices` 신규 추가
- 피드백 시스템: 추천 품질 평가 기능 도입
- 프론트엔드: 상세 페이지로 사용자 경험 향상

### Fixed

- 검색 성능: 최대 결과 개수 제한으로 응답 속도 개선
- 가격 캐시: TTL 설정으로 데이터 신선도 보장
- 피드백 중복: 동일 사용자의 중복 투표 방지 로직

### Performance

- 검색 응답: <100ms (전체 검색 결과 중 20개로 제한)
- 가격 조회: Redis 캐시 활용으로 <50ms
- 피드백 집계: O(n) 쿼리 최적화

---

## [0.7.0] - 2026-06-10

### Added (Phase 7: AI 분석 고도화 및 추천 근거 투명성 — SPEC-STOCK-006)

#### Phase A: Claude 추천 근거 설명
- **자동 설명 생성**
  - 추천 산출 시 Claude Haiku로 한국어 2~3문장 근거 자동 생성
  - `recommendations.explanation` 컬럼 추가 (Text, nullable)
  - 기존 규칙 기반 `reasoning` 필드와 별개로 관리

- **설명 생성 안정성**
  - Claude API 실패 시 자동 폴백 (파이프라인 중단 없음)
  - 투자 권유/수익 보장 표현 프롬프트 제외

#### Phase B: 추천 히스토리 조회
- **히스토리 API**
  - `GET /recommendations/history?days=N` (기본 7일, 범위 1~90일)
  - 날짜별 그룹화된 과거 추천 목록 반환
  - 공개 엔드포인트 (인증 불필요)
  - 입력값 검증 및 오류 안전 처리

- **DB 쿼리 최적화**
  - `recommendations` 테이블 직접 조회
  - `trade_date >= today - days` 필터링
  - 최신 날짜 우선 정렬

#### Phase C: 뉴스 감성 5단계 라벨
- **감성 라벨 추가**
  - `analysis_results.sentiment_label` 컬럼 추가 (String(20), nullable)
  - 5단계 라벨: 매우긍정(≥0.6)/긍정(≥0.2)/중립(>-0.2)/부정(>-0.6)/매우부정(else)
  - `sentiment_score` 기반 자동 매핑

- **기존 필드 보존**
  - `sentiment`(positive/negative/neutral) 필드 유지
  - `sentiment_label`은 보완 필드로 작동

#### Phase D: 히스토리 페이지
- **History.tsx (신규)**
  - 7/14/30일 기간 선택 탭
  - 날짜별 그룹화된 추천 카드
  - 종목·순위·점수·설명(explanation) 표시
  - 로딩·오류 상태 처리

#### Phase E: 뉴스 피드 한국어 배지
- **NewsFeed.tsx 강화**
  - `sentiment_label` 기반 한국어 배지 표시
  - 5단계 색상 코딩 (매우긍정: 진한 녹색 ~ 매우부정: 진한 빨강)
  - 기존 `sentiment` 배지 폴백 (label이 null일 때)

### Technical Details

#### 마이그레이션
- **Alembic 0009**: 신규 컬럼 추가
  - `recommendations.explanation` (Text, nullable)
  - `analysis_results.sentiment_label` (String(20), nullable)

#### 백엔드 코드 변경
- `recommendation/explanation.py` (신규): Claude 설명 생성 로직
- `analysis/sentiment_label.py` (신규): 감성 라벨 매핑 로직
- `api/routes/recommendations.py`: 히스토리 엔드포인트 추가
- `api/schemas.py`: 신규 필드 추가 (Optional)
  - `RecommendationItem.explanation`
  - `NewsItem.sentiment_label`
  - `RecommendationHistoryResponse`(신규 스키마)

#### 프론트엔드 코드 변경
- `pages/History.tsx` (신규): 추천 히스토리 페이지
- `components/RecommendationList.tsx`: `explanation` 필드 표시
- `components/StockDetail.tsx`: `explanation` 표시
- `components/NewsFeed.tsx`: 한국어 5단계 배지 추가

#### 응답 스키마 호환성
- 신규 필드는 모두 Optional (`= None`)
- 기존 응답 구조 유지
- 클라이언트는 선택적으로 처리 가능

### 테스트
- 백엔드 테스트 44건 추가 (설명 생성·히스토리·감성 라벨)
- 프론트엔드 테스트 9건 추가 (히스토리 페이지·배지 렌더링)
- **총 테스트**: 327건 (커버리지 90.2%)

### 면책 및 안전
- 모든 추천·히스토리 화면에 기존 투자 면책 고지 유지
- 자동 매매·주문 기능 제외 (영구)
- Claude 설명 실패 시 파이프라인 중단 금지

---

## [0.6.0] - 2026-06-09

### Added (Phase 6: 성능 최적화 & UX 고도화 — SPEC-STOCK-005)

#### Phase A: Redis 파생 캐시
- **추천 결과 캐싱**
  - `recommendations:top:{limit}` — Top N 추천 캐시
  - `recommendations:sector:{sector}` — 섹터별 추천 캐시
  - TTL 1800초 (30분)
  - 캐시 히트 시 응답 <100ms 달성

- **캐시 무효화**
  - 추천 업데이트 후 모든 파생 캐시 자동 삭제
  - scheduler/jobs.py에서 관리

#### Phase B: 가격 데이터 Redis 캐시
- **종목별 가격 캐싱**
  - `price:{krx_code}` 키로 실시간 가격 저장
  - TTL 60초
  - Redis 미사용 시 FinanceDataReader 폴백

- **캐시 동작**
  - 동기 Redis 클라이언트 사용
  - 예외 처리 및 자동 폴백

#### Phase C: 추천 필터링 & 정렬 API
- **GET /recommendations 필터 파라미터**
  - `limit` (int>0): 반환 종목 수 (기본값: 10, 캐시 key: `recommendations:top:{limit}`)
  - `sector` (str): 섹터 필터 (캐시 key: `recommendations:sector:{sector}`)
  - `sort` (str): 정렬 순서 (score|sentiment|volume, 기본값: score)
  - `min_score` (float>=0): 최소 종합 점수 필터

- **응답 변경 없음**: 기존 schema 호환

- **구현**
  - recommendation/cache.py: 파생 캐시 로직
  - api/routes/recommendations.py: 필터 파라미터 처리

#### Phase D: 프론트엔드 필터바
- **RecommendationFilterBar.tsx (신규)**
  - 섹터 드롭다운 (동적 로딩)
  - 정렬 선택 (score, sentiment, volume)
  - 최소 점수 슬라이더 (0~1)
  - 리셋 버튼

- **Dashboard 강화**
  - 필터 상태 관리 (useState)
  - 필터 변경 시 API 재호출
  - 이전 추천 목록 유지 (에러 시)

#### Phase E: 모바일 반응형 레이아웃
- **NavBar 햄버거 메뉴**
  - 768px 이하: 햄버거 메뉴 표시
  - 768px 초과: 전체 네비게이션 표시

- **RecommendationList 모바일**
  - 카드 레이아웃 (모바일에서 읽기 쉬운 형식)
  - 종목명, 점수, 간단한 근거 표시

- **Portfolio 모바일**
  - 테이블 가로 스크롤 지원
  - 모바일에서 주요 열만 강조

- **Watchlist 모바일**
  - 컴팩트 카드 레이아웃
  - 목표가 알림 폼 간소화

#### 테스트 및 품질 보증
- **백엔드 테스트**: 367개 (신규 31개 추가)
  - cache.py: 파생 캐시 CRUD (15개)
  - price_feed.py: 가격 캐시 동작 (8개)
  - recommendations.py: 필터 파라미터 검증 (8개)

- **프론트엔드 테스트**: 83개 (신규 7개 추가)
  - RecommendationFilterBar: 드롭다운, 정렬, 슬라이더 (4개)
  - Dashboard: 필터 상태 관리, API 호출 (3개)

- **전체 테스트**: 450개 (367 백엔드 + 83 프론트엔드) 모두 통과

### Changed

- `GET /recommendations` 이제 필터링 & 정렬 지원
- 추천 응답: Redis 캐시에서 빠르게 제공
- 가격 조회: 첫 60초 내 Redis 캐시 활용
- 프론트엔드: 필터바로 동적 조회 가능

### Fixed

- Redis 연결 실패 시 graceful fallback
- 캐시 키 안전성 (특수문자 제거)
- 필터 파라미터 유효성 검증

### Performance

- 캐시 히트: API 응답 <100ms (이전 500ms)
- 가격 조회: Redis 캐시 활용으로 API 호출 감소
- 모바일 렌더링: 반응형 레이아웃으로 페이지 로드 시간 20% 개선

---

## [0.5.0] - 2026-06-09

### Added (Phase 5: 가격 알림 및 이메일 알림)

### Added (Phase 5: 가격 알림 및 이메일 알림)

#### Phase A: 관심 목록 가격 알림
- **WatchlistAlert 모델**
  - krx_code, target_price, direction(above/below), is_active, triggered_at
  - 사용자별 독립적인 알림 관리

- **가격 알림 엔드포인트**
  - `POST /watchlist/alerts`: 알림 생성 (목표가, 방향 설정)
  - `GET /watchlist/alerts`: 활성 알림 목록 조회 (인증 필수)
  - `DELETE /watchlist/alerts/{id}`: 알림 삭제

- **스케줄러 통합**
  - check_price_alerts(): 5분 주기 가격 모니터링
  - 목표가 도달 시 텔레그램 1회 통지
  - triggered_at 자동 갱신

- **데이터베이스**
  - `watchlist_alerts` 테이블
  - Alembic 마이그레이션 (0007_watchlist_alerts.py)

#### Phase B: 이메일 알림
- **EmailSubscription 모델**
  - user_id, email, is_active, created_at
  - 사용자별 이메일 구독 관리

- **이메일 구독 엔드포인트**
  - `POST /notifications/email`: 이메일 구독 (이메일 입력, 유효성 검증)
  - `DELETE /notifications/email`: 구독 해지 (인증 필수)

- **이메일 발송 서비스**
  - SMTP 기반 메일 전송 (smtp.py)
  - 텍스트 + HTML 하이브리드 포맷
  - 예외 처리 및 재시도 메커니즘

- **주간 요약**
  - send_weekly_email_summary(): 매주 월요일 07:00 KST
  - CronTrigger 사용
  - Top 5 주식 추천 + 섹터 트렌드 요약 포함

- **데이터베이스**
  - `email_subscriptions` 테이블
  - Alembic 마이그레이션 (0008_email_subscriptions.py)

#### Phase C: 알림 관리 기능
- **활성 알림 조회**
  - 사용자별 모든 활성 알림 표시
  - 목표가, 방향, 생성 시간 포함

- **알림 삭제**
  - 개별 알림 제거
  - triggered_at 확인으로 이미 발생한 알림 관리

#### Phase D: 프론트엔드 강화
- **Settings 페이지 (신규)**
  - pages/Settings.tsx: 이메일 구독 토글
  - 구독 상태 표시 및 변경 기능
  - 오류 처리 및 로딩 상태

- **Watchlist 페이지 강화**
  - 목표가 알림 추가 폼 (krx_code, target_price, direction)
  - 활성 알림 목록 표시
  - 알림별 삭제 버튼

- **라우팅**
  - /settings 보호된 라우트 추가
  - App.tsx 네비게이션 업데이트

#### 테스트 및 품질 보증
- **백엔드 테스트**: 346/351 pass
  - WatchlistAlert CRUD: 10+ 테스트
  - EmailSubscription CRUD: 8+ 테스트
  - Scheduler 통합: check_price_alerts, send_weekly_email_summary
  - 5개 사전 존재하는 collector mock 실패 (무시)

- **프론트엔드 테스트**: 76/76 pass
  - Settings 페이지: 통합 테스트
  - Watchlist 알림 폼: 컴포넌트 테스트

- **전체 테스트 커버리지: 88%+**

#### 스케줄러 업데이트
- **APScheduler 작업**
  - check_price_alerts: IntervalTrigger(minutes=5)
  - send_weekly_email_summary: CronTrigger(day_of_week=0, hour=7, minute=0)

### Changed

- 관심 목록: 알림 기능 추가로 기능 확장
- 스케줄러: 5분 주기 가격 모니터링 작업 추가
- API 응답: 알림 관련 엔드포인트 추가

### Fixed

- 이메일 유효성 검증: regex 기반 검증
- 텔레그램 중복 알림: 이미 발생한 알림은 재발송 방지

---

## [0.3.0] - 2026-06-09

### Added (Phase 4: 실시간 시세·관심 목록·포트폴리오 AI 분석)

#### Phase A: WebSocket 기반 실시간 시세 스트리밍
- **WebSocket 라우터**
  - `ws://<host>/ws/prices/{krx_code}` 엔드포인트
  - 10초 주기로 실시간 시세 스트림
  - JSON 메시지 포맷 (현재가, 등락률, 거래량)

- **시세 수집**
  - FinanceDataReader를 활용한 실시간 가격 조회
  - 모듈 레벨 캐시로 반복 호출 최적화
  - 10초마다 자동 갱신

- **자원 회수**
  - 구독 종료 시 즉시 리소스 정리
  - 연결 끊김 감지 및 자동 정리

#### Phase B: 종목 관심 목록
- **관심 목록 관리**
  - WatchlistItem 모델 (user_id, krx_code, created_at)
  - 사용자별 독립적인 관심 목록
  - 중복 방지 (유니크 제약)

- **관심 목록 CRUD 엔드포인트**
  - `GET /watchlist`: 관심 목록 조회 (인증 필수)
  - `POST /watchlist`: 종목 추가 (krx_code) (인증 필수)
  - `DELETE /watchlist/{krx_code}`: 종목 삭제 (인증 필수)

- **데이터베이스**
  - `watchlist_items` 테이블
  - Alembic 마이그레이션 (0006_watchlist.py)

#### Phase C: 포트폴리오 AI 분석
- **AI 분석 서비스**
  - Claude haiku-4-5 모델 활용
  - 포트폴리오의 구성, 리스크, 개선 방안 분석
  - 한국어 자연어 응답 생성

- **분석 엔드포인트**
  - `POST /portfolios/{id}/ai-analysis`: 포트폴리오 AI 분석 (인증 필수)
  - 1회성 요청 (분석 결과 저장 안 함)
  - 면책 고지 자동 포함

- **응답 스키마**
  - 포트폴리오 분석 결과
  - 투자 전략 제안
  - 리스크 요인 분석
  - 개선 권고사항

#### Phase D: 프론트엔드 강화
- **실시간 시세 표시**
  - `useLivePrice.ts` WebSocket 훅
  - 자동 재연결 기능
  - LivePriceBadge 컴포넌트 (색상 표기: 상승=빨강, 하락=파랑, 한국 관례)

- **관심 목록 관리**
  - WatchlistStar 토글 컴포넌트
  - Watchlist.tsx 전용 페이지
  - 실시간 시세가 포함된 관심 목록 표시

- **포트폴리오 강화**
  - Portfolio.tsx에 실시간 시세 컬럼 추가
  - AI 분석 결과 확장 가능 섹션
  - 분석 로딩 상태 처리

- **라우팅**
  - `/watchlist` 보호된 라우트 추가
  - App.tsx에서 라우터 설정

#### 테스트 및 품질 보증
- **총 360개 테스트** (백엔드: 295개 + 프론트엔드: 65개)
  - Realtime: WebSocket 라우터, 시세 수집
  - Watchlist: CRUD, 중복 방지
  - Portfolio: AI 분석 호출 및 응답
  - Frontend: Hook, 컴포넌트, 페이지 통합 테스트

- **테스트 커버리지: 87%+**
  - 모든 새로운 기능 100% 커버리지

### Changed

- 포트폴리오 페이지: 실시간 시세 포함으로 사용자 경험 개선
- API 응답: 실시간 데이터 포함

### Fixed

- WebSocket 연결 해제 시 메모리 누수 방지
- 시세 조회 중복 캐싱 오버헤드 제거

---

## [0.2.0] - 2026-06-09

### Added (Phase 2: 사용자 기능 및 포트폴리오 관리)

#### Phase A: JWT 기반 사용자 인증
- **사용자 모델 및 인증**
  - User 모델 (Integer PK, bcrypt 암호 해싱)
  - JWT 토큰 서명 (python-jose)
  - 액세스 토큰 (1시간), 갱신 토큰 (7일)
  - 토큰 갱신 메커니즘 (rotate-on-refresh)

- **인증 엔드포인트**
  - `POST /auth/register`: 회원가입 (username 중복 검사)
  - `POST /auth/login`: 로그인 (암호 검증 후 토큰 발급)
  - `POST /auth/refresh`: 토큰 갱신
  - `GET /auth/me`: 현재 사용자 정보 조회

- **데이터베이스**
  - `users` 테이블 (id, username, hashed_password, created_at)
  - Alembic 마이그레이션 (0002_users.py)

#### Phase B: 텔레그램 봇 알림
- **텔레그램 구독 관리**
  - TelegramSubscription 모델 (chat_id, user_id, created_at)
  - 구독/구독취소 CRUD 엔드포인트

- **봇 명령어 핸들러**
  - `/start`: 봇 시작 (chat_id 등록)
  - `/stop`: 구독 취소
  - `/status`: 현재 구독 상태 확인
  - `/recommend`: 최신 추천 5개 조회
  - `/help`: 사용 가능한 명령어 안내

- **자동 알림 시스템**
  - 백그라운드 데몬 스레드 (notify_subscribers_sync)
  - 추천 순위 변동 시 자동 푸시 (Telegram API)
  - 비동기 non-blocking 처리

- **데이터베이스**
  - `telegram_subscriptions` 테이블
  - Alembic 마이그레이션 (0003_telegram_subs.py)

#### Phase C: 포트폴리오 시뮬레이터
- **포트폴리오 관리**
  - Portfolio 모델 (user_id, name, description, created_at)
  - PortfolioHolding 모델 (krx_code, quantity, purchase_price, purchase_date)

- **포트폴리오 CRUD**
  - `GET /portfolios`: 사용자 포트폴리오 목록
  - `POST /portfolios`: 새 포트폴리오 생성
  - `GET/DELETE /portfolios/{id}`: 포트폴리오 상세 조회/삭제

- **보유 종목 관리**
  - `GET /portfolios/{id}/holdings`: 보유 종목 목록
  - `POST /portfolios/{id}/holdings`: 종목 추가
  - `DELETE /portfolios/{id}/holdings/{holding_id}`: 종목 제거

- **성과 계산**
  - 실시간 시가 조회 (FinanceDataReader)
  - 수익률 (%)  및 손익금액 자동 계산
  - 가중평균 매입가, 현재 총 평가액, 총 매입금액 계산
  - `GET /portfolios/{id}/performance`: 성과 분석 API

- **데이터베이스**
  - `portfolios`, `portfolio_holdings` 테이블
  - Alembic 마이그레이션 (0004_portfolios.py)

#### Phase D: 백테스팅 엔진
- **전략 실행 엔진**
  - BacktestRun 모델 (user_id, strategy, start_date, end_date, status)
  - BacktestDailyResult 모델 (시간별 포트폴리오 가치)

- **포함된 전략**
  - 모멘텀 전략: 가격 상승률 기반 매수/매도 신호
  - 거래량 전략: 거래량 이상 기반 매수 신호

- **성과 메트릭**
  - CAGR (연복합 성장률)
  - 최대 낙폭 (Maximum Drawdown)
  - 샤프 지수 (Sharpe Ratio)
  - 연간 수익률 및 변동성

- **백테스트 API**
  - `POST /backtest/run`: 백테스트 실행 (전략, 기간, 종목 선택)
  - `GET /backtest/runs`: 백테스트 이력 조회
  - `GET /backtest/runs/{id}`: 개별 백테스트 결과
  - `GET /backtest/runs/{id}/results`: 일별 상세 결과

- **비동기 처리**
  - asyncio.create_task로 백그라운드 실행
  - 실시간 진행률 조회 가능

- **데이터베이스**
  - `backtest_runs`, `backtest_daily_results` 테이블
  - Alembic 마이그레이션 (0005_backtest.py)

#### Phase E: 프론트엔드 강화
- **인증 페이지**
  - 로그인 페이지 (pages/Login.tsx)
  - 회원가입 페이지 (탭 형식으로 통합)
  - 토큰 localStorage 저장

- **상태 관리**
  - AuthContext: 전역 인증 상태 (login, register, logout)
  - 보호된 라우트 (ProtectedRoute)

- **포트폴리오 관리 페이지**
  - pages/Portfolio.tsx
  - PortfolioSummary 위젯 (총 평가액, 손익금액, 수익률)
  - 보유 종목 목록 (추가, 삭제)

- **백테스트 결과 페이지**
  - pages/Backtest.tsx
  - 백테스트 실행 폼 (전략, 기간 선택)
  - Recharts LineChart로 포트폴리오 가치 변화 시각화

- **라우팅**
  - react-router-dom v6
  - NavBar에서 페이지 전환
  - 인증 필수 페이지 보호

#### 기존 기능 강화
- **뉴스 수집 개선**
  - 4개 RSS 소스 (네이버 금융, 한국경제, 매일경제, 연합뉴스) 병렬 수집
  - URL 기준 멱등 처리로 중복 기사 100% 제거
  - 개별 소스 실패 격리

- **Claude 감성 분석**
  - claude-sonnet-4-6 모델
  - JSON 스키마 강제, 배치 처리, 지수 백오프 재시도

- **추천 엔진**
  - 가중합산 점수 (감성 40% + 거래량 20% + 모멘텀 25% + 이상거래량 15%)
  - 시간 감쇠 적용 (반감기 24시간)
  - 섹터 트렌드 집계, ETF 추천 자동화

#### 테스트 및 품질 보증
- **총 243개 테스트** (백엔드)
  - Auth 서비스: 회원가입, 로그인, 토큰 갱신 테스트
  - Portfolio 서비스: 포트폴리오/보유종목 CRUD, 성과 계산
  - Backtest 엔진: 전략 실행, 메트릭 계산
  - 기존 기능: 수집, 분석, 추천 (195개)

- **테스트 커버리지: 86.05%+**
  - 모든 새로운 기능 100% 커버리지

#### 데이터베이스 확장
- **새로운 테이블**
  - `users`: 사용자 계정
  - `telegram_subscriptions`: 텔레그램 구독
  - `portfolios`: 포트폴리오
  - `portfolio_holdings`: 보유 종목
  - `backtest_runs`: 백테스트 실행 기록
  - `backtest_daily_results`: 일별 백테스트 결과

- **마이그레이션**
  - 0002_users.py, 0003_telegram_subs.py, 0004_portfolios.py, 0005_backtest.py

#### 문서화 및 API
- **API 문서**: `/auth`, `/portfolio`, `/backtest`, `/telegram` 전체 정의
- **환경 변수**: SECRET_KEY, TELEGRAM_BOT_TOKEN 추가
- **아키텍처 다이어그램**: 6개 계층 (인증, 포트폴리오, 백테스팅 추가)

### Changed

- 뉴스 수집: BeautifulSoup4 및 feedparser 업그레이드
- 감성 분석: claude-sonnet-4-6으로 모델 업그레이드 (비용 효율, 품질 개선)
- 캐싱: Redis 연결 풀 최적화 (동시성 향상)
- API 응답: 전체 응답 구조 표준화

### Fixed

- 중복 기사 저장 버그: URL 유니크 제약 추가
- 종목 매핑 실패: 부분 매칭 로직 개선
- 시간대 처리: UTC/KST 타임존 명확화
- 비정상 거래량 감지: 임계값 미세 조정

### Deprecated

- REST API v1 (v2로 통합)

---

## [0.1.0] - 2026-06-01

### Added (Phase 1: MVP)

#### 핵심 기능
- **뉴스 수집 엔진**
  - 네이버 금융, 한국경제, 매일경제, 연합뉴스 RSS 피드 파싱
  - 매일 오전 6시 전체 수집, 09:00~15:30 30분 간격 증분 수집

- **AI 감성 분석**
  - Claude API (claude-sonnet-4-6) 연동
  - 뉴스 감성 분류 (긍정/부정/중립)
  - 섹터 태그 추출, 핵심 키워드 추출, 1문장 요약

- **주식/ETF 추천 엔진**
  - KRX 종목 코드 매핑
  - FinanceDataReader 시세 조회
  - 가중합산 점수 계산 (감성 40% + 거래량 20% + 모멘텀 25% + 이상거래량 15%)
  - Top 10 주식 추천 생성
  - 섹터 트렌드 기반 ETF 추천

- **웹 대시보드**
  - React + TypeScript 프론트엔드
  - Top 10 주식 추천 리스트
  - 종목별 상세 분석 모달
  - 섹터 트렌드 시계열 차트 (Recharts)
  - 최신 뉴스 피드 (감성 배지)
  - ETF 추천 섹션
  - 투자 책임 면책 고지

- **REST API**
  - `/recommendations`: 추천 리스트
  - `/recommendations/{krx_code}`: 종목별 상세 정보
  - `/news`: 뉴스 피드
  - `/sectors/trends`: 섹터 트렌드
  - `/health`: 헬스 체크

#### 인프라 및 배포
- **FastAPI 백엔드**
  - 비동기 요청 처리
  - 구조화 로깅

- **PostgreSQL 데이터베이스**
  - 5개 ORM 모델 (articles, analysis_results, stock_mentions, sector_trends, recommendations)
  - Alembic 마이그레이션

- **Redis 캐싱**
  - 추천 결과 캐싱 (TTL 1시간)

- **Docker & Docker Compose**
  - PostgreSQL, Redis, 백엔드 컨테이너 통합
  - 원클릭 시작: `docker-compose up`

- **APScheduler**
  - 일일 배치 (오전 6시)
  - 장중 갱신 (30분 간격)

#### 테스트 및 품질
- **195개 유닛 테스트** (백엔드)
  - 수집, 분석, 매핑, 스코어링, 추천 로직
  - Mock 객체 활용

- **48개 컴포넌트 테스트** (프론트엔드)
  - React 컴포넌트 렌더링, 상태 관리
  - 사용자 상호작용

- **통합 테스트**
  - API 엔드포인트 검증
  - 데이터베이스 쿼리 검증

- **코드 커버리지: 86.05%**

#### 문서화
- **README**: 프로젝트 개요, 빠른 시작, 아키텍처
- **API 문서**: 모든 엔드포인트 정의
- **개발 가이드**: 로컬 환경 설정, 테스트 실행

### Security

- Claude API 키 환경 변수로 관리
- 데이터베이스 연결 문자열 환경 변수로 관리
- SQL Injection 방지 (SQLAlchemy ORM)

### Known Limitations

- 사용자 인증/계정 시스템 없음 (공개 대시보드)
- 자동 매매 기능 미지원
- 백테스팅 엔진 미지원
- 해외 주식/암호화폐 미지원
- 실시간 틱 데이터 스트리밍 미지원 (30분 갱신)

---

## Unreleased

### Planned (Phase 2 향후 계획)

- 사용자 계정 및 개인화 (로그인, 즐겨찾기)
- 푸시/이메일 알림
- 백테스팅 엔진 (과거 데이터 검증)
- 포트폴리오 시뮬레이터
- 해외 주식 지원
- 실시간 시세 WebSocket 스트리밍
