# SPEC Review Report: SPEC-STOCK-031
Iteration: 1/3
Verdict: FAIL
Overall Score: 0.67

---

## Must-Pass Results

- [PASS] MP-1 REQ Number Consistency: REQ-PAL-001 through REQ-PAL-008, sequential, no gaps, consistent 3-digit zero-padding, prefix PAL used consistently. Evidence: spec.md:L92, L97, L100, L104, L108, L112, L116, L120.

- [FAIL] MP-2 EARS Format Compliance: All 11 acceptance criteria in acceptance.md §1 (L13-26) are descriptive test assertion statements, not EARS-pattern statements. None use "The [system] shall", "When [trigger], the [system] shall", "While [condition], the [system] shall", or any other EARS pattern. The section is labeled "EARS 인수 조건" but the content does not conform. For example, acceptance.md:L15 states "`POST`·`GET`·`PUT`·`DELETE /portfolios/{id}/alerts` 엔드포인트가 존재하며 인증된 소유자에게 동작한다" — this is a declarative test assertion, not an EARS-format requirement. acceptance.md:L16 states "활성 `portfolio_target_return` 알림에서 YTD 총수익률이 `condition_value` 이상이면 알림이 1회 발화하고 `is_triggered=true`로 갱신된다" — again a descriptive assertion, not EARS. No AC in §1 includes "the system shall" formulation. Note: the REQUIREMENTS in spec.md §3 ARE properly formatted in EARS style — this failure is specific to the acceptance criteria in acceptance.md §1.

- [PASS] MP-3 YAML Frontmatter Validity: All required fields present with correct types. id="SPEC-STOCK-031" (string), version="0.1.0" (string), status="draft" (string), created_at="2026-06-23" (ISO date string), priority="high" (string), labels=["portfolio","alerts","notifications","backend","frontend"] (array). Evidence: spec.md:L1-11.

- [N/A] MP-4 Section 22 Language Neutrality: SPEC is scoped to a single-project stack (Python+FastAPI backend, React+TypeScript frontend). No multi-language LSP tooling is referenced. Auto-passes.

---

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 — Minor-to-moderate ambiguity in some requirements from HOW details | spec.md:L106 (function names in REQ-PAL-004), L113 (function/constant names in REQ-PAL-006), L121-122 (DB constraint details in REQ-PAL-008). Core business logic is clear (total_return >= threshold, MDD <= threshold). |
| Completeness | 0.75 | 0.75 — One non-critical structural issue; frontmatter complete | All required sections present across spec.md and acceptance.md. No standalone ACCEPTANCE CRITERIA section in spec.md itself (ACs in separate file). HISTORY (L17-21), WHY (L40-44), WHAT (L29-58), REQUIREMENTS (L90-123), Exclusions (L75-87) all present. |
| Testability | 0.75 | 0.75 — Mostly binary-testable; one or two minor interpretation issues | acceptance.md:L22 allows "409 또는 400" creating ambiguous expected behavior in tests. acceptance.md:L19 "best-effort" qualified by testable assertion "(발송 실패가 인박스 적재를 차단하지 않음)". NFR-002, NFR-003 are measurable. |
| Traceability | 1.0 | 1.0 — Complete bidirectional traceability | All 8 REQs (REQ-PAL-001 through REQ-PAL-008) have corresponding ACs in acceptance.md:L13-22. All AC-referenced REQ IDs exist in spec.md §3. NFR-001/002/003 in acceptance.md map to spec.md §4. No orphaned ACs. No uncovered REQs. |

---

## Defects Found

D1. spec.md:L106 — REQ-PAL-004 names specific function implementations in normative requirement text: "`_run_general_alert_check`", "`check_and_trigger_all_alerts`", "`check_all_portfolio_alerts`". Requirements must specify WHAT behavior is required ("the system shall check portfolio alerts as part of the existing periodic alert evaluation job"), not name the specific functions implementing that behavior (HOW). — Severity: major

D2. spec.md:L113 — REQ-PAL-006 names specific code artifacts in normative requirement text: function `is_channel_enabled_async()` and constant `SUPPORTED_ALERT_TYPES`. A requirement should state the behavior ("the system shall respect per-channel notification preferences") without naming the specific function or constant implementing the gate. — Severity: major

D3. spec.md:L121-122 — REQ-PAL-008 embeds DB-level implementation details in normative requirement text: "`(user_id, portfolio_id, alert_type)` UNIQUE 제약", "`notifications` UNIQUE 제약(`user_id, type, krx_code, ref_date`)", and "`krx_code` 필드에 포트폴리오 식별자(`PORT_{portfolio_id}`)" with specific field naming conventions. These are implementation decisions belonging in §5 Technical Approach, not in a normative requirement. The requirement should state the uniqueness constraint behavior and idempotency guarantee without specifying the specific columns, constraint names, or value encoding scheme. — Severity: major

D4. acceptance.md:L13-26 (§1 EARS 인수 조건 전체) — All 11 acceptance criteria do not conform to EARS format. The section is labeled "EARS 인수 조건" but contains descriptive test assertion statements rather than EARS-structured requirements. None use any of the five EARS patterns. Specific examples:
- L15: "`POST`·`GET`·`PUT`·`DELETE /portfolios/{id}/alerts` 엔드포인트가 존재하며 인증된 소유자에게 동작한다" — should be "When an authenticated owner submits a valid alert creation request, the system shall create a portfolio alert and return HTTP 201."
- L16: "활성 `portfolio_target_return` 알림에서 YTD 총수익률이 `condition_value` 이상이면 알림이 1회 발화하고 `is_triggered=true`로 갱신된다" — should be "When the scheduler evaluates an active portfolio_target_return alert and the YTD total return is greater than or equal to condition_value, the system shall fire the alert exactly once and update is_triggered to true."
This is an MP-2 violation. — Severity: critical

D5. acceptance.md:L22 — REQ-PAL-008 acceptance criterion specifies "`409`(또는 `400`)" as the expected response code, allowing either code. This makes the criterion non-binary-testable: a tester cannot write a deterministic assertion without choosing one specific code. The implementation will commit to one code, making the other alternative dead. The AC should specify a single expected status code. — Severity: minor

D6. spec.md:L98 (REQ-PAL-002) and L102 (REQ-PAL-003) — Both requirements reference "§5.2에 정의한다" (defined in §5.2) within the normative requirement text, deferring a requirement detail (evaluation period) to the Technical Approach section. Requirements should be self-contained; cross-references to implementation sections create dependency on HOW content. The evaluation period (YTD) should be stated directly in the requirement. — Severity: minor

---

## Chain-of-Verification Pass

Re-read performed on all sections. New defects from second pass:

D6 (above) — Requirements REQ-PAL-002 and REQ-PAL-003 cross-reference §5.2 for the evaluation period definition, embedding a forward reference to a Technical Approach section within normative requirement text. First pass did not flag this explicitly.

Verification confirmed (first pass was otherwise thorough):
- REQ sequencing: verified end-to-end, REQ-PAL-001 through REQ-PAL-008, no gaps.
- Traceability: verified each REQ has an AC in acceptance.md §1, all AC REQ references resolve.
- Exclusions: 8 specific exclusion items (L79-86) — verified specific, not vague.
- Contradictions: no contradictions found between requirements. REQ-PAL-004 (no new scheduler job) is consistent with REQ-PAL-002/003 ("when scheduler evaluates"). REQ-PAL-008 (UNIQUE constraint reject) is consistent with §2.2 exclusion (no duplicate alerts per portfolio+type). NFR-004 (graceful degradation) is consistent with REQ-PAL-005 (best-effort delivery).

---

## Recommendation

The SPEC fails primarily on MP-2 (EARS format compliance) and secondarily has major defects from HOW details embedded in normative requirements. The following actionable fixes are required:

**Fix 1 (MP-2 — Critical): Rewrite acceptance.md §1 in EARS format.**

Every AC must use one of the five EARS patterns. Replace the current descriptive assertion table with EARS-structured statements. Examples:

For REQ-PAL-001 (Ubiquitous):
> "The system shall expose POST, GET, PUT, and DELETE endpoints at `/portfolios/{portfolio_id}/alerts`, each requiring authentication and returning 403/404 for unauthorized or non-owned portfolios."

For REQ-PAL-002 (Event-driven):
> "When the scheduler evaluates an active `portfolio_target_return` alert and the portfolio's YTD total return percentage is greater than or equal to condition_value, the system shall fire the alert exactly once and set is_triggered to true."

For REQ-PAL-006 (State-driven):
> "While a user has disabled a specific notification channel for an alert type, the system shall skip delivery to that channel for portfolio alerts of that type."

For REQ-PAL-008 (Unwanted):
> "If a creation request for a (user_id, portfolio_id, alert_type) combination that already exists is received, the system shall reject the request with HTTP 409 Conflict and create no duplicate record."

**Fix 2 (D1 — Major): Remove function names from REQ-PAL-004 (spec.md:L106).**

Replace: "THE 시스템 SHALL 기존 10분 주기 일반 알림 점검 잡(`_run_general_alert_check`)을 확장하여, 종목 알림 점검(`check_and_trigger_all_alerts`)에 더해 포트폴리오 알림 점검(`check_all_portfolio_alerts`)을 함께 호출한다."

With: "THE 시스템 SHALL 기존 10분 주기 알림 점검 잡을 확장하여, 종목 알림 점검과 포트폴리오 알림 점검을 함께 수행한다. 신규 스케줄러 잡 또는 주기는 추가하지 않는다." (Move specific function names to §5.4 Technical Approach where they belong.)

**Fix 3 (D2 — Major): Remove function/constant names from REQ-PAL-006 (spec.md:L113).**

Replace: "THE 시스템 SHALL 해당 alert_type에 대해 `is_channel_enabled_async()` 게이팅 결과에 따라 비활성 채널의 발송을 생략한다. 신규 alert_type(`portfolio_target_return`·`portfolio_mdd_breach`)은 `SUPPORTED_ALERT_TYPES`에 추가되어 설정 게이팅 대상이 된다."

With: "THE 시스템 SHALL 사용자별 채널 활성화 설정에 따라 비활성 채널로의 알림 발송을 생략한다. 신규 alert_type 2종은 기존 알림 설정 게이팅 대상에 포함되어야 한다." (Move `is_channel_enabled_async`, `SUPPORTED_ALERT_TYPES` to §5.7 Technical Approach.)

**Fix 4 (D3 — Major): Move DB implementation details out of REQ-PAL-008 (spec.md:L121-122).**

The first sentence of REQ-PAL-008 (UNIQUE constraint rejection → 409/400) is appropriate for a requirement. The second sentence naming specific columns and value encoding (`notifications UNIQUE 제약(user_id, type, krx_code, ref_date)`, `krx_code 필드에 PORT_{portfolio_id}`) should be moved to §5.3 Technical Approach. Replace the second sentence with: "발화 멱등성은 알림 인박스 테이블의 UNIQUE 제약을 통해 동일 일자 중복 적재를 방지한다."

**Fix 5 (D5 — Minor): Specify a single HTTP status code in REQ-PAL-008 AC.**

Decide between 409 and 400 and remove the "또는" ambiguity. 409 Conflict is semantically correct for UNIQUE constraint violation. Use "409 Conflict" consistently in both the requirement and the acceptance criterion.

**Fix 6 (D6 — Minor): Inline the evaluation period in REQ-PAL-002 and REQ-PAL-003.**

In both requirements, replace "평가 대상 기간은 §5.2에 정의한다" with the actual period: "평가 기준 기간은 YTD(연초 대비, periods[0])로 고정한다."

---

Verdict: FAIL
