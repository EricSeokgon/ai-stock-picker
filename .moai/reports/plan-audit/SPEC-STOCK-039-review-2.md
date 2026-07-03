# SPEC Review Report: SPEC-STOCK-039
Iteration: 2/3
Verdict: FAIL
Overall Score: 0.75

## Must-Pass Results

- [PASS] MP-1 YAML Frontmatter: 9개 필수 필드 모두 존재. `id: SPEC-STOCK-039` (L2), `version: 0.2.0` (L3), `status: draft` (L4), `created_at: 2026-06-25` (L5), `updated_at: 2026-06-25` (L6), `author: ircp` (L7), `priority: medium` (L8), `issue_number: null` (L9), `labels: [portfolio, polling, market-status, frontend, backend]` (L10) — 모두 정상. v0.1.0에서 지적된 D1/D2/D3 전부 해결.
- [PASS] MP-2 EARS Format: AC-001~AC-004(Ubiquitous), AC-010(Event-Driven), AC-011/012/015(Ubiquitous), AC-013/014(Event-Driven), AC-020(State-Driven), AC-021(Event-Driven), AC-030/031(State-Driven), AC-032/040(Event-Driven), AC-050/060(Unwanted) — 전 17개 AC가 EARS 단일 문장 형식을 준수. BDD 시나리오는 별도 섹션에 분리되어 공식 AC로 표기되지 않음.
- [PASS] MP-3 AC Subject: 전 AC가 "THE 시스템 SHALL" 주어를 사용. 컴포넌트·버튼·페이지를 주어로 쓴 AC 없음.
- [PASS] MP-4 EARS Pattern Rules: WHEN 패턴(AC-010, AC-013, AC-014, AC-021, AC-032, AC-040)에 THEN 없음. IF 패턴(AC-050, AC-060)에 THEN 있음. WHILE 패턴(AC-020, AC-030, AC-031)에 THEN 없음. 모두 정합.
- [PASS] MP-5 REQ Text Forbidden Terms: v0.1.0의 "scipy" 제거 확인. REQ-POLL-NFR-005(L80): "외부 과학 계산 라이브러리"는 카테고리 기술이지 특정 라이브러리명이 아님. 전 REQ에 함수명·HTTP 상태 코드·SQL·라이브러리명 없음.
- [PASS] MP-6 REQ Prefix: REQ-POLL-001~004, REQ-POLL-010~015, REQ-POLL-020~022, REQ-POLL-030~032, REQ-POLL-040, REQ-POLL-050, REQ-POLL-060~061, REQ-POLL-NFR-001~005 — 전체 22개 REQ가 "REQ-POLL-*" 또는 "REQ-POLL-NFR-*" 접두사를 사용. v0.1.0의 "NFR-" 접두사 문제 해결.
- [FAIL] MP-7 AC Coverage: REQ-POLL-NFR-001(spec.md:L76), REQ-POLL-NFR-002(spec.md:L77), REQ-POLL-NFR-005(spec.md:L80)에 대응하는 공식 AC가 없음. acceptance.md의 DoD 체크리스트(L109: "WebSocket·scipy 미사용")가 언급하지만 DoD 항목은 EARS AC와 동일하지 않음. 3개 REQ-POLL-NFR-* 항목이 AC 미보유 상태로 잔존.

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 band | REQ 대부분 단일 해석 가능. REQ-POLL-022(L53)의 "시작하기 직전이면" 트리거 타이밍이 미정의(minor). 용어 섹션(L26-28)이 핵심 용어를 명확히 정의. |
| Completeness | 0.90 | 0.75-1.0 band | YAML 9개 필드 전부 수정 완료. 모든 구조적 섹션(HISTORY·개요·요구사항·수용기준·Exclusions) 존재. AC-015 신규 추가로 REQ-POLL-015 커버리지 충족. NFR-001/002/005 AC 미보유 상태가 유일 잔존 결함. |
| Testability | 0.75 | 0.75 band | 대부분 AC가 이진 판정 가능. AC-021(acceptance.md:L29)의 "먼저 확인한다" 검증이 블랙박스 관점에서 어려움(minor). 나머지 모두 명확하게 PASS/FAIL 판정 가능. |
| Traceability | 0.75 | 0.75 band | REQ-POLL-015 → AC-015 연결 신규 완료. REQ-POLL-060 → AC-060(소유권 불일치 케이스만 커버; 인증 실패 케이스 AC 미보유). REQ-POLL-NFR-001/002/005 → AC 없음. 3개 NFR이 uncovered 상태. |

## Defects Found

D1. spec.md:L76 — REQ-POLL-NFR-001에 대응하는 AC 없음. "소켓 기반 통신 없이 구현한다"를 검증하는 EARS AC가 acceptance.md에 존재하지 않음. DoD L109의 "WebSocket 미사용" 언급은 공식 AC가 아님. — Severity: major (MP-7 FAIL)

D2. spec.md:L77 — REQ-POLL-NFR-002에 대응하는 AC 없음. "네트워크·데이터베이스 의존 없이 단독 검증 가능"을 확인하는 AC가 없음. — Severity: major (MP-7 FAIL)

D3. spec.md:L80 — REQ-POLL-NFR-005에 대응하는 AC 없음. "표준 라이브러리만 사용"을 검증하는 AC가 없음. DoD L109의 언급은 공식 AC가 아님. — Severity: major (MP-7 FAIL)

D4. acceptance.md:L43 — REQ-POLL-060(L71)의 인증 보호 측면에 대응 AC 없음. AC-060은 소유권 불일치만 커버하고, 미인증 사용자의 갱신 요청에 대한 401 응답 시나리오 AC 없음. (Iteration 1 D9, 미해결) — Severity: minor

D5. spec.md:L53 — REQ-POLL-022의 "시작하기 직전이면" 트리거 타이밍이 구체적 정의 없음(폴링 타이머 콜백 진입 시점 등 명시 필요). (Iteration 1 D8, 미해결) — Severity: minor

## Chain-of-Verification Pass

두 번째 자체 검토에서 확인한 사항:

**새로운 발견:**
1. AC-010(acceptance.md:L16)이 "WHEN 자동 갱신이 시작되고 시장이 개장 상태이면"으로 WHEN 패턴에 복합 조건(이벤트+상태)을 혼용함. 엄격한 EARS에서는 이벤트(WHEN)와 상태(WHILE)를 분리해야 하나, 이 항목은 THEN 키워드가 없으므로 MP-4 패턴 규칙을 위반하지 않음. AC 하나에서 시작 이벤트와 개장 상태를 동시에 기술한 것이며, 기능적으로 REQ-POLL-010과 REQ-POLL-020 양쪽을 커버함. Minor 관찰로 기록하되 MP-2/MP-4 판정에 영향 없음.

2. REQ-POLL-020(spec.md:L51)의 "WHILE 시장 개장 중, SHALL 폴링 수행"에 직접 대응하는 WHILE 패턴 AC가 없음. AC-010(WHEN 시작 시)이 부분적으로 커버하나 WHILE 상태로서의 지속적 폴링 보증 AC가 별도로 없음. 그러나 기능적 동작은 AC-010과 AC-020의 역-조건에서 충분히 추론 가능하므로 critical 결함은 아님.

3. 전체 REQ 번호 확인: REQ-POLL-001~004, 010~015, 020~022, 030~032, 040, 050, 060~061, REQ-POLL-NFR-001~005 — 22개 전체 재확인 완료. 의도적 카테고리 기반 십진 그룹핑으로 갭이 존재하나 이는 동일 SPEC 내 일관된 패턴이며 YAML 관련 MP-1 위반이 아님.

4. AC-015 신규 문구 재확인: "THE 시스템 SHALL 현재가 갱신 시 신규 데이터 수집 없이 기존 성과 조회 경로의 재호출로만 처리한다." — Ubiquitous 패턴 정상, REQ-POLL-015의 제약을 충분히 커버함. 단, "만"이라는 부사어가 단독 검증 가능성을 높이는 긍정적 요소.

**확인 완료(변경 없음):**
- 전 17개 AC 주어 "THE 시스템 SHALL" 재확인 → MP-3 PASS 유지
- WHEN/WHILE/IF-THEN 패턴 전체 재확인 → MP-4 PASS 유지
- NFR 접두사 REQ-POLL-NFR-* 전체 재확인 → MP-6 PASS 유지

## Regression Check (Iteration 2)

Defects from iteration 1:

- D1 (spec.md:L5 created → created_at): [RESOLVED] — spec.md:L5에서 `created_at: 2026-06-25` 확인.
- D2 (spec.md:L6 updated → updated_at): [RESOLVED] — spec.md:L6에서 `updated_at: 2026-06-25` 확인.
- D3 (labels 필드 누락): [RESOLVED] — spec.md:L10에서 `labels: [portfolio, polling, market-status, frontend, backend]` 확인.
- D4 (NFR-005 "scipy" 포함): [RESOLVED] — spec.md:L80에서 "외부 과학 계산 라이브러리"로 대체, "scipy" 제거 확인.
- D5 (NFR-001~005 접두사 "NFR-"): [RESOLVED] — spec.md:L76-80에서 REQ-POLL-NFR-001~005로 전면 개명 확인.
- D6 (REQ-POLL-015 AC 없음): [RESOLVED] — acceptance.md:L24에서 AC-015 추가 확인.
- D7 (NFR-001/002/005 AC 없음): [UNRESOLVED] — REQ-POLL-NFR-001, REQ-POLL-NFR-002, REQ-POLL-NFR-005에 대응 AC 여전히 없음. MP-7 FAIL 지속.
- D8 (REQ-POLL-022 타이밍 모호): [UNRESOLVED] — minor, spec.md:L53 변경 없음.
- D9 (REQ-POLL-060 인증 AC 없음): [UNRESOLVED] — minor, acceptance.md 미수정.

## Recommendation

**FAIL — 다음 1가지 수정 후 재심사 필요:**

1. **REQ-POLL-NFR-001/002/005 AC 추가** (MP-7): acceptance.md에 다음 3개 AC를 추가. 부정적 아키텍처 제약은 Unwanted IF-THEN 패턴으로 표현할 수 있음:

   **NFR-001 대응 AC:**
   ```
   - **AC-NFR-001**: THE 시스템 SHALL 자동 갱신을 위해 영구적 소켓 연결을 사용하지 않고 단방향 주기 요청 방식으로만 가격을 조회한다.
   ```
   또는 Ubiquitous:
   ```
   - **AC-NFR-001**: THE 시스템 SHALL 자동 갱신 구현이 REST 폴링 방식으로 동작함을 단위 테스트로 검증 가능하도록 한다.
   ```

   **NFR-002 대응 AC:**
   ```
   - **AC-NFR-002**: THE 시스템 SHALL 장중 판정 함수를 네트워크·데이터베이스 의존 없이 호출하여 결과를 반환하도록 한다.
   ```

   **NFR-005 대응 AC:**
   ```
   - **AC-NFR-005**: THE 시스템 SHALL 시간 계산을 표준 라이브러리만으로 수행하여 외부 패키지 없이 테스트 가능하도록 한다.
   ```

   단, 이 세 NFR은 부정적 아키텍처 제약이므로 DoD 항목을 공식 Ubiquitous AC로 격상시키는 방식도 동등하게 허용 가능.

**선택 권고 수정사항 (비필수):**

2. REQ-POLL-060 인증 보호 AC 추가 (D4/iteration-1 D9): "IF 미인증 사용자가 포트폴리오 현재가 갱신을 요청하면, THEN THE 시스템 SHALL 인증 오류로 응답한다" 형식 AC 신설.

3. REQ-POLL-022의 "시작하기 직전이면"(spec.md:L53) → "폴링 타이머가 만료되어 재조회를 시작하기 직전이면"으로 트리거 타이밍 명확화 (D5).
