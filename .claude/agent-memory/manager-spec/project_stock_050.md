---
name: project-stock-050
description: SPEC-STOCK-050 거래 기반 홀딩스 동기화 — 049 후속(첫 이연항목), 신규 테이블 0(txn 0030 + holdings 028 재사용), 이동평균 재계산, 미리보기 diff + 적용
metadata:
  type: project
---

SPEC-STOCK-050 — 거래 기반 홀딩스 동기화 (Transaction-to-Holdings Reconciliation). SPEC-049(거래 원장) 후속. **049 가 가장 먼저 이연한 항목**(`PortfolioHolding` 자동 동기화)을 구현.

**Why:** 049 독립 원장 → 매매를 거래원장·홀딩스에 **이중 입력**해야 하는 마찰. 원장을 진실 소스로 삼아 이동평균 원가법으로 홀딩스를 재계산·동기화하면 이중 입력 제거. 미리보기(diff) 먼저 제공 → 기존 수동 홀딩스 덮어쓰기 전 검토(안전).

**실제 049 구현 확인(중요 — 049 written spec 과 코드가 상이):**
- `PortfolioTransaction` 실제 컬럼: `txn_type`(BUY/SELL, NOT `side`), `krx_code` String(20), `quantity` Int, `price` Numeric(18,2), `txn_date` **Date**, `note` Text, created_at. **fee·market 컬럼 없음.** (049 spec.md 는 side/fee/market/traded_at 라 썼으나 코드는 다름.)
- 소유권 확인 `_verify_portfolio_owner` → **403**(NOT 404).
- SELL net_qty 검증은 krx_code 전체 누적(BUY−SELL), market 무관.
- 최신 마이그레이션 = **0030**. → 050 신규 마이그 **0개**.

**How to apply (구현 시 핵심 제약):**
- **신규 테이블·마이그레이션 0**. 재사용: `portfolio_transactions`(0030) + `portfolio_holdings`(028: krx_code String(10), quantity Int, avg_buy_price Numeric(10,2), market default KRX, currency KRW, UNIQUE(portfolio_id,krx_code,market)).
- **서비스 sync**(`holdings_sync.py`, `db: Session`): `compute_ledger_positions`(txn_date ASC,id ASC 리플레이 이동평균), `preview_sync`(diff added/updated/removed, 저장 미변경), `apply_sync`(upsert/remove, market=KRX). async 혼용 금지.
- **이동평균**: BUY: cost+=price*qty, pos+=qty. SELL: avg=cost/pos; cost-=avg*qty; pos-=qty (avg 불변). pos==0 → 홀딩 제거. **수치앵커(AC-003)**: BUY10@1000·BUY10@2000·SELL5@3000 → 홀딩 qty=15·avg=**1500**.
- **명시적 동기화만**: 049 add/delete_transaction 자동 트리거 **금지**(049 독립원장 계약·기존 12 테스트 보존). 사용자가 preview/apply 명시 요청 시만.
- **원장 종목만 동기화**: 원장에 거래 없는 홀딩스는 보존(삭제·수정 안 함).
- **KRX 시장 대상**(txn 에 market 없음). 해외 원장 동기화는 향후 SPEC.
- **원장 불일치**: 누적 SELL > 누적 BUY(049 delete 로 발생 가능) → 동기화 전체 거부, 홀딩스 불변(REQ-SYNC-011).
- **엔드포인트**: `GET /portfolios/{id}/holdings/sync/preview`, `POST /portfolios/{id}/holdings/sync`. get_db_session+get_current_user, 소유권 403, HTTPException 400/409.
- **스키마**: SyncPreviewItem(krx_code, change Literal[added/updated/removed], quantity, avg_buy_price), SyncPreviewResponse(items, has_changes), SyncApplyResponse(synced, holdings).
- **제외**: 자동매매(영구), 증권사연동/임포트, 거래시 자동트리거, 원장없는 수동홀딩스 삭제, 해외시장 원장동기화, FIFO, 실현손익 재정의(049 담당), 동기화 이력/알림, 통화환산·수수료(txn 에 fee 없음).
- **프론트**: `portfolio.ts`(+.js) previewHoldingsSync·applyHoldingsSync, 동기화 패널(.tsx+.js) 미리보기 diff·적용 리로드없음. `.js`/`.ts` 페어 동기화 필수.

REQ 16(REQ-SYNC-001~016)·AC 11(AC-050-001~011)·테스트 11(T-050-001~011). 신규 접두사 `REQ-SYNC-`. 파일 spec.md 단일. 자체 감사 PASS(D1 0건).
