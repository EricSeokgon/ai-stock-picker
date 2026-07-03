# plan-auditor Review — SPEC-STOCK-038-review-2

Score: 0.85
Result: PASS
Threshold: 0.80
Iteration: 2/3

---

## Regression Check (Iteration 2)

Defects from iteration 1:

- **MP-4** (EARS keyword violation in REQ-DASH-008): **RESOLVED** — spec.md:L109 now reads `(State-driven)` and L111 uses `WHILE 대시보드 데이터를 조회하는 중이면`. Pattern and label are both correct.
- **MP-5** (library names scipy/numpy in REQ-DASH-NFR-001): **RESOLVED** — spec.md:L123 now reads `외부 과학 계산 라이브러리를 사용하지 않고 표준 산술 연산만으로 계산한다`. No specific library names remain in REQ text.
- **D1** (weasel word "의미 있는" in REQ-DASH-007/AC-10): **UNRESOLVED** — spec.md:L107 and acceptance.md:L46 both still use `의미 있는 빈 상태 안내`. This was flagged as minor and optional in iteration 1.
- **D3** (missing edge-case AC for single-type portfolio): **UNRESOLVED** — no AC added for 100%-domestic-only or 100%-foreign-only portfolios. Flagged as minor and optional in iteration 1.
- **D4** (WHEN/WHILE mismatch between REQ-DASH-008 and AC-11): **RESOLVED** as a consequence of the MP-4 fix. Both now use WHILE.

---

## Must-Pass Results

- **[PASS] MP-1 REQ Number Consistency**: REQ-DASH-001 through REQ-DASH-009 are sequential with no gaps. REQ-DASH-NFR-001 through REQ-DASH-NFR-005 are sequential with no gaps. All 14 REQs carry `REQ-DASH-*` prefix. Evidence: spec.md:L81–L139.
- **[PASS] MP-2 EARS Format Compliance**: All 14 REQs and all 17 ACs match exactly one EARS pattern. Event-driven uses `WHEN ... THE 시스템 SHALL` without THEN (REQ-DASH-001/002/003/005/006, AC-1/3/5/8/9). Unwanted uses `IF ... THEN THE 시스템 SHALL` (REQ-DASH-007/009/NFR-001/003/005, AC-2/4/10/12/15/17). State-driven uses `WHILE ... THE 시스템 SHALL` without THEN (REQ-DASH-008, AC-11). Ubiquitous uses `THE 시스템 SHALL` directly (REQ-DASH-004/NFR-002/004, AC-6/7/13/14/16). No BDD Given/When/Then patterns present.
- **[PASS] MP-3 Subject Consistency**: All REQs and ACs use `THE 시스템 SHALL` as the sole subject. No chart, component, or page appears as subject. Verified across spec.md:L83–L139 and acceptance.md:L10–L74.
- **[PASS] MP-4 EARS Pattern Correctness**: Pattern keywords match their semantics across all 14 REQs. REQ-DASH-008 (spec.md:L109–L111) correctly uses `WHILE` for a persistent loading state. Unwanted REQs all use `IF ... THEN THE 시스템 SHALL`. Event-driven REQs use `WHEN ... THE 시스템 SHALL` (no THEN). No mismatched keywords found.
- **[PASS] MP-5 REQ Text Technology Neutrality**: No function names, HTTP status codes, SQL keywords, or library names appear in REQ-DASH-001 through REQ-DASH-NFR-005 text. Technical stack references (numpy, Recharts) are confined to Section 1.4 (spec.md:L59–L64), which is descriptive context, not normative REQ text. REQ-DASH-NFR-001 (spec.md:L123) uses `외부 과학 계산 라이브러리` — technology-neutral. Evidence: spec.md:L83–L139.
- **[PASS] MP-6 REQ Prefix**: All requirements use `REQ-DASH-*` prefix. No deviation from the declared prefix scheme. Evidence: spec.md:L81–L139.

---

## Category Scores (0.0–1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 — minor ambiguity in one or two requirements | "의미 있는 빈 상태 안내" in spec.md:L107 and acceptance.md:L46 has no measurable definition |
| Completeness | 0.75 | 0.75 — one non-critical section sparse | YAML version field not bumped (still "0.1.0") and HISTORY table not updated after content changes; all structural sections present |
| Testability | 0.75 | 0.75 — one AC not precisely binary-testable | AC-10 (acceptance.md:L46): "의미 있는 빈 상태 안내" requires judgment to evaluate; all other 16 ACs are binary-testable |
| Traceability | 1.0 | 1.0 — full coverage | All 14 REQs have at least one AC; all 17 ACs reference valid REQs; no orphans. REQ-DASH-001: AC-1,AC-2; REQ-DASH-002: AC-3,AC-4; REQ-DASH-003: AC-5,AC-6; REQ-DASH-004: AC-7; REQ-DASH-005: AC-8; REQ-DASH-006: AC-9; REQ-DASH-007: AC-10; REQ-DASH-008: AC-11; REQ-DASH-009: AC-12; NFR-001: AC-13; NFR-002: AC-14; NFR-003: AC-15; NFR-004: AC-16; NFR-005: AC-17 |

---

## Defects Found

D1. spec.md:L107, acceptance.md:L46 — `의미 있는 빈 상태 안내` is a weasel phrase. A tester cannot determine PASS/FAIL without knowing what constitutes "meaningful" (의미 있는). The phrase provides no minimum content requirement for the empty-state message. **Severity: minor** (carried from iteration 1, still unresolved, not a blocking MP issue).

D2. spec.md:L3, spec.md:L19–L21 — YAML `version` field is `"0.1.0"` and the HISTORY table contains only one row (v0.1.0, 2026-06-25) despite the document being modified from the v1-audited state (REQ-DASH-008 label and keyword changed, REQ-DASH-NFR-001 text revised). The document's change history is not reflected in its own metadata. **Severity: minor** (administrative; does not affect requirement validity).

D3. acceptance.md — No AC covers the edge case of a portfolio where all holdings belong to a single asset type (100% domestic or 100% foreign). AC-6 asserts `비중(%)의 합이 100이 되도록 계산한다` without specifying floating-point tolerance, which leaves the rounding behavior unspecified. **Severity: minor** (carried from iteration 1, still unresolved, not a blocking MP issue).

---

## Chain-of-Verification Pass

Second-look findings: No new must-pass defects discovered beyond those identified in the first pass above.

Verified in second pass:
- All 14 REQ-DASH-* entries re-read in full (001–009, NFR-001–005). Sequential numbering confirmed end-to-end with no gaps or duplicates.
- EARS pattern verification re-run for every REQ and every AC (14 REQs + 17 ACs = 31 items checked individually).
- Subject check re-verified: no non-시스템 subject found in any SHALL clause.
- REQ text scanned character-by-character for library names in normative sections: only Section 1.4 (tech stack context) references specific libraries, which is acceptable.
- Exclusions section (spec.md:L144–L155): 9 concrete exclusion entries, all specific and unambiguous.
- No contradictions found between requirements within spec.md.
- AC-12 (acceptance.md:L54) states `자원을 찾을 수 없음으로 응답한다` — this is consistent with REQ-DASH-009 (spec.md:L115) which says `해당 포트폴리오의 존재를 드러내지 않는 방식으로 접근을 거부한다`. The AC narrows the behavior to a 404-equivalent response; no contradiction with REQ-DASH-NFR-003.
- REQ-DASH-NFR-004 uses `props` (React-specific term): noted as borderline in review 1. Confirmed acceptable given this is an explicitly React-scoped SPEC (spec.md:L63).

---

## Recommendation

PASS. All must-pass criteria are satisfied. The two blocking defects from iteration 1 (MP-4, MP-5) have been fully resolved.

The following non-blocking improvements are recommended but do not prevent implementation:

1. **D1** — spec.md:L107, acceptance.md:L46: Replace `의미 있는 빈 상태 안내` with a concrete, testable specification, for example `해당 기간에 데이터가 없음을 설명하는 텍스트를 포함한 빈 상태 메시지`. This gives a tester a binary criterion: does the displayed message include explanatory text about missing data?

2. **D2** — spec.md:L3, spec.md:L19: Bump `version` to `"0.2.0"` and add a HISTORY row documenting the changes made (REQ-DASH-008 pattern corrected, REQ-DASH-NFR-001 library references removed).

3. **D3** — acceptance.md: Add an AC for single-type portfolio allocation (e.g., `IF 모든 보유 종목이 동일한 자산유형이면, THEN THE 시스템 SHALL 해당 유형의 비중을 100으로 반환한다`). Add a floating-point tolerance note to AC-6, e.g., `±0.01% 이내의 오차를 허용한다`.
