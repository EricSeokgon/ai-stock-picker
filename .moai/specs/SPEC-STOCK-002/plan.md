# SPEC-STOCK-002 구현 계획 (plan.md)

## 1. 아키텍처 변경 사항 (기존 구조에 추가)

SPEC-STOCK-001의 FastAPI + PostgreSQL + Redis + React 구조를 유지하면서 다음 레이어를 추가한다.

```
[기존 유지]
  scheduler/jobs.py (run_daily_pipeline)  ── (후크 추가) ──┐
  FastAPI app, PostgreSQL, Redis, React + Recharts         │
  FinanceDataReader (시세 조회)                            │
                                                           ▼
[Phase 3 신규]
  auth/        ── JWT 인증 (register/login/refresh/me), bcrypt 해싱, 토큰 검증 의존성
  telegram/    ── 봇 명령어 핸들러(/start /subscribe /unsubscribe /today /sectors)
                  + run_daily_pipeline 완료 후 자동 발송 모듈
  portfolio/   ── 사용자별 가상 포트폴리오 CRUD + 수익률 계산(FinanceDataReader 재사용)
  backtest/    ── 비동기 백테스트 러너(가격 모멘텀 + 거래량 이상, 균등 가중)
                  + 지표 계산(누적수익률/승률/평균수익률/MaxDD/Sharpe)
  frontend/    ── 로그인·회원가입 페이지, 포트폴리오 페이지, 백테스팅 페이지,
                  대시보드 "내 포트폴리오 요약" 위젯
```

핵심 통합 포인트:
- **인증 의존성**: 포트폴리오 엔드포인트는 access token 검증 의존성을 공유한다.
- **스케줄러 후크**: `run_daily_pipeline` 정상 완료 직후 텔레그램 자동 발송 함수를 호출한다(실패해도 파이프라인 자체는 성공 처리).
- **시세 재사용**: 포트폴리오 현재가와 백테스트 과거 시세는 모두 FinanceDataReader를 통해 조회한다.
- **하위 호환**: 기존 5개 테이블·기존 API는 수정하지 않고, 신규 테이블·신규 라우터만 추가한다.

---

## 2. 신규 DB 테이블 스키마 (5개)

### 2.1 `users` (REQ-AUTH)

| 컬럼 | 타입 | 제약 |
|------|------|------|
| id | BIGSERIAL | PK |
| username | VARCHAR(50) | UNIQUE, NOT NULL |
| email | VARCHAR(255) | UNIQUE, NOT NULL |
| hashed_password | VARCHAR(255) | NOT NULL (bcrypt) |
| is_active | BOOLEAN | NOT NULL DEFAULT true |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |

인덱스: `username`, `email` UNIQUE 인덱스.

### 2.2 `telegram_subscriptions` (REQ-TG)

| 컬럼 | 타입 | 제약 |
|------|------|------|
| id | BIGSERIAL | PK |
| chat_id | BIGINT | UNIQUE, NOT NULL |
| username | VARCHAR(100) | NULL (텔레그램 표시명) |
| subscribed_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |
| is_active | BOOLEAN | NOT NULL DEFAULT true |

비고: 텔레그램 구독은 익명 chat_id 기반으로, `users`와 강결합하지 않는다(웹 계정 없이도 구독 가능).

### 2.3 `portfolios` (REQ-PORT)

| 컬럼 | 타입 | 제약 |
|------|------|------|
| id | BIGSERIAL | PK |
| user_id | BIGINT | FK → users(id), NOT NULL |
| name | VARCHAR(100) | NOT NULL DEFAULT '기본 포트폴리오' |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |

인덱스: `user_id`.

### 2.4 `portfolio_holdings` (REQ-PORT)

| 컬럼 | 타입 | 제약 |
|------|------|------|
| id | BIGSERIAL | PK |
| portfolio_id | BIGINT | FK → portfolios(id) ON DELETE CASCADE, NOT NULL |
| krx_code | VARCHAR(20) | NOT NULL |
| quantity | INTEGER | NOT NULL CHECK (quantity > 0) |
| purchase_price | NUMERIC(15,2) | NOT NULL CHECK (purchase_price > 0) |
| added_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |

제약: `(portfolio_id, krx_code)` UNIQUE (한 포트폴리오 내 동일 종목 중복 방지).

### 2.5 `backtest_runs` (REQ-BT)

| 컬럼 | 타입 | 제약 |
|------|------|------|
| id | BIGSERIAL | PK (= job_id) |
| status | VARCHAR(20) | NOT NULL DEFAULT 'pending' (pending/running/completed/failed) |
| start_date | DATE | NOT NULL |
| end_date | DATE | NOT NULL |
| metrics | JSONB | NULL (완료 시 핵심 지표 저장) |
| error_message | TEXT | NULL |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |
| completed_at | TIMESTAMPTZ | NULL |

### 2.6 `backtest_daily_results` (REQ-BT)

| 컬럼 | 타입 | 제약 |
|------|------|------|
| id | BIGSERIAL | PK |
| run_id | BIGINT | FK → backtest_runs(id) ON DELETE CASCADE, NOT NULL |
| trade_date | DATE | NOT NULL |
| portfolio_return | NUMERIC(10,6) | NOT NULL (당일 추천 포트폴리오 익일 수익률) |
| benchmark_return | NUMERIC(10,6) | NOT NULL (KOSPI 익일 수익률) |
| top10_stocks | JSONB | NOT NULL (당일 Top 10 krx_code 배열) |

제약: `(run_id, trade_date)` UNIQUE. 인덱스: `run_id`.

> 비고: 명세상 신규 테이블은 5개로 안내되었으나, 백테스트 일별 결과를 정규화 저장하기 위해 `backtest_daily_results`를 분리한다(총 6개 테이블). `metrics`는 `backtest_runs.metrics` JSONB에 요약 저장한다.

---

## 3. 신규 API 엔드포인트

### 3.1 인증 (REQ-AUTH)

| 메서드 | 경로 | 인증 | 설명 |
|--------|------|------|------|
| POST | `/auth/register` | 불필요 | 회원가입 (username, email, password) |
| POST | `/auth/login` | 불필요 | 로그인 → access + refresh token |
| POST | `/auth/refresh` | refresh token | access token 갱신 |
| GET | `/auth/me` | access token | 현재 사용자 정보 |

### 3.2 텔레그램 (REQ-TG)

봇 명령어는 텔레그램 webhook/polling으로 처리(REST 엔드포인트 외부 노출 아님). 자동 발송은 스케줄러 후크.

| 트리거 | 동작 |
|--------|------|
| `/start` | 봇 소개·구독 안내 |
| `/subscribe` | chat_id 구독 등록 |
| `/unsubscribe` | 구독 취소 |
| `/today` | 당일 Top 5 즉시 조회 |
| `/sectors` | 섹터 트렌드 Top 3 즉시 조회 |
| `run_daily_pipeline` 완료 후크 | 활성 구독자에게 Top 5 + 섹터 Top 3 자동 발송 |

### 3.3 포트폴리오 (REQ-PORT) — 전부 access token 필요

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/portfolio` | 내 포트폴리오 조회 |
| POST | `/portfolio/holdings` | 종목 추가 (krx_code, quantity, purchase_price) |
| PUT | `/portfolio/holdings/{krx_code}` | 수량 변경 |
| DELETE | `/portfolio/holdings/{krx_code}` | 종목 제거 |
| GET | `/portfolio/performance` | 수익률 분석 + 편입 제안 |

### 3.4 백테스팅 (REQ-BT)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/backtest/run` | 백테스트 실행 요청(비동기) → job_id 반환 |
| GET | `/backtest/status/{job_id}` | 실행 상태 조회 |
| GET | `/backtest/results/{job_id}` | 결과(지표 + 일별 수익률) 조회 |
| GET | `/backtest/history` | 과거 백테스트 목록 |

---

## 4. 구현 단계 (Priority별)

### Phase 3-A (Priority High): JWT 인증

1. `python-jose`, `passlib[bcrypt]` 의존성 추가, JWT 서명 시크릿 환경 변수 도입.
2. `users` 테이블 + Alembic 마이그레이션.
3. 비밀번호 해싱(bcrypt cost 12) + 검증 유틸, 토큰 발급/검증 유틸.
4. `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/me` 라우터.
5. 재사용 가능한 `get_current_user` 인증 의존성(포트폴리오에서 공유).

### Phase 3-B (Priority High): 텔레그램 알림

1. `python-telegram-bot` 의존성 추가, `TELEGRAM_BOT_TOKEN` 환경 변수 도입.
2. `telegram_subscriptions` 테이블 + 마이그레이션.
3. 명령어 핸들러: `/start /subscribe /unsubscribe /today /sectors` (기존 추천·섹터 조회 로직 재사용).
4. 자동 발송 모듈 + `run_daily_pipeline` 완료 후크 연동(부분 실패 격리, 403 시 구독 비활성).

### Phase 3-C (Priority Medium): 포트폴리오 시뮬레이터

1. `portfolios`, `portfolio_holdings` 테이블 + 마이그레이션.
2. 포트폴리오 CRUD 라우터(인증 의존성 적용, 소유권 검증).
3. 현재가·수익률 계산(FinanceDataReader 재사용, 종목별/전체).
4. Top 10 추천 대비 미보유 종목 "편입 제안" 로직.
5. 프론트엔드: 로그인/회원가입 페이지, 포트폴리오 관리 페이지, 대시보드 요약 위젯.

### Phase 3-D (Priority Low): 백테스팅 엔진

1. `backtest_runs`, `backtest_daily_results` 테이블 + 마이그레이션.
2. 비동기 러너(백그라운드 태스크/워커): 영업일별 시세 기반 점수 재계산 → 익일 수익률 측정.
3. 지표 계산: 누적 수익률(vs KOSPI), 승률, 평균 수익률, Max Drawdown, Sharpe(국고채 3년물 무위험).
4. 상태/결과/이력 조회 라우터.
5. 프론트엔드: 기간 선택 페이지, 누적 수익률 vs KOSPI 라인 차트, 지표 카드.

---

## 5. 기술 스택 추가 사항

| 패키지 | 용도 | 비고 |
|--------|------|------|
| `python-telegram-bot` | 텔레그램 봇 명령어·발송 | 비동기 API |
| `python-jose[cryptography]` | JWT 인코딩/디코딩 | access/refresh token |
| `passlib[bcrypt]` | bcrypt 비밀번호 해싱 | cost factor 12 |

신규 환경 변수: `TELEGRAM_BOT_TOKEN`, `JWT_SECRET_KEY`, `JWT_ALGORITHM`(예: HS256), `ACCESS_TOKEN_EXPIRE_MINUTES=60`, `REFRESH_TOKEN_EXPIRE_DAYS=7`, `RISK_FREE_RATE`(국고채 3년물). 모두 `.env.example`에 추가하고 버전 관리 제외.

기존 스택(FastAPI/PostgreSQL/Redis/React/Recharts/FinanceDataReader/APScheduler)은 변경하지 않는다.

---

## 6. 리스크

| 리스크 | 영향 | 완화 방안 |
|--------|------|----------|
| 비동기 백테스트가 단일 서버 자원을 장시간 점유 | 다른 요청 응답 저하 | 백그라운드 태스크/별도 워커로 분리, 동시 실행 1건 제한, 진행률·상태 폴링 제공 |
| FinanceDataReader 과거 시세 결측·지연 | 백테스트·포트폴리오 정확도 저하 | 결측 영업일 스킵·기록(REQ-BT-008), 현재가 실패 시 종목 단위 격리(REQ-PORT-009) |
| 텔레그램 발송이 파이프라인을 블로킹/실패 전파 | 일일 추천 생성 자체 실패 | 발송을 파이프라인 성공 이후 후크로 분리, 발송 실패는 로그·격리(REQ-TG-007) |
| JWT 시크릿·봇 토큰 노출 | 계정 탈취·봇 도용 | 환경 변수 관리, 로그에 토큰·비밀번호 원문 금지(REQ-NFR-004), 운영 HTTPS 강제 |
| 백테스트 단순화(뉴스 감성 배제)로 인한 성과 오해 | 사용자가 실거래 성과로 오인 | 단순화 사실을 결과·UI에 명시(REQ-BT-003), 면책 고지 유지(REQ-FE-005) |
| 포트폴리오 소유권 검증 누락 | 타 사용자 데이터 접근 | 모든 포트폴리오 엔드포인트에서 user_id 소유권 검증(REQ-PORT-008) |
| 기존 시스템 회귀 | MVP 기능 손상 | 신규 테이블·라우터만 추가, 기존 자산 무수정(REQ-NFR-005), 회귀 테스트 |
