# SPEC Review Report: SPEC-STOCK-035
Iteration: 1/3
Verdict: FAIL
Overall Score: 0.21

---

## Must-Pass Results

- [PASS] MP-1 REQ number consistency: Two internally sequential series — REQ-RPT-001 through REQ-RPT-005 (spec.md:L100–L118) and REQ-RPT-NFR-001 through REQ-RPT-NFR-005 (spec.md:L124–L128). Each series is sequential with no gaps, no duplicates, and consistent zero-padding (001, 002, 003, 004, 005). The dual-series design is documented at spec.md:L23–L25.
- [FAIL] MP-2 EARS format compliance: Seven AC bullets in acceptance.md §1 use artifact/component as grammatical subject rather than "THE 시스템 SHALL." The project-specific audit rule states requirements MUST follow EARS patterns with "THE SYSTEM SHALL." Clear violations: acceptance.md:L13 ("THE CSV의 각 행 SHALL"), L14 ("THE 응답 SHALL"), L19 ("THE 문서 SHALL"), L20 ("WHERE...THE 문서 SHALL"), L21 ("WHERE...THE 문서 SHALL"), L26 ("THE 응답의 기간 식별자 SHALL"), L31 ("THE 저장된 스냅샷 SHALL"). Three additional borderline violations: L40 ("THE 시스템의 신규 수치 보조 계산 SHALL"), L44 ("THE 시스템의 CSV 직렬화 SHALL"), L48 ("THE 손익행 생성·CSV 직렬화 컴포넌트 SHALL").
- [PASS] MP-3 YAML frontmatter validity: All six required fields present — id: "SPEC-STOCK-035" (string, spec.md:L2), version: "0.1.0" (string, L3), status: "draft" (string, L4), created_at: "2026-06-24" (ISO date, L5), priority: "medium" (string, L8), labels: array of 6 strings (L10). No type mismatches.
- [N/A] MP-4 Section 22 language neutrality: N/A — This is a single-project application SPEC (FastAPI + React portfolio reporting), not a multi-language tooling SPEC.

---

## Category Scores (0.0–1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 | spec.md §3 normative requirements (L100–L128) are unambiguous. Non-system EARS subjects in acceptance.md create minor ambiguity: a tester reading "THE CSV의 각 행 SHALL" (acceptance.md:L13) must infer that "the system SHALL produce a CSV where each row contains..." — reasonable engineers would resolve this consistently, but it introduces one interpretive step. |
| Completeness | 1.0 | 1.0 | All required sections present: HISTORY (spec.md:L17–L21), WHY/Motivation (L42–L48), WHAT/Scope (L29–L57), REQUIREMENTS §3 (L98–L128), ACCEPTANCE CRITERIA (acceptance.md), Exclusions §2.2 (spec.md:L83–L94) with 8 specific entries. YAML frontmatter complete. All 10 REQs have corresponding ACs. All ACs trace to valid REQs. |
| Testability | 0.75 | 0.75 | Most ACs are binary testable. acceptance.md:L56 "5초 이내에 완료" is measurable. acceptance.md:L40 "신규 외부 통계·최적화 라이브러리를 도입하지 않는다" is verifiable via import analysis. acceptance.md:L48 "결정적 결과를 반환한다" requires knowing test inputs/outputs but is still testable. No weasel words ("appropriate", "adequate", "reasonable") found. Non-system subjects (D1–D7) require minor inference — one AC bullet whose subject is "THE 문서 SHALL" is testable but less precisely specified than "THE 시스템 SHALL 응답 문서에 포함한다." |
| Traceability | 1.0 | 1.0 | Perfect bidirectional traceability. REQ-RPT-001→AC-RPT-001, REQ-RPT-002→AC-RPT-002, REQ-RPT-003→AC-RPT-003, REQ-RPT-004→AC-RPT-004, REQ-RPT-005→AC-RPT-005, REQ-RPT-NFR-001→AC-RPT-NFR-001, REQ-RPT-NFR-002→AC-RPT-NFR-002, REQ-RPT-NFR-003→AC-RPT-NFR-003, REQ-RPT-NFR-004→AC-RPT-NFR-004, REQ-RPT-NFR-005→AC-RPT-NFR-005. No orphaned ACs. No uncovered REQs. |

---

## Defects Found

**Score calculation**: Start 1.0 — D1–D7 (7 major × −0.10) = −0.70 — D8–D10 (3 minor × −0.03) = −0.09 → 0.21

D1. acceptance.md:L13 — "THE CSV의 각 행 SHALL 종목 코드·종목명·수량·평균 단가·현재가·평가 손익 금액·수익률·비중을 순서대로 포함한다." The grammatical subject is "CSV의 각 행" (each row of the CSV), not "THE 시스템". The EARS Ubiquitous pattern requires "The [system] shall [response]." — Severity: major

D2. acceptance.md:L14 — "THE 응답 SHALL 첨부 파일로 다운로드되도록 지시하는 헤더를 포함한다." Subject is "응답" (response/artifact), not "THE 시스템". — Severity: major

D3. acceptance.md:L19 — "THE 문서 SHALL 보유 종목 상세 목록을 포함한다." Subject is "문서" (document/artifact). — Severity: major

D4. acceptance.md:L20 — "WHERE 배당 데이터가 가용하면 THE 문서 SHALL 배당 요약을 포함한다." Uses the Optional EARS trigger (WHERE) correctly but the response subject is "THE 문서" not "THE 시스템". EARS Optional: "Where [feature exists], the [system] shall [response]." — Severity: major

D5. acceptance.md:L21 — "WHERE 벤치마크가 지정되면 THE 문서 SHALL 벤치마크 비교를 포함한다." Same issue as D4. — Severity: major

D6. acceptance.md:L26 — "THE 응답의 기간 식별자 SHALL 표준 기간 코드가 아닌 커스텀 범위를 나타낸다." Subject is "응답의 기간 식별자" (response's period identifier), an artifact attribute. — Severity: major

D7. acceptance.md:L31 — "THE 저장된 스냅샷 SHALL 요청된 월 식별자를 포함한다." Subject is "저장된 스냅샷" (stored snapshot/artifact). — Severity: major

D8. acceptance.md:L40 — "THE 시스템의 신규 수치 보조 계산 SHALL 표준 수학 연산 및 프로젝트 승인 수치 라이브러리만 사용하며 신규 외부 통계·최적화 라이브러리를 도입하지 않는다." The grammatical subject is "신규 수치 보조 계산" (new numeric auxiliary calculations) — the system appears only as a possessive modifier. — Severity: minor

D9. acceptance.md:L44 — "THE 시스템의 CSV 직렬화 SHALL 언어 표준 라이브러리만 사용하며 외부 CSV 처리 라이브러리를 도입하지 않는다." Grammatical subject is "CSV 직렬화" (CSV serialization), not "the system." — Severity: minor

D10. acceptance.md:L48 — "THE 손익행 생성·CSV 직렬화 컴포넌트 SHALL 데이터베이스·외부 캐시·외부 네트워크 의존 없이 입력값만으로 결정적 결과를 반환한다." Subject is a named component, no system reference at all. — Severity: minor

---

## Chain-of-Verification Pass

Re-read pass findings:

1. **REQ sequencing end-to-end**: Re-verified manually — REQ-RPT-001, 002, 003, 004, 005 in sequence (spec.md:L100, L104, L108, L112, L116); REQ-RPT-NFR-001, 002, 003, 004, 005 (L124, L125, L126, L127, L128). No gaps detected.

2. **Traceability full coverage**: Re-verified every REQ↔AC pairing. All 10 REQs covered; all 10 AC groups trace to existing REQs. Confirmed bidirectional.

3. **Exclusions specificity**: §2.2 (spec.md:L83–L94) contains 8 clearly scoped exclusions — PDF/Excel/HTML, scheduled reports, auto monthly snapshot cron, chart rendering, multi-portfolio aggregation, trend analysis, and price inference. Each includes brief rationale. Not vague.

4. **Contradiction check between requirements**: No contradictions found. REQ-RPT-NFR-001 (no external stats libraries) and REQ-RPT-NFR-002 (CSV standard library only) are complementary, not contradictory. REQ-RPT-004 (snapshot persistence) is consistent with §2.2 exclusion of auto cron loading.

5. **Normative text implementation details**: Re-read spec.md §3 (L98–L128) — confirmed no function names (`generate_holding_report_rows`, `generate_csv_content`), no library names (`io`, `csv`, `numpy`), no HTTP status codes, no SQL column names, and no math formulas in backticks appear in normative SHALL text. These implementation details exist only in §5 Technical Approach and §7 Dependencies, which are informative sections.

6. **EARS violations recount**: Confirmed 7 clear major violations (D1–D7) and 3 borderline minor violations (D8–D10). No new violations discovered beyond those listed.

Second-pass new finding: None — first pass was thorough. Sections re-verified: YAML frontmatter, §3 Requirements, acceptance.md §1 (all 17 AC bullets), traceability map, exclusions.

---

## Recommendation

The SPEC fails MP-2 (EARS format compliance). The normative requirements in spec.md §3 are well-formed and compliant. All defects are concentrated in acceptance.md §1 where AC sub-bullets describe output artifact properties rather than system behaviors.

**Actionable fixes for manager-spec (ordered by priority):**

**Fix 1 — D1 (acceptance.md:L13):** Replace artifact subject with system subject.
- Current: "THE CSV의 각 행 SHALL 종목 코드·종목명·수량·평균 단가·현재가·평가 손익 금액·수익률·비중을 순서대로 포함한다."
- Corrected: "THE 시스템 SHALL CSV의 각 데이터 행에 종목 코드·종목명·수량·평균 단가·현재가·평가 손익 금액·수익률·비중을 순서대로 포함한다."

**Fix 2 — D2 (acceptance.md:L14):** Replace artifact subject.
- Current: "THE 응답 SHALL 첨부 파일로 다운로드되도록 지시하는 헤더를 포함한다."
- Corrected: "THE 시스템 SHALL 응답에 첨부 파일 다운로드를 지시하는 헤더를 포함한다."

**Fix 3 — D3 (acceptance.md:L19):** Replace artifact subject.
- Current: "THE 문서 SHALL 보유 종목 상세 목록을 포함한다."
- Corrected: "THE 시스템 SHALL 반환 문서에 보유 종목 상세 목록을 포함한다."

**Fix 4 — D4 (acceptance.md:L20):** Preserve Optional EARS trigger; fix subject.
- Current: "WHERE 배당 데이터가 가용하면 THE 문서 SHALL 배당 요약을 포함한다."
- Corrected: "WHERE 배당 데이터가 가용하면 THE 시스템 SHALL 반환 문서에 배당 요약을 포함한다."

**Fix 5 — D5 (acceptance.md:L21):** Same pattern as Fix 4.
- Current: "WHERE 벤치마크가 지정되면 THE 문서 SHALL 벤치마크 비교를 포함한다."
- Corrected: "WHERE 벤치마크가 지정되면 THE 시스템 SHALL 반환 문서에 벤치마크 비교를 포함한다."

**Fix 6 — D6 (acceptance.md:L26):** Replace artifact attribute subject.
- Current: "THE 응답의 기간 식별자 SHALL 표준 기간 코드가 아닌 커스텀 범위를 나타낸다."
- Corrected: "THE 시스템 SHALL 응답의 기간 식별자를 표준 기간 코드가 아닌 커스텀 범위 형식으로 반환한다."

**Fix 7 — D7 (acceptance.md:L31):** Replace artifact subject.
- Current: "THE 저장된 스냅샷 SHALL 요청된 월 식별자를 포함한다."
- Corrected: "THE 시스템 SHALL 저장된 스냅샷에 요청된 월 식별자를 포함하여 반환한다."

**Fix 8 — D8 (acceptance.md:L40):** Make system the grammatical subject.
- Current: "THE 시스템의 신규 수치 보조 계산 SHALL 표준 수학 연산 및 프로젝트 승인 수치 라이브러리만 사용하며 신규 외부 통계·최적화 라이브러리를 도입하지 않는다."
- Corrected: "THE 시스템 SHALL 신규 수치 보조 계산을 표준 수학 연산 및 프로젝트 승인 수치 라이브러리만으로 구현하며 신규 외부 통계·최적화 라이브러리를 도입하지 않는다."

**Fix 9 — D9 (acceptance.md:L44):** Same pattern as Fix 8.
- Current: "THE 시스템의 CSV 직렬화 SHALL 언어 표준 라이브러리만 사용하며 외부 CSV 처리 라이브러리를 도입하지 않는다."
- Corrected: "THE 시스템 SHALL CSV 직렬화를 언어 표준 라이브러리만으로 수행하며 외부 CSV 처리 라이브러리를 도입하지 않는다."

**Fix 10 — D10 (acceptance.md:L48):** Add system subject.
- Current: "THE 손익행 생성·CSV 직렬화 컴포넌트 SHALL 데이터베이스·외부 캐시·외부 네트워크 의존 없이 입력값만으로 결정적 결과를 반환한다."
- Corrected: "THE 시스템 SHALL 손익행 생성 및 CSV 직렬화를 데이터베이스·외부 캐시·외부 네트워크 의존 없이 입력값만으로 결정적 결과를 반환하도록 구현한다."

Note: spec.md §3 (normative requirements) and §2.2 (exclusions) require no changes — they are correctly formed. Only acceptance.md §1 requires revision.
