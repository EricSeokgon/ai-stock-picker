# SPEC-STOCK-035 구현 계획 (Implementation Plan)

> 작업 분해(T-001~T-008). 시간 추정 없음 — 우선순위·의존 순서로만 기술한다.
> 방법론: TDD(RED-GREEN-REFACTOR) 권장. 순수 함수 우선 테스트.

---

## 마일스톤 개요

| 마일스톤 | 작업 | 우선순위 |
|----------|------|----------|
| M1: 데이터 계약 | T-001(스키마) · T-002(마이그레이션·모델) | High |
| M2: 순수 함수 | T-003(손익행 생성) · T-004(CSV 직렬화) | High |
| M3: 서비스 | T-005(CSV·JSON·커스텀 범위) · T-006(스냅샷 upsert·목록) | High |
| M4: API | T-007(엔드포인트 4종) | High |
| M5: 프론트 | T-008(`.js`/`.ts` 쌍) | Medium |

---

## T-001 — Pydantic 스키마 추가 [High]

- 파일: `backend/src/stock_picker/portfolio/schemas.py` [MODIFY]
- 내용:
  - `HoldingReportRow`(ticker·name·quantity·avg_cost·current_price·pnl_amount·pnl_pct·weight_pct).
  - `PortfolioReportSummary`(portfolio_id·generated_at·period·total_value_krw·total_return_pct·mdd_pct·holdings·dividend_summary·benchmark). `DividendSummary`·`BenchmarkComparison` 임베드.
  - `MonthlySnapshot`(id·portfolio_id·month·total_value_krw·total_return_pct·holding_count·created_at). `ConfigDict(from_attributes=True)`.
  - `PortfolioReportSummary`에 `@MX:ANCHOR` + `@MX:REASON`.
- 의존: 없음.
- 완료 조건: 스키마 import·검증 테스트 통과, 030/033/034 스키마와 명명 충돌 없음.

## T-002 — DB 마이그레이션·ORM 모델 [High]

- 파일: `backend/alembic/versions/0022_portfolio_monthly_snapshots.py` [NEW], `backend/src/stock_picker/db/models.py` [MODIFY]
- 내용:
  - 테이블 `portfolio_monthly_snapshots`: id·portfolio_id(FK CASCADE)·month String(7)·total_value_krw Float·total_return_pct Float nullable·holding_count Integer·created_at TIMESTAMPTZ.
  - `UniqueConstraint("portfolio_id", "month", name="uq_snapshot_portfolio_month")`.
  - 인덱스 `(portfolio_id, month)`.
  - `revision="0022"`, `down_revision="0021"`.
  - ORM 모델 `PortfolioMonthlySnapshot`(Base 상속, `RebalancingPlan` 패턴 모방).
- 의존: 없음.
- 완료 조건: `alembic upgrade head` 성공(SQLite·Postgres), Unique 제약 동작 확인.

## T-003 — 순수 함수: 손익행 생성 [High]

- 파일: `backend/src/stock_picker/portfolio/report.py` [NEW]
- 내용:
  - `generate_holding_report_rows(holdings, prices, fx_rates, total_value_krw)` → `list[HoldingReportRow]`.
  - 평가손익·수익률·비중 산출, 평균단가/총액 0 가드.
  - `@MX:ANCHOR` + `@MX:REASON`(fan_in ≥ 3).
  - 모듈 상단 `@MX:NOTE`(CSV 표준 라이브러리 전용·금액 KRW·BOM 사유).
- 의존: T-001.
- 완료 조건: DB·네트워크 없이 단위 테스트 통과(REQ-RPT-NFR-003), 엣지 E-3·E-4·E-5 처리.

## T-004 — 순수 함수: CSV 직렬화 [High]

- 파일: `backend/src/stock_picker/portfolio/report.py` [MODIFY]
- 내용:
  - `generate_csv_content(rows)` → `str`. `io.StringIO` + `csv.writer`.
  - 한국어 헤더: `종목코드,종목명,수량,평균단가(KRW),현재가(KRW),평가손익(KRW),수익률(%),비중(%)`.
  - 외부 CSV 라이브러리 미사용(REQ-RPT-NFR-002).
- 의존: T-003.
- 완료 조건: 헤더·행 수·구분자 단위 테스트 통과, 빈 목록(E-1)·한국어(E-12) 처리.

## T-005 — 서비스: CSV·JSON 요약·커스텀 범위 [High]

- 파일: `backend/src/stock_picker/portfolio/report.py` [MODIFY]
- 내용:
  - CSV 리포트 서비스: 소유권 확인 → `calculate_performance` → 손익행 생성 → CSV 문자열.
  - JSON 요약 서비스: 030 `calculate_performance_summary` + 033 `get_dividend_summary`(선택) + 034 `get_benchmark_comparison_service`(benchmark 지정 시) + 손익행 → `PortfolioReportSummary`.
  - 커스텀 범위 서비스: 030 헬퍼 재사용(가격 시계열·가치 산출·`_compute_period_returns`) → 범위 수익률·MDD → `PortfolioReportSummary`(period="custom:...").
  - 소유권 None → 404(REQ-RPT-005).
- 의존: T-003, T-004.
- 완료 조건: 030/033/034 결과 집계 동작, 소유권 404·미지원 포맷 처리, 엣지 E-2·E-6·E-7·E-8·E-9.

## T-006 — 서비스: 월별 스냅샷 upsert·목록 [High]

- 파일: `backend/src/stock_picker/portfolio/report.py` [MODIFY]
- 내용:
  - 스냅샷 생성 서비스: 소유권 확인 → 총액·기간 수익률·종목 수 산출 → `(portfolio_id, month)` DB-중립 upsert(SELECT-then-write).
  - 스냅샷 목록 서비스: 소유권 확인 → 월 오름차순 조회.
  - upsert 분기에 `@MX:WARN` + `@MX:REASON`(동시 경합 주의).
- 의존: T-002.
- 완료 조건: 멱등성(REQ-RPT-NFR-004) 테스트 통과(동일 월 재요청 시 단일 레코드), 엣지 E-10·E-11.

## T-007 — 라우터 엔드포인트 4종 [High]

- 파일: `backend/src/stock_picker/portfolio/router.py` [MODIFY]
- 내용:
  - `GET /{portfolio_id}/report?format=&period=` → CSV `StreamingResponse`(text/csv + Content-Disposition: attachment) 또는 미지원 포맷 오류.
  - `GET /{portfolio_id}/report/summary?benchmark=&period=` → `PortfolioReportSummary`.
  - `POST /{portfolio_id}/report/snapshot`(Body: month) → `MonthlySnapshot`.
  - `GET /{portfolio_id}/report/snapshots` → `list[MonthlySnapshot]`.
  - `Depends(get_current_user)`·`get_db_session`·`get_redis_client` 재사용.
- 의존: T-005, T-006.
- 완료 조건: 4종 엔드포인트 통합 테스트 통과, CSV 첨부 헤더 확인, 소유권 404·포맷 오류.

## T-008 — 프론트엔드 (`.js`/`.ts` 쌍) [Medium]

- 파일: `frontend/src/api/portfolio.js`(+`.ts`) [MODIFY], `frontend/src/components/PortfolioReportPanel.js` [NEW], `frontend/src/pages/Portfolio.js`(+`.tsx`) [MODIFY]
- 내용:
  - API 클라이언트: `apiDownloadReport`(blob)·`apiGetReportSummary`·`apiCreateSnapshot`·`apiGetSnapshots`.
  - `PortfolioReportPanel`: CSV 다운로드 버튼·JSON 요약 카드·스냅샷 목록·생성 버튼.
  - Portfolio 페이지에 리포트 섹션 통합(기존 섹션 보존).
- 의존: T-007.
- 완료 조건: `.js`·`.ts` 쌍 동시 수정, 다운로드·요약·스냅샷 UI 동작.

---

## 위험 요소 (Risks)

| 위험 | 영향 | 완화 |
|------|------|------|
| 030/033/034 서비스 시그니처 변경 | 집계 호출 깨짐 | 기존 서비스 수정 금지(§제외), 호출 인터페이스만 의존 |
| CSV 한국어 인코딩 깨짐(Excel) | 사용자 가독성 | UTF-8 BOM 프리픽스, E-12 테스트 |
| 스냅샷 upsert 동시성 경합 | 중복 레코드 | Unique 제약 + SELECT-then-write, DB가 제약 위반 차단 |
| 커스텀 범위 가격 조회 지연 | NFR-005 위반 | 030 asyncio.gather 병렬 조회 재사용, Redis 캐시 활용 |
| 미지원 포맷 처리 누락 | REQ-RPT-005 후반 미충족 | format 검증 분기 + BDD-6 테스트 |

---

## 검증 게이트 (Quality Gates)

- TRUST 5: 테스트 85%+·한국어 주석·ruff·OWASP(소유권 404 정보 비노출)·conventional commit.
- LSP: run 단계 0 errors·0 type errors·0 lint errors.
- scipy 미사용·외부 CSV 라이브러리 미사용 정적 확인.
- 기존 SPEC-030/033/034/service.py 회귀 테스트 통과(집계 호출이 기존 동작을 깨지 않음).
