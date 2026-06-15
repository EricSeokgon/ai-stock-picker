# SPEC-STOCK-023 — 코드베이스 분석 (research.md)

요청 5종 시나리오를 기존 알림 인프라와 대조하여 **재사용 vs 신규**를 분류한 결과. 핵심 결론: 요청 5종 중 3종(급등락·목표가·실시간 임계값)은 이미 구현 완료, 진짜 신규는 거래량 급증·추천 점수 변화·장중 게이팅 3종.

---

## 1. 기존 알림 인프라 (재사용 대상)

### 1.1 알림 엔티티 — `Alert` (SPEC-020, 마이그 0017)
`backend/src/stock_picker/db/models.py:591`

```
alerts: id PK(Int), user_id FK CASCADE, krx_code, stock_name?,
        alert_type String(20), condition_value Float, condition_direction String(8)?,
        is_active, is_triggered, triggered_at?, triggered_message String(500)?, created_at
Index: ix_alerts_user_active(user_id, is_active)
```

- `alert_type`이 String(20) → **`volume_spike` 값 추가에 스키마 변경 불필요**.
- `condition_value`(Float) → `volume_spike`에서 거래량 배수로 재활용 가능.
- 마이그레이션 목록 최신 = `0017_alerts.py`. 신규 SPEC은 마이그 추가 불필요.

### 1.2 알림 점검 서비스 — `general_alert_service.py` (SPEC-020)
- `_VALID_ALERT_TYPES = {"target_price", "surge_drop", "ex_dividend"}` → `volume_spike` 추가 지점.
- 순수 판정 함수 패턴 확립됨: `check_target_price(alert, price_data)`, `check_surge_drop(alert, price_data)` — DB 비의존, `(triggered: bool, message: str)` 반환. **`check_volume_spike`도 동일 패턴으로 추가**.
- `check_and_trigger_all_alerts(session)`: 활성·미발동 알림 순회 → `get_stock_price_data` 1회 호출 → 유형별 분기 → `alerts` 업데이트(is_triggered=True) + `notifications` pg_insert(on_conflict_do_nothing, constraint `uq_notification_user_type_code_date`) + 이메일 베스트에포트. **`volume_spike` 분기를 이 사다리에 추가**.
- `build_notification_payload`: type_label_map에 `target_price/surge_drop/ex_dividend` 매핑 존재 → `volume_spike`·`rec_score_change` 라벨 추가 필요.
- `_try_send_alert_email`: 사용자 이메일 조회 미구현 상태(@MX:TODO, PRIORITY LOW) — 기존 한계, 본 SPEC에서 확대하지 않음.

### 1.3 시세 모듈 — `mapping/prices.py`
- `get_stock_price_data(krx_code)` → `{close_price, change_rate, volume}` 최신 1건(executor 격리, async).
- `_fetch_price(krx_code)` → 내부적으로 **30일 df를 가져오나 최신 1건만 반환**(`df.iloc[-1]`). 평균 거래량 산출에 필요한 원천 데이터가 이미 조회됨.
- `get_stock_price_history(krx_code, days)` → `{date, close}` 시계열(**volume 미포함**) → 거래량 평균에는 부적합.
- **신규 필요**: 30일 평균 거래량 + 당일 거래량을 함께 반환하는 함수(`_fetch_price` 패턴 재사용, df의 `Volume` 컬럼 평균). 기존 함수 시그니처는 보존.
- `change_rate`는 전일 대비 변동률(FinanceDataReader `Change`) → 급등락 임계값 비교에 그대로 사용 중.

### 1.4 추천 변동 감지 — `notifications/rec_change.py` (SPEC-013)
- `_get_latest_two_trade_dates(db)` → 최신 2개 trade_date(이미 점수 변동 비교에 필요한 두 날짜를 조회).
- `_get_rec_codes_for_date(db, date)` → 해당 날짜 추천 종목코드 집합(현재는 **종목코드만**, 점수 미포함) → 점수 변동에는 `total_score`도 함께 조회 필요.
- `check_rec_changes()`: 차집합으로 신규 진입(`rec_new`)·탈락(`rec_dropped`)만 감지. **점수 변동은 미구현** → 본 SPEC의 진짜 신규.
- `_get_users_watching(db, krx_code)` → 관심목록(WatchlistItem) 보유자 → `rec_score_change` 대상자로 재사용.
- `_insert_notification_safe(...)` → UNIQUE 충돌 무시 멱등 적재 → `rec_score_change` 적재에 재사용.
- 첫 실행 처리: `len(dates) < 2`면 조용히 종료 → 점수 변동도 동일 가드 적용.

### 1.5 인박스 — `Notification` (SPEC-013, 마이그 0014)
- `type` 컬럼 자유 문자열 + UNIQUE(user_id, type, krx_code, ref_date) → `volume_spike`·`rec_score_change` type 값 추가에 스키마 변경 불필요.
- 인박스 API(`inbox_router.py`): GET /notifications·unread-count·PATCH read/read-all → 신규 type도 동일하게 조회·읽음 처리됨(차별 없음).

### 1.6 추천 점수 — `Recommendation` (마이그 0009/0012)
`backend/src/stock_picker/db/models.py:157`
- `total_score Numeric(6,3)`, `base_score?`, `feedback_score?`, `trade_date`, `krx_code`, `rank`.
- 점수 변동 비교는 `(trade_date, krx_code) → total_score`를 두 날짜에서 조회해 차이 산출. 산식(SPEC-009) 변경 없이 **읽기 전용 참조**.

### 1.7 스케줄러 — `scheduler/jobs.py`
- `_run_general_alert_check` (`check_alerts`, IntervalTrigger 10분) → `check_and_trigger_all_alerts` 호출. **가격·거래량 알림 점검의 단일 진입점** → 장중 게이팅을 여기(또는 서비스 진입부)에 적용.
- `run_daily_pipeline`(06:00)·`run_intraday_pipeline`(09-15시 30분): 추천 재계산 직후 `check_rec_changes()` 예외 격리 호출 → **점수 변동 감지를 같은 지점에 연동**.
- `check_price_alerts`(5분, SPEC-004 watchlist_alerts 별도) → 본 SPEC 무관(변경 없음).
- **운영 결함 참고**: `setup_scheduler()`가 앱 기동 경로에서 호출되는지 SPEC-022가 lifespan 연동 수정 중 → 본 SPEC은 기존 잡에 얹으므로 그 수정에 의존(신규 잡 미추가).

### 1.8 채널
- 텔레그램: `telegram/notifier.py` `_send_message_sync(chat_id, msg)`.
- 이메일: `notifications/email_service.py`(`_get_smtp_config`, `send_price_alert_email`); SMTP 미설정 시 graceful skip.
- 인앱: `notifications` 테이블 + `inbox_router.py`.
- **신규 채널 없음** — 위 3개만 사용.

---

## 2. 요청 5종 시나리오 → 재사용/신규 매핑

| # | 요청 시나리오 | 상태 | 근거 |
|---|--------------|------|------|
| 1 | 급등/급락 5%+ | **재사용** | `surge_drop` 유형 + `check_surge_drop`(condition_value=%, direction either/above/below). `change_rate` 제공됨. |
| 2 | 거래량 2× 30일평균 | **신규** | `volume_spike` 유형 부재. 30일 평균 거래량 산출 함수 부재(history는 volume 미포함). check 함수 신규. |
| 3 | 추천 점수 0.2+ 변화 | **신규** | `rec_change.py`는 진입/탈락만 감지, 점수 델타 미구현. `Recommendation.total_score`로 산출 가능. |
| 4 | 목표가 도달 | **재사용** | `target_price` 유형 + `check_target_price`(close vs value, above/below). |
| 5 | 실시간 임계값 돌파 | **재사용(+게이팅)** | `target_price`가 장중 주기 점검으로 충족. WebSocket 틱 알림은 범위 밖. 장중 게이팅만 신규. |

---

## 3. 진짜 신규 작업 요약

1. **`volume_spike` 알림 유형**: `_VALID_ALERT_TYPES` 확장 + 30일 평균 거래량 산출 함수(prices.py) + `check_volume_spike` 순수 함수 + 점검 루프 분기.
2. **`rec_score_change` 감지**: `rec_change.py`에 두 날짜 공통 종목 `total_score` 델타 산출 + 임계값(0.2) 초과 시 관심목록 보유자 인박스 알림.
3. **장중 게이팅**: `_is_market_open` 게이트(09:00~15:30 KST) + 환경 변수 토글.

신규 DB 테이블·마이그레이션 없음(0017 유지). 신규 채널·신규 프론트 페이지·신규 스케줄러 잡 없음.

---

## 4. 위험 및 주의사항

- **거래량 데이터 신뢰성**: FinanceDataReader가 일부 종목·당일 거래량을 제공하지 못할 수 있음 → 평균 0/데이터 없음 가드 필수(REQ-023-005).
- **점수 변동 노이즈**: 임계값 0.2가 너무 낮으면 알림 폭주 가능 → 환경 변수/설정으로 임계값 조정 가능하게 설계 권장(어뷰징 방지는 범위 밖이나 임계값은 노출).
- **장중 게이팅과 테스트**: 게이팅이 활성이면 단위 테스트가 시간 의존 → `ALERT_MARKET_HOURS_GATE` 토글 또는 `now` 주입으로 테스트 격리.
- **루프 지연**: `volume_spike`가 종목당 30일 df 조회를 추가하므로, 알림 수 증가 시 점검 루프 지연 가능(기존 `@MX:WARN` 동일 한계). 종목당 1회 호출로 제한(REQ-023-026).
- **SPEC-022 스케줄러 연동 의존**: `check_alerts`·파이프라인이 실제로 기동되어야 본 SPEC 알림이 발동 → SPEC-022 lifespan 수정과 순서 의존.
