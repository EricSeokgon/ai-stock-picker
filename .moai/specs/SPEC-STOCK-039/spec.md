---
id: SPEC-STOCK-039
version: 0.2.0
status: draft
created_at: 2026-06-25
updated_at: 2026-06-25
author: ircp
priority: medium
issue_number: null
labels: [portfolio, polling, market-status, frontend, backend]
---

# SPEC-STOCK-039 — 실시간 가격 폴링 & 자동 갱신

## HISTORY

| 버전 | 일자 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 0.1.0 | 2026-06-25 | ircp | 초안 — REST 폴링 자동 갱신, KRX 장중 게이팅, 시장 상태 배지 |

## 개요

포트폴리오 페이지와 대시보드에서 보유 종목 현재가를 사용자 지정 주기(30초/60초/120초)로 REST 폴링하여 자동 갱신한다. KRX 장중(평일 09:00–15:30 KST)에만 폴링하고, 장 마감 시에는 상태 배지를 표시하며 폴링을 중단해 외부 API 호출을 절약한다. WebSocket을 사용하지 않으며, 가격 갱신은 기존 성과 조회 경로를 재호출해 처리한다.

## 용어

- **THE 시스템**: 본 SPEC이 정의하는 실시간 가격 폴링·시장 상태 기능 전체(백엔드 시장 상태 제공 + 프론트엔드 자동 갱신).
- **장중**: KRX 정규장 개장 시간대 — 평일(월–금) 09:00–15:30 KST.
- **폴링 사이클**: 보유 종목 현재가를 1회 재조회하여 화면을 갱신하는 단위 동작.

## 기능 요구사항 (EARS)

### 시장 상태 (Market Status)

- **REQ-POLL-001** (Ubiquitous): THE 시스템 SHALL 한국 거래소의 현재 개장 여부를 조회할 수 있는 시장 상태 정보를 제공한다.
- **REQ-POLL-002** (State-Driven): WHILE 현재 시각이 평일 09:00 이상 15:30 이하(한국 표준시)인 동안, THE 시스템 SHALL 시장 상태를 개장으로 보고한다.
- **REQ-POLL-003** (State-Driven): WHILE 현재 시각이 주말이거나 평일 정규장 시간대 밖인 동안, THE 시스템 SHALL 시장 상태를 마감으로 보고한다.
- **REQ-POLL-004** (Ubiquitous): THE 시스템 SHALL 시장 상태 조회를 인증 없이 누구나 이용할 수 있도록 공개한다.

### 자동 갱신 폴링 (Auto-refresh)

- **REQ-POLL-010** (Event-Driven): WHEN 사용자가 자동 갱신을 시작하면, THE 시스템 SHALL 선택된 주기마다 보유 종목 현재가를 재조회하여 화면을 갱신한다.
- **REQ-POLL-011** (Ubiquitous): THE 시스템 SHALL 자동 갱신 주기를 30초·60초·120초 중에서 사용자가 선택할 수 있도록 제공한다.
- **REQ-POLL-012** (Ubiquitous): THE 시스템 SHALL 자동 갱신 기본 주기를 60초로 설정한다.
- **REQ-POLL-013** (Event-Driven): WHEN 사용자가 자동 갱신을 일시 중지하면, THE 시스템 SHALL 이후 폴링 사이클을 더 이상 수행하지 않는다.
- **REQ-POLL-014** (Event-Driven): WHEN 사용자가 일시 중지된 자동 갱신을 재개하면, THE 시스템 SHALL 폴링 사이클을 다시 수행한다.
- **REQ-POLL-015** (Ubiquitous): THE 시스템 SHALL 보유 종목 현재가 갱신을 신규 데이터 수집 없이 기존 성과 조회 경로의 재호출로 수행한다.

### 장중 게이팅 (Market-Hours Gating)

- **REQ-POLL-020** (State-Driven): WHILE 시장이 개장 상태인 동안, THE 시스템 SHALL 자동 갱신 폴링 사이클을 수행한다.
- **REQ-POLL-021** (Unwanted): IF 시장이 마감 상태이면, THEN THE 시스템 SHALL 폴링 사이클을 건너뛰고 보유 종목 현재가를 재조회하지 않는다.
- **REQ-POLL-022** (Event-Driven): WHEN 폴링 사이클을 시작하기 직전이면, THE 시스템 SHALL 먼저 시장 개장 여부를 확인한다.

### 상태 표시 (Status Display)

- **REQ-POLL-030** (State-Driven): WHILE 시장이 개장 상태인 동안, THE 시스템 SHALL 장 중임을 알리는 상태 배지를 표시한다.
- **REQ-POLL-031** (State-Driven): WHILE 시장이 마감 상태인 동안, THE 시스템 SHALL 장 마감임을 알리는 상태 배지를 표시한다.
- **REQ-POLL-032** (Event-Driven): WHEN 보유 종목 현재가가 갱신되면, THE 시스템 SHALL 마지막 갱신 시각을 화면에 표시한다.

### 생명주기 정리 (Lifecycle Cleanup)

- **REQ-POLL-040** (Event-Driven): WHEN 사용자가 자동 갱신이 동작 중인 화면을 벗어나면, THE 시스템 SHALL 진행 중인 자동 폴링을 중단한다.

### 동시 요청 방지 (Concurrency Guard)

- **REQ-POLL-050** (Unwanted): IF 이전 폴링 요청이 아직 완료되지 않았으면, THEN THE 시스템 SHALL 새로운 폴링 요청을 시작하지 않고 해당 사이클을 건너뛴다.

### 소유권·접근 보호 (Ownership)

- **REQ-POLL-060** (Ubiquitous): THE 시스템 SHALL 보유 종목 현재가 갱신 요청에 대해 기존 성과 조회와 동일한 인증·소유권 보호를 적용한다.
- **REQ-POLL-061** (Unwanted): IF 인증된 사용자가 소유하지 않은 포트폴리오의 현재가 갱신을 요청하면, THEN THE 시스템 SHALL 해당 포트폴리오를 찾을 수 없음으로 응답한다.

## 비기능 요구사항 (NFR)

- **REQ-POLL-NFR-001**: THE 시스템 SHALL 소켓 기반 실시간 통신 없이 단방향 주기 요청만으로 자동 갱신을 구현한다.
- **REQ-POLL-NFR-002**: THE 시스템 SHALL 장중 판정 로직을 네트워크·데이터베이스 의존 없이 단독으로 검증 가능한 순수 함수로 구현한다.
- **REQ-POLL-NFR-003**: THE 시스템 SHALL 기본 폴링 주기를 60초로 한다.
- **REQ-POLL-NFR-004**: THE 시스템 SHALL 이전 폴링 요청이 완료되기 전에는 새 요청을 발생시키지 않는다(디바운스/스킵).
- **REQ-POLL-NFR-005**: THE 시스템 SHALL 시간 계산에 외부 과학 계산 라이브러리를 사용하지 않고 표준 라이브러리만 사용한다.

## Exclusions (What NOT to Build)

- WebSocket 실시간 가격 스트리밍 — REST 폴링만 구현한다.
- 해외 시장(NYSE/NASDAQ) 개장 시간 판정 — 본 SPEC은 KRX 장중만 다룬다.
- 가격 변동 시 푸시 알림 — 알림은 SPEC-031/036 범위.
- Redis 가격 캐시 추가·캐시 전략 변경 — 기존 캐시(가격 60초, 해외 86400초)만 그대로 사용한다.
- 신규 가격 데이터 수집 경로 — 기존 성과 조회 경로 재호출만 사용한다.
- 기존 알림 장중 게이팅 함수(SPEC-023)의 수정 — 별도 순수 함수를 신설한다.

## 델타 마커 (Delta Markers)

| 구분 | 대상 | 변경 |
|------|------|------|
| 신규(BE) | `portfolio/` 장중 판정 순수 함수 | 평일+시간 검사 시장 개장 판정 + 시장 상태 서비스 |
| 신규(BE) | 시장 상태 엔드포인트 | public `GET /market/status` |
| 재사용(BE) | `GET /portfolios/{id}/performance` | 폴링이 재호출 (수정 없음) |
| 미변경(BE) | `general_alert_service._is_market_open` | SPEC-023 소유, 수정 안 함 |
| 신규(FE) | 폴링 훅 + 시장 상태 배지 + 마지막 갱신 시각 표시 | Portfolio·Dashboard 통합 |
| 재사용(FE) | `apiGetPerformance` | 폴링 재호출 (수정 없음) |
| 마이그레이션 | 없음 | 신규 테이블·컬럼 없음 (최신 0024 유지) |

## MX Tag 계획

- `@MX:ANCHOR`: 장중 판정 순수 함수 — 시장 상태 서비스·라우터·테스트 3곳 이상 참조 예상.
- `@MX:NOTE`: 시장 상태 엔드포인트가 public(인증 미적용)임을 명시.
- `@MX:NOTE`: 장중 판정이 기존 SPEC-023 `_is_market_open`과 별개이며 평일 검사를 추가함을 명시.

## 참고

- 상세 기술 접근·작업 분해는 `plan.md`, 수용 기준은 `acceptance.md`, 사전 조사는 `research.md` 참조.
