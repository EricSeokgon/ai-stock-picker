---
name: project-stock-036
description: SPEC-STOCK-036 포트폴리오 알림 확장 — SPEC-031 인프라 재사용, 값/종목 임계 2종 신규
metadata:
  type: project
---

SPEC-STOCK-036 = 포트폴리오 알림 확장 (Portfolio Alert Extension). **재사용 SPEC, 신규 테이블·마이그레이션 없음(0022 유지).**

**⚠️ 핵심 충돌 발견 (2026-06-24):** 작업지시서는 "포트폴리오 알림 시스템을 신규 구축"으로 기술하며 신규 `portfolio_alert_rules`+`portfolio_alert_history` 테이블·마이그 0023·6개 엔드포인트를 요구했으나, **SPEC-STOCK-031이 이미 포트폴리오 알림 전체를 구현**(commit 3d6cf97):
- 테이블 `portfolio_alerts`(마이그 0020): id, user_id FK, portfolio_id FK, alert_type String(30), condition_value Float, is_active, is_triggered, triggered_at, triggered_message, created_at + UNIQUE(user_id,portfolio_id,alert_type)
- 모델 `PortfolioAlert`(models.py:653)
- 순수함수 `check_portfolio_return_alert`·`check_portfolio_mdd_alert`(portfolio_alerts.py) — performance.periods[0]=YTD 기준
- 오케스트레이션 `check_all_portfolio_alerts(session)` — 활성·미발화 조회→portfolio별 성과요약 1회→평가→portfolio_alerts UPDATE(is_triggered=True 1회발화)+notifications INSERT(krx_code=`PORT_{id}`, on_conflict_do_nothing uq_notification_user_type_code_date 멱등)+이메일/텔레그램 best-effort(is_channel_enabled_async 게이팅)
- 서비스 CRUD `create/list/update/delete_portfolio_alert`
- 라우터 `POST/GET/PUT/DELETE /portfolios/{id}/alerts[/{alert_id}]`(소유권 404)
- 스케줄러 연동(jobs.py:415 check_all_portfolio_alerts 호출)
- 스키마 `PortfolioAlertCreate/Update/Response`(alert_type Literal["portfolio_target_return","portfolio_mdd_breach"])
- 테스트 `tests/unit/test_portfolio_alerts.py`

**진짜 신규(SPEC-031 미커버 2종)**:
1. `portfolio_value_below` — 포트폴리오 현재 평가액이 임계 KRW 이하 (SPEC-031은 수익률%·MDD%만, 절대 KRW 없음). 데이터=service.py 보유종목 평가액 합계(current_value).
2. `holding_return` — 개별 보유종목 수익률(PnL%) 임계 도달 (SPEC-031은 포트폴리오 레벨만). 데이터=get_portfolio_with_holdings 파생 per-holding return_pct. condition_direction(above/below) 필요 → SPEC-031 PortfolioAlert에 condition_direction 컬럼 없음 → **하위호환 nullable 컬럼 추가 또는 condition_value 부호로 처리** 결정 필요(RUN에서). 종목 식별=신규 nullable `target_krx_code` 컬럼 또는 별도 처리.

**설계 결정(SPEC-020→023 재사용 패턴 적용)**:
- 신규 테이블·마이그 금지 → `portfolio_alerts.alert_type`에 값 2개 추가, 필요 컬럼은 nullable 추가 마이그(0023, down_rev=0022) 최소화. (RUN에서 컬럼 추가 vs condition_value 인코딩 최종결정)
- 신규 순수함수 `check_portfolio_value_alert`·`check_holding_return_alert`
- `check_all_portfolio_alerts`에 분기 2개 추가(기존 로직 불변)
- 스키마 Literal에 값 2개 추가
- 알림 이력=기존 `notifications` 테이블 재사용(별도 portfolio_alert_history 테이블 거부)
- 신규 엔드포인트 없음(기존 CRUD가 alert_type만 확장하면 동작) → 단, 작업지시의 `POST /alerts/evaluate` 수동트리거·`GET /alerts/history`는 신규 추가 가능
- REQ 접두사 `REQ-PALX-*`(SPEC-031 REQ-PAL-* 충돌회피)

**제외**: 자동매매(영구)·신규 portfolio_alert_rules/history 테이블·신규 마이그(가능하면)·SPEC-031 기존 2유형 재구현·신규 채널·WebSocket·notifications 재구현.

**파일 구조**: spec/plan/acceptance/spec-compact + research (작업지시 5파일). frontmatter 8필드 아님—작업지시는 6필드(id/version/status/created_at/priority/labels) 사용.
