# SPEC-STOCK-036 — RUN 압축 참조 (spec-compact)

> 포트폴리오 알림 확장. **재사용 SPEC — SPEC-031 인프라 위에 알림 유형 2종 추가.**

## 핵심 제약사항

- scipy 등 신규 과학 라이브러리 금지 — numpy + math만.
- 소유권 위반 → HTTP 404 (403 아님).
- 순수 함수로 조건 평가(DB 없이 검증 가능).
- DB-중립 upsert(SELECT-then-write 또는 기존 멱등 INSERT 재사용).
- 코드 주석·커밋 메시지 한국어.
- 패키지 `backend/src/stock_picker/portfolio/`. 다음 마이그레이션 = 0023(현재 0022).
- **신규 테이블 금지.** 필요 시 `portfolio_alerts`에 nullable 컬럼만 추가.

## ⚠️ 재사용 (변경 금지)

- 테이블 `portfolio_alerts`(마이그 0020, SPEC-031), 모델 `PortfolioAlert`(models.py:653).
- `check_all_portfolio_alerts(session)`(portfolio_alerts.py:93) — 분기 추가만.
- `check_portfolio_return_alert`·`check_portfolio_mdd_alert`(기존 2유형) — 불변.
- 인박스 `notifications`(마이그 0014) — 발화 이력 진실 소스, 멱등 INSERT(krx_code=`PORT_{id}`,
  on_conflict_do_nothing `uq_notification_user_type_code_date`).
- 채널 게이팅 `is_channel_enabled_async`(SPEC-025), 이메일/텔레그램 best-effort.
- 평가 데이터: `service.py` 보유종목 평가 로직(종목별 `return_pct`, 합계 `current_value`),
  `get_portfolio_with_holdings`(service.py:87).
- 스케줄러 연동(jobs.py:415) — 신규 잡 없음.

## 신규 순수 함수 시그니처

```
check_portfolio_value_alert(alert, current_value_krw) -> tuple[bool, str]
check_holding_return_alert(alert, holding_return_pct) -> tuple[bool, str]
```

- 평가액: `current_value_krw <= alert.condition_value` → 발화.
- 종목 수익률: 방향 "above" → `pct >= value`, "below" → `pct <= value`.

## 신규 alert_type 값

- `portfolio_value_below` — 평가액(KRW) 이하 임계.
- `holding_return` — 개별 종목 수익률(%) 임계 + 방향(above/below).

## 스키마 (schemas.py)

- `PortfolioAlertCreate/Update/Response`의 `alert_type` Literal에 2값 추가.
- 종목 유형용 선택 필드: 대상 종목 식별자, 비교 방향.

## DB 설계 요약

- 기존 `portfolio_alerts` 재사용. 신규 컬럼(조건부, RUN 확정): `target_krx_code`(nullable),
  `condition_direction`(nullable, above/below). 마이그 0023 down_rev=0022. 기존 행 NULL.
- 별도 history 테이블 없음 → `notifications` 재사용.

## 엔드포인트

- 재사용: `POST/GET/PUT/DELETE /portfolios/{id}/alerts[/{alert_id}]`(유형 확장).
- 신규: `POST /portfolios/{id}/alerts/evaluate`(즉시 평가), `GET /portfolios/{id}/alerts/history`(이력).

## REQ 매핑

- 기능: REQ-PALX-001~012.
- NFR: REQ-PALX-NFR-001(라이브러리)·002(순수함수)·003(소유권404)·004(DB중립 멱등)·005(시세실패격리)·006(채널실패격리).
- AC: AC-1~15. 작업: T-001~T-008.

## @MX 태그 계획

- `check_all_portfolio_alerts`: 기존 `@MX:ANCHOR` 유지 + SPEC-036 참조 추가.
- 신규 순수 함수: `@MX:NOTE`. nullable 컬럼: `@MX:NOTE`(NULL=하위호환 의미).

## 프런트 파일 목록

- `frontend/src/pages/Portfolio.{js,tsx}` — 알림 규칙 폼/목록에 신규 2종 입력.
- `frontend/src/api/portfolio.{js,ts}` — 즉시 평가·이력 클라이언트.

## 제외

자동매매(영구)·신규 테이블(portfolio_alert_rules/history)·SPEC-031 기존 2유형 재구현·
신규 채널(웹푸시/SMS)·WebSocket 푸시·신규 스케줄러 잡·시계열/예측.
