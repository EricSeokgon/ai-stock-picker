---
name: project-stock-spec-conventions
description: Brownfield SPEC-authoring conventions for ai-stock-picker portfolio domain — ownership status, migrations, JSON storage, scipy ban, frontend file pairing
metadata:
  type: project
---

ai-stock-picker SPEC 작성 시 따라야 하는 브라운필드 관례 (SPEC-026~032 portfolio 계열에서 확인).

**Why:** 이 프로젝트는 SPEC-STOCK-NNN 계열로 portfolio 기능을 점진 확장 중이며, 신규 SPEC은 기존 코드 관례와 충돌하지 않아야 한다. 사용자가 매 SPEC마다 동일 제약을 carry-over로 명시한다.

**How to apply:** portfolio 도메인 신규 SPEC을 작성할 때 아래를 기본 전제로 삼는다.

- **패키지**: `backend/src/stock_picker/portfolio/`. `backtest/` 아님(backtest는 별도 함수).
- **소유권 위반 상태코드**: 신규 코드는 `404 Not Found`(403 아님). `get_portfolio_with_holdings()`가 None 반환 → 404. 단 레거시 `ai_analysis.analyze_portfolio`·`optimize_portfolio`는 예외적으로 403 사용 — 신규 코드는 404 관례 따름.
- **Alembic**: `backend/alembic/versions/NNNN_name.py`(`src/.../migrations/` 아님). `revision`/`down_revision` 문자열. 리비전 순차 증가 — 최신 확인 후 +1. (0020=SPEC-031, 0021=SPEC-032).
- **JSON 컬럼 저장**: SQLite 테스트 호환을 위해 JSONB 대신 `Text` + JSON 직렬화 문자열 사용(기존 `ai_advice.payload`·`screener_presets.criteria` 패턴). 요청서가 JSONB라 해도 Text로 구현.
- **scipy 금지** (반복 NFR-001): 수치 계산은 `numpy` + `math`만. `risk_analysis.py`가 모범 — 순수 함수 레이어 + 오케스트레이션 함수 분리, 모듈 상단 @MX:NOTE로 금지 명시.
- **순수 함수 분리**: 핵심 계산은 DB·Redis 없이 테스트 가능한 순수 함수로(`calculate_*`), 서비스가 가격/소유권/저장을 주입.
- **가격 조회 재사용**: KRX `realtime/price_feed.get_current_price(code)["price"]`, 해외 `portfolio/service._fetch_foreign_price(ticker, redis)` × `fx_rate.get_usd_krw_rate(redis)`. USD→KRW 환산 후 예산/금액 비교(`calculate_performance` 패턴).
- **시장/통화 메타**: `PortfolioHolding.market`(KRX|NYSE|NASDAQ)·`currency`(KRW|USD), server_default KRX/KRW (SPEC-028). 국내/해외 분기 기준.
- **프론트 .js/.ts 쌍**: `frontend/src/api/portfolio.js`와 `.ts`, `pages/Portfolio.js`와 `.tsx`를 항상 동시 수정. 컴포넌트는 컴파일된 .js 형태로 커밋됨.
- **언어**: `code_comments: ko`, `git_commit_messages: ko`. 커밋 끝에 `🗿 MoAI <email@mo.ai.kr>`.
- **환경**: gh CLI 미설치.

**기존 기능 중복 주의 (브라운필드)**: 신규 SPEC 작성 전 동일 도메인 기존 SPEC을 반드시 grep으로 확인할 것. 예: **배당 분석은 SPEC-019가 이미 구현**(`portfolio/dividends.py` `get_dividend_info`·`calculate_portfolio_dividends`, 스키마 `PortfolioDividends`/`HoldingDividend`/`DividendCalendarMonth`, `GET /portfolios/{id}/dividends`, DB 없이 FDR+Redis TTL 86400s). SPEC-033(배당 수익률)은 019를 대체하지 않고 **강화 레이어**로 정의 — 019 데이터 레이어 재사용 + 신규 가치(DRIP 재투자 시뮬레이션, 날짜 정밀 캘린더)만 추가, 신규 스키마명·엔드포인트 경로(`/dividend/*` 단수 vs 019 `/dividends` 복수)를 분리해 충돌 회피. 요청서가 신규 테이블(예: 0022_dividend_cache)을 언급해도 기존이 Redis 캐시로 동작하면 신규 마이그레이션 미도입이 맞다.

**SPEC 문서 5종 세트**: research.md, spec.md(YAML frontmatter 8필드 + HISTORY 표 + EARS REQ + §제외(What NOT to Build) + Delta Markers 표 + MX Tag Plan), acceptance.md(EARS AC + Given-When-Then BDD + 엣지 케이스 표 + DoD), plan.md(T-001~ 작업분해, 시간추정 금지), spec-compact.md(run-phase 압축 참조). REQ 접두사는 기능별 고유(충돌 회피): OPT(026)·RISK(027)·FA(028)·PBT(029)·PS(030)·PAL(031)·RBA(032)·DVY(033, 019 DIV 회피)·BMK(034).

**SPEC-034(벤치마크 비교) 강화 레이어 패턴**: SPEC-030(성과 요약) 위에 시장 벤치마크(KOSPI=^KS11/KOSDAQ=^KQ11/SP500=^GSPC/NASDAQ=^IXIC) 상대 성과(초과수익·알파·베타·100 재기준화 차트)를 얹는다. 030의 기간 헬퍼(`_compute_period_dates`)·가치 시계열(`_compute_portfolio_values`·`_align_close_series`)·연환산 재사용(수정 금지), 027 numpy 베타(`np.cov/np.var(ddof=1)`, scipy 없이)·NaN 가드 모방, 029 `_fetch_price_series_sync`로 지수 심볼(`^...`) FDR 조회(run_in_executor 격리). 베타 일별 ≥20개(미만 None), var=0 None. 신규 모듈 `portfolio/benchmark.py`(순수 함수 3종+서비스 2종), 엔드포인트 `/benchmark`·`/benchmark/chart`. 마이그레이션 없음(yfinance 온디맨드). 최신 리비전은 0021(SPEC-032); 033·034 모두 마이그레이션 미도입.

**SPEC-035(성과 리포트) 집계·직렬화 레이어 패턴**: 030(성과)·033(배당)·034(벤치마크) 서비스 결과를 **집계**해 다운로드 리포트(CSV 손익표·JSON 통합 요약)로 묶고 월별 스냅샷을 영속화한다. 신규 지표 계산 없음 — 030 `calculate_performance_summary`·033 `get_dividend_summary`·034 `get_benchmark_comparison_service`·service `calculate_performance`/`get_portfolio_with_holdings` 호출만(전부 수정 금지). 신규 모듈 `portfolio/report.py`(순수 함수 2종 `generate_holding_report_rows`·`generate_csv_content` + 서비스 5종). **CSV 외부 라이브러리 금지**(`io.StringIO`+`csv` 표준만, 한국어 헤더·UTF-8 BOM). 엔드포인트 `/report`(StreamingResponse text/csv attachment)·`/report/summary`·`/report/snapshot`·`/report/snapshots`. **마이그레이션 0022 도입**(`portfolio_monthly_snapshots`, `UniqueConstraint(portfolio_id, month)`) — 033/034와 달리 035는 스냅샷 영속화로 신규 테이블 필요. upsert는 DB-중립 SELECT-then-write(SQLite 호환, ON CONFLICT 금지). REQ 접두사 `RPT`. 스키마 `HoldingReportRow`·`PortfolioReportSummary`(033/034 스키마 임베드)·`MonthlySnapshot`.

**EARS 정규 REQ 텍스트 금지어 회피(plan-auditor 대비)**: REQ 본문(SHALL 진술)에 함수명·HTTP 코드·SQL·변수명·파일경로·라이브러리명·자료구조 리터럴 금지 — 자연어 행동 서술로. 단 도메인 개념 수치(재기준화 100, 베타 최소 데이터 20)는 NFR/REQ에 허용. 설계 결정 노트·기술 접근(§5)에는 함수명·심볼 명시 가능.

**SPEC-039(실시간 폴링) REST 폴링·장중 게이팅 패턴**: 보유 종목 현재가를 30/60/120초 REST 폴링(기본 60, WebSocket 금지)으로 자동 갱신. 가격 갱신은 **신규 수집·엔드포인트 없이 기존 `GET /portfolios/{id}/performance` 재호출**(service `calculate_performance`가 KRX/해외 통합 처리). **시장 상태는 public `GET /market/status`(인증 없음, `/portfolios` prefix 밖 신규 라우터)** — 시장 상태는 사용자·포트폴리오 비종속 전역 정보라 인증 불필요. **장중 판정 갭 주의**: `notifications/general_alert_service.py::_is_market_open`은 시간만 검사하고 **요일(평일)은 검사 안 함**(SPEC-023 소유, 수정 금지). SPEC-039는 평일+시간 검사 신규 순수 함수를 `portfolio/market_status.py`에 별도 작성(`ZoneInfo("Asia/Seoul")`, 표준 라이브러리만, scipy 금지). 프론트는 폴링 훅(주기 선택·일시중지/재개·사이클 전 장중 확인 게이팅·in-flight 스킵·useEffect cleanup·마지막 갱신 시각)+상태 배지. 마이그레이션 없음(최신 0024 유지, 035=0022·036=0023·037=0024). REQ 접두사 `POLL`.
