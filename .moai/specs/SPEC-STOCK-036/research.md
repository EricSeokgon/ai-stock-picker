# SPEC-STOCK-036 리서치 — 포트폴리오 알림 확장

> 작성일: 2026-06-24 · 대상 브랜치: `feature/SPEC-STOCK-036`

## 1. 핵심 발견 — 포트폴리오 알림은 이미 구현됨 (SPEC-STOCK-031)

작업 지시서는 "포트폴리오 알림 시스템을 신규 구축"으로 기술하고, 신규
`portfolio_alert_rules`·`portfolio_alert_history` 테이블, 마이그레이션 0023, 6종
엔드포인트, 순수 함수 2종을 요구한다. 그러나 **코드베이스 조사 결과 포트폴리오
알림 인프라 전체가 SPEC-STOCK-031(commit `3d6cf97`)로 이미 존재**한다.

따라서 SPEC-036은 **신규 구축 SPEC이 아니라 재사용·확장 SPEC**으로 재정의한다.
(SPEC-020 → SPEC-023의 알림 유형 추가 재사용 패턴과 동일.)

### 1.1 이미 존재하는 자산 (재구현 금지)

| 자산 | 위치 | 비고 |
|------|------|------|
| 테이블 `portfolio_alerts` | 마이그 `0020_portfolio_alerts.py` | id, user_id, portfolio_id, alert_type(30), condition_value(Float), is_active, is_triggered, triggered_at, triggered_message, created_at + UNIQUE(user_id,portfolio_id,alert_type) |
| 모델 `PortfolioAlert` | `db/models.py:653` | — |
| 순수 함수 `check_portfolio_return_alert` | `portfolio/portfolio_alerts.py:34` | YTD 수익률 ≥ 목표 |
| 순수 함수 `check_portfolio_mdd_alert` | `portfolio/portfolio_alerts.py:60` | YTD MDD ≤ 임계(음수) |
| 오케스트레이션 `check_all_portfolio_alerts` | `portfolio/portfolio_alerts.py:93` | 활성·미발화 조회 → portfolio별 성과요약 1회 → 평가 → UPDATE + notifications INSERT(멱등) + 채널 발송 |
| CRUD 서비스 | `portfolio/portfolio_alerts.py:313~` | create/list/update/delete |
| 라우터 | `portfolio/router.py:295~` | POST/GET/PUT/DELETE `/portfolios/{id}/alerts[/{alert_id}]` (소유권 404) |
| 스키마 | `portfolio/schemas.py:339~` | `PortfolioAlertCreate/Update/Response` |
| 스케줄러 연동 | `scheduler/jobs.py:415` | `check_all_portfolio_alerts` 호출 |
| 테스트 | `tests/unit/test_portfolio_alerts.py` | — |

### 1.2 SPEC-031이 커버하지 않는 진짜 신규 영역 (= SPEC-036 범위)

작업 지시서가 요구한 알림 유형 중 SPEC-031에 **없는 것은 2종뿐**이다.

| 작업지시 요구 유형 | SPEC-031 존재 여부 | 결론 |
|---------------------|--------------------|------|
| (1) 총 수익률 임계 | 존재(`portfolio_target_return`) | 재사용·문서화만 |
| MDD 임계(부가) | 존재(`portfolio_mdd_breach`) | 재사용·문서화만 |
| (2) 개별 보유종목 수익률 임계 | **없음** | **신규 `holding_return`** |
| (3) 포트폴리오 평가액 임계(KRW) | **없음** | **신규 `portfolio_value_below`** |

## 2. 신규 2종에 필요한 데이터 소스 (모두 기존 코드 재사용)

- **포트폴리오 평가액**: `portfolio/service.py`의 보유종목 평가 로직이 종목별
  현재가 × 수량 합계(`current_value`)를 이미 산출. SPEC-036은 이 합계를 임계
  KRW와 비교.
- **개별 보유종목 수익률**: `get_portfolio_with_holdings`(`service.py:87`) +
  서비스의 holdings 파생 로직이 종목별 `return_pct`(round 2)를 이미 산출.
- 현재가 조회는 동기 `realtime/price_feed.py get_current_price` 및 service.py 내부
  `_get_current_price` 패턴을 따른다(신규 데이터 공급자 없음).

## 3. 모델 컬럼 제약 (RUN 단계 결정 사항)

- 개별 보유종목 알림은 **대상 종목 식별자**와 **방향(이상/이하)** 이 필요하나,
  현재 `PortfolioAlert`에는 `target_krx_code`·`condition_direction` 컬럼이 없다.
- 두 가지 후보: (A) `portfolio_alerts`에 nullable 컬럼 2개 추가(마이그 0023,
  down_rev=0022, 기존 행은 NULL → 하위 호환), (B) `condition_value` 부호/별도
  인코딩으로 우회. **하위 호환과 가독성을 위해 (A) nullable 컬럼 추가를 권장**하되
  최종 결정은 RUN에서 확정한다. (A) 채택 시에도 신규 테이블은 만들지 않는다.

## 4. 알림 이력 (history)

- 작업 지시서의 `portfolio_alert_history` 신규 테이블은 거부한다.
- 발화 이력은 **기존 `notifications` 테이블**(마이그 0014)이 진실 소스다.
  `check_all_portfolio_alerts`가 발화 시 `notifications`에 멱등 INSERT(krx_code=
  `PORT_{portfolio_id}`)하는 흐름이 이미 존재 → 이력 조회는 인박스 API 재사용.

## 5. 마이그레이션 현황

- 최신 마이그레이션 = `0022_portfolio_monthly_snapshots.py`.
- SPEC-036은 컬럼 추가가 필요한 경우에만 `0023`(down_rev=0022) 1건, 신규 테이블 없음.

## 6. 프런트엔드 패턴

- 기존 알림 UI는 NavBar 종 아이콘/배지·`Notifications` 페이지(SPEC-013)가 존재.
- 포트폴리오 알림 설정 UI는 `frontend/src/pages/Portfolio.*` + `api/portfolio.*`
  패턴을 따른다(신규 컴포넌트는 알림 규칙 폼/목록에 한정).

## 7. 신규 패턴 없음

본 SPEC은 SPEC-031/SPEC-027/SPEC-030의 기존 스타일(순수 함수 + 서비스 + 라우터 +
Redis 캐시 재사용 + 한국어 주석)을 그대로 따른다. scipy 금지(numpy + math만),
소유권 위반 404, DB-중립 upsert(SELECT-then-write) 제약을 유지한다.
