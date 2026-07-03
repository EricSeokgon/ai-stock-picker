# SPEC Review Report: SPEC-STOCK-036
Iteration: 1/3
Verdict: FAIL
Overall Score: 0.62

---

## Must-Pass Results

- [PASS] **MP-1 REQ number consistency**: Two distinct sequential series, each internally gap-free.
  - Functional series: REQ-PALX-001 through REQ-PALX-012 (spec.md:L82–L117) — 12 entries, 3-digit zero-padded, no gaps.
  - NFR series: REQ-PALX-NFR-001 through REQ-PALX-NFR-006 (spec.md:L121–L137) — 6 entries, no gaps.
  - Each series uses a consistent prefix; no duplicate numbers exist within or across series.

- [FAIL] **MP-2 EARS format compliance**: All 15 acceptance criteria in acceptance.md use Given-When-Then (GWT) format, not any of the five EARS patterns.
  - acceptance.md:L3 explicitly declares: "형식: Given-When-Then."
  - AC-1 through AC-15 (acceptance.md:L6–L94): every criterion opens with "Given … / When … / Then THE 시스템 SHALL …".
  - GWT is not equivalent to any of the five EARS patterns (Ubiquitous, Event-driven, State-driven, Optional, Unwanted). The MP-2 criterion requires every acceptance criterion to match one of the five EARS patterns. GWT test scenario format does not satisfy this requirement regardless of whether the "Then" clause contains "THE 시스템 SHALL."
  - Rubric band: Score 0.25 — all ACs are in test-scenario format, zero ACs in pure EARS form.

- [PASS] **MP-3 YAML frontmatter validity**: All six required fields are present with correct types.
  - spec.md:L2: `id: "SPEC-STOCK-036"` (string) — PASS
  - spec.md:L3: `version: "0.1.0"` (string) — PASS
  - spec.md:L4: `status: "draft"` (valid enum value) — PASS
  - spec.md:L5: `created_at: "2026-06-24"` (ISO date string) — PASS
  - spec.md:L6: `priority: "medium"` (valid enum value) — PASS
  - spec.md:L7: `labels: ["portfolio", "alert", "notification", "backend", "frontend"]` (array) — PASS

- [N/A] **MP-4 Section 22 language neutrality**: This SPEC targets a single-language Python/JavaScript project, not multi-language LSP tooling. Auto-pass per N/A rule.

---

## Category Scores (0.0–1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 — minor ambiguity in one or two requirements | spec.md:L121 REQ-PALX-NFR-001 labeled "(Unwanted)" but uses Ubiquitous structure; all other REQs are unambiguous |
| Completeness | 0.75 | 0.75 — one non-critical section missing | HISTORY (spec.md:L13), WHY (spec.md:L20), WHAT (spec.md:L40), REQUIREMENTS (spec.md:L76), Exclusions (spec.md:L61), Technical Approach (HOW, spec.md:L141) all present; no formal ACCEPTANCE CRITERIA section in spec.md itself (ACs live in separate acceptance.md); YAML complete |
| Testability | 0.75 | 0.75 — one AC not precisely binary-testable, minor interpretation needed | GWT "Then" clauses are binary-testable (e.g., acceptance.md:L10 "등록 결과를 반환한다"; L46 "추가로 적재하지 않는다"); no weasel words ("appropriate", "reasonable") found in AC responses; however, AC-15 acceptance.md:L94 "채널 발송 실패는 무시한다" requires behavioral observation that may need test infrastructure |
| Traceability | 0.50 | 0.50 — multiple REQs lack ACs, one AC references behavior with no REQ | REQ-PALX-012 success path uncovered (acceptance.md has no AC for successful channel delivery); REQ-PALX-NFR-001 and REQ-PALX-NFR-002 have no numbered ACs; AC-10 (rule deletion, acceptance.md:L60) has no corresponding normative REQ |

---

## Defects Found

**D1.** acceptance.md:L3, L6–L94 — All 15 ACs use Given-When-Then format, not EARS patterns. Every AC opens with "Given … / When … / Then THE 시스템 SHALL …". GWT is explicitly declared at acceptance.md:L3 ("형식: Given-When-Then"). The MP-2 criterion requires each AC to match one of the five EARS patterns; GWT does not. — **Severity: critical**

**D2.** spec.md:L116–L117, acceptance.md (absent) — REQ-PALX-012 success path has no AC. REQ-PALX-012 states the system shall send via email or Telegram when the user's channel notification is activated. AC-15 covers only the failure/isolation case. No AC verifies that the channel delivery actually occurs when it should. — **Severity: major**

**D3.** acceptance.md:L60–L64, spec.md (absent) — AC-10 ("규칙 삭제") is an orphan AC with no corresponding normative REQ. The WHAT section (spec.md:L55) mentions deletion in prose, but no normative REQ-PALX-* entry requires deletion capability. Prose in WHAT is not normative; an orphan AC traces to nothing. — **Severity: major**

**D4.** spec.md:L121–L122 — REQ-PALX-NFR-001 is labeled "(Unwanted)" but uses the Ubiquitous EARS structure ("THE 시스템 SHALL … 도입하지 않는다") without the "IF [undesired condition], THEN" prefix required by the Unwanted pattern. The content is valid Ubiquitous EARS, but the mismatched label creates implementer confusion and suggests the author misunderstood EARS classification. — **Severity: minor**

**D5.** spec.md:L121–L122, acceptance.md:L100–L101 — REQ-PALX-NFR-001 (no new scientific libraries) has no numbered AC. The Quality Gate in acceptance.md mentions "신규 과학 라이브러리 미도입" as a process check, not a formal binary-testable acceptance criterion. Traceability requires a numbered AC. — **Severity: minor**

**D6.** spec.md:L124–L125, acceptance.md (absent) — REQ-PALX-NFR-002 (alert evaluation logic as pure function, DB-independent) has no numbered AC. The Quality Gate mentions "순수 함수…DB 없이 단위 검증" but this is a process gate, not a formal acceptance criterion. — **Severity: minor**

**D7.** acceptance.md:L102, L107 — Implementation details appear in the acceptance document outside normative ACs. Line 102 names functions `check_portfolio_value_alert`, `check_holding_return_alert`; line 107 names enum values `portfolio_value_below`, `holding_return`. These are HOW details that violate the WHAT-only principle in acceptance documents. — **Severity: minor**

---

## Chain-of-Verification Pass

Second-look findings: One additional concern confirmed, no new critical defects found beyond D1–D7.

Sections re-verified:
- **REQ numbering end-to-end**: Confirmed both series are gap-free (001–012, NFR-001–NFR-006). MP-1 PASS confirmed.
- **Traceability for every REQ**: Mapped all 18 REQs against 15 ACs individually. Gaps at REQ-PALX-012 success path, REQ-PALX-NFR-001, REQ-PALX-NFR-002 confirmed. REQ-PALX-001 through REQ-PALX-011 and REQ-PALX-NFR-003 through REQ-PALX-NFR-006 all have AC coverage.
- **Traceability for every AC**: AC-10 confirmed orphan (no DELETE REQ). All other ACs trace to at least one REQ.
- **Exclusions specificity**: spec.md:L61–L73 has 8 itemized exclusions, each specific and unambiguous (auto-trading, new tables, SPEC-031 existing types, new channels, WebSocket, new scheduler job, time-series analysis, trade recommendation). No vague entries. PASS.
- **Contradictions**: No contradictions found. REQ-PALX-007 (prevent same-day duplicate) and REQ-PALX-NFR-004 (DB-neutral upsert) are complementary, not contradictory. REQ-PALX-012 (optional channel delivery) and REQ-PALX-NFR-006 (channel failure isolation) are complementary.
- **RQ-4 normative text purity**: The REQUIREMENTS section (spec.md:L82–L137) contains zero function names, HTTP codes, SQL, or library names. Implementation details are confined to the explicitly non-normative Technical Approach section (spec.md:L141). PASS.

---

## Recommendation

The SPEC fails on MP-2. The following actions are required before re-audit:

**Fix 1 (Critical — resolves D1):** Convert all 15 acceptance criteria in acceptance.md from Given-When-Then format to one of the five EARS patterns.

The recommended mapping:
- GWT "Given [state] / When [event] / Then THE 시스템 SHALL [response]" → EARS Event-driven: "WHEN [event or state context], THE 시스템 SHALL [response]"
- AC-7 (duplicate prevention) → EARS State-driven: "WHILE [condition], THE 시스템 SHALL [response]"
- AC-8 (inactive rule exclusion) → EARS State-driven: "WHILE [inactive condition], THE 시스템 SHALL [exclusion]"
- AC-11 (access denial) → EARS Unwanted: "IF [unauthorized access], THEN THE 시스템 SHALL [deny and respond]"

State context from the "Given" clause should be embedded into the WHEN trigger or collapsed into the precondition wording within the EARS pattern.

**Fix 2 (Major — resolves D2):** Add an AC covering the success path of REQ-PALX-012. Example: "WHEN a fired alert rule's user has channel notification enabled, THE 시스템 SHALL send the alert content via the configured email or Telegram channel."

**Fix 3 (Major — resolves D3):** Add a normative REQ for rule deletion in spec.md. Suggested placement after REQ-PALX-009: "REQ-PALX-010 (Event-Driven): WHEN a user requests deletion of their own alert rule, THE 시스템 SHALL remove that rule and exclude it from all future evaluations." Note: if added, REQ-PALX-010 through REQ-PALX-012 must be renumbered (current 010–012 would become 011–013 or the DELETE req should take a new number such as REQ-PALX-013). Verify no existing cross-references break.

**Fix 4 (Minor — resolves D4):** Correct the EARS label on REQ-PALX-NFR-001. Change "(Unwanted)" to "(Ubiquitous)" since the text structure is "THE 시스템 SHALL [negation]." Alternatively, restructure to true Unwanted form: "IF 새로운 외부 과학 계산 라이브러리를 도입하게 되면, THEN THE 시스템 SHALL 해당 도입을 거부하고 표준 수치 연산만 사용한다" — but this changes semantics. The simpler fix is correcting the label.

**Fix 5 (Minor — resolves D5, D6):** Add numbered ACs for REQ-PALX-NFR-001 and REQ-PALX-NFR-002 in acceptance.md. Example for NFR-001: "IF a new scientific computation library (such as scipy or statsmodels) is imported, THE 시스템 SHALL fail the ruff lint gate or CI dependency check." Example for NFR-002: "THE 시스템 SHALL provide alert evaluation functions that accept numeric inputs and return boolean results without requiring any database connection or session."

**Fix 6 (Minor — resolves D7):** Remove function names (`check_portfolio_value_alert`, `check_holding_return_alert`) and enum values (`portfolio_value_below`, `holding_return`) from acceptance.md lines 102 and 107. Replace with behavioral descriptions. Example: "조건 평가 함수들은 데이터베이스 없이 단위 테스트로 검증 가능하다" (no function names needed).
