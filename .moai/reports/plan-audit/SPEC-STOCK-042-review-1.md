# SPEC-STOCK-042 Plan Audit — Review 1

Date: 2026-06-30
Auditor: plan-auditor
Iteration: 1/3
Verdict: FAIL
Overall Score: 0.62

---

## Must-Pass Results

- [PASS] **MP-1 REQ number consistency**: REQ-SHARE-001 through REQ-SHARE-011, 11 entries, sequential with no gaps, no duplicates, consistent zero-padding. Verified at spec.md:L73–L118.
- [FAIL] **MP-2 EARS format compliance**: All 13 ACs (spec.md:L261–L274, Section 9) are written in tabular shorthand form — e.g., AC-1: "`POST /portfolios/{id}/share` → 200 + `share_token`·`share_url`·`is_public=True` 반환". Not one AC matches any of the five EARS patterns (Ubiquitous/Event-driven/State-driven/Optional/Unwanted). Additionally, two REQ sentences lack explicit SHALL: spec.md:L83 ("반환한다" — missing SHALL) and spec.md:L118 ("제외된다" — missing SHALL).
- [PASS] **MP-3 YAML frontmatter validity**: All six required fields present with correct types — `id: SPEC-STOCK-042` (string), `version: 0.1.0` (string), `status: draft` (string), `created_at: 2026-06-30` (ISO date), `priority: medium` (string), `labels: [portfolio, sharing, social, feed, backend, frontend]` (array). Verified spec.md:L1–L13.
- [N/A] **MP-4 Section 22 language neutrality**: This SPEC is clearly scoped to a single-language project (Python FastAPI + React/TypeScript). Criterion auto-passes.

---

## Category Scores (0.0–1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 — Minor ambiguity in one or two requirements | REQs are generally precise. Two ambiguities: (1) REQ-SHARE-003 second sentence lacks SHALL (spec.md:L83); (2) undefined check precedence when 403 (owner self-like) and 404 (non-public) conditions overlap (spec.md:L99–L103). |
| Completeness | 0.75 | 0.75 — One non-critical section missing or sparse | All sections present. Gaps: REQ-SHARE-003's "200 when record exists" scenario has no AC; AC-13 traces to "NFR" (not a REQ-SHARE-NNN). |
| Testability | 0.75 | 0.75 — One AC is not precisely binary-testable | ACs are binary-testable despite not being EARS-formatted. Two test coverage gaps: REQ-SHARE-003 "200" scenario and REQ-SHARE-004 "non-owner 404" each lack a dedicated test case. |
| Traceability | 0.50 | 0.50 — Multiple REQs lack ACs or multiple ACs reference non-existent REQs | AC-13 (spec.md:L274) references "NFR" which is not a valid REQ-SHARE-NNN. REQ-SHARE-003 has two scenarios; only scenario (b) is covered by AC-4; scenario (a) (record exists → 200) has no AC. |

---

## D1: EARS Compliance

**REQs (spec.md:L73–L118):**

REQ-SHARE-001 through REQ-SHARE-011 all follow a "WHEN X, THEN 시스템은 Y SHALL" or "IF X, THEN 시스템은 Y SHALL" structure. The IF/THEN SHALL form is valid EARS Unwanted behavior. The WHEN/THEN form is a deviation — standard EARS Event-driven is "WHEN [trigger], the [system] SHALL [response]" without a separate "THEN" keyword. This THEN usage makes the patterns resemble BDD Given/When/Then rather than pure EARS.

Two REQ sentences are missing explicit SHALL:

- spec.md:L83 (REQ-SHARE-003, second sentence): "IF 해당 포트폴리오에 공유 레코드가 한 번도 생성된 적이 없으면, THEN **204 No Content**(본문 없음)를 반환한다." The verb "반환한다" is descriptive, not normative. Must be "반환해야 한다(SHALL)".
- spec.md:L118 (REQ-SHARE-011, second sentence): "또한 `GET /feed` 결과에서 비공개 포트폴리오는 제외된다(`is_public=False` 는 피드 미노출)." The verb "제외된다" is descriptive. Must be "제외되어야 한다(SHALL)".

REQ-SHARE-007 (spec.md:L99) embeds an implementation detail: "시스템은 `portfolio_likes` 에 1행을 적재하고" — specifying the DB table name is HOW, not WHAT. The requirement should state the observable outcome (a like entry is created; the requester's like is recorded), not the storage mechanism.

**ACs (spec.md:L261–L274):**

All 13 ACs are tabular shorthand. Zero match EARS patterns. Examples:
- AC-1: "`POST /portfolios/{id}/share` → 200 + `share_token`·`share_url`·`is_public=True` 반환"
- AC-8: "인증 사용자 좋아요 → 200 + `like_count` +1, 재좋아요 시 `like_count` 불변·200(멱등)"

This is a MP-2 failure. None of the 13 ACs use a WHEN/IF/WHERE/WHILE pattern or include the word SHALL.

---

## D2: Acceptance Criteria

**Coverage of REQs:**

| REQ | AC(s) | Gap |
|-----|-------|-----|
| REQ-SHARE-001 | AC-1, AC-2 | No gap |
| REQ-SHARE-002 | AC-3 | No gap |
| REQ-SHARE-003 | AC-4 | AC-4 covers only the 204 (no record) scenario. The 200 (record exists) scenario has NO corresponding AC. |
| REQ-SHARE-004 | AC-5 | No gap |
| REQ-SHARE-005 | AC-6 | No gap |
| REQ-SHARE-006 | AC-7 | No gap |
| REQ-SHARE-007 | AC-8 | No gap |
| REQ-SHARE-008 | AC-9 | No gap |
| REQ-SHARE-009 | AC-10 | No gap |
| REQ-SHARE-010 | AC-11 | No gap |
| REQ-SHARE-011 | AC-12 | No gap |
| (NFR) | AC-13 | "NFR" is not a valid REQ-SHARE-NNN identifier (traceability violation). |

**Testability of ACs:**

Despite EARS non-compliance, all 13 ACs are binary-testable (PASS/FAIL deterministic). Notable observations:
- AC-6 includes "소유자 user_id·이메일 미노출" — verifiable by inspecting response fields. Testable.
- AC-11 includes "`size` 100 초과 입력 시 100 클램핑" — precise threshold, testable.
- AC-13 covers schema-level assertions (migration count, table count, no new libraries). Testable.

No ACs contain weasel words such as "appropriate", "adequate", or "reasonable".

---

## D3: Test Plan

**Required scenarios per audit checklist:** All 8 specified scenarios are covered.

| Required Scenario | Test |
|-------------------|------|
| Token generation idempotency | T-002 |
| Disable → 404 | T-004 |
| View count increment | T-005 |
| Like idempotency | T-008 |
| Feed pagination + sorting | T-011, T-012 |
| Self-like 403 | T-009 |
| Unauthenticated view allowed | T-006 |
| Unauthenticated like 401 | T-010 |

**Coverage gaps identified:**

| Gap | Missing REQ coverage |
|-----|---------------------|
| No test for GET /portfolios/{id}/share with existing record → 200 | REQ-SHARE-003 (scenario a) |
| No test for GET /portfolios/{id}/share with no record → 204 | REQ-SHARE-003 (scenario b) |
| No test for non-owner calling POST/DELETE/GET /portfolios/{id}/share → 404 | REQ-SHARE-004 |

REQ-SHARE-003 and REQ-SHARE-004 have zero dedicated test coverage. T-001 through T-012 do not include these scenarios. Two test cases must be added.

---

## D4: Technical Consistency

All critical technical parameters verified against spec.md:

| Check | Spec Reference | Result |
|-------|---------------|--------|
| down_revision = "0025" | spec.md:L125 `down_revision = '0025'` | PASS |
| share_token: secrets.token_urlsafe(16), 22 chars, VARCHAR(32) | spec.md:L132 + L156 | PASS |
| like_count = COUNT(*) from portfolio_likes, not stored | spec.md:L158 | PASS |
| view_count atomic increment (UPDATE ... SET view_count = view_count + 1) | spec.md:L300 | PASS |
| Router prefix: /portfolios (owner), /shared + /feed (public) | spec.md:L175 | PASS |
| Anonymous GET /shared/{token} allowed | REQ-SHARE-005 (L91) | PASS |
| POST /shared/{token}/like requires auth → 401 if unauth | REQ-SHARE-009 (L107) | PASS |
| Owner like own portfolio → 403 | REQ-SHARE-008 (L103) | PASS |
| Non-owner owner-endpoints → 404 | REQ-SHARE-004 (L87) | PASS |

One internal consistency note: spec.md:L83 says the second scenario of REQ-SHARE-003 returns 204 when no share record exists. The API table at spec.md:L169 shows `200 ShareResponse / 204 / 404` for GET /portfolios/{id}/share. Consistent.

One semantic ambiguity: when the portfolio owner calls `POST /shared/{share_token}/like` on their own portfolio that is currently `is_public=False`, which check fires first — 404 (REQ-SHARE-011) or 403 (REQ-SHARE-008)? The check precedence is unspecified. Implementation will need to decide (404 should take precedence per security convention, since revealing 403 discloses ownership). This should be specified.

---

## D5: Scope Discipline

No out-of-scope items appear in REQs. All prohibited items from spec.md:L54–L65 are absent from the requirement set:

| Out-of-Scope Item | Present in REQs? |
|-------------------|-----------------|
| Follow/follower graph | No |
| Comments/replies | No |
| Like notifications | No |
| Portfolio forking | No |
| WebSocket real-time | No |
| Unlike (좋아요 취소) | No |
| New external libraries | No (secrets is stdlib) |
| View history/time-series | No |

PASS — no scope creep detected.

---

## D6: Security & Privacy

| Check | Spec Reference | Result |
|-------|---------------|--------|
| Public view excludes owner user_id / email (NFR-5) | spec.md:L284; REQ-SHARE-005 L91; SharePublicResponse schema L193–200 | PASS — schema contains no user_id, email, or username field |
| share_token unguessable via secrets.token_urlsafe(16) (NFR-6) | spec.md:L285 | PASS |
| Rate limiting / deduplication for view_count | Not mentioned anywhere | GAP |

**view_count rate limiting absent (spec.md:L280–L286 NFR section):** Anonymous users can call `GET /shared/{share_token}` indefinitely, incrementing `view_count` on each request. The spec provides no rate limiting, IP-based deduplication, or session deduplication mechanism. This allows artificial inflation of view_count. The NFR section should address this, even if only to explicitly acknowledge the accepted risk.

---

## Defects Found

**D1.** spec.md:L261–L274 (Section 9, AC-1 through AC-13) — All 13 Acceptance Criteria are tabular shorthand descriptions; zero match any of the five EARS patterns. This violates MP-2. Example: AC-1 reads "`POST /portfolios/{id}/share` → 200 + `share_token`·`share_url`·`is_public=True` 반환" — contains no WHEN/IF/WHERE/WHILE keyword and no SHALL. — **Severity: critical**

**D2.** spec.md:L83 (REQ-SHARE-003, second sentence) — "반환한다" is descriptive, missing normative SHALL. Correct form: "반환해야 한다(SHALL)". — **Severity: major**

**D3.** spec.md:L118 (REQ-SHARE-011, second sentence) — "또한 `GET /feed` 결과에서 비공개 포트폴리오는 제외된다" uses "제외된다" (descriptive); missing SHALL. Correct form: "제외되어야 한다(SHALL)". — **Severity: major**

**D4.** spec.md:L274 (AC-13) — AC-13 is mapped to "NFR" as the traced requirement, but "NFR" is not a valid REQ-SHARE-NNN identifier in this document. AC-13 must trace to a REQ-SHARE-NNN or be restructured. — **Severity: major**

**D5.** spec.md:L265 (AC-4) — REQ-SHARE-003 has two distinct outcomes: (a) share record exists → 200 ShareResponse, (b) no share record → 204. AC-4 covers only outcome (b). Outcome (a) has no AC. — **Severity: major**

**D6.** spec.md:L241–L254 (Test Plan, T-001 through T-012) — No test covers REQ-SHARE-003 (GET /portfolios/{id}/share with existing record → 200, or with no record → 204). No test covers REQ-SHARE-004 (non-owner calling owner-only endpoints → 404). Two REQs lack any test-plan traceability. — **Severity: major**

**D7.** spec.md:L75–L118 (all REQs) — All Event-driven REQs use "WHEN X, THEN 시스템은 Y SHALL" structure. Standard EARS Event-driven omits "THEN" and writes "WHEN X, the system SHALL Y" directly. The THEN insertion deviates from the EARS standard. — **Severity: minor**

**D8.** spec.md:L99 (REQ-SHARE-007) — "시스템은 `portfolio_likes` 에 1행을 적재하고" specifies the DB table name as the storage mechanism. This is a HOW detail (implementation). Replace with outcome language: "시스템은 해당 사용자의 좋아요를 기록하고(SHALL record the user's like)". — **Severity: minor**

**D9.** spec.md:L280–L286 (NFR section) — No rate limiting or deduplication for view_count is mentioned. view_count can be inflated by anonymous bot traffic. NFRs should address this explicitly, even if the accepted policy is "no rate limit in MVP". — **Severity: minor**

**D10.** spec.md:L99–L103 (REQ-SHARE-007 and REQ-SHARE-008) — Undefined precedence when both 404 (is_public=False, REQ-SHARE-011) and 403 (owner self-like, REQ-SHARE-008) conditions apply simultaneously. The spec does not specify which check runs first. Implementation must infer the order. — **Severity: minor**

---

## Chain-of-Verification Pass

Second-look findings: Confirmed all defects above. Additional confirmation:

- Verified end-to-end REQ numbering (001–011, no gaps): CONFIRMED.
- Verified AC-to-REQ traceability for all 13 ACs: AC-13 "NFR" confirmed as invalid. REQ-SHARE-003 scenario-a gap confirmed.
- Verified test plan for REQ-SHARE-003 and REQ-SHARE-004: both confirmed absent from T-001–T-012.
- Re-read REQ-SHARE-007 for HOW detail: `portfolio_likes` table name confirmed present in normative text.
- Re-read Section 2.2 Out-of-Scope for scope creep: none found in REQs.
- Re-read NFR section: view_count rate limiting confirmed absent.
- Checked `SharePublicResponse` schema for any user_id/email fields: none found. Privacy requirement holds.

No new defects discovered beyond D1–D10 above.

---

## Required Changes (blocking)

1. **Rewrite all 13 ACs in EARS format** (D1 — MP-2 failure). Each AC must use one of:
   - Event-driven: "When [trigger], the system shall [response]"
   - Unwanted: "If [condition], then the system shall [response]"
   Example fix for AC-1: "When an owner calls `POST /portfolios/{id}/share`, the system shall return HTTP 200 with a `ShareResponse` containing `share_token`, `share_url`, and `is_public=True`."

2. **Add SHA must in REQ-SHARE-003 second sentence** (D2): Change spec.md:L83 "반환한다" → "반환해야 한다(SHALL)".

3. **Add SHALL in REQ-SHARE-011 second sentence** (D3): Change spec.md:L118 "제외된다" → "제외되어야 한다(SHALL)".

4. **Fix AC-13 traceability** (D4): Map AC-13 to an explicit REQ or create NFR-REQ entries (e.g., REQ-SHARE-012 for DB migration constraints). Alternatively, split AC-13 into sub-criteria each mapped to the relevant REQ.

5. **Add AC for REQ-SHARE-003 scenario (a)** (D5): Add an AC covering "When an owner calls `GET /portfolios/{id}/share` and a share record exists, the system shall return HTTP 200 with a `ShareResponse` containing the current `share_token`, `is_public`, `view_count`, and `like_count`."

6. **Add missing test cases** (D6): Add at minimum:
   - T-013: GET /portfolios/{id}/share with existing share record → 200 ShareResponse (covers REQ-SHARE-003 scenario a)
   - T-014: GET /portfolios/{id}/share with no share record → 204 (covers REQ-SHARE-003 scenario b)
   - T-015: Non-owner calls POST/DELETE/GET /portfolios/{id}/share → 404 (covers REQ-SHARE-004)

---

## Suggestions (non-blocking)

1. **Specify 403 vs 404 check order** (D10): Add a note to REQ-SHARE-008 or Section 11 stating that the `is_public` check (→ 404) fires before the owner-self-check (→ 403), so a non-public portfolio returns 404 regardless of whether the requester is the owner.

2. **Remove HOW detail from REQ-SHARE-007** (D8): Replace "`portfolio_likes` 에 1행을 적재하고" with outcome-only language. The table name belongs in Section 4 (DB schema), not in a behavioral requirement.

3. **Address view_count abuse** (D9): Add NFR-8 acknowledging either: (a) rate limiting is out of scope for MVP and accepted risk; or (b) a basic rate limit (e.g., 1 increment per IP per minute) is applied. Either stance is acceptable — the gap is the silence.

4. **WHEN/THEN → WHEN/SHALL in REQs** (D7): All Event-driven REQs would be cleaner without the THEN connector. Example: "WHEN 소유자가 POST ... 를 호출하면, 시스템은 ... 해야 한다(SHALL)" rather than inserting THEN. Minor style issue; functional meaning is preserved.

5. **`LikeResponse.liked` is always True**: Since unlike is explicitly out of scope, `liked: bool` will always be `True` in MVP. A comment in Section 6 acknowledging this (e.g., "liked: bool — always True in v1; False reserved for future unlike support") would aid implementers.
