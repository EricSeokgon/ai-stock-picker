# SPEC-STOCK-039 Research — 실시간 가격 폴링 & 자동 갱신

## 목적

포트폴리오 페이지·대시보드에서 보유 종목 현재가를 사용자 지정 주기(30s/60s/120s)로 REST 폴링하여 자동 갱신한다. KRX 장중(평일 09:00–15:30 KST)에만 폴링을 수행하고, 장 마감 시에는 상태 배지만 표시하며 폴링을 중단해 API 쿼터를 절약한다. WebSocket은 사용하지 않는다.

## 기존 시스템 조사 (브라운필드)

### 1. 가격 조회 경로 (재사용 — 신규 수집 없음)

- **KRX 현재가**: `realtime/price_feed.py::get_current_price(krx_code)` → `{"krx_code", "price", "change_pct", "timestamp"}` 반환. Redis 캐시 TTL 60초(`price:{krx_code}`), 미스 시 FinanceDataReader 폴백. 조회 실패 시 None.
- **해외 현재가**: `portfolio/service.py::_fetch_foreign_price(ticker, redis)`(USD) × `fx_rate.get_usd_krw_rate(redis)` → KRW 환산. 해외 가격 캐시 TTL 86400초.
- **통합 성과 진입점**: `portfolio/service.py::calculate_performance(db, portfolio_id, user_id, redis)` — KRX/해외 보유 모두 현재가를 조회해 손익·분류·섹터 집계를 반환. 라우터 `GET /portfolios/{id}/performance`가 이를 노출(소유권 404, 인증 필요).

→ **폴링은 기존 `/performance` 엔드포인트를 재호출하는 것으로 충분**하다. 새 데이터 수집 경로·새 가격 엔드포인트 불필요.

### 2. 장중 시간 판정 로직 (기존 — 단 평일 미검증)

- `notifications/general_alert_service.py`에 이미 `_is_market_open(now_kst=None)` 존재.
  - 상수: `_KST = ZoneInfo("Asia/Seoul")`, `_MARKET_OPEN = time(9, 0)`, `_MARKET_CLOSE = time(15, 30)`.
  - 로직: `_MARKET_OPEN <= now.time() <= _MARKET_CLOSE` — **시간대만 검사하고 요일(평일)은 검사하지 않는다.**
  - `ALERT_MARKET_HOURS_GATE` 환경변수로 게이팅(`general_alert_service.py:475`).
  - 출처 주석: SPEC-STOCK-023 REQ-023-020~024.

→ **갭 식별**: 요청서는 "평일 09:00–15:30"을 명시하나 기존 함수는 토·일을 장중으로 오판한다. SPEC-039는 **요일 검사를 포함한 순수 함수**를 `portfolio/` 패키지에 신규 작성(패키지 관례)하고, 시장 상태 엔드포인트가 이를 호출한다. 기존 `general_alert_service._is_market_open`은 수정하지 않는다(SPEC-023 소유, 스코프 외).

### 3. 라우터·소유권·인증 관례

- `portfolio/router.py` prefix `/portfolios`, 전부 인증 의존성(`get_current_user`) 사용. 소유권 불일치 → 404(`get_portfolio_with_holdings` None → 404, 신규 코드 관례).
- 시장 상태는 사용자·포트폴리오에 종속되지 않는 전역 정보 → **인증 불필요(public)**. 단 보유 갱신(`/performance`)은 기존대로 인증 유지.
- public 엔드포인트는 `/portfolios` prefix 밖에 두는 것이 의미상 적절(시장 메타). 신규 라우터 또는 기존 시장 메타 라우터에 `GET /market/status` 배치.

### 4. 프론트엔드 현황

- `frontend/src/api/portfolio.ts`(+`.js`): `apiGetPerformance(token, portfolioId)` 이미 존재 → 폴링이 재사용. `.js`/`.ts` 쌍 동시 수정 관례.
- `frontend/src/pages/Portfolio.tsx`(+`.js`), `Dashboard.tsx`(+`.js`)가 표시 대상.
- 폴링·정리(cleanup)·in-flight 디바운스는 신규 React 훅으로 캡슐화하는 것이 적절(예: `usePricePolling`).
- 상태 배지·마지막 갱신 시각 표시 컴포넌트 신규.

### 5. 마이그레이션

- 신규 테이블·컬럼 없음. 폴링은 기존 엔드포인트 재호출, 시장 상태는 순수 시간 계산. 최신 리비전 0024(SPEC-037) — **0025 도입하지 않음**. (033·034 동일 무도입 선례.)

## 설계 결정

| 결정 | 선택 | 근거 |
|------|------|------|
| 전송 방식 | REST 폴링 | NFR-001 WebSocket 금지. 기존 `/performance` 재호출로 충분 |
| 시장 상태 노출 | 신규 public 엔드포인트 `GET /market/status` | 인증 불필요한 전역 정보. 프론트가 폴링 사이클 전 게이팅에 사용 |
| 장중 판정 | 신규 순수 함수(요일+시간) `portfolio/`에 작성 | 기존 `_is_market_open`은 평일 미검증·SPEC-023 소유. NFR-002 순수 함수 |
| 가격 갱신 | 기존 `/performance` 재호출 | NFR — 신규 수집 금지 |
| 기본 주기 | 60초 | NFR-003 |
| 동시 요청 방지 | in-flight 가드(이전 요청 미완료 시 스킵) | NFR-004 |
| 시간 계산 | 표준 라이브러리(`datetime`, `zoneinfo`)만 | NFR-005 scipy 금지 |
| 마이그레이션 | 없음 | 신규 테이블 불필요 |

## 제외 (Out of Scope)

- WebSocket 실시간 스트리밍
- 해외 시장(NYSE/NASDAQ) 개장 시간 — SPEC-039는 KRX 한정
- 가격 알림 푸시 알림
- 캐싱·Redis 가격 캐시 추가(기존 캐시만 사용)
- 신규 가격 데이터 수집 경로

## REQ 접두사

`POLL` — 기존 도메인 접두사(OPT/RISK/FA/.../RPT/PAL/AIEX/DASH)와 충돌 없음.

## 관련 SPEC

- SPEC-STOCK-023: 알림 장중 게이팅(`_is_market_open` 출처) — 본 SPEC은 이를 수정하지 않고 별도 순수 함수 신설.
- SPEC-STOCK-028: 해외 자산 — 폴링은 기존 `/performance`가 처리하는 KRX/해외 통합 결과를 그대로 갱신.
- SPEC-STOCK-038: 대시보드 — 폴링 대상 페이지.
