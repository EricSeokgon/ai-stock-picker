# SPEC-STOCK-032 Plan Audit — Review 1

## Verdict: FAIL (score: 0.00)

> Score calculation: 1.00 − 4×0.15 (critical) − 5×0.10 (major) − 2×0.03 (minor) = −0.16 → floored to 0.00. PASS threshold is 0.80.

---

## Must-Pass Results

- **[FAIL] MP-1 REQ Number Consistency**: REQ-RBA-001~006 are sequential with no gaps and consistent zero-padding. NFR-001~006 use a different prefix (not REQ-) and are also sequentially numbered. No violation. However, MP-1 passes only for the REQ-RBA-* series. PASS for REQ numbering.
- **[FAIL] MP-2 EARS Format Compliance**: Multiple acceptance criteria and requirements use WHEN...THEN...form (non-EARS Event-driven) or assertion form ("X는 Y여야 한다") rather than "THE 시스템 SHALL". See D5–D9 below.
- **[PASS] MP-3 YAML Frontmatter Validity**: All six required fields present — `id: "SPEC-STOCK-032"` (L2), `version: "0.1.0"` (L3), `status: "draft"` (L4), `created_at: "2026-06-23"` (L5), `priority: "high"` (L8), `labels: [...]` (L10). Types correct.
- **[N/A] MP-4 Language Neutrality**: This SPEC is scoped to a single-technology project (Python + JavaScript). KRX/NYSE/NASDAQ refer to stock exchanges, not programming languages. N/A.

**Overall Verdict: FAIL — MP-2 EARS Format Compliance fails.**

---

## Defects Found

### Critical — Normative text contains implementation details

**D1. spec.md:L126-127 — NFR-001 hardcodes library names in normative SHALL**

> "THE 시스템 SHALL 본 SPEC 신규 코드에서 `scipy`를 import하지 않는다. 수치 계산은 `numpy` + `math`만 사용한다"

Library names (`scipy`, `numpy`, `math`) are implementation details. A normative requirement must express the architectural constraint ("The system shall use only standard numeric libraries") without naming specific libraries. Naming libraries blocks implementors from substituting equivalent tools and encodes HOW, not WHAT.

**D2. spec.md:L128 — NFR-002 uses function name as the SHALL subject**

> "THE `calculate_rebalancing_orders` 순수 함수 SHALL DB·Redis·외부 API 의존 없이..."

`calculate_rebalancing_orders` is an implementation-level function name. A requirement must describe the behavior, not the name of the artifact that satisfies it ("The rebalancing calculation function shall be testable without external dependencies").

**D3. spec.md:L131 — NFR-005 hardcodes HTTP status code in normative requirement**

> "소유권 위반 시 `404 Not Found`로 응답한다(코드베이스 관례, 403 아님)"

HTTP status codes are implementation/protocol details. The audit instructions explicitly list "HTTP status codes" as forbidden in normative requirements text. The observable behavior should be expressed as "The system shall reject requests from unauthorized users with a not-found response" without specifying the code literal.

**D4. acceptance.md:L43 — AC-NFR-001 embeds a shell command as verification criteria**

> "AC-NFR-001: `portfolio/rebalancing.py`는 `scipy`를 import하지 않는다(`grep -r "import scipy"` 결과 없음)."

An acceptance criterion must be a binary-testable EARS statement, not a shell command (`grep -r "import scipy"`). The verification method is a test procedure, not a requirement. Additionally, the file path `portfolio/rebalancing.py` is an implementation detail embedded in a normative AC.

---

### Major — EARS pattern violated

**D5. spec.md:L100 — REQ-RBA-001 uses WHEN...THEN form (non-standard EARS)**

> "WHEN 사용자가 포트폴리오에 대해 리밸런싱 주문 계산을 요청하면 THEN THE 시스템 SHALL..."

Standard EARS Event-driven pattern: "When [trigger], the [system] shall [response]." The word "THEN" before "THE 시스템 SHALL" is not part of the EARS Event-driven template. It appears in the EARS Unwanted pattern ("If [condition], then the system shall…") but not Event-driven. The presence of "THEN" makes this a hybrid BDD/EARS form.

**D6. spec.md:L112 — REQ-RBA-004 uses WHEN...THEN form (same violation)**

> "WHEN 복수 종목이 리밸런싱 대상이면 THEN THE 시스템 SHALL 언더웨이트(매수) 종목을..."

Same non-standard EARS issue as D5.

**D7. spec.md:L116 — REQ-RBA-005 mixes two EARS patterns in a single requirement entry**

> "WHEN 사용자가 `dry_run=true`(기본)로 주문을 미리보기하면 THEN THE 시스템 SHALL DB에 기록하지 않고... IF 사용자가 `dry_run=false`로 확정하면 THEN THE 시스템 SHALL 주문 계획서를... 저장하고..."

A single EARS requirement entry must express exactly one trigger/response pair. This entry combines an Event-driven pattern (WHEN...SHALL) and an Unwanted/optional pattern (IF...THEN...SHALL) in a single bullet. These must be split into two separate requirements.

**D8. acceptance.md:L11-12 — AC-RBA-001 uses assertion form, not EARS**

> "WHEN `calculate_rebalancing_orders`가 holdings·target_weights·budget을 받으면 THEN 각 종목의 `quantity`는 정수(1주 단위)여야 한다."

The response clause "각 종목의 `quantity`는 정수여야 한다" is an assertion (X must be Y), not an EARS response clause. Standard EARS: "When [trigger], the system shall [observable system action]." Additionally, the AC references the internal function name `calculate_rebalancing_orders`.

**D9. acceptance.md:L16 — AC-RBA-002 first criterion uses WHILE...THEN (non-EARS)**

> "WHILE 매수 주문을 산출하는 동안 THEN 모든 `buy` 주문의 `estimated_amount` 합계(`total_buy_amount`)는 `budget`을 초과하지 않아야 한다."

Standard EARS State-driven: "While [condition], the [system] shall [response]." This criterion uses "THEN" (not part of State-driven pattern) and formulates the response as an assertion ("초과하지 않아야 한다") rather than "THE 시스템 SHALL [action]."

---

### Minor — Ambiguous values / missing cross-references

**D10. acceptance.md — NFR-003 has no dedicated AC-NFR-003 entry**

The NFR section in spec.md defines NFR-003 (market-based commission differentiation, L128-129), but the AC-NFR block in acceptance.md jumps from AC-NFR-002 (L43) directly to AC-NFR-004 (L44). NFR-003 is tested indirectly through Scenario 3 and AC-RBA-003 but has no dedicated traceability entry.

**D11. acceptance.md:L28 — AC-RBA-004 references internal variable name `delta_value`**

> "WHEN 예산이 모든 매수를 충족하기에 부족하면 THEN 조정 금액(delta_value)이 큰 언더웨이트 종목부터..."

`delta_value` is an internal algorithm variable name embedded in an EARS acceptance criterion. The AC should describe observable sorting behavior without naming internal variables.

---

## Category Scores (rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 — Minor ambiguity in one or two requirements | REQ-RBA-005 (L116) requires interpretation of two behaviors from one entry. All other REQs are unambiguous in intent. |
| Completeness | 0.75 | 0.75 — One non-critical section missing | All required sections present. Separate acceptance.md file fully cross-referenced. HISTORY, WHY (동기), WHAT (범위), REQUIREMENTS, AC (via reference), Exclusions all present. Deduct for AC-NFR-003 traceability gap. |
| Testability | 0.50 | 0.50 — Several ACs contain weasel words or require judgment | acceptance.md:L11, L16, L21 use assertion form ("X여야 한다") which requires interpretation. AC-NFR-001 specifies a shell verification command rather than a binary PASS/FAIL criterion. |
| Traceability | 0.75 | 0.75 — One indirect coverage gap | REQ-RBA-001~006 all have corresponding ACs. NFR-001~006 mostly covered. NFR-003 covered only indirectly. All ACs reference valid REQ/NFR identifiers. |

---

## Chain-of-Verification Pass

Second-look findings after re-reading each section:

1. **REQ sequence re-verified end-to-end**: REQ-RBA-001, 002, 003, 004, 005, 006 — confirmed sequential, no gaps, consistent prefix. NFR-001~006 also sequential. No MP-1 violation confirmed.

2. **EARS compliance re-checked for every REQ entry**: REQ-RBA-002 (State-driven, L104) uses "WHILE ... THE 시스템 SHALL" correctly without "THEN" — this one REQ is conforming. REQ-RBA-003 (L107) and REQ-RBA-006 (L119) use Ubiquitous pattern "THE 시스템 SHALL" correctly. REQ-RBA-001, 004, 005 confirmed as violations.

3. **Exclusions specificity checked**: spec.md:L83-93 ("2.2 제외") contains 8 specific exclusion entries (자동 매매, 현금 잔고, AI 재호출, 세금 정밀, 분수 주식, 이력 대시보드, 실시간 스트리밍, 다중 통화). Each is specific and actionable. No vagueness.

4. **Contradiction scan**: No contradiction found between requirements. NFR-005 specifies 404 (not 403) and provides rationale ("코드베이스 관례"). Exclusion of automatic trading is consistent with REQ-RBA-005 (dry-run/save only). No internal conflicts detected.

5. **Additional defect from second pass**: acceptance.md:L32-33 (AC-RBA-005) hardcodes the table name `rebalancing_plans` in the acceptance criterion ("THEN `rebalancing_plans` 테이블에 행이 추가되지 않아야 한다"). This is a minor implementation detail in a normative AC but does not change the FAIL verdict. Noted for completeness; not added to formal defect count.

---

## Recommendations

### Fix D1 (Critical — NFR-001):
Replace:
> "THE 시스템 SHALL 본 SPEC 신규 코드에서 `scipy`를 import하지 않는다. 수치 계산은 `numpy` + `math`만 사용한다"

With:
> "THE 시스템 SHALL 본 SPEC 신규 수치 계산 코드를 표준 라이브러리 및 프로젝트 승인 라이브러리만으로 구현하며, 새로운 외부 최적화 라이브러리를 도입하지 않는다."

Technical rationale (scipy prohibition) should move to the Technical Approach section (Section 5) as a design decision note.

### Fix D2 (Critical — NFR-002):
Replace:
> "THE `calculate_rebalancing_orders` 순수 함수 SHALL DB·Redis·외부 API 의존 없이..."

With:
> "THE 시스템의 핵심 리밸런싱 계산 컴포넌트 SHALL DB·외부 캐시·외부 API에 대한 의존 없이, 입력값(보유 현황·가격·목표 비중·예산·수수료율)만으로 결정적 결과를 반환하여 단위 테스트가 가능해야 한다."

### Fix D3 (Critical — NFR-005):
Replace:
> "소유권 위반 시 `404 Not Found`로 응답한다(코드베이스 관례, 403 아님)"

With:
> "THE 시스템 SHALL 요청 사용자가 해당 포트폴리오의 소유자가 아닌 경우, 포트폴리오가 존재하지 않는 경우와 동일한 오류 응답을 반환하여 소유권 정보를 노출하지 않는다."

HTTP status code detail should move to the Technical Approach section as a design convention note.

### Fix D4 (Critical — AC-NFR-001):
Replace:
> "AC-NFR-001: `portfolio/rebalancing.py`는 `scipy`를 import하지 않는다(`grep -r "import scipy"` 결과 없음)."

With:
> "THE 시스템 SHALL 리밸런싱 계산 모듈 내에서 프로젝트 승인 외 외부 최적화 라이브러리를 사용하지 않는다."

### Fix D5, D6 (Major — REQ-RBA-001, REQ-RBA-004):
Remove "THEN" before "THE 시스템 SHALL" to conform to EARS Event-driven pattern:

> "WHEN 사용자가 포트폴리오에 대해 리밸런싱 주문 계산을 요청하면 THE 시스템 SHALL 현재 비중을 목표 비중으로 이동시키는 매수/매도 수량을 1주 단위 정수로 계산하되, 주어진 예산 한도 내에서 산출한다."

### Fix D7 (Major — REQ-RBA-005):
Split into two separate requirements:

> **REQ-RBA-005a** (Event-driven): WHEN 사용자가 `dry_run=true`(기본)로 주문을 미리보기 요청하면 THE 시스템 SHALL DB에 기록하지 않고 계획서를 반환한다.

> **REQ-RBA-005b** (Event-driven): WHEN 사용자가 `dry_run=false`로 주문 계획을 확정하면 THE 시스템 SHALL 주문 계획서를 영속 저장소에 저장하고 저장된 계획서를 반환한다.

Note: REQ-RBA-006 would need renumbering if REQ-RBA-005 is split.

### Fix D8 (Major — AC-RBA-001):
Replace assertion form with EARS:

> "WHEN 리밸런싱 주문 계산 요청이 완료되면 THE 시스템 SHALL 각 종목의 주문 수량을 1주 단위 정수로 반환한다."
> "WHEN 매수 조정 금액을 현재가로 나눈 값이 소수이면 THE 시스템 SHALL 매수 수량을 내림(floor) 처리하여 정수로 반환한다."

### Fix D9 (Major — AC-RBA-002):
Replace:

> "WHILE 매수 주문을 산출하는 동안 THE 시스템 SHALL 모든 매수 주문 금액 합계가 지정된 예산을 초과하지 않도록 보장한다."

### Fix D10 (Minor — AC-NFR-003 gap):
Add a dedicated entry in the AC-NFR section:

> "AC-NFR-003: WHEN 종목 market 속성이 국내(KRX)이면 THE 시스템 SHALL 국내 수수료율을 적용하고, 해외(NYSE/NASDAQ)이면 THE 시스템 SHALL 해외 수수료율을 적용한다."

### Fix D11 (Minor — AC-RBA-004 variable name):
Replace:

> "WHEN 예산이 모든 매수를 충족하기에 부족하면 THEN 조정 금액(delta_value)이 큰 언더웨이트 종목부터..."

With:

> "WHEN 예산이 모든 매수를 충족하기에 부족하면 THE 시스템 SHALL 비중 조정 필요량이 큰 언더웨이트 종목부터 우선하여 예산을 배분한다."
