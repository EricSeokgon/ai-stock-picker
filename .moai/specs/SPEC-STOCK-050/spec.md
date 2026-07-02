---
id: SPEC-STOCK-050
title: 거래 기반 홀딩스 동기화 (Transaction-to-Holdings Reconciliation)
status: completed
version: 1.0.0
created: 2026-07-01
updated: 2026-07-01
author: ircp
priority: high
issue_number: null
branch: feature/SPEC-STOCK-036
labels: [portfolio, holdings, transactions, reconciliation, moving-average]
---

# SPEC-STOCK-050 — 거래 기반 홀딩스 동기화 (Transaction-to-Holdings Reconciliation)

## 1. 개요 (Overview)

SPEC-STOCK-049 가 포트폴리오에 **거래 원장(transaction ledger)** 과 **이동평균 원가법 실현손익(realized P&L)** 을 도입했다. 그러나 SPEC-049 는 거래 원장을 **독립 원장**으로 설계하여, 거래를 기록해도 `PortfolioHolding`(현재 보유 상태) 이 **자동으로 갱신되지 않는다**(§2.2 명시적 이연). 그 결과 사용자는 동일한 매매를 **두 번 입력**해야 한다 — 한 번은 거래 원장(`portfolio_transactions`)에, 또 한 번은 보유 종목(`portfolio_holdings`)의 수량·평균단가에. 이 **이중 입력(double-entry)** 은 오류와 불일치의 원인이며, SPEC-049 가 가장 먼저 이연한 후속 항목이다.

본 SPEC 은 이 갭을 메운다. 거래 원장을 **단일 진실 소스(source of truth)** 로 삼아, 원장을 재생(replay)하여 보유 종목을 **이동평균 원가법**으로 재계산·동기화한다. 사용자는 (1) 동기화 결과를 **미리보기(preview/diff)** 로 확인하고, (2) 확정 시 보유 종목을 원장 기반 값으로 갱신한다. 이로써 거래만 기록하면 보유 상태가 자동 산출되어 이중 입력이 사라진다.

- **스키마**: **신규 테이블·마이그레이션 없음**. 기존 `portfolio_transactions`(마이그 0030) 와 `portfolio_holdings`(SPEC-028) 두 테이블만 재사용한다.
- **홀딩스 동기화 서비스 (backend, sync)**: 원장 재생·미리보기·적용. 기존 홀딩스 CRUD(sync `Session`) 및 실현손익 계산과 동일한 이동평균 규약을 따른다.
- **엔드포인트**: `GET /portfolios/{id}/holdings/sync/preview`(미리보기), `POST /portfolios/{id}/holdings/sync`(적용).
- **프론트엔드**: 동기화 미리보기 패널(추가·수정·제거 종목 표시), 적용 버튼.

본 SPEC 은 **수동 원장 기반 재계산**이며, 증권사 연동·자동 매매와 **무관**하다(§2.2 영구 제외). 거래 원장(049) 로직·실현손익 계산은 **변경하지 않는다**.

### 1.1 동기 (Why)

SPEC-049 의 독립 원장은 스코프·위험을 낮추기 위한 의도적 선택이었으나, 실사용에서는 이중 입력이라는 마찰을 남겼다. 원장을 진실 소스로 삼아 보유 상태를 파생하면, 사용자는 매매를 한 번만 기록하면 된다. 이동평균 원가법은 SPEC-049 실현손익·기존 `avg_buy_price` 와 이미 일관되므로, 동일 규약을 재사용해 보유 상태를 산출하면 원장과 홀딩스 간 **정합성**이 보장된다. 미리보기(diff) 를 먼저 제공해 기존 수동 홀딩스를 덮어쓰기 전에 사용자가 변경을 검토할 수 있게 하여 안전성을 확보한다.

---

## 2. 범위 (Scope)

### 2.1 In-Scope

- **홀딩스 동기화 서비스 (sync)**: `backend/src/stock_picker/portfolio/holdings_sync.py`
  - `compute_ledger_positions(db, portfolio_id, user_id)` — 원장을 `txn_date ASC, id ASC` 로 재생하여 종목별 `(quantity, avg_buy_price)` 산출(이동평균 원가법). 원장 불일치(누적 SELL > 누적 BUY) 시 거부.
  - `preview_sync(db, portfolio_id, user_id)` — 원장 파생 홀딩스와 저장된 홀딩스를 비교하여 종목별 added/updated/removed 분류(저장 미변경).
  - `apply_sync(db, portfolio_id, user_id)` — 원장 파생 값으로 홀딩스 upsert/remove 후 반환.
- **엔드포인트**: `backend/src/stock_picker/portfolio/router.py` — `GET /{portfolio_id}/holdings/sync/preview`, `POST /{portfolio_id}/holdings/sync`. 기존 홀딩스 엔드포인트와 동일한 소유권 확인·의존성(`get_db_session`, `get_current_user`).
- **Pydantic 스키마**: `backend/src/stock_picker/portfolio/schemas.py` — `SyncPreviewItem`, `SyncPreviewResponse`, `SyncApplyResponse`.
- **프론트엔드 API**: `frontend/src/api/portfolio.ts`(+빌드 산출물 `.js`) — `previewHoldingsSync`, `applyHoldingsSync`.
- **프론트엔드 UI**: 포트폴리오 상세의 홀딩스 동기화 패널(`.tsx` + `.js`) — 미리보기(추가·수정·제거 목록)·적용 버튼.
- **백엔드 단위 테스트**: `backend/tests/unit/test_holdings_sync_050.py`(pytest, sync 픽스처 DB).
- **프론트엔드 단위 테스트**: `frontend/src/__tests__/holdings_sync_050.test.tsx`(vitest + React Testing Library, API 모킹).

### 2.2 Out-of-Scope (제외 — What NOT to Build)

> [HARD] 본 SPEC 은 아래 항목을 명시적으로 제외한다.

- **자동 매매·자동 주문 실행** (규제·책임 리스크로 프로젝트 **영구 제외**). 본 SPEC 은 원장 기반 재계산일 뿐 어떤 주문도 실행하지 않는다.
- **증권사 API 연동·거래내역 자동 임포트** — 거래는 SPEC-049 대로 사용자가 수동 입력한다(브로커 연동 없음).
- **거래 기록 시 실시간 자동 동기화(트리거)** — `add_transaction`/`delete_transaction`(049) 는 **변경하지 않는다**. 동기화는 사용자가 명시적으로 미리보기·적용을 요청할 때만 수행한다(049 독립 원장 계약 및 기존 테스트 보존).
- **원장에 없는 수동 홀딩스의 삭제** — 거래 원장에 대응 거래가 **하나도 없는** 종목의 홀딩스는 동기화가 건드리지 않고 **보존**한다(원장이 다루는 종목만 동기화).
- **해외 시장(NYSE/NASDAQ) 원장 동기화** — `portfolio_transactions` 에는 `market` 컬럼이 없으므로 동기화는 홀딩스의 **KRX 시장**(기본값) 을 대상으로 한다. 해외 시장 원장 동기화는 향후 SPEC(원장에 market 컬럼 추가 필요)로 이연한다.
- **FIFO·개별법(lot) 원가 추적** — SPEC-049 와 동일하게 **이동평균 원가법(총평균)** 단일 방식만 지원한다.
- **실현손익 재정의·변경** — 실현손익은 SPEC-049 `get_realized_pnl` 이 담당하며 본 SPEC 은 이를 변경하지 않는다. 본 SPEC 은 **보유 수량·평균단가** 동기화만 다룬다.
- **동기화 이력·감사 로그 저장** — 동기화 결과를 별도 테이블에 기록하지 않는다(미리보기·적용만).
- **동기화 관련 알림·인박스 이벤트** — 동기화는 알림을 발생시키지 않는다.
- **통화 환산·수수료 반영** — 원장(049)에는 fee 컬럼이 없으므로 원가에 수수료를 산입하지 않으며 환율 환산도 하지 않는다.

---

## 3. 요구사항 (Requirements — EARS)

> REQ 번호는 홀딩스 동기화 도메인 신규 접두사 `REQ-SYNC-` 로 001 부터 부여한다(거래 원장 `REQ-TXN-`(049)·홀딩스·좋아요·피드 등 기존 접두사와 충돌 회피). 모든 REQ 는 관찰 가능한 동작을 단일 SHALL 로 기술한다.

### 3.1 홀딩스 재계산 (REQ-SYNC-001 ~ 006)

- **REQ-SYNC-001**: When a user requests holdings synchronization for a portfolio they own, the system SHALL recompute that portfolio's holdings from its transaction ledger using the moving-average cost basis.
- **REQ-SYNC-002**: When synchronization replays a BUY transaction for a ticker, the system SHALL increase that ticker's held quantity by the BUY quantity and set its average buy price to the cost-weighted moving average including that BUY.
- **REQ-SYNC-003**: When synchronization replays a SELL transaction for a ticker, the system SHALL decrease that ticker's held quantity by the SELL quantity while leaving its average buy price unchanged.
- **REQ-SYNC-004**: Where a ticker's net held quantity after replaying all of its transactions equals zero, the system SHALL NOT retain a holding for that ticker.
- **REQ-SYNC-005**: When synchronization is applied, the system SHALL persist the recomputed holdings as that portfolio's holdings for the tickers present in the ledger.
- **REQ-SYNC-006**: If a user requests synchronization for a portfolio they do not own, then the system SHALL reject the request.

### 3.2 미리보기·차이 (REQ-SYNC-007 ~ 010)

- **REQ-SYNC-007**: When a user requests a synchronization preview for a portfolio they own, the system SHALL compute the ledger-derived holdings without modifying the stored holdings.
- **REQ-SYNC-008**: When a synchronization preview is computed, the system SHALL report for each affected ticker its resulting quantity and average buy price.
- **REQ-SYNC-009**: When a synchronization preview is computed, the system SHALL classify each affected ticker as added, updated, or removed relative to the currently stored holdings.
- **REQ-SYNC-010**: Where the stored holdings already match the ledger-derived holdings, the system SHALL report no changes in the preview.

### 3.3 정합성·계산 (REQ-SYNC-011 ~ 013)

- **REQ-SYNC-011**: If a ticker's cumulative SELL quantity exceeds its cumulative BUY quantity in the ledger, then the system SHALL reject the synchronization as a ledger inconsistency and SHALL NOT modify the stored holdings.
- **REQ-SYNC-012**: When synchronization computes a ticker's average buy price, the system SHALL calculate it as the ticker's remaining total cost divided by its remaining quantity using decimal arithmetic.
- **REQ-SYNC-013**: Where a ticker in the ledger has only BUY transactions, the system SHALL set that ticker's holding quantity to the sum of its BUY quantities and its average buy price to the cost-weighted average of those BUYs.

### 3.4 프론트엔드 (REQ-SYNC-014 ~ 016)

- **REQ-SYNC-014**: Where the holdings synchronization view is rendered for a portfolio, the page SHALL provide a control to request a synchronization preview.
- **REQ-SYNC-015**: When a synchronization preview is available, the page SHALL display the added, updated, and removed tickers before the user applies synchronization.
- **REQ-SYNC-016**: When the user applies synchronization, the page SHALL display the updated holdings without requiring a full page reload.

---

## 4. 인수 조건 (Acceptance Criteria — EARS)

> 모든 AC 는 EARS(Event-driven / State-driven / Unwanted behavior) 형식으로 작성하며, 각 AC 는 단일 관찰 가능 동작(단일 SHALL)만 검증한다. 총 11개.

### AC-050-001 — 매수 동기화 (REQ-SYNC-001·002)

When a user applies synchronization for a portfolio whose ledger has a single BUY of 10 shares at 1000 for a ticker,
the system shall persist a holding for that ticker with quantity 10 and average buy price 1000.

### AC-050-002 — 이동평균 매수 (REQ-SYNC-002·013)

When a user applies synchronization for a ticker whose ledger has BUY 10 @ 1000 then BUY 10 @ 2000,
the system shall persist a holding with quantity 20 and average buy price 1500.

### AC-050-003 — 매도 후 평균단가 불변 (REQ-SYNC-003)

When a user applies synchronization for a ticker whose ledger has BUY 10 @ 1000, BUY 10 @ 2000, then SELL 5 @ 3000,
the system shall persist a holding with quantity 15 and average buy price 1500.

### AC-050-004 — 전량 매도 시 홀딩 제거 (REQ-SYNC-004)

When a user applies synchronization for a ticker whose ledger has BUY 10 @ 1000 then SELL 10 @ 3000,
the system shall retain no holding for that ticker.

### AC-050-005 — 저장 반영 (REQ-SYNC-005)

When a user applies synchronization and then requests that portfolio's holdings,
the system shall return holdings equal to the ledger-derived values.

### AC-050-006 — 타인 포트폴리오 거부 (REQ-SYNC-006)

If a user requests synchronization for a portfolio owned by another user,
then the system shall reject the request.

### AC-050-007 — 미리보기 무변경 (REQ-SYNC-007)

When a user requests a synchronization preview,
the system shall leave the stored holdings unchanged.

### AC-050-008 — 미리보기 분류 (REQ-SYNC-009)

When a synchronization preview is computed for a portfolio whose ledger adds a new ticker not present in stored holdings,
the system shall classify that ticker as added.

### AC-050-009 — 변경 없음 보고 (REQ-SYNC-010)

Where the stored holdings already equal the ledger-derived holdings,
the system shall report no changes in the preview.

### AC-050-010 — 원장 불일치 거부 (REQ-SYNC-011)

If a ticker's ledger has cumulative SELL quantity greater than its cumulative BUY quantity,
then the system shall reject the synchronization without modifying the stored holdings.

### AC-050-011 — 프론트 미리보기·리로드 없는 적용 (REQ-SYNC-014·015·016)

Where the synchronization view shows a preview with added, updated, and removed tickers,
the page shall render the updated holdings without a full page reload after the user applies synchronization.

---

## 5. 기술 설계 (Technical Approach)

### 5.1 스키마 (마이그레이션 없음)

- **신규 테이블·마이그레이션 없음.** 기존 두 테이블만 재사용한다:
  - `portfolio_transactions`(마이그 0030): `id`·`portfolio_id`(FK CASCADE)·`krx_code`(String(20))·`txn_type`(`"BUY"`|`"SELL"`)·`quantity`(Integer)·`price`(Numeric(18,2))·`txn_date`(Date)·`note`·`created_at`. (fee·market 컬럼 없음.)
  - `portfolio_holdings`(SPEC-028): `id`·`portfolio_id`(FK CASCADE)·`krx_code`(String(10))·`quantity`(Integer)·`avg_buy_price`(Numeric(10,2))·`market`(String(10), default `"KRX"`)·`currency`(String(3), default `"KRW"`)·`added_at`. UNIQUE`(portfolio_id, krx_code, market)`.
- 동기화는 홀딩스의 **KRX 시장**(`market="KRX"`) 을 대상으로 upsert 한다(원장에 market 컬럼이 없으므로; §2.2). `avg_buy_price` 는 `Numeric(10,2)` 범위(≤ 99,999,999.99) 내 KRW 종목을 전제한다.

### 5.2 홀딩스 동기화 서비스 (`holdings_sync.py`, sync)

- 모든 함수는 `db: Session` 을 받는 **sync** 함수다(기존 `service.add_holding`/`remove_holding`·`transactions.add_transaction` 패턴 준수). async 컨텍스트를 호출하지 않는다. 소유권 확인은 049 와 동일한 `_verify_portfolio_owner`(미소유 시 **403**) 규약을 재사용한다(REQ-SYNC-006).
- `compute_ledger_positions(db, portfolio_id, user_id) -> dict[str, tuple[int, Decimal]]`:
  1. 소유권 확인.
  2. 해당 포트폴리오의 모든 거래를 `txn_date ASC, id ASC` 로 조회.
  3. `krx_code` 별 **이동평균 원가법** 리플레이:
     - 상태: `position`(수량), `cost`(총원가, `Decimal`). `avg = cost / position`(`position > 0` 일 때).
     - **BUY**: `cost += price*quantity`; `position += quantity`(REQ-SYNC-002·013).
     - **SELL**: `avg = cost/position`(`position > 0`); `cost -= avg*quantity`; `position -= quantity`(평균단가 불변, REQ-SYNC-003). 리플레이 중 `position - quantity < 0` 이 되면 원장 불일치로 `HTTPException`(400/409) 발생, 어떤 홀딩스도 수정하지 않음(REQ-SYNC-011).
  4. `position == 0` 종목은 결과에서 제외(REQ-SYNC-004). `position > 0` 종목은 `(position, round(avg, 2))` 로 반환(REQ-SYNC-012).
- `preview_sync(db, portfolio_id, user_id) -> SyncPreviewResponse`:
  1. `compute_ledger_positions` 로 원장 파생 홀딩스 산출(저장 미변경, REQ-SYNC-007).
  2. 저장된 `portfolio_holdings`(market=KRX) 와 비교하여 종목별 분류(REQ-SYNC-008·009):
     - 원장에 있고 홀딩스에 없음 → `added`.
     - 양쪽에 있고 `(quantity, avg_buy_price)` 상이 → `updated`.
     - 홀딩스에 있으나 원장 net=0 → `removed`.
     - 양쪽에 있고 동일 → 변경 없음(diff 미포함).
  3. 원장에 대응 거래가 없는 홀딩스는 diff 에서 제외(보존; §2.2).
  4. 모든 항목이 동일하면 빈 변경 목록 반환(REQ-SYNC-010).
- `apply_sync(db, portfolio_id, user_id) -> SyncApplyResponse`:
  1. `compute_ledger_positions` 산출(불일치 시 거부, 저장 미변경 — REQ-SYNC-011).
  2. 원장이 다루는 종목에 대해 홀딩스 upsert(존재하면 `quantity`·`avg_buy_price` 갱신, 없으면 `add_holding` 로 생성; market=KRX). net=0 종목은 홀딩스 존재 시 삭제(REQ-SYNC-004·005).
  3. 커밋 후 갱신된 홀딩스 요약 반환.
- **수치 예시(설계 앵커, AC-050-003)**: BUY 10@1000 → cost 10000, pos 10, avg 1000. BUY 10@2000 → cost 30000, pos 20, avg 1500. SELL 5@3000 → cost -= 1500*5 = 22500, pos 15, avg **1500**. 홀딩스: quantity=15, avg_buy_price=1500.00.

### 5.3 엔드포인트·스키마

- `router.py`(기존 portfolio 라우터에 추가, 홀딩스·거래와 동일 패턴):
  - `GET /{portfolio_id}/holdings/sync/preview` → `SyncPreviewResponse`.
  - `POST /{portfolio_id}/holdings/sync` → `SyncApplyResponse`.
  - 각 엔드포인트는 `db: Session = Depends(get_db_session)`, `current_user: User = Depends(get_current_user)`. 서비스 검증 실패는 `HTTPException`(403/400/409)으로 매핑.
- `schemas.py`:
  - `SyncPreviewItem`: `krx_code: str`, `change: Literal["added","updated","removed"]`, `quantity: int`, `avg_buy_price: Decimal`.
  - `SyncPreviewResponse`: `items: list[SyncPreviewItem]`, `has_changes: bool`.
  - `SyncApplyResponse`: `synced: int`(동기화된 종목 수), `holdings: list[...]`(갱신된 KRX 홀딩스 요약: `krx_code`·`quantity`·`avg_buy_price`).

### 5.4 프론트엔드 (`portfolio.ts`, 홀딩스 동기화 패널)

- `portfolio.ts`: `previewHoldingsSync(portfolioId)`, `applyHoldingsSync(portfolioId)`. 타입에 `SyncPreviewItem`·`SyncPreviewResponse`·`SyncApplyResponse` 추가.
- 동기화 패널(`.tsx`): "미리보기" 버튼(REQ-SYNC-014) → 추가·수정·제거 종목 목록 표시(REQ-SYNC-015), "적용" 버튼 → 성공 시 로컬 상태에 갱신 홀딩스 반영하여 리로드 없이 표시(REQ-SYNC-016). 변경 없음 시 안내 문구.

### 5.5 빌드 산출물 동기화 (.js/.ts 페어)

- 본 프로젝트는 `.tsx`/`.ts` 소스와 커밋된 `.js` 빌드 산출물을 **쌍으로** 유지한다. 수정한 모든 프론트 소스(`portfolio.ts`, 동기화 패널 `.tsx`)는 대응 `.js` 도 함께 갱신한다. 백엔드 Python 파일은 빌드 산출물 페어가 없다.

---

## 6. 테스트 목록 (Test Plan)

- 백엔드: `backend/tests/unit/test_holdings_sync_050.py`(pytest, sync 픽스처 DB). 신규 외부 의존성 없음.
- 프론트엔드: `frontend/src/__tests__/holdings_sync_050.test.tsx`(vitest + React Testing Library, `portfolio` API 모듈 모킹).

| ID | 테스트 | 검증 REQ / AC |
|----|--------|---------------|
| T-050-001 | BUY 10@1000 원장 → 적용 시 홀딩 quantity=10·avg=1000 | REQ-SYNC-001·002 / AC-001 |
| T-050-002 | BUY 10@1000·BUY 10@2000 → 홀딩 quantity=20·avg=1500 | REQ-SYNC-002·013 / AC-002 |
| T-050-003 | BUY 10@1000·BUY 10@2000·SELL 5@3000 → 홀딩 quantity=15·avg=1500 | REQ-SYNC-003 / AC-003 |
| T-050-004 | BUY 10·SELL 10 → 해당 종목 홀딩 제거 | REQ-SYNC-004 / AC-004 |
| T-050-005 | 적용 후 홀딩스 조회 → 원장 파생 값과 일치 | REQ-SYNC-005 / AC-005 |
| T-050-006 | 타인 포트폴리오 동기화 → 거부(403) | REQ-SYNC-006 / AC-006 |
| T-050-007 | 미리보기 요청 → 저장 홀딩스 불변 | REQ-SYNC-007 / AC-007 |
| T-050-008 | 원장에 신규 종목 → 미리보기 change=added 분류 | REQ-SYNC-009 / AC-008 |
| T-050-009 | 홀딩스 == 원장 파생 → 미리보기 has_changes=false | REQ-SYNC-010 / AC-009 |
| T-050-010 | 누적 SELL > 누적 BUY 원장 → 동기화 거부·홀딩스 불변 | REQ-SYNC-011 / AC-010 |
| T-050-011 | 프론트 미리보기 diff 표시 → 적용 시 리로드 없이 홀딩스 갱신 | REQ-SYNC-014·015·016 / AC-011 |

품질 게이트: 백엔드 pytest 통과(커버리지 기준 충족), 프론트 vitest 통과, ESLint·ruff 통과, 신규 외부 의존성 0, **신규 테이블·마이그레이션 0개**, `.js`/`.ts` 페어 동기화, scipy 미사용(Decimal/표준 라이브러리만).

---

## 7. HISTORY

| Version | Date | Author | Note |
|---------|------|--------|------|
| 0.1.0 | 2026-07-01 | ircp | 최초 초안 — SPEC-049 거래 원장 후속(가장 먼저 이연된 항목: `PortfolioHolding` 자동 동기화). 거래 원장을 진실 소스로 삼아 이동평균 원가법으로 홀딩스를 재계산·동기화(미리보기 diff + 적용). **신규 테이블·마이그레이션 없음** — 기존 `portfolio_transactions`(0030)·`portfolio_holdings`(028) 재사용. 동기화 서비스는 sync(`Session`) — 049 거래 서비스·홀딩스 CRUD 패턴 준수. 거래 기록 시 자동 트리거 아님(049 독립 원장 계약·기존 테스트 보존, 명시적 미리보기·적용만). 원장 없는 수동 홀딩스 보존, KRX 시장 대상(원장에 market 없음). 실제 049 구현 모델 기준(txn_type·krx_code(20)·price(18,2)·txn_date·note; fee·market 없음; 소유권 미충족 403). REQ-SYNC-001~016(16개), AC-050-001~011(11개), 테스트 T-050-001~011(11개). 신규 접두사 `REQ-SYNC-`. |

---

## 8. 의존성 (Dependencies)

- **SPEC-STOCK-049** (거래 원장 & 실현손익): `portfolio_transactions` 테이블(마이그 0030)·거래 원장 이동평균 규약·`_verify_portfolio_owner`(403) 패턴을 재사용한다. 049 의 `add_transaction`/`delete_transaction`/`get_realized_pnl` 로직 자체는 변경하지 않는다.
- **SPEC-STOCK-028** (해외 자산 지원): `PortfolioHolding` 의 `krx_code`·`market`·`avg_buy_price` 컬럼 규약 재사용. 동기화 upsert 대상은 KRX 시장 홀딩스.
- **포트폴리오 기반 인프라**: `Portfolio` 모델·`get_db_session`·`get_current_user`·portfolio `router.py`·`service.add_holding`/`remove_holding` — 소유권 확인·의존성 주입·홀딩스 CRUD 재사용.

## 9. 기술 제약 (Technical Constraints)

- **동기화 서비스는 sync(`Session`)** 이다(기존 `service.add_holding`/`transactions.add_transaction` 패턴). async 컨텍스트를 호출하지 않는다(sync/async 혼용 금지).
- **이동평균 원가법 단일 방식**: 홀딩스 수량·평균단가는 이동평균(총평균) 원가법으로만 재계산한다. FIFO/개별법 로트 추적은 제외(§2.2). SPEC-049 실현손익과 동일 규약.
- **명시적 동기화만**: 거래 기록(`add_transaction`)·삭제(`delete_transaction`) 시 자동 트리거하지 않는다. 사용자가 미리보기·적용을 명시 요청할 때만 홀딩스를 갱신하여 049 독립 원장 계약과 기존 테스트를 보존한다.
- **원장이 다루는 종목만 동기화**: 거래 원장에 대응 거래가 없는 홀딩스는 보존(삭제·수정하지 않음). 원장 종목만 upsert/remove.
- **KRX 시장 대상**: `portfolio_transactions` 에 `market` 컬럼이 없으므로 동기화는 홀딩스의 `market="KRX"` 를 대상으로 한다. 해외 시장 원장 동기화는 향후 SPEC.
- **원장 불일치 처리**: 종목별 누적 SELL 이 누적 BUY 를 초과하면(거래 삭제 등으로 발생 가능) 동기화 전체를 거부하고 저장 홀딩스를 변경하지 않는다(REQ-SYNC-011).
- **수치 타입**: 금액은 `Decimal` 로 계산하고 홀딩스 `avg_buy_price` 는 `Numeric(10,2)` 로 저장(round 2). 부동소수 오차를 피한다.
- **정렬 안정성**: 원장 리플레이는 `txn_date` 기준 정렬하되 동일 일자 거래는 `id` 를 보조 정렬 키로 사용해 결정적 순서를 보장한다.
- **소유자 전용**: 동기화·미리보기는 소유자만 수행할 수 있으며 미소유 시 403(049 규약 재사용).
- React + TypeScript(`.tsx`/`.ts`) 소스, Vite 빌드. 커밋된 `.js` 산출물과 페어 동기화 필수.
- ESLint·ruff 통과, 신규 외부 의존성 금지, scipy 미사용, 모든 신규 동작 단위 테스트 필수.

---

## 10. 구현 노트 (Implementation Notes)

### 백엔드 구현

**홀딩스 동기화 서비스** (`backend/src/stock_picker/portfolio/holdings_sync.py`):
- `compute_ledger_positions(db, portfolio_id, user_id)` — 원장을 `txn_date ASC, id ASC` 로 재생하여 종목별 `(quantity, avg_buy_price)` 산출(이동평균 원가법). 원장 불일치(누적 SELL > 누적 BUY) 시 거부.
- `preview_sync(db, portfolio_id, user_id)` — 원장 파생 홀딩스와 저장된 홀딩스를 비교하여 종목별 added/updated/removed 분류(저장 미변경).
- `apply_sync(db, portfolio_id, user_id)` — 원장 파생 값으로 홀딩스 upsert/remove 후 반환.

**라우터 엔드포인트** (`backend/src/stock_picker/portfolio/router.py`):
- `GET /portfolios/{portfolio_id}/holdings/sync/preview` → `SyncPreviewResponse`
- `POST /portfolios/{portfolio_id}/holdings/sync` → `SyncApplyResponse`

**Pydantic 스키마** (`backend/src/stock_picker/portfolio/schemas.py`):
- `SyncPreviewItem`, `SyncPreviewResponse`, `SyncApplyResponse` 추가

### 프론트엔드 구현

**API 함수** (`frontend/src/api/portfolio.ts`):
- `previewHoldingsSync(portfolioId)` — GET `/portfolios/{portfolioId}/holdings/sync/preview`
- `applyHoldingsSync(portfolioId)` — POST `/portfolios/{portfolioId}/holdings/sync`

**UI 컴포넌트** (`HoldingsSyncPanel.tsx`):
- 미리보기 버튼(REQ-SYNC-014) → 추가·수정·제거 종목 목록 표시(REQ-SYNC-015)
- 적용 버튼 → 성공 시 로컬 상태에 갱신 홀딩스 반영하여 리로드 없이 표시(REQ-SYNC-016)

### 테스트 결과

**백엔드 단위 테스트** (`backend/tests/unit/test_holdings_sync_050.py`):
- T-050-001 ~ T-050-010 (10/10 PASS)
  - BUY 10@1000 원장 → 적용 시 홀딩 quantity=10·avg=1000
  - BUY 10@1000·BUY 10@2000 → 홀딩 quantity=20·avg=1500
  - BUY 10@1000·BUY 10@2000·SELL 5@3000 → 홀딩 quantity=15·avg=1500
  - BUY 10·SELL 10 → 해당 종목 홀딩 제거
  - 적용 후 홀딩스 조회 → 원장 파생 값과 일치
  - 타인 포트폴리오 동기화 → 거부(403)
  - 미리보기 요청 → 저장 홀딩스 불변
  - 원장에 신규 종목 → 미리보기 change=added 분류
  - 홀딩스 == 원장 파생 → 미리보기 has_changes=false
  - 누적 SELL > 누적 BUY 원장 → 동기화 거부·홀딩스 불변

**프론트엔드 단위 테스트** (`frontend/src/__tests__/holdings_sync_050.test.tsx`):
- T-050-011 (2/2 PASS)
  - `previewHoldingsSync` GET 요청 컨트랙트 검증
  - `applyHoldingsSync` POST 요청 컨트랙트 및 응답 형태 검증

### 설계 원칙

- **신규 테이블·마이그레이션 0개**: 기존 `portfolio_transactions`(마이그 0030) + `portfolio_holdings`(SPEC-028) 재사용
- **이동평균 원가법**: SPEC-049 실현손익과 동일 규약 준수
- **명시적 동기화**: 사용자 미리보기·적용 요청 시만 수행(거래 기록 시 자동 트리거 없음)
- **KRX 시장 대상**: 원장에 market 컬럼이 없으므로 KRX 홀딩스만 동기화
- **소유권 검증**: 049 규약 재사용(`_verify_portfolio_owner`, 미소유 시 403)
- **Decimal 수치 계산**: 부동소수 오차 회피
