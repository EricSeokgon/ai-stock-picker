# SPEC-STOCK-030 Compact

> 포트폴리오 기간별 성과 요약(YTD/1M/3M/6M/1Y). Run 단계용 압축본.

## 요구사항

REQ-PS-001 (Ubiquitous): THE 시스템 SHALL `GET /portfolios/{portfolio_id}/performance-summary` 엔드포인트를 제공한다(인증·소유자).
REQ-PS-002 (Event-driven): WHEN 성과 요약 요청 시 THEN YTD/1M/3M/6M/1Y 5개 기간 모두 계산한다.
REQ-PS-003 (Ubiquitous): THE 시스템 SHALL 각 기간별 `total_return_pct`·`annualized_return_pct`·`mdd_pct`를 산출한다. 수식은 spec.md §5.2 참고.
REQ-PS-004 (State-driven): WHILE Redis 캐시 유효 시 THE 시스템 SHALL 재계산 없이 캐시 반환. 캐시 키 포맷·TTL은 spec.md §5.3 참고.
REQ-PS-005 (Unwanted): IF 보유 종목 없음 또는 데이터 부족 시 THEN 200 OK + 5개 기간 빈 데이터(`has_data=false`) 반환(4xx 아님).
REQ-PS-006 (Ubiquitous): THE 시스템 SHALL KRX(원화)+NYSE/NASDAQ(달러→원화 환산) 혼합 포트폴리오를 KRW 통일 계산한다.
REQ-PS-007 (Event-driven): WHEN `refresh=true` 시 THEN 캐시 무시·재조회·재계산·캐시 갱신.
REQ-PS-008 (Optional): WHERE 기간 시작일 이전 거래일 데이터 없을 경우 THE 시스템 SHALL 가용 최이른 거래일 기준 계산 또는 유효일<2 시 빈 데이터.
REQ-PS-009 (Ubiquitous): THE 프론트엔드 SHALL `PerformanceSummaryPanel`로 5개 기간 카드 표시(양수 녹색·음수 적색).
REQ-PS-010 (Ubiquitous): THE 시스템 SHALL 응답에 `calculated_at`(ISO-8601 UTC)·`disclaimer`(문자열)를 포함한다. [scipy 금지는 NFR-001]

### NFR
NFR-001: scipy 금지(numpy+math만). NFR-002: 캐시 히트 500ms 이내, FDR `run_in_executor`+`gather`. NFR-003: 커버리지 85%+. NFR-004: FDR 실패 graceful(예외 비전파). NFR-005: 환율 실패 fallback 1350.0.

## 인수 조건

### Scenario 1: 정상 5기간 성과 조회
Given: 삼성전자(KRX)·애플(NYSE) 보유. When: `GET .../performance-summary`. Then: 200 + 5기간 각 total_return_pct·annualized_return_pct·mdd_pct, 해외 KRW 환산.

### Scenario 2: Redis 캐시 히트
Given: 당일 캐시 존재. When: refresh=false. Then: 캐시 반환, FDR 미호출, 500ms 이내.

### Scenario 3: 캐시 갱신
Given: 당일 캐시 존재. When: refresh=true. Then: 캐시 무시·FDR 재조회·재계산·캐시 갱신.

### Scenario 4: 빈 포트폴리오
Given: 보유 종목 0. When: `GET .../performance-summary`. Then: 200 OK + 5기간 빈 데이터(has_data=false), 예외 없음.

### Scenario 5: 기간 시작일 이전 상장 종목
Given: 1Y 시작일 이후 상장 종목 포함. When: 1Y 계산. Then: 가용 최이른 거래일 기준 계산 또는 유효일<2 시 빈 데이터, 타 기간 정상.

### Scenario 6: 타인 포트폴리오 접근
Given: user_id != portfolio.user_id. When: `GET .../{other}/performance-summary`. Then: 404 Not Found(코드베이스 관례).

### Scenario 7: YTD 경계 케이스
Given: 1월 초. When: YTD 계산. Then: 유효 거래일<2 시 YTD 빈 데이터, 추측 단언 금지, 타 기간 정상.

### Scenario 8: FDR 조회 실패
Given: FDR 일시 실패. When: 성과 요약 요청. Then: 예외 비전파, 실패 종목/기간 제외 또는 빈 데이터, 5기간 구조 유지.

### Scenario 9: 프론트엔드 PerformanceSummaryPanel 렌더링
Given: API 5기간 데이터 반환. When: Portfolio 페이지 로드. Then: 5개 기간 카드 렌더링, 양수 녹색·음수 적색, 로딩 상태 표시.

## 수정 파일 목록

- [NEW] backend/src/stock_picker/portfolio/performance_summary.py
- [NEW] backend/tests/unit/test_portfolio_performance_summary.py
- [NEW] backend/tests/integration/test_portfolio_performance_summary_router.py
- [NEW] frontend/src/components/PerformanceSummaryPanel.js
- [MODIFY] backend/src/stock_picker/portfolio/schemas.py — PerformanceSummaryResponse·PeriodPerformance 추가
- [MODIFY] backend/src/stock_picker/portfolio/router.py — GET /performance-summary 추가
- [MODIFY] frontend/src/api/portfolio.js — apiGetPerformanceSummary 추가
- [MODIFY] frontend/src/pages/Portfolio.js — PerformanceSummaryPanel 통합
- [MODIFY] frontend/src/api/portfolio.ts — TS 인터페이스 추가
- [MODIFY] frontend/src/pages/Portfolio.tsx — PerformanceSummaryPanel 통합
- [EXISTING] backend/src/stock_picker/portfolio/backtest.py — _fetch_price_series_sync·_align_close_series·_compute_returns 재사용(수정 없음)
- [EXISTING] backend/src/stock_picker/portfolio/service.py — get_portfolio_with_holdings 재사용
- [EXISTING] backend/src/stock_picker/portfolio/fx_rate.py — get_usd_krw_rate·_FALLBACK_RATE 재사용
- [EXISTING] backend/src/stock_picker/backtest/metrics.py — calculate_max_drawdown 재사용

마이그레이션: 불필요(0018 유지, 신규 테이블 없음).

## 제외 사항 (What NOT to Build)

- 일별 수익률 시계열 조회 (SPEC-029 백테스팅 기능)
- 종목별 개별 성과 분석
- 비교 벤치마크 (KOSPI, S&P500 대비)
- 배당 수익률 포함 계산
- 샤프 비율·변동성 등 위험조정 지표 (SPEC-029·SPEC-027 영역)
- 거래 비용(수수료·세금·슬리피지)·리밸런싱
- 사용자 정의 기간 (SPEC-029 백테스트 사용)
- 결과 영속화·히스토리 (one-shot + Redis 캐시만)
- 자동 매매/주문 실행 (프로젝트 영구 제외)
