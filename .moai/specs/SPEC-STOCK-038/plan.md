# SPEC-STOCK-038 Implementation Plan

## Task Breakdown

### T-001: 백엔드 순수 함수 모듈 생성
**파일**: `backend/src/stock_picker/portfolio/dashboard.py` (신규)
**내용**:
- `filter_snapshots_by_range(snapshots, days)` — 기간별 스냅샷 필터 (순수 함수)
- `aggregate_by_sector(holdings)` — 섹터별 집계 (순수 함수)
- `aggregate_by_asset_type(holdings)` — 자산유형별 집계 (순수 함수)
- `ALLOWED_DAYS = {7, 30, 90, 365}` — 허용 기간 상수

### T-002: 스키마 추가
**파일**: `backend/src/stock_picker/portfolio/schemas.py` (수정)
**내용**:
- `ValueDataPoint` — {date: str, total_value_krw: float}
- `ValueSeriesResponse` — {data: list[ValueDataPoint], period_days: int}
- `SectorItem` — {sector: str, value_krw: float, return_pct: float}
- `SectorResponse` — {sectors: list[SectorItem]}
- `AssetTypeItem` — {asset_type: str, value_krw: float, weight_pct: float}
- `AssetAllocationResponse` — {assets: list[AssetTypeItem]}

### T-003: 백엔드 엔드포인트 추가
**파일**: `backend/src/stock_picker/portfolio/router.py` (수정)
**내용**:
- `GET /portfolios/{id}/dashboard/value-series?days=30` — 가치 시계열
- `GET /portfolios/{id}/dashboard/sector-summary` — 섹터 집계
- `GET /portfolios/{id}/dashboard/asset-allocation` — 자산유형 배분
- 모두 `get_portfolio_with_holdings` 소유권 검증 → 없으면 404

### T-004: 단위 테스트 작성 (RED)
**파일**: `backend/tests/unit/test_dashboard_038.py` (신규)
**내용**: 순수 함수 + 소유권 + 기간 검증 테스트 (목표 20~24개)

### T-005: 테스트 통과 (GREEN)
T-001~T-003 구현으로 T-004의 모든 테스트를 통과시킨다.

### T-006: 프론트엔드 차트 컴포넌트 생성
**파일**:
- `frontend/src/components/DashboardValueChart.tsx` + `.js`
- `frontend/src/components/DashboardSectorHeatmap.tsx` + `.js`
- `frontend/src/components/DashboardAssetAllocation.tsx` + `.js`
- `frontend/src/components/DashboardBenchmarkChart.tsx` + `.js` (벤치마크 재사용 래퍼)
**내용**: Recharts 기반, props-driven, 로딩/빈 상태 지원

### T-007: 대시보드 페이지 통합
**파일**: `frontend/src/pages/Dashboard.tsx` + `.js` (신규)
**내용**: 4종 차트 반응형 그리드, 기간 선택 탭(7d/30d/90d/365d), API 연동

### T-008: MX 태그 + Sync
- `dashboard.py` 순수 함수에 `@MX:ANCHOR` (fan_in ≥ 3 예상)
- CHANGELOG.md v0.38.0 추가
- README.md Phase 38 추가
- progress.md 생성

## Dependencies

```
T-001 → T-002 → T-003 → T-004 → T-005
                                    ↓
                              T-006 → T-007 → T-008
```

## Constraints

- 신규 DB 테이블/마이그레이션 없음 (0024 유지)
- scipy 미사용
- HTTP 404 (소유권 위반)
- SELECT-then-write 불필요 (읽기 전용 집계)
