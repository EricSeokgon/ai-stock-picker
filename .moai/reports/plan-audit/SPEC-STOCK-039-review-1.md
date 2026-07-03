# SPEC Review Report: SPEC-STOCK-039
Iteration: 1/3
Verdict: FAIL
Overall Score: 0.55

## Must-Pass Results

- [FAIL] MP-1 YAML Frontmatter: `created_at` 필드가 없고 `created`(L5)로 잘못 명명됨. `updated_at` 필드가 없고 `updated`(L6)로 잘못 명명됨. `labels` 필드 자체가 누락됨 (frontmatter 어디에도 없음). 총 3개 위반.
- [PASS] MP-2 EARS Format: 모든 AC(AC-001~AC-060)가 올바른 EARS 단일 문장 형식을 사용함. BDD Given/When/Then 시나리오는 acceptance.md의 별도 섹션에 분리되어 있으며 공식 AC로 표기되지 않음.
- [PASS] MP-3 AC Subject: 모든 AC의 주어가 "THE 시스템 SHALL"임. 폴러·버튼·페이지 등 하위 컴포넌트를 주어로 쓴 AC 없음.
- [PASS] MP-4 EARS Pattern Rules: WHEN 패턴에 THEN 없음(AC-010, AC-013, AC-014, AC-021, AC-032, AC-040). IF 패턴에 THEN 있음(AC-050, AC-060). WHILE 패턴에 THEN 없음(AC-020, AC-030, AC-031).
- [FAIL] MP-5 REQ Text Forbidden Terms: NFR-005(spec.md:L79)에 "scipy"라는 라이브러리 명칭이 포함됨 — "THE 시스템 SHALL 시간 계산에 scipy를 사용하지 않고 표준 라이브러리만 사용한다." 구체적 라이브러리 이름은 REQ 텍스트에 금지됨.
- [FAIL] MP-6 REQ Prefix: NFR-001~NFR-005(spec.md:L75-79)가 "NFR-" 접두사를 사용함. 요구 형식은 "REQ-POLL-NFR-*"임. 5개 NFR 모두 해당.
- [FAIL] MP-7 AC Coverage: REQ-POLL-015(spec.md:L46) — "기존 성과 조회 경로의 재호출로 수행한다" 제약사항에 대응하는 AC가 acceptance.md에 존재하지 않음. 또한 NFR-001(WebSocket 미사용), NFR-002(순수 함수), NFR-005(scipy 미사용)에 대응하는 AC 없음.

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 band | 대부분 REQ가 단일하고 명확한 해석을 가짐. REQ-POLL-022(L52)의 "시작하기 직전이면" 트리거가 얼마나 직전인지 미정의(minor). 용어 섹션(L26-28)이 핵심 용어를 잘 정의함. |
| Completeness | 0.50 | 0.50 band | HISTORY·개요·요구사항·수용기준·Exclusions 섹션 모두 존재. 그러나 YAML frontmatter가 3개 필드 누락/오명명(MP-1 FAIL). 합리적 엔지니어라면 `created_at` vs `created` 파싱 오류를 일으킬 수 있음. |
| Testability | 0.75 | 0.75 band | 대부분 AC가 이진 판정 가능. AC-021(L25 of acceptance.md)의 "먼저 확인한다"는 실행 순서 검증이 블랙박스 테스트로 판정하기 어려움(minor). 나머지 모든 AC는 명확하게 PASS/FAIL 판정 가능. |
| Traceability | 0.50 | 0.50 band | REQ-POLL-015(spec.md:L46)에 대응 AC 없음. NFR-001(L75), NFR-002(L76), NFR-005(L79)에 대응 AC 없음. REQ-POLL-060(L70)은 소유권 위반 케이스만 AC-060으로 커버하고 인증 실패 케이스(양수 인증 요구) AC 없음. 총 4개 이상의 REQ/NFR이 AC 미보유. |

## Defects Found

D1. spec.md:L5 — `created` 필드명이 `created_at`이어야 함. YAML 파싱 도구가 required field 부재로 오류 처리 가능. — Severity: critical (MP-1 FAIL)

D2. spec.md:L6 — `updated` 필드명이 `updated_at`이어야 함. 동일 이유. — Severity: critical (MP-1 FAIL)

D3. spec.md:L1-10 — `labels` 필드 자체가 없음. 필수 프론트매터 필드 누락. — Severity: critical (MP-1 FAIL)

D4. spec.md:L79 — NFR-005가 "scipy"라는 구체적 라이브러리 이름을 포함. "특정 라이브러리 미사용"이 아니라 "시간 계산을 네트워크·DB 의존 없이 수행 가능한 순수 계산으로 구현한다"로 기술해야 함. — Severity: major (MP-5 FAIL)

D5. spec.md:L75-79 — NFR-001~NFR-005 접두사가 "NFR-"이며, 요구 형식인 "REQ-POLL-NFR-001" 등과 불일치. — Severity: major (MP-6 FAIL)

D6. acceptance.md — REQ-POLL-015(spec.md:L46)에 대응하는 AC 없음. REQ-POLL-015는 "기존 성과 조회 경로의 재호출" 방식을 명시한 기능 요구사항이나 이를 검증하는 수용 기준 없음. 예: "WHEN 보유 종목 현재가가 갱신되면, THE 시스템 SHALL 신규 데이터 수집 경로가 아닌 기존 성과 조회 엔드포인트를 통해 가격을 조회한다" 형식의 AC 추가 필요. — Severity: major (MP-7 FAIL)

D7. acceptance.md — NFR-001(WebSocket 미사용), NFR-002(순수 함수), NFR-005 관련 AC 없음. DoD 체크리스트에만 언급되어 있어 공식 수용 기준 없음. — Severity: minor (MP-7 FAIL 보조 근거)

D8. spec.md:L52 — REQ-POLL-022의 "시작하기 직전이면" 트리거가 구체적 타이밍 정의 없음. 폴링 사이클 직전을 어떻게 판정하는지(코드 진입 시점? 타이머 콜백 시점?) 모호함. — Severity: minor (D1 Vague criteria)

D9. acceptance.md:L43 — REQ-POLL-060의 인증 보호 관련 AC 없음. AC-060은 소유권 불일치만 검증하고 미인증 사용자가 가격 갱신 요청할 때의 응답(401 등)을 검증하는 AC가 없음. — Severity: minor (D2 Missing negative test)

## Chain-of-Verification Pass

두 번째 검토에서 발견된 추가 사항:

- NFR-002(spec.md:L76)가 "순수 함수로 구현한다"(HOW 언어)를 포함함. REQ 텍스트는 WHAT/WHY를 기술해야 하나 NFR-002는 구현 방식을 지시함. MP-5 위반 경계선상이지만(특정 라이브러리·함수명은 아님) RQ-4 위반(구현 세부사항 포함)에 해당함.
- REQ-POLL-002(spec.md:L35)의 "(한국 표준시)" 표기 — 이 시스템이 KRX 전용이므로 도메인 용어로 허용 가능하나, "KST" 약어보다 "한국 표준시" 풀네임을 사용한 것은 적절한 선택.
- REQ 번호 간격(001→010→020→030→040→050→060) — 카테고리별 십진 그룹핑이며 의도적 패턴. 표준 plan-auditor의 순번 연속성 검사와 별개로, 이 SPEC 고유 검사(MP-6)에서 접두사 형식만 확인.
- 모든 AC 주어를 재확인: "THE 시스템 SHALL" 17개 AC 전체 확인 완료 — MP-3 PASS 유지.
- acceptance.md의 Given-When-Then BDD 시나리오와 엣지케이스 표는 공식 AC로 레이블되지 않음 — MP-2 PASS 유지.

## Recommendation

**FAIL — 다음 4가지를 수정 후 재심사 필요:**

1. **YAML frontmatter 수정** (MP-1): spec.md:L5를 `created_at: 2026-06-25`로, L6를 `updated_at: 2026-06-25`로 변경. frontmatter에 `labels` 필드 추가 (예: `labels: [polling, realtime, market-status]`).

2. **NFR 접두사 통일** (MP-6): NFR-001~NFR-005를 REQ-POLL-NFR-001~REQ-POLL-NFR-005로 전면 개명. acceptance.md의 DoD 참조도 함께 업데이트.

3. **NFR-005 라이브러리명 제거** (MP-5): spec.md:L79의 "scipy를 사용하지 않고"를 삭제하고, 대신 "THE 시스템 SHALL 시간 계산을 네트워크·데이터베이스 접근 없이 순수 계산만으로 수행할 수 있도록 구현한다(REQ-POLL-NFR-002 참조)"로 기술하거나 NFR-002에 흡수.

4. **REQ-POLL-015 AC 추가** (MP-7): acceptance.md에 다음 AC를 추가:
   ```
   - **AC-015**: WHEN 보유 종목 현재가가 갱신 요청되면, THE 시스템 SHALL 신규 가격 수집 경로를 사용하지 않고 기존 성과 조회 경로를 재호출하여 현재가를 얻는다.
   ```
   또는 DoD 체크 항목을 공식 Ubiquitous AC로 격상:
   ```
   - **AC-015**: THE 시스템 SHALL 현재가 갱신을 위해 신규 데이터 수집 엔드포인트를 호출하지 않는다.
   ```

**선택 권고 수정사항 (비필수):**

5. REQ-POLL-060 인증 보호 AC 추가 (D9): "IF 미인증 사용자가 포트폴리오 현재가 갱신을 요청하면, THEN THE 시스템 SHALL 인증 오류로 응답한다" 형식 AC 신설.

6. NFR-002(spec.md:L76)의 "순수 함수로 구현한다" → "네트워크·데이터베이스 의존 없이 단독으로 검증 가능하도록 구현한다"로 HOW 언어 제거.
