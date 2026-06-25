# SPEC-STOCK-038 Progress

Status: COMPLETE
Version: v0.38.0
Completed: 2026-06-25

## Tasks

- [x] T-001: dashboard.py 순수 함수 (filter_snapshots_by_range, aggregate_by_sector, aggregate_by_asset_type)
- [x] T-002: schemas.py 스키마 추가 (ValueDataPoint, ValueSeriesResponse, SectorItem 등)
- [x] T-003: router.py 엔드포인트 3개 추가 (value-series, sector-summary, asset-allocation)
- [x] T-004: test_dashboard_038.py 작성 (22개 테스트)
- [x] T-005: 모든 테스트 통과 (22/22)
- [x] T-006: 프론트엔드 차트 컴포넌트 4종 (tsx+js 쌍)
- [x] T-007: Dashboard 페이지 + dashboard API 모듈
- [x] T-008: MX 태그(@MX:ANCHOR × 3) + Sync

## Test Results

- 신규 테스트: 22/22 통과
- 전체 단위 테스트: 985 passed, 8 failed (pre-existing)
- scipy 미사용: 확인
- 소유권 위반 HTTP 404: 확인
- 허용 기간 외 422: 확인

## Implementation Summary

### Backend

**New File**: `backend/src/stock_picker/portfolio/dashboard.py`
- Pure functions for portfolio dashboard aggregation
- `filter_snapshots_by_range(snapshots, num_days)` — 기간별 스냅샷 필터링
- `aggregate_by_sector(holdings, prices)` — 섹터별 평가액·수익률 집계
- `aggregate_by_asset_type(holdings)` — 국내/해외 자산유형별 비중 집계

**Modified**: `backend/src/stock_picker/portfolio/schemas.py`
- New dataclasses: ValueDataPoint, ValueSeriesResponse, SectorItem, SectorResponse, AssetTypeItem, AssetAllocationResponse

**Modified**: `backend/src/stock_picker/portfolio/router.py`
- GET `/dashboard/value-series` — 월별 스냅샷 기반 가치 시계열
- GET `/dashboard/sector-summary` — 섹터별 평가액·수익률 요약
- GET `/dashboard/asset-allocation` — 국내/해외 자산 구성 비중

**New Test**: `backend/tests/unit/test_dashboard_038.py`
- 22 test cases covering all three aggregation functions
- Period filtering (7d/30d/90d/365d)
- Edge cases: empty snapshots, missing prices, zero holdings

### Frontend

**New Components**:
- `DashboardValueChart.{tsx,js}` — LineChart, 기간 탭 선택 (7d/30d/90d/365d)
- `DashboardSectorHeatmap.{tsx,js}` — BarChart, 섹터별 평가액·수익률, 수익률 컬러링
- `DashboardAssetAllocation.{tsx,js}` — PieChart, 국내/해외 비중
- `DashboardBenchmarkChart.{tsx,js}` — 100 기준 재기준화 멀티라인 (SPEC-034 재사용)

**New API**: `frontend/src/api/dashboard.{ts,js}`
- `getValueSeries(portfolioId, days)` — value-series 엔드포인트
- `getSectorSummary(portfolioId)` — sector-summary 엔드포인트
- `getAssetAllocation(portfolioId)` — asset-allocation 엔드포인트

**New Page**: `frontend/src/pages/Dashboard.{tsx,js}`
- Responsive grid layout (desktop 2×2, mobile 1×4)
- Independent loading/empty states per component
- Period selection shared across value/benchmark charts
- Error boundaries and retry logic

## MX Tags

- `@MX:ANCHOR` on `filter_snapshots_by_range` (high fan_in: used by Dashboard, tests)
- `@MX:ANCHOR` on `aggregate_by_sector` (3+ callers: Dashboard, tests, potential reports)
- `@MX:ANCHOR` on `aggregate_by_asset_type` (3+ callers: Dashboard, tests, potential rebalancing)

## Files Changed

### Backend
- `backend/src/stock_picker/portfolio/dashboard.py` (NEW)
- `backend/src/stock_picker/portfolio/schemas.py` (MODIFIED)
- `backend/src/stock_picker/portfolio/router.py` (MODIFIED)
- `backend/tests/unit/test_dashboard_038.py` (NEW)

### Frontend
- `frontend/src/api/dashboard.ts` (NEW)
- `frontend/src/api/dashboard.js` (NEW)
- `frontend/src/components/DashboardValueChart.tsx` (NEW)
- `frontend/src/components/DashboardValueChart.js` (NEW)
- `frontend/src/components/DashboardSectorHeatmap.tsx` (NEW)
- `frontend/src/components/DashboardSectorHeatmap.js` (NEW)
- `frontend/src/components/DashboardAssetAllocation.tsx` (NEW)
- `frontend/src/components/DashboardAssetAllocation.js` (NEW)
- `frontend/src/components/DashboardBenchmarkChart.tsx` (NEW)
- `frontend/src/components/DashboardBenchmarkChart.js` (NEW)
- `frontend/src/pages/Dashboard.tsx` (NEW)
- `frontend/src/pages/Dashboard.js` (NEW)
