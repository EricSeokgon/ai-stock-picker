---
id: SPEC-STOCK-002
version: 0.1.0
status: draft
created: 2026-06-01
updated: 2026-06-01
author: ircp
priority: high
issue_number: null
---

# SPEC-STOCK-002: 한국 주식 & ETF 추천 시스템 — Phase 3 (인증·알림·포트폴리오·백테스팅)

## HISTORY

- 2026-06-01 (v0.1.0): 최초 작성. SPEC-STOCK-001(MVP) 완료 위에 Phase 3 4대 기능(JWT 인증, 텔레그램 알림, 포트폴리오 시뮬레이터, 백테스팅 엔진)을 단일 SPEC으로 정의.

---

## 1. 시스템 개요

### 1.1 목적

SPEC-STOCK-001로 구축한 공개 추천 대시보드(뉴스 수집 → Claude 감성 분석 → 트렌드 집계 → 추천 엔진 → 웹 대시보드)를 **개인화·능동적 가치 전달·검증 가능성** 축으로 확장한다. Phase 3는 다음을 더한다.

1. **사용자 인증(JWT)**: 개인화 기능(포트폴리오, 구독)의 기반.
2. **텔레그램 알림**: 사용자가 대시보드를 열지 않아도 매일 추천을 받아보는 push 채널.
3. **포트폴리오 시뮬레이터**: 추천을 가상 보유로 연결하여 수익률을 추적.
4. **백테스팅 엔진**: 추천 알고리즘을 과거 시세에 재현하여 성과를 KOSPI 대비 정량 검증.

### 1.2 타겟 사용자

| 사용자 그룹 | 특성 | Phase 3에서 추가되는 핵심 니즈 |
|------------|------|------------------------------|
| 개인 투자자 (입문~중급) | 매일 대시보드 방문이 번거로움 | 텔레그램으로 매일 아침 Top 5 자동 수신, 관심 종목을 가상 포트폴리오로 추적 |
| 액티브 트레이더 | 즉각적인 조회와 성과 검증 중시 | 봇 명령어로 즉시 추천·섹터 조회, 백테스트로 전략 신뢰도 확인 |
| 검증 지향 사용자 | 추천 알고리즘의 실제 성과를 의심 | KOSPI 대비 초과 수익률·승률·Sharpe·Max Drawdown 등 정량 지표 제공 |

### 1.3 핵심 가치 제안

- **개인화**: 로그인 사용자별 가상 포트폴리오와 알림 구독을 분리 관리.
- **능동적 전달**: 일일 파이프라인 완료 시 텔레그램으로 추천을 자동 발송(pull → push 전환).
- **검증 가능성**: 백테스팅으로 "이 추천이 과거에 통했는가"를 벤치마크 대비 수치로 제시.
- **안전한 확장**: 자동 매매를 영구 제외하여 규제·책임 리스크를 차단하고, 정보 제공 도구의 정체성을 유지.

### 1.4 기존 시스템과의 관계 (SPEC-STOCK-001 재정의 금지)

다음은 SPEC-STOCK-001에서 이미 구현 완료된 자산이며 **본 SPEC에서 재정의하지 않고 재사용**한다.

- 백엔드: FastAPI + PostgreSQL + Redis, 프론트엔드: React + Recharts
- 기존 5개 테이블: `articles`, `analysis_results`, `stock_mentions`, `sector_trends`, `recommendations`
- 기존 API: `GET /recommendations`, `GET /news`, `GET /sectors/trends`, `GET /recommendations/{krx_code}`
- 기존 스케줄러: `scheduler/jobs.py`의 `run_daily_pipeline` (텔레그램 알림은 이 후크에 연동)
- 기존 시세 조회: FinanceDataReader (포트폴리오 현재가·백테스팅 시세에 재사용)

---

## 2. 핵심 기능 요구사항 (EARS)

표기 규칙: **WHEN**(이벤트 구동), **WHILE**(상태 구동), **WHERE**(선택적 기능), **IF...THEN**(원치 않는 동작), **SHALL**(보편 요구).

### 2.1 JWT 사용자 인증 (REQ-AUTH) — Priority High

- **REQ-AUTH-001 (Event)**: **WHEN** 사용자가 `POST /auth/register`로 username, email, password를 제출하면, the 시스템 **SHALL** 신규 계정을 생성하고 `users` 테이블에 저장한다.
- **REQ-AUTH-002 (Ubiquitous)**: the 시스템 **SHALL** 비밀번호를 bcrypt(cost factor 최소 12)로 해싱하여 저장하며, 평문 비밀번호는 어떤 저장소·로그에도 남기지 않는다.
- **REQ-AUTH-003 (Event)**: **WHEN** 사용자가 `POST /auth/login`으로 올바른 자격 증명을 제출하면, the 시스템 **SHALL** access token(만료 1시간)과 refresh token(만료 7일)을 발급한다.
- **REQ-AUTH-004 (Event)**: **WHEN** 사용자가 유효한 refresh token으로 `POST /auth/refresh`를 호출하면, the 시스템 **SHALL** 새 access token을 발급한다.
- **REQ-AUTH-005 (Event)**: **WHEN** 인증된 사용자가 `GET /auth/me`를 호출하면, the 시스템 **SHALL** 현재 사용자 정보(id, username, email, is_active)를 반환하되 비밀번호 해시는 제외한다.
- **REQ-AUTH-006 (Ubiquitous)**: the 시스템 **SHALL** 회원가입 시 비밀번호 최소 8자, RFC 5322 호환 이메일 형식, username·email 중복 불가를 검증한다.
- **REQ-AUTH-007 (Unwanted)**: **IF** 잘못된 자격 증명, 만료/위변조된 토큰, 또는 중복 username/email이 입력되면, **THEN** the 시스템 **SHALL** 적절한 HTTP 상태 코드(401/409/422)와 함께 명확한 오류 메시지를 반환하고 계정 생성·토큰 발급을 거부한다.
- **REQ-AUTH-008 (Ubiquitous)**: the 시스템 **SHALL** 인증이 필요한 모든 엔드포인트에서 access token의 서명·만료·활성 사용자 여부를 검증한다.

### 2.2 텔레그램 알림 시스템 (REQ-TG) — Priority High

- **REQ-TG-001 (Event)**: **WHEN** 사용자가 봇에 `/start`를 보내면, the 시스템 **SHALL** 봇 소개와 구독 방법 안내를 응답한다.
- **REQ-TG-002 (Event)**: **WHEN** 사용자가 `/subscribe`를 보내면, the 시스템 **SHALL** 해당 chat_id를 `telegram_subscriptions`에 활성 구독으로 등록한다.
- **REQ-TG-003 (Event)**: **WHEN** 사용자가 `/unsubscribe`를 보내면, the 시스템 **SHALL** 해당 chat_id의 구독을 비활성(is_active=false)으로 전환한다.
- **REQ-TG-004 (Event)**: **WHEN** 사용자가 `/today`를 보내면, the 시스템 **SHALL** 당일 Top 5 추천(rank, krx_code, 근거 요약)을 즉시 응답한다.
- **REQ-TG-005 (Event)**: **WHEN** 사용자가 `/sectors`를 보내면, the 시스템 **SHALL** 상위 3개 섹터 트렌드를 즉시 응답한다.
- **REQ-TG-006 (Event)**: **WHEN** 일일 파이프라인(`run_daily_pipeline`)이 정상 완료되면, the 시스템 **SHALL** 모든 활성 구독자에게 Top 5 추천 종목과 상위 3개 섹터 트렌드를 자동 발송한다.
- **REQ-TG-007 (Unwanted)**: **IF** 특정 구독자에게 발송이 실패(차단·삭제된 chat 등)하면, **THEN** the 시스템 **SHALL** 해당 발송만 스킵·로그하고 나머지 구독자 발송을 계속하며, 차단(403) 응답을 받은 chat_id는 구독을 비활성화한다.
- **REQ-TG-008 (Ubiquitous)**: the 시스템 **SHALL** `TELEGRAM_BOT_TOKEN`을 환경 변수로 관리하고 버전 관리에 포함하지 않는다.

### 2.3 포트폴리오 시뮬레이터 (REQ-PORT) — Priority Medium

- **REQ-PORT-001 (Event)**: **WHEN** 인증된 사용자가 `GET /portfolio`를 호출하면, the 시스템 **SHALL** 해당 사용자의 포트폴리오와 보유 종목 목록을 반환한다.
- **REQ-PORT-002 (Event)**: **WHEN** 인증된 사용자가 `POST /portfolio/holdings`로 krx_code, quantity, purchase_price를 제출하면, the 시스템 **SHALL** 해당 종목을 포트폴리오에 추가한다.
- **REQ-PORT-003 (Event)**: **WHEN** 인증된 사용자가 `PUT /portfolio/holdings/{krx_code}`로 수량을 변경하면, the 시스템 **SHALL** 해당 보유 종목의 수량을 갱신한다.
- **REQ-PORT-004 (Event)**: **WHEN** 인증된 사용자가 `DELETE /portfolio/holdings/{krx_code}`를 호출하면, the 시스템 **SHALL** 해당 보유 종목을 제거한다.
- **REQ-PORT-005 (Event)**: **WHEN** 인증된 사용자가 `GET /portfolio/performance`를 호출하면, the 시스템 **SHALL** FinanceDataReader 현재가 기준으로 종목별 및 전체 포트폴리오의 평가금액과 수익률을 계산하여 반환한다.
- **REQ-PORT-006 (Ubiquitous)**: the 시스템 **SHALL** 포트폴리오 성과 조회 시 현재 Top 10 추천 중 미보유 종목을 "편입 제안" 목록으로 함께 제시한다.
- **REQ-PORT-007 (State)**: **WHILE** 사용자가 인증되지 않은 상태에서 포트폴리오 엔드포인트에 접근하면, the 시스템 **SHALL** 401을 반환하고 어떤 포트폴리오 데이터도 노출하지 않는다.
- **REQ-PORT-008 (Unwanted)**: **IF** 존재하지 않는 krx_code, 음수/0 수량, 또는 다른 사용자의 포트폴리오에 대한 조작이 시도되면, **THEN** the 시스템 **SHALL** 해당 요청을 거부(404/422/403)한다.
- **REQ-PORT-009 (Unwanted)**: **IF** 현재가 조회가 실패하면, **THEN** the 시스템 **SHALL** 해당 종목 평가금액을 "조회 불가"로 표시하고 나머지 종목 계산을 계속한다.

### 2.4 백테스팅 엔진 (REQ-BT) — Priority Low

- **REQ-BT-001 (Event)**: **WHEN** 사용자가 `POST /backtest/run`으로 기간(기본 2025-01-01 ~ 2026-06-01)을 제출하면, the 시스템 **SHALL** 비동기 백테스트 작업을 생성하고 즉시 job_id를 반환한다.
- **REQ-BT-002 (Ubiquitous)**: the 시스템 **SHALL** 과거 영업일별로 당시 시세 데이터(가격 모멘텀 + 거래량 이상 신호)로 추천 점수를 재계산하고, 다음 영업일 수익률로 추천 성과를 측정한다.
- **REQ-BT-003 (Ubiquitous)**: the 시스템 **SHALL** 과거 뉴스·감성 데이터가 없으므로 감성·볼륨 가중치를 균등 배분한 단순화 알고리즘을 사용하며, 이 단순화 사실을 결과에 명시한다.
- **REQ-BT-004 (Ubiquitous)**: the 시스템 **SHALL** 누적 수익률(vs KOSPI 벤치마크), 승률(추천 종목 중 익일 플러스 비율), 평균 수익률(Top 10 익일 평균), 최대 낙폭(Max Drawdown), Sharpe Ratio(무위험 수익률 = 한국 국고채 3년물)를 산출한다.
- **REQ-BT-005 (Event)**: **WHEN** 사용자가 `GET /backtest/status/{job_id}`를 호출하면, the 시스템 **SHALL** 작업 상태(pending/running/completed/failed)를 반환한다.
- **REQ-BT-006 (Event)**: **WHEN** 백테스트가 완료된 상태에서 `GET /backtest/results/{job_id}`를 호출하면, the 시스템 **SHALL** 핵심 지표와 일별 수익률 시계열을 반환한다.
- **REQ-BT-007 (Event)**: **WHEN** 사용자가 `GET /backtest/history`를 호출하면, the 시스템 **SHALL** 과거 백테스트 실행 목록을 반환한다.
- **REQ-BT-008 (Unwanted)**: **IF** 특정 영업일 시세 데이터가 결측이거나 백테스트 실행 중 오류가 발생하면, **THEN** the 시스템 **SHALL** 해당 일자를 스킵하고 작업을 계속하되 결측을 기록하며, 치명적 오류 시 작업 상태를 `failed`로 표시하고 오류 사유를 기록한다.

### 2.5 프론트엔드 (REQ-FE)

- **REQ-FE-001 (Event)**: **WHEN** 사용자가 로그인/회원가입 페이지에서 자격 증명을 제출하면, the 시스템 **SHALL** 인증을 수행하고 토큰을 클라이언트에 안전하게 보관한 뒤 인증 상태 UI로 전환한다.
- **REQ-FE-002 (Ubiquitous)**: the 시스템 **SHALL** 포트폴리오 관리 페이지에서 종목 추가/삭제/수량 변경과 종목별·전체 수익률을 표시한다.
- **REQ-FE-003 (Ubiquitous)**: the 시스템 **SHALL** 대시보드에 "내 포트폴리오 요약" 위젯(인증 사용자 한정)을 추가한다.
- **REQ-FE-004 (Ubiquitous)**: the 시스템 **SHALL** 백테스팅 페이지에서 기간 선택, 누적 수익률 vs KOSPI 라인 차트(Recharts), 핵심 지표 카드(승률, Sharpe, Max Drawdown)를 표시한다.
- **REQ-FE-005 (Ubiquitous)**: the 시스템 **SHALL** 포트폴리오·백테스팅 화면을 포함한 모든 추천 관련 화면에 투자 책임 면책 고지를 유지한다.

### 2.6 비기능 요구사항 (REQ-NFR)

- **REQ-NFR-001 (Ubiquitous)**: the 시스템 **SHALL** 운영 환경에서 모든 인증·개인화 트래픽을 HTTPS로 처리한다.
- **REQ-NFR-002 (Ubiquitous)**: the 시스템 **SHALL** `TELEGRAM_BOT_TOKEN`, JWT 서명 시크릿 등 모든 신규 시크릿을 환경 변수로 관리하고 버전 관리에 포함하지 않는다.
- **REQ-NFR-003 (Ubiquitous)**: the 시스템 **SHALL** 백테스트를 비동기로 실행하여 장시간 연산이 API 응답·웹 요청을 블로킹하지 않도록 한다.
- **REQ-NFR-004 (Ubiquitous)**: the 시스템 **SHALL** 인증, 알림 발송, 포트폴리오 조작, 백테스트 실행 각 단계의 결과와 실패를 구조화 로그로 남기되, 비밀번호·토큰 원문은 로그에 포함하지 않는다.
- **REQ-NFR-005 (Ubiquitous)**: the 시스템 **SHALL** Phase 3 기능 추가 시 SPEC-STOCK-001의 기존 API·테이블·동작을 변경 없이 유지한다(하위 호환).

---

## 3. Exclusions (What NOT to Build)

본 SPEC 범위에서 명시적으로 **제외**되는 항목:

- **자동 매매/주문 실행**: 증권사 API를 통한 실제 매수/매도 주문 기능은 **영구 제외**한다 (규제·책임 리스크).
- **이메일 알림**: 텔레그램으로 대체하며, 이메일 알림은 Phase 4로 연기한다.
- **소셜 로그인(OAuth)**: Google/Kakao 등 소셜 로그인은 Phase 4로 연기하며, 본 SPEC은 자체 JWT 인증만 다룬다.
- **해외 주식/암호화폐**: 한국 주식(KRX)과 국내 상장 ETF만 대상이며 해외 자산은 제외한다.
- **과거 뉴스 데이터 기반 백테스팅**: 과거 뉴스·감성 데이터가 없으므로 백테스트는 시세(가격 모멘텀 + 거래량 이상) 기반으로 단순화하며, 뉴스 감성 재현은 제외한다.
- **실제 포트폴리오 성과 추적**: 증권사 계좌 연동이 없으므로 가상 포트폴리오만 제공하며, 실제 체결·수수료·세금 반영은 제외한다.
- **결제/구독 과금**: 유료 플랜·결제는 본 SPEC 범위 밖이다.

---

## 4. 가정 및 제약 (Assumptions & Constraints)

ASSUMPTIONS I'M MAKING:
1. SPEC-STOCK-001의 백엔드/DB/스케줄러 구조가 안정적으로 운영 중이며, `run_daily_pipeline`에 후크를 추가해도 기존 흐름이 깨지지 않는다고 가정한다.
2. 텔레그램 봇 토큰을 발급받을 수 있고, 운영 환경에서 텔레그램 API에 안정적으로 접근 가능하다고 가정한다.
3. FinanceDataReader가 2025-01-01 ~ 2026-06-01 기간의 KRX 일별 시세와 KOSPI 지수를 백테스트에 충분한 정확도로 제공한다고 가정한다.
4. Sharpe Ratio의 무위험 수익률 기준은 한국 국고채 3년물 수익률(백테스트 시점 기준 고정 또는 일별 적용)을 사용한다.
5. MVP와 동일하게 단일 서버(또는 단일 컨테이너 세트) 운영을 가정하며, 대규모 동시 사용자·고가용성은 가정하지 않는다.

제약:
- 본 시스템은 **투자 정보 제공 도구**이며 투자 권유·자문이 아니다. 포트폴리오·백테스팅 화면을 포함한 모든 화면에 면책 고지를 유지한다 (REQ-FE-005).
- 신규 기술 스택 추가: `python-telegram-bot`(봇), `python-jose`(JWT), `passlib[bcrypt]`(해싱). 기존 스택(FastAPI/PostgreSQL/Redis/React/Recharts/FinanceDataReader/APScheduler)은 변경하지 않는다.
- 백테스트 기간 기본값은 1년(2025-01-01 ~ 2026-06-01)으로 고정하되, 요청 시 부분 기간 지정을 허용한다.

---

## 5. 우선순위 요약

| 우선순위 | 기능 | 근거 |
|---------|------|------|
| High | REQ-AUTH (JWT 인증) | 포트폴리오·알림 개인화의 기반, 가장 먼저 구현 |
| High | REQ-TG (텔레그램 알림) | 인증과 독립적, 빠른 가치 제공 |
| Medium | REQ-PORT (포트폴리오 시뮬레이터) | 인증에 의존 |
| Low | REQ-BT (백테스팅 엔진) | 가장 복잡, 독립적, 후순위 |
