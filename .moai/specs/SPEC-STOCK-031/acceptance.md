# SPEC-STOCK-031 인수 조건 (Acceptance Criteria)

> **형식 안내**: 이 문서는 두 섹션으로 구성됩니다.
> - **§1 EARS 인수 조건**: spec.md §3 EARS 요구사항과 1:1 매핑되는 검증 가능한 인수 기준 (must-pass 기준).
> - **§2 BDD 시나리오**: 각 인수 기준을 자동화 테스트로 구현하기 위한 Given-When-Then 형식 상세 시나리오.

---

## §1. EARS 형식 인수 조건

각 REQ-PAL-XXX에 대응하는 EARS 형식 인수 조건. 각 항목은 검증 가능한 단일 EARS 문장으로 기술된다.

| REQ ID | 인수 조건 (EARS 형식) |
|--------|----------------------------------|
| REQ-PAL-001 | THE 시스템 SHALL `POST`, `GET`, `PUT`, `DELETE /portfolios/{portfolio_id}/alerts` 엔드포인트를 제공하며, 인증된 소유자에게만 알림 생성·목록 조회·수정·삭제가 동작하고 비소유자 요청에는 `404 Not Found`로 응답한다. |
| REQ-PAL-002 | WHEN 스케줄러가 활성 `portfolio_target_return` 알림을 평가하고 YTD 총수익률이 `condition_value` 이상이면 THE 시스템 SHALL 해당 알림을 정확히 1회 발화하고 `is_triggered`를 `true`로 갱신한다. |
| REQ-PAL-003 | WHEN 스케줄러가 활성 `portfolio_mdd_breach` 알림을 평가하고 YTD MDD(음수)가 `condition_value`(음수) 이하이면 THE 시스템 SHALL 해당 알림을 정확히 1회 발화하고 `is_triggered`를 `true`로 갱신한다. |
| REQ-PAL-004 | THE 시스템 SHALL 기존 10분 주기 알림 점검 잡에서 종목 알림 점검과 포트폴리오 알림 점검을 동일 잡으로 함께 수행하며, 신규 스케줄러 잡·주기를 추가하지 않는다. |
| REQ-PAL-005 | WHEN 포트폴리오 알림이 발화되면 THE 시스템 SHALL 인박스 알림을 `notifications` 테이블에 적재하고, 이메일·텔레그램은 best-effort로 발송한다. IF 이메일·텔레그램 발송이 실패하면 THEN THE 시스템 SHALL 인박스 적재를 차단하지 않는다. |
| REQ-PAL-006 | WHILE 사용자가 특정 alert_type의 발송 채널을 비활성화한 동안 THE 시스템 SHALL 해당 채널의 발송을 생략하고 인박스 적재는 유지하며, 신규 alert_type 2종을 알림 설정 게이팅 대상으로 포함한다. |
| REQ-PAL-007 | THE 프론트엔드 SHALL Portfolio 페이지에 포트폴리오 알림 설정 패널을 제공하여, 사용자가 포트폴리오별로 알림을 설정·조회·삭제할 수 있도록 한다. |
| REQ-PAL-008 | IF 동일 `(user_id, portfolio_id, alert_type)` 조합의 알림 생성 요청이 수신되면 THEN THE 시스템 SHALL `409 Conflict`로 거부하고 중복 행을 생성하지 않으며, 알림 발화 시 동일 날짜에 대한 중복 발송이 발생하지 않도록 멱등성을 보장한다. |
| NFR-001 | THE 시스템 SHALL 본 SPEC 신규 코드(`portfolio/portfolio_alerts.py`)에서 `scipy`를 import하지 않는다(정적 검사로 검증 가능). |
| NFR-002 | WHILE 동일 포트폴리오에 두 알림 타입이 모두 설정된 동안 THE 시스템 SHALL 점검 시 성과 요약을 1회만 조회하여 Redis 캐시를 재사용한다. |
| NFR-003 | THE `portfolio/portfolio_alerts.py` 코드 SHALL 단위 테스트 커버리지 85% 이상을 충족한다. |

---

## §2. BDD 시나리오 (자동화 테스트 기반)

> 각 시나리오에 해당 REQ ID를 명시한다. 시나리오는 §1 EARS 조건을 구현하는 자동화 테스트의 기반이다.

---

### Scenario 1: 목표 수익률 알림 발화
**Covers**: REQ-PAL-002, REQ-PAL-005

**Given**: 활성 `portfolio_target_return` 알림(`condition_value=10.0`, 목표 +10%)이 존재하고 `is_triggered=false`이다.

**When**: 성과 요약이 YTD 총수익률 `+12.0%`를 반환하는 상태에서 `check_all_portfolio_alerts`가 실행된다.

**Then**:
- 알림이 발화한다(`triggered=true`).
- `portfolio_alerts` 행이 `is_triggered=true`·`triggered_at`·`triggered_message`로 갱신된다.
- `notifications` 테이블에 인박스 알림이 적재된다(`type=portfolio_target_return`, `krx_code=PORT_{id}`).

---

### Scenario 2: MDD 임계값 알림 발화
**Covers**: REQ-PAL-003, REQ-PAL-005

**Given**: 활성 `portfolio_mdd_breach` 알림(`condition_value=-15.0`, 임계 -15%)이 존재하고 `is_triggered=false`이다.

**When**: 성과 요약이 YTD MDD `-16.5%`를 반환하는 상태에서 점검이 실행된다.

**Then**:
- 알림이 발화한다(`-16.5% <= -15.0%`).
- `is_triggered=true`로 갱신되고 인박스 알림이 적재된다.

---

### Scenario 3: 이미 발화된 알림 (멱등성)
**Covers**: REQ-PAL-002, REQ-PAL-008

**Given**: 이미 발화된 알림(`is_triggered=true`)이 존재한다.

**When**: 점검이 다시 실행된다(조건이 여전히 충족됨).

**Then**:
- 해당 알림은 재평가 대상에서 제외된다(`WHERE is_triggered=false`).
- 중복 알림이 발송되지 않는다.
- 동일 일자 재발화가 시도되더라도 `notifications` UNIQUE 제약으로 중복 인박스 적재가 차단된다.

---

### Scenario 4: 타인 포트폴리오 알림 생성
**Covers**: REQ-PAL-001, NFR-005

**Given**: `user_id != portfolio.user_id`인 다른 사용자의 포트폴리오가 존재한다.

**When**: 인증된 사용자가 `POST /portfolios/{other_user_portfolio_id}/alerts`를 호출한다.

**Then**:
- `404 Not Found`로 응답한다(`get_portfolio_with_holdings` None 반환, 코드베이스 관례, 403 아님).
- 알림이 생성되지 않는다.

---

### Scenario 5: 채널 비활성화 (이메일 생략)
**Covers**: REQ-PAL-006

**Given**: 사용자가 `portfolio_target_return`의 이메일 채널을 비활성화했고(`NotificationPreference.email_enabled=false`), 활성 알림이 발화 조건을 충족한다.

**When**: 알림이 발화하여 발송 파이프라인을 실행한다.

**Then**:
- 인박스 알림은 적재된다.
- `is_channel_enabled_async`가 False를 반환하여 이메일이 발송되지 않는다.
- 텔레그램은 게이팅 결과에 따라 처리된다.

---

### Scenario 6: 비활성 알림 건너뜀
**Covers**: REQ-PAL-002, REQ-PAL-004

**Given**: `is_active=false`인 알림이 존재한다(발화 조건은 충족 가능).

**When**: 스케줄러 점검이 실행된다.

**Then**:
- 비활성 알림은 평가 대상에서 제외된다(`WHERE is_active=true`).
- 알림이 발화하지 않는다.

---

### Scenario 7: 프론트엔드 알림 설정 패널
**Covers**: REQ-PAL-007

**Given**: Portfolio 페이지가 로드되고 포트폴리오 알림 API가 사용 가능하다.

**When**: 사용자가 알림 설정 영역(예: "알림 설정" 버튼)을 연다.

**Then**:
- `PortfolioAlertPanel` 컴포넌트가 마운트되어 알림 설정 폼(타입 선택·임계값 입력)이 표시된다.
- 기존 설정된 알림 목록이 조회·표시된다.
- 알림 삭제 동작이 제공된다.

---

### Scenario 8: 중복 알림 생성 거부
**Covers**: REQ-PAL-008

**Given**: 특정 포트폴리오에 `portfolio_target_return` 알림이 이미 존재한다.

**When**: 동일 사용자가 동일 포트폴리오에 동일 타입 알림을 다시 생성하려 한다.

**Then**:
- `(user_id, portfolio_id, alert_type)` UNIQUE 제약에 따라 `409 Conflict`로 거부된다.
- 중복 행이 생성되지 않는다.

---

## 성능·신뢰성 기준 (Performance & Reliability Criteria)

| 항목 | 기준 |
|------|------|
| 성과 요약 조회 | SPEC-030 Redis 캐시(`portfolio_perf_summary:{id}:{date}`, TTL 3600s) 재사용, portfolio_id별 1회(NFR-002) |
| 성과 조회 실패 | graceful degradation(해당 포트폴리오 건너뜀, 예외 비전파, NFR-004) |
| 이메일/텔레그램 발송 | best-effort(실패가 인박스 적재를 차단하지 않음, NFR-004) |
| 멱등성 | 알림 상태 머신(`is_triggered`) + `notifications` UNIQUE(`PORT_{id}`, ref_date) 이중 방어 |

---

## 품질 게이트 (Quality Gate)

- [ ] REQ-PAL-001 ~ REQ-PAL-008 전부 구현·검증.
- [ ] NFR-001(scipy 금지) 정적 검사 통과.
- [ ] NFR-003 단위 테스트 커버리지 85% 이상.
- [ ] 조건 평가 순수 함수 단위 테스트 PASS(발화·비발화·경계값·has_data=false).
- [ ] 오케스트레이션 테스트 PASS(발화·멱등·비활성 건너뜀·graceful·채널 게이팅).
- [ ] CRUD 테스트 PASS(생성/목록/수정/삭제·소유권 404·중복 409).
- [ ] 프론트엔드 알림 설정 패널 렌더링 확인(Scenario 7).
- [ ] 마이그레이션 `0020_portfolio_alerts.py` upgrade/downgrade 동작 확인.

## 완료 정의 (Definition of Done)

- 모든 인수 시나리오(1~8)가 자동화 테스트로 통과한다.
- §1 EARS 인수 조건 전 항목이 충족된다.
- 모든 품질 게이트 체크리스트 항목이 충족된다.
- MX 태그가 신규/수정 코드에 부여되었다(ANCHOR·NOTE·WARN).
- 기존 종목 알림(SPEC-020~025) 로직이 수정되지 않았다(`alerts` 테이블·`check_and_trigger_all_alerts` 불변).
- SPEC-030 성과 요약 코드(`performance_summary.py`)가 수정되지 않았다.
- 코드 주석은 한국어로 작성되었다.
