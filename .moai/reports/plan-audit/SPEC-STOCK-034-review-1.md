# SPEC Review Report: SPEC-STOCK-034
Iteration: 1/3
Verdict: FAIL
Overall Score: 0.71

---

## Must-Pass Results

- [PASS] MP-1 REQ number consistency: spec.md:L103-L131 — Functional REQs REQ-BMK-001 through REQ-BMK-005 are sequential with no gaps, no duplicates, consistent three-digit zero-padding. NFRs REQ-BMK-NFR-001 through REQ-BMK-NFR-005 are likewise sequential with no gaps.
- [PASS] MP-2 EARS format compliance: acceptance.md:L11-L33 — All 10 EARS ACs in §1 (AC-001-1, AC-001-2, AC-002-1, AC-002-2, AC-003-1, AC-003-2, AC-004-1, AC-004-2, AC-005-1, AC-005-2, AC-005-3) match valid EARS patterns. No assertion-form ACs detected.
- [PASS] MP-3 YAML frontmatter validity: spec.md:L1-L11 — All six required fields present: `id: "SPEC-STOCK-034"` (string, matches SPEC-{DOMAIN}-{NUM}), `version: "0.1.0"` (string), `status: "draft"` (valid enum), `created_at: "2026-06-24"` (ISO date), `priority: "medium"` (valid enum), `labels: [array]`.
- [N/A] MP-4 Section 22 language neutrality: SPEC-STOCK-034 targets a single-technology project (FastAPI + React, spec.md:L64). Not multi-language LSP tooling. Auto-pass.

---

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 — minor ambiguity in one or two requirements | spec.md:L113 REQ-BMK-003 uses vague "충분한" (sufficient) resolved only by cross-referencing NFR-004; formula prose in REQ-BMK-003 and AC-003-1 are functional but dense |
| Completeness | 1.0 | 1.0 — all required sections present, frontmatter complete, substantive exclusions | HISTORY (L17), WHY (L44), WHAT (L29), REQUIREMENTS (L101), AC via acceptance.md, Exclusions (L85) with 8 specific entries |
| Testability | 1.0 | 1.0 — all ACs binary-testable, no weasel words | acceptance.md:L11-L33 — every AC specifies a binary outcome (returns X, includes Y, responds identically, returns null); "미산정 값" (null) is schema-defined as Optional[float] in spec.md:L230 |
| Traceability | 0.50 | 0.50 — multiple REQs lack ACs | REQ-BMK-NFR-001, REQ-BMK-NFR-002, REQ-BMK-NFR-005 have no EARS ACs in acceptance.md §1; only acceptance.md §4 (NFR Verification table, prose) references them |

---

## Defects Found

**D1. spec.md:L130 — REQ-BMK-NFR-004 EARS pattern violated — Severity: major**

The text reads: "THE 베타 산출 컴포넌트 SHALL 일별 수익률 데이터가 최소 20개 미만이면 베타를 미산정 값으로 반환한다."

The condition clause ("일별 수익률 데이터가 최소 20개 미만이면" = "if fewer than 20 daily return data points") appears inside the SHALL body rather than as a leading trigger keyword. EARS requires the trigger to precede the subject+SHALL:
- Correct Event-driven: `WHEN 일별 수익률 데이터가 20개 미만이면 THE 베타 산출 컴포넌트 SHALL 베타를 미산정 값으로 반환한다.`
- Correct Unwanted: `IF 일별 수익률 데이터가 최소 20개 미만이면 THEN THE 시스템 SHALL 베타를 미산정 값으로 반환한다.`

As written, the structure is `[Subject] SHALL [embedded-if-condition + action]` which does not match any of the five EARS patterns. Deduction: -0.10.

**D2. acceptance.md — REQ-BMK-NFR-001, REQ-BMK-NFR-002, REQ-BMK-NFR-005 uncovered by EARS ACs — Severity: major**

Three of the ten numbered requirements have no corresponding EARS acceptance criterion in acceptance.md §1:
- REQ-BMK-NFR-001 (spec.md:L127, external library constraint): only appears in acceptance.md:L120 as a grep-check description in the NFR Verification table (prose, not EARS).
- REQ-BMK-NFR-002 (spec.md:L128, pure-function testability): only appears in acceptance.md:L121 as a prose verification method.
- REQ-BMK-NFR-005 (spec.md:L131, 85% coverage): only appears in acceptance.md:L124 as a pytest command description.

Traceability rubric score drops to 0.50. REQ-BMK-NFR-003 and REQ-BMK-NFR-004 are covered by AC-005-2 and AC-005-3 respectively (acceptance.md:L29 heading), but NFR-001, NFR-002, NFR-005 are not. Deduction: -0.10.

**D3. spec.md:L113 / acceptance.md:L21 — Formula density in normative SHALL text — Severity: minor**

REQ-BMK-003 embeds both the alpha and beta formulas as Korean prose in a single SHALL clause: "연환산 알파를 연환산 포트폴리오 수익률과 연환산 벤치마크 수익률의 차이로 산출하고, 베타를 일별 포트폴리오 수익률과 일별 벤치마크 수익률의 공분산을 일별 벤치마크 수익률의 분산으로 나눈 값으로 산출한다." The formula text is not in backticks (therefore not a critical violation), but the compound nature (two separate computation definitions in a single SHALL clause) reduces clarity. A tester cannot independently verify alpha without also reading the beta specification in the same sentence. The equivalent AC-003-1 (acceptance.md:L21) repeats this structure. Deduction: -0.03.

**D4. spec.md:L113 — "충분한" (sufficient) undefined in REQ-BMK-003 — Severity: minor**

REQ-BMK-003 triggers "WHEN 충분한 일별 수익률 시계열 데이터가 가용하면" (WHEN sufficient daily return time-series data is available). "충분한" is not quantified within REQ-BMK-003 itself. The threshold (minimum 20 data points) is only defined in REQ-BMK-NFR-004 (spec.md:L130). A reader of REQ-BMK-003 in isolation cannot determine when the requirement applies without cross-referencing NFR-004. Deduction: -0.03.

**D5. spec.md:L121 vs L129 — Duplicate graceful-degradation requirement — Severity: minor**

REQ-BMK-005 (spec.md:L121, second clause) and REQ-BMK-NFR-003 (spec.md:L129) express substantively identical behavior: when benchmark data is unavailable for a period, return null indicators without raising an error. The two formulations differ only in phrasing ("벤치마크 지표를 미산정 값으로 반환한다" vs "벤치마크 관련 지표를 미산정 값으로 처리하고 오류를 발생시키지 않는다"). Redundant normative requirements risk divergent future edits. Deduction: -0.03.

---

## Score Calculation

| Component | Deduction | Running Score |
|-----------|-----------|---------------|
| Start | — | 1.00 |
| D1 (Major: REQ-BMK-NFR-004 EARS malformed) | -0.10 | 0.90 |
| D2 (Major: traceability gap for NFR-001, NFR-002, NFR-005) | -0.10 | 0.80 |
| D3 (Minor: formula density) | -0.03 | 0.77 |
| D4 (Minor: vague trigger in REQ-BMK-003) | -0.03 | 0.74 |
| D5 (Minor: duplicate requirement) | -0.03 | 0.71 |

Final Score: **0.71** — below PASS threshold (0.80).

---

## Chain-of-Verification Pass

Re-reading all sections after first pass:

- Verified REQ sequencing end-to-end: REQ-BMK-001, 002, 003, 004, 005, NFR-001, NFR-002, NFR-003, NFR-004, NFR-005. No gaps confirmed.
- Verified every AC in acceptance.md §1 individually: 10 ACs checked. All follow WHEN/THE/SHALL or IF/THEN/THE/SHALL. No assertion forms detected.
- Verified exclusions specificity: 8 named exclusions in spec.md:L88-L98, each with concrete scope boundary. Not vague.
- Verified contradictions: No direct contradictions found. REQ-BMK-005 second clause and NFR-003 are redundant (D5), not contradictory.
- Verified acceptance.md §2 (BDD scenarios): Correctly labeled as Given/When/Then — these are not presented as EARS ACs, so §2 does not affect MP-2 verdict.
- New finding on second pass: Confirmed D2 is accurate — acceptance.md §4 table (L119-L124) uses grep/pytest commands as verification methods, not EARS SHALL statements. NFR-001, NFR-002, NFR-005 remain uncovered by EARS ACs.

No additional defects found beyond D1-D5.

---

## Recommendation

The SPEC fails the 0.80 score threshold. Required fixes before re-audit:

**Fix 1 (addresses D1):** Rewrite REQ-BMK-NFR-004 (spec.md:L130) to place the condition trigger before THE SYSTEM SHALL. Recommended form:
> IF 일별 수익률 데이터가 최소 20개 미만이면 THEN THE 시스템 SHALL 베타를 미산정 값으로 반환한다.

**Fix 2 (addresses D2):** Add EARS ACs to acceptance.md §1 for the three uncovered NFRs. Suggested:
- AC-NFR-001: `THE 시스템 SHALL 벤치마크 비교 계산 구현 시 scipy를 포함한 새로운 외부 통계·최적화 라이브러리를 사용하지 않는다.` (Ubiquitous — or reframe as a constraint AC)
- AC-NFR-002: `THE 시스템의 핵심 벤치마크 비교·차트·베타 계산 컴포넌트 SHALL 데이터베이스·외부 캐시·외부 네트워크 의존 없이 입력 데이터만으로 결정적 결과를 반환한다.`
- AC-NFR-005: `THE 시스템 SHALL 벤치마크 비교 계산 모듈의 단위 테스트 커버리지를 85% 이상으로 유지한다.`

**Fix 3 (addresses D3, optional):** Split REQ-BMK-003 into REQ-BMK-003a (alpha) and REQ-BMK-003b (beta) to separate the two computation definitions for independent testability.

**Fix 4 (addresses D4, optional):** Add "일별 수익률 20개 이상" (20 or more daily returns) as the explicit threshold definition within REQ-BMK-003, removing the dependency on cross-referencing NFR-004.

**Fix 5 (addresses D5, optional):** Remove the duplicate graceful-degradation clause from REQ-BMK-005 (second IF/THEN clause) and retain it only in REQ-BMK-NFR-003, or conversely consolidate REQ-BMK-NFR-003 into REQ-BMK-005 and remove NFR-003.

Fixes 1 and 2 are required (score impact -0.20 total). Fixes 3-5 are recommended to reach a clean 1.0 after must-pass items are resolved.
