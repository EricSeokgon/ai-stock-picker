# SPEC-STOCK-030 인수 조건 (Acceptance Criteria)

> **형식 안내**: 이 문서는 두 섹션으로 구성됩니다.
> - **§1 EARS 인수 조건**: spec.md §3 EARS 요구사항과 1:1 매핑되는 검증 가능한 인수 기준 (must-pass 기준).
> - **§2 BDD 시나리오**: 각 인수 기준을 자동화 테스트로 구현하기 위한 Given-When-Then 형식 상세 시나리오.

---

## §1. EARS 형식 인수 조건

각 REQ-PS-XXX에 대한 검증 가능한 인수 조건. 구현 완료 시 모든 항목을 체크해야 한다.

| REQ ID | 인수 조건 (검증 가능한 단일 기준) |
|--------|----------------------------------|
| REQ-PS-001 | `GET /portfolios/{id}/performance-summary` 엔드포인트가 존재하며 인증된 소유자에게 `200 OK`로 응답한다. |
| REQ-PS-002 | 정상 응답에 `periods` 배열 내 `ytd`·`1m`·`3m`·`6m`·`1y` 5개 기간이 모두 포함된다. |
| REQ-PS-003 | 각 기간 항목에 `total_return_pct`·`annualized_return_pct`·`mdd_pct` 필드가 숫자 또는 null로 포함된다. |
| REQ-PS-004 | 당일 캐시 유효 시 `refresh=false`(기본값)로 재요청하면 FDR API 호출 없이 캐시 데이터가 반환된다(재계산 없음). |
| REQ-PS-005 | 보유 종목이 없는 포트폴리오 요청 시 `200 OK`와 함께 5개 기간이 모두 `has_data=false`인 응답이 반환된다(4xx 오류 없음). |
| REQ-PS-006 | KRX 종목(KRW)과 NYSE/NASDAQ 종목(USD)이 혼합된 포트폴리오에서 해외 종목 가치가 KRW로 환산되어 포트폴리오 총 가치에 합산된다. |
| REQ-PS-007 | `refresh=true` 파라미터로 요청하면 기존 캐시를 무시하고 재계산한 결과를 반환하며 캐시를 갱신한다. |
| REQ-PS-008 | 1Y 시작일 이전에 상장한 종목이 있으면 가용한 가장 이른 거래일부터 계산하거나, 유효 거래일이 2일 미만이면 `has_data=false`로 표시한다. |
| REQ-PS-009 | 프론트엔드에 `PerformanceSummaryPanel` 컴포넌트가 존재하고 Portfolio 페이지에서 5개 기간 카드를 렌더링한다. |
| REQ-PS-010 | 응답 JSON에 `calculated_at`(ISO-8601 UTC 문자열)·`disclaimer`(문자열) 필드가 포함된다. |
| NFR-001 | `portfolio/performance_summary.py` 코드에 `import scipy` 구문이 존재하지 않는다(ruff/grep 정적 검사). |
| NFR-002 | Redis 캐시 히트 시 응답 완료까지 500ms 이내이다. |
| NFR-003 | `pytest --cov=stock_picker/portfolio/performance_summary` 결과 커버리지 85% 이상. |

---

## §2. BDD 시나리오 (자동화 테스트 기반)

> 각 시나리오에 해당 REQ ID를 명시한다. 시나리오는 §1 EARS 조건을 구현하는 자동화 테스트의 기반이다.

---

### Scenario 1: 정상 5기간 성과 조회
**Covers**: REQ-PS-001, REQ-PS-002, REQ-PS-003, REQ-PS-006

**Given**: 포트폴리오에 삼성전자(KRX, 005930), 애플(NYSE, AAPL)을 보유하고 충분한 과거 시세 데이터가 존재한다.

**When**: 인증된 소유자가 `GET /portfolios/{id}/performance-summary`를 호출한다.

**Then**:
- `200 OK`로 응답한다.
- `periods` 배열에 5개 기간(ytd/1m/3m/6m/1y)이 모두 포함된다.
- 각 기간 항목에 `total_return_pct`·`annualized_return_pct`·`mdd_pct`가 산출된다.
- 각 항목에 `start_date`·`end_date`·`trading_days`·`has_data=true`가 포함된다.
- 해외 종목(AAPL) 가치가 USD/KRW 환율로 KRW 환산되어 합산된다.

---

### Scenario 2: Redis 캐시 히트
**Covers**: REQ-PS-004, NFR-002

**Given**: 이전 요청에서 성과 요약을 계산하여 Redis에 당일 캐시가 존재한다(TTL 유효).

**When**: 동일 사용자가 `refresh=false`(기본값)로 성과 요약을 재요청한다.

**Then**:
- Redis에서 캐시된 데이터를 그대로 반환한다.
- FDR API를 호출하지 않는다(재계산 없음).
- 응답시간은 500ms 이내이다(NFR-002).

---

### Scenario 3: 캐시 갱신
**Covers**: REQ-PS-007

**Given**: Redis에 당일 캐시된 성과 요약이 존재한다.

**When**: 사용자가 `refresh=true` 쿼리 파라미터로 요청한다.

**Then**:
- 기존 캐시를 무시한다.
- FDR에서 최신 시세를 재조회하여 5개 기간을 재계산한다.
- 재계산 결과로 캐시를 갱신한다.
- 갱신된 결과를 반환한다.

---

### Scenario 4: 빈 포트폴리오
**Covers**: REQ-PS-005

**Given**: 보유 종목이 하나도 없는 포트폴리오가 존재한다.

**When**: 인증된 소유자가 `GET /portfolios/{id}/performance-summary`를 호출한다.

**Then**:
- `200 OK`로 응답한다(4xx 오류가 아니다).
- `periods` 배열에 5개 기간이 모두 포함되며 각 항목은 빈 데이터(`has_data=false`, 수익률 필드 null)이다.
- 예외가 발생하지 않는다.

---

### Scenario 5: 기간 시작일 이전 상장 종목
**Covers**: REQ-PS-008

**Given**: 1Y 기간 시작일(1년 전) 이전에는 상장하지 않았으나 그 이후 상장한 종목을 포함한 포트폴리오가 존재한다.

**When**: 1Y 기간 성과 요약을 계산한다.

**Then**:
- 해당 종목의 가용한 가장 이른 거래일부터 시세를 사용하여 1Y 수익률을 정상 계산하거나, 유효 거래일이 2일 미만이면 1Y 기간을 빈 데이터(`has_data=false`)로 표시한다.
- 다른 기간(YTD/1M/3M/6M)은 영향 없이 정상 계산된다.

---

### Scenario 6: 타인 포트폴리오 접근
**Covers**: 보안 소유권 검증 (service.get_portfolio_with_holdings 관례)

**Given**: `user_id != portfolio.user_id`인 다른 사용자의 포트폴리오가 존재한다.

**When**: 인증된 사용자가 `GET /portfolios/{other_user_portfolio_id}/performance-summary`를 호출한다.

**Then**:
- `404 Not Found`로 응답한다(코드베이스 관례: `get_portfolio_with_holdings`는 소유권 불일치 시 404를 반환한다).
- 성과 데이터를 반환하지 않는다.

---

### Scenario 7: YTD 경계 케이스 (연초)
**Covers**: REQ-PS-008 (YTD 적용)

**Given**: 오늘이 당해 1월 초(예: 1월 2일)이며 포트폴리오에 종목을 보유한다.

**When**: YTD 기간 성과를 계산한다.

**Then**:
- YTD 유효 거래일이 2일 미만이면 YTD 기간을 빈 데이터(`has_data=false`)로 표시한다.
- 추측으로 수익률을 단언하지 않는다.
- 나머지 기간(1M/3M/6M/1Y)은 정상 계산된다.

---

### Scenario 8: FDR 조회 실패 (graceful degradation)
**Covers**: NFR-004

**Given**: 포트폴리오에 종목을 보유하나 FDR 시세 조회가 일시적으로 실패한다.

**When**: 성과 요약을 요청한다.

**Then**:
- 예외를 전파하지 않는다(NFR-004).
- 조회 실패 종목/기간을 제외하거나 빈 데이터를 반환한다.
- 일부 기간만 데이터가 있어도 5개 기간 구조는 유지된다.

---

### Scenario 9: 프론트엔드 PerformanceSummaryPanel 렌더링
**Covers**: REQ-PS-009

**Given**: 포트폴리오 성과 요약 API가 5개 기간 데이터를 반환한다.

**When**: Portfolio 페이지를 로드하면 `PerformanceSummaryPanel` 컴포넌트가 마운트된다.

**Then**:
- 5개 기간(YTD/1M/3M/6M/1Y) 카드가 각각 렌더링된다.
- 각 카드에 기간 라벨과 `total_return_pct` 수치가 표시된다.
- 양수 수익률은 녹색(`text-green-*`), 음수 수익률은 적색(`text-red-*`) 스타일로 표시된다.
- API 로딩 중에는 로딩 상태(스켈레톤 또는 스피너)가 표시된다.

---

## 성능 기준 (Performance Criteria)

| 항목 | 기준 |
|------|------|
| Redis 캐시 히트 응답시간 | 500ms 이내(NFR-002) |
| FDR 병렬 조회 | `run_in_executor` + `asyncio.gather`로 이벤트 루프 비블로킹 |
| FDR API 실패 | graceful degradation(빈 배열/빈 데이터 반환, 예외 비전파) |
| 환율 조회 실패 | fallback 1350.0 사용, 계산 중단 없음 |

---

## 품질 게이트 (Quality Gate)

- [ ] REQ-PS-001 ~ REQ-PS-010 전부 구현·검증.
- [ ] NFR-001(scipy 금지) 정적 검사 통과.
- [ ] NFR-003 단위 테스트 커버리지 85% 이상.
- [ ] 단위 테스트 30개 이상 PASS.
- [ ] 통합 테스트(200/401/404/refresh/빈 포트폴리오) PASS.
- [ ] 프론트엔드 5개 기간 카드 렌더링 확인(Scenario 9).

## 완료 정의 (Definition of Done)

- 모든 인수 시나리오(1~9)가 자동화 테스트로 통과한다.
- §1 EARS 인수 조건 전 항목이 충족된다.
- 모든 품질 게이트 체크리스트 항목이 충족된다.
- MX 태그가 신규/수정 코드에 부여되었다(ANCHOR·NOTE).
- 신규 DB 마이그레이션이 추가되지 않았다(0018 유지).
- 코드 주석은 한국어로 작성되었다.
