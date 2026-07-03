# SPEC-STOCK-031 구현 계획 (Implementation Plan)

> 포트폴리오 알림 강화(목표 수익률·MDD 임계값). TDD(RED-GREEN-REFACTOR) 방법론. 기존 알림 인프라(SPEC-020~025)·성과 요약(SPEC-030) 재사용.

---

## 1. 작업 분해 (Task Decomposition)

| Task | 내용 | 산출물 | 우선순위 |
|------|------|--------|---------|
| **T-001** | `portfolio_alerts` 테이블 마이그레이션 + `PortfolioAlert` ORM 모델 | `alembic/versions/0020_portfolio_alerts.py` 신규, `db/models.py` 수정 | High |
| **T-002** | `schemas.py`에 `PortfolioAlertCreate`·`PortfolioAlertUpdate`·`PortfolioAlertResponse` 추가 | `portfolio/schemas.py` 수정 | High |
| **T-003** | `portfolio_alerts.py` 조건 평가 순수 함수 + `check_all_portfolio_alerts` 오케스트레이션 + CRUD 서비스 | `portfolio/portfolio_alerts.py` 신규 | High |
| **T-004** | `router.py`에 포트폴리오 알림 CRUD 엔드포인트 추가 | `portfolio/router.py` 수정 | High |
| **T-005** | 스케줄러 통합(`_run_general_alert_check` 확장) + `SUPPORTED_ALERT_TYPES` 추가 + alert_type 상수 등록 | `scheduler/jobs.py`·`notifications/preferences.py`·`alerts/service.py` 수정 | High |
| **T-006** | 단위 테스트 작성(커버리지 85%+) | `tests/unit/test_portfolio_alerts.py` 신규 | High |
| **T-007** | 프론트엔드 `PortfolioAlertPanel.js` + API 클라이언트(`.ts`/`.js`) + Portfolio 페이지(`.tsx`/`.js`) 통합 | `frontend/src/components/PortfolioAlertPanel.js` 신규, `api/portfolio.{ts,js}`·`pages/Portfolio.{tsx,js}` 수정 | Medium |
| **T-008** | MX 태그 검수 및 정리 | 전체 신규/수정 파일 | Low |

### 마일스톤 그룹핑

- **M1 (DB·스키마)**: T-001 → T-002. 마이그레이션·모델 → 스키마 순서(의존성 순).
- **M2 (백엔드 코어)**: [RED 테스트] → T-003(서비스) → T-004(라우터) → T-005(스케줄러·설정).
- **M3 (백엔드 테스트)**: T-006. TDD 원칙상 RED 단계는 각 구현(T-003·T-004) 전에 실패 테스트로 선행.
- **M4 (프론트엔드)**: T-007.
- **M5 (마무리)**: T-008.

> TDD 적용: T-003·T-004 구현 전 T-006의 해당 테스트를 먼저 작성하여 RED 확인 후 GREEN으로 구현.

---

## 2. 기술 스택 (Technology Stack)

| 계층 | 기술 | 비고 |
|------|------|------|
| 언어 | Python 3.11 | `target-version = "py311"` |
| 웹 프레임워크 | FastAPI | 기존 `portfolio/router.py` 확장 |
| ORM | SQLAlchemy(2.x, Mapped) | `db/models.py` `Alert` 모델 패턴 모방 |
| 마이그레이션 | Alembic | `0020_portfolio_alerts.py`, down_revision=`0019` |
| DB | PostgreSQL(asyncpg) | 신규 테이블 `portfolio_alerts` 1개 추가 |
| 캐싱 | Redis(redis.asyncio) | SPEC-030 성과 요약 캐시 재사용(`portfolio_perf_summary:{id}:{date}`) |
| 스케줄러 | APScheduler | 기존 10분 주기 잡 확장(신규 잡 없음) |
| 프론트엔드 | React + TypeScript | 알림 설정/조회 패널 |
| 테스트 | pytest + pytest-asyncio | 단위 테스트 |

신규 라이브러리 도입 없음. 수익률·MDD 계산은 SPEC-030 재사용으로 numpy·scipy 직접 사용 없음(NFR-001 자동 충족).

---

## 3. 구현 상세 접근 (Reference Implementations)

research.md에서 식별한 재사용 패턴(파일·라인).

### 3.1 ORM 모델·마이그레이션 (T-001)

- `Alert` ORM 모델 — `db/models.py:609-648`. `Mapped` 패턴·`__table_args__` Index·FK CASCADE 참조. `portfolio_alerts`는 `krx_code`·`stock_name`·`condition_direction` 제거, `portfolio_id` FK 추가, `(user_id, portfolio_id, alert_type)` UNIQUE 추가.
- 마이그레이션 형식 — `alembic/versions/0017_alerts.py`(테이블 생성 + Index), `0019_portfolio_foreign_asset.py`(down_revision 체인). UNIQUE 제약 명명 관례: `uq_*`(예: `uq_portfolio_alert_user_pf_type`).

### 3.2 조건 평가 순수 함수 (T-003, REQ-PAL-002·003)

- `check_target_price()` — `general_alert_service.py:117-...`. 순수 함수(상태·DB 없음), `(triggered: bool, msg: str)` 반환 패턴.
- 성과 요약 데이터 구조 — `PerformanceSummaryResponse.periods[0]`(YTD), `PeriodPerformance.total_return_pct`·`mdd_pct`·`has_data`(SPEC-030 `schemas.py`).

### 3.3 점검 오케스트레이션 (T-003, REQ-PAL-002~005)

- `check_and_trigger_all_alerts()` — `general_alert_service.py:456-540`. 활성 미발화 조회 → 평가 → UPDATE + notification INSERT(on_conflict_do_nothing) + commit → best-effort 이메일/텔레그램.
- 트랜잭션 패턴 — `general_alert_service.py:522-526`(`pg_insert` + `on_conflict_do_nothing(constraint="uq_notification_user_type_code_date")`).
- 성과 요약 재사용 — `calculate_performance_summary(portfolio_id, user_id, db, redis)`(SPEC-030 `performance_summary.py`). portfolio_id별 1회 조회로 캐시 활용(NFR-002).

### 3.4 발송·게이팅 (T-003, REQ-PAL-005·006)

- `is_channel_enabled_async(session, user_id, alert_type, channel)` — `preferences.py:39-74`(fail-open).
- 이메일 발송 — `_try_send_alert_email()` 패턴(`general_alert_service.py`), `EmailSubscription` 조회 + `_send_email`. 포트폴리오 컨텍스트로 subject/body 조정.
- 텔레그램 발송 — `_try_send_telegram()` 패턴, `TelegramSubscription` 조회.

### 3.5 CRUD·소유권·라우터 (T-004, REQ-PAL-001·008, NFR-005)

- `get_portfolio_with_holdings()` — `service.py:87-100`. 소유권 불일치 시 None → 404.
- 알림 CRUD 라우터 패턴 — `general_alert_router.py`(POST/GET/PUT/DELETE, `Depends(get_current_user)`, 서비스 내부 소유권 검증).
- UNIQUE 중복 처리 — `(user_id, portfolio_id, alert_type)` 충돌 시 `IntegrityError` 포착 → 409(또는 사전 SELECT 후 409).

### 3.6 스케줄러·설정 (T-005, REQ-PAL-004·006)

- `_run_general_alert_check()` — `scheduler/jobs.py:405-421`. 10분 주기 잡. `check_all_portfolio_alerts(session)` 호출 1줄 추가.
- `SUPPORTED_ALERT_TYPES` — `preferences.py:28-36`. 튜플에 `"portfolio_target_return"`·`"portfolio_mdd_breach"` 추가.

### 3.7 스키마 (T-002, REQ-PAL-001)

- 응답 스키마 패턴 — SPEC-030 `PerformanceSummaryResponse`(Pydantic v2, validator 없는 응답). 검증 필요 시 `model_validator(mode="after")`.

### 3.8 프론트엔드 (T-007)

- 패널 카드 레이아웃·async state — `BacktestPanel.js`·`PerformanceSummaryPanel.js`(loading/error/result 패턴).
- API 클라이언트 — `portfolio.{ts,js}`(`apiGetPerformanceSummary` 등 기존 함수 패턴, 토큰·query/body).

---

## 4. 리스크 분석 (Risk Analysis)

| 리스크 | 영향 | 완화책 |
|--------|------|--------|
| **성과 요약 조회 지연** | FDR 조회로 알림 점검 타임아웃 | NFR-002: SPEC-030 Redis 캐시(TTL 3600s) 재사용, `refresh=false`로 캐시 우선. portfolio_id별 1회 조회 |
| **성과 요약 조회 실패** | 알림 점검 불가 | NFR-004: 해당 포트폴리오 건너뜀, 예외 비전파(graceful), 다른 알림 점검 계속 |
| **멱등성 갭(portfolio_id 부재)** | notifications 테이블에 portfolio_id 컬럼 없음 | `krx_code` 필드에 `PORT_{portfolio_id}` 사용 + `ref_date` 일별 → 기존 UNIQUE 제약으로 일자별 1회 발송 보장(REQ-PAL-008) |
| **1회 발화 한계(re-arm 없음)** | 조건 변동 후 재도달 시 미발화 | 의도된 동작(범위 제외). 사용자가 알림 삭제·재생성으로 초기화. SPEC 제외 사항·UI에 명시 |
| **중복 알림 생성 시도** | 동일 (portfolio, type) 중복 | UNIQUE 제약 `uq_portfolio_alert_user_pf_type` + 409 응답(REQ-PAL-008) |
| **기준 기간 모호성** | 어느 기간 수익률/MDD로 평가? | §5.2: YTD(`periods[0]`) 고정. 사용자 선택 미제공(범위 제외) |
| **소유권 위반** | 타사용자 포트폴리오 알림 조작 | NFR-005: `get_portfolio_with_holdings` None → 404(403 아님, 코드베이스 관례) |
| **이메일/텔레그램 발송 실패** | 알림 발송 누락 | NFR-004: best-effort, 인박스 적재는 차단하지 않음. `is_channel_enabled_async` fail-open |

---

## 5. 검증 전략 (Test Strategy)

### 5.1 단위 테스트 (T-006)

- **조건 평가 순수 함수**:
  - `check_portfolio_return_alert`: 목표 도달(수익률 ≥ 목표) 발화, 미도달 비발화, `has_data=false` 비발화, `total_return_pct=None` 비발화.
  - `check_portfolio_mdd_alert`: 임계 초과(MDD ≤ 임계, 더 큰 낙폭) 발화, 미초과 비발화, 경계값(`MDD == 임계`) 발화, `has_data=false` 비발화.
- **오케스트레이션**(`check_all_portfolio_alerts`):
  - 발화 시 `is_triggered=true`·`triggered_at`·`triggered_message` 갱신.
  - notification INSERT 멱등성(`on_conflict_do_nothing`, `PORT_{id}` krx_code).
  - 이미 발화된 알림(`is_triggered=true`) 재점검 시 미발화(멱등).
  - `is_active=false` 알림 건너뜀.
  - 성과 조회 실패 시 예외 비전파(graceful).
  - 동일 포트폴리오 2개 알림 → 성과 요약 1회 조회(NFR-002).
- **채널 게이팅**: 이메일 비활성 시 이메일 미발송·인박스만(REQ-PAL-006).
- **CRUD 서비스**: 생성·목록·수정·삭제, 소유권 불일치 None/404, 중복 생성 409.
- **scipy 미사용 검증**: `portfolio_alerts.py` import 정적 검사.

### 5.2 인수 시나리오 매핑

acceptance.md §2 BDD 시나리오 1~8을 단위 테스트로 구현한다(라우터 통합 경로는 단위 테스트 내 의존성 모킹으로 커버). 통합 테스트는 선택적이며, 필요 시 `tests/integration/`에 추가한다.

### 5.3 커버리지 목표 (NFR-003)

`portfolio/portfolio_alerts.py` 서비스·순수 함수 85% 이상. `router.py` 추가분은 omit 대상 가능(pyproject `omit` 패턴 확인).

---

## 6. 구현 순서 요약

1. **M1**: T-001(마이그레이션·모델) → T-002(스키마).
2. **M2**: [RED 테스트] → T-003(순수 함수·오케스트레이션·CRUD) → T-004(라우터) → T-005(스케줄러·설정).
3. **M3**: T-006 GREEN 완료 + 커버리지 85% 달성.
4. **M4**: T-007 프론트엔드.
5. **M5**: T-008 MX 태그 검수.

각 단위 완료 후 진행 상황을 `progress.md`에 기록한다.
