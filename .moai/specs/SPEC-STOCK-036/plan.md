# SPEC-STOCK-036 — 구현 계획 (Plan)

> 우선순위 라벨 사용(시간 추정 금지). 작업 순서: T-001 → T-008.

## 기술 접근 요약

SPEC-STOCK-031 포트폴리오 알림 인프라(`portfolio_alerts` 테이블, 오케스트레이션,
CRUD, 스케줄러, 인박스 적재)를 재사용하고, `alert_type`에 `portfolio_value_below`·
`holding_return` 2종을 추가한다. 평가액·종목 수익률 데이터는 `portfolio/service.py`
보유종목 평가 로직을 재사용한다. 신규 테이블 없음(필요 시 nullable 컬럼만 0023 추가).

## 마일스톤

- **M1 (스키마·모델)** — T-001, T-002 — Priority High
- **M2 (순수 함수·메시지)** — T-003, T-004 — Priority High
- **M3 (서비스·라우터 연동)** — T-005, T-006 — Priority High
- **M4 (프런트·테스트)** — T-007, T-008 — Priority Medium

## 작업 목록

### T-001 — 스키마 확장 (alert rule schemas)

- `portfolio/schemas.py`의 `PortfolioAlertCreate`/`PortfolioAlertUpdate`/
  `PortfolioAlertResponse`의 `alert_type` Literal에 `portfolio_value_below`·
  `holding_return` 추가.
- 종목 수익률 규칙용 선택 필드(대상 종목 식별자·비교 방향) 추가, 평가액·기존 유형에는 선택적.
- 검증: 미지원 유형/모순 입력 거부.
- 의존: 없음. Priority High.

### T-002 — 모델·마이그레이션 0023 (조건부)

- 개별 종목 알림에 필요한 `target_krx_code`·`condition_direction`를 `PortfolioAlert`에
  **nullable 컬럼**으로 추가할지 RUN에서 최종 결정. 추가 시 마이그레이션 `0023`
  (down_rev=0022), 기존 행은 NULL(하위 호환). **신규 테이블 생성 금지.**
- 대안(부호/인코딩 우회) 채택 시 마이그레이션 생략.
- 의존: 없음(T-001과 병행 가능). Priority High.

### T-003 — `check_portfolio_value_alert` 순수 함수

- 시그니처: `check_portfolio_value_alert(alert, current_value_krw) -> tuple[bool, str]`.
- 포트폴리오 현재 평가액이 임계 금액 이하이면 발화(True, 한국어 메시지).
- DB·상태 의존 없음. numpy/math만. (REQ-PALX-005, REQ-PALX-NFR-002)
- 의존: 없음. Priority High.

### T-004 — `check_holding_return_alert` 순수 함수 + 메시지 빌더

- 시그니처: `check_holding_return_alert(alert, holding_return_pct) -> tuple[bool, str]`.
- 비교 방향(이상/이하)에 따라 임계 도달 판정. (REQ-PALX-006)
- 유형별 인박스 제목·발화 메시지 빌더(`_build_notification_title` 확장).
- 의존: T-001(방향 필드). Priority High.

### T-005 — 서비스 레이어 연동 (create/list/update/delete/evaluate)

- 기존 CRUD(`create/list/update/delete_portfolio_alert`)가 신규 유형도 처리하도록 검증·확장.
- `check_all_portfolio_alerts`에 신규 2종 분기 추가(기존 분기 불변):
  평가액 유형 → 포트폴리오 평가액 합계 산출 후 평가, 종목 수익률 유형 → 대상 종목
  `return_pct` 산출 후 평가. 데이터는 `service.py` 보유종목 평가 로직 재사용.
- 발화 시 기존 멱등 `notifications` INSERT + 채널 best-effort 흐름 재사용.
- 시세·평가 실패 시 해당 포트폴리오 건너뜀(REQ-PALX-NFR-005).
- 의존: T-002, T-003, T-004. Priority High.

### T-006 — 라우터 엔드포인트

- 기존 `POST/GET/PUT/DELETE /portfolios/{id}/alerts[/{alert_id}]` 재사용(유형만 확장).
- 신규: `POST /portfolios/{id}/alerts/evaluate`(즉시 평가 트리거, REQ-PALX-011),
  `GET /portfolios/{id}/alerts/history`(발화 이력, 인박스 재사용, REQ-PALX-010).
- 소유권 위반 404 유지(REQ-PALX-NFR-003).
- 의존: T-005. Priority High.

### T-007 — 프런트엔드 컴포넌트 + API 클라이언트

- `frontend/src/pages/Portfolio.*` 알림 규칙 폼/목록에 신규 2종 입력(평가액 임계,
  종목 선택·임계·방향) 추가.
- `frontend/src/api/portfolio.*`에 즉시 평가·이력 조회 클라이언트 추가.
- 의존: T-006. Priority Medium.

### T-008 — 테스트 (24+ tests)

- 단위: `check_portfolio_value_alert`(경계 포함), `check_holding_return_alert`(이상/이하),
  메시지 빌더, 비활성 제외, 일자별 중복 방지 멱등성.
- 통합: 규칙 생성/조회/수정/삭제, 즉시 평가, 이력 조회, 소유권 404, 시세·채널 실패 격리.
- SPEC-031 기존 2유형 회귀 테스트 포함.
- 테스트 경로: `backend/tests/unit/`, `backend/tests/integration/`.
- 커버리지 85% 이상. 의존: T-001~T-007. Priority Medium.

## 리스크

- **컬럼 추가 vs 인코딩 우회**: 종목 식별·방향 저장 방식 결정이 마이그레이션 유무를
  좌우한다. 하위 호환·가독성을 위해 nullable 컬럼 추가를 권장하되 RUN에서 확정.
- **이중 발화 가능성**: 평가액·종목 알림과 SPEC-031 수익률 알림이 동시 활성일 경우 서로
  독립 발화한다(의도된 동작으로 문서화).
- **시세 정합성**: 종목 수익률은 동기 현재가 조회에 의존 — 실패 시 해당 포트폴리오 격리.

## @MX 태그 계획

- `check_all_portfolio_alerts`: 기존 `@MX:ANCHOR` 유지(fan_in≥3), SPEC 참조에 036 추가.
- 신규 순수 함수: `@MX:NOTE`(조건 평가 의도).
- nullable 컬럼 추가 시 모델에 `@MX:NOTE`(하위 호환 NULL 의미).
