# SPEC Review Report: SPEC-STOCK-042
Iteration: 2/3
Verdict: MINOR ISSUES
Overall Score: 0.80

---

## Must-Pass Results

- [PASS] **MP-1 REQ number consistency**: REQ-SHARE-001 through REQ-SHARE-011, 11 entries, sequential with no gaps, no duplicates, consistent zero-padding. Verified at spec.md:L74–L119.
- [PASS] **MP-2 EARS format compliance**: All 14 ACs (spec.md:L266–L279, Section 9) now use proper EARS patterns. AC-1 through AC-7, AC-11, AC-13, AC-14 use Event-driven ("WHEN … THE SYSTEM SHALL"). AC-5, AC-9, AC-10, AC-12 use Unwanted behavior ("IF … THE SYSTEM SHALL"). Every AC includes explicit SHALL. No AC remains in tabular shorthand. Verified each AC individually.
- [PASS] **MP-3 YAML frontmatter validity**: All six required fields present — `id: SPEC-STOCK-042` (string), `version: 0.2.0` (string), `status: draft` (string), `created_at: 2026-06-30` (ISO date), `priority: medium` (string), `labels: [portfolio, sharing, social, feed, backend, frontend]` (array). Verified spec.md:L1–L13.
- [N/A] **MP-4 Section 22 language neutrality**: Single-language project (Python FastAPI + React/TypeScript). Auto-passes.

---

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 — Minor ambiguity in one or two requirements | REQs are generally precise. Residual issues: (1) multiple secondary REQ clauses use descriptive language without SHALL (see D1–D4 below); (2) check-order precedence for simultaneous 404/403 conditions still unspecified (spec.md:L99–L104, from v1 D10). |
| Completeness | 0.85 | between 0.75 and 1.0 — All required sections present; minor gaps in secondary REQ normative markers | All sections present: HISTORY (L17), WHY (L35), WHAT (L41), REQUIREMENTS (L70), ACCEPTANCE CRITERIA (L262), Exclusions (L54, 9 items). No missing sections. Minor: several secondary REQ clauses descriptive rather than normative. |
| Testability | 0.75 | 0.75 — One AC not precisely binary-testable due to incomplete field enumeration | All 14 ACs are binary-testable. Gap: AC-14 (L279) does not verify `like_count` despite REQ-SHARE-003 (L84) requiring it in ShareResponse. Two test scenarios lack coverage (see D5, D6). |
| Traceability | 0.85 | between 0.75 and 1.0 — All REQs have ACs; all ACs reference valid REQs; two minor coverage gaps | Every REQ-SHARE-001..011 has at least one AC. Every AC traces to a valid REQ-SHARE-NNN. Two minor gaps: AC-14 omits `like_count` field (incomplete coverage of REQ-SHARE-003 contract); AC-13 traces to REQ-SHARE-010 but that REQ does not explicitly state the privacy constraint (only the schema in Section 6 implies it). |

---

## Regression Check (Iteration 2)

Defects from v1 iteration:

| Defect | v1 Description | Status |
|--------|---------------|--------|
| D1 (critical) | All 13 ACs tabular shorthand, zero EARS patterns | RESOLVED — All 14 ACs now use WHEN/IF + THE SYSTEM SHALL. Verified spec.md:L266–L279. |
| D2 (major) | REQ-SHARE-003 second sentence "반환한다" missing SHALL | RESOLVED — spec.md:L84 now reads "반환해야 한다 (SHALL)". |
| D3 (major) | REQ-SHARE-011 second sentence "제외된다" missing SHALL | RESOLVED — spec.md:L119 now reads "제외되어야 한다 (SHALL)". |
| D4 (major) | AC-13 traced to "NFR" (invalid REQ identifier) | RESOLVED — spec.md:L278 now reads "(REQ-SHARE-010)". |
| D5 (major) | REQ-SHARE-003 scenario (a) record-exists → 200 had no AC | RESOLVED — AC-14 (spec.md:L279) added covering this scenario. |
| D6 (major) | No tests for REQ-SHARE-003 and REQ-SHARE-004 | PARTIALLY RESOLVED — T-013 (existing record → 200), T-014 (non-owner GET → 404), T-015 (non-owner DELETE → 404) added. Remaining gap: no test for REQ-SHARE-003 scenario (b) (no record → 204), and non-owner POST → 404 still untested (see D5 below). |
| D7 (minor) | WHEN/THEN style deviation in Event-driven REQs | UNRESOLVED — All Event-driven REQs still use "WHEN X, THEN 시스템은 Y SHALL" rather than standard EARS "WHEN X, the system SHALL Y". Present throughout spec.md:L76–L112. |
| D8 (minor) | REQ-SHARE-007 contains DB table name (implementation detail) | UNRESOLVED — spec.md:L100 still reads "시스템은 `portfolio_likes` 에 1행을 적재하고" — `portfolio_likes` table name is a HOW detail in a behavioral requirement. |
| D9 (minor) | No NFR addressing view_count inflation risk | UNRESOLVED — spec.md:L285–L291 NFR section still has no NFR-8 for view_count rate limiting or accepted-risk statement. |
| D10 (minor) | 403 vs 404 check order unspecified for simultaneous conditions | UNRESOLVED — no text in spec.md specifies which check fires first when owner calls like on their own non-public portfolio. |

---

## Defects Found (New in v0.2.0 / Residual Unresolved)

**D1.** spec.md:L100 (REQ-SHARE-007, second IF clause) — "THEN 시스템은 신규 행을 추가하지 않고 **200 LikeResponse**(현재 `like_count`, `liked=True`) 를 반환한다(멱등 — 409 가 아님)" — verb "반환한다" is descriptive, not normative. Missing SHALL. This clause specifies idempotent re-like behavior, which is a behavioral requirement. Correct form: "반환해야 한다(SHALL)". — Severity: **minor**

**D2.** spec.md:L76 (REQ-SHARE-001, second sentence) — "동일 포트폴리오에 대한 반복 호출은 **기존 `share_token` 을 보존**하며 새 토큰을 발급하지 않는다(멱등 재공유)" — "발급하지 않는다" is descriptive. This is a normative idempotency constraint. Correct form: "발급하지 않아야 한다(SHALL)". AC-2 covers this behavior so AC traceability is intact, but the REQ clause itself is non-normative. — Severity: **minor**

**D3.** spec.md:L80 (REQ-SHARE-002, second sentence) — "`share_token` 행과 누적 카운터(`view_count`·좋아요)는 보존하며 삭제하지 않는다(재공개 시 동일 토큰·카운터 유지)" — "보존하며 삭제하지 않는다" is descriptive. Correct form: "보존해야 하며 삭제하지 않아야 한다(SHALL)". AC-3 covers this in normative EARS form. — Severity: **minor**

**D4.** spec.md:L113–L115 (REQ-SHARE-010, sub-bullets) — The behavioral sub-constraints for sort and size use descriptive language: "`size` 는 기본 20, 최대 100 으로 제한한다(초과 입력 시 100 으로 클램핑). `page` 는 1 부터 시작하며 범위를 벗어나면 빈 `items` 를 반환한다." Both "제한한다" and "반환한다" are descriptive. AC-11 (spec.md:L276) covers these behaviors in normative EARS form, so AC coverage is intact, but the REQ sub-bullets lack SHALL. — Severity: **minor**

**D5.** spec.md:L256–L258 (Test Plan, T-001 through T-015) — Two test gaps remain:
  (a) No test covers REQ-SHARE-003 scenario (b): GET /portfolios/{id}/share when no share record exists → 204. AC-4 (spec.md:L269) specifies this behavior but no test verifies it. T-013 covers the "record exists → 200" scenario, not the "no record → 204" scenario.
  (b) No test covers non-owner calling `POST /portfolios/{id}/share` → 404. T-014 covers non-owner GET, T-015 covers non-owner DELETE, but non-owner POST is the third owner-only verb listed in REQ-SHARE-004 (spec.md:L88: "소유자 전용 엔드포인트(POST/DELETE/GET /portfolios/{portfolio_id}/share)") and has no test.
  — Severity: **minor**

**D6.** spec.md:L279 (AC-14) vs spec.md:L84 (REQ-SHARE-003) — AC-14 verifies "share_token, share_url, is_public, view_count" in the 200 ShareResponse, but REQ-SHARE-003 explicitly requires "(`share_token`, `is_public`, `share_url`, `view_count`, `like_count`)" — AC-14 omits `like_count`. Similarly, T-013 (spec.md:L256) lists "share_token·is_public·view_count 포함 검증" without mentioning `like_count`. An implementation that returns ShareResponse without `like_count` would pass AC-14 and T-013 yet violate REQ-SHARE-003. — Severity: **minor**

**D7.** (Residual from v1 D7) spec.md:L76–L112 (all Event-driven REQs) — All use "WHEN X, THEN 시스템은 Y SHALL" with explicit THEN connector. Standard EARS Event-driven pattern is "WHEN [trigger], the [system] SHALL [response]" without THEN. Style deviation persists. Not blocking. — Severity: **minor**

**D8.** (Residual from v1 D8) spec.md:L100 (REQ-SHARE-007) — "`portfolio_likes` 에 1행을 적재하고" specifies DB table name (HOW). Still present. Not blocking. — Severity: **minor**

**D9.** (Residual from v1 D9) spec.md:L285–L291 (NFR section) — No NFR addresses view_count inflation via repeated anonymous calls. Silence on accepted risk. Not blocking. — Severity: **minor**

**D10.** (Residual from v1 D10) spec.md:L99–L104 (REQ-SHARE-007, REQ-SHARE-008, REQ-SHARE-011) — Check precedence unspecified when `is_public=False` (→ 404 per REQ-SHARE-011) AND requester is owner (→ 403 per REQ-SHARE-008) simultaneously. Not blocking. — Severity: **minor**

---

## Chain-of-Verification Pass

Second-look findings after completing initial analysis:

Re-read all 14 ACs individually: all confirmed EARS-compliant with THE SYSTEM SHALL. CONFIRMED.

Re-read REQ-SHARE-001 through REQ-SHARE-011 end-to-end for non-normative clauses: identified D1 (REQ-007 second IF clause), D2 (REQ-001 second sentence), D3 (REQ-002 second sentence), D4 (REQ-010 sub-bullets). No additional non-normative clauses found.

Verified traceability table: every REQ-SHARE-001..011 maps to at least one AC. Every AC-1..14 maps to a valid REQ-SHARE-NNN. D6 is the only incomplete coverage (like_count omitted from AC-14 and T-013 vs REQ-SHARE-003).

Re-read test plan T-001 through T-015: confirmed D5 — no test for (a) no-record → 204 scenario of REQ-SHARE-003, and (b) non-owner POST → 404 for REQ-SHARE-004. These are the only remaining test gaps.

Re-read Out-of-Scope section: no scope creep in REQs. All 9 exclusion items absent from requirements section. PASS.

Re-read DB schema, API table, Pydantic schemas for internal consistency: FeedItem schema (spec.md:L204–L210) correctly excludes user_id/email. ShareResponse schema (spec.md:L188–L192) includes like_count. AC-14 and T-013 don't verify like_count — gap confirmed (D6). Otherwise consistent.

Re-checked YAML frontmatter: version: 0.2.0 — YAML parses this as string. All 6 required fields present and correctly typed. PASS.

No additional defects beyond D1–D10 discovered in the second pass.

---

## Summary Assessment

All 6 v1 blocking defects (B1–B6) are confirmed resolved:
- B1: All 14 ACs now in EARS format with THE SYSTEM SHALL
- B2: REQ-SHARE-003 second sentence now has SHALL
- B3: REQ-SHARE-011 second sentence now has SHALL
- B4: AC-13 now traces to REQ-SHARE-010 (not NFR)
- B5: AC-14 added for REQ-SHARE-003 scenario (a)
- B6: T-013, T-014, T-015 added

All 4 must-pass criteria (MP-1 through MP-4) pass.

Remaining defects (D1–D10) are all minor severity. No defect is blocking. The SPEC is ready for implementation. The items below are recommended as pre-implementation cleanup or implementation notes, not blockers.

---

## Recommendation (Non-blocking Fixes Before or During Implementation)

1. **AC-14 and T-013: add `like_count` to verified fields** (D6 — highest priority minor): AC-14 should read "…`share_token`, `share_url`, `is_public`, `view_count`, `like_count` 를 포함한 **200 응답**…". T-013 should include `like_count` in its verification list. This prevents a silent omission during implementation.

2. **Add missing test scenarios** (D5):
   - Add T-016: GET /portfolios/{id}/share when no share record exists (owner) → 204 (covers REQ-SHARE-003 scenario b / AC-4)
   - Add to T-014 or add T-017: non-owner POST /portfolios/{id}/share → 404 (covers third verb of REQ-SHARE-004)

3. **Normalize secondary REQ clauses to SHALL** (D1–D4): In REQ-SHARE-001 (L76), REQ-SHARE-002 (L80), REQ-SHARE-007 second IF clause (L100), and REQ-SHARE-010 sub-bullets (L113–L115), change descriptive verbs ("반환한다", "발급하지 않는다", "보존하며 삭제하지 않는다", "제한한다") to normative form ("…해야 한다(SHALL)").

4. **Specify 403 vs 404 check order** (D10): In Section 11 (Implementation Notes), add item 8 clarifying that is_public check (→ 404) fires before owner-self check (→ 403), so a non-public portfolio returns 404 regardless of requester identity.

5. **Add NFR-8 for view_count rate limiting stance** (D9): Even one line ("view_count 증가에 대한 속도 제한은 MVP 범위 외 — 남용 허용 리스크 인지 및 수용") closes the silence.

6. **Remove DB table name from REQ-SHARE-007** (D8): Replace "`portfolio_likes` 에 1행을 적재하고" with "해당 사용자의 좋아요를 기록하고(SHALL record the like)". The table name belongs in Section 4, not in a behavioral requirement.
