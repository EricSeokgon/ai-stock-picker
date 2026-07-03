---
id: SPEC-STOCK-049
title: 포트폴리오 거래 내역 & 실현손익 (Transaction Ledger & Realized P&L)
status: draft
version: 0.1.0
created: 2026-07-01
updated: 2026-07-01
author: ircp
priority: high
issue_number: null
branch: feature/SPEC-STOCK-036
labels: [portfolio, transactions, ledger, realized-pnl, analytics]
---

# SPEC-STOCK-049 — 포트폴리오 거래 내역 & 실현손익 (Transaction Ledger & Realized P&L)

## 1. 개요 (Overview)

SPEC-STOCK-042~048 이 공개 포트폴리오 공유·좋아요·댓글·대댓글·알림 딥링크로 **소셜 아크**를 완성했다. 포트폴리오 분석 영역은 벤치마크 비교(034)·배당(019/033)·리밸런싱(032)·리스크(027)·기간별 성과(030)·월별 스냅샷(035)까지 폭넓게 갖추었다. 그러나 이 모든 기능은 **현재 보유 상태(current position)** 만을 다룬다 — `PortfolioHolding` 은 종목별 `quantity`·`avg_buy_price` 만 저장할 뿐, **개별 매수·매도 거래를 기록하지 않는다**. 그 결과 앱에는 **거래 내역(trade journal)** 도, **실현손익(realized P&L)** 도 존재하지 않는다.

한국 개인투자자에게 **실현손익**은 핵심 관심사다. 종목을 언제 얼마에 사고팔았는지, 팔아서 실제로 얼마를 벌거나 잃었는지는 미실현 평가손익(기존 performance·benchmark 모듈이 담당)과 별개로 반드시 필요한 정보다. 본 SPEC 은 포트폴리오에 **거래 원장(transaction ledger)** 을 도입하여, 사용자가 매수·매도 거래를 수동 기록하고 **이동평균 원가법(moving-average cost basis)** 으로 산출된 종목별·전체 실현손익을 조회할 수 있게 한다.

- **스키마 (마이그레이션 0030)**: 신규 테이블 `portfolio_transactions` 1개. `id`·`portfolio_id`(FK, CASCADE)·`krx_code`·`market`·`side`(BUY/SELL)·`quantity`·`price`·`fee`·`traded_at`·`created_at`. `down_revision = "0029"`.
- **거래 원장 서비스 (backend, sync)**: 거래 기록·조회·삭제 및 **이동평균 원가법 실현손익 계산**. 기존 홀딩스 CRUD(sync `Session`) 와 동일한 패턴을 따른다.
- **엔드포인트**: POST/GET/DELETE `/portfolios/{id}/transactions`, GET `/portfolios/{id}/realized-pnl`.
- **프론트엔드**: 거래 입력 폼·거래 목록·전체 실현손익 표시.

본 SPEC 은 **매매 원장(수동 기록)** 이며, 증권사 주문 실행이나 자동 매매와 **무관**하다(§2.2 영구 제외). 기존 `PortfolioHolding` 로직은 **변경하지 않는다** — 거래 원장은 독립적으로 동작하며 홀딩스를 자동 갱신하지 않는다.

### 1.1 동기 (Why)

미실현 평가손익만으로는 투자 성과를 완전히 파악할 수 없다. "지금 얼마 평가액인가"와 "실제로 팔아서 얼마 벌었나"는 다른 질문이다. 거래 원장은 후자에 답한다. 이동평균 원가법은 이미 홀딩스의 `avg_buy_price` 가 채택한 방식과 일관되며, FIFO/개별법 로트 추적의 복잡도 없이 한국 개인투자자에게 익숙한 총평균 기반 실현손익을 제공한다. 수동 기록으로 시작해 스코프와 위험을 낮추고, 증권사 연동·자동 홀딩스 동기화는 향후 SPEC 으로 분리한다.

---

## 2. 범위 (Scope)

### 2.1 In-Scope

- **DB 마이그레이션 0030**: `backend/alembic/versions/0030_portfolio_transactions_049.py` — `portfolio_transactions` 테이블 신규 및 `(portfolio_id, krx_code)` 인덱스. `down_revision = "0029"`.
- **ORM 모델**: `backend/src/stock_picker/db/models.py` — `PortfolioTransaction` 모델 추가.
- **거래 원장 서비스 (sync)**: `backend/src/stock_picker/portfolio/transactions.py`
  - `record_transaction(db, portfolio_id, user_id, krx_code, market, side, quantity, price, fee, traded_at)` — 검증 후 거래 저장.
  - `list_transactions(db, portfolio_id, user_id, page, size)` — 거래 시각 최신순 페이지네이션 + total.
  - `delete_transaction(db, portfolio_id, transaction_id, user_id)` — 소유자 전용 삭제, 미존재 시 404.
  - `compute_realized_pnl(db, portfolio_id, user_id)` — 이동평균 원가법 종목별·전체 실현손익.
- **엔드포인트**: `backend/src/stock_picker/portfolio/router.py` — POST/GET/DELETE `/{portfolio_id}/transactions`, GET `/{portfolio_id}/realized-pnl`. 기존 홀딩스 엔드포인트와 동일한 소유권 확인·의존성(`get_db_session`, `get_current_user`).
- **Pydantic 스키마**: `backend/src/stock_picker/portfolio/schemas.py` — `TransactionCreate`, `TransactionItem`, `TransactionListResponse`, `RealizedPnlItem`, `RealizedPnlResponse`.
- **프론트엔드 API**: `frontend/src/api/portfolio.ts`(+빌드 산출물 `.js`) — `postTransaction`, `getTransactions`, `deleteTransaction`, `getRealizedPnl`.
- **프론트엔드 UI**: 포트폴리오 상세의 거래 원장 패널/뷰(`.tsx` + `.js`) — 거래 입력 폼·거래 목록·전체 실현손익.
- **백엔드 단위 테스트**: `backend/tests/unit/test_transactions_049.py`(pytest, sync 픽스처 DB).
- **프론트엔드 단위 테스트**: `frontend/src/__tests__/transactions_049.test.tsx`(vitest + React Testing Library, API 모킹).

### 2.2 Out-of-Scope (제외 — What NOT to Build)

> [HARD] 본 SPEC 은 아래 항목을 명시적으로 제외한다.

- **자동 매매·자동 주문 실행** (규제·책임 리스크로 프로젝트 **영구 제외**). 본 SPEC 은 **수동 매매 원장(trade journal)** 이며 어떤 주문도 실행하지 않는다.
- **증권사 API 연동·거래내역 자동 임포트** — 거래는 사용자가 수동 입력한다(브로커 연동 없음).
- **`PortfolioHolding` 자동 동기화** — 거래 기록이 홀딩스의 `quantity`·`avg_buy_price` 를 자동 갱신하지 않는다. 거래 원장은 **독립 원장**이며 기존 홀딩스 로직을 변경하지 않는다(향후 SPEC).
- **FIFO·개별법(lot) 원가 추적** — **이동평균 원가법(총평균)** 단일 방식만 지원한다.
- **양도소득세·거래세·세율 계산** — 실현손익 원금만 산출하며 세금 계산은 제외한다.
- **통화 환산 실현손익(USD→KRW)** — 각 거래는 입력된 표시통화 그대로 집계하며 환율 환산은 제외한다(fx_rate 별도).
- **미실현(평가) 손익** — 실시간 시세 기반 미실현손익은 기존 performance(030)·benchmark(034) 모듈이 담당한다. 본 SPEC 은 **실현손익만** 다룬다.
- **배당 소득 원장** — 배당은 SPEC-019/033 별도 도메인이며 거래 원장에 포함하지 않는다.
- **거래 수정(edit)** — 생성·조회·삭제만 지원한다(수정은 삭제 후 재생성).
- **거래 기록 관련 알림·인박스 이벤트** — 거래 기록은 알림을 발생시키지 않는다.
- **공유 포트폴리오에 대한 거래 원장 공개** — 거래 내역은 소유자 전용이며 공개 공유(042)에 노출하지 않는다.

---

## 3. 요구사항 (Requirements — EARS)

> REQ 번호는 거래 원장 도메인 신규 접두사 `REQ-TXN-` 로 001 부터 부여한다(홀딩스·댓글·좋아요·피드 등 기존 접두사와 충돌 회피). 모든 REQ 는 관찰 가능한 동작을 단일 SHALL 로 기술한다.

### 3.1 거래 기록·검증 (REQ-TXN-001 ~ 005)

- **REQ-TXN-001**: When a user submits a BUY transaction for a portfolio they own, the system SHALL persist the transaction recording its side as BUY together with its quantity, price, and fee.
- **REQ-TXN-002**: When a user submits a SELL transaction whose quantity does not exceed the net held quantity (cumulative BUY quantity minus cumulative SELL quantity) for that ticker and market, the system SHALL persist the transaction recording its side as SELL.
- **REQ-TXN-003**: If a user submits a SELL transaction whose quantity exceeds the net held quantity for that ticker and market, then the system SHALL reject the request and SHALL NOT persist the transaction.
- **REQ-TXN-004**: If a user submits a transaction whose quantity or price is not positive, then the system SHALL reject the request.
- **REQ-TXN-005**: If a user submits a transaction for a portfolio they do not own, then the system SHALL reject the request with a not-found error.

### 3.2 거래 조회·삭제 (REQ-TXN-006 ~ 008)

- **REQ-TXN-006**: When a user requests the transaction list for a portfolio they own, the system SHALL return the transactions ordered by trade time newest-first.
- **REQ-TXN-007**: When the transaction list is paginated, the system SHALL page over that portfolio's transactions and report the total transaction count.
- **REQ-TXN-008**: When a user deletes a transaction belonging to a portfolio they own, the system SHALL remove that transaction.

### 3.3 실현손익 계산 (REQ-TXN-009 ~ 013)

- **REQ-TXN-009**: When realized profit and loss is requested for a portfolio, the system SHALL compute per-ticker realized profit and loss using the moving-average cost basis over that ticker's transactions in trade-time order.
- **REQ-TXN-010**: When a SELL transaction is processed during realized profit and loss computation, the system SHALL add to realized profit and loss the sale proceeds net of the sell fee minus the average cost of the sold quantity.
- **REQ-TXN-011**: When a BUY transaction is processed during realized profit and loss computation, the system SHALL include that BUY's fee in the ticker's cost basis.
- **REQ-TXN-012**: When realized profit and loss is requested, the system SHALL return the sum of all per-ticker realized profit and loss as the portfolio total.
- **REQ-TXN-013**: Where a ticker has BUY transactions but no SELL transactions, the system SHALL report zero realized profit and loss for that ticker.

### 3.4 프론트엔드 (REQ-TXN-014 ~ 016)

- **REQ-TXN-014**: Where the transaction ledger view is rendered for a portfolio, the page SHALL provide a form to submit a new transaction.
- **REQ-TXN-015**: When a transaction submission succeeds, the page SHALL display the new transaction in the transaction list without requiring a full page reload.
- **REQ-TXN-016**: Where realized profit and loss is available, the page SHALL display the portfolio's total realized profit and loss.

---

## 4. 인수 조건 (Acceptance Criteria — EARS)

> 모든 AC 는 EARS(Event-driven / State-driven / Unwanted behavior) 형식으로 작성하며, 각 AC 는 단일 관찰 가능 동작(단일 SHALL)만 검증한다. 총 12개.

### AC-049-001 — 매수 거래 기록 (REQ-TXN-001)

When a user submits a BUY transaction for a portfolio they own,
the system shall persist a transaction whose stored side equals BUY with the submitted quantity, price, and fee.

### AC-049-002 — 보유 이내 매도 기록 (REQ-TXN-002)

When a user submits a SELL transaction of 5 shares for a ticker whose net held quantity is 10,
the system shall persist a transaction whose stored side equals SELL.

### AC-049-003 — 보유 초과 매도 거부 (REQ-TXN-003)

If a user submits a SELL transaction of 15 shares for a ticker whose net held quantity is 10,
then the system shall reject the request and persist no transaction.

### AC-049-004 — 음수/영 수량·가격 거부 (REQ-TXN-004)

If a user submits a transaction whose quantity is zero or whose price is negative,
then the system shall reject the request.

### AC-049-005 — 타인 포트폴리오 거부 (REQ-TXN-005)

If a user submits a transaction for a portfolio owned by another user,
then the system shall reject the request with a not-found (404) error.

### AC-049-006 — 목록 최신순 (REQ-TXN-006)

When a user requests the transaction list for a portfolio with three transactions,
the system shall return them ordered by trade time newest-first.

### AC-049-007 — 페이지네이션 총계 (REQ-TXN-007)

When the transaction list is requested with a page size smaller than the portfolio's transaction count,
the system shall report the full transaction count as the total.

### AC-049-008 — 거래 삭제 (REQ-TXN-008)

When a user deletes a transaction belonging to a portfolio they own,
the system shall remove that transaction from the ledger.

### AC-049-009 — 이동평균 실현손익 (REQ-TXN-009·010·011)

When realized P&L is computed for a ticker with BUY 10 @ 1000 (fee 0), BUY 10 @ 2000 (fee 0), then SELL 5 @ 3000 (fee 0),
the system shall report that ticker's realized profit and loss as 7500.

### AC-049-010 — 전체 합계 (REQ-TXN-012)

When realized P&L is requested for a portfolio whose tickers have per-ticker realized values,
the system shall report the portfolio total equal to the sum of all per-ticker realized values.

### AC-049-011 — 매도 없으면 0 (REQ-TXN-013)

Where a ticker has only BUY transactions and no SELL transactions,
the system shall report zero realized profit and loss for that ticker.

### AC-049-012 — 프론트 폼·리로드 없는 표시·총 실현손익 (REQ-TXN-014·015·016)

Where the transaction ledger view has a submit form and a newly submitted transaction,
the page shall render the new transaction in the list without a full page reload and display the portfolio's total realized profit and loss.

---

## 5. 기술 설계 (Technical Approach)

### 5.1 스키마 (마이그레이션 0030)

- `0030_portfolio_transactions_049.py`: `down_revision = "0029"`.
  - `op.create_table("portfolio_transactions", ...)`:
    - `id` Integer PK autoincrement.
    - `portfolio_id` Integer, `ForeignKey("portfolios.id", ondelete="CASCADE")`, not null.
    - `krx_code` String(10) not null (기존 홀딩스 컬럼명 규약과 일치 — KRX 코드 또는 해외 티커).
    - `market` String(10) not null, `server_default="KRX"`.
    - `side` String(4) not null (`"BUY"` | `"SELL"`).
    - `quantity` Integer not null.
    - `price` Numeric(10, 2) not null.
    - `fee` Numeric(10, 2) not null, `server_default="0"`.
    - `traded_at` `DateTime(timezone=True)` not null.
    - `created_at` `DateTime(timezone=True)`, `server_default=func.now()`, not null.
  - `op.create_index("ix_portfolio_transactions_portfolio_ticker", "portfolio_transactions", ["portfolio_id", "krx_code"])`.
  - `downgrade`: 인덱스·테이블 역순 제거.
- **모델**(`models.py` `PortfolioTransaction`): 위 컬럼을 `Mapped[...]` 로 선언. `portfolio: Mapped["Portfolio"] = relationship("Portfolio", lazy="noload")`. `Decimal` 사용은 기존 `PortfolioHolding.avg_buy_price`(`Numeric(10,2)`) 패턴과 일치.

### 5.2 거래 원장 서비스 (`transactions.py`, sync)

- 모든 함수는 `db: Session` 을 받는 **sync** 함수다(기존 `service.add_holding`/`remove_holding` 패턴 준수). async 컨텍스트를 호출하지 않는다.
- `record_transaction(db, portfolio_id, user_id, krx_code, market, side, quantity, price, fee, traded_at)`:
  1. 소유권 확인: `portfolios.id == portfolio_id AND user_id == user_id`. 없으면 404(REQ-TXN-005).
  2. `quantity <= 0` 또는 `price < 0` 이면 거부(REQ-TXN-004, 400/422). (수량은 양의 정수, 가격은 음수 금지; fee 도 음수 금지.)
  3. `side == "SELL"` 이면 순보유수량 검증: 같은 `(portfolio_id, krx_code, market)` 의 `SUM(BUY.quantity) - SUM(SELL.quantity)` 계산 → `sell_qty` 초과 시 거부(REQ-TXN-003, 400/409). `side == "BUY"` 는 이 검증을 건너뛴다.
  4. 저장 후 반환(REQ-TXN-001·002).
- `list_transactions(db, portfolio_id, user_id, page, size)`: 소유권 확인 후 `traded_at DESC`(동시각은 `id DESC` 보조 정렬) offset/limit, `total = count`(REQ-TXN-006·007).
- `delete_transaction(db, portfolio_id, transaction_id, user_id)`: `portfolio → user` 체인 소유권 확인. 없으면 404. 있으면 삭제(REQ-TXN-008).
- `compute_realized_pnl(db, portfolio_id, user_id)`:
  1. 소유권 확인.
  2. 해당 포트폴리오의 모든 거래를 `traded_at ASC, id ASC` 로 조회.
  3. `(krx_code, market)` 별로 **이동평균 원가법** 리플레이:
     - 상태: `position`(수량), `cost`(총원가). `avg = cost / position`(`position > 0` 일 때).
     - **BUY**: `cost += price*quantity + fee`; `position += quantity`(REQ-TXN-011 — 매수 수수료를 원가에 산입).
     - **SELL**: `avg_cost = cost/position`; `realized += (price*quantity - fee) - avg_cost*quantity`(REQ-TXN-010 — 매도대금에서 매도수수료 차감 후 매도수량의 평균원가 차감); `cost -= avg_cost*quantity`; `position -= quantity`(avg 는 이동평균이므로 매도 시 불변).
  4. 종목별 `realized` 를 `RealizedPnlItem` 으로, 합계를 `total_realized_pnl` 로 반환(REQ-TXN-009·012·013 — 매도 없으면 realized=0).
- **수치 예시(설계 앵커, AC-049-009)**: BUY 10@1000 → avg 1000, pos 10, cost 10000. BUY 10@2000 → cost 30000, pos 20, avg 1500. SELL 5@3000, fee 0 → realized += (15000-0) - 1500*5 = 15000 - 7500 = **7500**. pos 15, cost 22500.

### 5.3 엔드포인트·스키마

- `router.py`(기존 portfolio 라우터에 추가, 홀딩스와 동일 패턴):
  - `POST /{portfolio_id}/transactions` → 201, 바디 `TransactionCreate`. 서비스 검증 실패는 `HTTPException`(404/400/409)으로 매핑.
  - `GET /{portfolio_id}/transactions?page=&size=` → `TransactionListResponse`.
  - `DELETE /{portfolio_id}/transactions/{transaction_id}` → 204.
  - `GET /{portfolio_id}/realized-pnl` → `RealizedPnlResponse`.
  - 각 엔드포인트는 `db: Session = Depends(get_db_session)`, `current_user: User = Depends(get_current_user)`.
- `schemas.py`:
  - `TransactionCreate`: `krx_code: str`, `market: str = "KRX"`, `side: Literal["BUY","SELL"]`, `quantity: int`, `price: Decimal`, `fee: Decimal = 0`, `traded_at: datetime`.
  - `TransactionItem`: 위 필드 + `id`, `created_at`.
  - `TransactionListResponse`: `items: list[TransactionItem]`, `total: int`, `page: int`, `size: int`.
  - `RealizedPnlItem`: `krx_code: str`, `market: str`, `realized_pnl: Decimal`.
  - `RealizedPnlResponse`: `items: list[RealizedPnlItem]`, `total_realized_pnl: Decimal`.

### 5.4 프론트엔드 (`portfolio.ts`, 거래 원장 뷰)

- `portfolio.ts`: `postTransaction(portfolioId, body)`, `getTransactions(portfolioId, page, size)`, `deleteTransaction(portfolioId, txId)`, `getRealizedPnl(portfolioId)`. 타입에 `TransactionItem`·`RealizedPnlResponse` 추가.
- 거래 원장 뷰(`.tsx`): 거래 입력 폼(종목·시장·매수/매도·수량·가격·수수료·거래일, REQ-TXN-014), 제출 성공 시 로컬 상태에 append 하여 리로드 없이 목록 갱신(REQ-TXN-015), 상단/요약에 전체 실현손익 표시(REQ-TXN-016). 삭제 버튼(REQ-TXN-008 연동).

### 5.5 빌드 산출물 동기화 (.js/.ts 페어)

- 본 프로젝트는 `.tsx`/`.ts` 소스와 커밋된 `.js` 빌드 산출물을 **쌍으로** 유지한다. 수정한 모든 프론트 소스(`portfolio.ts`, 거래 원장 `.tsx`)는 대응 `.js` 도 함께 갱신한다. 백엔드 Python 파일은 빌드 산출물 페어가 없다.

---

## 6. 테스트 목록 (Test Plan)

- 백엔드: `backend/tests/unit/test_transactions_049.py`(pytest, sync 픽스처 DB). 신규 외부 의존성 없음.
- 프론트엔드: `frontend/src/__tests__/transactions_049.test.tsx`(vitest + React Testing Library, `portfolio` API 모듈 모킹).

| ID | 테스트 | 검증 REQ / AC |
|----|--------|---------------|
| T-049-001 | 매수 거래 기록 → side=BUY·수량·가격·수수료 저장 확인 | REQ-TXN-001 / AC-001 |
| T-049-002 | 순보유 10주에 5주 매도 → side=SELL 저장 | REQ-TXN-002 / AC-002 |
| T-049-003 | 순보유 10주에 15주 매도 → 거부, 거래 미생성 | REQ-TXN-003 / AC-003 |
| T-049-004 | 수량 0 또는 가격 음수 → 거부 | REQ-TXN-004 / AC-004 |
| T-049-005 | 타인 포트폴리오 거래 → 404 | REQ-TXN-005 / AC-005 |
| T-049-006 | 거래 3건 목록 → traded_at 최신순 반환 | REQ-TXN-006 / AC-006 |
| T-049-007 | size < 거래수 → total=전체 거래수 | REQ-TXN-007 / AC-007 |
| T-049-008 | 소유 거래 삭제 → 원장에서 제거 | REQ-TXN-008 / AC-008 |
| T-049-009 | BUY 10@1000·BUY 10@2000·SELL 5@3000 → 종목 realized=7500 | REQ-TXN-009·010·011 / AC-009 |
| T-049-010 | 다종목 per-ticker realized → total=합계 | REQ-TXN-012 / AC-010 |
| T-049-011 | 매수만 있는 종목 → realized=0 | REQ-TXN-013 / AC-011 |
| T-049-012 | 프론트 폼 제출 → 리로드 없이 목록 추가 + 전체 실현손익 표시 | REQ-TXN-014·015·016 / AC-012 |

품질 게이트: 백엔드 pytest 통과(커버리지 기준 충족), 프론트 vitest 통과, ESLint·ruff 통과, 신규 외부 의존성 0, **신규 테이블 1개(마이그레이션 0030)**, `.js`/`.ts` 페어 동기화, scipy 미사용(numpy/표준 라이브러리만).

---

## 7. HISTORY

| Version | Date | Author | Note |
|---------|------|--------|------|
| 0.1.0 | 2026-07-01 | ircp | 최초 초안 — 소셜 아크(042~048) 완료 후 신규 도메인 개설. 포트폴리오 **거래 원장(transaction ledger)** 과 **이동평균 원가법 실현손익(realized P&L)** 도입. 신규 테이블 `portfolio_transactions` 1개(마이그레이션 0030, down_revision 0029). 거래 원장 서비스는 sync(`Session`) — 기존 홀딩스 CRUD 패턴 준수. 기존 `PortfolioHolding` 로직 불변(독립 원장, 자동 동기화 없음). 매매 원장은 수동 기록이며 자동 매매·주문 실행과 무관(영구 제외). REQ-TXN-001~016(16개), AC-049-001~012(12개), 테스트 T-049-001~012(12개). |

---

## 8. 의존성 (Dependencies)

- **SPEC-STOCK-028** (해외 자산 지원): `PortfolioHolding` 의 `krx_code`·`market` 컬럼 규약 — 거래 원장의 종목 식별 컬럼 규약을 재사용한다(홀딩스 로직 자체는 변경하지 않음).
- **포트폴리오 기반 인프라**: `Portfolio` 모델·`get_db_session`·`get_current_user`·portfolio `router.py` — 소유권 확인·의존성 주입 패턴 재사용.

## 9. 기술 제약 (Technical Constraints)

- **거래 원장 서비스는 sync(`Session`)** 이다(기존 `service.add_holding`/`remove_holding` 패턴). async 컨텍스트를 호출하지 않는다(sync/async 혼용 금지).
- **이동평균 원가법 단일 방식**: 실현손익은 이동평균(총평균) 원가법으로만 산출한다. FIFO/개별법 로트 추적은 제외(§2.2).
- **독립 원장**: 거래 기록은 `PortfolioHolding` 을 자동 갱신하지 않는다. 기존 홀딩스·performance·benchmark 로직을 변경하지 않는다.
- **표시통화 그대로 집계**: 실현손익은 각 거래의 입력 통화 단위로 집계하며 환율 환산을 수행하지 않는다(§2.2). (혼합 통화 종목은 종목별로 분리 집계되므로 통화 혼동이 발생하지 않는다.)
- **매도 검증**: SELL 은 같은 `(portfolio_id, krx_code, market)` 순보유수량(누적 BUY − 누적 SELL) 이내여야 한다. 초과 시 거부(REQ-TXN-003).
- **수치 타입**: 금액은 `Numeric(10,2)`/`Decimal` 로 저장·계산한다(기존 `avg_buy_price` 패턴). 실현손익 계산은 `Decimal` 로 수행하여 부동소수 오차를 피한다.
- **정렬 안정성**: 목록·리플레이는 `traded_at` 기준 정렬하되 동일 시각 거래는 `id` 를 보조 정렬 키로 사용해 결정적 순서를 보장한다.
- **CASCADE 삭제**: `portfolio_id` FK 는 `ondelete=CASCADE` — 포트폴리오 삭제 시 거래 원장이 함께 제거된다.
- **소유자 전용**: 거래 원장·실현손익은 소유자만 조회·수정할 수 있으며 공개 공유(042)에 노출하지 않는다(§2.2).
- React + TypeScript(`.tsx`/`.ts`) 소스, Vite 빌드. 커밋된 `.js` 산출물과 페어 동기화 필수.
- ESLint·ruff 통과, 신규 외부 의존성 금지, scipy 미사용, 모든 신규 동작 단위 테스트 필수.
