---
id: "SPEC-STOCK-035"
version: "0.2.0"
status: "draft"
created_at: "2026-06-24"
updated_at: "2026-06-24"
author: "ircp"
priority: "medium"
issue_number: 0
labels: ["portfolio", "report", "csv", "snapshot", "backend", "frontend"]
---

# SPEC-STOCK-035: 포트폴리오 성과 리포트 자동 생성 (Portfolio Performance Report Generation)

> Roadmap 성과 평가(performance evaluation) 계열 통합 SPEC. SPEC-030(기간별 성과)·033(배당 수익률)·034(벤치마크 비교)가 각각 산출하는 데이터를 **다운로드 가능한 리포트**(CSV 보유 종목 손익표·JSON 구조화 요약)로 묶어 제공한다. 추가로 월말 시점 스냅샷을 영속화하고 커스텀 날짜 범위 리포트를 지원한다. 신규 지표는 계산하지 않으며, 기존 서비스 결과를 집계·직렬화한다.

## HISTORY

| 버전 | 날짜 | 변경 내용 |
|------|------|-----------|
| 0.1.0 | 2026-06-24 | 최초 작성. SPEC-030/033/034 서비스 결과를 집계하는 리포트 레이어 정의. 신규 핵심: CSV 보유 손익표 스트리밍·JSON 통합 요약·커스텀 날짜 범위·월별 스냅샷 영속화. 신규 엔드포인트 4종(`/report`·`/report/summary`·`/report/snapshot`·`/report/snapshots`). 신규 테이블·마이그레이션(0022) `portfolio_monthly_snapshots`. REQ-RPT-001~005 + NFR-001~005. |
| 0.2.0 | 2026-06-24 | plan-auditor v1 지적사항 반영 — acceptance.md §1 EARS 주어 10건 수정(아티팩트 주어 → "THE 시스템 SHALL" 패턴 일관화). |

> **REQ 접두사 설계 원칙**: 본 SPEC은 `REQ-RPT-*`(RePorT) 접두사를 사용한다. 기존 SPEC 접두사(OPT/RISK/FA/PBT/PS/PAL/RBA/DVY/BMK)와 충돌하지 않는다.

> **번호 체계**: REQ-RPT-001~005 연속 번호. NFR은 REQ-RPT-NFR-001~005.

---

## 1. 개요 (Overview)

### 1.1 기능 설명

투자자는 자신의 포트폴리오 성과를 외부에서 보관·공유·세무 신고에 활용하기 위해 **파일로 내려받기**를 원한다. 현재 시스템은 성과(030)·배당(033)·벤치마크(034)를 각각의 API로 화면에 표시할 뿐, 다운로드 가능한 통합 리포트가 없다.

SPEC-035는 이 간극을 메운다.

- **CSV 보유 종목 손익표** — 종목별 한 줄(종목코드·종목명·수량·평균단가·현재가·평가손익·수익률·비중)로 구성된 첨부 파일.
- **JSON 통합 요약** — 포트폴리오 요약·기간 성과·배당 요약·벤치마크 비교를 한 문서로 묶은 구조화 데이터.
- **커스텀 날짜 범위** — 표준 기간(YTD/1M/...) 대신 임의 시작일~종료일의 수익률·보유 상세.
- **월별 스냅샷** — 월말 시점의 총 평가액·기간 수익률·보유 종목 수를 영속 저장하여 시계열 추적의 기반을 제공.

### 1.2 동기 (Motivation)

- **데이터 이동성(portability)**: 화면 표시만으로는 회계·세무·기록 보관에 부적합하다. CSV/JSON은 스프레드시트·외부 분석 도구로 이동 가능하다.
- **통합 관점**: 성과·배당·벤치마크가 분산된 API로 존재한다. 한 번의 요청으로 묶인 요약 문서가 의사결정 효율을 높인다.
- **시계열 추적의 기반**: 월별 스냅샷을 누적하면 향후 성과 추이 분석·차트의 데이터 원천이 된다.

본 SPEC은 정보 제공·기록 보관 지원이며, 실제 매매·실시간 알림을 하지 않는다.

### 1.3 목표 (Goals)

- 포트폴리오 보유 종목별 손익을 한 줄씩 담은 다운로드 가능한 CSV 파일을 생성한다.
- 포트폴리오 요약·기간 성과·배당 요약·벤치마크 비교를 묶은 구조화 JSON 요약을 제공한다.
- 커스텀 시작일·종료일이 주어지면 해당 범위의 포트폴리오 수익률·보유 상세를 산출한다.
- 월말 시점 총 평가액·기간 수익률·보유 종목 수를 영속 저장하고 동일 월 중복을 방지한다.
- 핵심 변환(손익행 생성·CSV 직렬화)을 DB·외부 API 없이 테스트 가능한 순수 함수로 분리한다.
- 프론트엔드에 리포트 다운로드·요약·스냅샷 UI를 추가한다.

### 1.4 기술 스택 (확정·재사용)

FastAPI + PostgreSQL(asyncpg) + SQLAlchemy + Redis + React + JavaScript/TypeScript. 리포트 데이터는 SPEC-030/033/034 서비스 결과를 **집계**하여 구성한다. CSV 직렬화는 표준 라이브러리(`io` + `csv`)만 사용하며 외부 CSV 라이브러리를 도입하지 않는다. 수치 보조 계산은 `numpy` + `math`만 사용한다(scipy 미사용). 월별 스냅샷 영속화를 위해 신규 테이블·마이그레이션(0022)을 도입한다.

---

## 2. 범위 (Scope)

### 2.1 포함 (In Scope)

- 신규 순수 함수 모듈 `portfolio/report.py`:
  - 보유 손익행 생성(순수 함수) — 보유·가격·환율·총액으로부터 종목별 손익행 목록 산출.
  - CSV 직렬화(순수 함수) — 손익행 목록을 한국어 헤더의 CSV 문자열로 변환(표준 라이브러리만 사용).
- 신규 서비스 오케스트레이션 — 소유권 확인, 030/033/034 서비스 결과 집계, 커스텀 범위 산출, 월별 스냅샷 upsert·조회.
- 신규 Pydantic 스키마(`portfolio/schemas.py`): `HoldingReportRow`, `PortfolioReportSummary`, `MonthlySnapshot`.
- 신규 DB 테이블 `portfolio_monthly_snapshots` + 마이그레이션 0022 + ORM 모델.
- 신규 엔드포인트 4개(`portfolio/router.py`):
  - `GET /portfolios/{portfolio_id}/report`(CSV 첨부 다운로드)
  - `GET /portfolios/{portfolio_id}/report/summary`(JSON 통합 요약)
  - `POST /portfolios/{portfolio_id}/report/snapshot`(월별 스냅샷 생성·갱신)
  - `GET /portfolios/{portfolio_id}/report/snapshots`(스냅샷 목록 조회)
- 프론트엔드 리포트 패널 컴포넌트 + API 클라이언트 확장(`.js`/`.ts` 쌍).
- 단위 테스트(커버리지 85% 이상).

### 2.2 제외 (What NOT to Build)

> [HARD] 본 SPEC은 다음을 **빌드하지 않는다**.

- **신규 지표 계산**: 기간 수익률·MDD·배당 수익률·알파·베타는 SPEC-030/033/034가 산출한다. 035는 이를 *집계·직렬화*할 뿐 재계산·재정의하지 않으며, 030/033/034의 엔드포인트·스키마를 변경하지 않는다.
- **PDF·Excel(xlsx)·HTML 리포트**: 본 SPEC의 출력 포맷은 CSV와 JSON으로 한정한다. PDF 렌더링·바이너리 Excel·HTML 템플릿은 제외한다(요청 포맷 외 오류 반환).
- **예약·자동 발송 리포트**: 리포트는 사용자 요청 시점에 즉시 생성한다. 스케줄러로 정기 생성·이메일 발송하지 않는다.
- **자동 월별 스냅샷 적재**: 월별 스냅샷은 명시적 요청으로만 생성·갱신한다. 매월 말 자동 cron 적재는 제외한다(향후 별도 SPEC).
- **차트 렌더링·이미지 생성**: 리포트는 데이터(CSV/JSON)만 제공한다. 서버 측 차트 이미지·그래프 PNG 생성은 제외한다.
- **다중 포트폴리오 합산 리포트**: 리포트는 단일 포트폴리오 단위로 생성한다. 여러 포트폴리오를 통합한 집계 리포트는 제외한다.
- **스냅샷 이력 기반 추세 분석**: 035는 스냅샷을 *저장·조회*만 한다. 누적 스냅샷으로부터의 추세선·성장률 산출은 제외한다(향후 별도 SPEC).
- **가격 데이터 미확보 시 추측**: 보유 종목 현재가를 확보할 수 없으면 기존 서비스(030/service.py) 관례대로 처리(매수가 대체·수익률 0)하며, 임의 값을 단언하지 않는다.

---

## 3. 기능 요구사항 (EARS Requirements)

### REQ-RPT-001 (Event-driven) — CSV 보유 손익 리포트

WHEN 사용자가 포트폴리오의 CSV 리포트를 요청하면 THE 시스템 SHALL 보유 종목마다 한 행을 담은 다운로드 가능한 파일을 생성하며, 각 행은 종목 코드·종목명·수량·평균 단가·현재가·평가 손익 금액·수익률·포트폴리오 비중을 포함한다.

### REQ-RPT-002 (Event-driven) — JSON 통합 요약 리포트

WHEN 사용자가 포트폴리오의 JSON 리포트를 요청하면 THE 시스템 SHALL 포트폴리오 요약·각 표준 기간의 성과·배당 요약·벤치마크 비교를 담은 구조화 문서를 반환한다.

### REQ-RPT-003 (Event-driven) — 커스텀 날짜 범위

WHEN 커스텀 시작일과 종료일이 제공되면 THE 시스템 SHALL 표준 기간 대신 해당 날짜 범위에 대한 포트폴리오 수익률과 보유 상세를 산출한다.

### REQ-RPT-004 (Event-driven) — 월별 스냅샷

WHEN 시스템이 포트폴리오에 대한 월별 스냅샷을 생성하면 THE 시스템 SHALL 요청된 월의 말 시점 기준 포트폴리오 총 평가액·기간 수익률·보유 종목 수를 저장한다.

### REQ-RPT-005 (Unwanted) — 소유권 확인 및 포맷 검증

IF 요청 사용자가 소유하지 않은 포트폴리오에 대해 리포트를 요청하면 THEN THE 시스템 SHALL 존재하지 않는 포트폴리오에 대한 요청과 동일하게 응답하여 소유권 정보를 노출하지 않는다. IF 지원하지 않는 리포트 포맷이 요청되면 THEN THE 시스템 SHALL 지원되는 포맷을 안내하는 오류를 반환한다.

---

## 4. 비기능 요구사항 (NFR)

- **REQ-RPT-NFR-001 (외부 최적화 라이브러리 비도입)**: THE 시스템 SHALL 본 SPEC 신규 수치 보조 계산을 표준 수학 연산 및 프로젝트 승인 수치 라이브러리만으로 구현하며, 새로운 외부 통계·최적화 라이브러리를 도입하지 않는다.
- **REQ-RPT-NFR-002 (CSV 표준 라이브러리 전용)**: THE 시스템 SHALL CSV 직렬화를 언어 표준 라이브러리만으로 수행하며, 별도의 외부 CSV 처리 라이브러리를 도입하지 않는다.
- **REQ-RPT-NFR-003 (순수 함수 테스트성)**: THE 시스템의 핵심 손익행 생성·CSV 직렬화 컴포넌트 SHALL 데이터베이스·외부 캐시·외부 네트워크 호출에 대한 의존 없이 입력값만으로 결정적 결과를 반환한다.
- **REQ-RPT-NFR-004 (월별 스냅샷 멱등성)**: IF 동일한 포트폴리오와 동일한 월에 대해 스냅샷 생성이 다시 요청되면, THEN THE 시스템 SHALL 중복 레코드를 생성하지 않고 기존 레코드를 갱신하여 포트폴리오·월 조합당 단일 레코드를 유지한다.
- **REQ-RPT-NFR-005 (리포트 생성 응답성)**: THE 시스템 SHALL 최대 50개 보유 종목을 가진 포트폴리오에 대해 리포트 생성을 5초 이내에 완료한다.

---

## 5. 기술 접근 방식 (Technical Approach)

### 5.1 순수 함수 (`portfolio/report.py`)

```python
def generate_holding_report_rows(
    holdings: list[dict],            # [{ticker, name, quantity, avg_cost, current_price}, ...]
    prices: dict[str, float],        # {ticker: current_price_krw}
    fx_rates: dict[str, float],      # {ticker: fx_rate}  (KRX=1.0)
    total_value_krw: float,
) -> list[HoldingReportRow]: ...

def generate_csv_content(rows: list[HoldingReportRow]) -> str: ...
    # 헤더: 종목코드,종목명,수량,평균단가(KRW),현재가(KRW),평가손익(KRW),수익률(%),비중(%)
```

#### 5.1.1 `generate_holding_report_rows` 알고리즘

1. 각 보유 종목에 대해 현재가(KRW)·평균단가(KRW)를 확정(해외 종목은 환율 적용).
2. 평가손익 금액 = `(현재가 - 평균단가) × 수량`.
3. 수익률(%) = `(현재가 / 평균단가 - 1) × 100`(평균단가 0이면 0).
4. 비중(%) = `(현재가 × 수량) / total_value_krw × 100`(총액 0이면 0).
5. `HoldingReportRow` 목록 반환. 순수 함수 — DB·가격 조회를 하지 않는다(REQ-RPT-NFR-003).

#### 5.1.2 `generate_csv_content` 알고리즘

1. `io.StringIO` 버퍼 생성.
2. `csv.writer`로 한국어 헤더 1행 + 손익행 N행 작성.
3. 문자열 반환. Excel 한국어 호환을 위해 UTF-8 BOM 프리픽스를 응답 인코딩 단계에서 부착(접근 방식 결정).

> **설계 결정 노트(CSV 라이브러리)**: REQ-RPT-NFR-002 구현 시 `io.StringIO` + `csv` 표준 모듈만 사용하고 외부 CSV 라이브러리를 import하지 않는다.
> **설계 결정 노트(통화)**: 모든 금액 컬럼은 KRW 단위로 통일한다. 해외(USD) 종목은 `fx_rate`로 KRW 환산 후 표기한다(SPEC-028 관행).

### 5.2 서비스 오케스트레이션

```
CSV 리포트 서비스(portfolio_id, user_id, db, redis, period):
  1. get_portfolio_with_holdings(db, portfolio_id, user_id)  # None → 404 (REQ-RPT-005)
  2. calculate_performance(db, portfolio_id, user_id, redis)  # 종목별 현재가(KRW)·수익률·총액 (SPEC-017/028 재사용)
  3. generate_holding_report_rows(holdings, prices, fx_rates, total_value_krw)
  4. generate_csv_content(rows) → 첨부 파일 스트림 응답

JSON 요약 서비스(portfolio_id, user_id, db, redis, benchmark, period):
  1. 소유권 확인 (404)
  2. calculate_performance_summary(...) (SPEC-030)  → 기간 성과·MDD
  3. get_dividend_summary(...) (SPEC-033)           → 배당 요약 (선택)
  4. get_benchmark_comparison_service(...) (SPEC-034) → 벤치마크 비교 (benchmark 지정 시)
  5. generate_holding_report_rows(...)              → 보유 상세
  6. RETURN PortfolioReportSummary

커스텀 범위 서비스(portfolio_id, user_id, db, redis, start, end):
  1. 소유권 확인 (404)
  2. 종목별 가격 시계열 조회(start~end) → 가중 가치 시계열 산출 (SPEC-030 헬퍼 재사용)
  3. _compute_period_returns(values) → 범위 수익률·MDD
  4. generate_holding_report_rows(...) → 보유 상세
  5. RETURN PortfolioReportSummary (period="custom:start~end")

월별 스냅샷 생성 서비스(portfolio_id, user_id, db, redis, month):
  1. 소유권 확인 (404)
  2. 총 평가액·해당 월 기간 수익률·보유 종목 수 산출
  3. (portfolio_id, month) upsert → 존재 시 UPDATE, 없으면 INSERT (REQ-RPT-NFR-004)
  4. RETURN MonthlySnapshot

월별 스냅샷 목록 서비스(portfolio_id, user_id, db):
  1. 소유권 확인 (404)
  2. (portfolio_id) 스냅샷 목록 조회 (월 오름차순)
  3. RETURN list[MonthlySnapshot]
```

> **설계 결정 노트(소유권 응답)**: REQ-RPT-005 구현 시 `get_portfolio_with_holdings()` None → `404 Not Found`(코드베이스 관례, 403 아님).
> **설계 결정 노트(포맷 검증)**: 지원 포맷은 CSV·JSON 2종. `format` 쿼리 파라미터가 둘 중 하나가 아니면 지원 포맷을 안내하는 오류를 반환한다(REQ-RPT-005 후반).
> **설계 결정 노트(데이터 집계)**: 035 서비스는 030/033/034 서비스를 호출해 결과를 집계하며, 수익률·MDD·알파·베타·배당률을 재계산하지 않는다(§2.2 제외).

### 5.3 스키마 (`portfolio/schemas.py`)

```python
class HoldingReportRow(BaseModel):
    ticker: str
    name: str
    quantity: float
    avg_cost: float            # KRW
    current_price: float       # KRW (해외 종목은 환율 환산)
    pnl_amount: float          # KRW
    pnl_pct: float             # %
    weight_pct: float          # 포트폴리오 총액 대비 비중(%)

class PortfolioReportSummary(BaseModel):
    portfolio_id: int
    generated_at: datetime
    period: str
    total_value_krw: float
    total_return_pct: float
    mdd_pct: Optional[float]
    holdings: list[HoldingReportRow]
    dividend_summary: Optional[DividendSummary]   # SPEC-033
    benchmark: Optional[BenchmarkComparison]      # SPEC-034

class MonthlySnapshot(BaseModel):
    id: int
    portfolio_id: int
    month: str                 # "YYYY-MM"
    total_value_krw: float
    total_return_pct: Optional[float]
    holding_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

> **명명 충돌 회피**: 035 스키마(`HoldingReportRow`/`PortfolioReportSummary`/`MonthlySnapshot`)는 030/033/034 스키마와 이름이 분리되어 충돌하지 않는다. `dividend_summary`·`benchmark` 필드는 033/034 스키마를 임베드한다.

### 5.4 DB 테이블·마이그레이션 (0022)

테이블 `portfolio_monthly_snapshots`:

| 컬럼 | 타입 | 비고 |
|------|------|------|
| `id` | Integer PK autoincrement | |
| `portfolio_id` | Integer FK → portfolios.id (CASCADE) | |
| `month` | String(7) | "YYYY-MM" |
| `total_value_krw` | Float | |
| `total_return_pct` | Float nullable | 산출 불가 시 NULL |
| `holding_count` | Integer | |
| `created_at` | TIMESTAMP(timezone=True) server_default now() | |

- Unique 제약: `UniqueConstraint("portfolio_id", "month", name="uq_snapshot_portfolio_month")` (REQ-RPT-NFR-004).
- 인덱스: `(portfolio_id, month)` 조회 최적화.

> **설계 결정 노트(마이그레이션 리비전)**: 최신 리비전은 `0021_rebalancing_plans.py`(SPEC-032). 035는 `0022_portfolio_monthly_snapshots.py`(`revision="0022"`, `down_revision="0021"`).
> **설계 결정 노트(upsert 이식성)**: SQLite 테스트 호환을 위해 `(portfolio_id, month)`로 SELECT 후 존재 시 UPDATE, 없으면 INSERT하는 DB-중립 upsert를 사용한다. `ON CONFLICT` 등 방언 종속 구문을 사용하지 않는다(`RebalancingPlan`·`PortfolioAlert` 관례).

### 5.5 라우터 (`portfolio/router.py`)

```
GET /portfolios/{portfolio_id}/report?format=<csv|json, 기본 csv>&period=<YTD|1M|3M|6M|1Y, 기본 YTD>
  소유권 불일치 → 404 (REQ-RPT-005)
  미지원 포맷 → 오류 (REQ-RPT-005)
  Response(csv): 첨부 파일 스트림(text/csv, Content-Disposition: attachment)

GET /portfolios/{portfolio_id}/report/summary?benchmark=<KOSPI|...,선택>&period=<YTD|...,기본 YTD>
  소유권 불일치 → 404
  Response: PortfolioReportSummary (JSON)

POST /portfolios/{portfolio_id}/report/snapshot
  Body: {month: "YYYY-MM"}
  소유권 불일치 → 404
  Response: MonthlySnapshot

GET /portfolios/{portfolio_id}/report/snapshots
  소유권 불일치 → 404
  Response: list[MonthlySnapshot]
```

기존 `Depends(get_current_user)` + `get_db_session` + `get_redis_client` 패턴 재사용. `report` 접두 경로는 기존 엔드포인트와 충돌 없음. CSV 첨부는 `StreamingResponse`(`text/csv`) + `Content-Disposition: attachment` 헤더로 반환한다.

### 5.6 프론트엔드

- `frontend/src/components/PortfolioReportPanel.js` — CSV 다운로드 버튼 + JSON 요약 카드 + 월별 스냅샷 목록·생성 버튼.
- `frontend/src/api/portfolio.js`(+`.ts`) — `apiDownloadReport`(blob)·`apiGetReportSummary`·`apiCreateSnapshot`·`apiGetSnapshots`.
- `frontend/src/pages/Portfolio.js`(+`.tsx`) — 리포트 섹션 통합(기존 섹션 보존).

---

## 6. Delta Markers (변경 영향 분석)

| 마커 | 파일 | 내용 |
|------|------|------|
| [EXISTING] | `backend/src/stock_picker/portfolio/performance_summary.py` | 기간 정의·가치 시계열·`_compute_period_returns` 재사용(수정 없음) |
| [EXISTING] | `backend/src/stock_picker/portfolio/dividend_yield.py` | `get_dividend_summary` 재사용(수정 없음) |
| [EXISTING] | `backend/src/stock_picker/portfolio/benchmark.py` | `get_benchmark_comparison_service` 재사용(수정 없음) |
| [EXISTING] | `backend/src/stock_picker/portfolio/service.py` | `get_portfolio_with_holdings`·`calculate_performance` 재사용(수정 없음) |
| [NEW] | `backend/src/stock_picker/portfolio/report.py` | 순수 함수 2종 + 서비스 오케스트레이션 5종 |
| [MODIFY] | `backend/src/stock_picker/portfolio/schemas.py` | `HoldingReportRow`·`PortfolioReportSummary`·`MonthlySnapshot` 추가 |
| [MODIFY] | `backend/src/stock_picker/portfolio/router.py` | report·report/summary·report/snapshot·report/snapshots 엔드포인트 4종 추가 |
| [MODIFY] | `backend/src/stock_picker/db/models.py` | `PortfolioMonthlySnapshot` ORM 모델 추가 |
| [NEW] | `backend/alembic/versions/0022_portfolio_monthly_snapshots.py` | 스냅샷 테이블·Unique 제약·인덱스 마이그레이션 |
| [NEW] | `backend/tests/unit/test_report.py` | 순수 함수·서비스 단위 테스트(커버리지 85%+) |
| [NEW] | `frontend/src/components/PortfolioReportPanel.js` | 리포트 다운로드·요약·스냅샷 패널 |
| [MODIFY] | `frontend/src/api/portfolio.js` | 리포트 API 클라이언트 추가 |
| [MODIFY] | `frontend/src/api/portfolio.ts` | 리포트 API 클라이언트 추가 |
| [MODIFY] | `frontend/src/pages/Portfolio.js` | 리포트 섹션 통합 |
| [MODIFY] | `frontend/src/pages/Portfolio.tsx` | 리포트 섹션 통합 |

> **DB 마이그레이션 도입**: 월별 스냅샷 영속화를 위해 신규 테이블·마이그레이션 0022가 **필요**하다. 최신 리비전 `0021_rebalancing_plans.py`(SPEC-032)를 `down_revision`으로 둔다.

---

## 7. 의존성 (Dependencies)

- **SPEC-030**(성과 요약): 기간 정의·가치 시계열 산출(`_compute_period_dates`·`_align_close_series`·`_compute_portfolio_values`·`_compute_period_returns`)·`calculate_performance_summary` 재사용. 030 코드(엔드포인트·스키마)는 수정·제거하지 않는다.
- **SPEC-033**(배당 수익률): `get_dividend_summary`·`DividendSummary` 임베드(수정 없음).
- **SPEC-034**(벤치마크 비교): `get_benchmark_comparison_service`·`BenchmarkComparison` 임베드(수정 없음).
- **SPEC-028**(해외 자산 지원): `PortfolioHolding.market`/`currency`, `_fetch_foreign_price`, `fx_rate` — KRW 환산.
- **SPEC-017**(포트폴리오 성과): `get_portfolio_with_holdings` 소유권, `calculate_performance` 현재가·수익률 산출.
- **SPEC-032**(리밸런싱): `0021_rebalancing_plans.py` 최신 리비전 — 0022의 `down_revision`. ORM 모델 `RebalancingPlan` 패턴 모방.

---

## 8. MX 태그 계획 (MX Tag Plan)

코드 주석 언어는 한국어(`language.yaml` `code_comments: ko`).

- **@MX:ANCHOR** (`report.py`의 `generate_holding_report_rows` 순수 함수 진입점):
  - 사유: 서비스 오케스트레이션 다수 + 단위 테스트에서 fan_in ≥ 3 예상. `@MX:REASON` 필수.
- **@MX:ANCHOR** (`PortfolioReportSummary` 응답 스키마):
  - 사유: router·service·프론트 API 래퍼·테스트 3곳 이상 참조. `@MX:REASON` 필수.
- **@MX:NOTE** (`report.py` 모듈 상단):
  - CSV 표준 라이브러리(`io`/`csv`) 전용·외부 CSV 라이브러리 금지, 금액 KRW 단위 통일·UTF-8 BOM 사유 명시.
- **@MX:WARN** (월별 스냅샷 upsert 분기):
  - DB-중립 SELECT-then-write upsert·동시 요청 시 경합 주의. `@MX:REASON` 필수.
- **@MX:TODO** (RED 단계):
  - 미구현 순수 함수·오케스트레이션 임시 마커. GREEN 단계에서 제거.

태그 설명은 한국어로 작성하고, 에이전트 생성 태그는 `[AUTO]` 접두사를 포함한다.

---

## 9. 수용 기준 (Acceptance Criteria)

상세 BDD 시나리오·EARS 수용 기준은 [acceptance.md](acceptance.md) 참조. 작업 분해는 [plan.md](plan.md), 압축 참조는 [spec-compact.md](spec-compact.md) 참조.
