# Acceptance Criteria — SPEC-STOCK-013 알림·모니터링 시스템 (Phase 14)

Given-When-Then 시나리오. 모든 인박스 API는 JWT 인증을 전제로 한다.

---

## AC-1 알림 인박스 목록 조회 (REQ-NOTI-002)
- **Given** 사용자 A에게 알림 3건이 존재할 때
- **When** A가 `GET /notifications`를 호출하면
- **Then** 3건이 `created_at` 내림차순으로 반환된다.

## AC-2 미읽음 필터 (REQ-NOTI-003)
- **Given** A에게 읽음 2건·미읽음 1건이 있을 때
- **When** `GET /notifications?unread_only=true`를 호출하면
- **Then** 미읽음 1건만 반환된다.

## AC-3 미읽음 개수 (REQ-NOTI-004)
- **Given** A에게 미읽음 4건이 있을 때
- **When** `GET /notifications/unread-count`를 호출하면
- **Then** `{ "unread_count": 4 }`가 반환된다.

## AC-4 단건 읽음 처리 (REQ-NOTI-005)
- **Given** A의 미읽음 알림 id=10이 있을 때
- **When** `PATCH /notifications/10/read`를 호출하면
- **Then** 해당 알림 `is_read=true`·`read_at` 설정된 레코드가 반환되고, 이후 unread-count가 1 감소한다.

## AC-5 전체 읽음 처리 (REQ-NOTI-006)
- **Given** A의 미읽음 5건이 있을 때
- **When** `PATCH /notifications/read-all`을 호출하면
- **Then** `{ "updated": 5 }`가 반환되고 unread-count는 0이 된다.

## AC-6 타 사용자 알림 차단 (REQ-NOTI-007, REQ-NFR-004)
- **Given** 알림 id=20이 사용자 B 소유일 때
- **When** 사용자 A가 `PATCH /notifications/20/read` 또는 단건 조회를 시도하면
- **Then** `404 Not Found`가 반환되고 레코드는 변경되지 않는다.

## AC-7 limit 상한 (REQ-NOTI-008)
- **Given** A에게 알림 120건이 있을 때
- **When** `GET /notifications?limit=200`을 호출하면
- **Then** 최대 100건만 반환된다(상한 클램프).

---

## AC-8 가격 알림 발동 시 인박스 생성 (REQ-PA-001, REQ-PA-002)
- **Given** A의 활성 `WatchlistAlert`(목표가·방향)가 현재가 조건을 충족할 때
- **When** `check_price_alerts`가 실행되어 `_trigger_alert`가 호출되면
- **Then** A에게 `type='price_alert'`·해당 `krx_code`·`related_alert_id`·한국어(목표가/현재가/방향 포함) 알림 1건이 생성된다.

## AC-9 외부 채널 실패와 무관한 인박스 생성 (REQ-PA-003)
- **Given** A의 텔레그램/이메일 발송이 실패하는 상황에서 알림이 발동될 때
- **When** `_trigger_alert`가 실행되면
- **Then** 인앱 알림 레코드는 정상 생성된다.

## AC-10 인박스 생성 실패 격리 (REQ-PA-004)
- **Given** 알림 N건 중 1건의 인박스 쓰기가 실패할 때
- **When** `check_price_alerts`가 실행되면
- **Then** 에러가 로깅되고 나머지 알림 처리가 계속된다.

---

## AC-11 추천 신규 진입 알림 (REQ-RC-002, REQ-RC-007)
- **Given** 종목 X가 A의 관심목록에 있고, X가 현재 trade_date 추천에는 있으나 직전 trade_date 추천에는 없었을 때
- **When** 추천 변경 감지가 실행되면
- **Then** A에게 `type='rec_new'`·`krx_code=X`·`ref_date=현재 trade_date`·한국어 알림 1건이 생성된다.

## AC-12 추천 이탈 알림 (REQ-RC-003)
- **Given** 종목 Y가 A의 관심목록에 있고, Y가 직전 trade_date 추천에는 있었으나 현재 trade_date 추천에는 없을 때
- **When** 추천 변경 감지가 실행되면
- **Then** A에게 `type='rec_dropped'`·`krx_code=Y` 알림 1건이 생성된다.

## AC-13 장중 재실행 멱등성 (REQ-RC-005)
- **Given** AC-11로 X의 `rec_new` 알림이 이미 생성된 상태에서
- **When** 같은 trade_date에 장중 파이프라인이 추천 변경 감지를 재실행하면
- **Then** 동일 `(user_id, type='rec_new', krx_code=X, ref_date)` 알림이 추가 생성되지 않는다(중복 0건).

## AC-14 첫 실행 처리 (REQ-RC-006)
- **Given** `recommendations`에 직전 distinct trade_date가 존재하지 않을 때(최초 실행)
- **When** 추천 변경 감지가 실행되면
- **Then** `rec_dropped` 알림은 생성되지 않는다(예외 없이 종료).

## AC-15 관심목록 외 종목 무시 (REQ-RC-002, REQ-RC-003)
- **Given** 추천에서 진입/이탈한 종목이 어떤 사용자의 관심목록에도 없을 때
- **When** 추천 변경 감지가 실행되면
- **Then** 해당 종목에 대한 알림은 생성되지 않는다.

---

## AC-16 파이프라인 연동 & 격리 (REQ-MON-001, REQ-MON-002)
- **Given** `run_daily_pipeline`이 정상 실행되고 추천 변경 감지가 예외를 던지는 상황일 때
- **When** 파이프라인이 실행되면
- **Then** 감지 예외는 로깅되고 파이프라인 전체는 실패하지 않는다(추천 적재는 보존).

## AC-17 신규 타이머 미도입 (REQ-MON-003)
- **Given** 스케줄러 설정을 점검할 때
- **When** `setup_scheduler()`가 등록한 잡을 확인하면
- **Then** 추천 변경 감지 전용 신규 타이머 잡은 없으며, 감지는 기존 추천 파이프라인 내부에서만 호출된다.

---

## AC-18 NavBar 미읽음 배지 (REQ-FE-001, REQ-FE-004)
- **Given** 로그인한 사용자에게 미읽음 알림이 있을 때
- **When** 임의 페이지를 렌더링하면
- **Then** NavBar에 종 아이콘과 미읽음 개수 배지가 표시된다. 비로그인 시 종 아이콘은 렌더링되지 않는다.

## AC-19 인박스 읽음 상호작용 (REQ-FE-002, REQ-FE-003)
- **Given** 인박스에 미읽음 알림이 있을 때
- **When** 사용자가 알림을 클릭하거나 "모두 읽음"을 누르면
- **Then** 해당 read 엔드포인트가 호출되고 배지 카운트가 갱신된다.

---

## AC-20 품질 게이트 (REQ-NFR-002, REQ-NFR-003)
- **Given** 구현이 완료되었을 때
- **When** `ruff check` + `pytest --cov-fail-under=85`와 frontend `npm run lint`·`npm run build`를 실행하면
- **Then** 모두 통과하고, 알림 본문·주석은 한국어, 식별자·EARS 키워드는 영어로 작성되어 있다.

---

## Definition of Done
- [ ] AC-1 ~ AC-20 전부 충족
- [ ] 마이그레이션 0014 적용·롤백 검증
- [ ] 기존 관심목록·가격 알림 CRUD 동작 회귀 없음
- [ ] 신규 알림 채널 미도입(텔레그램·이메일·인앱만), 자동 매매 미포함
- [ ] progress.md 상태 갱신
