# SPEC-STOCK-035 Progress

## Status: COMPLETE

## Tasks

| Task | Description | Status |
|------|-------------|--------|
| T-001 | 스키마 정의 (3종: HoldingReportRow, PortfolioReportSummary, MonthlySnapshot) | DONE |
| T-002 | DB 모델 + migration 0022 (portfolio_monthly_snapshots 테이블) | DONE |
| T-003 | generate_holding_report_rows 순수 함수 (보유 종목별 손익 행 생성) | DONE |
| T-004 | generate_csv_content 순수 함수 (stdlib csv 전용, scipy 금지) | DONE |
| T-005 | 서비스 레이어 (CSV·JSON·커스텀범위·스냅샷 upsert/list) | DONE |
| T-006 | 라우터 엔드포인트 4종 (GET report, GET summary, POST snapshot, GET snapshots) | DONE |
| T-007 | 프론트엔드 컴포넌트 (PortfolioReportPanel) + API 클라이언트 (portfolio.js/.ts) | DONE |
| T-008 | 테스트 25종 + NFR 검증 | DONE |

## Test Results

```
backend/tests/unit/test_report.py
===================== 25 passed =====================

Coverage Analysis:
✓ scipy 금지 (NFR-001): CSV stdlib 전용 검증
✓ CSV stdlib 전용 (NFR-002): csv.writer, io.StringIO 만 사용 확인
✓ HTTP 404 ownership (REQ-RPT-005): 미소유 포트폴리오 접근 시 404 확인
✓ Snapshot upsert 멱등성 (NFR-004): 동일 기간 재저장 시 중복 없음 확인
✓ 포맷 미지원 400 (REQ-RPT-005): format=pdf 등 미지원 포맷 시 400 거부 확인
```

## Implementation Details

### Backend Files Created

1. **backend/src/stock_picker/portfolio/report.py** (NEW)
   - Pure function `generate_holding_report_rows(holdings, prices, fx_rates, total_value_krw) -> list[HoldingReportRow]`
   - Pure function `generate_csv_content(rows) -> str` (io.StringIO + csv stdlib only)
   - Service functions for CSV report, JSON summary, custom range, snapshot upsert/list

2. **backend/tests/unit/test_report.py** (NEW)
   - 25 tests covering:
     - CSV content generation (format validation, column count, header row)
     - Holding report row calculation (avg price, current price, P&L, return %, weight)
     - JSON summary generation (return rate, holdings summary, dividend summary, benchmark summary)
     - Custom date range parsing ("custom:2026-01-01~2026-06-30")
     - Snapshot upsert/list (uniqueness, duplicate prevention)
     - Ownership validation (404 for non-owner)
     - Format validation (400 for unsupported format)
   - scipy-free, no external CSV library
   - Snapshot upsert idempotency verification

3. **backend/alembic/versions/0022_portfolio_monthly_snapshots.py** (NEW)
   - Migration for `portfolio_monthly_snapshots` table
   - Columns: id, portfolio_id, snapshot_date, total_value_krw, holding_count, created_at, updated_at
   - Indexes on (portfolio_id, snapshot_date) for UNIQUE constraint + query optimization

### Backend Files Modified

1. **backend/src/stock_picker/db/models.py**
   - Added PortfolioMonthlySnapshot ORM model

2. **backend/src/stock_picker/portfolio/schemas.py**
   - Added HoldingReportRow schema (ticker, company_name, avg_buy_price, current_price, evaluation_gain, return_pct, weight_pct, currency)
   - Added PortfolioReportSummary schema (period, return_pct, dividend_summary, benchmark_summary, holdings_count, report_date)
   - Added MonthlySnapshot schema (snapshot_date, total_value_krw, holding_count)

3. **backend/src/stock_picker/portfolio/router.py**
   - Added 4 new endpoints:
     - GET /portfolios/{id}/report?format=csv|json&period=YTD
     - GET /portfolios/{id}/report/summary?benchmark=&period=YTD
     - POST /portfolios/{id}/report/snapshot
     - GET /portfolios/{id}/report/snapshots

### Frontend Files

1. **frontend/src/components/PortfolioReportPanel.js** (NEW)
   - Report download UI (format selector, period selector)
   - Snapshot history view (date list, delete functionality)
   - CSV/JSON format display

2. **frontend/src/api/portfolio.js** (MOD)
   - Added API functions: getReport(), getReportSummary(), createSnapshot(), getSnapshots()

3. **frontend/src/api/portfolio.ts** (MOD)
   - TypeScript versions of portfolio report API functions

4. **frontend/src/pages/Portfolio.js** (MOD)
   - Integrated PortfolioReportPanel in Portfolio page

5. **frontend/src/pages/Portfolio.tsx** (MOD)
   - TypeScript version integration

## Quality Metrics

- **Test Coverage**: 25 tests, all passing
- **scipy Compliance**: NFR-001 enforced (no scipy imports)
- **CSV Library**: NFR-002 enforced (stdlib csv only, no pandas)
- **Ownership Validation**: REQ-RPT-005 enforced (404 for non-owner)
- **Snapshot Idempotency**: NFR-004 enforced (upsert prevents duplicates)
- **Format Validation**: REQ-RPT-005 enforced (400 for unsupported format)

## Acceptance Criteria Met

- [x] CSV 보유 손익표 다운로드 (8열, stdlib csv 전용)
- [x] JSON 통합 요약 리포트 (기간 수익률·배당·벤치마크)
- [x] 월별 포트폴리오 스냅샷 영속화 (upsert, migration 0022)
- [x] 커스텀 날짜 범위 리포트 ("custom:{시작일}~{종료일}" 형식)
- [x] 순수 함수 (scipy 금지, CSV stdlib 전용)
- [x] 25개 단위 테스트 (NFR·REQ 검증)
- [x] 프론트엔드 컴포넌트 + API 클라이언트
- [x] 소유권 검증 (HTTP 404)
- [x] 포맷 미지원 시 400 응답
- [x] Snapshot upsert 멱등성

## Related SPECs

- SPEC-STOCK-034: 벤치마크 비교 (벤치마크 요약 데이터 통합)
- SPEC-STOCK-033: 배당 분석 (배당 요약 데이터 통합)
- SPEC-STOCK-030: 기간별 성과 요약 (기간별 수익률 계산)

## Notes

- CSV 다운로드는 클라이언트가 `fetch(..., {method: 'GET'})` → Blob 변환 → `URL.createObjectURL()` → `<a>` 다운로드로 처리
- 스냅샷은 매달 자동 저장되거나 사용자가 수동으로 저장 가능
- JSON 요약은 배당/벤치마크 데이터가 있을 때만 포함 (선택적)
- 커스텀 기간은 "YTD", "1M", "3M", "6M", "1Y" 표준 기간 외 자유 지정 가능

## Version

- SPEC Version: 1.0.0
- Implementation Version: 0.35.0
- Status: COMPLETE (Ready for merge)
- Last Updated: 2026-06-24
