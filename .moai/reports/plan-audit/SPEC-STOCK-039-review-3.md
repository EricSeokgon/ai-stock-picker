# SPEC Review Report: SPEC-STOCK-039
Iteration: 3/3
Verdict: PASS
Overall Score: 0.88

## Must-Pass Results

- [PASS] MP-1 YAML Frontmatter: 9개 필수 필드 모두 존재. `id: SPEC-STOCK-039` (spec.md:L2), `version: 0.2.0` (spec.md:L3), `status: draft` (spec.md:L4), `created_at: 2026-06-25` (spec.md:L5), `updated_at: 2026-06-25` (spec.md:L6), `author: ircp` (spec.md:L7), `priority: medium` (spec.md:L8), `issue_number: null` (spec.md:L9), `labels: [portfolio, polling, market-status, frontend, backend]` (spec.md:L10).
- [PASS] MP-2 EARS Format: 전체 21개 AC(AC-001~004, AC-010~015, AC-020~021, AC-030~032, AC-040, AC-050, AC-060, AC-NFR-001/002/005)가 EARS 단일 문장 형식 준수. BDD 시나리오는 acceptance.md:L55 이하 별도 섹션에 분리되어 공식 AC로 표기되지 않음.
- [PASS] MP-3 AC Subject: 전 21개 AC가 "THE 시스템 SHALL" 주어를 사용. AC-NFR-001(IF-THEN), AC-NFR-002(Ubiquitous), AC-NFR-005(Ubiquitous) 신규 추가 항목 모두 주어 정합. 이질 주어(컴포넌트·버튼·페이지) 없음.
- [PASS] MP-4 EARS Pattern Rules: AC-NFR-001(acceptance.md:L51)이 "IF...THEN THE 시스템 SHALL" 형식으로 IF-THEN 패턴 준수. AC-NFR-002/005(acceptance.md:L52-53)는 Ubiquitous("THE 시스템 SHALL") 패턴으로 THEN 없음. 기존 WHEN/WHILE/IF-THEN 패턴 모두 이전 iteration에서 검증 완료.
- [PASS] MP-5 REQ Text Forbidden Terms: spec.md 전 REQ에 함수명·HTTP 상태 코드·SQL·라이브러리명 없음. REQ-POLL-NFR-005(spec.md:L80)의 "외부 과학 계산 라이브러리"는 카테고리 기술로 특정 라이브러리명 아님. 이전 iteration에서 지적된 "scipy" 제거 유지 확인.
- [PASS] MP-6 REQ Prefix: REQ-POLL-001~004, REQ-POLL-010~015, REQ-POLL-020~022, REQ-POLL-030~032, REQ-POLL-040, REQ-POLL-050, REQ-POLL-060~061, REQ-POLL-NFR-001~005 — 전체 22개 REQ가 "REQ-POLL-*" 또는 "REQ-POLL-NFR-*" 접두사 사용.
- [PASS] MP-7 AC Coverage: v0.3.0에서 AC-NFR-001(acceptance.md:L51), AC-NFR-002(acceptance.md:L52), AC-NFR-005(acceptance.md:L53) 추가로 전체 22개 REQ 커버리지 완성. 세부 매핑: REQ-POLL-NFR-001→AC-NFR-001, REQ-POLL-NFR-002→AC-NFR-002, REQ-POLL-NFR-003→AC-012(60초 기본주기), REQ-POLL-NFR-004→AC-050(in-flight 스킵), REQ-POLL-NFR-005→AC-NFR-005. Iteration 2의 유일 MP-7 FAIL 원인(3개 NFR AC 미보유) 완전 해결.

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 band | 대부분 REQ 단일 해석 가능. REQ-POLL-022(spec.md:L53)의 "시작하기 직전이면" 트리거 타이밍이 여전히 미정의(minor, iteration 1~3 미해결). 용어 섹션(spec.md:L26-28)이 핵심 용어를 명확히 정의하여 주요 개념 모호성 없음. |
| Completeness | 0.95 | 1.0 band 근접 | 모든 구조적 섹션 존재(HISTORY·개요·기능요구사항·비기능요구사항·Exclusions·델타마커·MX태그계획). YAML 9개 필드 완전. AC-NFR-001/002/005 신규 추가로 NFR 전체 커버리지 달성. 잔존 미비점: REQ-POLL-060 인증 실패 시나리오 AC 없음(minor). |
| Testability | 0.80 | 0.75-1.0 band | 신규 AC-NFR-001은 코드 또는 네트워크 트래픽 검사로 이진 판정 가능(WebSocket 부재 확인). AC-NFR-002는 함수 격리 호출로 이진 판정 가능. AC-NFR-005는 의존성 분석으로 이진 판정 가능. AC-021(acceptance.md:L29)의 "먼저 확인한다" 검증은 블랙박스 관점에서 여전히 경계적(minor). |
| Traceability | 0.90 | 0.75-1.0 band | 22개 전 REQ가 ≥1개 AC를 보유. AC-NFR-001/002/005 → REQ-POLL-NFR-001/002/005 역방향 추적 가능. 잔존 부분 커버리지: REQ-POLL-060(spec.md:L71)의 인증 보호 측면이 AC-060으로 소유권 불일치만 커버하고 미인증 요청 거부 케이스 AC 미보유(minor). |

## Defects Found

D1. acceptance.md:L43 — REQ-POLL-060(spec.md:L71)의 인증 보호 측면 AC 부재. AC-060은 소유권 불일치(포트폴리오 미소유)만 커버하고, 미인증 사용자의 현재가 갱신 요청에 대한 인증 오류 응답 시나리오 AC가 없음. (Iteration 1 D9, Iteration 2 D4 — 3회 연속 미해결) — Severity: minor

D2. spec.md:L53 — REQ-POLL-022의 "시작하기 직전이면" 트리거 타이밍 모호. 폴링 타이머 만료 콜백 진입 시점인지, 실제 HTTP 요청 직전인지 구체적 정의 없음. (Iteration 1 D8, Iteration 2 D5 — 3회 연속 미해결) — Severity: minor

## Chain-of-Verification Pass

두 번째 자체 검토에서 확인한 사항:

**새로운 발견 없음 — 신규 AC 3개 집중 재검토:**

1. AC-NFR-001(acceptance.md:L51): "IF 자동 갱신 기능이 동작하면, THEN THE 시스템 SHALL 소켓 기반 지속 연결 없이 단방향 주기 요청만으로 보유 종목 현재가를 갱신한다." — IF-THEN 패턴 정합, 주어 "THE 시스템" 정합, REQ-POLL-NFR-001(spec.md:L76)의 "소켓 기반 통신 없이" 제약을 Observable outcome으로 표현. WebSocket 코드/트래픽 부재 확인으로 이진 판정 가능.

2. AC-NFR-002(acceptance.md:L52): "THE 시스템 SHALL 장중 판정 함수가 네트워크·데이터베이스 접근 없이 시각 입력만으로 결과를 반환하도록 구현한다." — Ubiquitous 패턴 정합, REQ-POLL-NFR-002(spec.md:L77)의 "순수 함수" 제약 커버. 격리된 단위 테스트로 이진 판정 가능. "구현한다"는 아키텍처 제약의 허용 표현.

3. AC-NFR-005(acceptance.md:L53): "THE 시스템 SHALL 시간·날짜 계산에 외부 과학 계산 라이브러리를 사용하지 않고 언어 표준 라이브러리만으로 처리한다." — Ubiquitous 패턴 정합, REQ-POLL-NFR-005(spec.md:L80) 커버. 의존성 분석(import 검사)으로 이진 판정 가능.

**전체 RE Q 번호 재확인:**
REQ-POLL-001~004, 010~015, 020~022, 030~032, 040, 050, 060~061, NFR-001~005 — 22개 재확인 완료. 십진 그룹핑(카테고리별 10 단위 구간)은 동일 SPEC 내 의도적 패턴으로 MP-1 위반 아님.

**spec.md 버전 관찰:**
spec.md:L3의 version이 0.2.0으로 유지됨(수정 범위가 acceptance.md만이므로 spec.md 버전 미갱신). MP-1 위반 아님 — version 필드는 존재하며 유효한 문자열.

**전 21개 AC 주어 재확인:** "THE 시스템 SHALL" — MP-3 PASS 유지.
**WHEN/WHILE/IF-THEN 패턴 전체 재확인:** — MP-4 PASS 유지.
**REQ-POLL-NFR-003 → AC-012 연결 확인:** AC-012: "THE 시스템 SHALL 별도 선택이 없으면 60초 주기를 적용한다." — REQ-POLL-NFR-003: "기본 폴링 주기를 60초로 한다." 완전 대응.
**REQ-POLL-NFR-004 → AC-050 연결 확인:** AC-050: "IF 직전 폴링 요청이 미완료이면, THEN THE 시스템 SHALL 새 요청을 시작하지 않고 사이클을 건너뛴다." — REQ-POLL-NFR-004: "이전 요청 완료 전 새 요청 발생 않음" 완전 대응.

## Regression Check (Iteration 3)

Defects from iteration 2:

- D1 (REQ-POLL-NFR-001 AC 없음): [RESOLVED] — acceptance.md:L51에서 AC-NFR-001 추가 확인. "IF 자동 갱신 기능이 동작하면, THEN THE 시스템 SHALL 소켓 기반 지속 연결 없이 단방향 주기 요청만으로 보유 종목 현재가를 갱신한다."
- D2 (REQ-POLL-NFR-002 AC 없음): [RESOLVED] — acceptance.md:L52에서 AC-NFR-002 추가 확인. "THE 시스템 SHALL 장중 판정 함수가 네트워크·데이터베이스 접근 없이 시각 입력만으로 결과를 반환하도록 구현한다."
- D3 (REQ-POLL-NFR-005 AC 없음): [RESOLVED] — acceptance.md:L53에서 AC-NFR-005 추가 확인. "THE 시스템 SHALL 시간·날짜 계산에 외부 과학 계산 라이브러리를 사용하지 않고 언어 표준 라이브러리만으로 처리한다."
- D4 (REQ-POLL-060 인증 보호 AC 부재): [UNRESOLVED] — minor, acceptance.md 미수정. 3회 연속 미해결로 기록.
- D5 (REQ-POLL-022 타이밍 모호): [UNRESOLVED] — minor, spec.md:L53 변경 없음. 3회 연속 미해결로 기록.

## Stagnation Notice

D4와 D5는 3회 연속 반복 미해결 상태이나, 모두 Severity: minor 등급으로 MP 기준에 영향을 주지 않는다. 이 항목들은 구현 단계에서 개발자 판단으로 처리 가능한 범위이며 SPEC 자체의 실행 가능성을 방해하지 않는다.

## Recommendation

**PASS — 추가 수정 없이 구현 단계 진행 가능.**

모든 MP 기준(MP-1~MP-7)이 충족되었다. Iteration 2의 유일한 MP-7 FAIL 원인인 REQ-POLL-NFR-001/002/005 AC 부재가 v0.3.0에서 완전히 해결되었다.

잔존 minor 사항(D1, D2)은 구현 단계에서 다음과 같이 처리할 수 있다:
- D1(REQ-POLL-060 인증 AC): 백엔드 구현 시 기존 성과 조회 경로와 동일한 인증 미들웨어를 적용하며, 단위 테스트에서 401 응답 케이스를 포함하면 SPEC 의도를 충족한다.
- D2(REQ-POLL-022 타이밍): 폴링 타이머 콜백 진입 시 시장 개장 여부를 확인하는 방식으로 구현하면 AC-021과 REQ-POLL-022의 의도를 모두 만족한다.
