# plan-auditor Review — SPEC-STOCK-038-review-1

Score: 0.62
Result: FAIL
Threshold: 0.80

---

## Critical Issues (Must-Pass)

### MP-4 FAIL: EARS Pattern Violation in REQ-DASH-008

spec.md:L109–L111

```
### REQ-DASH-008 — 로딩 상태 (Event-driven)

WHEN 대시보드 데이터를 조회하는 중이면, THE 시스템 SHALL 각 차트 영역에 로딩 표시를 노출한다.
```

The label "(Event-driven)" and keyword `WHEN` are both wrong for this condition. "조회하는 중이면" (while querying) describes a **persistent state**, not a discrete event. The correct EARS pattern is State-driven: `WHILE [condition], THE 시스템 SHALL [response]`.

The corresponding acceptance criterion (acceptance.md:L50) correctly uses `WHILE`, exposing the contradiction:

```
WHILE 대시보드 데이터를 조회하는 중이면, THE 시스템 SHALL 각 차트 영역에 로딩 표시를 노출한다.
```

`WHEN` triggers on an event (a single transition). `WHILE` holds during a state (a duration). Using `WHEN` for a state violates MP-4.

---

### MP-5 FAIL: Library Names in REQ Text (REQ-DASH-NFR-001)

spec.md:L121–L123

```
### REQ-DASH-NFR-001 — 계산 라이브러리 제약 (Unwanted)

IF 대시보드 집계에 수치 계산이 필요하면, THEN THE 시스템 SHALL scipy를 사용하지 않고
numpy 및 표준 수학 연산만으로 계산한다.
```

`scipy` and `numpy` are specific library names hardcoded in the REQ text. Requirements must state WHAT is required (the constraint on the system's behavior), not HOW via named tools. The REQ should express the constraint in technology-neutral terms — e.g., "외부 과학 계산 라이브러리를 사용하지 않고 표준 산술 연산만으로 계산한다".

Note: acceptance.md:L58 (AC-13) correctly avoids naming specific libraries: "외부 과학 계산 라이브러리를 사용하지 않는다". The AC is well-written; the source REQ is not.

---

## Defects

**D1. spec.md:L107 / acceptance.md:L46** — "의미 있는 빈 상태 안내" is vague.

REQ-DASH-007 and AC-10 both use "의미 있는" (meaningful) without defining what constitutes a meaningful empty-state message. A tester cannot determine PASS/FAIL without judgment. Severity: **minor**.

Fix: Replace "의미 있는 빈 상태 안내" with a testable specification, e.g., "해당 기간에 데이터가 없음을 설명하는 텍스트 안내".

---

**D3. acceptance.md:AC-5 / AC-6** — Missing edge-case test for single-type portfolios.

AC-5 and AC-6 cover the normal aggregation case and the sum=100 invariant, but there is no AC for a portfolio where all holdings are 100% domestic (no foreign entries) or vice versa. The sum=100 AC-6 also has no defined tolerance for floating-point rounding (e.g., 33.33+33.33+33.34). Severity: **minor**.

---

**D4. spec.md:L109–L111 vs acceptance.md:L50** — EARS keyword mismatch between REQ and AC.

REQ-DASH-008 in spec.md uses `WHEN`; AC-11 in acceptance.md uses `WHILE`. These describe the same requirement with different EARS patterns. This inconsistency means an implementer reading the REQ and a tester reading the AC may develop different mental models of when the loading indicator should appear. Severity: **major** (same root cause as MP-4 above; fixing MP-4 also resolves D4).

---

## Chain-of-Verification Pass

Second-look findings: No new issues discovered beyond those identified in the first pass.

Verified in second pass:
- All 14 REQ-DASH-* entries read in full (001–009, NFR-001–005)
- REQ number sequencing confirmed end-to-end: 001→009 sequential, NFR-001→005 sequential, no gaps
- Traceability verified for all 14 REQs → all have at least 1 AC; all 17 ACs trace to existing REQs
- Exclusions section (spec.md:L144–L155): 9 specific exclusions, sufficiently concrete
- No contradictions found between functional requirements within spec.md
- REQ-DASH-NFR-004 references "props" (React-specific term) — borderline, but acceptable given this is an explicitly React-scoped SPEC

---

## Recommendation

Two fixes required before PASS:

1. **Fix MP-4** — spec.md:L109: Change label and keyword.
   - Change `(Event-driven)` to `(State-driven)`
   - Change `WHEN 대시보드 데이터를 조회하는 중이면,` to `WHILE 대시보드 데이터를 조회하는 중이면,`
   - This also resolves D4 (WHEN/WHILE mismatch with AC-11).

2. **Fix MP-5** — spec.md:L123: Remove specific library names from REQ text.
   - Current: `THE 시스템 SHALL scipy를 사용하지 않고 numpy 및 표준 수학 연산만으로 계산한다.`
   - Replace with: `THE 시스템 SHALL 외부 과학 계산 라이브러리를 사용하지 않고 표준 산술 연산만으로 집계를 수행한다.`
   - The technology-stack section (spec.md:L61) may retain the specific library names as context, as that section describes HOW, not WHAT.

Optional improvements (not blocking):

3. **D1** — spec.md:L107, acceptance.md:L46: Replace "의미 있는 빈 상태 안내" with a concrete description of the minimum required content for the empty-state message.

4. **D3** — acceptance.md: Add AC for 100%-single-type portfolio (e.g., all domestic, no foreign) to validate AC-6 sum=100 holds; add floating-point tolerance clarification.
