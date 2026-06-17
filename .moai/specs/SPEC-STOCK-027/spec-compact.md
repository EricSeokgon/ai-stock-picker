# SPEC-STOCK-027 (Compact) — 리스크 분석 및 상관관계 매트릭스

> Run 단계용 압축본. 요구사항 + 인수 기준만 포함.

## 핵심
포트폴리오의 통계적 리스크 프로필 제공. 종목 쌍 상관관계 매트릭스 + 종목별 연환산 변동성 + 포트폴리오 변동성 + 분산투자 효익 + 프론트 상관관계 히트맵.
과거 가격(FinanceDataReader) 기반 numpy 계산. **scipy 미사용**. 신규 DB 마이그레이션 없음(0018 유지).

## 수정/신규 파일
- `backend/pyproject.toml` (numpy>=1.26 직접 의존성 추가, scipy 금지)
- `backend/src/stock_picker/portfolio/risk_analysis.py` (신규 — calculate_risk_analysis + 순수 통계 함수)
- `backend/src/stock_picker/portfolio/schemas.py` (HoldingVolatility, RiskAnalysisResult 추가)
- `backend/src/stock_picker/portfolio/router.py` (GET /{id}/risk-analysis)
- `frontend/src/api/portfolio.ts` (apiGetRiskAnalysis)
- `frontend/src/components/RiskAnalysisPanel.tsx` (신규 — 히트맵 + 변동성 테이블 + 요약 + 기간 선택기)
- `frontend/src/pages/Portfolio.tsx` (PortfolioScoreCard 아래 RiskAnalysisPanel 렌더)
- `backend/tests/unit/test_portfolio_risk.py` (신규, 8개+)
- `backend/tests/integration/test_portfolio_router.py` (통합 3개 추가)

## 엔드포인트
`GET /portfolios/{portfolio_id}/risk-analysis?period={int}&refresh={bool}` (async, 인증·소유권)
- period ∈ {30,60,90,180,252}, 기본 90, 외 값은 422.
- 유효 종목 < 2개면 400. 미존재 404. 소유자 불일치 403.

## 출력 스키마 (RiskAnalysisResult)
- `correlation_matrix`: dict[str, dict[str, float]] (외부/내부 키 모두 krx_code, 대각 1.0, -1~1)
- `holdings_volatility`: [{ krx_code, name, annualized_volatility_pct, price_data_days }]
- `portfolio_volatility_pct`: float
- `diversification_benefit_pct`: float (음수 클램프 0)
- `period_days`: int
- `calculated_at`: str/datetime

## 계산식 (numpy)
- 상관관계: 일간 수익률 피어슨 corr (np.corrcoef / pandas .corr()), 대각 1.0, 공통일 부족 쌍은 0.0.
- 종목 변동성: std(daily_returns) × √252 × 100.
- 포트폴리오 변동성: sqrt(wᵀ · cov · w) × √252 × 100 (w=비중).
- 분산투자 효익: (1 - port_vol / Σ(weightᵢ × volᵢ)) × 100, 음수→0.

## 요구사항 (EARS)
- REQ-RISK-001: WHEN GET risk-analysis THEN correlation_matrix+holdings_volatility+portfolio_volatility_pct+diversification_benefit_pct+period_days+calculated_at.
- REQ-RISK-002: 상관계수 -1~1, 대각 1.0.
- REQ-RISK-003: 연환산 변동성 = std×√252×100.
- REQ-RISK-004: 포트폴리오 변동성 = sqrt(wᵀΣw)×√252×100.
- REQ-RISK-005: 분산투자 효익 = (1 - port/weighted_avg)×100, 음수 클램프 0.
- REQ-RISK-006: correlation_matrix = dict[str, dict[str, float]].
- REQ-RISK-PERIOD-001: period 기본 90.
- REQ-RISK-PERIOD-002: period ∉ {30,60,90,180,252} → 422.
- REQ-RISK-PERIOD-003: period일 이내 데이터 사용.
- REQ-RISK-DATA-001: FDR 종가 시계열 수집.
- REQ-RISK-DATA-002: FDR 실패 종목 제외, 예외 비전파.
- REQ-RISK-DATA-003: price_data_days 반환.
- REQ-RISK-CONSTRAINT-001: 유효 종목 < 2개 → 400.
- REQ-RISK-CONSTRAINT-002: 공통일 부족 쌍 → 0.0.
- REQ-RISK-AUTH-001/002/003: 401 / 404 / 403.
- REQ-RISK-CACHE-001: 캐시 존재 AND ?refresh=false → FDR 미호출.
- REQ-RISK-CACHE-002: ?refresh=true → 재계산·갱신.
- REQ-RISK-CACHE-003: 키 portfolio_risk:{id}:{period}:{date}, TTL 3600s.
- REQ-RISK-CACHE-004: Redis 미가용 → 직접 계산(graceful).
- REQ-RISK-NFR-001: numpy 사용, scipy 금지.
- REQ-RISK-NFR-002: FDR run_in_executor(이벤트 루프 비블로킹).
- REQ-RISK-NFR-003: 과거 데이터 기반 통계(미래 예측 아님) 명시.
- REQ-RISK-FE-001~004: 히트맵·변동성 테이블·요약·기간 선택기.

## 캐시
키 `portfolio_risk:{portfolio_id}:{period}:{date}`, TTL 3600s, ?refresh=true 강제 갱신. redis.asyncio(api/deps.py) 재사용, graceful degradation.

## 인수 기준
- AC-1 전체 스키마 / AC-2 상관 -1~1·대각1 / AC-3 변동성 식 / AC-4 포트폴리오 변동성(가중치) / AC-5 분산투자 효익(음수 클램프) / AC-6 캐시(FDR 0회) / AC-7 2종목 미만 400 / AC-8 404·403 / AC-9 FDR 실패 graceful / AC-10 period 422 / AC-11 프론트 패널.

## 테스트 (8 단위 + 3 통합)
unit: test_correlation_matrix_calculation, test_volatility_calculation, test_portfolio_volatility_with_weights, test_diversification_benefit, test_risk_analysis_redis_cache_hit, test_risk_analysis_min_two_holdings, test_risk_analysis_portfolio_not_found, test_risk_analysis_wrong_owner, test_risk_analysis_fdr_failure_graceful.
integration: test_risk_analysis_endpoint_200, test_risk_analysis_endpoint_400_min_holdings, test_risk_analysis_endpoint_422_invalid_period.

## 재사용
- SPEC-026: Portfolio.tsx·PortfolioScoreCard·api/portfolio.ts 구조.
- SPEC-017: get_portfolio_with_holdings·비중 데이터.
- mapping/prices.py: FDR + run_in_executor + Redis graceful 패턴.
- api/deps.py: Redis.

## 제외
scipy/MPT·효율적 프론티어 · Monte Carlo · VaR/CVaR · Sharpe/Sortino/Beta · 미래 예측 · 세금/거래비용 · 해외자산(SPEC-028) · 상관/변동성 시계열(rolling) · 위험 한도 알림 · optimize 엔드포인트 수정 · 자동매매 · 신규 마이그레이션.
