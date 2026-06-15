---
id: SPEC-STOCK-023
version: 0.1.0
status: draft
created: 2026-06-15
updated: 2026-06-15
author: ircp
priority: high
issue_number: null
---

# SPEC-STOCK-023: 주식 알림 강화 — 조건별 가격/거래량/추천 알림

## HISTORY

- 2026-06-15 (v0.1.0): 최초 작성. SPEC-STOCK-004(가격 알림)·013(인박스·추천 변동 알림)·020(사용자 정의 알림 3종: 목표가·급등락·배당락)이 구축한 알림 인프라 위에, **조건별 시장 신호 알림**을 강화한다. 요청 5종 시나리오 중 **(1)급등/급락, (4)목표가 도달, (5)실시간 임계값 돌파**는 이미 `alerts` 테이블의 `surge_drop`·`target_price` 유형으로 구현 완료 → 재사용·문서화. **진짜 신규 = (2)거래량 급증(`volume_spike` 유형 추가, 30일 평균 거래량 대비 배수)·(3)추천 점수 변화(`rec_score_change`, 직전 대비 total_score 변동 감지)·장중 시간 게이팅**. 신규 DB 테이블·마이그레이션 없음(0017 유지). 알림 채널은 기존 텔레그램·이메일·인앱 인박스만 사용. 자동 매매/주문은 영구 제외. 신규 프론트 페이지 없음(SPEC-007 알림 설정 페이지 재사용).

---

## 1. 시스템 개요

### 1.1 목적

SPEC-STOCK-004·013·020으로 가격 알림·인박스·사용자 정의 알림(목표가/급등락/배당락)을 완성한 위에, **특정 시장 조건에서 발동하는 강화 알림**을 추가한다. Phase 23은 다음을 추가/확장한다.

1. **거래량 급증 알림 (신규)**: `volume_spike` 알림 유형을 추가한다. 종목의 당일 거래량이 최근 30일 평균 거래량의 N배(기본 2.0배)를 초과하면 발동한다. 평균 거래량은 `prices.py`가 이미 가져오는 30일 OHLCV df에서 산출한다.
2. **추천 점수 변화 알림 (신규)**: 추천 파이프라인 재계산 시, 특정 종목의 `total_score`가 직전 추천 대비 임계값(기본 0.2) 이상 변동하면 관심목록 보유 사용자에게 인박스 알림을 생성한다. 기존 `rec_change.py`(신규 진입/탈락 감지) 옆에 점수 변동 감지를 추가한다.
3. **장중 시간 게이팅 (신규)**: 가격·거래량 기반 알림 점검은 한국 증시 개장 시간(09:00~15:30 KST)에만 발동하도록 게이팅한다. 장 마감 후의 중복·오발동을 방지한다.
4. **급등/급락·목표가·실시간 임계값 돌파 (재사용)**: 요청 시나리오 1·4·5는 기존 `surge_drop`·`target_price` 유형으로 이미 충족된다. 본 SPEC은 이를 재구현하지 않고, 동작을 문서화하고 장중 게이팅·채널 일관성만 보강한다.

### 1.2 타겟 사용자

| 사용자 그룹 | 특성 | Phase 23에서 추가되는 핵심 니즈 |
|------------|------|------------------------------|
| 모멘텀 추종 사용자 | 거래량 폭증을 매매 신호로 활용 | 거래량이 평균 대비 급증한 종목을 즉시 알림으로 포착 |
| 추천 추적 사용자 | 관심종목의 추천 강도 변화를 알고 싶음 | 추천 점수가 크게 오르내릴 때 알림 수신 |
| 능동 알림 사용자 | 장중에만 의미 있는 알림을 원함 | 개장 시간에만 가격·거래량 알림이 발동 |

### 1.3 핵심 가치 제안

- **신호 강화**: 단순 가격 임계값을 넘어 거래량·추천 점수 변화라는 추가 시장 신호를 알림화한다.
- **자산 재활용**: 이미 수집되는 30일 OHLCV(`prices.py`)·추천 점수 히스토리(`recommendations` 테이블)·알림 인프라(`alerts`/`notifications`/텔레그램/이메일)를 신규 외부 서비스 없이 가치로 전환한다.
- **노이즈 절감**: 장중 게이팅으로 무의미한 장외 시간 알림을 차단한다.
- **하위 호환**: 신규 알림 유형·알림 타입 값은 추가 전용이며, SPEC-004·013·020 동작과 기존 데이터를 보존한다. 신규 DB 테이블·마이그레이션 없음.
- **안전한 확장**: 가격/거래량 조회(FinanceDataReader) 실패 시 해당 알림만 건너뛰고 나머지 알림·기능은 정상 동작한다(graceful degradation).

### 1.4 기존 시스템과의 관계 (재정의 금지, 재사용·확장만)

다음은 이미 구현 완료된 자산이며 **본 SPEC에서 재정의하지 않고 재사용·확장**한다.

- **알림 엔티티 `Alert`**(`db/models.py`, 마이그 0017, SPEC-020): `id, user_id(FK CASCADE), krx_code, stock_name?, alert_type String(20), condition_value Float, condition_direction String(8)?, is_active, is_triggered, triggered_at?, triggered_message String(500)?, created_at`. 본 SPEC은 `alert_type`에 **`volume_spike` 값을 추가**하며 컬럼·테이블은 변경하지 않는다(스키마 변경 없음 → 마이그레이션 불필요).
- **알림 점검 루프**(`notifications/general_alert_service.py` `check_and_trigger_all_alerts`): 활성·미발동 알림을 순회하며 `target_price`(`check_target_price`)·`surge_drop`(`check_surge_drop`)을 평가하고 `notifications` 적재 + 이메일 베스트에포트를 수행한다. 본 SPEC은 여기에 **`volume_spike` 분기와 순수 판정 함수 `check_volume_spike`를 추가**한다.
- **시세 모듈**(`mapping/prices.py`): `get_stock_price_data()`는 `{close_price, change_rate, volume}` 최신 1건 반환, `_fetch_price()`는 30일 df를 가져온 뒤 최신 1건만 반환, `get_stock_price_history()`는 30일 `{date, close}` 시계열 반환(volume 미포함). 본 SPEC은 **30일 평균 거래량 산출 함수**를 추가한다(기존 함수 시그니처 변경 금지).
- **추천 변동 감지**(`notifications/rec_change.py` `check_rec_changes`): 최신 2개 `trade_date`의 추천 종목 집합 차집합으로 신규 진입/탈락만 감지(`rec_new`/`rec_dropped`). 본 SPEC은 같은 모듈에 **점수 변동 감지(`rec_score_change`)를 추가**하며 기존 차집합 로직은 변경하지 않는다.
- **인박스 테이블 `Notification`**(마이그 0014, SPEC-013): `user_id, type, krx_code, title, body, is_read, ref_date, related_alert_id, created_at, read_at` + UNIQUE(user_id, type, krx_code, ref_date). 본 SPEC은 `type`에 **`volume_spike`·`rec_score_change` 값을 추가**한다(스키마 변경 없음).
- **알림 채널**: 텔레그램(`telegram/notifier.py` `_send_message_sync`)·이메일(`notifications/email_service.py`)·인앱 인박스(`notifications` 테이블 + `inbox_router.py`). 본 SPEC은 신규 채널을 추가하지 않고 위 3개만 사용한다.
- **스케줄러**(`scheduler/jobs.py`): `_run_general_alert_check`(`check_alerts`, 10분 IntervalTrigger)가 `check_and_trigger_all_alerts`를 호출한다. `run_daily_pipeline`·`run_intraday_pipeline`이 추천 재계산 직후 `check_rec_changes`를 호출한다. 본 SPEC은 **신규 타이머를 추가하지 않고** 기존 잡에 게이팅·점수 변동 호출을 연동한다.
- **알림 라우터**(`notifications/general_alert_router.py`, prefix `/alerts`): POST/GET/PUT/DELETE + POST `/alerts/check`. 본 SPEC은 신규 라우터를 추가하지 않고 `volume_spike` 유형이 기존 CRUD·검증을 통과하도록 검증 집합만 확장한다.

---

## 2. 핵심 기능 요구사항 (EARS)

표기 규칙: **WHEN**(이벤트 구동), **WHILE**(상태 구동), **WHERE**(선택적 기능), **IF...THEN**(원치 않는 동작), **SHALL**(보편 요구).

### 2.1 거래량 급증 알림 — `volume_spike` (REQ-023-001~007) — Priority High

- **REQ-023-001 (Ubiquitous)**: the 시스템 **SHALL** 알림 유형 집합에 `volume_spike`를 추가하여, 사용자가 `POST /alerts`로 `alert_type="volume_spike"` 알림을 생성·수정·삭제·조회할 수 있게 한다(기존 `Alert` CRUD 재사용, 신규 컬럼·테이블 없음).
- **REQ-023-002 (Ubiquitous)**: the 시스템 **SHALL** `volume_spike` 알림의 `condition_value`를 거래량 배수 임계값(평균 대비, 기본 2.0)으로 해석한다.
- **REQ-023-003 (Event)**: **WHEN** 알림 점검 루프가 `volume_spike` 알림을 평가하면, the 시스템 **SHALL** 해당 종목의 당일 거래량을 최근 30일 평균 거래량과 비교하여, 당일 거래량 ≥ (평균 × `condition_value`)일 때 발동한다.
- **REQ-023-004 (Ubiquitous)**: the 시스템 **SHALL** 30일 평균 거래량을 `prices.py`가 이미 조회하는 30일 OHLCV df에서 산출하며, 동기 라이브러리(FinanceDataReader)를 executor 격리 패턴으로 호출하여 비동기 이벤트 루프를 차단하지 않는다.
- **REQ-023-005 (Unwanted)**: **IF** 30일 평균 거래량이 0이거나 거래량 데이터가 없으면, **THEN** the 시스템 **SHALL** 해당 알림을 발동하지 않고 건너뛰며(0으로 나누기 방지), 서버 오류를 발생시키지 않는다.
- **REQ-023-006 (Event)**: **WHEN** `volume_spike` 알림이 발동하면, the 시스템 **SHALL** 발동 메시지(당일 거래량·평균 거래량·배수 포함)를 `notifications` 테이블(type=`volume_spike`)에 적재하고, 기존 패턴(UNIQUE 제약으로 일자별 중복 무시)을 따른다.
- **REQ-023-007 (Ubiquitous)**: the 시스템 **SHALL** `volume_spike` 알림 발동 시 텔레그램·이메일을 베스트에포트로 발송하고(실패해도 예외 전파 없음), 인박스 적재는 채널 발송 성공 여부와 독립적으로 수행한다.

### 2.2 추천 점수 변화 알림 — `rec_score_change` (REQ-023-008~013) — Priority High

- **REQ-023-008 (Event)**: **WHEN** 추천 파이프라인 재계산이 완료되면, the 시스템 **SHALL** 최신 `trade_date`와 직전 `trade_date`의 동일 종목 `total_score`를 비교하여 변동량을 산출한다.
- **REQ-023-009 (Event)**: **WHEN** 한 종목의 `total_score` 변동량 절댓값이 임계값(기본 0.2) 이상이면, the 시스템 **SHALL** 해당 종목을 관심목록(`WatchlistItem`)에 보유한 사용자에게 `rec_score_change` 인박스 알림을 생성한다.
- **REQ-023-010 (Ubiquitous)**: the 시스템 **SHALL** `rec_score_change` 알림 본문에 직전 점수·현재 점수·변동 방향(상승/하락)·변동량을 포함한다.
- **REQ-023-011 (Unwanted)**: **IF** 비교 가능한 직전 `trade_date`가 없거나(첫 실행) 두 날짜 모두에 존재하는 종목이 없으면, **THEN** the 시스템 **SHALL** 알림을 생성하지 않고 조용히 종료한다(`check_rec_changes`의 첫 실행 처리와 동일 패턴).
- **REQ-023-012 (State)**: **WHILE** 동일 사용자·동일 종목·동일 `ref_date`(최신 trade_date)·동일 type의 알림이 이미 존재하는 동안, the 시스템 **SHALL** `notifications` UNIQUE 제약으로 중복 생성을 무시한다(장중 30분 재실행 멱등성).
- **REQ-023-013 (Event)**: **WHEN** 추천 파이프라인(`run_daily_pipeline`·`run_intraday_pipeline`)이 `check_rec_changes`를 호출하는 시점에, the 시스템 **SHALL** 점수 변동 감지도 함께 수행하며, 점수 변동 감지 실패가 파이프라인 진행을 중단시키지 않는다(예외 격리).

### 2.3 급등/급락·목표가·실시간 임계값 돌파 (재사용 문서화) (REQ-023-014~016) — Priority Medium

- **REQ-023-014 (Event)**: **WHEN** `surge_drop` 알림이 평가되면, the 시스템 **SHALL** 종목의 전일 대비 변동률(`change_rate`)을 `condition_value`(±%, 기본 5%)·`condition_direction`(above/below/either)과 비교하여 발동한다(기존 `check_surge_drop` 재사용, 본 SPEC에서 재구현하지 않음).
- **REQ-023-015 (Event)**: **WHEN** `target_price` 알림이 평가되면, the 시스템 **SHALL** 종목의 현재가(`close_price`)를 사용자 설정 목표가·방향과 비교하여 발동한다(기존 `check_target_price` 재사용). 본 SPEC은 이를 "실시간 임계값 돌파"(요청 시나리오 5)의 충족 수단으로 문서화한다.
- **REQ-023-016 (Ubiquitous) [HARD]**: the 시스템 **SHALL** "실시간"의 범위를 장중 주기 점검(기존 `check_alerts` 10분 주기, 일별 종가/변동률 스냅샷 기반)으로 정의하며, WebSocket 틱 단위 실시간 알림은 본 SPEC 범위에서 제외한다(§4 참조).

### 2.4 장중 시간 게이팅 (REQ-023-017~019) — Priority Medium

- **REQ-023-017 (State)**: **WHILE** 현재 시각이 한국 증시 개장 시간(09:00~15:30 KST) 밖인 동안, the 시스템 **SHALL** 가격·거래량 기반 알림 점검(`target_price`·`surge_drop`·`volume_spike`)을 발동시키지 않는다.
- **REQ-023-018 (Ubiquitous)**: the 시스템 **SHALL** 장중 게이팅을 알림 점검 루프 진입부에서 평가하여, 장외 시간에는 외부 시세 API 호출 자체를 생략한다(불필요한 호출·발동 방지).
- **REQ-023-019 (Where)**: **WHERE** 게이팅을 우회해야 하는 운영/테스트 상황이 있으면, the 시스템 **SHALL** 환경 변수 또는 설정으로 장중 게이팅을 비활성화할 수 있는 토글을 제공한다(기본값: 게이팅 활성).

### 2.5 알림 채널 일관성 (REQ-023-020~022) — Priority Medium

- **REQ-023-020 (Ubiquitous) [HARD]**: the 시스템 **SHALL** 모든 신규·기존 알림을 기존 3개 채널(텔레그램·이메일·인앱 인박스)로만 전달하며, 신규 채널(웹푸시·SMS·카카오톡·모바일 푸시)을 추가하지 않는다.
- **REQ-023-021 (Unwanted)**: **IF** 텔레그램 또는 이메일 발송이 실패하면, **THEN** the 시스템 **SHALL** 오류를 로그한 뒤 인박스 적재는 정상 수행하고 점검 루프를 계속한다(채널 장애가 알림 유실로 직결되지 않음).
- **REQ-023-022 (Ubiquitous)**: the 시스템 **SHALL** 신규 알림 유형(`volume_spike`·`rec_score_change`)의 인박스 알림이 기존 인박스 API(`GET /notifications`·unread-count·read 처리)에서 차별 없이 조회·읽음 처리되도록 한다.

### 2.6 비기능 요구사항 (REQ-023-023~027)

- **REQ-023-023 (Ubiquitous) [HARD]**: the 시스템 **SHALL** 신규 알림 유형·인박스 type 값을 추가 전용으로 정의하여 SPEC-004·013·020 동작과 기존 데이터의 하위 호환을 보장하며, **신규 DB 테이블·마이그레이션을 생성하지 않는다**(최신 마이그레이션 0017 유지).
- **REQ-023-024 (Ubiquitous) [HARD]**: the 시스템 **SHALL** FinanceDataReader·텔레그램·이메일 가용성과 무관하게 모든 기존 기능을 동작시킨다(graceful degradation).
- **REQ-023-025 (Ubiquitous)**: the 시스템 **SHALL** 알림 점검의 호출·발동·실패·게이팅 스킵을 구조화 로그로 남기되, 시크릿·민감정보를 로그에 포함하지 않는다.
- **REQ-023-026 (Ubiquitous)**: the 시스템 **SHALL** `volume_spike` 거래량 비교 시 종목당 시세 조회를 1회로 제한하고(루프 내 중복 호출 방지), 알림 수 증가에 따른 지연을 기존 `check_and_trigger_all_alerts`의 베스트에포트 패턴 범위 내에서 유지한다.
- **REQ-023-027 (Ubiquitous)**: the 시스템 **SHALL** 신규 판정 함수(`check_volume_spike`, 점수 변동 감지)를 DB 비의존 순수 함수로 분리하여 단위 테스트가 가능하도록 한다(기존 `check_target_price`·`check_surge_drop` 패턴 준수).

---

## 3. 면책 및 안전 (Disclaimer & Safety)

- **REQ-SAFE-001 (Ubiquitous) [HARD]**: the 시스템 **SHALL** 알림 메시지에 투자 책임 면책 고지 원칙을 유지하며, 알림을 매수/매도 권유로 표현하지 않는다(정보 제공 목적 명시).
- **REQ-SAFE-002 (Unwanted) [HARD]**: **IF** 어떤 알림 기능이 매수/매도 주문, 자동 매매, 수익 보장을 시도하면, **THEN** the 시스템 **SHALL** 이를 거부한다(영구 제외, §4 참조).

---

## 4. Exclusions (What NOT to Build)

본 SPEC 범위에서 **명시적으로 제외**하는 항목이다.

- **자동 매매·주문 실행 (영구 제외)**: 어떤 형태의 실제 매수/매도 주문, 증권사 API 연동, 자동 매매 로직도 구현하지 않는다. 본 시스템은 정보 제공 도구로만 유지된다.
- **신규 알림 채널**: 웹푸시·SMS·카카오톡·모바일 푸시(iOS/Android)·기타 외부 채널은 추가하지 않는다. 알림은 기존 텔레그램·이메일·인앱 인박스 3개 채널로만 전달한다.
- **WebSocket 틱 단위 실시간 알림**: "실시간 임계값 돌파"는 기존 장중 주기 점검(10분, 일별 종가/변동률 스냅샷)으로 충족한다. WebSocket 가격 피드(`realtime/`)와 연동한 틱 단위 즉시 알림은 범위 밖이다.
- **신규 DB 테이블·마이그레이션**: `volume_spike`는 기존 `alerts` 테이블, `rec_score_change`는 기존 `notifications` 테이블을 재사용한다. 신규 테이블·컬럼·마이그레이션을 만들지 않는다(0017 유지).
- **기존 알림 유형 재구현**: `target_price`(목표가)·`surge_drop`(급등락)은 SPEC-020에서 이미 구현 완료. 재구현·치환하지 않고 재사용·문서화만 한다.
- **신규 프론트엔드 페이지**: 알림 설정 UI는 기존 페이지(SPEC-007/020 알림 설정·SPEC-013 인박스 벨/배지)를 사용한다. 신규 React 페이지·라우트를 만들지 않는다. (프론트는 신규 `alert_type` 옵션 노출만 필요하며, 백엔드 범위 SPEC이므로 프론트 변경은 선택사항으로 둔다.)
- **알림 어뷰징 방지·중복 투표·레이트리밋**: 알림 생성·점검의 레이트리밋, 사용자별 알림 개수 상한 강화는 범위 밖이다.
- **추천 점수 변동의 추천 산식 반영**: 점수 변동은 **감지·알림**만 한다. 변동을 추천 점수 재계산에 피드백하는 로직은 범위 밖이다(SPEC-009 가중치 산식 변경 금지).
- **거래량 지표 고도화**: `volume_spike`는 30일 단순 평균 대비 배수만 판정한다. 거래량 가중 이동평균·OBV·기술적 거래량 지표는 범위 밖이다.
- **다국어화**: 알림 메시지·UI는 한국어만 다룬다.

---

## 5. 설계 결정 (Design Decisions)

### 5.1 `volume_spike`는 기존 `alerts` 테이블 재사용 (마이그레이션 없음)
- `Alert.alert_type`은 String(20)이므로 `volume_spike` 값 추가에 스키마 변경이 불필요하다. `condition_value`(Float)를 거래량 배수로, `condition_direction`은 미사용(또는 NULL)로 둔다.
- `general_alert_service._VALID_ALERT_TYPES`에 `volume_spike`를 추가하고, `AlertCreate.validate_alert_type` 검증을 통과시킨다.
- 점검 분기는 `check_and_trigger_all_alerts`의 `if alert.alert_type == ...` 사다리에 `volume_spike` 분기를 추가한다.

### 5.2 30일 평균 거래량 산출 (시세 함수 보존)
- `prices.py` `_fetch_price`는 30일 df를 가져오나 최신 1건만 반환한다. `get_stock_price_history`는 volume을 포함하지 않는다.
- 신규 함수 `get_avg_volume(krx_code, days=30)`(또는 점검부에서 사용할 헬퍼)을 `prices.py`에 추가하여, executor 격리로 30일 df의 평균 거래량과 당일 거래량을 함께 반환한다. 기존 `get_stock_price_data`·`get_stock_price_history`는 변경하지 않는다.
- 판정은 순수 함수 `check_volume_spike(alert, volume_data)`로 분리(평균 0 가드 포함).

### 5.3 점수 변동 감지는 `rec_change.py` 확장 (notifications 재사용)
- 기존 `check_rec_changes`가 최신 2개 `trade_date`를 이미 조회한다. 같은 두 날짜에서 **양쪽 모두 존재하는 종목**의 `total_score` 차이를 산출하는 `check_rec_score_changes`(또는 `check_rec_changes` 내 단계)를 추가한다.
- 알림 type=`rec_score_change`, `ref_date`=최신 trade_date로 `notifications` 적재 → 기존 UNIQUE(user_id,type,krx_code,ref_date)로 멱등성 확보.
- 대상 사용자는 기존 `_get_users_watching`(관심목록 보유자)를 재사용한다.

### 5.4 장중 게이팅 (신규 타이머 없음)
- 알림 점검 루프 진입부에 `_is_market_open(now_kst)` 게이트를 둔다(09:00~15:30 Asia/Seoul). 장외면 외부 호출 없이 0건 반환.
- 환경 변수 토글(예: `ALERT_MARKET_HOURS_GATE`, 기본 활성)로 테스트·운영 우회를 허용한다.
- 기존 `check_alerts`(10분)·파이프라인 호출 시점은 변경하지 않는다.

### 5.5 채널 일관성
- `volume_spike`·`rec_score_change` 발동 시 `notifications` 적재 + 텔레그램/이메일 베스트에포트는 `_trigger_alert`(가격 알림)·`check_and_trigger_all_alerts`(일반 알림)의 기존 패턴을 따른다. 채널 발송 실패는 인박스 적재와 독립적으로 처리한다.

---

## 6. 수용 기준 요약

상세 Given-When-Then 시나리오·태스크는 `progress.md`·아래 §7을 따른다. 핵심 게이트:

- `alert_type="volume_spike"` 알림이 기존 `Alert` CRUD로 생성·조회·삭제되고, 당일 거래량 ≥ 30일 평균 × 배수일 때 발동하며, 평균 0일 때 안전하게 건너뛴다.
- 추천 재계산 후 동일 종목 `total_score` 변동이 임계값(0.2) 이상이면 관심목록 보유자에게 `rec_score_change` 인박스 알림이 생성되고, 첫 실행·중복 실행에서 안전하다.
- `surge_drop`(급등락)·`target_price`(목표가/실시간 임계값) 알림 동작이 보존된다.
- 장외 시간에는 가격·거래량 알림이 발동하지 않으며, 게이팅 토글로 우회 가능하다.
- 모든 알림이 텔레그램·이메일·인앱 인박스로만 전달되고, 채널 실패가 인박스 적재를 막지 않는다.
- 신규 DB 테이블·마이그레이션이 추가되지 않고(0017 유지), 자동 매매·신규 채널은 제공되지 않는다.

---

## 7. 태스크 (Tasks)

### M1 — 거래량 급증 알림 (`volume_spike`)
- **T1-1**: `prices.py`에 30일 평균 거래량 + 당일 거래량 산출 함수 추가(executor 격리, 기존 함수 불변).
- **T1-2**: `general_alert_service.py` `_VALID_ALERT_TYPES`에 `volume_spike` 추가 + `AlertCreate` 검증 통과 확인.
- **T1-3**: 순수 판정 함수 `check_volume_spike(alert, volume_data)` 구현(평균 0 가드, 발동 메시지 생성).
- **T1-4**: `check_and_trigger_all_alerts`에 `volume_spike` 분기 + `notifications`(type=`volume_spike`) 적재 + 텔레그램/이메일 베스트에포트.

### M2 — 추천 점수 변화 알림 (`rec_score_change`)
- **T2-1**: `rec_change.py`에 양쪽 trade_date 공통 종목의 `total_score` 변동 산출 로직 추가.
- **T2-2**: 임계값(기본 0.2) 이상 변동 종목 → 관심목록 보유자에게 `rec_score_change` 인박스 알림 생성(`_insert_notification_safe` 재사용, 메시지에 직전/현재/방향/변동량).
- **T2-3**: 첫 실행(직전 날짜 없음)·중복 실행(UNIQUE) 안전 처리.
- **T2-4**: `run_daily_pipeline`·`run_intraday_pipeline`의 `check_rec_changes` 호출 지점에 점수 변동 감지 연동(예외 격리).

### M3 — 장중 시간 게이팅
- **T3-1**: `_is_market_open(now_kst)` 게이트 헬퍼(09:00~15:30 Asia/Seoul) 구현.
- **T3-2**: 가격·거래량 알림 점검 루프 진입부에 게이트 적용(장외 시 외부 호출 생략·0건 반환).
- **T3-3**: 환경 변수 토글(`ALERT_MARKET_HOURS_GATE`, 기본 활성) 추가.

### M4 — 채널 일관성 + 검증
- **T4-1**: `volume_spike`·`rec_score_change` 인박스 알림이 기존 인박스 API에서 조회·읽음 처리되는지 검증.
- **T4-2**: 채널 발송 실패(텔레그램/이메일) 시 인박스 적재·루프 지속 동작 검증.
- **T4-3**: 신규 판정 함수 단위 테스트 + 점검 루프/게이팅 통합 테스트(커버리지 85%+ 유지).
- **T4-4**: 면책·자동매매 제외·신규 채널 미추가·마이그레이션 미추가(0017 유지) 최종 확인.
