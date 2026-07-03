# SPEC-STOCK-034 구현 계획 (Plan) — 포트폴리오 벤치마크 비교

> [spec.md](spec.md) 구현을 위한 작업 분해(T-001~T-007). 시간 추정 금지 — 우선순위(High/Medium/Low)와 순서 의존성으로 표기. 개발 방법론은 `quality.yaml` 설정을 따른다(브라운필드 TDD).

---

## 1. 기술 접근 요약

- 신규 모듈 `portfolio/benchmark.py`: 순수 함수 3종 + 서비스 오케스트레이션 2종.
- 재사용: SPEC-030(기간 헬퍼·가치 시계열·연환산), SPEC-027(numpy 베타 패턴·일별 수익률), SPEC-028(KRW 환산), SPEC-029(FDR 시계열 조회).
- 신규 스키마 4종, 신규 엔드포인트 2종. DB 테이블·마이그레이션·scipy 없음.

---

## 2. 작업 분해 (Tasks)

### T-001 — 스키마 정의 [Priority: High]

- `portfolio/schemas.py` 하단에 SPEC-034 주석과 함께 추가:
  - `BenchmarkPeriodReturn`, `BenchmarkComparison`, `BenchmarkChartPoint`, `BenchmarkChartData`.
- Pydantic v2(`BaseModel`, `Optional`, `date`/`datetime`) 기존 import 재사용.
- **의존성**: 없음(선행 작업).
- **검증**: 모델 인스턴스화·직렬화 단위 테스트.

### T-002 — 순수 함수: 베타 산출 [Priority: High]

- `benchmark.py`에 `calculate_beta(portfolio_daily_returns, benchmark_daily_returns)` 구현.
- numpy 전용: `np.cov`, `np.var(ddof=1)`. 데이터 < 20 또는 var=0 또는 NaN/Inf → None.
- 모듈 상단 `@MX:NOTE`: scipy 금지·numpy/math 전용 명시.
- **의존성**: 없음.
- **검증**: 20개 경계(19/20), 무변동 벤치마크, 동일 시리즈(베타≈1) 테스트.

### T-003 — 순수 함수: 벤치마크 비교 [Priority: High]

- `calculate_benchmark_comparison(portfolio_history, benchmark_history, period)` 구현.
- 공통 거래일 inner join → 기간 수익률(포트폴리오·벤치마크)·초과수익·연환산 알파·베타(T-002 호출).
- 벤치마크 데이터 None/결측 시 벤치마크 지표 미산정(graceful degradation).
- 진입 함수에 `@MX:ANCHOR` + `@MX:REASON`.
- **의존성**: T-001(스키마), T-002(베타).
- **검증**: 정상 비교, 벤치마크 None, 공통 거래일 < 2 테스트.

### T-004 — 순수 함수: 재기준화 차트 [Priority: High]

- `calculate_benchmark_chart(portfolio_history, benchmark_history, period)` 구현.
- 공통 거래일 정렬 → 첫날 100 기준 포트폴리오·벤치마크 인덱스 산출.
- 벤치마크 결측 날짜 인덱스 None.
- **의존성**: T-001(스키마).
- **검증**: 첫 시점 100 확인, 벤치마크 결측 날짜 None 테스트.

### T-005 — 서비스 오케스트레이션 [Priority: High]

- `benchmark.py`에 비교/차트 서비스 2종 구현:
  - 소유권 확인(`get_portfolio_with_holdings` → None 시 404).
  - 기간 시작일 산정(SPEC-030 기간 헬퍼 재사용).
  - 포트폴리오 일별 가치 시계열 산출(SPEC-030 가치 로직 재사용, USD KRW 환산).
  - 벤치마크 지수 심볼 가격 시계열 온디맨드 조회(동기 FDR + `run_in_executor` 격리, `@MX:WARN`).
  - 순수 함수(T-003/T-004) 호출 후 응답 구성.
- 벤치마크 심볼 매핑 상수(KOSPI→^KS11 등).
- **의존성**: T-003, T-004.
- **검증**: 소유권 404, 벤치마크 조회 실패 시 graceful, 정상 경로 통합 테스트(가격 조회 모킹).

### T-006 — 라우터 엔드포인트 [Priority: Medium]

- `portfolio/router.py`에 2종 추가:
  - `GET /{portfolio_id}/benchmark?benchmark=&period=` → `BenchmarkComparison`.
  - `GET /{portfolio_id}/benchmark/chart?benchmark=&period=` → `BenchmarkChartData`.
- `Query(default=...)` 파라미터 + 지원 벤치마크/기간 검증.
- 기존 의존성 주입(`get_current_user`/`get_db_session`/`get_redis_client`) 재사용.
- **의존성**: T-005.
- **검증**: 엔드포인트 응답 모델·기본값·검증 테스트.

### T-007 — 프론트엔드 통합 [Priority: Medium]

- `frontend/src/components/BenchmarkComparisonCard.js` — 벤치마크 선택 + 비교 지표 카드.
- `frontend/src/components/BenchmarkChart.js` — 100 기준 재기준화 라인 차트.
- `frontend/src/api/portfolio.js`(+`.ts`) — `apiGetBenchmarkComparison`·`apiGetBenchmarkChart`.
- `frontend/src/pages/Portfolio.js`(+`.tsx`) — 벤치마크 섹션 통합(기존 섹션 보존).
- **의존성**: T-006(API 계약).
- **검증**: 컴포넌트 렌더·API 호출 형태 확인.

---

## 3. 작업 순서 (Dependency Order)

```
T-001 (스키마) ─┬─> T-003 (비교) ─┐
T-002 (베타) ───┘                 ├─> T-005 (서비스) ─> T-006 (라우터) ─> T-007 (프론트)
T-001 (스키마) ───> T-004 (차트) ─┘
```

- 백엔드 우선(T-001~T-006) 완료 후 프론트(T-007).
- T-002·T-004는 T-001 이후 병렬 가능. T-003은 T-002 의존.

---

## 4. 마일스톤

| 마일스톤 | 포함 작업 | 완료 기준 |
|----------|-----------|-----------|
| M1 — 순수 계산 코어 | T-001~T-004 | 순수 함수 3종 단위 테스트 통과, scipy 부재 |
| M2 — 서비스·API | T-005~T-006 | 소유권 404·graceful degradation·엔드포인트 동작 |
| M3 — 프론트·마감 | T-007 | UI 통합, 커버리지 85%+, DoD 충족 |

---

## 5. 리스크 및 대응

| 리스크 | 영향 | 대응 |
|--------|------|------|
| 지수 심볼(`^KS11` 등) FDR 조회 실패 | 벤치마크 지표 미산정 | graceful degradation(None) — REQ-BMK-005, 오류 비전파 |
| 포트폴리오/벤치마크 거래일 불일치 | 공통 거래일 축소, 베타 데이터 부족 | inner join + 20개 임계 None 처리 |
| 030 가치 시계열 함수가 첫/마지막만 사용 | 일별 시계열 직접 필요 | 서비스에서 일별 시계열을 그대로 순수 함수에 주입 |
| USD/KRW 환산 누적 부동소수 오차 | 미세 수익률 오차 | round 일관성, 비율 비교로 통화 상쇄 |
| 빈 포트폴리오 | 비교 산출 불가 | 미산정/0 처리, 오류 없음(EC-01) |

---

## 6. 품질 게이트

- scipy 미사용(numpy+math) — grep 검증.
- 소유권 위반 시 404(403 아님).
- 신규 DB 마이그레이션 없음.
- 단위 테스트 커버리지 85% 이상.
- @MX 태그(ANCHOR/NOTE/WARN) 한국어·`[AUTO]` 접두사.
- 프론트 `.js`/`.ts` 쌍 동시 갱신.
- 기존 SPEC-030/027/028 코드 미수정.
