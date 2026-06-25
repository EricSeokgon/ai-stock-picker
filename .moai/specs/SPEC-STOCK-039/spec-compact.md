# SPEC-STOCK-039 (Compact) — 실시간 가격 폴링 & 자동 갱신

run-phase 압축 참조. 상세는 spec.md/plan.md/acceptance.md/research.md.

## 핵심
- 포트폴리오·대시보드에서 보유 종목 현재가를 30/60/120초 REST 폴링으로 자동 갱신. 기본 60초.
- KRX 장중(평일 09:00–15:30 KST)에만 폴링. 마감 시 배지만 표시, 폴링 스킵.
- WebSocket·scipy 금지. 신규 마이그레이션 없음(최신 0024 유지). REQ 접두사 `POLL`.

## 백엔드
- 신규 `portfolio/market_status.py`: `is_market_open(now_kst=None)` — 평일 AND `time(9,0)<=t<=time(15,30)`, `ZoneInfo("Asia/Seoul")`, 표준 라이브러리만. `@MX:ANCHOR`(fan_in≥3)+`@MX:NOTE`(SPEC-023 `_is_market_open`과 별개·평일 검사 추가).
- 기존 `general_alert_service._is_market_open` 수정 금지(SPEC-023 소유, 요일 미검사).
- `schemas.py` `MarketStatus`(`is_open`/`now_kst`/`session`).
- public `GET /market/status`(인증 없음) — `/portfolios` prefix 밖 신규 라우터, `main.py` 등록.
- 현재가 갱신은 기존 `GET /portfolios/{id}/performance`(인증·소유권 404) 재호출 — 신규 수집/엔드포인트 없음.

## 프론트(.js/.ts 쌍)
- `apiGetMarketStatus()`(토큰 불필요), `apiGetPerformance` 재사용.
- 폴링 훅: 주기 선택·기본 60·일시중지/재개·사이클 전 장중 확인 게이팅·in-flight 스킵·useEffect cleanup·마지막 갱신 시각.
- `MarketStatusBadge`(장 중/장 마감 + 갱신 시각), Portfolio·Dashboard 통합.

## 작업
T-001 장중 순수 함수 → T-002 스키마/서비스 → T-003 public 엔드포인트 → T-004 API 래퍼 → T-005 폴링 훅 → T-006 배지 → T-007 페이지 통합 → T-008 검증.

## REQ 요약
- POLL-001~004 시장 상태(개장/마감/public)
- POLL-010~015 자동 갱신(주기 30/60/120, 기본 60, 일시중지/재개, 기존 경로 재사용)
- POLL-020~022 장중 게이팅(마감 시 스킵, 사이클 전 확인)
- POLL-030~032 배지·마지막 갱신 시각
- POLL-040 화면 이탈 정리
- POLL-050 in-flight 스킵
- POLL-060~061 인증·소유권 404
- NFR-001 WebSocket 금지, NFR-002 순수 함수, NFR-003 기본 60s, NFR-004 동시 요청 방지, NFR-005 scipy 금지

## 검증 포인트
개장 경계 09:00/15:30 포함, 08:59/15:31 마감, 주말 마감, 마감 폴링 스킵, in-flight 스킵, 화면 이탈 정리, 소유권 404.
