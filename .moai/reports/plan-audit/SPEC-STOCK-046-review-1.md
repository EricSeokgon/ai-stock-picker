# Plan Audit — SPEC-STOCK-046 (공유 포트폴리오 댓글) — Review 1

Date: 2026-07-01
Auditor: manager-spec (self-audit, plan-auditor checklist)
Verdict: PASS (no D1 defects)

---

## Scope verified

Feature: Shared Portfolio Comments — adds plain-text comments to public shared portfolios
(`/shared/{token}`), extending the social arc (042 share+like → 043 like-notif → 044 FE →
045 trending/search → 046 comments). New table `portfolio_comments` (migration 0028,
down_rev=0027), `PortfolioComment` model, create/list/delete endpoints, owner inbox
notification (`portfolio_comment`), SharedPortfolio comment UI, inbox badge.

---

## Checklist

| # | Check | Result | Notes |
|---|-------|--------|-------|
| 1 | Directory format `.moai/specs/SPEC-STOCK-046/spec.md` | PASS | Not a flat file |
| 2 | ID uniqueness | PASS | No prior SPEC-STOCK-046; 045 is latest |
| 3 | Frontmatter 8 fields (id,version,status,created,updated,author,priority,issue_number) | PASS | author=ircp, status=draft, version=0.1.0 |
| 4 | EARS compliance (all REQs) | PASS | When/If...then/Where + single SHALL each |
| 5 | Single SHALL per AC | PASS | 18 ACs, each one observable behavior |
| 6 | Exclusions section (`2.2 Out-of-Scope`) present, ≥1 entry | PASS | 11 explicit exclusions incl. permanent auto-trading |
| 7 | No implementation leakage in §3 Requirements | PASS | Function/schema names confined to §5 Technical Approach |
| 8 | REQ → AC → Test traceability | PASS | All 21 REQs covered by 18 tests; see matrix below |
| 9 | Korean body, English code identifiers | PASS | EARS keywords + identifiers in English |
| 10 | Reuses existing infra, no needless new tables | PASS | 1 new table justified (text content has no existing home); reuses share/notification infra |

---

## Codebase-fact verification (anti-hallucination)

- `User.username` exists (models.py:34, String(50) unique) — used for `CommentItem.username`. CONFIRMED.
- Migration head = `0027` (revision="0027", down_revision="0026") → 0028 down_rev=0027 correct. CONFIRMED.
- `PortfolioLike.share_id` references `portfolio_shares.id` (not portfolio_id) → `PortfolioComment` mirrors this. CONFIRMED.
- `add_like` notification pattern: `krx_code=f"P{portfolio.id}"`, `UNIQUE(user_id,type,krx_code,ref_date)`,
  IntegrityError→rollback for daily idempotency. Reused for `portfolio_comment`. CONFIRMED (sharing.py:254-273).
- `Notification.krx_code` String(10), `type` String(20) — `portfolio_comment` (17 chars) fits type;
  `f"P{id}"` fits krx_code. `portfolio_like` vs `portfolio_comment` differ in type → no UNIQUE collision. CONFIRMED.
- Public router registration pattern (`shared_router`, `like_router`, prefix-less, main.py:123-124) → new
  comment endpoints follow same pattern. CONFIRMED.
- `Notifications.tsx` TypeBadge label/color maps (lines 17,23) → add `portfolio_comment`. CONFIRMED.

---

## Traceability matrix (REQ → Test)

| REQ | Test |
|-----|------|
| REQ-COMMENT-001..005 (create) | T-046-001..005 |
| REQ-COMMENT-006..009 (list) | T-046-006..009 |
| REQ-COMMENT-010..013 (delete) | T-046-010..013 |
| REQ-COMMENT-014 (notif) | T-046-014 |
| REQ-COMMENT-015,016 (notif suppress) | T-046-015 |
| REQ-COMMENT-017 (FE submit) | T-046-016 |
| REQ-COMMENT-018,020 (FE load / empty) | T-046-017 |
| REQ-COMMENT-019,021 (FE delete control / badge) | T-046-018 |

All 21 REQs traced. No orphan REQs, no orphan tests.

---

## Findings

- D1 (blocking): none.
- D2 (should-fix): none.
- D3 (nice-to-have):
  - Frontend delete control scoped to author's own comments only; owner-moderation delete
    (REQ-COMMENT-011, backend-supported) has no frontend control. Documented as intentional in §5.6.
    Acceptable for medium scope; could be a follow-up.
  - Comment notification is daily-idempotent (at most one per owner/portfolio/day), so a burst of
    comments yields one notification. This is consistent with the like pattern and explicitly stated
    (REQ-COMMENT-016); not a defect.

## Verdict

PASS — ready for Run phase. No D1 defects to fix.
