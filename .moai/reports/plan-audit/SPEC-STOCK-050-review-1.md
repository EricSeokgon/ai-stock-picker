# Plan Audit — SPEC-STOCK-050 (거래 기반 홀딩스 동기화) — Review 1

- **Auditor**: manager-spec self-audit
- **Date**: 2026-07-01
- **Verdict**: PASS (D1 defects: 0)

## 1. Scope & Classification

- Correctly classified as SPEC (feature to build), not a report. Directory structure `.moai/specs/SPEC-STOCK-050/spec.md` (no flat file). PASS.
- `## 2.2 Out-of-Scope (What NOT to Build)` present with 10 explicit exclusions incl. permanent auto-trading exclusion. PASS.

## 2. EARS Compliance

- All 16 REQs (REQ-SYNC-001~016) use EARS keywords (When/Where/If...then) with a single SHALL each. PASS.
- All 11 ACs (AC-050-001~011) are single-SHALL, observable, EARS-formatted (Event/State/Unwanted). PASS.
- REQ→AC→Test traceability table complete; every AC maps to ≥1 REQ and every test maps to an AC. PASS.

## 3. Grounding Against Actual Implementation (critical)

- **Verified actual model** `PortfolioTransaction`: `txn_type`(not `side`), `krx_code` String(20), `price` Numeric(18,2), `txn_date` Date, `note` (no `fee`, no `market`). SPEC-050 designed against ACTUAL code, not SPEC-049's divergent written spec. PASS — avoids D1 defect.
- **Owner check**: `_verify_portfolio_owner` raises **403** (confirmed in transactions.py:29). REQ-SYNC-006/AC-006 + §9 say 403 (not 404). PASS.
- **Holdings model**: `avg_buy_price` Numeric(10,2), UNIQUE(portfolio_id, krx_code, market). Sync targets market="KRX" documented as constraint (txn has no market column). PASS.
- **Latest migration = 0030** (confirmed). SPEC-050 correctly declares **zero new migrations/tables** — precedent: 044/045/047 had 0. PASS.

## 4. Numeric Anchor Consistency

- Anchor BUY 10@1000 · BUY 10@2000 · SELL 5@3000 → holding qty 15, avg 1500. Moving-average replay verified: cost 30000/pos 20 → avg 1500; SELL 5 → cost 22500/pos 15 → avg 1500. Consistent with SPEC-049 realized-P&L anchor (same trade sequence). PASS.

## 5. Consistency / Non-Regression

- Explicitly does NOT modify 049's `add_transaction`/`delete_transaction`/`get_realized_pnl` (independent-ledger contract + existing tests preserved). Sync is explicit-only (no auto-trigger). PASS — avoids breaking 049's 12 tests.
- "Preserve manual holdings not in ledger" rule prevents destructive overwrite. Ledger-inconsistency rejection (REQ-SYNC-011) handles the delete-a-BUY edge case reachable via 049's delete_transaction. PASS.

## 6. Complexity Bounds

- 16 REQs / 11 ACs / 11 tests — within target band (10~16 REQs, 9~12 ACs). Zero new tables. Sync service in new file `holdings_sync.py`, 2 endpoints, 3 schemas, 2 frontend functions. Medium complexity, matches recent SPEC cadence. PASS.

## 7. Minor Observations (non-blocking, D2/D3)

- D3: `avg_buy_price` Numeric(10,2) could truncate very high KRW prices (>99,999,999.99) — acceptable for KRW equities; documented in §5.1. No action.
- D3: `SyncApplyResponse.holdings` schema shape left as summary ("...") — acceptable at spec granularity; finalized in Run. No action.

## Conclusion

No D1 (blocking) defects. SPEC is internally consistent, grounded in the actual codebase, EARS-compliant, and correctly scoped. Ready for /moai run.
