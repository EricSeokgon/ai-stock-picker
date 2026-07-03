# Plan Audit — SPEC-STOCK-048 (공유 포트폴리오 댓글 대댓글) — Review 1

- Auditor: manager-spec (self-audit)
- Date: 2026-07-01
- Verdict: PASS (D1 defects fixed in-session)

## Scope Summary

SPEC-STOCK-048 extends SPEC-046 flat comments into single-level threaded replies. Reuses `portfolio_comments` with one new nullable self-FK column (`parent_comment_id`) via migration 0029. Reply notifications reuse `type="portfolio_comment"` + `krx_code=f"P{id}"`, so SPEC-047 deep-links apply automatically with no inbox_router change. Comment service stays sync.

- REQ count: 15 (REQ-REPLY-001~015)
- AC count: 12 (AC-048-001~012)
- Test count: 12 (T-048-001~012)
- New tables: 0 (migration 0029 = one column add)
- New external deps: 0

## Checklist

| Check | Result | Note |
|-------|--------|------|
| EARS compliance (When/If/Where + SHALL) | PASS | All 15 REQs and 12 ACs use EARS keywords |
| Single SHALL per AC | PASS | Each AC has exactly one SHALL |
| Exclusions section present | PASS | §2.2 with auto-trading (permanent) + 10 explicit exclusions |
| No implementation names as requirements | PASS | REQs use domain contract terms (`parent_comment_id` is the API field, consistent with 047's `link`/`krx_code`) |
| Migration numbering | PASS | 0029, down_revision=0028 (0028 confirmed latest on disk) |
| Sync/async boundary respected | PASS | §8 constraint: comment service sync; no async inbox_router call |
| REQ ↔ AC ↔ Test traceability | PASS (after fix) | See D1 fixes below |
| Reuses existing infra | PASS | portfolio_comments, add_comment/list_comments, Notification 046 pattern, 047 deep-link |
| No auto-trading | PASS | §2.2 first exclusion |

## D1 Defects Found and Fixed

1. **Traceability mismatch on REQ-REPLY-010**: Original REQ-010 stated "no additional owner notification" but AC-048-009 / T-048-009 verified CASCADE deletion — the REQ and its AC tested different behaviors, leaving CASCADE deletion without a REQ and the no-owner-notify rule untested.
   - Fix: Redefined REQ-REPLY-010 as the delete-cascade rule (new §3.4). Moved "no additional owner notification" to a §8 technical constraint (behavioral rule, not a testable observable distinct from the parent-author notification). AC-009 header corrected to (REQ-REPLY-010).

2. **REQ-REPLY-011 (reply author display name) lacked AC coverage**: Fixed by extending AC-048-005 to assert each reply includes its author's display name (still single SHALL).

3. **REQ-REPLY-015 (no full-page reload) lacked AC coverage**: Fixed by extending AC-048-012 to cover a newly submitted reply rendering nested without reload; T-048-012 updated accordingly.

4. **Stale REQ reference in §5.2 step 6**: Referenced old REQ-010 meaning; repointed to §8 constraint and added an explicit delete-cascade design line mapping to REQ-REPLY-010.

## Residual Risks (non-blocking)

- Reusing `type="portfolio_comment"` means reply notifications show the "댓글" badge, not a distinct "답글" badge. Accepted and documented in §2.2 / §8. A future SPEC could add a dedicated type + badge + inbox_router deep-link extension.
- Daily notification idempotency (UNIQUE + IntegrityError rollback) merges multiple same-day replies to the same author/portfolio into one notification. Accepted (matches SPEC-043/046 behavior), documented in §8.
- CHANGELOG for SPEC-046 mentions `deleted_at`/`updated_at` soft-delete on `portfolio_comments`, but migration 0028 and the ORM model have neither (hard delete). SPEC-048 correctly assumes hard delete + CASCADE. No action needed for 048; noted for accuracy.

## Verdict

PASS. All D1 traceability defects fixed in-session. 15 REQ / 12 AC / 12 test with clean 1:1 or documented grouped mapping. Ready for /moai run.
