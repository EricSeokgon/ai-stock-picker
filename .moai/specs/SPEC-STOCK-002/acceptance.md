# SPEC-STOCK-002 인수 기준 (acceptance.md)

표기: Given(전제) - When(행위) - Then(기대 결과). 각 Feature별 3개 이상.

---

## 1. JWT 사용자 인증 (REQ-AUTH)

### AC-AUTH-01: 회원가입 성공
- **Given** 미등록 username·email과 8자 이상 비밀번호가 주어졌을 때
- **When** `POST /auth/register`를 호출하면
- **Then** 201과 함께 사용자가 생성되고, `users.hashed_password`는 bcrypt 해시(cost ≥ 12)로 저장되며, 응답에 평문 비밀번호가 포함되지 않는다.

### AC-AUTH-02: 로그인 토큰 발급
- **Given** 가입된 사용자가 있을 때
- **When** 올바른 자격 증명으로 `POST /auth/login`을 호출하면
- **Then** access token(만료 1시간)과 refresh token(만료 7일)이 발급되고, access token으로 `GET /auth/me` 호출 시 200과 사용자 정보(해시 제외)가 반환된다.

### AC-AUTH-03: 잘못된 자격 증명 거부
- **Given** 가입된 사용자가 있을 때
- **When** 틀린 비밀번호로 `POST /auth/login`을 호출하면
- **Then** 401이 반환되고 토큰이 발급되지 않는다.

### AC-AUTH-04: 토큰 갱신
- **Given** 유효한 refresh token이 있을 때
- **When** `POST /auth/refresh`를 호출하면
- **Then** 새 access token이 발급되고, 만료된/위변조된 토큰일 경우 401이 반환된다.

### AC-AUTH-05: 중복 가입 거부
- **Given** 이미 존재하는 email이 있을 때
- **When** 동일 email로 `POST /auth/register`를 호출하면
- **Then** 409가 반환되고 신규 계정이 생성되지 않는다.

---

## 2. 텔레그램 알림 시스템 (REQ-TG)

### AC-TG-01: 구독 등록
- **Given** 봇과 대화를 시작한 사용자가 있을 때
- **When** `/subscribe`를 보내면
- **Then** 해당 chat_id가 `telegram_subscriptions`에 `is_active=true`로 저장되고 구독 완료 메시지를 받는다.

### AC-TG-02: 일일 자동 발송
- **Given** 활성 구독자 2명과 당일 추천 데이터가 생성된 상태에서
- **When** `run_daily_pipeline`이 정상 완료되면
- **Then** 두 구독자 모두 Top 5 추천(rank, krx_code, 근거 요약)과 상위 3개 섹터 트렌드를 자동 수신한다.

### AC-TG-03: 즉시 조회 명령어
- **Given** 당일 추천 데이터가 있는 상태에서
- **When** 사용자가 `/today`를 보내면
- **Then** Top 5 추천이 즉시 응답되고, `/sectors`는 섹터 Top 3을 응답한다.

### AC-TG-04: 발송 실패 격리
- **Given** 활성 구독자 중 1명이 봇을 차단한 상태에서
- **When** 자동 발송이 실행되면
- **Then** 차단된 chat은 스킵·로그되고 그 chat_id는 구독 비활성으로 전환되며, 나머지 구독자는 정상 수신한다.

---

## 3. 포트폴리오 시뮬레이터 (REQ-PORT)

### AC-PORT-01: 종목 추가 및 조회
- **Given** 인증된 사용자가 있을 때
- **When** `POST /portfolio/holdings`로 krx_code·quantity·purchase_price를 추가한 뒤 `GET /portfolio`를 호출하면
- **Then** 추가한 종목이 보유 목록에 나타난다.

### AC-PORT-02: 수익률 계산
- **Given** 보유 종목이 있는 포트폴리오가 있을 때
- **When** `GET /portfolio/performance`를 호출하면
- **Then** FinanceDataReader 현재가 기준 종목별·전체 평가금액과 수익률이 반환되고, Top 10 추천 중 미보유 종목이 "편입 제안"으로 함께 제시된다.

### AC-PORT-03: 미인증 접근 차단
- **Given** access token이 없는 요청자가 있을 때
- **When** `GET /portfolio`를 호출하면
- **Then** 401이 반환되고 어떤 포트폴리오 데이터도 노출되지 않는다.

### AC-PORT-04: 소유권·유효성 검증
- **Given** 인증된 사용자 A가 있을 때
- **When** 존재하지 않는 krx_code 추가, 0 이하 수량 추가, 또는 타 사용자 보유 종목 조작을 시도하면
- **Then** 각각 404/422/403으로 거부된다.

---

## 4. 백테스팅 엔진 (REQ-BT)

### AC-BT-01: 비동기 실행과 상태 추적
- **Given** 유효한 기간(2025-01-01 ~ 2026-06-01)이 주어졌을 때
- **When** `POST /backtest/run`을 호출하면
- **Then** 즉시 job_id가 반환되고, `GET /backtest/status/{job_id}`로 상태(pending→running→completed)를 추적할 수 있다.

### AC-BT-02: 지표 산출
- **Given** 완료된 백테스트 job이 있을 때
- **When** `GET /backtest/results/{job_id}`를 호출하면
- **Then** 누적 수익률(vs KOSPI), 승률, 평균 수익률, Max Drawdown, Sharpe Ratio(국고채 3년물 무위험 기준)와 일별 수익률 시계열이 반환되고, 결과에 "시세 기반 단순화(뉴스 감성 균등 배분)" 사실이 명시된다.

### AC-BT-03: 결측·오류 처리
- **Given** 특정 영업일 시세가 결측인 기간이 주어졌을 때
- **When** 백테스트가 실행되면
- **Then** 해당 일자는 스킵·기록되고 작업은 계속되며, 치명적 오류 발생 시 상태가 `failed`로 표시되고 오류 사유가 기록된다.

### AC-BT-04: 이력 조회
- **Given** 과거 백테스트 실행 기록이 있을 때
- **When** `GET /backtest/history`를 호출하면
- **Then** 실행 목록(상태·기간·생성/완료 시각)이 반환된다.

---

## 5. 프론트엔드 (REQ-FE)

### AC-FE-01: 인증 흐름
- **Given** 로그인/회원가입 페이지가 있을 때
- **When** 사용자가 가입·로그인하면
- **Then** 토큰이 안전하게 보관되고 인증 상태 UI로 전환된다.

### AC-FE-02: 포트폴리오 관리·요약
- **Given** 인증 사용자가 보유 종목을 가진 상태에서
- **When** 포트폴리오 페이지와 대시보드를 열면
- **Then** 포트폴리오 페이지에 종목 추가/삭제/수량 변경과 종목별·전체 수익률이 표시되고, 대시보드에 "내 포트폴리오 요약" 위젯이 나타난다.

### AC-FE-03: 백테스팅 시각화
- **Given** 완료된 백테스트 결과가 있을 때
- **When** 백테스팅 페이지를 열면
- **Then** 누적 수익률 vs KOSPI 라인 차트(Recharts)와 핵심 지표 카드(승률, Sharpe, Max Drawdown)가 표시되고, 면책 고지가 유지된다.

---

## 6. 엣지 케이스

- 만료 직전 access token으로 호출 시 만료 경계 처리(만료 후 401).
- 동일 종목을 동일 포트폴리오에 중복 추가 시 `(portfolio_id, krx_code)` UNIQUE 위반 → 422 또는 기존 보유 갱신 안내.
- 빈 포트폴리오에서 `GET /portfolio/performance` 호출 시 빈 목록 + 편입 제안만 정상 반환.
- 텔레그램 자동 발송 시 활성 구독자가 0명이면 발송 없이 정상 종료(오류 아님).
- 백테스트 기간이 미래거나 start_date > end_date이면 422로 거부.
- 백테스트 동시 실행 요청이 들어오면 동시 실행 1건 제한 정책에 따라 대기/거부 처리.
- 사용자 비활성(is_active=false) 상태에서 인증 토큰 사용 시 401.
- `run_daily_pipeline`이 실패한 날에는 텔레그램 자동 발송을 트리거하지 않는다.

---

## 7. Definition of Done

- [ ] REQ-AUTH / REQ-TG / REQ-PORT / REQ-BT / REQ-FE / REQ-NFR 전 요구사항 구현.
- [ ] 신규 6개 테이블 Alembic 마이그레이션 작성·적용(`users`, `telegram_subscriptions`, `portfolios`, `portfolio_holdings`, `backtest_runs`, `backtest_daily_results`).
- [ ] 신규 API(인증 4, 포트폴리오 5, 백테스트 4) + 텔레그램 명령어 5종 + 자동 발송 후크 동작.
- [ ] 위 모든 인수 기준(AC-*)과 엣지 케이스를 검증하는 자동화 테스트 통과, 코드 커버리지 85% 이상.
- [ ] 비밀번호·토큰 원문이 로그·응답·DB 평문에 노출되지 않음(REQ-AUTH-002, REQ-NFR-004) 검증.
- [ ] SPEC-STOCK-001 기존 API·테이블·테스트가 변경 없이 그대로 통과(하위 호환, REQ-NFR-005).
- [ ] 포트폴리오·백테스팅 화면에 투자 책임 면책 고지 표시(REQ-FE-005).
- [ ] 백테스트가 비동기로 실행되어 API/웹 요청을 블로킹하지 않음(REQ-NFR-003) 검증.
- [ ] 신규 환경 변수(`TELEGRAM_BOT_TOKEN`, `JWT_SECRET_KEY` 등) `.env.example` 추가, 시크릿 버전 관리 제외.
- [ ] 운영 환경 HTTPS 적용 확인(REQ-NFR-001).
- [ ] 제외 항목(자동 매매·이메일·소셜 로그인·해외 자산·뉴스 기반 백테스트·실거래 추적)이 구현되지 않음을 확인.
- [ ] README / CHANGELOG / API 문서에 Phase 3 기능 반영.
