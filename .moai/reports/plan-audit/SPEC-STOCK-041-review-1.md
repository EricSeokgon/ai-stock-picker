# SPEC-STOCK-041 감사 보고서

**감사 대상**: SPEC-STOCK-041 — 포트폴리오 목표 관리  
**감사 일시**: 2026-06-29  
**반복 차수**: 1/3  
**감사 판정**: **수정 권장 (FAIL)**  
**종합 품질 점수**: **6 / 10**

---

## 요약 (Summary)

SPEC-STOCK-041은 EARS 패턴과 YAML 프론트매터가 전반적으로 올바르게 작성되어 있으며, REQ-AC 트레이서빌리티도 완전하다. 그러나 `deadline`만 있는 목표의 `achievement_rate` 반환값이 정의되지 않았고(Critical), GET 응답이 단일 객체인지 배열인지 미결이며(Critical), POST 시 기존 활성 목표 처리 동작이 REQ와 AC에서 누락되어 있다(Major). 이 결함들이 해소되지 않으면 구현 단계에서 개발자 간 다른 결과물이 나올 가능성이 높다.

---

## Must-Pass 체크 결과

| 항목 | 판정 | 증거 |
|------|------|------|
| MP-1: REQ 번호 순서 (gaps·중복·제로패딩) | PASS | REQ-GOAL-001~007 전체 존재, 중복 없음, `001`-`007` 일관된 3자리 패딩. 단, 문서 내 제시 순서가 001→002→003→006→007→004→005로 비선형 — gaps/duplicate는 없으나 순서 혼란은 Major Issue로 별도 기록 |
| MP-2: EARS 패턑 준수 | PASS | 7개 REQ 전부 EARS 패턴(Event-driven, Unwanted behavior, Ubiquitous) 사용. SHALL 키워드 일관 적용 (spec.md:L69-88) |
| MP-3: YAML 프론트매터 유효성 | PASS | id, version, status, created_at, priority, labels 전부 정의, 타입 정상 (spec.md:L1-13) |
| MP-4: 언어 중립성 | N/A | 단일 Python/React 스택 프로젝트, 다국어 도구 열거 불필요 |

---

## 차원별 점수 (0.0–1.0)

| 차원 | 점수 | 근거 |
|------|------|------|
| 명확성 (Clarity) | 0.50 | deadline-only 목표의 achievement_rate, GET 응답 형태가 미정의로 두 개발자가 다르게 구현 가능 (spec.md:L80, L126) |
| 완전성 (Completeness) | 0.75 | 섹션 구조는 갖췄으나 POST 기존 목표 처리 동작이 REQ/AC에서 누락, Over-the-limit deadline 처리 없음 |
| 테스트가능성 (Testability) | 0.75 | 대부분 AC는 이진 판단 가능. AC-6(L199) 정밀도 미명시로 부동소수점 테스트 불안정 가능 |
| 트레이서빌리티 (Traceability) | 1.00 | REQ-GOAL-001~007 전부 AC 대응 완전, 고아 AC 없음 |

---

## Critical Issues (구현 전 반드시 수정)

### C-1: `deadline`만 있는 목표의 `achievement_rate` 반환값 미정의

**위치**: spec.md:L69-80, L148-149

**문제**: REQ-GOAL-001(L69)은 `target_amount`, `target_return_rate`, `deadline` 세 값 중 최소 1개만 있으면 유효한 목표로 인정한다. 따라서 `deadline=2026-12-31`만 지정하고 나머지가 None인 목표는 합법적으로 생성된다.

REQ-GOAL-007(L79-80)은 `target_amount` 또는 `target_return_rate`가 미설정이면 "해당 항목은 달성률 계산에서 제외"라고만 규정한다. **두 항목 모두 None인 경우** `achievement_rate`가 무엇인지 정의하지 않는다.

`GoalWithProgressResponse`(L148)에서 `achievement_rate: float`는 nullable이 아닌 `float`로 선언되어 있어, null 반환도 불가하다.

**영향**: 개발자마다 다르게 구현 가능.
- 구현자 A: 0.0 반환 (미달성 처리)
- 구현자 B: None 반환 → 스키마 위반 런타임 오류
- 구현자 C: POST에서 422 반환 (deadline만 목표 거부)

**수정 방법**: 다음 중 하나를 REQ-GOAL-007 및 GoalCreate 검증에 명시한다.  
- 옵션 1: deadline만 있는 목표는 `achievement_rate=null` (GoalWithProgressResponse에서 `float | None`으로 변경)  
- 옵션 2: GoalCreate 검증을 강화해 `target_amount` 또는 `target_return_rate` 중 하나는 반드시 제공하도록 강제 (deadline은 단독으로는 불허)

---

### C-2: GET 응답 형태 미정의 — 단일 객체 vs 배열

**위치**: spec.md:L126, L144-149, L162-163

**문제**: API 경로(L126)는 `/portfolios/{portfolio_id}/goals`(복수형)이며, Pydantic 스키마(L145)는 `GoalWithProgressResponse`(단수)이다. 프론트엔드 API 래퍼(L162)는 `getPortfolioGoal(portfolioId)`(단수)를 사용한다.

MVP에서 활성 목표가 1개이지만, REST 규약상 복수형 컬렉션 엔드포인트(`/goals`)는 배열을 반환한다. 반면 단수 래퍼와 단수 스키마 명칭은 단일 객체를 암시한다.

**영향**: 백엔드 구현자와 프론트엔드 구현자가 다른 가정하에 작업할 수 있다.  
- 백엔드: `[GoalWithProgressResponse]` 반환 → 204는 `[]` 반환  
- 프론트엔드: 단일 객체 기대 → 배열[0]으로 파싱 필요 여부 불명확

**수정 방법**: 두 가지 중 하나를 명시한다.  
- 옵션 A: 단일 객체 반환 → 경로를 `/portfolios/{portfolio_id}/goal`(단수)로 변경하거나, 복수형 경로지만 단일 객체 반환을 명시  
- 옵션 B: 배열 반환 → `GoalWithProgressResponse`가 배열(리스트)로 래핑됨을 명시, 204 대신 `200 []` 반환 고려

---

## Major Issues (구현 중 혼란 야기)

### M-1: REQ 번호 비선형 제시 순서 혼란

**위치**: spec.md:L69-88 (섹션 3.1~3.4)

**문제**: 섹션 3.1 내에 REQ-GOAL-001, 002, 003이 나온 직후 REQ-GOAL-006(L72)이 등장하고, REQ-GOAL-004와 005는 이후 섹션(3.3, 3.4)에 출현한다. 문서 제시 순서: **001 → 002 → 003 → 006 → 007 → 004 → 005**.

독자는 004/005가 누락된 것으로 오해하거나, 섹션별 분류를 번호로 추적할 때 혼선이 생긴다. 구현 priority 파악도 불명확해진다.

**수정 방법**: REQ 번호를 섹션 배치 순서에 맞게 재할당한다 (예: 3.1의 4개를 001~004, 3.2를 005, 3.3을 006, 3.4를 007로 재정렬). 또는 섹션 순서를 REQ 번호 순서에 맞게 재배치한다.

---

### M-2: POST 시 기존 활성 목표 존재 케이스가 REQ와 AC에서 누락

**위치**: spec.md:L117 (섹션 4.1), L69 (REQ-GOAL-001), L193 (AC-1)

**문제**: 섹션 4.1(L117)에는 "동일 포트폴리오에 `is_active=True` 목표가 이미 있으면 기존 비활성화 후 신규 생성 **또는** 409 반환 — RUN 단계에서 확정"이라고 기술되어 있다. 이 두 옵션(자동 대체 vs 409 에러)은 전혀 다른 UX를 생성하며 중요한 비즈니스 결정이다.

그런데 REQ-GOAL-001(L69)에는 이 케이스에 대한 언급이 없다. AC-1(L193)도 "금액만/수익률만/3종 조합"만 다루며, 기존 목표 존재 케이스가 없다.

**영향**: 구현자가 RUN 단계에서 스스로 결정해야 하며, 잘못된 선택을 되돌리려면 스키마·테스트 재작성 비용 발생.

**수정 방법**: PLAN 단계에서 결정 후 REQ-GOAL-001 또는 신규 REQ에 명시한다. AC-1에도 해당 시나리오(기존 활성 목표 대체 또는 409)를 추가한다.

---

### M-3: 과거 deadline 처리 및 `days_remaining` 음수 시나리오 미정의

**위치**: spec.md:L71, L104, L149

**문제**:  
1. POST 시 `deadline`에 과거 날짜를 허용하는지 GoalCreate 검증에서 명시되지 않음.  
2. `days_remaining`(L149)는 `int | None`으로 선언되어 있으나, deadline이 지난 목표에서 이 값이 음수가 되는 케이스(예: -5일)에 대한 처리 규칙이 없음.  
   - 음수를 그대로 반환하면 프론트엔드 진행률 바 렌더링 오류 가능  
   - 0으로 클램핑하면 "초과" 의미 소실  
   - `None` 반환이면 스키마와 모순 (deadline 없음과 구분 불가)

**수정 방법**: `deadline` 필드에 `date >= today` 검증 추가(선택) 또는 음수 `days_remaining` 반환 값을 스키마에 명시. "기한 초과" 상태 표현 방식을 결정해 REQ에 추가한다.

---

### M-4: `achievement_rate` 음수 발생 시 처리 미정의

**위치**: spec.md:L78

**문제**: REQ-GOAL-007(L78) 계산식: `achievement_rate = (current_return_rate / target_return_rate) * 100`

`current_return_rate`가 음수(-5%)이고 `target_return_rate`가 양수(10%)이면 `achievement_rate = -50%`가 된다. 이 음수 값에 대한 처리가 SPEC에 없다.  
- 그대로 반환: 프론트엔드 진행률 바가 음수 입력 처리 필요  
- 0으로 클램핑: 손실 상태를 사용자에게 숨김  
- 두 개발자 간 다른 선택 가능

**수정 방법**: REQ-GOAL-007 또는 별도 규칙으로 `achievement_rate = max(0.0, 계산값)` 또는 "음수 그대로 반환" 중 하나를 명시한다. 프론트엔드 컴포넌트 스펙(섹션 7)에도 음수 입력 처리 방식을 기술한다.

---

### M-5: AC-6 정밀도 미명시

**위치**: spec.md:L198-L199

**문제**:  
- AC-5(L198): `(current_value/target_amount)*100` 과 **±0.01% 이내** 일치 → 명확
- AC-6(L199): `(current_return_rate/target_return_rate)*100` 과 **"일치"** → 정밀도 없음

부동소수점 연산에서 완전 일치(`==`)는 실패 가능. AC-5와의 비일관성도 혼란을 야기한다.

**수정 방법**: AC-6에 AC-5와 동일한 "±0.01% 이내" 또는 명확한 부동소수점 허용 오차를 추가한다.

---

## Minor Issues (수정 권장)

### MN-1: GoalCreate에 `target_amount`, `target_return_rate` 음수 가드 없음

**위치**: spec.md:L139-141

REQ-GOAL-007(L80)은 "0 이하이면 해당 항목을 계산에서 제외"라고 규정한다. 그런데 GoalCreate 스키마(L139-141)에는 음수 검증이 없다. 음수 `target_amount` 또는 `target_return_rate`로 목표 생성이 가능하고, 이 경우 생성은 성공하지만 달성률 계산에서 제외되어 의미없는 목표가 저장된다.

**수정 방법**: `GoalCreate`에 `target_amount > 0`, `target_return_rate > 0` 검증을 추가한다.

---

### MN-2: GoalCreate 422 검증 및 0 나눗셈 가드 테스트가 "추가 권장"으로만 표기

**위치**: spec.md:L185

"추가 권장"이라고 표기된 두 테스트는 REQ-GOAL-001의 최소 1개 제공 규칙과 REQ-GOAL-007의 0 나눗셈 방지의 핵심 동작을 검증한다. 필수 테스트 항목(T-001~T-010)에 포함되지 않아 구현자가 생략할 수 있다.

**수정 방법**: T-011(`GoalCreate` 세 값 모두 None → 422), T-012(`target_amount=0`인 경우 달성률 계산 제외)를 정식 테스트 목록에 추가한다.

---

### MN-3: NFR-6 커버리지 기준 미명시

**위치**: spec.md:L214

"프로젝트 기준(`fail_under`)을 충족한다"에서 `fail_under` 값이 명시되지 않았다. 다른 SPEC에서는 `fail_under`가 85%로 설정된 경우가 있으나, 이 SPEC에서 직접 확인할 수 없다.

**수정 방법**: 프로젝트 `pytest.ini` 또는 `pyproject.toml`의 `fail_under` 값을 명시적으로 기재하거나, "프로젝트 표준(85%) 준수"라고 구체화한다.

---

### MN-4: `notifications` 테이블 멱등 적재 검증이 AC-8에서 누락

**위치**: spec.md:L200, L230

AC-8(L200)은 "텔레그램+이메일 발송 호출 + `goal_reached_notified=True` 전환"만 검증한다. 하지만 SPEC 개요(L32-33)와 구현 노트(L230)는 `notifications` 테이블 멱등 적재(SPEC-036 패턴 재사용)를 명시한다. `notifications` 테이블 적재 자체가 AC로 측정되지 않아, notifications 인프라 재사용 여부가 자동으로 검증되지 않는다.

**수정 방법**: AC-8에 "notifications 테이블에 목표 달성 알림 행이 1건 적재됨"을 추가한다.

---

### MN-5: REQ-GOAL-003, REQ-GOAL-004에 DB 컬럼명이 포함됨

**위치**: spec.md:L71, L84

- REQ-GOAL-003(L71): "`is_active=False`" 는 DB 컬럼명+값
- REQ-GOAL-004(L84): "`goal_reached_notified == False`", "`goal_reached_notified = True`" 는 DB 컬럼명

요구사항(WHAT)에 구현 세부사항(HOW)이 포함되어 있어, 향후 컬럼명 변경 시 SPEC 수정이 필요해진다.

**수정 방법**: "소프트 삭제(논리적 비활성화)", "알림 발송 여부 플래그" 등 동작 수준의 언어로 교체한다.

---

## 검증 완료 항목 (Verified OK)

| 항목 | 결과 |
|------|------|
| YAML 프론트매터 6개 필수 필드 | 전부 존재, 타입 정상 (L1-13) |
| EARS 패턴 7개 REQ | 전부 준수 — WHEN/IF/THEN/SHALL 사용 (L69-88) |
| REQ-AC 트레이서빌리티 | REQ-001~007 전부 AC 대응, 고아 AC 없음 (L191-203) |
| T-001~T-010 vs REQ-GOAL-001~007 커버리지 | 전 REQ 커버됨 (L173-183) |
| Out-of-Scope 항목 명확성 | 8개 항목 구체적으로 나열 (L54-61) |
| scipy 제외 조항 | NFR-1(L209) + AC-11(L203) 이중 적용 ✓ |
| migration 0025 단일 제약 | NFR-3(L211) + AC-11(L203) 이중 적용 ✓ |
| calculate_performance() 재사용 명시 | NFR-2(L210) + 구현 노트(L222-226) ✓ |
| 자동 매매 제외 | NFR-4(L212) + Out-of-Scope(L54) 이중 적용 ✓ |
| _build_portfolio_data() 오용 주의 | 섹션 11.3(L226) 명시 ✓ |
| 알림 멱등(goal_reached_notified 플래그) | REQ-GOAL-004(L84) + AC-9(L201) ✓ |
| 소유권 검증 404 정책 | REQ-GOAL-005(L88) + AC-10(L202) ✓ |

---

## Chain-of-Verification Pass (2차 자기 점검)

2차 검토에서 추가 발견된 사항:

1. **T-010 테스트 가능성**: "달성률 100% 이상 → 알림 발송 (스케줄러 트리거)"는 단위 테스트에서 스케줄러를 어떻게 호출하는지 기술되지 않았음. 실제로는 스케줄러 잡 함수를 직접 호출하거나 의존성 주입으로 모킹하는 방식이 필요하나, SPEC이 이를 제시하지 않음. 이는 Minor 수준이므로 MN-6으로 추가.

2. **GoalWithProgressResponse extends GoalResponse 관계**: L145의 "GoalWithProgressResponse (extends GoalResponse)"에서 상속 관계가 명시되어 있는데, L144의 GoalResponse에는 `goal_reached_notified` 필드가 없음. 이 필드를 API 응답으로 노출할 필요가 있는지(특히 GET 응답에서) 미정. Minor 수준.

3. **REQ-GOAL-002에 활성 목표 없을 때의 GET 동작 미포함**: REQ-GOAL-002는 활성 목표가 있는 케이스만 다루고, 없는 케이스는 REQ-GOAL-006으로 분리. 이는 의도적 분리이므로 OK.

4. **섹션 4.1 "앱 레벨 강제"와 DB-레벨 제약 없음의 위험**: 동시 POST 요청 시 race condition 발생 가능. 이는 이미 인지된 설계 결정이고 "MVP"로 한정됨. Minor.

---

### MN-6: T-010 스케줄러 단위 테스트 호출 방식 미기술

**위치**: spec.md:L183

T-010은 "스케줄러 트리거"를 테스트하는데, 실제로 단위 테스트에서 스케줄러를 어떻게 실행하는지(직접 함수 호출 vs pytest-apscheduler 등) 기술되지 않아 구현자가 결정해야 한다. Minor Issue.

**수정 방법**: "스케줄러 잡 함수(`check_all_portfolio_goals`)를 직접 호출하고 알림 헬퍼를 mock으로 대체" 등 접근 방식을 테스트 계획에 추가한다.

---

## 권장 수정 사항 (manager-spec 전달)

### 반드시 수정 (Critical — 구현 착수 전)

1. **C-1 해소**: REQ-GOAL-001 검증 강화(`target_amount` 또는 `target_return_rate` 중 최소 1개 필수 — `deadline`만 단독 허용 불가) OR REQ-GOAL-007에 "두 항목 모두 미설정 시 `achievement_rate=null`" 규칙 추가 및 `GoalWithProgressResponse.achievement_rate`를 `float | None`으로 변경. 두 옵션 중 하나를 명시적으로 선택해야 함.

2. **C-2 해소**: GET 엔드포인트 응답이 단일 객체인지 배열인지 결정하고 API 표(섹션 5), Pydantic 스키마(섹션 6), 프론트엔드 API 래퍼(섹션 7)를 일관되게 기술한다.

### 수정 권장 (Major — 구현 혼란 방지)

3. **M-1**: REQ 번호를 문서 내 섹션 순서에 맞게 재할당(001-007을 섹션 3.1→3.4 순서대로 배치).

4. **M-2**: REQ-GOAL-001에 "기존 활성 목표 자동 비활성화 후 신규 생성" 또는 "409 반환" 중 하나를 확정 기재. AC-1에도 해당 시나리오 추가.

5. **M-3**: GoalCreate에 `deadline >= today` 검증 추가 여부 결정. `days_remaining` 음수 처리 방식 명시.

6. **M-4**: `achievement_rate` 음수 클램핑 여부 명시 (REQ-GOAL-007에 `max(0.0, ...)` 또는 "음수 허용" 중 선택).

7. **M-5**: AC-6에 "±0.01% 이내" 또는 동등한 허용 오차를 추가.
