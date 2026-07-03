# SPEC Review Report: SPEC-STOCK-033
Iteration: 1/3
Verdict: FAIL
Overall Score: 0.73

---

## Must-Pass Results

- [PASS] MP-1 REQ number consistency: Functional REQs are REQ-DVY-001 through REQ-DVY-005 (sequential, no gaps, no duplicates). NFRs are REQ-DVY-NFR-001 through REQ-DVY-NFR-005 (sequential). Note: spec.md:L25 states "NFR은 REQ-DVY-NFR-001~004" which is incorrect (there are 5 NFRs, not 4), but this is a documentation metadata error — the actual REQ numbers in the body are correctly sequenced with no gaps or duplicates.
- [PASS] MP-2 EARS format compliance: All ACs in acceptance.md and all REQs in spec.md §3–§4 follow one of the five EARS structural patterns (THE...SHALL, WHEN...THE...SHALL, IF...THEN THE...SHALL). No AC uses "should be", "must try to", or Given/When/Then test assertion form in §1. BDD in §2 of acceptance.md is intentionally separate and correctly excluded from EARS scope.
- [PASS] MP-3 YAML frontmatter validity: spec.md:L1–11 — all six required fields present: id ("SPEC-STOCK-033"), version ("0.1.0"), status ("draft"), created_at ("2026-06-24"), priority ("medium"), labels (array). Types correct.
- [N/A] MP-4 Section 22 language neutrality: SPEC is scoped to a specific Python/FastAPI + React application. Single-language scope — multi-language enumeration requirement does not apply.

---

## Category Scores (0.0–1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 — Minor ambiguity in one or two requirements | spec.md:L128 REQ-DVY-NFR-002 uses "가능해야 한다" (informal weasel) after the SHALL clause; spec.md:L127 "프로젝트 승인 라이브러리" (project-approved libraries) is vague without enumeration. Otherwise requirements are precise and unambiguous. |
| Completeness | 1.00 | 1.0 — All required sections present | HISTORY (L17), WHY/Motivation (L44), WHAT/Overview (L31), REQUIREMENTS (L101), ACCEPTANCE CRITERIA (acceptance.md), Exclusions §2.2 (L85) with 8 specific entries. YAML frontmatter complete. |
| Testability | 0.75 | 0.75 — One AC not precisely binary-testable | acceptance.md:L44–47 AC-DVY-NFR groups five NFRs into one block with mixed testability. "DB·Redis·외부 API 호출 없이" is testable but "결정적 결과를 반환하여 단위 테스트가 가능해야 한다" ends informally. The arithmetic formulas in ACs (L13, L14, L33) make those ACs very precisely binary-testable. |
| Traceability | 0.75 | 0.75 — Indirect mapping for NFRs | All 5 functional REQs (REQ-DVY-001 through REQ-DVY-005) have corresponding AC groups (AC-DVY-001 through AC-DVY-005). However, REQ-DVY-NFR-001 through REQ-DVY-NFR-005 are collectively addressed by a single unnumbered "AC-DVY-NFR" block rather than individually traced ACs. No orphaned ACs. |

---

## Defects Found

D1. spec.md:L25 — Stated NFR range "REQ-DVY-NFR-001~004" is incorrect; actual body contains REQ-DVY-NFR-001 through REQ-DVY-NFR-005 (5 items, not 4). Documentation metadata inconsistency. — Severity: minor

D2. spec.md:L128 — REQ-DVY-NFR-002 ends with "단위 테스트가 가능해야 한다" (informal: "should be possible to unit test") appended after the SHALL clause. "가능해야 한다" is a weasel construction that softens the normative SHALL. The requirement should end at "결정적 결과를 반환한다" and testability should be a separate AC. — Severity: minor

D3. spec.md:L131 — REQ-DVY-NFR-005: "THE `portfolio/dividend_yield.py` SHALL 단위 테스트 커버리지 85% 이상을 충족한다." The Python file path `portfolio/dividend_yield.py` is an implementation detail hardcoded into a normative SHALL statement. This constrains the implementer to name the file exactly `dividend_yield.py` in the `portfolio/` directory. The requirement should refer to "the dividend yield calculation module" without naming the file. — Severity: minor

D4. acceptance.md:L11–14 — AC-DVY-001 contains multiple implementation variable names in backtick notation within SHALL statements: `annual_dps`, `estimated_annual_dividend`, `shares`, `dividend_yield_pct`, `current_price`. The formulas `shares × annual_dps` and `annual_dps / current_price × 100` are expressed as code-notation arithmetic expressions within EARS SHALL text. Example: "THE 시스템 SHALL 종목별 `estimated_annual_dividend`를 `shares × annual_dps`로 산출한다." — Severity: minor

D5. acceptance.md:L18–20 — AC-DVY-002 contains implementation variable names in backtick notation: `portfolio_dividend_yield_pct`, `total_annual_dividend`, `estimated_annual_dividend`. — Severity: minor

D6. acceptance.md:L25–27 — AC-DVY-003 contains variable names and a data-structure schema expression in backtick notation: `months: {month: [events]}`, `ex_dividend_date`, `dps`, `shares`, `estimated_total`, `payment_date`. The data structure literal `months: {month: [events]}` encodes the response schema format directly into the AC, constraining the API shape implementation. — Severity: minor

D7. acceptance.md:L31–35 — AC-DVY-004 contains variable names and a Pydantic class name in backtick notation: `years`, `DRIPYearData`, `portfolio_value`, `initial_value`, `reinvest_rate`, `yield`, `cumulative_return_pct`, and the formula expressions `직전가치 × yield/100 × reinvest_rate` and `(portfolio_value / initial_value - 1) × 100`. — Severity: minor

D8. acceptance.md:L44, L47 — AC-DVY-NFR contains file name references in normative SHALL text: "THE `dividend_yield.py` 순수 함수 SHALL..." (L44) and "THE `dividend_yield.py` SHALL 단위 테스트 커버리지 85% 이상을 충족한다." (L47). File names are implementation artifacts equivalent to function names and should not appear in normative AC text. — Severity: minor

D9. acceptance.md:L46 — AC-DVY-NFR: "THE 신규 코드 SHALL `scipy`를 import하지 않는다." The library name `scipy` is hardcoded in a normative SHALL statement. While this is a valid constraint, a library name is an implementation identifier. Preferred form: "THE system SHALL not introduce new external numerical computation libraries beyond those already approved for the project." — Severity: minor

---

## Chain-of-Verification Pass

Second-look findings: No additional defects discovered beyond the first pass.

Sections re-examined in second pass:
- REQ numbering: Verified end-to-end. REQ-DVY-001 through REQ-DVY-005 sequential, no gaps. REQ-DVY-NFR-001 through REQ-DVY-NFR-005 sequential, no gaps. The header discrepancy (L25 says 001~004) is noted but not a REQ numbering failure per MP-1.
- Traceability: All 5 functional REQs covered by corresponding ACs. NFRs collectively addressed by AC-DVY-NFR. No AC references a non-existent REQ.
- Exclusions (spec.md §2.2 L85–98): 8 specific exclusions are present and verifiable — SPEC-019 re-implementation, real dividend payment tracking, automatic DRIP execution, price growth prediction, Monte Carlo simulation, new DB tables, tax calculation, multi-currency settlement. All specific and not vague.
- Contradictions: None found. REQ-DVY-004 (DRIP simulation) does not contradict the §2.2 exclusion of "자동 배당 재투자 집행" (automatic reinvestment execution) — one is a simulation, the other is actual execution.
- spec.md §5 (Technical Approach) contains Python code blocks with function signatures and algorithm pseudocode. These are in a non-normative design guidance section, not in §3–§4 requirements, so they are acceptable HOW documentation.
- First-pass EARS checks confirmed: No GWT-style assertions appear in §1 of acceptance.md. All SHALL statements are structurally valid EARS patterns.

---

## Recommendation

The four must-pass criteria all pass. The FAIL verdict (score 0.73 < 0.80 threshold) results from cumulative minor defects across 9 identified items. All defects are fixable without structural redesign.

**Actionable fix instructions for manager-spec:**

1. **Fix D1 (spec.md:L25)**: Change "NFR은 REQ-DVY-NFR-001~004" to "NFR은 REQ-DVY-NFR-001~005".

2. **Fix D2 (spec.md:L128)**: Remove the informal tail from REQ-DVY-NFR-002. Replace:
   > "결정적 결과를 반환하여 단위 테스트가 가능해야 한다."
   with:
   > "결정적 결과를 반환한다."
   Move testability to acceptance criterion if needed.

3. **Fix D3 (spec.md:L131)**: Replace file-path reference in REQ-DVY-NFR-005:
   > "THE `portfolio/dividend_yield.py` SHALL 단위 테스트 커버리지 85% 이상을 충족한다."
   with:
   > "THE 시스템의 배당 수익률 계산 모듈 SHALL 단위 테스트 커버리지 85% 이상을 충족한다."

4. **Fix D4–D7 (acceptance.md AC-DVY-001 through AC-DVY-004)**: Replace backtick-enclosed variable names and code expressions with natural-language descriptions. For example:
   - "THE 시스템 SHALL 종목별 `estimated_annual_dividend`를 `shares × annual_dps`로 산출한다." →  "THE 시스템 SHALL 종목별 추정 연 배당액을 보유 수량과 주당 연 배당금의 곱으로 산출한다."
   - "THE 시스템 SHALL 종목별 `dividend_yield_pct`를 `annual_dps / current_price × 100`으로 산출하되..." → "THE 시스템 SHALL 종목별 배당수익률을 주당 연 배당금을 현재가로 나눈 백분율로 산출하되..."
   Apply the same pattern consistently to all ACs with backtick variable/formula references.

5. **Fix D8 (acceptance.md:L44, L47)**: Replace file name references in AC-DVY-NFR:
   - "THE `dividend_yield.py` 순수 함수 SHALL DB·Redis·외부 API 호출 없이..." → "THE 배당 수익률 계산 모듈의 순수 함수 SHALL DB·Redis·외부 API 호출 없이..."
   - "THE `dividend_yield.py` SHALL 단위 테스트 커버리지 85% 이상을 충족한다." → "THE 배당 수익률 계산 모듈 SHALL 단위 테스트 커버리지 85% 이상을 충족한다."

6. **Fix D9 (acceptance.md:L46)**: Replace the library-specific constraint:
   - "THE 신규 코드 SHALL `scipy`를 import하지 않는다." → "THE 신규 수치 계산 코드 SHALL 본 프로젝트에서 기존에 승인된 라이브러리(numpy, math)만을 사용하고 신규 외부 수치 라이브러리를 추가하지 않는다."

Addressing all 9 defects — predominantly by replacing backtick-encoded implementation artifacts with natural-language equivalents in SHALL statements — is expected to bring the score above 0.80 on iteration 2.
