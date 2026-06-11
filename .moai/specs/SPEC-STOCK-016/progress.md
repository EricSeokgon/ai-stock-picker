# SPEC-STOCK-016 진행 상황 — 실시간 주가 스트리밍 (Real-time Stock Price Streaming)

- **상태(Status)**: RUN COMPLETE
- **버전**: 0.2.0
- **생성일**: 2026-06-12
- **우선순위**: medium
- **마이그레이션**: 변경 없음 (최신 0014 유지)
- **REQ 접두사**: REQ-WSM-* / REQ-SUB-* / REQ-RT-* / REQ-ALERT-* / REQ-FEM-* / REQ-NFR-*

> SPEC-STOCK-003(단일 종목 `/ws/prices/{krx_code}`)의 확장. 단일 연결 멀티플렉스 스트림(`/ws/prices`) + Dashboard 라이브 시세 + 가격 알림 인박스 연동. 기존 엔드포인트·REST 폴링은 무중단 유지.

---

## 마일스톤 (Milestones)

| ID | 마일스톤 | 우선순위 | 상태 | 관련 REQ |
|----|----------|----------|------|----------|
| M1 | 멀티플렉스 WebSocket 백엔드 (`/ws/prices`, ConnectionManager, JSON 프로토콜) | High | DONE | REQ-WSM-001/002/006/007 |
| M2 | 가격 폴링/모킹 서비스 (배치 폴링, get_current_price 재사용, REALTIME_PRICE_MOCK) | High | DONE | REQ-RT-001~004 |
| M3 | 구독 관리 (subscribe/unsubscribe 레지스트리·역색인, 연결 정리) | High | DONE | REQ-SUB-001~005, REQ-WSM-003/004/005 |
| M4 | 프론트 멀티플렉스 훅 (`useLivePrices(symbols)`, 구독 reconcile, 폴백) | Medium | DONE | REQ-FEM-001/002/005/006 |
| M5 | Dashboard/Watchlist UI (Dashboard 라이브 시세, Watchlist 단일 연결 마이그레이션) | Medium | DONE | REQ-FEM-003/004 |
| M6 | 가격 알림 연동 + 테스트 (watchlist_alerts 평가→inbox, pytest/vitest, 린트·커버리지) | Medium | DONE | REQ-ALERT-001~005, REQ-NFR-005 |

---

## 상태 범례

- **TODO**: 미착수
- **IN_PROGRESS**: 진행 중
- **DONE**: 완료
- **BLOCKED**: 차단됨

---

## 체크리스트 (마일스톤별 세부)

### M1 — 멀티플렉스 WebSocket 백엔드
- [x] `/ws/prices` 엔드포인트 추가 (기존 `/ws/prices/{krx_code}`와 공존)
- [x] `ConnectionManager` (연결별 구독 집합) 구현
- [x] JSON 프로토콜 파싱: subscribe/unsubscribe, error 응답
- [x] 무인증 연결 수락 (공개 시세)

### M2 — 가격 폴링/모킹 서비스
- [x] 구독 심볼 배치 폴링 루프 (`price_broadcast_loop`)
- [x] `get_current_price` 재사용 (Redis 캐시 + FDR)
- [x] `REALTIME_PRICE_MOCK` 모킹 모드 (결정론적 시세)
- [x] 심볼별 실패 스킵·로그·다음 주기 재시도

### M3 — 구독 관리
- [x] 심볼→구독자 역색인 (중복 구독 단일 fetch)
- [x] 미구독 심볼 미조회 (REQ-SUB-005)
- [x] 연결 종료 시 레지스트리 정리
- [x] lifespan 백그라운드 태스크로 broadcast 루프 시작

### M4 — 프론트 멀티플렉스 훅
- [x] `hooks/useLivePrices.ts` 단일 연결 복수 종목 훅
- [x] symbols 변경 시 subscribe reconcile (재연결 없이)
- [x] WebSocket 불가 시 graceful degradation (마지막 값 유지)
- [x] 기존 단수형 `useLivePrice.ts` 보존

### M5 — Dashboard/Watchlist UI
- [x] `App.tsx` Dashboard: 멀티플렉스 훅으로 추천 종목 구독
- [x] `pages/Watchlist.tsx`: N개 연결 → 단일 멀티플렉스 연결 마이그레이션
- [x] 인라인 가격 표시 (LivePriceBadge 없이 직접 렌더링)

### M6 — 가격 알림 연동 + 테스트
- [x] 폴링 루프에서 `watchlist_alerts` 임계 평가 (`evaluate_alerts`)
- [x] 임계 도달 시 `notifications` 인박스 멱등 insert (price_alert)
- [x] 이미 발동된 알림 재발동 방지 (is_active + triggered_at 이중 확인)
- [x] 알림 실패가 가격 스트림을 끊지 않음 (예외 격리)
- [x] pytest 백엔드 테스트 (27개 신규): test_connection_manager.py(14) + test_price_broadcast.py(13) + test_ws_prices_multiplex.py(7, 통합)
- [x] vitest 프론트 테스트 (9개 신규): useLivePrices.test.ts

---

## 구현 완료 파일 목록

### 신규 파일
- `backend/src/stock_picker/realtime/connection_manager.py`
- `backend/src/stock_picker/realtime/price_broadcast.py`
- `backend/tests/unit/test_connection_manager.py`
- `backend/tests/unit/test_price_broadcast.py`
- `backend/tests/integration/test_ws_prices_multiplex.py`
- `frontend/src/hooks/useLivePrices.ts`
- `frontend/src/__tests__/useLivePrices.test.ts`

### 수정 파일
- `backend/src/stock_picker/realtime/ws_router.py` (멀티플렉스 엔드포인트 + manager 싱글턴 추가)
- `backend/src/stock_picker/api/main.py` (lifespan 컨텍스트 매니저 추가)
- `frontend/src/pages/Watchlist.tsx` (useLivePrices 통합)
- `frontend/src/App.tsx` (useLivePrices import + Dashboard 구독)

## 테스트 결과 요약 (2026-06-12)

| 스위트 | 통과 | 실패 | 비고 |
|--------|------|------|------|
| backend pytest | 650 | 5 | 5개 실패는 기존 test_collectors.py (pre-existing) |
| frontend vitest | 179 | 0 | 전체 통과 |

---

## 비고 (Notes)

- **DB 변경 없음**: 구독은 인메모리. 마이그레이션 0014 유지.
- **충돌 회피**: SPEC-003이 `REQ-WS-*`·`REQ-FE-*`를 선점하여, 본 SPEC은 `REQ-WSM-*`·`REQ-FEM-*` 등 멀티플렉스 전용 접두사 사용.
- **영구 제외**: 자동 매매/주문, WebSocket 토큰 인증, Redis pub/sub 멀티프로세스, 신규 데이터소스, 신규 알림 채널.
