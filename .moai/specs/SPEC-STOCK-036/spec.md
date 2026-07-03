---
id: "SPEC-STOCK-036"
version: "0.2.0"
status: "draft"
created_at: "2026-06-24"
priority: "medium"
labels: ["portfolio", "alert", "notification", "backend", "frontend"]
---

# SPEC-STOCK-036 — 포트폴리오 알림 확장 (Portfolio Alert Extension)

## HISTORY

- 2026-06-24 (v0.2.0): plan-auditor v1 지적사항 반영 — acceptance.md GWT→EARS 전환(15건),
  REQ-PALX-013(규칙 삭제) 추가, NFR-001 레이블 Unwanted→Ubiquitous 수정,
  REQ-PALX-012·NFR-001·NFR-002에 대응 AC 추가(AC-16·AC-ALT-NFR-001·AC-ALT-NFR-002),
  acceptance.md 구현 세부(함수명·열거값) 제거.
- 2026-06-24 (v0.1.0): 초안 작성. SPEC-STOCK-031 포트폴리오 알림 인프라를 재사용하여
  평가액 임계·개별 보유종목 수익률 임계 2종을 확장. 신규 테이블 없음(필요 시
  마이그레이션 0023으로 nullable 컬럼만 추가).

---

## Overview / WHY

사용자는 포트폴리오에 특정 조건이 충족되면(목표 수익률 도달, 평가액 하락, 개별
종목 손익 도달 등) 알림을 받기를 원한다. 포트폴리오 수익률·MDD 임계 알림은
SPEC-STOCK-031에서 이미 구현되었으나, 다음 두 관점이 비어 있다.

1. **포트폴리오 평가액(절대 금액, KRW) 임계 알림** — 수익률%가 아닌 평가 금액이
   특정 금액 이하로 떨어지면 알리고 싶다(예: 원금 방어선 관리).
2. **개별 보유종목 수익률 임계 알림** — 포트폴리오 전체가 아니라 특정 보유 종목의
   손익률이 임계에 도달하면 알리고 싶다(예: 익절/손절 후보 인지).

본 SPEC은 SPEC-031의 알림 인프라(테이블 `portfolio_alerts`, 순수 함수,
오케스트레이션, CRUD, 스케줄러 연동, 인박스 적재)를 **재사용**하고, 위 2종의 알림
유형만 추가한다. 알림 이력은 기존 `notifications` 인박스를 진실 소스로 사용한다.

WHY: 알림 시스템은 점진적으로 확장되어야 하며, 동일 기능을 재구축하면 중복·드리프트가
발생한다. SPEC-031 위에 최소 표면적으로 2종을 더하는 것이 유지보수·일관성 측면에서 옳다.

---

## WHAT

### 개요

`portfolio_alerts.alert_type`에 두 가지 신규 유형을 추가한다.

- `portfolio_value_below` — 포트폴리오 현재 평가액이 임계 금액(KRW) 이하일 때 발화.
- `holding_return` — 지정한 개별 보유종목의 수익률이 임계(%)에 도달할 때 발화.
  방향(이상/이하)을 지정할 수 있어 익절·손절 모두 표현 가능.

기존 알림 규칙 CRUD·스케줄러 점검·인박스 적재·채널 발송(이메일/텔레그램) 흐름은
변경 없이 신규 2종에도 그대로 적용된다.

### 요구사항 요약

- 사용자는 포트폴리오별로 알림 규칙을 생성·조회·수정(활성/비활성 토글 포함)·삭제할 수 있다.
- 시스템은 주기적으로 활성 규칙을 현재 포트폴리오 상태와 대조하여 조건 충족 시 알림을 발화한다.
- 발화된 알림은 인박스에 기록되며, 일자별 중복 발화는 방지된다.
- 알림 규칙은 소유자만 접근할 수 있으며, 타 사용자의 규칙 접근은 거부된다.
- 알림 조건 평가는 DB 없이 독립 검증 가능한 순수 함수로 수행된다.

### Exclusions (What NOT to Build)

- **자동 매매·주문 실행** — 규제·책임 리스크로 영구 제외.
- **신규 `portfolio_alert_rules` / `portfolio_alert_history` 테이블** — SPEC-031의
  `portfolio_alerts` 및 SPEC-013의 `notifications`를 재사용하므로 생성하지 않는다.
- **SPEC-031 기존 2유형(`portfolio_target_return`, `portfolio_mdd_breach`) 재구현** —
  변경하지 않는다.
- **신규 알림 채널(웹푸시·SMS·카카오톡 등)** — 기존 이메일·텔레그램·인앱 인박스만 사용.
- **WebSocket 실시간 알림 푸시** — 주기 점검 방식만 유지.
- **신규 스케줄러 잡** — 기존 `check_all_portfolio_alerts` 점검 지점에 연동만 한다.
- **알림 조건 시계열·과거 회귀 분석·예측** — 현재 상태 기준 단발 평가만.
- **종목 추천 재가중·매매 시점 추천** — 알림은 정보 제공에 한정.

---

## REQUIREMENTS

> EARS 형식. 정규 요구문에는 함수명·HTTP 코드·SQL·라이브러리명·변수명을 쓰지 않는다.

### 기능 요구사항 (REQ-PALX-*)

- **REQ-PALX-001 (Ubiquitous):** THE 시스템 SHALL 포트폴리오별로 평가액 임계 알림 규칙과
  개별 보유종목 수익률 임계 알림 규칙을 정의·저장하는 수단을 제공한다.

- **REQ-PALX-002 (Event-Driven):** WHEN 사용자가 평가액 임계 알림 규칙을 생성하면,
  THE 시스템 SHALL 임계 금액과 활성 상태를 포함한 규칙을 해당 포트폴리오에 등록한다.

- **REQ-PALX-003 (Event-Driven):** WHEN 사용자가 개별 보유종목 수익률 알림 규칙을 생성하면,
  THE 시스템 SHALL 대상 종목, 임계 수익률, 비교 방향(이상 또는 이하)을 포함한 규칙을 등록한다.

- **REQ-PALX-004 (Event-Driven):** WHEN 시스템이 활성 알림 규칙을 현재 포트폴리오 상태와
  대조할 때, THE 시스템 SHALL 평가액 규칙은 포트폴리오 현재 평가액을, 종목 수익률 규칙은
  대상 종목의 현재 수익률을 기준으로 조건 충족 여부를 판정한다.

- **REQ-PALX-005 (Event-Driven):** WHEN 평가액 알림 규칙의 포트폴리오 현재 평가액이 임계 금액
  이하가 되면, THE 시스템 SHALL 해당 규칙을 발화하고 발화 메시지를 기록한다.

- **REQ-PALX-006 (Event-Driven):** WHEN 개별 보유종목 알림 규칙의 대상 종목 수익률이 지정한
  방향 기준으로 임계에 도달하면, THE 시스템 SHALL 해당 규칙을 발화하고 발화 메시지를 기록한다.

- **REQ-PALX-007 (Event-Driven):** WHEN 알림 규칙이 발화되면, THE 시스템 SHALL 발화 내역을
  사용자 알림 이력에 기록하고, 동일 규칙의 동일 일자 중복 발화를 방지한다.

- **REQ-PALX-008 (State-Driven):** WHILE 알림 규칙이 비활성 상태인 동안, THE 시스템 SHALL
  해당 규칙을 점검 대상에서 제외한다.

- **REQ-PALX-009 (Event-Driven):** WHEN 사용자가 알림 규칙의 활성 상태를 전환하면,
  THE 시스템 SHALL 변경된 활성 상태를 즉시 반영한다.

- **REQ-PALX-010 (Event-Driven):** WHEN 사용자가 자신의 알림 규칙 목록 또는 알림 발화 이력을
  요청하면, THE 시스템 SHALL 해당 사용자에게 속한 항목만 반환한다.

- **REQ-PALX-011 (Event-Driven):** WHEN 사용자가 알림 규칙 즉시 평가를 요청하면,
  THE 시스템 SHALL 해당 포트폴리오의 활성 규칙을 현재 상태로 즉시 점검한다.

- **REQ-PALX-012 (Optional):** WHERE 사용자가 발화 알림에 대한 채널 수신을 활성화한 경우,
  THE 시스템 SHALL 이메일 또는 텔레그램으로 발화 내용을 부가 발송한다.

- **REQ-PALX-013 (Event-Driven):** WHEN 인증된 사용자가 자신의 알림 규칙 삭제를 요청하면,
  THE 시스템 SHALL 해당 규칙을 영구적으로 제거한다.

### 비기능 요구사항 (REQ-PALX-NFR-*)

- **REQ-PALX-NFR-001 (Ubiquitous):** THE 시스템 SHALL 외부 과학 계산 라이브러리를 새로
  도입하지 않는다(수치 계산은 표준 수치 연산만 사용).

- **REQ-PALX-NFR-002 (Ubiquitous):** THE 시스템 SHALL 알림 조건 평가 로직을 데이터 저장소 없이
  독립적으로 검증할 수 있는 순수 함수로 제공한다.

- **REQ-PALX-NFR-003 (Unwanted):** IF 알림 규칙 요청자가 해당 규칙의 소유자가 아니면,
  THEN THE 시스템 SHALL 그 요청을 거부하고 자원 부재로 응답한다.

- **REQ-PALX-NFR-004 (Event-Driven):** WHEN 동일 규칙·동일 일자에 대해 발화 기록을 적재할 때,
  THE 시스템 SHALL 데이터베이스 종류에 중립적인 방식으로 중복을 방지한다.

- **REQ-PALX-NFR-005 (Unwanted):** IF 알림 점검 중 특정 포트폴리오의 시세 또는 평가에 실패하면,
  THEN THE 시스템 SHALL 그 포트폴리오만 건너뛰고 나머지 점검을 계속한다.

- **REQ-PALX-NFR-006 (Unwanted):** IF 부가 채널 발송이 실패하면, THEN THE 시스템 SHALL
  알림 발화 자체는 유지하고 채널 실패를 무시한다.

---

## Technical Approach

> 기술 접근은 RUN 단계 참고용. 정규 요구문(위)에는 포함하지 않는다.

### 재사용 (변경 없음)

- 테이블 `portfolio_alerts`(SPEC-031, 마이그 0020), 모델 `PortfolioAlert`.
- 오케스트레이션 `check_all_portfolio_alerts`(분기 추가만), 스케줄러 연동 지점.
- 인박스 `notifications`(SPEC-013, 마이그 0014) — 발화 이력 진실 소스, 멱등 INSERT.
- 채널 게이팅 `is_channel_enabled_async`(SPEC-025), 이메일/텔레그램 best-effort 헬퍼.
- 평가액·종목 수익률 데이터: `portfolio/service.py`의 보유종목 평가 로직 및
  `get_portfolio_with_holdings`(종목별 `return_pct`, 합계 `current_value`).

### 신규 (최소 추가)

- 순수 함수 `check_portfolio_value_alert(alert, current_value_krw) -> (bool, str)`.
- 순수 함수 `check_holding_return_alert(alert, holding_return_pct) -> (bool, str)`.
- 메시지 빌더(한국어, 사람 친화) — 알림 유형별 발화 문구.
- 스키마 `PortfolioAlertCreate/Update/Response`의 `alert_type` Literal에 값 2개 추가.
- (조건부) 마이그레이션 0023(down_rev=0022): `portfolio_alerts`에 nullable 컬럼
  `target_krx_code`·`condition_direction` 추가 — 신규 테이블 없음, 기존 행은 NULL로 하위 호환.
  최종 채택 여부는 RUN에서 확정(부호 인코딩 대안 검토 포함).
- 프런트엔드: 포트폴리오 화면 알림 규칙 폼/목록에 신규 2종 입력 추가, API 클라이언트 확장.

### 제약 재확인

- scipy 등 신규 과학 라이브러리 금지(numpy + math만).
- 소유권 위반은 404로 응답(403 아님).
- DB-중립 upsert(SELECT-then-write 또는 기존 멱등 INSERT 재사용).
- 코드 주석 한국어, 커밋 메시지 한국어.
- 패키지 경로 `backend/src/stock_picker/portfolio/`.

### 의존성

- SPEC-STOCK-031(포트폴리오 알림 인프라), SPEC-STOCK-013(인박스), SPEC-STOCK-025(채널 게이팅),
  SPEC-STOCK-017(포트폴리오 보유·평가), SPEC-STOCK-030(성과 요약 — 기존 유형 재사용 시).
