---
id: "SPEC-STOCK-031"
version: "0.2.0"
status: "draft"
created_at: "2026-06-23"
updated_at: "2026-06-23"
author: "ircp"
priority: "high"
issue_number: 0
labels: ["portfolio", "alerts", "notifications", "backend", "frontend"]
---

# SPEC-STOCK-031: 포트폴리오 알림 강화 (Portfolio Alert Enhancement)

> Roadmap Phase 3 "포트폴리오 AI 최적화" 계열 SPEC. 기존 종목 단위 알림(SPEC-020~025)이 개별 종목의 목표가·급등락을 감지하는 것과 달리, 본 SPEC은 **포트폴리오 단위**의 총수익률·최대낙폭(MDD)을 감지하는 알림을 추가한다. SPEC-030(포트폴리오 기간별 성과 요약)이 산출하는 성과 데이터를 알림 조건 평가의 데이터 소스로 재사용한다.

## HISTORY

| 버전 | 날짜 | 변경 내용 |
|------|------|-----------|
| 0.1.0 | 2026-06-23 | 최초 작성 |
| 0.2.0 | 2026-06-23 | plan-auditor v1 지적사항 반영 — acceptance.md EARS 형식 교정, REQ 구현 세부사항 분리 |

> **REQ 접두사 설계 원칙**: 본 SPEC은 `REQ-PAL-*`(Portfolio ALert) 접두사를 사용한다. SPEC-020(종목 알림)이 `REQ-ALERT-*`를, SPEC-025(알림 설정)가 `REQ-PREF-*`를 점유하므로 충돌을 회피한다.

> **번호 체계**: REQ-PAL-001~008 연속 번호를 사용한다.

---

## 1. 개요 (Overview)

### 1.1 기능 설명

사용자가 보유한 포트폴리오에 대해 두 종류의 포트폴리오 단위 알림을 설정·발송한다.

1. **목표 수익률 알림**(`portfolio_target_return`): 포트폴리오 총수익률이 사용자가 정의한 목표치(예: +10%)에 도달하면 알림을 발송한다.
2. **MDD 임계값 알림**(`portfolio_mdd_breach`): 포트폴리오 최대낙폭(MDD)이 사용자가 정의한 임계값(예: -15%)을 초과하면 알림을 발송한다.

알림은 기존 알림 인프라(SPEC-020~025)의 발송 파이프라인(인박스 → 이메일 → 텔레그램)과 알림 설정 게이팅(`is_channel_enabled_async`)을 그대로 재사용한다. 알림 조건 평가에 필요한 총수익률·MDD는 SPEC-030의 `get_performance_summary()`(정확히는 `calculate_performance_summary()`)가 반환하는 성과 요약에서 추출하며, 본 SPEC에서 재계산하지 않는다.

### 1.2 동기 (Motivation)

현재 알림 인프라(SPEC-020~025)는 **종목 단위** 알림만 지원한다(목표가·급등락·거래량 급증·배당락·추천 변동). 그러나 사용자가 "내 포트폴리오 전체 수익률이 목표치에 도달했는가" 또는 "내 포트폴리오의 낙폭이 위험 수준을 넘었는가"를 자동으로 감지받을 방법이 없다. 사용자는 SPEC-030 성과 요약을 직접 매번 조회해야 한다.

본 SPEC은 포트폴리오 단위 알림을 추가하여, 사용자가 임계값을 한 번 설정하면 스케줄러가 주기적으로 성과를 점검하고 조건 도달 시 자동으로 알림을 발송하도록 한다. 기존 알림 발송·설정 인프라를 재사용함으로써 신규 발송 채널을 구현하지 않는다.

### 1.3 목표 (Goals)

- 포트폴리오 단위 알림 두 종류(`portfolio_target_return`·`portfolio_mdd_breach`)를 CRUD로 관리한다.
- 신규 `portfolio_alerts` 테이블로 알림 규칙을 영속화한다(기존 `alerts` 테이블 미사용).
- 기존 10분 주기 알림 점검 잡을 확장하여 포트폴리오 알림도 함께 점검한다.
- 기존 발송 파이프라인(인박스·이메일·텔레그램)과 설정 게이팅을 재사용한다.
- SPEC-030 성과 요약을 데이터 소스로 재사용하여 수익률·MDD를 산출한다(재구현 금지).
- 프론트엔드 Portfolio 페이지에 포트폴리오 알림 설정/조회 UI를 추가한다.

### 1.4 기술 스택 (확정·재사용)

FastAPI + PostgreSQL(asyncpg) + SQLAlchemy + Alembic + Redis + React + TypeScript. 신규 라이브러리는 도입하지 않는다. 통계 계산은 SPEC-030 `performance_summary.py`를 재사용하므로 본 SPEC 코드에서 numpy·scipy를 직접 사용하지 않는다(NFR-001 자동 충족).

---

## 2. 범위 (Scope)

### 2.1 포함 (In Scope)

- 신규 `portfolio_alerts` 테이블 마이그레이션(`0020_portfolio_alerts.py`, down_revision=0019).
- 신규 서비스 `portfolio/portfolio_alerts.py`(알림 조건 평가 순수 함수 + 비동기 점검 오케스트레이션).
- `PortfolioAlertCreate`·`PortfolioAlertUpdate`·`PortfolioAlertResponse` Pydantic 스키마 추가(`portfolio/schemas.py`).
- 포트폴리오 알림 CRUD 엔드포인트(`portfolio/router.py`).
- 기존 10분 주기 알림 점검 잡(`scheduler/jobs.py`) 확장 — `check_all_portfolio_alerts()` 호출 추가.
- 신규 alert_type 상수 등록(`alerts/service.py` 또는 `notifications/general_alert_service.py`).
- `SUPPORTED_ALERT_TYPES`에 신규 타입 2종 추가(`notifications/preferences.py`).
- 프론트엔드 포트폴리오 알림 설정 패널 + API 클라이언트 확장.
- 단위 테스트(커버리지 85% 이상).

### 2.2 제외 (What NOT to Build)

> [HARD] 본 SPEC은 다음을 **빌드하지 않는다**.

- **자동 매매/주문 실행**: 규제·책임 리스크로 프로젝트 전체에서 **영구 제외**.
- **종목 단위 알림(stock alerts) 변경**: 기존 SPEC-020~025의 종목 알림 로직(`alerts` 테이블·`check_and_trigger_all_alerts`)은 수정하지 않는다.
- **실시간 WebSocket 알림**: 본 SPEC은 배치 스케줄러(10분 주기) 기반 알림만 제공한다. 실시간 푸시는 향후 SPEC.
- **포트폴리오당 동일 타입 복수 알림 동시 설정**: UI·관리 복잡성을 회피하기 위해 `(user_id, portfolio_id, alert_type)` 단위로 알림 1개만 허용한다(UNIQUE 제약).
- **성과 지표 재구현**: 총수익률·MDD는 SPEC-030 `performance_summary`를 재사용한다. 본 SPEC에서 수익률·MDD 계산 로직을 새로 작성하지 않는다.
- **알림 재발화(re-arm)·반복 알림**: 알림은 조건 도달 시 1회만 발화한다(`is_triggered=true` 후 미발화). 조건이 변동했다가 재도달해도 자동 재발화하지 않는다. 사용자는 알림을 삭제·재생성하여 초기화한다.
- **기준 기간 사용자 선택**: 어느 기간(YTD/1M/...)을 기준으로 평가할지는 §5.2에 고정 정의하며, 사용자가 기간을 선택하는 기능은 제공하지 않는다.
- **알림 이력·통계 대시보드**: 발화 이력 집계·차트는 제공하지 않는다(인박스 알림 목록은 기존 SPEC-013 인프라 사용).

---

## 3. 기능 요구사항 (EARS Requirements)

### REQ-PAL-001 (Ubiquitous)

THE 시스템 SHALL 포트폴리오 알림 CRUD 엔드포인트를 제공한다 — 알림 생성(CREATE), 포트폴리오별 알림 목록 조회(LIST), 알림 수정(UPDATE), 알림 삭제(DELETE). 모든 엔드포인트는 인증된 소유자에게만 동작한다.

### REQ-PAL-002 (Event-driven)

WHEN 스케줄러 점검이 활성 `portfolio_target_return` 알림을 평가할 때 THEN THE 시스템 SHALL SPEC-030 성과 요약의 YTD 기간(`periods[0]`) 총수익률이 알림의 `condition_value`(목표 수익률 %) 이상이면 알림을 발화하고, 1회만 발화한다(멱등).

### REQ-PAL-003 (Event-driven)

WHEN 스케줄러 점검이 활성 `portfolio_mdd_breach` 알림을 평가할 때 THEN THE 시스템 SHALL SPEC-030 성과 요약의 YTD 기간(`periods[0]`) MDD(음수)가 알림의 `condition_value`(임계값 %, 음수) 이하이면(더 큰 낙폭) 알림을 발화하고, 1회만 발화한다(멱등).

### REQ-PAL-004 (Ubiquitous)

THE 시스템 SHALL 기존 10분 주기 알림 점검 잡에 포트폴리오 알림 점검을 통합하여, 종목 알림과 포트폴리오 알림을 동일 잡에서 실행한다. 신규 스케줄러 잡·주기는 추가하지 않는다. (구체적인 함수·통합 지점은 §5.4 참조)

### REQ-PAL-005 (Event-driven)

WHEN 포트폴리오 알림이 발화되면 THEN THE 시스템 SHALL 기존 종목 알림과 동일한 발송 파이프라인(인박스 → 이메일 → 텔레그램)을 통해 알림을 발송한다. 인박스 알림은 기존 `notifications` 테이블에 적재하고, 이메일·텔레그램은 best-effort로 발송한다(실패 시 인박스 적재를 차단하지 않음).

### REQ-PAL-006 (State-driven)

WHILE 사용자가 특정 발송 채널(이메일·텔레그램)을 비활성화한 동안 THE 시스템 SHALL 해당 alert_type에 대해 사용자 알림 설정을 확인하고 비활성 채널의 발송을 생략한다. 신규 alert_type 2종(`portfolio_target_return`·`portfolio_mdd_breach`)은 알림 설정 게이팅 대상으로 등록된다. (게이팅 함수·상수는 §5.7 참조)

### REQ-PAL-007 (Ubiquitous)

THE 프론트엔드 SHALL Portfolio 페이지에 포트폴리오 알림 설정 패널을 제공하여, 사용자가 포트폴리오별로 목표 수익률 알림·MDD 임계값 알림을 설정·조회·삭제할 수 있도록 한다.

### REQ-PAL-008 (Unwanted)

IF 동일 사용자가 동일 포트폴리오에 대해 이미 존재하는 alert_type의 알림을 재생성하려 하면 THEN THE 시스템 SHALL `409 Conflict`로 거부하고 중복 행을 생성하지 않는다. 또한 알림 발화 시 동일 날짜에 대한 중복 발송이 발생하지 않도록 멱등성을 보장한다. (중복 방지 제약·멱등성 구현은 §5.3·§5.7 참조)

---

## 4. 비기능 요구사항 (NFR)

- **NFR-001 (scipy 금지)**: THE 시스템 SHALL 본 SPEC 신규 코드에서 `scipy`를 import하지 않는다. 수익률·MDD 계산은 SPEC-030 `performance_summary.py`(numpy + math 전용)를 재사용하므로 본 요건은 자동 충족된다.
- **NFR-002 (성능)**: THE 시스템 SHALL 포트폴리오 알림 점검 시 SPEC-030 성과 요약의 Redis 캐시(`portfolio_perf_summary:{id}:{date}`, TTL 3600s)를 재사용하여 FDR 반복 호출을 회피한다. 동일 포트폴리오에 두 알림 타입이 모두 설정된 경우 성과 요약을 1회만 조회한다.
- **NFR-003 (테스트 커버리지)**: THE `portfolio/portfolio_alerts.py` 서비스·순수 함수 코드 SHALL 단위 테스트 커버리지 85% 이상을 충족한다.
- **NFR-004 (graceful degradation)**: IF 성과 요약 조회 또는 이메일·텔레그램 발송이 실패하면 THEN THE 시스템 SHALL 예외를 전파하지 않고 해당 알림을 건너뛰거나 인박스 적재만 수행하여, 다른 알림 점검을 차단하지 않는다(기존 `check_and_trigger_all_alerts` 패턴 일관성).
- **NFR-005 (소유권 일관성)**: THE 시스템 SHALL 포트폴리오 소유권 확인에 `get_portfolio_with_holdings()`(소유권 불일치 시 None 반환)를 사용하고, 소유권 위반 시 `404 Not Found`로 응답한다(코드베이스 관례, 403 아님).

---

## 5. 기술 접근 방식 (Technical Approach)

### 5.1 `portfolio_alerts` 테이블 스키마

```
portfolio_alerts
  id                INTEGER PK AUTOINCREMENT
  user_id           INTEGER NOT NULL  FK(users.id, ondelete=CASCADE)
  portfolio_id      INTEGER NOT NULL  FK(portfolios.id, ondelete=CASCADE)
  alert_type        VARCHAR(30) NOT NULL  -- 'portfolio_target_return' | 'portfolio_mdd_breach'
  condition_value   FLOAT NOT NULL        -- 목표 수익률 % (예: 10.0) 또는 MDD 임계값 % (예: -15.0)
  is_active         BOOLEAN NOT NULL DEFAULT true
  is_triggered      BOOLEAN NOT NULL DEFAULT false
  triggered_at      TIMESTAMPTZ NULLABLE
  triggered_message VARCHAR(500) NULLABLE
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now()

  UNIQUE (user_id, portfolio_id, alert_type)   -- uq_portfolio_alert_user_pf_type
  INDEX  (user_id, is_active)                   -- ix_portfolio_alerts_user_active
```

기존 `alerts` 테이블과 스키마 형태는 유사하나 `krx_code`·`stock_name`·`condition_direction` 컬럼이 없고 `portfolio_id` 컬럼이 추가된다. 별도 엔터티로 분리하여 종목/포트폴리오 도메인 경계를 명확히 한다(research.md §4.2 Option B).

### 5.2 알림 조건 평가 (순수 함수)

평가 기준 기간은 **YTD**로 고정한다(`performance.periods[0]`, 가장 보편적인 포트폴리오 성과 지표). 해당 기간에 `has_data=false`이면 발화하지 않는다.

```
check_portfolio_return_alert(alert, performance) -> (triggered: bool, message: str):
  period = performance.periods[0]   # YTD
  if not period.has_data or period.total_return_pct is None: return (False, "")
  if period.total_return_pct >= alert.condition_value:
      msg = f"포트폴리오 수익률이 {total_return_pct:.2f}%에 도달했습니다 (목표 {condition_value:.2f}%)"
      return (True, msg)
  return (False, "")

check_portfolio_mdd_alert(alert, performance) -> (triggered: bool, message: str):
  period = performance.periods[0]   # YTD
  if not period.has_data or period.mdd_pct is None: return (False, "")
  if period.mdd_pct <= alert.condition_value:   # 예: -16.5% <= -15.0%
      msg = f"포트폴리오 최대낙폭이 {mdd_pct:.2f}%에 도달했습니다 (임계 {condition_value:.2f}%)"
      return (True, msg)
  return (False, "")
```

두 함수는 순수 함수다(DB 쿼리·상태 변경 없음). 기존 `check_target_price()`(general_alert_service.py) 패턴을 모방한다.

### 5.3 점검 오케스트레이션 (`portfolio/portfolio_alerts.py`)

```
check_all_portfolio_alerts(session) -> int:
  1. 활성 미발화 알림 조회: SELECT * FROM portfolio_alerts WHERE is_active=true AND is_triggered=false
  2. portfolio_id별 그룹핑 (성과 요약 1회 조회 재사용, NFR-002)
  3. FOR EACH portfolio_id:
       a. calculate_performance_summary(portfolio_id, user_id, db, redis)  # SPEC-030 재사용, 캐시 활용
       b. FOR EACH alert of this portfolio:
            - alert_type별 순수 함수 호출 (check_portfolio_return_alert | check_portfolio_mdd_alert)
            - IF triggered:
                · UPDATE portfolio_alerts SET is_triggered=true, triggered_at=now(), triggered_message=msg
                · INSERT INTO notifications (...) via on_conflict_do_nothing(constraint="uq_notification_user_type_code_date")
                  krx_code = f"PORT_{portfolio_id}",  type = alert_type,  ref_date = triggered_at.date()
                · await session.commit()
                · best-effort 이메일·텔레그램 발송 (is_channel_enabled_async 게이팅)
  4. RETURN triggered_count

예외 처리: 알림별 try-except, 성과 조회 실패 시 해당 포트폴리오 건너뜀, rollback on error (NFR-004).
```

### 5.4 스케줄러 통합 (`scheduler/jobs.py`)

기존 `_run_general_alert_check()`(10분 주기)를 확장한다.

```
async def _run_general_alert_check() -> None:
    async with AsyncSessionLocal() as session:
        stock_count = await check_and_trigger_all_alerts(session)        # 기존 (수정 없음)
        portfolio_count = await check_all_portfolio_alerts(session)      # 신규 호출
        log.info("알림 점검 완료", stock=stock_count, portfolio=portfolio_count)
```

신규 스케줄러 잡·주기는 추가하지 않는다. 기존 `IntervalTrigger(minutes=10)` 잡을 재사용한다(REQ-PAL-004).

### 5.5 스키마 (`portfolio/schemas.py`)

- `PortfolioAlertCreate`: `alert_type`(Literal "portfolio_target_return"/"portfolio_mdd_breach"), `condition_value`(float).
- `PortfolioAlertUpdate`: `condition_value`(float|None), `is_active`(bool|None).
- `PortfolioAlertResponse`: `id`(int), `portfolio_id`(int), `alert_type`(str), `condition_value`(float), `is_active`(bool), `is_triggered`(bool), `triggered_at`(str|None), `triggered_message`(str|None), `created_at`(str).
- Pydantic v2 패턴. `condition_value` 부호 검증은 필요 시 `model_validator`로 추가(예: MDD 임계값은 음수 권장).

### 5.6 라우터 (`portfolio/router.py`)

- `POST   /portfolios/{portfolio_id}/alerts` — 생성. 소유권 확인 → 중복 시 409.
- `GET    /portfolios/{portfolio_id}/alerts` — 포트폴리오별 알림 목록.
- `PUT    /portfolios/{portfolio_id}/alerts/{alert_id}` — 수정(condition_value·is_active).
- `DELETE /portfolios/{portfolio_id}/alerts/{alert_id}` — 삭제.
- 모두 `Depends(get_current_user)` + `get_portfolio_with_holdings` 소유권 확인. 소유권 불일치 → 404(NFR-005).

### 5.7 알림 설정·발송 인프라 재사용

- `is_channel_enabled_async(session, user_id, alert_type, channel)` — 채널 게이팅(SPEC-025, fail-open).
- `notifications` 테이블 + UNIQUE 제약 `uq_notification_user_type_code_date` — 인박스 멱등성.
- 이메일·텔레그램 발송: 기존 `_try_send_alert_email`·`_try_send_telegram` 패턴 모방(포트폴리오 컨텍스트 메시지로 조정).
- `SUPPORTED_ALERT_TYPES` 튜플에 신규 타입 2종 추가(`notifications/preferences.py`) — alert_type은 VARCHAR이므로 DB 변경 불필요.

### 5.8 프론트엔드

- `frontend/src/components/PortfolioAlertPanel.js` — 알림 설정 폼(타입 선택·임계값 입력) + 알림 목록(조회·삭제). 기존 패널 카드 레이아웃 패턴 재사용.
- `frontend/src/api/portfolio.ts`(+`.js`) — `apiCreatePortfolioAlert`·`apiListPortfolioAlerts`·`apiUpdatePortfolioAlert`·`apiDeletePortfolioAlert`.
- `frontend/src/pages/Portfolio.tsx`(+`.js`) — PortfolioAlertPanel 통합(기존 섹션 보존).

---

## 6. Delta Markers (변경 영향 분석)

브라운필드 프로젝트 변경 영향을 명시한다.

| 마커 | 파일 | 내용 |
|------|------|------|
| [EXISTING] | `backend/src/stock_picker/notifications/general_alert_service.py` | `check_and_trigger_all_alerts`·`is_channel_enabled_async` 호출 패턴·이메일/텔레그램 발송 패턴 참조(수정 없음) |
| [EXISTING] | `backend/src/stock_picker/notifications/inbox_router.py` | 인박스 알림 목록 조회(수정 없음, 신규 타입 자동 노출) |
| [EXISTING] | `backend/src/stock_picker/portfolio/performance_summary.py` | `calculate_performance_summary` 재사용(수정 없음, SPEC-030) |
| [EXISTING] | `backend/src/stock_picker/portfolio/service.py` | `get_portfolio_with_holdings` 소유권 확인 재사용(수정 없음) |
| [MODIFY] | `backend/src/stock_picker/scheduler/jobs.py` | `_run_general_alert_check`에 `check_all_portfolio_alerts` 호출 추가 |
| [MODIFY] | `backend/src/stock_picker/notifications/preferences.py` | `SUPPORTED_ALERT_TYPES`에 2종 추가 |
| [MODIFY] | `backend/src/stock_picker/alerts/service.py` | 신규 alert_type 상수 등록(존재 시) |
| [MODIFY] | `backend/src/stock_picker/portfolio/schemas.py` | `PortfolioAlert*` 스키마 추가 |
| [MODIFY] | `backend/src/stock_picker/portfolio/router.py` | 포트폴리오 알림 CRUD 엔드포인트 추가 |
| [MODIFY] | `backend/src/stock_picker/db/models.py` | `PortfolioAlert` ORM 모델 추가 |
| [NEW] | `backend/src/stock_picker/portfolio/portfolio_alerts.py` | 알림 조건 평가 + 점검 오케스트레이션 |
| [NEW] | `backend/alembic/versions/0020_portfolio_alerts.py` | `portfolio_alerts` 테이블 마이그레이션(down_revision=0019) |
| [NEW] | `backend/tests/unit/test_portfolio_alerts.py` | 단위 테스트(커버리지 85%+) |
| [NEW] | `frontend/src/components/PortfolioAlertPanel.js` | 알림 설정/조회 패널 |
| [MODIFY] | `frontend/src/api/portfolio.ts` | 알림 CRUD API 클라이언트 추가 |
| [MODIFY] | `frontend/src/api/portfolio.js` | 알림 CRUD API 클라이언트 추가 |
| [MODIFY] | `frontend/src/pages/Portfolio.tsx` | PortfolioAlertPanel 통합 |
| [MODIFY] | `frontend/src/pages/Portfolio.js` | PortfolioAlertPanel 통합 |

> **마이그레이션 경로 정정**: 본 프로젝트의 Alembic 마이그레이션은 `backend/alembic/versions/NNNN_name.py` 형식(`backend/src/stock_picker/migrations/versions/` 아님)이다. 최신 리비전은 `0019`이므로 신규 마이그레이션은 `0020_portfolio_alerts.py`(down_revision=`0019`)이다.

---

## 7. 의존성 (Dependencies)

- **SPEC-030**(포트폴리오 기간별 성과 요약): `calculate_performance_summary` 재사용 — 총수익률·MDD 데이터 소스. 본 SPEC은 SPEC-030 코드를 수정하지 않는다.
- **SPEC-025**(알림 설정): `is_channel_enabled_async`·`SUPPORTED_ALERT_TYPES`·`NotificationPreference`.
- **SPEC-020**(종목 알림): `check_and_trigger_all_alerts` 오케스트레이션·발송 파이프라인 패턴, 알림 상태 머신(`is_triggered`).
- **SPEC-013**(알림 인박스): `notifications` 테이블·UNIQUE 제약·인박스 라우터.
- **SPEC-017**(포트폴리오 성과): `get_portfolio_with_holdings` 소유권 확인.

---

## 8. MX 태그 계획 (MX Tag Plan)

코드 주석 언어는 한국어(`language.yaml` `code_comments: ko`).

- **@MX:ANCHOR** (`portfolio_alerts.py`의 `check_all_portfolio_alerts` 오케스트레이션 진입점):
  - 사유: scheduler/jobs.py + 단위 테스트에서 fan_in ≥ 3 예상. `@MX:REASON` 필수.
- **@MX:NOTE** (`check_portfolio_return_alert`·`check_portfolio_mdd_alert` 순수 함수):
  - 알림 조건 평가 비즈니스 로직(목표 수익률 도달·MDD 임계 초과 정의) 설명.
- **@MX:NOTE** (`portfolio_alerts.py` 모듈 상단):
  - 기존 알림 인프라 재사용 원칙·멱등성(notifications UNIQUE, `PORT_{id}` krx_code) 명시.
- **@MX:WARN** (notifications INSERT 멱등성 처리부):
  - `krx_code` 필드 의미 전용(`PORT_{portfolio_id}`) 주의. `@MX:REASON` 필수.
- **@MX:TODO** (RED 단계):
  - 미구현 순수 함수·오케스트레이션에 테스트 작성 전 임시 마커. GREEN 단계에서 제거.

태그 설명은 한국어로 작성하고, 에이전트 생성 태그는 `[AUTO]` 접두사를 포함한다.
