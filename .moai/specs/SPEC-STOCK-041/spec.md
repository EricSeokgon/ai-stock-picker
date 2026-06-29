---
id: SPEC-STOCK-041
title: 포트폴리오 목표 관리
status: draft
version: 0.3.0
created_at: 2026-06-29
updated_at: 2026-06-29
author: ircp
priority: medium
issue_number: null
branch: feature/SPEC-STOCK-036
labels: [portfolio, goal, notification, backend, frontend]
---

# SPEC-STOCK-041 — 포트폴리오 목표 관리 (Portfolio Goal Management)

## HISTORY

| Version | Date | Author | Note |
|---------|------|--------|------|
| 0.1.0 | 2026-06-29 | ircp | 최초 초안 — 목표 CRUD + 달성률 계산 + 목표 달성 알림 트리거 + 프론트 목표 패널. EARS REQ 7개·DB 마이그 0025·제외 항목 정의 |
| 0.2.0 | 2026-06-29 | ircp | plan-auditor v1 지적사항 반영 — C-1, C-2, Major 5건 해소 |
| 0.3.0 | 2026-06-29 | ircp | plan-auditor v2 minor 수정 — N-1 EARS 패턴·N-2 T-013 분리·MN-4 AC-9 강화·MN-6 T-010 mock 명시 |

---

## 1. 개요 (Overview)

사용자가 포트폴리오별로 투자 목표(목표 금액·목표 수익률·기한)를 설정하고 달성률을 추적할 수 있게 한다.
목표가 달성(또는 달성 임박)되면 기존 알림 인프라(텔레그램·이메일, SPEC-031/036)를 재사용해 알림을 발송한다.

- 목표는 **정보 제공 + 알림** 용도이며, 자동 매매·자동 리밸런싱 로직은 포함하지 않는다.
- 현재 평가액·현재 수익률은 기존 성과 계산 로직(`portfolio/service.py`의 `calculate_performance()`)을 재사용한다.
- 목표 달성 알림은 SPEC-036 `portfolio_alerts.py`가 사용하는 알림 인프라(텔레그램 `_send_message_sync`, 이메일 `send_general_alert_email`, `notifications` 테이블 멱등 적재)를 그대로 재사용하며, 신규 알림 채널을 추가하지 않는다.

### 1.1 동기 (Why)

SPEC-026(AI 최적화)·SPEC-036(포트폴리오 임계 알림)으로 포트폴리오의 "현재 상태"는 충분히 관측 가능해졌으나, 사용자가 자신의 **목표 대비 진척도**를 정량적으로 추적할 수단이 없다. 본 SPEC은 목표라는 기준점을 도입해 "지금 얼마나 왔는가"를 달성률(%)로 제공하고, 목표 도달 시점을 알림으로 통지한다.

---

## 2. 범위 (Scope)

### 2.1 In-Scope

- 포트폴리오 목표 CRUD (생성·조회·소프트 삭제)
- 달성률(achievement_rate, %) 계산 및 잔여일(days_remaining) 산출
- 목표 달성(달성률 100% 이상) 시 알림 트리거 (텔레그램 + 이메일, 1회 발송 멱등)
- 프론트엔드 목표 패널(`PortfolioGoalPanel`) — 목표 입력 폼 + 진행률 바 + 잔여일 배지
- 신규 DB 테이블 `portfolio_goals` (마이그레이션 0025)

### 2.2 Out-of-Scope (제외)

> [HARD] 본 SPEC은 아래 항목을 명시적으로 제외한다.

- **자동 매매·자동 주문 실행** (규제·책임 리스크로 프로젝트 영구 제외)
- **자동 리밸런싱** — 목표는 정보 제공·알림 전용
- **포트폴리오당 다중 목표** — MVP는 포트폴리오당 활성 목표 1개만 (앱 레벨 강제)
- **신규 알림 채널** (웹푸시·SMS·카카오톡 등) — 기존 텔레그램·이메일만 재사용
- **목표 수정(PUT/PATCH)** — MVP는 생성·삭제만 (수정은 삭제 후 재생성으로 대체)
- **달성 임박(예: 90%) 사전 알림** — MVP는 100% 도달 알림만 (사전 알림은 후속 SPEC)
- **신규 수치 계산 라이브러리(scipy 등) 도입** — 기존 산술 연산만 사용
- **목표 달성 이력/시계열 저장** — 현재 활성 목표 상태만 관리

---

## 3. 요구사항 (Requirements — EARS)

> REQ 번호는 논리적 실행 순서(생성 → 조회 → 삭제 → 소유권 → 목표없음 GET → 달성률 계산 → 스케줄러 알림)에 맞춰 부여한다.

### 3.1 목표 생성 (REQ-GOAL-001)

- **REQ-GOAL-001**: WHEN 사용자가 `POST /portfolios/{portfolio_id}/goals` 를 호출하면, THEN 시스템은 `target_amount`(선택), `target_return_rate`(선택, %), `deadline`(선택, date) 으로 목표를 생성하고 **201 GoalResponse** 를 반환해야 한다(SHALL). **`target_amount` 또는 `target_return_rate` 중 적어도 1개는 반드시 제공되어야 한다.** `deadline` 단독 입력(금액·수익률 모두 None)은 유효하지 않으며 **422 Unprocessable Entity** 를 반환한다.
- **REQ-GOAL-001a**: IF 동일 포트폴리오에 이미 `is_active=True` 목표가 존재하면, THEN 시스템은 `POST /portfolios/{portfolio_id}/goals` 에서 **409 Conflict** 를 반환해야 한다(SHALL). 사용자는 기존 목표를 먼저 `DELETE` 한 뒤 신규 목표를 생성해야 한다(중복 목표 방지, 활성 목표 1개 제약).

### 3.2 목표 조회 (REQ-GOAL-002)

- **REQ-GOAL-002**: WHEN 사용자가 `GET /portfolios/{portfolio_id}/goals` 를 호출하면, THEN 시스템은 **단일** 활성 목표를 `current_value`, `current_return_rate`, `achievement_rate`(%), `days_remaining` 와 함께 **200 GoalWithProgressResponse(단일 객체)** 로 반환해야 한다(SHALL). 응답은 배열이 아니라 **단일 객체**이다.
  - `days_remaining`: `deadline` 미설정 시 `null`. **`deadline` 이 과거(오늘 이전)이면 음수가 아니라 `0` 을 반환한다**(기한 초과 목표도 진행률 추적 가능).

### 3.3 목표 삭제 (REQ-GOAL-003)

- **REQ-GOAL-003**: WHEN 사용자가 `DELETE /portfolios/{portfolio_id}/goals/{goal_id}` 를 호출하면, THEN 시스템은 해당 목표를 **소프트 삭제**(논리적 비활성화) 하고 **204** 를 반환해야 한다(SHALL).

### 3.4 소유권·접근 제어 (REQ-GOAL-004)

- **REQ-GOAL-004**: IF 요청 사용자가 해당 포트폴리오의 소유자가 아니면, THEN 시스템은 모든 목표 엔드포인트에서 **404** 를 반환해야 한다(SHALL). (존재 여부 노출 방지를 위해 403 이 아닌 404 사용 — 기존 포트폴리오 라우터 규약 준수)

### 3.5 활성 목표 없음 처리 (REQ-GOAL-005)

- **REQ-GOAL-005**: IF 해당 포트폴리오에 활성 목표가 존재하지 않으면, THEN `GET` 은 404 가 아니라 **빈 응답**(204 No Content)을 반환해야 한다(SHALL). (단일 객체 또는 204 — 빈 배열을 반환하지 않는다.)

### 3.6 달성률 계산 (REQ-GOAL-006)

- **REQ-GOAL-006**: 시스템은 달성률을 다음 규칙으로 계산해야 한다(SHALL):
  - 금액 목표: `achievement_rate = round((current_value / target_amount) * 100, 2)` (소수점 2자리 반올림)
  - 수익률 목표: `achievement_rate = round((current_return_rate / target_return_rate) * 100, 2)` (소수점 2자리 반올림)
  - 금액·수익률이 **모두 설정된 경우**: 두 달성률의 **MIN(최솟값)** 을 사용한다.
  - `target_amount` 또는 `target_return_rate` 가 0 이하이거나 미설정인 경우 해당 항목은 달성률 계산에서 제외한다(0 나눗셈 방지).
  - **`achievement_rate` 는 0 이상으로 클램핑한다 — 음수 수익률이어도 `max(0.0, 계산값)` 을 적용해 최소 0.0 을 반환한다.**

### 3.7 목표 달성 알림 (REQ-GOAL-007)

- **REQ-GOAL-007**: WHEN 스케줄러가 실행될 때(60분 주기), IF 어떤 목표의 `achievement_rate >= 100%` 이고 AND 아직 달성 알림이 발송되지 않았으면(`goal_reached_notified == False`), THEN 시스템은 SPEC-031/036 알림 인프라(텔레그램 + 이메일)로 달성 알림을 발송하고 알림 발송 여부 플래그(`goal_reached_notified = True`)를 갱신해야 한다(SHALL). 동일 목표에 대해 알림은 **1회만** 발송된다(멱등).

---

## 4. DB 스키마 (Migration 0025)

> 마이그레이션 경로: `backend/alembic/versions/0025_portfolio_goals_041.py`
> down_revision = `0024` (직전: `0024_ai_recommendation_037.py`)

```sql
-- portfolio_goals (신규 테이블, 마이그레이션 0025)
CREATE TABLE portfolio_goals (
    id                    SERIAL PRIMARY KEY,
    portfolio_id          INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    target_amount         NUMERIC(15,2),          -- 선택: 목표 평가액(원)
    target_return_rate    NUMERIC(8,4),           -- 선택: 목표 수익률(%)
    deadline              DATE,                    -- 선택: 목표 기한
    is_active             BOOLEAN NOT NULL DEFAULT TRUE,
    goal_reached_notified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at            TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_portfolio_goals_portfolio_id ON portfolio_goals (portfolio_id);
```

### 4.1 활성 목표 1개 제약 (앱 레벨)

- `UNIQUE(portfolio_id, is_active)` 형태의 부분 유일 제약은 PostgreSQL 부분 인덱스로도 가능하나, **MVP는 앱 레벨에서 강제**한다.
- `POST` 처리 시: 동일 포트폴리오에 활성 목표(`is_active=True`)가 이미 존재하면 **409 Conflict 를 반환**한다(REQ-GOAL-001a). 자동 비활성화 후 신규 생성은 채택하지 않는다 — 사용자가 기존 목표를 명시적으로 `DELETE` 한 뒤 재생성하도록 강제한다.

---

## 5. API 엔드포인트

| Method | Path | 응답 | 설명 |
|--------|------|------|------|
| POST | `/portfolios/{portfolio_id}/goals` | 201 `GoalResponse` / 422 / 409 | 목표 생성(활성 1개). 금액·수익률 모두 미입력 시 422, 활성 목표 이미 존재 시 409 |
| GET | `/portfolios/{portfolio_id}/goals` | 200 `GoalWithProgressResponse`(**단일 객체**) / 204 | 활성 목표 + 진척도 조회. 활성 목표 없으면 204 No Content |
| DELETE | `/portfolios/{portfolio_id}/goals/{goal_id}` | 204 | 소프트 삭제(논리적 비활성화) |

- **GET 응답 형태**: `GET /portfolios/{portfolio_id}/goals` 는 **단일 `GoalWithProgressResponse` 객체**를 반환한다(배열 아님). 활성 목표가 없으면 본문 없이 **204 No Content** 를 반환한다(빈 배열 `[]` 를 반환하지 않는다).
- 모든 엔드포인트는 `get_current_user` 보호 + 소유권 검증(REQ-GOAL-004).
- 라우터 prefix 는 기존 `/portfolios` (복수) 를 따른다 — `portfolio/router.py` 확장. 경로는 복수형(`/goals`)이지만 활성 목표 1개 제약에 따라 GET 은 단일 객체를 반환한다.

---

## 6. Pydantic 스키마

> 위치: `backend/src/stock_picker/portfolio/schemas.py` 확장

- **`GoalCreate`**
  - `target_amount: Decimal | None`
  - `target_return_rate: Decimal | None`
  - `deadline: date | None`
  - 검증(`model_validator(mode="after")`): **적어도 하나의 (`target_amount`, `target_return_rate`) 가 필수**다. 둘 다 None 이면 422 (deadline 단독은 불허). 또한 `target_amount`, `target_return_rate` 가 제공되면 각각 `> 0` 이어야 한다(음수·0 가드, MN-1).
  - `deadline` 은 **과거 날짜도 허용**한다(사용자가 추적용 과거 목표를 설정할 수 있음). 과거 기한의 진행률·잔여일 처리는 `days_remaining` 규칙(아래)을 따른다.
- **`GoalResponse`**
  - `id: int`, `portfolio_id: int`, `target_amount: Decimal | None`, `target_return_rate: Decimal | None`, `deadline: date | None`, `is_active: bool`, `created_at: datetime`
- **`GoalWithProgressResponse`** (extends `GoalResponse`)
  - `current_value: float`
  - `current_return_rate: float`
  - `achievement_rate: float`  (%, 0 이상으로 클램핑 — REQ-GOAL-006, 소수점 2자리)
  - `days_remaining: int | None`  (deadline 미설정 시 null, **deadline 이 과거이면 음수가 아니라 0 을 반환** — REQ-GOAL-002)

---

## 7. 프론트엔드 컴포넌트

- **`PortfolioGoalPanel.tsx`** (+ `.js` 사이드카) — 신규 컴포넌트
  - 목표 입력 폼(목표 금액 / 목표 수익률 / 기한, 부분 입력 허용)
  - 진행률 바(달성률 %, 100% 도달 시 강조)
  - 잔여일 배지(`days_remaining`, deadline 없으면 미표시)
  - 활성 목표가 없으면 "목표 설정하기" 빈 상태 UI
- **배치**: `frontend/src/pages/Portfolio.tsx` 에서 `AICommentaryPanel` **앞**에 렌더.
- **API 래퍼**: `frontend/src/api/portfolio.ts` (+ `.js`) 에 추가
  - `getPortfolioGoal(portfolioId): Promise<GoalWithProgressResponse | null>` — 활성 목표 단일 객체 반환, 204(활성 목표 없음)이면 `null` 반환
  - `createPortfolioGoal(portfolioId, payload)` — 422(금액·수익률 모두 미입력)·409(활성 목표 중복) 에러 처리 포함
  - `deletePortfolioGoal(portfolioId, goalId)`
  - **진행률 바**는 `achievement_rate` 가 항상 0 이상임을 전제로 렌더한다(REQ-GOAL-006 클램핑). 잔여일 배지는 `days_remaining === 0` 일 때 "기한 초과/마감" 표기를 적용한다.

---

## 8. 테스트 계획 (TDD · pytest)

> 위치: `backend/tests/unit/test_portfolio_goal_041.py` (+ 필요 시 `backend/tests/integration/`)

| ID | 시나리오 |
|----|----------|
| T-001 | 목표 생성 성공 — 금액만 |
| T-002 | 목표 생성 성공 — 수익률만 |
| T-003 | 목표 생성 성공 — 금액 + 수익률 + 기한 |
| T-004 | 목표 조회 — 금액 목표 달성률 계산 검증 |
| T-005 | 목표 조회 — 수익률 목표 달성률 계산 검증 |
| T-006 | 목표 조회 — 금액·수익률 모두 설정 시 MIN 사용 검증 |
| T-007 | 소유권 검증 — 타인 포트폴리오 접근 시 404 |
| T-008 | 목표 없을 때 GET → 빈 응답(204, 404 아님) |
| T-009 | 목표 삭제 성공 — is_active=False |
| T-010 | 스케줄러 달성 알림 발송 — `check_portfolio_goals()` 함수를 직접 호출하고, 텔레그램/이메일 헬퍼(`send_message_sync`, `send_general_alert_email`)를 `unittest.mock.patch` 로 mock 처리하여 알림 1회 발송 및 `goal_reached_notified=True` 업데이트를 확인 |
| T-011 | 기한 초과 목표 조회 시 `days_remaining=0` 반환 확인 (음수 아님) |
| T-012 | `GoalCreate` 검증 — `deadline` 만 입력(금액·수익률 모두 None) → 422 |
| T-013a | `target_amount=0` 또는 음수 값 POST 시 422 반환 (GoalCreate 스키마 검증 레이어) |
| T-013b | 서비스 레이어에서 target_amount 가 유효하지 않은 기존 행 대상 달성률 계산 시 0 나눗셈 가드 동작 확인 (유닛 테스트) |
| T-014 | 활성 목표 존재 시 POST → 409 Conflict |
| T-015 | 음수 수익률에서도 `achievement_rate >= 0.0` 클램핑 확인 |

---

## 9. 수용 기준 (Acceptance Criteria — EARS 매핑)

| AC | 연결 REQ | 측정 가능 기준 |
|----|----------|----------------|
| AC-1 | REQ-GOAL-001 | `POST` 에 금액만/수익률만/금액+수익률+기한 조합 입력 시 201 + 저장된 값 반환 |
| AC-1a | REQ-GOAL-001 | `POST` 에 `deadline` 만 입력(금액·수익률 모두 None) 시 **422 Unprocessable Entity** |
| AC-1b | REQ-GOAL-001a | 활성 목표가 이미 존재하는 포트폴리오에 `POST` → **409 Conflict** |
| AC-2 | REQ-GOAL-002 | `GET` 응답이 **단일 객체**이며 `current_value`·`current_return_rate`·`achievement_rate`·`days_remaining` 필드가 모두 존재 |
| AC-2a | REQ-GOAL-002 | 과거 `deadline` 목표 `GET` 시 `days_remaining=0` 반환(음수 아님) |
| AC-3 | REQ-GOAL-003 | `DELETE` 후 동일 목표 행이 논리적 비활성화(`is_active=False`), 응답 204 |
| AC-4 | REQ-GOAL-004 | 타 사용자 포트폴리오에 대한 모든 목표 엔드포인트 호출 → 404 |
| AC-5 | REQ-GOAL-005 | 활성 목표 없는 포트폴리오 `GET` → 204(본문 없음), 404·빈 배열 아님 |
| AC-6 | REQ-GOAL-006 | 금액 목표: `round((current_value/target_amount)*100, 2)`(소수점 2자리 반올림) 과 ±0.01% 이내 일치 |
| AC-7 | REQ-GOAL-006 | 수익률 목표: `round((current_return_rate/target_return_rate)*100, 2)`(소수점 2자리 반올림) 과 ±0.01% 이내 일치 |
| AC-8 | REQ-GOAL-006 | 금액·수익률 모두 설정 시 두 달성률 중 MIN 반환 |
| AC-8a | REQ-GOAL-006 | 음수 수익률 목표에서도 `achievement_rate >= 0.0` (음수 클램핑) |
| AC-9 | REQ-GOAL-007 | 달성률 ≥ 100% AND 알림 미발송 목표에 대해 스케줄러 1회 실행 시 텔레그램+이메일 발송 호출 + 알림 발송 여부 플래그 전환. 달성 알림 발송 후 `goal_reached_notified=True` DB 업데이트 확인. 알림은 1회만 발송됨(중복 방지: `goal_reached_notified==True` 이면 재발송 없음) |
| AC-10 | REQ-GOAL-007 | 이미 알림이 발송된 목표는 재실행 시 알림 미발송(멱등) |
| AC-11 | NFR | 신규 마이그레이션은 0025 단 1개, 신규 테이블 `portfolio_goals` 1개. scipy 등 신규 수치 라이브러리 미추가 |

---

## 10. 비기능 요구사항 (NFR)

- **NFR-1**: 신규 수치 계산 라이브러리(scipy 등) 미사용 — 표준 산술 연산만 사용한다.
- **NFR-2**: 현재 평가액·현재 수익률은 기존 성과 계산 로직(`portfolio/service.py`의 `calculate_performance()`, SPEC-026/017 자산)을 재사용하고 재구현하지 않는다.
- **NFR-3**: DB 변경은 마이그레이션 **0025 단 1개**(테이블 1개)로 제한한다. 기존 테이블 스키마를 변경하지 않는다.
- **NFR-4**: 자동 거래 로직을 포함하지 않는다(영구 제외 정책).
- **NFR-5**: 목표 달성 알림은 기존 알림 채널(텔레그램·이메일)만 사용하고, SPEC-036 `portfolio_alerts.py` 의 발송 헬퍼·`notifications` 멱등 적재 패턴을 재사용한다.
- **NFR-6**: 백엔드 TDD(pytest), 커버리지는 프로젝트 기준(`fail_under`)을 충족한다. 프론트엔드는 React 컴포넌트로 구현한다.

---

## 11. 코드베이스 정합성 노트 (Implementation Notes)

> RUN 단계에서 작업지시서와 실제 코드가 다른 지점 — 실제 코드를 따른다.

1. **마이그레이션 경로 정정**: 작업지시서의 `backend/src/stock_picker/migrations/versions/` 는 존재하지 않는다. 실제 경로는 **`backend/alembic/versions/`** 이며 최신 마이그레이션은 **0024**(`0024_ai_recommendation_037.py`). 따라서 신규는 0025, `down_revision="0024"`.
2. **`performance.py` 부재**: 작업지시서가 언급한 `portfolio/performance.py` 파일은 존재하지 않는다. 현재 평가액·수익률 계산의 단일 진입점은 **`portfolio/service.py` 의 `calculate_performance(db, portfolio_id, user_id)`** (`@MX:ANCHOR` 표시됨, 반환 dict: `total_invested`·`total_current`·`total_return_pct`·`holdings`·`classification_summary`·`sector_performance`). 목표 진척도 계산은 이 함수를 재사용한다.
   - `current_value` ← `total_current`
   - `current_return_rate` ← `total_return_pct`
3. **`_build_portfolio_data()` 위치**: 작업지시서가 SPEC-026 산출로 언급한 `_build_portfolio_data()` 는 **`portfolio/ai_analysis.py:76`** 에 정의되어 있다(AI 입력 구성용). 목표 진척도 산정에는 평가액·수익률만 필요하므로 `calculate_performance()` 사용을 우선한다.
4. **알림 인프라 재사용 대상**(SPEC-036 `portfolio_alerts.py`):
   - 이메일: `notifications/email_service.py` 의 `send_general_alert_email(...)`
   - 텔레그램: `telegram/notifier.py` 의 `_send_message_sync(...)`
   - 인앱 적재: `notifications` 테이블, UNIQUE 제약 `uq_notification_user_type_code_date` 로 멱등 보장(목표 달성은 `goal_reached_notified` 플래그로 추가 멱등). 알림 type 값/krx_code 컨벤션(예: `PORT_{portfolio_id}`)은 RUN 단계에서 SPEC-036 패턴에 맞춰 확정한다.
5. **스케줄러 연동**: 60분 주기 목표 점검 잡은 `scheduler/jobs.py` 에 등록한다. SPEC-036 의 `check_all_portfolio_alerts` 와 동일한 예외 격리 패턴을 따른다. (스케줄러 lifespan 기동 자체는 SPEC-022 영역 — 본 SPEC 범위 밖.)

---

## 12. 의존성

- **SPEC-026 / SPEC-017**: 성과 계산(`calculate_performance`, `get_portfolio_with_holdings`) 재사용
- **SPEC-031 / SPEC-036**: 알림 인프라(`portfolio_alerts.py` 발송 헬퍼, `notifications` 테이블, 이메일·텔레그램) 재사용
- **기술 스택**: FastAPI + SQLAlchemy + Alembic(Python 3.12), React + TypeScript(Vite)
