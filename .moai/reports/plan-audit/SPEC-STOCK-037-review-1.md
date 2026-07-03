# SPEC Review Report: SPEC-STOCK-037
Iteration: 1/3
Verdict: FAIL
Overall Score: 0.38

---

## Must-Pass Results

- [FAIL] **MP-1 REQ number consistency**: The `## 비기능 요구사항 (REQ-AIEX-NFR)` subsection header (spec.md:L77) names the group `REQ-AIEX-NFR`, yet all five entries within use the prefix `NFR-` (NFR-001 through NFR-005, spec.md:L79–83) instead of the `REQ-AIEX-NFR-001` pattern. This breaks naming consistency within the requirements section: the REQ-AIEX-* namespace used by all 16 functional requirements is abandoned for NFRs. Additionally, the grouped numbering scheme restarts at 001 for each sub-group (PORT-001, RAT-001, PREF-001 etc.), which deviates from the flat sequential REQ-001…REQ-N contract. The NFR prefix mismatch is unambiguous — NFR-001 and REQ-AIEX-PORT-001 belong to the same Requirements section but follow different naming schemes.

- [FAIL] **MP-2 EARS format compliance**: All 17 acceptance criteria in acceptance.md use Given/When/Then (Gherkin/BDD) format, not any of the five EARS patterns. acceptance.md:L10–12 illustrates: `- **Given** 보유 종목 3개를 가진 포트폴리오를 소유한 사용자가 있고 / - **When** 사용자가 해당 포트폴리오에 대한 개인화 추천을 요청하면 / - **Then** THE 시스템 SHALL ...`. Valid EARS event-driven format is a single sentence: "WHEN [trigger], THE [system] SHALL [response]." The three-bullet Given/When/Then structure is BDD, not EARS. The acceptance.md header acknowledges EARS format ("EARS 형식: WHEN/IF/WHILE 조건 + THEN THE 시스템 SHALL 응답") yet none of the 17 ACs comply. This is a document-wide systematic violation.

- [FAIL] **MP-3 YAML frontmatter validity**: Two required fields are defective.
  - spec.md:L5: field is named `created: 2026-06-25` — required name is `created_at`. Wrong field name.
  - spec.md:L1–10: `labels` field is entirely absent from the frontmatter block. Required field `labels` (array or string) is missing.

- [N/A] **MP-4 Section 22 language neutrality**: This SPEC targets a single-language Python + React project. N/A — auto-passes.

---

## Category Scores (0.0–1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 band | Most requirements are unambiguous. Minor ambiguity: REQ-AIEX-APPLY-002 (spec.md:L65) uses "유사한 종목" (similar stocks) without defining similarity; REQ-AIEX-APPLY-003 (spec.md:L66) self-contradicts by combining SHALL with "높일 수 있다" (may increase); REQ-AIEX-PORT-003 (spec.md:L47) uses "과도하게 집중" without a numeric threshold. Core requirements are otherwise unambiguous. |
| Completeness | 0.50 | 0.50 band | HISTORY present (spec.md:L14–16). WHY/WHAT merged into 개요 section (spec.md:L20–28) — sections not individually labeled but covered. Requirements section present with 21 entries. Exclusions present and specific (spec.md:L87–95). AC section exists in acceptance.md. However: YAML frontmatter missing two required fields (created_at, labels); REQ-AIEX-APPLY-003, NFR-001, and NFR-005 have no AC (three uncovered requirements). |
| Testability | 0.50 | 0.50 band | Most ACs are binary-testable. Two failures: AC-3 (acceptance.md:L21–24) — "과도하게 집중" has no numeric threshold, making PASS/FAIL judgment subjective; AC-7 (acceptance.md:L44–48) — "분석 관점 설명과 면책 안내" has no measurable criteria for a tester to apply. NFR-001 testability unclear since its AC is missing. |
| Traceability | 0.50 | 0.50 band | 14 of 17 REQ-AIEX-* requirements have at least one AC. Three requirements lack coverage: REQ-AIEX-APPLY-003 (no AC exists in acceptance.md), NFR-001 (no AC), NFR-005 (no AC). AC-15 traces to both REQ-AIEX-OWN-001 and NFR-003 — dual-trace acceptable. All other ACs reference valid REQ identifiers. |

---

## Defects Found

**D1.** spec.md:L5 — `created` field name used instead of required `created_at`. YAML frontmatter field name mismatch breaks MP-3. — Severity: **critical**

**D2.** spec.md:L1–10 — `labels` field entirely absent from YAML frontmatter. Required field per MP-3. — Severity: **critical**

**D3.** acceptance.md:L10–109 (all 17 ACs) — Every acceptance criterion uses Given/When/Then (BDD/Gherkin) format instead of one of the five EARS patterns. The header states EARS format is required but no AC complies. MP-2 failure is document-wide. — Severity: **critical**

**D4.** spec.md:L77–83 — NFR entries (NFR-001 through NFR-005) use prefix `NFR-` instead of `REQ-AIEX-NFR-` or any REQ-* convention. The subsection header says `REQ-AIEX-NFR` but items are labeled `NFR-001` etc., creating naming inconsistency within the Requirements section. MP-1 violation. — Severity: **major**

**D5.** spec.md:L79 (NFR-001) — Hardcodes specific library names `scipy` and `numpy` in normative requirement text: "scipy를 사용하지 않고 numpy와 표준 수학 연산만 사용한다". This is HOW (specific implementation technology), not WHAT. Library names in normative REQ text violate RQ-4. — Severity: **major**

**D6.** acceptance.md — REQ-AIEX-APPLY-003 (spec.md:L66) has no corresponding acceptance criterion in acceptance.md. The 17 ACs cover PORT-001..004, RAT-001..003, PREF-001..003, APPLY-001..002, HIST-001..002, OWN-001, and three NFRs — APPLY-003 is absent. — Severity: **major**

**D7.** acceptance.md — NFR-001 (spec.md:L79) has no corresponding acceptance criterion. — Severity: **major**

**D8.** acceptance.md — NFR-005 (spec.md:L83) has no corresponding acceptance criterion. — Severity: **major**

**D9.** spec.md:L66 (REQ-AIEX-APPLY-003) — "THE 시스템 SHALL 해당 종목의 우선순위를 높일 수 있다" combines SHALL (mandatory obligation) with "높일 수 있다" (may/can increase). This is self-contradictory: SHALL establishes a mandate while "수 있다" removes it. The EARS Optional pattern (WHERE) still requires SHALL to assert a mandatory response. — Severity: **major**

**D10.** acceptance.md:L21–24 (AC-3) — "과도하게 집중" (overly concentrated) has no numeric threshold. A tester cannot determine PASS/FAIL without knowing at what percentage a sector is "over-concentrated." Not binary-testable. — Severity: **minor**

**D11.** acceptance.md:L44–48 (AC-7) — "분석 관점 설명과 면책 안내를 포함한다" has no measurable criteria. No definition of what phrases or patterns constitute compliant "analysis perspective" or "disclaimer." Not binary-testable without judgment call. — Severity: **minor**

---

## Chain-of-Verification Pass

Second-look findings: One new defect discovered in second pass.

- **D9 (new)**: Found on re-read of REQ-AIEX-APPLY-003 — "SHALL... 높일 수 있다" self-contradiction was not flagged in first-pass scan of requirements.
- **D4**: Confirmed on re-read — subsection header `REQ-AIEX-NFR` vs item labels `NFR-001..005` is internally inconsistent within the same subsection.
- REQ sequencing within each group: Verified all groups are internally sequential with no gaps (PORT 001-004, RAT 001-003, PREF 001-003, APPLY 001-003, HIST 001-002, OWN 001). No intra-group gap or duplicate found.
- Every AC subject verified: all 17 ACs correctly use "THE 시스템 SHALL" — no wrong subject (not "THE 추천 SHALL" etc.).
- Exclusions section verified for specificity: 7 entries, each with concrete rationale. Adequate.
- No contradiction found between Exclusions and included requirements.

---

## Recommendation

SPEC-STOCK-037 requires revision on four critical dimensions before it can pass audit. The following fixes are mandatory:

**Fix 1 (MP-3, D1): Rename YAML field** — spec.md:L5. Change `created: 2026-06-25` to `created_at: 2026-06-25`.

**Fix 2 (MP-3, D2): Add missing YAML field** — spec.md: insert `labels` field in the frontmatter block (e.g., `labels: [ai, recommendation, personalization]`).

**Fix 3 (MP-2, D3): Rewrite all 17 ACs in EARS format** — acceptance.md. Replace every Given/When/Then structure with a valid EARS sentence. Examples by pattern:
- Event-driven (replaces AC-1): "WHEN 사용자가 보유 종목이 있는 포트폴리오에 대한 개인화 추천을 요청하면, THE 시스템 SHALL 해당 포트폴리오의 보유 종목과 섹터 노출을 입력 맥락으로 사용하여 추천을 산출한다."
- Unwanted (replaces AC-4): "IF 요청된 포트폴리오에 보유 종목이 없으면, THEN THE 시스템 SHALL 추천 산출을 시도하지 않고 보유 종목이 없음을 알리는 안내 응답을 반환한다."
- State-driven (replaces AC-11): "WHILE 사용자가 종목 C를 싫어요로 표시한 상태이면, THE 시스템 SHALL 개인화 추천에서 종목 C를 후순위로 조정하거나 제외한다."

**Fix 4 (MP-1, D4): Rename NFR entries** — spec.md:L79–83. Either rename `NFR-001`..`NFR-005` to `REQ-AIEX-NFR-001`..`REQ-AIEX-NFR-005` (consistent with the subsection header), or integrate NFRs as additional REQ-AIEX-* entries with flat sequential numbering.

**Fix 5 (D5): Remove library names from NFR-001** — spec.md:L79. Rewrite as behavioral outcome: e.g., "THE 시스템 SHALL 점수·순위 계산에 외부 수치 라이브러리를 최소화하고 표준 수학 연산 기반의 순수 함수로 구현한다." (Remove specific library names scipy and numpy from normative text; they belong in the Implementation Notes or Tasks section.)

**Fix 6 (D6): Add AC for REQ-AIEX-APPLY-003** — acceptance.md. Add an AC covering the Optional requirement: "WHERE 사용자가 좋아요로 표시한 종목과 유사한 종목이 추천 풀에 존재하면, THE 시스템 SHALL 해당 종목의 추천 우선순위를 높인다."

**Fix 7 (D7): Add AC for NFR-001** — acceptance.md. Add an AC verifiable without running the system against scipy: e.g., "When the ranking computation module is invoked, THE 시스템 SHALL produce results using only standard math operations (no scipy dependency resolvable at import time)."

**Fix 8 (D8): Add AC for NFR-005** — acceptance.md. Add an AC covering the read-then-write preference pattern.

**Fix 9 (D9): Correct APPLY-003 SHALL/수 있다 contradiction** — spec.md:L66. Change "높일 수 있다" to "높인다" so the SHALL obligation is unambiguous. Or, if the behavior is truly optional, remove SHALL and use a non-normative note.

**Fix 10 (D10, D11): Add measurable thresholds to AC-3 and AC-7** — acceptance.md:L21–24 and L44–48. For AC-3: define a numeric threshold for sector concentration (e.g., "단일 섹터 비중이 50% 초과"). For AC-7: specify detectable phrases or patterns that constitute a compliant disclaimer (e.g., "이 정보는 투자 권유가 아닙니다" 포함 여부로 판정).
