# SPEC-STOCK-020 진행 상황 (Progress)

- **SPEC**: SPEC-STOCK-020 — 알림·알림 설정 (Price Alert & Notification System, Phase 20)
- **상태**: DONE
- **생성일**: 2026-06-15
- **작성자**: ircp
- **개발 방법론**: TDD (RED-GREEN-REFACTOR) — quality.yaml 기준
- **마이그레이션 목표**: 0017 (`alerts` 테이블만, down_rev=0016, notifications 재생성 없음)

---

## 핵심 주의 사항 (RUN 시작 전 필독)

> **알림 인프라 상당 부분이 이미 존재한다 (SPEC-013 Phase H, SPEC-004 Phase F).**
> 본 SPEC은 **재사용·확장**이며, 아래는 절대 재구축 금지:
> - `notifications` 테이블 (마이그 0014) — 신규 생성 금지, 발동 알림은 이 테이블에 적재.
> - 인박스 엔드포인트 (`inbox_router.py`, `GET /notifications/`·`unread-count`·`PATCH {id}/read`·`read-all`) — 재사용.
> - `watchlist_alerts`·`/watchlist/alerts`·`check_price_alerts`·`_trigger_alert` — 불변(공존).
> - 프론트 NavBar 벨·배지·`Notifications.tsx`·`api/notifications.ts` — 재사용.
>
> **진짜 신규**: `surge_drop`·`ex_dividend` 알림 유형, 알림 수정(PUT), 통합 `alerts` 테이블/라우터/점검 잡.

---

## 마일스톤 진행

| 마일스톤 | 설명 | 상태 |
|----------|------|------|
| M1 | `Alert` 모델 + 마이그레이션 0017 + Alert 스키마 | ✅ 완료 |
| M2 | 알림 CRUD 서비스·라우터 (`/alerts`, 인증·소유권) | ✅ 완료 |
| M3 | 점검 로직 (target_price·surge_drop·ex_dividend, graceful skip) | ✅ 완료 |
| M4 | 발동→인박스 적재(기존 notifications) + 이메일 베스트에포트 | ✅ 완료 |
| M5 | `POST /alerts/check` + 스케줄러 잡 `check_alerts` | ✅ 완료 |
| M6 | 프론트 `/alerts` 페이지 + 라우트/링크 (벨 재사용) | ✅ 완료 |
| M7 | 테스트 & 품질 게이트 (커버리지 ≥85%, 회귀 보호) | ✅ 완료 |

---

## 결정된 설계 사실 (스코프 잠금)

- **PK**: Integer autoincrement (요청서 UUID 대신 코드베이스 규약 일치).
- **`alerts` 컬럼**: id, user_id(FK CASCADE), krx_code, stock_name?, alert_type(String(20)),
  condition_value(Float), condition_direction(String(8)?), is_active, is_triggered, triggered_at?,
  triggered_message(String(500)?), created_at.
- **알림 유형 평가**: target_price=close_price vs value(above/below), surge_drop=change_rate(%) vs
  value(above/below/either), ex_dividend=오늘==기준일-N일(기준일 미확보 시 미발동).
- **데이터 출처**: `mapping/prices.py get_stock_price_data`(시세) + SPEC-019 `portfolio/dividends.py`
  배당 조회(ex_dividend_date, Redis 캐시 재사용).
- **발동 알림 적재**: 기존 `notifications` 테이블, type ∈ {target_price, surge_drop, ex_dividend},
  ref_date=triggered_at.date()로 UNIQUE 멱등.
- **이메일**: `notifications/email_service.py` smtplib 재사용. env `SMTP_PASSWORD`(요청서 `SMTP_PASS` 아님).
- **점검**: `POST /alerts/check`(무인증) + 스케줄러 잡 `check_alerts`(IntervalTrigger 기본 10분, 예외 격리).

---

## 미해결 / RUN 확인 필요

- 신규 모듈 파일 위치: `notifications/general_alert_*.py` vs 신규 `alerts/` 패키지 — 기존 `notifications/`
  구조와의 정합성을 RUN에서 결정.
- `/alerts` 라우터와 기존 `/watchlist/alerts`(alert_router) 네이밍 혼동 방지 — prefix `/alerts`로 분리 확정.
- 점검 주기 설정 키(예: env `ALERT_CHECK_INTERVAL_MINUTES`) 도입 여부.

---

## 구현 결과 (2026-06-15)

- **백엔드 신규 테스트**: 23개 추가 (총 551개 통과, 5개 기존 실패 test_collectors.py 무관)
- **프론트엔드 신규 테스트**: 17개 추가 (총 217개 통과, 32개 파일)
- **ruff lint**: 신규 파일 모두 통과
- **신규 파일**: migration 0017, Alert 모델, general_alert_service.py, general_alert_router.py,
  scheduler/jobs.py(수정), api/main.py(수정), alerts.ts, Alerts.tsx, App.tsx(수정)

---

## 변경 이력

- 2026-06-15: SPEC 초안 작성, 상태 PLANNING. 기존 알림 인프라 중복 분석 완료(SPEC-013/004 재사용 확정).
- 2026-06-15: 구현 완료 (TDD M1-M7), 상태 DONE.
