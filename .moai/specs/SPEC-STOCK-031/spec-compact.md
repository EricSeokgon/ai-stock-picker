# SPEC-STOCK-031 Compact

> 포트폴리오 알림 강화(목표 수익률·MDD 임계값). 기존 알림 인프라(SPEC-020~025)·성과 요약(SPEC-030) 재사용. Run 단계용 압축본.

## 요구사항

REQ-PAL-001 (Ubiquitous): THE 시스템 SHALL 포트폴리오 알림 CRUD 엔드포인트를 제공한다(POST/GET/PUT/DELETE `/portfolios/{id}/alerts`, 인증·소유자).
REQ-PAL-002 (Event-driven): WHEN 활성 `portfolio_target_return` 평가 시 THEN YTD 기간(`periods[0]`) 총수익률 ≥ `condition_value`이면 1회 발화(멱등).
REQ-PAL-003 (Event-driven): WHEN 활성 `portfolio_mdd_breach` 평가 시 THEN YTD MDD(음수) ≤ `condition_value`(음수)이면 1회 발화(멱등).
REQ-PAL-004 (Ubiquitous): THE 시스템 SHALL 기존 10분 주기 잡(`_run_general_alert_check`)을 확장하여 `check_all_portfolio_alerts`를 함께 호출한다(신규 잡 없음).
REQ-PAL-005 (Event-driven): WHEN 알림 발화 시 THEN 인박스 → 이메일 → 텔레그램 발송(기존 파이프라인). 인박스 적재 후 이메일·텔레그램 best-effort.
REQ-PAL-006 (State-driven): WHILE 채널 비활성 동안 THE 시스템 SHALL `is_channel_enabled_async()`로 해당 채널 생략. 신규 타입 2종 `SUPPORTED_ALERT_TYPES`에 추가.
REQ-PAL-007 (Ubiquitous): THE 프론트엔드 SHALL Portfolio 페이지 `PortfolioAlertPanel`로 알림 설정·조회·삭제 제공.
REQ-PAL-008 (Unwanted): IF 동일 `(user_id, portfolio_id, alert_type)` 중복 생성 시 THEN `409 Conflict` 거부. 발화 멱등성은 `notifications` UNIQUE(`krx_code=PORT_{id}`, ref_date).

### NFR
NFR-001: scipy 금지(SPEC-030 재사용으로 자동 충족). NFR-002: 성과 요약 portfolio_id별 1회 조회(Redis 캐시 재사용). NFR-003: 커버리지 85%+. NFR-004: 성과 조회·발송 실패 graceful(예외 비전파). NFR-005: 소유권 불일치 404(403 아님, `get_portfolio_with_holdings`).

## 알림 조건 평가 (순수 함수, 기준 기간 YTD=periods[0])

```
check_portfolio_return_alert: has_data && total_return_pct >= condition_value → 발화
check_portfolio_mdd_alert:    has_data && mdd_pct <= condition_value(음수)    → 발화
```

## portfolio_alerts 테이블 스키마

```
id PK / user_id FK(users CASCADE) / portfolio_id FK(portfolios CASCADE)
alert_type VARCHAR(30)  -- 'portfolio_target_return' | 'portfolio_mdd_breach'
condition_value FLOAT   -- 목표 수익률 % (10.0) 또는 MDD 임계 % (-15.0)
is_active BOOL=true / is_triggered BOOL=false / triggered_at TZ / triggered_message VARCHAR(500) / created_at TZ
UNIQUE(user_id, portfolio_id, alert_type)  -- uq_portfolio_alert_user_pf_type
INDEX(user_id, is_active)                   -- ix_portfolio_alerts_user_active
```

## 인수 조건

### Scenario 1: 목표 수익률 알림 발화
Given: 활성 target_return 알림(condition=10.0). When: YTD 수익률 +12% 상태에서 점검. Then: 발화, is_triggered=true, 인박스 적재(krx_code=PORT_{id}).

### Scenario 2: MDD 임계값 알림 발화
Given: 활성 mdd_breach 알림(condition=-15.0). When: YTD MDD -16.5% 상태에서 점검. Then: 발화(-16.5<=-15.0), is_triggered=true, 인박스 적재.

### Scenario 3: 이미 발화된 알림(멱등)
Given: is_triggered=true. When: 재점검. Then: 평가 제외(WHERE is_triggered=false), 중복 미발송, notifications UNIQUE로 일자 중복 차단.

### Scenario 4: 타인 포트폴리오 알림 생성
Given: user_id != portfolio.user_id. When: POST `/portfolios/{other}/alerts`. Then: 404(코드베이스 관례, 403 아님).

### Scenario 5: 채널 비활성화(이메일 생략)
Given: target_return 이메일 비활성. When: 알림 발화. Then: 인박스 적재, 이메일 미발송(is_channel_enabled_async=False).

### Scenario 6: 비활성 알림 건너뜀
Given: is_active=false. When: 스케줄러 점검. Then: 평가 제외(WHERE is_active=true), 미발화.

### Scenario 7: 프론트엔드 알림 설정 패널
Given: Portfolio 페이지 로드. When: 알림 설정 영역 열기. Then: PortfolioAlertPanel 마운트, 설정 폼·목록·삭제 제공.

### Scenario 8: 중복 알림 생성 거부
Given: 동일 포트폴리오에 동일 타입 알림 존재. When: 재생성 시도. Then: UNIQUE 제약으로 `409 Conflict`, 중복 행 없음.

## 수정 파일 목록

- [NEW] backend/src/stock_picker/portfolio/portfolio_alerts.py — 조건 평가 순수 함수 + check_all_portfolio_alerts + CRUD 서비스
- [NEW] backend/alembic/versions/0020_portfolio_alerts.py — portfolio_alerts 테이블(down_revision=0019)
- [NEW] backend/tests/unit/test_portfolio_alerts.py — 단위 테스트(85%+)
- [NEW] frontend/src/components/PortfolioAlertPanel.js — 알림 설정/조회 패널
- [MODIFY] backend/src/stock_picker/db/models.py — PortfolioAlert ORM 모델 추가
- [MODIFY] backend/src/stock_picker/portfolio/schemas.py — PortfolioAlertCreate·Update·Response 추가
- [MODIFY] backend/src/stock_picker/portfolio/router.py — 알림 CRUD 엔드포인트 추가
- [MODIFY] backend/src/stock_picker/scheduler/jobs.py — _run_general_alert_check에 check_all_portfolio_alerts 호출 추가
- [MODIFY] backend/src/stock_picker/notifications/preferences.py — SUPPORTED_ALERT_TYPES에 2종 추가
- [MODIFY] backend/src/stock_picker/alerts/service.py — 신규 alert_type 상수 등록(존재 시)
- [MODIFY] frontend/src/api/portfolio.ts — 알림 CRUD API 클라이언트 추가
- [MODIFY] frontend/src/api/portfolio.js — 알림 CRUD API 클라이언트 추가
- [MODIFY] frontend/src/pages/Portfolio.tsx — PortfolioAlertPanel 통합
- [MODIFY] frontend/src/pages/Portfolio.js — PortfolioAlertPanel 통합
- [EXISTING] backend/src/stock_picker/portfolio/performance_summary.py — calculate_performance_summary 재사용(수정 없음, SPEC-030)
- [EXISTING] backend/src/stock_picker/notifications/general_alert_service.py — 발송·게이팅 패턴 참조(수정 없음)
- [EXISTING] backend/src/stock_picker/notifications/preferences.py(is_channel_enabled_async) — 채널 게이팅 재사용
- [EXISTING] backend/src/stock_picker/portfolio/service.py — get_portfolio_with_holdings 소유권 재사용

마이그레이션: 신규 1개(`0020_portfolio_alerts.py`). notifications/preferences 테이블 변경 없음(alert_type VARCHAR).

## 제외 사항 (What NOT to Build)

- 종목 단위 알림(stock alerts) 변경 없음 (SPEC-020~025 불변)
- 실시간 WebSocket 알림 (배치 스케줄러 10분 주기만)
- 포트폴리오당 동일 타입 복수 알림 (단일 alert per portfolio+type, UNIQUE)
- 성과 지표 재구현 (SPEC-030 performance_summary 재사용)
- 알림 재발화(re-arm)·반복 알림 (조건 도달 시 1회 발화)
- 기준 기간 사용자 선택 (YTD 고정)
- 알림 이력·통계 대시보드
- 자동 매매/주문 실행 (프로젝트 영구 제외)
