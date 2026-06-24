# SPEC-STOCK-035 압축 참조 (run-phase)

> 포트폴리오 성과 리포트 자동 생성. 030/033/034 결과 집계 + CSV/JSON 다운로드 + 월별 스냅샷.

## 핵심

- **패키지**: `backend/src/stock_picker/portfolio/` (신규 `report.py`).
- **소유권 위반**: 404(403 아님). `get_portfolio_with_holdings()` None → 404.
- **scipy 금지**: numpy + math만. **CSV 외부 라이브러리 금지**: `io.StringIO` + `csv`만.
- **마이그레이션**: 0022(최신 0021=SPEC-032). 테이블 `portfolio_monthly_snapshots`.
- **언어**: 주석·커밋 ko. 커밋 끝 `🗿 MoAI <email@mo.ai.kr>`.

## 순수 함수 (`report.py`)

```python
generate_holding_report_rows(holdings, prices, fx_rates, total_value_krw) -> list[HoldingReportRow]
  # pnl = (현재가-평균단가)*수량; pnl_pct=(현재가/평균단가-1)*100; weight=(현재가*수량)/total*100
generate_csv_content(rows) -> str
  # 헤더: 종목코드,종목명,수량,평균단가(KRW),현재가(KRW),평가손익(KRW),수익률(%),비중(%)
```

## 서비스 5종

- CSV: 소유권 → `calculate_performance` → 손익행 → CSV.
- JSON 요약: 030 `calculate_performance_summary` + 033 `get_dividend_summary`(선택) + 034 `get_benchmark_comparison_service`(benchmark 지정 시) + 손익행 → `PortfolioReportSummary`.
- 커스텀 범위: 030 헬퍼(`_align_close_series`·`_compute_portfolio_values`·`_compute_period_returns`) 재사용 → period="custom:start~end".
- 스냅샷 생성: 소유권 → 총액·수익률·종목수 → `(portfolio_id, month)` upsert(SELECT-then-write).
- 스냅샷 목록: 소유권 → 월 오름차순 조회.

## 스키마 (schemas.py 추가)

- `HoldingReportRow`(ticker·name·quantity·avg_cost·current_price·pnl_amount·pnl_pct·weight_pct).
- `PortfolioReportSummary`(portfolio_id·generated_at·period·total_value_krw·total_return_pct·mdd_pct·holdings·dividend_summary?·benchmark?).
- `MonthlySnapshot`(id·portfolio_id·month·total_value_krw·total_return_pct?·holding_count·created_at, from_attributes).

## DB (0022 + models.py)

- `portfolio_monthly_snapshots`: id·portfolio_id(FK CASCADE)·month String(7)·total_value_krw Float·total_return_pct Float null·holding_count Int·created_at TIMESTAMPTZ.
- `UniqueConstraint("portfolio_id","month", name="uq_snapshot_portfolio_month")`.
- DB-중립 upsert(SELECT-then-write, ON CONFLICT 금지 — SQLite 호환).

## 엔드포인트 (router.py)

- `GET /portfolios/{id}/report?format=csv|json&period=YTD` → StreamingResponse(text/csv, attachment) / 미지원 포맷 오류.
- `GET /portfolios/{id}/report/summary?benchmark=&period=YTD` → PortfolioReportSummary.
- `POST /portfolios/{id}/report/snapshot` Body{month} → MonthlySnapshot.
- `GET /portfolios/{id}/report/snapshots` → list[MonthlySnapshot].
- Depends: get_current_user·get_db_session·get_redis_client.

## REQ 매핑

- RPT-001 CSV 손익표 / RPT-002 JSON 요약 / RPT-003 커스텀 범위 / RPT-004 월별 스냅샷 / RPT-005 소유권 404 + 포맷 검증.
- NFR-001 라이브러리 비도입 / NFR-002 CSV 표준 라이브러리 / NFR-003 순수 함수 / NFR-004 스냅샷 멱등 upsert / NFR-005 50종목 5초.

## 재사용 (수정 금지)

- 030 `performance_summary.py`: 기간·가치 시계열·`_compute_period_returns`.
- 033 `dividend_yield.py`: `get_dividend_summary` / `DividendSummary`.
- 034 `benchmark.py`: `get_benchmark_comparison_service` / `BenchmarkComparison`.
- service.py: `get_portfolio_with_holdings`·`calculate_performance`.

## MX 태그

- ANCHOR: `generate_holding_report_rows`·`PortfolioReportSummary`(+REASON).
- NOTE: 모듈 상단(CSV 표준 라이브러리·KRW 통일·BOM).
- WARN: 스냅샷 upsert(+REASON, 동시성).
- TODO: RED 미구현 마커(GREEN 제거).

## 프론트 (.js/.ts 쌍 동시)

- `api/portfolio.js`(+.ts): apiDownloadReport(blob)·apiGetReportSummary·apiCreateSnapshot·apiGetSnapshots.
- `components/PortfolioReportPanel.js`: 다운로드·요약·스냅샷.
- `pages/Portfolio.js`(+.tsx): 리포트 섹션 통합.
