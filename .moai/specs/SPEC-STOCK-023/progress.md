# SPEC-STOCK-023 — 진행 상황 (progress.md)

- **SPEC**: SPEC-STOCK-023 — 주식 알림 강화 (조건별 가격/거래량/추천 알림)
- **상태**: completed
- **작성일**: 2026-06-15
- **완료일**: 2026-06-15
- **개발 방법론**: TDD (RED-GREEN-REFACTOR)
- **마이그레이션**: 신규 없음 (최신 0017 유지)
- **커밋**: `259844f`

---

## 태스크 체크리스트

### M1 — 거래량 급증 알림 (`volume_spike`) — Priority High
- [x] T1-1: `prices.py` 30일 평균 거래량 + 당일 거래량 산출 함수 추가 (executor 격리, 기존 함수 불변)
- [x] T1-2: `general_alert_service._VALID_ALERT_TYPES`에 `volume_spike` 추가 + `AlertCreate` 검증 통과
- [x] T1-3: 순수 판정 함수 `check_volume_spike(alert, volume_data)` 구현 (평균 0 가드, 발동 메시지)
- [x] T1-4: `check_and_trigger_all_alerts`에 `volume_spike` 분기 + notifications 적재 + 채널 베스트에포트

### M2 — 추천 점수 변화 알림 (`rec_score_change`) — Priority High
- [x] T2-1: `rec_change.py`에 두 trade_date 공통 종목 `total_score` 변동 산출 로직 추가
- [x] T2-2: 임계값(0.2) 이상 변동 → 관심목록 보유자 `rec_score_change` 인박스 알림 생성
- [x] T2-3: 첫 실행(직전 날짜 없음)·중복 실행(UNIQUE) 안전 처리
- [x] T2-4: 파이프라인(`run_daily_pipeline`·`run_intraday_pipeline`) 연동 (예외 격리)

### M3 — 장중 시간 게이팅 — Priority Medium
- [x] T3-1: `_is_market_open(now_kst)` 게이트 헬퍼 (09:00~15:30 Asia/Seoul)
- [x] T3-2: 가격·거래량 알림 점검 루프 진입부 게이트 적용 (장외 시 외부 호출 생략)
- [x] T3-3: 환경 변수 토글 `ALERT_MARKET_HOURS_GATE` (기본 활성)

### M4 — 채널 일관성 + 검증 — Priority Medium
- [x] T4-1: 신규 type 인박스 알림이 기존 인박스 API에서 조회·읽음 처리 검증
- [x] T4-2: 채널 발송 실패 시 인박스 적재·루프 지속 동작 검증
- [x] T4-3: 신규 판정 함수 단위 테스트 + 점검 루프/게이팅 통합 테스트 (커버리지 85%+)
- [x] T4-4: 면책·자동매매 제외·신규 채널/마이그레이션 미추가 최종 확인

---

## 수용 기준 (Given-When-Then)

### AC-1 — volume_spike 알림 생성·조회 (REQ-023-001)
- **Given** 인증된 사용자
- **When** `POST /alerts`로 `alert_type="volume_spike"`, `condition_value=2.0` 알림을 생성하면
- **Then** 기존 `Alert` CRUD로 저장되고 `GET /alerts`에서 조회된다 (신규 컬럼·테이블 없음).

### AC-2 — volume_spike 발동 (REQ-023-003)
- **Given** 종목의 당일 거래량이 30일 평균의 2.5배인 `volume_spike` 알림(배수 2.0)
- **When** 알림 점검 루프가 평가하면
- **Then** 알림이 발동하고 type=`volume_spike` 인박스 알림(당일/평균/배수 메시지)이 적재된다.

### AC-3 — volume_spike 평균 0 가드 (REQ-023-005)
- **Given** 30일 평균 거래량이 0이거나 거래량 데이터가 없는 종목
- **When** `volume_spike` 알림을 평가하면
- **Then** 발동하지 않고 건너뛰며 서버 오류가 발생하지 않는다 (0 나누기 방지).

### AC-4 — rec_score_change 발동 (REQ-023-008, 009, 010)
- **Given** 관심목록에 종목 A를 보유한 사용자, A의 total_score가 직전 0.55 → 최신 0.80 (변동 +0.25)
- **When** 추천 재계산 후 점수 변동 감지가 실행되면
- **Then** 임계값 0.2 초과로 `rec_score_change` 인박스 알림(직전/현재/상승/변동량)이 생성된다.

### AC-5 — rec_score_change 첫 실행 안전 (REQ-023-011)
- **Given** 추천 trade_date가 1개뿐(첫 실행)
- **When** 점수 변동 감지가 실행되면
- **Then** 알림을 생성하지 않고 조용히 종료한다.

### AC-6 — rec_score_change 중복 멱등 (REQ-023-012)
- **Given** 동일 사용자·종목·ref_date의 `rec_score_change` 알림이 이미 존재
- **When** 장중 30분 재실행으로 같은 변동이 다시 감지되면
- **Then** UNIQUE 제약으로 중복 생성이 무시된다.

### AC-7 — 급등락 재사용 보존 (REQ-023-014)
- **Given** `surge_drop` 알림(±5%, either), 전일 대비 +6% 종목
- **When** 점검 루프가 평가하면
- **Then** 기존 `check_surge_drop` 로직으로 발동한다 (동작 변경 없음).

### AC-8 — 목표가/실시간 임계값 재사용 보존 (REQ-023-015, 016)
- **Given** `target_price` 알림(above, 목표가 70000), 현재가 71000 종목
- **When** 장중 점검 루프가 평가하면
- **Then** 기존 `check_target_price` 로직으로 발동한다 (WebSocket 틱 없이 주기 점검으로 충족).

### AC-9 — 장중 게이팅 (REQ-023-017, 018)
- **Given** 현재 시각이 16:00 KST (장 마감 후), 게이팅 활성
- **When** 가격·거래량 알림 점검 루프가 진입하면
- **Then** 외부 시세 호출 없이 0건을 반환하고 알림이 발동하지 않는다.

### AC-10 — 게이팅 토글 (REQ-023-019)
- **Given** `ALERT_MARKET_HOURS_GATE`가 비활성으로 설정됨
- **When** 장외 시간에 점검 루프가 실행되면
- **Then** 게이팅을 우회하여 정상 평가한다.

### AC-11 — 채널 실패 격리 (REQ-023-021)
- **Given** 텔레그램/이메일 발송이 실패하는 환경
- **When** `volume_spike` 알림이 발동하면
- **Then** 인박스 적재는 정상 수행되고 점검 루프가 계속된다.

### AC-12 — 인박스 API 호환 (REQ-023-022)
- **Given** `volume_spike`·`rec_score_change` 인박스 알림 존재
- **When** `GET /notifications`·unread-count·PATCH read를 호출하면
- **Then** 신규 type도 차별 없이 조회·읽음 처리된다.

### AC-13 — 하위 호환·마이그레이션 무추가 (REQ-023-023)
- **Given** SPEC-023 구현 완료
- **When** Alembic 마이그레이션 목록과 기존 알림 동작을 확인하면
- **Then** 최신 마이그레이션은 0017로 유지되고 SPEC-004·013·020 동작·데이터가 보존된다.

### AC-14 — 자동매매·신규채널 제외 (REQ-SAFE-002, REQ-023-020)
- **Given** 본 SPEC 구현
- **When** 코드·엔드포인트를 검토하면
- **Then** 매수/매도 주문·자동 매매·신규 채널(웹푸시/SMS/모바일 푸시)이 존재하지 않는다.

---

## 변경 이력
- 2026-06-15: SPEC 초안 작성 (spec/research/progress 3파일). 모든 태스크 pending.
- 2026-06-15: 구현 완료 (커밋 259844f). M1~M4 전 태스크 완료. 신규 테스트 16개 (test_volume_spike.py), 기존 test_general_alerts.py 패치. 총 575개 단위 테스트 통과.
