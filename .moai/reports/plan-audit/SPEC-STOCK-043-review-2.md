# SPEC Review Report: SPEC-STOCK-043
Iteration: 2/3
Verdict: FAIL
Overall Score: 0.68

---

## Must-Pass Results

- [PASS] MP-1 REQ number consistency: REQ-SHARE-031 through REQ-SHARE-040 are fully covered with no gaps and no duplicates. Zero-padding is consistent (3 digits throughout). A naming asymmetry exists between 034a/034b and 039/039b (see D11), but this does not constitute a gap or duplicate per the strict MP-1 definition.

- [FAIL] MP-2 EARS format compliance: Five acceptance criteria (AC-043-001, AC-043-007, AC-043-008, AC-043-010, AC-043-011) contain multiple explicit "shall" clauses within a single criterion, violating the EARS single-response pattern "When [trigger], the [system] shall [response]." A criterion with two or three independent "shall" clauses does not match any of the five EARS patterns — it merges two or more EARS statements into one AC. See D1 through D5.

- [PASS] MP-3 YAML frontmatter validity: All six required fields are present with correct types. `id: SPEC-STOCK-043` (string), `version: 0.2.0` (string), `status: draft` (valid value), `created_at: 2026-06-29` (ISO date), `priority: medium` (valid value), `labels: [portfolio, sharing, social, notification, stats, backend, frontend]` (array). spec.md:L1-13.

- [N/A] MP-4 Section 22 language neutrality: This SPEC is scoped to a single-language Python project (ai-stock-picker). Python-specific references appear only in the Technical Design section, not in normative requirements. Criterion auto-passes.

---

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 — minor ambiguity in one or two requirements | REQs 031, 036, 037, 038 have compound SHALL clauses that a tester must interpret. REQ-039b (L116) omits the "then" keyword. All other requirements are precise and unambiguous. |
| Completeness | 1.00 | 1.0 — all sections present, frontmatter complete, at least one exclusion | HISTORY (L17-22), WHY (L36-39), WHAT/Scope (L26-65), REQUIREMENTS (L68-125), ACCEPTANCE CRITERIA (L128-213), 8 specific Exclusions (L53-65). All frontmatter fields present. |
| Testability | 0.75 | 0.75 — one AC is not precisely binary-testable but measurable with minor interpretation | Five compound-SHALL ACs (D1-D5) each contain 2-3 independently observable assertions that must be verified separately, meaning a single "PASS/FAIL on this AC" determination requires multi-step judgment. No weasel words found in any AC. |
| Traceability | 1.00 | 1.0 — every REQ has at least one AC; every AC references a valid REQ | REQ-031 → AC-001; REQ-032 → AC-002; REQ-033 → AC-003; REQ-034a → AC-004; REQ-034b → AC-005; REQ-035 → AC-006, AC-009; REQ-036 → AC-007, AC-008; REQ-037 → AC-010; REQ-038 → AC-011; REQ-039 → AC-012; REQ-039b → AC-012b; REQ-040a → AC-013; REQ-040b → AC-014. No orphaned ACs, no uncovered REQs. |

---

## Defects Found

### Critical (MP-2 violations — compound SHALL in acceptance criteria)

**D1. spec.md:L133-137** — AC-043-001 contains three separate "shall" clauses: "the system shall return 204 No Content", "the portfolio_likes row for that user shall be deleted", and "the derived like_count shall decrease by 1." Each is a distinct, independently observable outcome that could pass while the others fail. This does not match the EARS pattern "When [trigger], the [system] shall [response]" (singular response). Required fix: split into three separate ACs (one for 204 response, one for row deletion, one for like_count decrease), or combine the row deletion and count decrease into a single indivisible assertion under the 204 response. — Severity: critical

**D2. spec.md:L165-169** — AC-043-007 contains two explicit "shall" clauses: "the system shall return 200 (idempotent)" and "the count of `type=portfolio_like` notifications shall remain unchanged." A tester could confirm the 200 return without verifying the notification count, or vice versa. Required fix: split into two ACs (one verifying the idempotent 200, one verifying notification count unchanged), or rewrite as a single EARS criterion with a unified observable outcome. — Severity: critical

**D3. spec.md:L171-175** — AC-043-008 contains two explicit "shall" clauses: "the system shall return 403 Forbidden when `POST /shared/{share_token}/like` is called" and "no `portfolio_like` notification shall be created." The second assertion is an independent observable outcome from the same trigger. Required fix: split into two ACs or rewrite so the notification non-creation is expressed as a verification step within the single 403-response criterion. — Severity: critical

**D4. spec.md:L182-186** — AC-043-010 contains two explicit "shall" clauses testing two different HTTP endpoints: "the system shall include that notification in the unread count" (for `GET /notifications/unread-count`) and "`GET /notifications` shall include an item with `type=portfolio_like`" (a second endpoint call). A single EARS criterion must not span multiple distinct triggering actions. Required fix: split into two ACs, one per endpoint call. — Severity: critical

**D5. spec.md:L188-192** — AC-043-011 contains two explicit "shall" clauses: "the system shall upsert so that `share_view_stats.view_count = 2` for `(share_id, today)`" and "`portfolio_shares.view_count` shall also increase by 2." These are observations on two distinct tables and could diverge (one updated, the other not). Required fix: split into two ACs or make the second assertion a subordinate clause of the first via a single-shall formulation that describes both table updates as one atomic outcome. — Severity: critical

### Major (compound SHALL in requirements — normative text quality)

**D6. spec.md:L76** — REQ-SHARE-031 contains two SHALL clauses: "the system SHALL delete the like row and return 204 No Content" and a separate sentence "The derived `like_count` (= COUNT of `portfolio_likes`) SHALL decrease by 1." The second SHALL is a separate normative assertion. Required fix: move the `like_count` assertion to a separate REQ (e.g., REQ-SHARE-031b) or merge as a single observable outcome by dropping the second sentence and verifying count decrease only at the AC level. — Severity: major

**D7. spec.md:L102** — REQ-SHARE-036 contains two SHALL clauses: "the system SHALL NOT insert a new `Notification` row" and a second sentence "A `portfolio_like` notification SHALL only be created when a `portfolio_likes` row is actually inserted." The second sentence restates the first but as a positive-condition rule with its own SHALL. This is a compound REQ. Required fix: remove the second sentence (it is redundant with the first "SHALL NOT" clause) or convert to a cross-reference note. — Severity: major

**D8. spec.md:L106-107** — REQ-SHARE-037 contains two SHALL clauses: "the system SHALL include `type=portfolio_like` notifications in the response list, unread count... and read-marking... identically to other notification types" and "No new inbox endpoint SHALL be added." The second clause is a negative constraint that belongs in a separate REQ or in the Out-of-Scope section. Required fix: move the "No new inbox endpoint" constraint to a separate REQ-SHARE-037b or to the Out-of-Scope list at Section 2.2. — Severity: major

**D9. spec.md:L110** — REQ-SHARE-038 mixes two EARS patterns in one REQ. The first part uses Event-driven: "When `GET /shared/{share_token}` returns a successful public view response... the system SHALL upsert a row..." The second part adds a separate Unwanted-behavior clause: "If the share record is not public (404 response), no upsert SHALL occur." These are two distinct behaviors requiring separate patterns. Required fix: split into REQ-SHARE-038a (Event-driven: successful view → upsert) and REQ-SHARE-038b (Unwanted: non-public share → no upsert). — Severity: major

### Minor (naming inconsistency and EARS keyword omission)

**D10. spec.md:L116** — REQ-SHARE-039b reads "If the portfolio has no share record (`portfolio_shares` row does not exist), the system SHALL return 200 with 7 items all having `view_count=0`." The EARS Unwanted pattern requires "If [undesired condition], **then** the [system] shall [response]." The "then" keyword is absent. Required fix: insert "then" between the condition and the system clause. — Severity: minor

**D11. spec.md:L114/L116** — REQ-SHARE-039 (plain, L114) is retained alongside REQ-SHARE-039b (L116), but REQ-SHARE-034 and REQ-SHARE-040 were fully replaced by 034a/034b and 040a/040b (no plain 034 or 040 remains). The inconsistency creates a REQ where "039" implicitly serves as "039a" but is not labeled as such. The preamble note (L71-72) mentions only the 034/040 splits; the 039b addition is undocumented in that note. Required fix: either rename REQ-SHARE-039 to REQ-SHARE-039a and update the preamble, or document the 039/039b split pattern explicitly in the preamble note. — Severity: minor

---

## Chain-of-Verification Pass

Second-look findings: confirmed all v1 defects below; found additional REQ-level compound SHALL defects (D6-D9) and minor issues (D10-D11) not present in v1 report.

Re-read verification:
- Re-read every REQ from L74 to L124: all 13 REQs individually checked for EARS pattern and compound SHALL.
- Re-read every AC from L132 to L213: all 15 ACs individually checked for EARS pattern and "shall" count.
- Verified REQ numbering end-to-end (031 through 040b), not spot-checked.
- Verified traceability for all 13 REQs and all 15 ACs.
- Confirmed Exclusions section (8 entries, all specific and testable as exclusions).
- Checked for contradictions: none found between REQs. REQ-036 non-notification rule is consistent with REQ-033 (owner 403 blocks like creation). REQ-038 upsert rule is consistent with REQ-039 stats query.
- AC-043-006 (L159-163) was examined for borderline compound status: "the system shall return 200 **and** insert exactly one Notification row." This uses ONE "shall" with a compound response. Because the single "shall" governs a unified transactional action (respond with 200 indicating the combined operation succeeded), this is the least severe compound pattern and is not counted as a definitive MP-2 violation — but it is borderline and would benefit from being rewritten as two atomic ACs.

---

## Regression Check (Iteration 2)

Defects from iteration 1 (as described in the invocation prompt):

- **v1-MP-2 (All 14 ACs used Gherkin format)** — PARTIALLY RESOLVED: No Given/When/Then Gherkin structure remains in any AC. All ACs now use EARS trigger-response structure. However, compound SHALL clauses in ACs 001, 007, 008, 010, 011 constitute new MP-2 violations. MP-2 remains FAIL.

- **v1-D2 (REQ-031/032 mixed WHEN and IF pattern incorrectly)** — RESOLVED: REQ-SHARE-031 (L76) uses "When" (Event-driven). REQ-SHARE-032 (L80) uses "When" (Event-driven). Both patterns are now consistent. The mixed-pattern issue is gone.

- **v1-D3 (REQ-034 and REQ-040 were compound requirements)** — RESOLVED: REQ-034 was split into REQ-034a (L88) and REQ-034b (L92), each with a single SHALL. REQ-040 was split into REQ-040a (L120) and REQ-040b (L124), each with a single SHALL. Both defects eliminated.

- **v1-D4 (REQ-038 SQL syntax in requirement body)** — RESOLVED: REQ-038 (L110) normative text no longer contains SQL syntax (ON CONFLICT DO UPDATE was removed). The upsert behavior is now described in behavioral terms.

- **v1-D5 (REQ-035 Python f-string in normative SHALL clause)** — RESOLVED: The f-string `krx_code = f"P{portfolio_id}"` was moved to the blockquote design note (L98-99, under `> 설계 결정`), which is clearly non-normative. The normative SHALL clause at L96-97 contains no implementation-language syntax.

---

## Recommendation

The author has made genuine progress: Gherkin format is fully eliminated, v1-D2 through v1-D5 are all resolved. However, a new category of MP-2 violations has been introduced or exposed: compound SHALL clauses in acceptance criteria (D1-D5) and in requirements (D6-D9).

### Required fixes to achieve PASS at iteration 3

**Priority 1 — Split compound SHALL ACs (fixes D1-D5, resolves MP-2):**

AC-043-001: Split into three separate ACs:
- AC-043-001a: "When an authenticated non-owner user calls DELETE /shared/{share_token}/like and the user's like row exists, the system shall return 204 No Content."
- AC-043-001b: "When an authenticated non-owner user calls DELETE /shared/{share_token}/like and the user's like row exists, the system shall delete the portfolio_likes row for that user."
- AC-043-001c: "When an authenticated non-owner user calls DELETE /shared/{share_token}/like and the user's like row exists, the derived like_count shall decrease by 1."

AC-043-007: Split into two ACs:
- AC-043-007a: "When user B calls POST /shared/{share_token}/like again on a portfolio already liked, the system shall return 200."
- AC-043-007b: "When user B calls POST /shared/{share_token}/like again on a portfolio already liked, the count of type=portfolio_like notifications shall remain unchanged."

AC-043-008: Split into two ACs:
- AC-043-008a: "If the requesting user is the portfolio owner, then the system shall return 403 Forbidden when POST /shared/{share_token}/like is called."
- AC-043-008b: "If the requesting user is the portfolio owner, then no portfolio_like notification shall be created when POST /shared/{share_token}/like is called."

AC-043-010: Split into two ACs by endpoint:
- AC-043-010a: "When user A has one unread portfolio_like notification and calls GET /notifications/unread-count, the system shall include that notification in the unread count."
- AC-043-010b: "When user A has one unread portfolio_like notification and calls GET /notifications, the system shall include an item with type=portfolio_like in the response list."

AC-043-011: Split into two ACs by table:
- AC-043-011a: "When GET /shared/{share_token} is called twice for a public portfolio with no existing share_view_stats row for today (KST), the system shall result in share_view_stats.view_count = 2 for (share_id, today)."
- AC-043-011b: "When GET /shared/{share_token} is called twice for a public portfolio with no existing share_view_stats row for today (KST), portfolio_shares.view_count shall increase by 2."

**Priority 2 — Fix compound SHALL in REQs (fixes D6-D9, required for REQ quality):**

REQ-031 (L76): Remove the second SHALL sentence ("The derived like_count SHALL decrease by 1") from the normative REQ body. Verify at the AC level only (AC-043-001c above).

REQ-036 (L102): Remove the second sentence "A portfolio_like notification SHALL only be created when a portfolio_likes row is actually inserted" — it is redundant with the first "SHALL NOT" clause.

REQ-037 (L106-107): Move "No new inbox endpoint SHALL be added" to Section 2.2 Out-of-Scope or convert to a standalone REQ-037b.

REQ-038 (L110): Split into two REQs: one Event-driven for the successful-view upsert, one Unwanted for the non-public-share no-upsert.

**Priority 3 — Minor fixes (D10-D11):**

REQ-039b (L116): Insert "then" — "If the portfolio has no share record, **then** the system SHALL return 200..."

Preamble note (L71-72): Add mention of the 039/039b split, or rename REQ-039 to REQ-039a for consistency with the 034a/034b and 040a/040b pattern.
