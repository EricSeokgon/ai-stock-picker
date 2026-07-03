# SPEC Review Report: SPEC-STOCK-037
Iteration: 2/3
Verdict: FAIL
Overall Score: 0.81

---

## Must-Pass Results

- [PASS] **MP-1 REQ number consistency**: All NFR entries now carry the `REQ-AIEX-NFR-` prefix (spec.md:L81–85). Seven sub-groups verified end-to-end: PORT (001–004), RAT (001–003), PREF (001–003), APPLY (001–003), HIST (001–002), OWN (001), NFR (001–005). No gaps, no duplicates, consistent three-digit zero-padding within every group. D4 from review-1 is RESOLVED.

- [FAIL] **MP-2 EARS format compliance**: 19 of 20 ACs conform to canonical EARS patterns. AC-3 (acceptance.md:L18) uses a non-canonical hybrid: `"WHEN 추천 결과를 생성할 때 특정 섹터의 비중이 전체 포트폴리오의 50%를 초과하면, THEN THE 시스템 SHALL ..."`. The THEN keyword belongs exclusively to the Unwanted pattern (`IF [condition], THEN the [system] shall [response]`). The Event-Driven pattern is `WHEN [trigger], the [system] shall [response]` — no THEN. Mixing the WHEN event marker with the THEN consequence marker from a different pattern violates the rule "mixed informal/formal within a single criterion = FAIL." No other AC exhibits this deviation. Nineteen ACs are EARS-compliant; one is not. MP-2 requires every criterion to match exactly one of the five EARS patterns.

- [PASS] **MP-3 YAML frontmatter validity**: All six required fields are present with correct types. `id: SPEC-STOCK-037` (string, spec.md:L2), `version: 0.2.0` (string, spec.md:L3), `status: draft` (string, spec.md:L4), `created_at: 2026-06-25` (ISO date string, spec.md:L5 — D1 resolved), `priority: high` (string, spec.md:L9), `labels: [ai, recommendation, portfolio]` (array, spec.md:L10 — D2 resolved). No type mismatches.

- [N/A] **MP-4 Section 22 language neutrality**: Single-language Python + React project. Auto-passes.

---

## Category Scores (0.0–1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 band | Core requirements are unambiguous. Two residual vagueness points: (1) "유사한 종목" (similar stocks) is referenced in REQ-AIEX-APPLY-002 (spec.md:L67), REQ-AIEX-APPLY-003 (spec.md:L68), and AC-13 (acceptance.md:L58) without a definition of similarity — AC-12 operationalizes it as "같은 섹터" for APPLY-002 but AC-13 still leaves "유사한" undefined; (2) "분석 관점 설명" in AC-7 (acceptance.md:L34) lacks a detectable criterion. Minor ambiguity; a reasonable engineer would likely resolve it but interpretations could diverge. |
| Completeness | 0.75 | 0.75 band | All required document sections present: HISTORY (spec.md:L15–17), 개요 (WHY + WHAT merged, spec.md:L22–28), REQUIREMENTS (spec.md:L43–85, 21 entries), ACCEPTANCE CRITERIA (acceptance.md, 20 entries), Exclusions (spec.md:L89–97, 7 specific entries). YAML frontmatter complete. WHY and WHAT sections are not individually labeled — merged into 개요 — minor structural point but not a completeness failure. |
| Testability | 0.75 | 0.75 band | Most ACs are binary-testable. D10 resolved: AC-3 now specifies "50%를 초과하면" providing a concrete numeric threshold. Two residual issues: (1) AC-7 (acceptance.md:L34) — "분석 관점 설명과 면책 안내를 포함한다" — requires a judgment call as to what constitutes an "analysis perspective"; the absence of prohibited phrases is binary-testable but "분석 관점 설명" presence is not; (2) AC-13 (acceptance.md:L58) — "유사한 종목이 존재하는 상태이면" — without a similarity definition a tester cannot determine the state boundary. |
| Traceability | 1.0 | 1.0 band | All 21 REQ-AIEX-* entries have at least one AC. D6 (APPLY-003 missing AC), D7 (NFR-001 missing AC), D8 (NFR-005 missing AC) are all RESOLVED. Coverage: PORT-001→AC-1, PORT-002→AC-2, PORT-003→AC-3, PORT-004→AC-4, RAT-001→AC-5, RAT-002→AC-6, RAT-003→AC-7, PREF-001→AC-8, PREF-002→AC-9, PREF-003→AC-10, APPLY-001→AC-11, APPLY-002→AC-12, APPLY-003→AC-13, HIST-001→AC-14, HIST-002→AC-15, OWN-001→AC-16, NFR-001→AC-19, NFR-002→AC-18, NFR-003→AC-16 (dual-trace), NFR-004→AC-17, NFR-005→AC-20. No orphaned ACs; no uncovered REQs. |

---

## Defects Found

**D-new-1.** acceptance.md:L18 — AC-3 uses `"WHEN [condition], THEN THE 시스템 SHALL [response]"` — a non-canonical hybrid mixing the WHEN event marker (Event-Driven pattern) with the THEN consequence marker (Unwanted pattern only). Neither Event-Driven (`WHEN..., the [system] shall`) nor Unwanted (`IF..., THEN the [system] shall`) is satisfied. All other 19 ACs conform. — Severity: **critical** (triggers MP-2 failure)

**D11 (unresolved from review-1, minor).** acceptance.md:L34 — AC-7 states "분석 관점 설명과 면책 안내를 포함한다" with no measurable definition of "분석 관점 설명" (analysis-perspective explanation). The absence of investment-recommendation language is binary-testable; the PRESENCE of a qualifying "analysis perspective" is not, without a concrete criterion (e.g., a required phrase or content pattern). — Severity: **minor**

**D-new-2.** acceptance.md:L58 — AC-13 references "사용자가 좋아요로 표시한 종목과 유사한 종목이 존재하는 상태" without defining what "유사한" (similar) means. AC-12 operationalizes "유사한" as "같은 섹터" for APPLY-002 but AC-13 (covering APPLY-003) leaves the similarity criterion undefined. A tester cannot determine whether the trigger state is active without a concrete similarity definition. — Severity: **minor**

---

## Chain-of-Verification Pass

Second-look findings: one additional minor defect found (D-new-2: AC-13 "유사한" undefined), and one first-pass finding confirmed (D-new-1: AC-3 WHEN/THEN hybrid).

Re-read verification:
- All 21 REQ identifiers verified individually end-to-end: PORT(4), RAT(3), PREF(3), APPLY(3), HIST(2), OWN(1), NFR(5). No gaps discovered in second pass.
- All 20 AC-to-REQ trace mappings verified: no orphaned ACs, no uncovered REQs confirmed.
- Exclusions section re-read: 7 entries (자동 매매, 실시간 시세 피드, ML 모델 학습, 소셜·뉴스 감성 신규 수집, 4요인 스코어 산식 변경, 전역 추천 파이프라인 재작성, 기존 전역 피드백 의미 변경) — all specific with rationale. No conflict with included requirements.
- Contradictions check: APPLY-001 (downrank/exclude disliked), APPLY-002 (downrank similar to disliked), APPLY-003 (boost similar to liked) — these are additive, non-contradictory. Exclusion of "ML 모델 학습" is consistent with REQs that use rule-based preference application only.
- AC-3 WHEN/THEN deviation was caught on first pass and confirmed on second pass.
- D11 (AC-7 testability gap) remains unchanged from review-1; no fix was listed in the review-1 fix notes and the text is identical in v0.2.0.

---

## Regression Check (Iteration 2)

Defects from review-1 and their resolution status:

- **D1** (spec.md:L5, `created` → `created_at`): [RESOLVED] — spec.md:L5 now reads `created_at: 2026-06-25`.
- **D2** (missing `labels` field): [RESOLVED] — spec.md:L10 now has `labels: [ai, recommendation, portfolio]`.
- **D3** (all 17 ACs in GWT/Gherkin format): [RESOLVED] — All 20 ACs in v0.2.0 use EARS patterns. Systematic GWT structure is gone.
- **D4** (NFR-001..005 prefix inconsistency): [RESOLVED] — All NFR entries now use `REQ-AIEX-NFR-001`..`REQ-AIEX-NFR-005` (spec.md:L81–85).
- **D5** (NFR-001 hardcoded library names scipy/numpy): [RESOLVED] — spec.md:L81 now reads "외부 과학 계산 라이브러리에 의존하지 않는다" with no specific library names.
- **D6** (REQ-AIEX-APPLY-003 no AC): [RESOLVED] — AC-13 added at acceptance.md:L56–58.
- **D7** (NFR-001 no AC): [RESOLVED] — AC-19 added at acceptance.md:L80–82.
- **D8** (NFR-005 no AC): [RESOLVED] — AC-20 added at acceptance.md:L84–86.
- **D9** (REQ-AIEX-APPLY-003 SHALL/수 있다 contradiction): [RESOLVED] — spec.md:L68 now reads "THE 시스템 SHALL 해당 종목의 우선순위를 높인다." (unconditional SHALL).
- **D10** (AC-3 no numeric threshold for sector over-concentration): [RESOLVED] — acceptance.md:L18 now specifies "50%를 초과하면."
- **D11** (AC-7 "분석 관점 설명" not binary-testable): [UNRESOLVED] — Text at acceptance.md:L34 is unchanged from review-1. No fix was listed in the v0.2.0 changelog (spec.md:L17).

---

## Recommendation

Ten of eleven review-1 defects are resolved. One minor review-1 defect (D11) is unresolved and one new critical defect (D-new-1: AC-3 WHEN/THEN) triggers MP-2 failure. One new minor defect (D-new-2: AC-13 "유사한" undefined) was discovered.

Required actions for PASS:

**Fix 1 (D-new-1, MP-2, critical): Remove THEN from AC-3.**
acceptance.md:L18. Change:
`"WHEN 추천 결과를 생성할 때 특정 섹터의 비중이 전체 포트폴리오의 50%를 초과하면, THEN THE 시스템 SHALL 해당 섹터의 추가 추천을 제외하고 다른 섹터 종목을 우선하는 분산 지향 추천을 제시한다."`
to:
`"WHEN 추천 결과를 생성할 때 특정 섹터의 비중이 전체 포트폴리오의 50%를 초과하면, THE 시스템 SHALL 해당 섹터의 추가 추천을 제외하고 다른 섹터 종목을 우선하는 분산 지향 추천을 제시한다."`
(Remove the word "THEN" to conform to the Event-Driven EARS pattern.)

Recommended actions (minor, not blocking PASS individually but improve testability):

**Fix 2 (D11, minor): Specify a testable criterion for AC-7 disclaimer.**
acceptance.md:L34. Add a detectable phrase criterion, for example:
`"THE 시스템 SHALL 개인화 추천 근거 텍스트에 투자 권유·수익 보장 표현을 포함하지 않으며, '이 정보는 투자 권유가 아닙니다' 또는 이에 준하는 면책 문구를 포함한다."`

**Fix 3 (D-new-2, minor): Define "유사한" in AC-13.**
acceptance.md:L58. Operationalize similarity consistently with AC-12, for example:
`"WHILE 사용자가 좋아요로 표시한 종목과 같은 섹터의 종목이 추천 풀에 존재하는 상태이면, THE 시스템 SHALL 이후 개인화 추천에서 해당 종목의 우선순위를 높인다."`
