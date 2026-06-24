# SPEC-STOCK-034 수용 기준 (Acceptance Criteria) — 포트폴리오 벤치마크 비교

> 본 문서는 [spec.md](spec.md)의 REQ-BMK-001~005 및 NFR을 검증 가능한 수용 기준(AC)과 Given-When-Then(BDD) 시나리오로 전개한다. 모든 AC는 관찰 가능한 증거(반환값·상태·테스트 출력)로 판정한다.

---

## 1. EARS 수용 기준 (Acceptance Criteria)

### AC-BMK-001 — 벤치마크 수익률 조회 (REQ-BMK-001)

- **AC-001-1**: WHEN 특정 벤치마크와 기간으로 비교가 요청되면 THE 시스템 SHALL 해당 벤치마크 지수의 기간 시작·종료 가격으로부터 벤치마크 기간 수익률을 도출한다.
- **AC-001-2**: WHEN 지원되는 벤치마크 코드(코스피·코스닥·S&P500·나스닥)가 입력되면 THE 시스템 SHALL 각 코드를 대응하는 지수 심볼로 해석하여 가격을 조회한다.

### AC-BMK-002 — 기간 수익률 비교 (REQ-BMK-002)

- **AC-002-1**: WHEN 기간 벤치마크 수익률이 가용하면 THE 시스템 SHALL 포트폴리오 수익률, 벤치마크 수익률, 초과수익을 모두 포함한 비교 결과를 반환한다.
- **AC-002-2**: WHEN 초과수익을 산출하면 THE 시스템 SHALL 포트폴리오 수익률에서 벤치마크 수익률을 뺀 값을 초과수익으로 설정한다.

### AC-BMK-003 — 알파·베타 산출 (REQ-BMK-003)

- **AC-003-1**: WHEN 일별 수익률 데이터가 최소 요건(20개) 이상 가용하면 THE 시스템 SHALL 베타를 일별 포트폴리오·벤치마크 수익률의 공분산을 벤치마크 수익률의 분산으로 나눈 값으로 산출한다.
- **AC-003-2**: WHEN 기간 수익률이 가용하면 THE 시스템 SHALL 알파를 연환산 포트폴리오 수익률과 연환산 벤치마크 수익률의 차이로 산출한다.

### AC-BMK-004 — 차트 인덱스 데이터 (REQ-BMK-004)

- **AC-004-1**: WHEN 차트 데이터가 요청되면 THE 시스템 SHALL 포트폴리오 값과 벤치마크 값을 기간 시작 시점 100으로 재기준화한 시계열을 반환한다.
- **AC-004-2**: WHEN 차트 시계열을 구성하면 THE 시스템 SHALL 각 시점에 날짜·포트폴리오 인덱스·벤치마크 인덱스를 포함한다.

### AC-BMK-005 — 소유권 및 graceful degradation (REQ-BMK-005, NFR-003, NFR-004)

- **AC-005-1**: IF 비소유 포트폴리오에 대해 벤치마크 비교가 요청되면 THEN THE 시스템 SHALL 존재하지 않는 포트폴리오와 동일하게 응답하여 소유권 정보를 노출하지 않는다.
- **AC-005-2**: IF 특정 기간의 벤치마크 데이터를 확보할 수 없으면 THEN THE 시스템 SHALL 오류 없이 해당 기간의 벤치마크 수익률·초과수익·알파·베타를 미산정 값으로 반환한다.
- **AC-005-3**: IF 일별 수익률 데이터가 20개 미만이면 THEN THE 시스템 SHALL 베타를 미산정 값으로 반환한다.

### AC-BMK-NFR — 비기능 요구사항 수용 기준 (NFR-001, NFR-002, NFR-005)

- **AC-BMK-NFR-001**: WHEN the benchmark comparison is calculated, THE SYSTEM SHALL produce results using only approved numerical computation libraries without relying on external statistical optimization packages.
- **AC-BMK-NFR-002**: WHEN benchmark history data and portfolio history data are provided as function parameters, THE SYSTEM SHALL calculate the comparison result without accessing external data sources or databases.
- **AC-BMK-NFR-005**: IF benchmark price data is unavailable for a period, THE SYSTEM SHALL return a null value for that period's benchmark metrics and continue processing the response.

---

## 2. Given-When-Then 시나리오 (BDD)

### 시나리오 1 — 정상 벤치마크 비교 (해피 패스)

```gherkin
Given 사용자가 소유한 포트폴리오가 보유 종목과 충분한 가격 이력을 가진다
And 벤치마크 지수의 과거 가격 데이터가 비교 기간에 대해 가용하다
When 사용자가 KOSPI 벤치마크와 YTD 기간으로 벤치마크 비교를 요청한다
Then 시스템은 포트폴리오 수익률, 벤치마크 수익률, 초과수익을 반환한다
And 초과수익은 포트폴리오 수익률에서 벤치마크 수익률을 뺀 값과 일치한다
And 응답에 산출 시각이 포함된다
```

### 시나리오 2 — 알파·베타 산출 (충분한 일별 데이터)

```gherkin
Given 포트폴리오와 벤치마크의 공통 거래일 일별 수익률이 20개 이상 가용하다
When 사용자가 벤치마크 비교를 요청한다
Then 시스템은 베타를 공분산을 분산으로 나눈 값으로 반환한다
And 시스템은 알파를 연환산 포트폴리오 수익률과 연환산 벤치마크 수익률의 차이로 반환한다
```

### 시나리오 3 — 재기준화 차트

```gherkin
Given 사용자가 소유한 포트폴리오와 벤치마크 가격 데이터가 가용하다
When 사용자가 SP500 벤치마크와 1Y 기간으로 차트 데이터를 요청한다
Then 시스템은 시점별 포트폴리오 인덱스와 벤치마크 인덱스를 반환한다
And 첫 시점의 포트폴리오 인덱스와 벤치마크 인덱스는 모두 100이다
And 이후 시점의 인덱스는 각 시계열의 첫날 대비 상대 비율에 100을 곱한 값이다
```

### 시나리오 4 — 비소유 포트폴리오 (소유권 비노출)

```gherkin
Given 다른 사용자가 소유한 포트폴리오가 존재한다
When 요청 사용자가 그 포트폴리오의 벤치마크 비교를 요청한다
Then 시스템은 존재하지 않는 포트폴리오에 대한 요청과 동일하게 응답한다
And 응답은 포트폴리오의 존재 여부나 소유권을 노출하지 않는다
```

### 시나리오 5 — 벤치마크 데이터 미확보 (graceful degradation)

```gherkin
Given 사용자가 소유한 포트폴리오는 가격 이력을 가진다
But 요청한 벤치마크 지수의 데이터를 해당 기간에 확보할 수 없다
When 사용자가 벤치마크 비교를 요청한다
Then 시스템은 오류를 발생시키지 않는다
And 포트폴리오 수익률은 반환되지만 벤치마크 수익률, 초과수익, 알파, 베타는 미산정 값이다
```

### 시나리오 6 — 일별 데이터 부족 (베타 미산정)

```gherkin
Given 포트폴리오와 벤치마크의 공통 일별 수익률이 20개 미만이다
When 사용자가 벤치마크 비교를 요청한다
Then 시스템은 기간 수익률과 초과수익은 반환한다
But 베타는 미산정 값으로 반환한다
```

---

## 3. 엣지 케이스 (Edge Cases)

| ID | 상황 | 기대 동작 |
|----|------|-----------|
| EC-01 | 빈 포트폴리오(보유 종목 없음) | 포트폴리오 수익률 산출 불가 → 비교 결과를 미산정/0 처리, 오류 없음 |
| EC-02 | 벤치마크 무변동(분산 0) | 베타 미산정(None) — 0 나눗셈 가드 |
| EC-03 | 공통 거래일 < 2 | 기간 수익률 산출 불가 → 해당 지표 미산정, 오류 없음 |
| EC-04 | 공통 거래일 ≥ 2 이지만 < 20 | 기간 수익률·초과수익 반환, 베타 None |
| EC-05 | 포트폴리오·벤치마크 거래일 불일치(휴장일 차이) | inner join 후 공통 거래일로만 계산 |
| EC-06 | 일부 종목 가격 조회 실패 | 가용 종목만으로 비중 재정규화 후 포트폴리오 가치 산출 |
| EC-07 | 벤치마크 시계열 일부 날짜 결측 | 결측 날짜의 벤치마크 인덱스 None, 포트폴리오 인덱스는 유지 |
| EC-08 | 지원되지 않는 벤치마크 코드 입력 | 입력 검증 거부(허용 4종 외 거부) — 라우터 레벨 검증 |
| EC-09 | NaN/Inf 발생(가격 0 또는 이상치) | 베타·알파 NaN 가드 → None |
| EC-10 | USD 종목 포함 포트폴리오 | KRW 환산 후 가치 시계열 산출, 최종 비율 비교는 통화 무관 |

---

## 4. 비기능 검증 (NFR Verification)

| NFR | 검증 방법 |
|-----|-----------|
| REQ-BMK-NFR-001 (외부 라이브러리 비도입) | `benchmark.py`에 scipy import 부재 확인(grep). numpy+math만 사용 |
| REQ-BMK-NFR-002 (순수 함수 테스트성) | 순수 함수 3종을 DB·Redis·네트워크 없이 시계열 입력만으로 단위 테스트 |
| REQ-BMK-NFR-003 (graceful degradation) | 벤치마크 데이터 None 주입 시 예외 없이 미산정 반환 테스트 |
| REQ-BMK-NFR-004 (베타 최소 데이터) | 19개·20개 경계 입력으로 None/값 분기 테스트 |
| REQ-BMK-NFR-005 (커버리지) | `pytest --cov` 결과 벤치마크 모듈 85% 이상 |

---

## 5. 완료 정의 (Definition of Done)

- [ ] REQ-BMK-001~005 전체에 대응하는 순수 함수·서비스·엔드포인트 구현 완료.
- [ ] 순수 함수 3종(비교·차트·베타)이 DB·네트워크 없이 결정적으로 동작(단위 테스트 통과).
- [ ] 비소유 포트폴리오 요청 시 비존재와 동일 응답(404, 소유권 비노출).
- [ ] 벤치마크 데이터 미확보 기간에 대해 예외 없이 미산정 값 반환.
- [ ] 베타가 일별 데이터 20개 미만일 때 None 반환.
- [ ] 차트 첫 시점 인덱스가 포트폴리오·벤치마크 모두 100.
- [ ] scipy 미사용(numpy+math만) — grep 확인.
- [ ] 신규 DB 테이블·마이그레이션 없음.
- [ ] 신규 스키마 4종·엔드포인트 2종이 기존 명명·경로와 충돌 없음.
- [ ] 프론트 `.js`/`.ts` 쌍 동시 갱신(API 클라이언트·페이지·컴포넌트).
- [ ] 단위 테스트 커버리지 85% 이상.
- [ ] @MX 태그(ANCHOR/NOTE/WARN) 한국어 작성, `[AUTO]` 접두사 포함.
- [ ] 기존 SPEC-030/027/028 코드 미수정(재사용만).
