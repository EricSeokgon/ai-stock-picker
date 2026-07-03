# SPEC-STOCK-038 Compact Reference

## 목표

포트폴리오 가치 시계열·섹터 히트맵·자산유형 배분·벤치마크 비교 4종 차트 대시보드.
신규 DB 테이블 없음 (0024 유지). 기간 선택 7d/30d/90d/365d.

## REQ 요약 (REQ-DASH-*)

| REQ | 내용 | 패턴 |
|-----|------|------|
| 001 | 기간별 월별 스냅샷 시계열 데이터 | Event-driven |
| 002 | 섹터별 평가액·수익률 집계 | Event-driven |
| 003 | 자산유형(국내/해외)별 비중 집계 | Event-driven |
| 004 | 벤치마크 비교 데이터 (SPEC-034 재사용) | Ubiquitous |
| 005 | 4종 차트 반응형 그리드 렌더 | Event-driven |
| 006 | 기간 전환 시 가치·벤치마크 차트 갱신 | Event-driven |
| 007 | 빈 데이터 → 빈 상태 안내 (오류 아님) | Unwanted |
| 008 | 로딩 중 로딩 표시 | Event-driven |
| 009 | 미소유 포트폴리오 → 자원 부재로 응답 | Unwanted |
| NFR-001 | scipy 금지 | Unwanted |
| NFR-002 | 집계 로직 순수 함수 분리 | Ubiquitous |
| NFR-003 | 소유권 위반 → 존재 여부 비노출 | Unwanted |
| NFR-004 | 차트 컴포넌트 props 구동 | Ubiquitous |
| NFR-005 | 허용되지 않은 기간 값 거부 | Unwanted |

## 핵심 제약

- 신규 DB 테이블/마이그레이션 없음 (0024 유지)
- scipy 미사용 (numpy + math 표준만)
- 소유권 위반 HTTP 404 (403 아님)
- 섹터 미분류 → "기타/해외"
- 허용 기간: {7, 30, 90, 365} 이외 거부

## 구현 파일 목록

### 신규 (backend)
- `backend/src/stock_picker/portfolio/dashboard.py` — 순수 함수 (filter_snapshots_by_range, aggregate_by_sector, aggregate_by_asset_type)
- `backend/tests/unit/test_dashboard_038.py` — 단위 테스트 (목표 20~24개)

### 수정 (backend)
- `backend/src/stock_picker/portfolio/schemas.py` — ValueDataPoint, ValueSeriesResponse, SectorItem, SectorResponse, AssetTypeItem, AssetAllocationResponse
- `backend/src/stock_picker/portfolio/router.py` — GET /portfolios/{id}/dashboard/value-series, /sector-summary, /asset-allocation

### 신규 (frontend)
- `frontend/src/components/DashboardValueChart.{tsx,js}`
- `frontend/src/components/DashboardSectorHeatmap.{tsx,js}`
- `frontend/src/components/DashboardAssetAllocation.{tsx,js}`
- `frontend/src/components/DashboardBenchmarkChart.{tsx,js}`
- `frontend/src/pages/Dashboard.{tsx,js}`
- `frontend/src/api/dashboard.{ts,js}`

## API 엔드포인트

```
GET /portfolios/{id}/dashboard/value-series?days=30
→ ValueSeriesResponse {data: [{date, total_value_krw}], period_days}

GET /portfolios/{id}/dashboard/sector-summary
→ SectorResponse {sectors: [{sector, value_krw, return_pct}]}

GET /portfolios/{id}/dashboard/asset-allocation
→ AssetAllocationResponse {assets: [{asset_type, value_krw, weight_pct}]}
```

## 의존 SPEC

- SPEC-035: portfolio_monthly_snapshots (가치 시계열 원천)
- SPEC-034: GET /benchmark/chart (벤치마크 차트 재사용)
- SPEC-028: market 필드 (자산유형 분류)
- SPEC-017: get_portfolio_with_holdings (소유권 검증)
