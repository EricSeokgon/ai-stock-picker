---
id: SPEC-STOCK-004
version: 0.1.0
status: draft
created: 2026-06-09
updated: 2026-06-09
author: ircp
priority: high
issue_number: null
---

# SPEC-STOCK-004: 한국 주식 & ETF 추천 시스템 — Phase 5 (알림 시스템 고도화)

## HISTORY

- 2026-06-09 (v0.1.0): 최초 작성. SPEC-STOCK-001(MVP)·002(개인화)·003(실시간) 완료 위에 알림 시스템을 고도화한다. 2대 기능 — (A) 관심 목록 가격 알림(목표가 도달 시 텔레그램 통지), (B) 이메일 알림(SMTP 기반 가격 알림 및 주간 추천 요약) — 을 단일 SPEC으로 정의. SPEC-STOCK-003 Exclusions에서 연기된 "관심 목록 가격 알림" 및 CHANGELOG Planned의 "이메일 알림"을 구현한다.

---

## 1. 시스템 개요

### 1.1 목적

SPEC-STOCK-001~003으로 추천·개인화·실시간 시세 축을 완성한 위에, **사용자가 화면을 직접 보지 않아도 중요한 시점에 도달 정보를 받는** 알림 레이어를 더한다. Phase 5는 다음을 추가한다.

1. **관심 목록 가격 알림(Watchlist Price Alerts)**: 관심 종목에 목표가·방향(이상/이하)을 설정하면, 백그라운드 작업이 5분 주기로 현재가를 점검하여 조건 충족 시 텔레그램으로 통지한다.
2. **이메일 알림(Email Notifications)**: SMTP 기반으로 (1) 가격 알림 도달 메일, (2) 매주 월요일 오전 7시 주간 추천 요약 메일을 발송한다.

### 1.2 타겟 사용자

| 사용자 그룹 | 특성 | Phase 5에서 추가되는 핵심 니즈 |
|------------|------|------------------------------|
| 액티브 트레이더 | 특정 가격대 진입/이탈 시점을 놓치고 싶지 않음 | 목표가 도달 시 즉시 텔레그램 알림 |
| 개인 투자자 (입문~중급) | 상시 앱을 보지 않음 | 매주 추천 요약을 이메일로 받아 가볍게 확인 |
| 텔레그램 미사용자 | 텔레그램 봇 연동을 원치 않음 | 이메일로 가격 도달·주간 요약 수신 |

### 1.3 핵심 가치 제안

- **능동적 통지**: pull/실시간 화면 한계를 보완하여, 사용자가 정한 조건이 충족될 때 시스템이 먼저 알린다.
- **다채널**: 텔레그램(SPEC-STOCK-002 자산 재사용)과 이메일(신규 SMTP)을 함께 제공한다.
- **외부 의존 최소화**: 이메일은 외부 SaaS 없이 Python 표준 라이브러리(`smtplib`+`email`)로 구현한다.
- **안전한 확장**: 모든 알림은 **정보 제공**에 한정하며, 자동 매매/주문은 영구 제외를 유지한다.

### 1.4 기존 시스템과의 관계 (SPEC-STOCK-001/002/003 재정의 금지)

다음은 이미 구현 완료된 자산이며 **본 SPEC에서 재정의하지 않고 재사용**한다.

- 백엔드: FastAPI + PostgreSQL + Redis, 프론트엔드: React 18 + TypeScript + Vite + Recharts + React Router
- 인증: SPEC-STOCK-002의 JWT 인증(`users` 테이블, `get_current_user` 의존성) — Phase A/B 모두 의존
- 텔레그램: SPEC-STOCK-002의 `telegram/notifier.py`(`_send_message_sync(chat_id, message)`), `telegram_subscriptions` 테이블 — 가격 알림 전송에 재사용
- 관심 목록: SPEC-STOCK-003의 `watchlist_items` 테이블(마이그레이션 0006) — 가격 알림 대상 종목 기준
- 시세 조회: SPEC-STOCK-003의 `realtime/price_feed.py`(`get_current_price(krx_code)`) — 알림 조건 평가에 재사용
- 스케줄러: SPEC-STOCK-001/002의 `scheduler/jobs.py`(`AsyncIOScheduler`, `setup_scheduler()`) — 신규 알림 작업 등록처
- 추천 API/데이터: `recommendations`(주간 요약 메일 입력)

---

## 2. 핵심 기능 요구사항 (EARS)

표기 규칙: **WHEN**(이벤트 구동), **WHILE**(상태 구동), **WHERE**(선택적 기능), **IF...THEN**(원치 않는 동작), **SHALL**(보편 요구).

### 2.1 관심 목록 가격 알림 (REQ-WALERT) — Priority High

- **REQ-WALERT-001 (Event)**: **WHEN** 인증된 사용자가 `POST /watchlist/alerts`로 `{krx_code, target_price, direction}`(direction ∈ {above, below})을 제출하면, the 시스템 **SHALL** 해당 목표가 알림을 `watchlist_alerts`에 `is_active=true`로 저장하고 생성된 알림을 반환한다.
- **REQ-WALERT-002 (Event)**: **WHEN** 인증된 사용자가 `GET /watchlist/alerts`를 호출하면, the 시스템 **SHALL** 해당 사용자의 알림 목록(`id, krx_code, target_price, direction, is_active, triggered_at`)을 반환한다.
- **REQ-WALERT-003 (Event)**: **WHEN** 인증된 사용자가 `DELETE /watchlist/alerts/{id}`를 호출하면, the 시스템 **SHALL** 해당 알림을 삭제한다.
- **REQ-WALERT-004 (State)**: **WHILE** 백그라운드 가격 점검 작업이 약 5분 주기로 실행되는 동안, the 시스템 **SHALL** 모든 `is_active=true` 알림에 대해 `get_current_price(krx_code)`로 현재가를 조회하여 조건(direction=above면 현재가≥목표가, below면 현재가≤목표가)을 평가한다.
- **REQ-WALERT-005 (Event)**: **WHEN** 활성 알림의 조건이 충족되면, the 시스템 **SHALL** 사용자의 텔레그램 구독으로 도달 메시지를 1회 전송하고, 해당 알림을 `is_active=false`로 표시하며 `triggered_at`에 도달 시각을 기록한다.
- **REQ-WALERT-006 (Ubiquitous)**: the 시스템 **SHALL** 가격 도달 텔레그램 메시지에 종목명·목표가·방향·현재가를 한국어로 포함한다(예: "관심 종목 {name}이(가) 목표가 {price}에 도달했습니다.").
- **REQ-WALERT-007 (State)**: **WHILE** 사용자가 인증되지 않은 상태에서 알림 엔드포인트에 접근하면, the 시스템 **SHALL** 401을 반환하고 어떤 알림 데이터도 노출·변경하지 않는다.
- **REQ-WALERT-008 (Unwanted)**: **IF** 다른 사용자의 알림에 대한 조회·삭제, 또는 존재하지 않는 알림 삭제가 시도되면, **THEN** the 시스템 **SHALL** 적절한 상태 코드(403/404)로 거부한다.
- **REQ-WALERT-009 (Unwanted)**: **IF** 특정 알림의 시세 조회가 실패하면, **THEN** the 시스템 **SHALL** 해당 알림을 스킵하고 오류를 로그한 뒤 다음 주기에 재평가하며, 다른 알림 처리는 중단하지 않는다.
- **REQ-WALERT-010 (Unwanted)**: **IF** 사용자가 텔레그램 구독을 하지 않은 상태에서 알림 조건이 충족되면, **THEN** the 시스템 **SHALL** 텔레그램 전송을 건너뛰되 알림을 triggered 상태로 표시하고(이메일 구독 시 REQ-EMAIL-004로 처리), 오류로 처리하지 않는다.

### 2.2 이메일 알림 (REQ-EMAIL) — Priority Medium

- **REQ-EMAIL-001 (Event)**: **WHEN** 인증된 사용자가 `POST /notifications/email`로 `{email}`을 제출하면, the 시스템 **SHALL** 해당 이메일을 `email_subscriptions`에 `is_active=true`로 저장(또는 재활성화)하고 구독 상태를 반환한다.
- **REQ-EMAIL-002 (Event)**: **WHEN** 인증된 사용자가 `DELETE /notifications/email`을 호출하면, the 시스템 **SHALL** 해당 사용자의 이메일 구독을 `is_active=false`로 변경(구독 해지)한다.
- **REQ-EMAIL-003 (Ubiquitous)**: the 시스템 **SHALL** 이메일 발송에 외부 이메일 서비스 의존 없이 Python 표준 `smtplib`+`email`을 사용하며, 접속 정보(`SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM`)를 환경 변수로 읽는다.
- **REQ-EMAIL-004 (Event)**: **WHEN** 관심 목록 가격 알림이 도달(REQ-WALERT-005)하고 해당 사용자가 활성 이메일 구독을 보유하면, the 시스템 **SHALL** "가격 알림 도달" 본문(plain text, 한국어)을 구독 이메일로 발송한다.
- **REQ-EMAIL-005 (State)**: **WHILE** 매주 월요일 오전 7시(Asia/Seoul) 주간 요약 작업이 실행되는 동안, the 시스템 **SHALL** 모든 활성 이메일 구독자에게 상위 5개 추천 종목을 담은 "주간 추천 요약" 본문(plain text, 한국어)을 발송한다.
- **REQ-EMAIL-006 (Ubiquitous)**: the 시스템 **SHALL** 모든 알림 메일 본문에 "본 메일은 투자 권유가 아닌 정보 제공 목적이며, 수신을 원치 않으면 구독을 해지할 수 있습니다" 취지의 면책·해지 안내를 포함한다.
- **REQ-EMAIL-007 (Unwanted)**: **IF** SMTP 발송이 실패하면, **THEN** the 시스템 **SHALL** 해당 수신자 발송을 스킵하고 오류를 로그한 뒤 다른 수신자 발송 및 알림 처리(triggered 상태 기록 등)를 계속한다.
- **REQ-EMAIL-008 (Unwanted)**: **IF** 형식이 유효하지 않은 이메일 주소로 구독이 시도되면, **THEN** the 시스템 **SHALL** 422로 거부하고 구독을 저장하지 않는다.
- **REQ-EMAIL-009 (State)**: **WHILE** 사용자가 인증되지 않은 상태에서 이메일 구독 엔드포인트에 접근하면, the 시스템 **SHALL** 401을 반환하고 구독을 변경하지 않는다.

### 2.3 프론트엔드 (REQ-FE)

- **REQ-FE-001 (Ubiquitous)**: the 시스템 **SHALL** 관심 목록 페이지(SPEC-STOCK-003 `Watchlist.tsx`)에서 각 종목에 목표가 알림을 추가하는 UI(목표가 입력 + 이상/이하 선택)를 제공한다.
- **REQ-FE-002 (Ubiquitous)**: the 시스템 **SHALL** 관심 목록 페이지에서 사용자의 활성 가격 알림을 목록으로 표시하고, 각 알림에 삭제 기능을 제공한다.
- **REQ-FE-003 (Ubiquitous)**: the 시스템 **SHALL** 신규 설정 페이지 `/settings`(알림 설정)를 추가하여 이메일 구독 토글(구독/해지)과 현재 구독 상태를 표시한다.
- **REQ-FE-004 (Ubiquitous)**: the 시스템 **SHALL** `/settings` 라우트를 React Router에 등록하고 인증된 사용자만 접근 가능하도록 처리한다.
- **REQ-FE-005 (Unwanted)**: **IF** 알림 생성·삭제 또는 이메일 구독 요청이 실패하면, **THEN** the 시스템 **SHALL** 사용자에게 오류 메시지를 표시하고 직전 상태를 복원(UI 롤백)한다.

### 2.4 비기능 요구사항 (REQ-NFR)

- **REQ-NFR-001 (Ubiquitous)**: the 시스템 **SHALL** 가격 알림 점검·이메일 발송·주간 요약 각 단계의 결과·실패를 구조화 로그로 남기되, SMTP 비밀번호·JWT·텔레그램 토큰 등 자격 증명 원문은 로그에 포함하지 않는다.
- **REQ-NFR-002 (Ubiquitous)**: the 시스템 **SHALL** 모든 시크릿(SMTP 자격 증명, 텔레그램 토큰)을 환경 변수로 관리하고 버전 관리에 포함하지 않는다.
- **REQ-NFR-003 (Ubiquitous)**: the 시스템 **SHALL** 가격 알림 점검 작업이 단일 실패 알림으로 전체 주기를 중단하지 않도록 알림 단위로 예외를 격리한다.
- **REQ-NFR-004 (Ubiquitous)**: the 시스템 **SHALL** Phase 5 기능 추가 시 SPEC-STOCK-001/002/003의 기존 API·테이블·스케줄러 작업·동작을 변경 없이 유지한다(하위 호환).
- **REQ-NFR-005 (Ubiquitous)**: the 시스템 **SHALL** 알림 점검 주기(약 5분)와 주간 요약 시점(월요일 07:00 KST)을 기존 `scheduler/jobs.py`의 `AsyncIOScheduler`에 신규 작업으로 추가하며, 기존 작업 트리거를 변경하지 않는다.

---

## 3. Exclusions (What NOT to Build)

본 SPEC 범위에서 명시적으로 **제외**되는 항목:

- **자동 매매/주문 실행**: 증권사 API를 통한 실제 매수/매도 주문 기능은 **영구 제외**한다 (규제·책임 리스크).
- **푸시 알림(웹/모바일 Push)**: 브라우저/모바일 푸시 알림은 제외하며, 채널은 텔레그램과 이메일로 한정한다.
- **SMS 알림**: 문자(SMS) 채널은 제외한다.
- **소셜 로그인(OAuth)**: 이메일 인증/소셜 로그인은 본 SPEC 범위 밖이며, 이메일은 알림 수신 주소 등록 용도로만 사용한다.
- **외부 이메일 SaaS 연동**: SendGrid·SES·Mailgun 등 외부 이메일 서비스는 제외하며, 표준 `smtplib`만 사용한다.
- **HTML 이메일 템플릿/리치 콘텐츠**: 본 SPEC의 메일은 plain text(한국어)로 한정하며, HTML 디자인 템플릿은 제외한다.
- **알림 발송 이력 영구 보관/감사 로그 테이블**: triggered_at 기록 외 별도 발송 이력 테이블·시계열 추적은 제외한다.
- **해외 주식/암호화폐**: 한국 주식(KRX)과 국내 상장 ETF만 대상이다.

---

## 4. 가정 및 제약 (Assumptions & Constraints)

ASSUMPTIONS I'M MAKING:
1. SPEC-STOCK-002의 텔레그램 구독(`telegram_subscriptions` + `_send_message_sync(chat_id, message)`)이 안정적으로 운영 중이며, 사용자별 chat_id 매핑을 통해 가격 알림을 전송할 수 있다고 가정한다.
2. SPEC-STOCK-003의 `get_current_price(krx_code)`가 5분 주기 점검에 충분한 빈도·정확도로 KRX 현재가를 제공한다고 가정한다(장 마감 시 종가 유지).
3. SPEC-STOCK-001/002의 `scheduler/jobs.py` `AsyncIOScheduler`에 신규 작업(IntervalTrigger 5분, CronTrigger 월 07:00 KST)을 추가할 수 있다고 가정한다.
4. 운영 환경에 유효한 SMTP 서버 접속 정보가 환경 변수로 제공된다고 가정하며, 미설정 시 이메일 발송은 비활성(스킵+로그)으로 안전 동작한다고 가정한다.
5. 가격 알림은 "1회성"이다 — 도달 시 `is_active=false`로 비활성화되며, 재알림을 원하면 사용자가 알림을 다시 생성한다고 가정한다.
6. 이메일 구독 주소는 사용자당 1건(활성)으로 관리하며, `users`의 로그인 식별과는 별개의 수신 주소로 가정한다.

제약:
- 본 시스템은 **투자 정보 제공 도구**이며 투자 권유·자문이 아니다. 모든 알림 메시지·메일에 면책 고지를 유지한다(REQ-WALERT-006 맥락, REQ-EMAIL-006).
- 신규 테이블은 `watchlist_alerts`(마이그레이션 0007), `email_subscriptions`(마이그레이션 0008) 2종만 추가하며, 기존 테이블은 변경하지 않는다.
- 신규 외부 패키지 추가는 최소화한다(이메일은 표준 라이브러리, 스케줄링은 기존 APScheduler 재사용).

---

## 5. 기술 접근 (Technical Approach)

### 5.1 데이터 모델 (신규 2종)

`watchlist_alerts` 테이블 (마이그레이션 0007):

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | Integer | PK, autoincrement | 식별자 |
| user_id | Integer | FK(users.id, CASCADE), NOT NULL | 소유 사용자 |
| krx_code | String(10) | NOT NULL | KRX 종목코드 |
| target_price | Numeric/Float | NOT NULL | 목표가 |
| direction | String(5) | NOT NULL, ∈ {above, below} | 도달 방향 |
| is_active | Boolean | NOT NULL, default true | 활성 여부 |
| triggered_at | TIMESTAMPTZ | NULL | 도달(트리거) 시각 |
| created_at | TIMESTAMPTZ | server_default now() | 생성 시각 |

`email_subscriptions` 테이블 (마이그레이션 0008):

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | Integer | PK, autoincrement | 식별자 |
| user_id | Integer | FK(users.id, CASCADE), NOT NULL | 소유 사용자 |
| email | String(255) | NOT NULL | 수신 이메일 |
| is_active | Boolean | NOT NULL, default true | 구독 활성 여부 |
| created_at | TIMESTAMPTZ | server_default now() | 생성 시각 |

제약: `email_subscriptions`는 `UNIQUE(user_id)`로 사용자당 1건 관리(재구독 시 upsert/재활성화). 기존 테이블(`users`, `watchlist_items`, `recommendations`, `telegram_subscriptions`)은 **재사용만** 하며 스키마를 변경하지 않는다.

### 5.2 API 계약 (신규)

| 메서드 | 경로 | 인증 | 요청 | 응답 |
|--------|------|------|------|------|
| POST | `/watchlist/alerts` | 필요 | `{krx_code, target_price, direction}` | 생성된 알림 |
| GET | `/watchlist/alerts` | 필요 | — | `[{id, krx_code, target_price, direction, is_active, triggered_at}]` |
| DELETE | `/watchlist/alerts/{id}` | 필요 | — | 204 / 상태 코드 |
| POST | `/notifications/email` | 필요 | `{email}` | 구독 상태 |
| DELETE | `/notifications/email` | 필요 | — | 구독 해지 상태 |

### 5.3 백엔드 구조 (신규/변경 모듈)

- `db/models.py`(변경): `WatchlistAlert`, `EmailSubscription` 모델 추가.
- `alembic/versions/0007_watchlist_alerts.py`(신규): `watchlist_alerts` 테이블.
- `alembic/versions/0008_email_subscriptions.py`(신규): `email_subscriptions` 테이블.
- `notifications/alert_service.py`(신규): 가격 알림 CRUD + 조건 평가 로직(REQ-WALERT-001~003, 004).
- `notifications/alert_router.py`(신규): `/watchlist/alerts` 라우터(REQ-WALERT-001~003, 007, 008).
- `notifications/email_service.py`(신규): SMTP 발송(`smtplib`+`email`), plain text 한국어 템플릿(가격 도달·주간 요약), 면책 문구(REQ-EMAIL-003~007).
- `notifications/email_router.py`(신규): `/notifications/email` 라우터(REQ-EMAIL-001/002/008/009).
- `scheduler/jobs.py`(변경): `check_price_alerts()`(IntervalTrigger 5분), `send_weekly_email_summary()`(CronTrigger 월 07:00 KST) 작업 추가 및 `setup_scheduler()` 등록(REQ-NFR-005).
- 재사용: `telegram/notifier.py`(`_send_message_sync`), `realtime/price_feed.py`(`get_current_price`), `auth`(`get_current_user`).

### 5.4 프론트엔드 구조 (신규/변경)

- `pages/Watchlist.tsx`(변경): 종목별 목표가 알림 추가 UI + 활성 알림 목록·삭제(REQ-FE-001/002).
- `pages/Settings.tsx`(신규): 이메일 구독 토글·상태 표시(REQ-FE-003).
- 라우팅(변경): `/settings` 라우트 등록, 인증 가드 적용(REQ-FE-004).
- API 클라이언트(변경): 알림 CRUD·이메일 구독 호출 추가, 실패 시 롤백 처리(REQ-FE-005).

### 5.5 의존성 (Dependencies)

- **Phase A (가격 알림)**: SPEC-STOCK-003 `watchlist_items`·`get_current_price`, SPEC-STOCK-002 텔레그램·JWT, 기존 APScheduler에 의존. 먼저 구현.
- **Phase B (이메일)**: SPEC-STOCK-002 JWT, 기존 APScheduler, `recommendations`(주간 요약 입력)에 의존. 가격 도달 메일은 Phase A의 트리거(REQ-WALERT-005)에 연결되므로 Phase A 이후 통합.

---

## 6. 수용 기준 요약 (Acceptance Summary)

### Phase A — 관심 목록 가격 알림
- 인증 사용자 알림 CRUD 동작, 미인증 401, 타사용자/미존재 알림 조작 거부(REQ-WALERT-001/002/003/007/008).
- 5분 주기 점검에서 above/below 조건 평가 정확, 충족 시 텔레그램 1회 전송 + `is_active=false` + `triggered_at` 기록(REQ-WALERT-004/005/006).
- 개별 시세 조회 실패 격리, 텔레그램 미구독 시 안전 스킵(REQ-WALERT-009/010).

### Phase B — 이메일 알림
- 이메일 구독/해지 동작, 유효성 검증(422), 미인증 401(REQ-EMAIL-001/002/008/009).
- `smtplib` 기반 가격 도달 메일·월요일 07:00 주간 요약 메일 발송, plain text 한국어 + 면책/해지 안내(REQ-EMAIL-003/004/005/006).
- SMTP 실패 시 수신자 단위 격리, 다른 발송·triggered 기록 계속(REQ-EMAIL-007).

---

## 7. 우선순위 요약

| 우선순위 | 기능 | 근거 |
|---------|------|------|
| High | REQ-WALERT (관심 목록 가격 알림) | SPEC-STOCK-003에서 연기된 핵심 기능, 텔레그램·시세·관심목록 자산 위에 즉시 구현 가능 |
| Medium | REQ-EMAIL (이메일 알림) | 신규 SMTP 채널, 가격 도달 메일은 Phase A 트리거에 의존 |
