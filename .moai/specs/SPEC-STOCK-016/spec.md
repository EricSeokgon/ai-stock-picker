---
id: SPEC-STOCK-016
version: 0.1.0
status: draft
created: 2026-06-12
updated: 2026-06-12
author: ircp
priority: medium
issue_number: null
---

# SPEC-STOCK-016 — 실시간 주가 스트리밍 (Real-time Stock Price Streaming)

## HISTORY

- 2026-06-12 (v0.1.0): 초안 작성. Phase 15 멀티플렉스 WebSocket 실시간 시세 스트리밍. SPEC-003(단일 종목 `/ws/prices/{krx_code}`)의 확장으로, 단일 연결에서 다수 종목을 구독/해지하는 멀티플렉스 스트림과 Dashboard 라이브 시세, 가격 알림 인박스 연동을 추가한다.

---

## 1. 개요 (Overview)

### 1.1 배경

이 시스템에는 **이미 단일 종목 실시간 시세 스트리밍이 존재**한다(SPEC-STOCK-003, Phase 4).

- 백엔드: `realtime/ws_router.py`의 `GET ws /ws/prices/{krx_code}` — 종목 1개당 WebSocket 연결 1개, 10초 주기 폴링, JSON `{krx_code, price, change_pct, timestamp}` push.
- 백엔드: `realtime/price_feed.py`의 동기 함수 `get_current_price(krx_code)` — Redis 캐시(키 `price:{krx_code}`, TTL 60초) 우선, 미스 시 FinanceDataReader 폴백.
- 프론트: `hooks/useLivePrice.ts`(단일 종목 구독 훅) + `components/LivePriceBadge.tsx`(가격·등락률 배지). 현재 Watchlist·Portfolio 페이지에서 종목별로 각각 1개 연결을 생성.

문제점:
- 관심목록·포트폴리오·대시보드에 N개 종목이 있으면 **N개의 WebSocket 연결**이 생긴다(브라우저 동시 연결 한계·서버 부하).
- **Dashboard(메인 `/` 페이지, `App.tsx` 내 `Dashboard()` 컴포넌트)는 라이브 시세를 전혀 사용하지 않는다** — 추천 목록이 정적으로만 표시되며 수동 새로고침이 필요하다.
- 실시간 가격 변동이 **가격 알림(`watchlist_alerts`)을 즉시 발동시키지 못한다** — 현재 알림 발동은 스케줄러 `check_price_alerts`(5분 주기)에만 의존.

### 1.2 목표

단일 연결로 **여러 종목을 동시에 구독/해지**하는 멀티플렉스 WebSocket 스트림(`/ws/prices`)을 추가하고, Dashboard 추천 목록과 Watchlist에 자동 갱신 라이브 시세를 연결하며, 실시간 가격 갱신이 활성 가격 알림 임계값을 넘으면 **기존 인앱 알림 인박스(SPEC-STOCK-013/014 `notifications` 테이블)에 알림을 생성**한다.

기존 단일 종목 엔드포인트 `/ws/prices/{krx_code}`는 **무중단으로 유지**되며, 본 SPEC은 이를 대체하지 않고 멀티플렉스 경로를 추가한다.

### 1.3 아키텍처 (WebSocket 스트리밍)

```
[브라우저 단일 연결]                       [FastAPI 단일 프로세스]
  useLivePrices(["005930","000660"])
        │  ws /ws/prices                      ┌─────────────────────────────┐
        ├── subscribe {symbols:[...]} ───────▶│ ConnectionManager           │
        │                                     │  - 연결별 구독 심볼 집합     │
        │◀── subscribed {symbols:[...]} ──────│  - 심볼별 구독자 역색인      │
        │                                     └──────────────┬──────────────┘
        │                                                    │ 브로드캐스트 루프(주기 폴링)
        │◀── price {krx_code,price,...} ──────────┐          ▼
        │◀── price {krx_code,price,...} ──────────┤  get_current_price(심볼)  ← Redis 캐시 / FDR
        │                                         │  (또는 REALTIME_PRICE_MOCK 모킹)
        ├── unsubscribe {symbols:[...]} ─────────▶│          │
        │                                         │          ▼ 알림 평가 패스
        └── (연결 종료) ──────────────────────────┘  watchlist_alerts 임계 도달 →
                                                     notifications 인박스 insert (멱등)
```

설계 원칙:
- **구독 레지스트리는 인메모리**(프로세스 1개 기준). DB 스키마 변경 없음.
- 가격 출처는 **기존 `get_current_price` 재사용**(신규 데이터소스 없음). 개발용 모킹 모드 추가.
- 알림 발동은 **서버 측 DB 기반**(스트림은 익명·공개 시세, 인증 불필요).

---

## 2. 데이터 모델 (DB Schema)

### 2.1 DB 변경 없음

- 본 SPEC은 **신규 테이블·컬럼·마이그레이션을 추가하지 않는다**. 최신 Alembic 리비전은 `0014`로 유지된다.
- 구독 상태는 **WebSocket 연결 수명 동안만 유효한 인메모리 레지스트리**(`ConnectionManager`)로 관리한다. 영속화하지 않는다.

### 2.2 재사용 테이블

- `watchlist_alerts` (모델: `WatchlistAlert`): `krx_code`, `target_price`, `direction`("above"/"below"), `is_active`, `triggered_at`. 알림 평가에 사용(재정의 금지).
- `notifications` (모델: `Notification`): 알림 인박스. `type`은 기존 값 `price_alert` 재사용. UNIQUE 제약 `uq_notification_user_type_code_date(user_id, type, krx_code, ref_date)`로 중복 방지.

---

## 3. API 설계 (Message Protocol)

### 3.1 멀티플렉스 WebSocket 엔드포인트

```
ws /ws/prices            ← 신규 (멀티플렉스, 익명/공개 시세)
ws /ws/prices/{krx_code} ← 기존 SPEC-003 (단일 종목, 무중단 유지)
```

### 3.2 JSON 메시지 프로토콜

**클라이언트 → 서버:**

```json
{"action": "subscribe",   "symbols": ["005930", "000660"]}
{"action": "unsubscribe", "symbols": ["000660"]}
```

**서버 → 클라이언트:**

```json
{"type": "subscribed",   "symbols": ["005930", "000660"]}
{"type": "unsubscribed", "symbols": ["000660"]}
{"type": "price", "krx_code": "005930", "price": 71200.0, "change_pct": 1.42, "timestamp": "2026-06-12T10:31:00"}
{"type": "error", "message": "종목 코드 999999를 찾을 수 없습니다."}
```

규칙:
- `subscribe` 수신 즉시 각 유효 심볼의 **현재가 1건을 즉시 push**한 뒤, 이후 주기마다 갱신을 push한다.
- 유효하지 않은 심볼은 해당 심볼에 한해 `error` 메시지를 1회 보내고, 나머지 유효 심볼 구독은 정상 처리한다(연결 유지).
- 미지원 `action`·잘못된 JSON은 `error` 메시지로 응답하되 연결은 유지한다.

---

## 4. 프론트엔드 (Frontend)

### 4.1 신규/수정 구성요소

- `hooks/useLivePrices.ts` — **복수형 신규 훅**. 심볼 배열을 받아 단일 WebSocket 연결로 멀티 종목 시세를 구독하고 `Record<krxCode, LivePrice>`를 반환. 기존 단수형 `useLivePrice.ts`는 보존(소규모 단일 종목용).
- `components/LivePriceBadge.tsx` — 멀티플렉스 맵에서 가격을 주입받는 변형(prop으로 `LivePrice` 직접 수신) 지원. 기존 단일 종목 사용처 호환 유지.
- `App.tsx`의 `Dashboard()` — 추천(`RecommendationList`)·ETF(`EtfRecommendationList`) 목록 종목들을 `useLivePrices`로 일괄 구독해 라이브 시세를 표시.
- `pages/Watchlist.tsx` — 종목별 N개 연결을 `useLivePrices` 단일 연결로 마이그레이션(기능 동일, 연결 수 감소).

### 4.2 폴백

- WebSocket 연결 실패·미지원 시 기존 REST 가격 조회로 **graceful degradation**(자동 갱신은 멈추되 마지막 값·정적 표시는 유지).

---

## 5. 요구사항 (EARS Requirements)

> EARS 키워드(WHEN/WHILE/WHERE/IF...THEN/SHALL)와 코드·식별자만 영어로 작성한다.
>
> REQ 접두사 주의: SPEC-003이 이미 `REQ-WS-*`·`REQ-FE-*`를 사용했다. 충돌을 피하기 위해 본 SPEC은 멀티플렉스 전용 접두사 `REQ-WSM-*`(WebSocket Multiplex)·`REQ-FEM-*`(Frontend Multiplex)를 사용하고, 그 외 `REQ-SUB-*`·`REQ-RT-*`·`REQ-ALERT-*`·`REQ-NFR-*`를 사용한다.

### 5.1 멀티플렉스 WebSocket (REQ-WSM-*)

- REQ-WSM-001 (Event-Driven): WHEN a client opens a WebSocket connection to `/ws/prices`, the system SHALL accept the connection without requiring authentication.
- REQ-WSM-002 (Event-Driven): WHEN a `subscribe` message with valid `symbols` is received, the system SHALL immediately push one current price message per valid symbol.
- REQ-WSM-003 (State-Driven): WHILE a connection holds active subscriptions, the system SHALL push an updated `price` message for each subscribed symbol every polling interval.
- REQ-WSM-004 (Event-Driven): WHEN an `unsubscribe` message is received, the system SHALL remove the listed symbols from that connection's subscription set and stop pushing their updates.
- REQ-WSM-005 (Event-Driven): WHEN a WebSocket connection is closed or disconnected, the system SHALL release that connection's subscriptions and clean up the in-memory registry.
- REQ-WSM-006 (Unwanted): IF a received message is malformed JSON or has an unsupported `action`, THEN the system SHALL send an `error` message and SHALL keep the connection open.
- REQ-WSM-007 (Ubiquitous): The system SHALL keep the existing single-symbol endpoint `/ws/prices/{krx_code}` operational and unchanged.

### 5.2 구독 관리 (REQ-SUB-*)

- REQ-SUB-001 (Ubiquitous): The system SHALL maintain an in-memory subscription registry mapping each connection to its subscribed symbol set.
- REQ-SUB-002 (Ubiquitous): The system SHALL maintain a reverse index mapping each symbol to the set of connections subscribed to it, so a fetched price is fanned out to all interested connections.
- REQ-SUB-003 (Event-Driven): WHEN the same symbol is requested by multiple connections, the system SHALL fetch the price once per polling interval and broadcast it to all subscribers.
- REQ-SUB-004 (Unwanted): IF a `subscribe` message contains a symbol that has no resolvable price data, THEN the system SHALL send an `error` for that symbol only and SHALL still subscribe the remaining valid symbols.
- REQ-SUB-005 (State-Driven): WHILE no connection subscribes to a symbol, the system SHALL NOT fetch that symbol's price.

### 5.3 가격 폴링/모킹 (REQ-RT-*)

- REQ-RT-001 (Ubiquitous): The price polling loop SHALL reuse the existing `get_current_price(krx_code)` function (Redis cache + FinanceDataReader) as the production price source.
- REQ-RT-002 (Optional): WHERE the environment variable `REALTIME_PRICE_MOCK` is enabled, the system SHALL return deterministic mock prices instead of calling the external data source, so development works without market hours or network access.
- REQ-RT-003 (Unwanted): IF a price fetch fails for a symbol in a polling cycle, THEN the system SHALL skip that symbol for the cycle, log the failure, and retry on the next cycle without dropping the connection.
- REQ-RT-004 (Ubiquitous): The system SHALL NOT introduce any new paid or external market-data source beyond the existing FinanceDataReader path.

### 5.4 가격 알림 연동 (REQ-ALERT-*)

- REQ-ALERT-001 (Event-Driven): WHEN a polling cycle produces a fresh price for a symbol, the system SHALL evaluate active `watchlist_alerts` rows for that symbol against the alert `direction` and `target_price`.
- REQ-ALERT-002 (Event-Driven): WHEN an active alert's threshold condition is satisfied, the system SHALL create a `price_alert` notification in the existing `notifications` inbox for the alert's owning user.
- REQ-ALERT-003 (Ubiquitous): The system SHALL reuse the existing idempotent notification insert (UNIQUE `uq_notification_user_type_code_date`) so repeated cycles do not create duplicate alerts.
- REQ-ALERT-004 (State-Driven): WHILE an alert has already been triggered (`is_active = False` or `triggered_at` set), the system SHALL NOT re-trigger it from the streaming loop.
- REQ-ALERT-005 (Unwanted): IF notification creation fails, THEN the system SHALL log the error and SHALL continue broadcasting prices to clients (alert failure must not break the price stream).

### 5.5 프론트엔드 멀티플렉스 (REQ-FEM-*)

- REQ-FEM-001 (Ubiquitous): The frontend SHALL provide a `useLivePrices(symbols)` hook that opens a single WebSocket connection and returns a map of `krx_code` to its latest live price.
- REQ-FEM-002 (Event-Driven): WHEN the `symbols` array changes, the hook SHALL send `subscribe`/`unsubscribe` messages to reconcile the connection's subscription set without reopening the connection.
- REQ-FEM-003 (Event-Driven): WHEN the Dashboard renders recommendation and ETF lists, the frontend SHALL subscribe to those symbols and display auto-updating live prices without manual refresh.
- REQ-FEM-004 (State-Driven): WHILE the Watchlist page is open, the frontend SHALL display live prices for all watchlist items through one multiplexed connection instead of one connection per item.
- REQ-FEM-005 (Unwanted): IF the WebSocket is unavailable or disconnects, THEN the frontend SHALL degrade gracefully by retaining the last known values and SHALL NOT crash the page.
- REQ-FEM-006 (Ubiquitous): The frontend SHALL keep existing REST-based price/recommendation polling patterns unchanged as the fallback path.

### 5.6 비기능 요구사항 (REQ-NFR-*)

- REQ-NFR-001 (Ubiquitous): The subscription registry and broadcast loop SHALL operate within a single uvicorn process; multi-process broadcast via Redis pub/sub is out of scope (documented as a future scaling path).
- REQ-NFR-002 (Unwanted): IF a client connection is dead or its send buffer is broken, THEN the system SHALL drop that connection from the registry to prevent backpressure on other clients.
- REQ-NFR-003 (Ubiquitous): The polling interval SHALL be configurable and default to the existing 10-second cadence used by the single-symbol endpoint.
- REQ-NFR-004 (Ubiquitous): The streaming WebSocket SHALL carry only public market data and SHALL NOT expose any user-specific data over the anonymous connection.
- REQ-NFR-005 (Ubiquitous): Backend changes SHALL pass `ruff check` and maintain test coverage at or above the project floor (`fail_under = 85`); frontend changes SHALL pass lint, `npx vitest run`, and `tsc` build.

---

## 6. 핵심 설계 결정 (Key Design Decisions)

1. **연결 인증**: 시세는 공개 데이터이므로 멀티플렉스 스트림은 **익명(무인증)** 유지(기존 단일 종목 엔드포인트와 동일, 무중단). 가격 알림은 **서버 측 DB 기반**으로 발동되어 사용자별 인박스에 적재되므로 WebSocket 토큰 인증이 불필요하다. (대안: 쿼리 파라미터 토큰 `?token=...` — 본 SPEC 범위 밖.)
2. **가격 출처**: 기존 `get_current_price`(Redis 캐시 + FinanceDataReader)를 재사용. 개발용 `REALTIME_PRICE_MOCK` 모킹 모드 추가(장시간·네트워크 의존 제거). 신규 유료 소스 없음.
3. **상태 관리**: 단일 프로세스 **인메모리 브로드캐스트**(`ConnectionManager`). Redis pub/sub 멀티프로세스 확장은 향후 과제로 문서화(REQ-NFR-001).
4. **메시지 포맷**: `action`(subscribe/unsubscribe) 요청 / `type`(subscribed/unsubscribed/price/error) 응답의 JSON 프로토콜(§3.2).

---

## 7. Exclusions (What NOT to Build)

- **자동 매매·주문 실행**: 규제·책임 리스크로 **영구 제외**(프로젝트 전역 정책).
- **WebSocket 토큰 인증**: 본 SPEC의 멀티플렉스 스트림은 익명 공개 시세만 전송. 인증 스트림은 범위 밖.
- **Redis pub/sub 멀티프로세스 브로드캐스트**: 단일 프로세스 인메모리만 구현. 다중 워커 확장은 향후 과제.
- **신규 유료/외부 시세 데이터소스**: 기존 FinanceDataReader 경로만 사용.
- **기존 단일 종목 엔드포인트 `/ws/prices/{krx_code}` 제거·변경**: 무중단 유지(추가만).
- **REST 추천·가격 폴링 패턴 변경**: 기존 REST 흐름은 폴백으로 그대로 유지.
- **신규 알림 채널(웹푸시·SMS·카카오)**: 알림은 기존 인박스(`notifications`)에만 적재.
- **DB 스키마 변경·신규 마이그레이션**: 인메모리 구독 레지스트리로 처리(마이그레이션 0014 유지).
- **종목 검색·차트·추천 로직 변경**: 본 SPEC은 시세 스트리밍·구독·알림 연동에 한정.

---

## 8. 마일스톤 (Milestones)

> 시간 추정 없이 우선순위·순서로만 기술한다.

- **M1 — 멀티플렉스 WebSocket 백엔드** (Priority High): `/ws/prices` 엔드포인트, `ConnectionManager`, JSON 프로토콜 파싱(REQ-WSM-001/002/006/007).
- **M2 — 가격 폴링/모킹 서비스** (Priority High): 구독 심볼 배치 폴링 루프, `get_current_price` 재사용, `REALTIME_PRICE_MOCK` 모드, 실패 스킵·재시도(REQ-RT-001~004).
- **M3 — 구독 관리** (Priority High): subscribe/unsubscribe 레지스트리·역색인, 중복 구독 단일 fetch, 연결 정리(REQ-SUB-001~005, REQ-WSM-003/004/005).
- **M4 — 프론트 멀티플렉스 훅** (Priority Medium): `useLivePrices(symbols)` 단일 연결 훅, 구독 reconcile, 폴백(REQ-FEM-001/002/005/006).
- **M5 — Dashboard/Watchlist UI** (Priority Medium): Dashboard 추천 라이브 시세, Watchlist 단일 연결 마이그레이션(REQ-FEM-003/004).
- **M6 — 가격 알림 연동 + 테스트** (Priority Medium): 브로드캐스트 루프의 `watchlist_alerts` 평가→inbox 알림(멱등), pytest(백엔드)·vitest(프론트), 커버리지·린트 게이트(REQ-ALERT-001~005, REQ-NFR-005).
