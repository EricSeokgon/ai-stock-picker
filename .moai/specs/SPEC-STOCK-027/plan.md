# SPEC-STOCK-027 구현 계획 (Implementation Plan)

> 리스크 분석 및 상관관계 매트릭스 — 포트폴리오 통계적 리스크 프로필.

## 마일스톤 분해 (Milestone Decomposition)

### M1 — numpy 의존성 + 리스크 분석 서비스 (Priority: High)

numpy 직접 의존성 추가 + 상관관계/변동성/포트폴리오 변동성/분산투자 효익 계산 핵심 로직.

| 태스크 | 파일 | 내용 |
|--------|------|------|
| T1-1 | `backend/pyproject.toml` | `dependencies`에 `numpy>=1.26` 추가. scipy 추가 금지(REQ-RISK-NFR-001). |
| T1-2 | `backend/src/stock_picker/portfolio/risk_analysis.py` (신규) | `calculate_risk_analysis(portfolio_id, user_id, db, redis, period=90, refresh=False)`. 보유 종목 조회·소유권 검증, FDR 종가 시계열 수집(`run_in_executor`, 실패 종목 제외), 일간 수익률 산출. |
| T1-3 | `risk_analysis.py` (순수 계산 함수) | 상관관계 매트릭스(numpy, 대각 1.0)·종목별 연환산 변동성(std×√252×100)·공분산 행렬·포트폴리오 변동성(sqrt(wᵀΣw)×√252×100)·분산투자 효익(1 - port/weighted_avg, 음수 클램프 0). |

**완료 기준**: numpy 기반 계산 함수가 mock 가격 데이터로 상관관계·변동성·포트폴리오 변동성·분산투자 효익을 정확히 산출하며, scipy 미사용.

### M2 — 스키마 + 라우터 엔드포인트 (Priority: High)

| 태스크 | 파일 | 내용 |
|--------|------|------|
| T2-1 | `portfolio/schemas.py` | `HoldingVolatility`(krx_code, name, annualized_volatility_pct, price_data_days)·`RiskAnalysisResult`(correlation_matrix dict[str,dict[str,float]], holdings_volatility, portfolio_volatility_pct, diversification_benefit_pct, period_days, calculated_at) 스키마. |
| T2-2 | `portfolio/router.py` | `GET /portfolios/{portfolio_id}/risk-analysis?period={int}&refresh={bool}` (async, 인증·소유권). period ∈ {30,60,90,180,252} 검증(아니면 422), 기본값 90. 유효 종목 < 2개 시 400. |

**완료 기준**: 엔드포인트가 correlation_matrix·holdings_volatility·portfolio_volatility_pct·diversification_benefit_pct·period_days·calculated_at를 반환하고, 인증/소유권/period/2종목 미만 에러를 올바르게 처리.

### M3 — Redis 캐싱 (Priority: Medium)

| 태스크 | 파일 | 내용 |
|--------|------|------|
| T3-1 | `portfolio/risk_analysis.py` | Redis 캐시 레이어. 키 `portfolio_risk:{portfolio_id}:{period}:{date}`, TTL 3600s, `?refresh=true` 시 무시·재계산. graceful degradation(Redis 미가용 시 직접 계산). |

**완료 기준**: `?refresh=false` + 캐시 존재 시 FinanceDataReader 호출 0회. `?refresh=true` 시 재계산·재적재.

### M4 — 프론트엔드 RiskAnalysisPanel (Priority: Medium)

| 태스크 | 파일 | 내용 |
|--------|------|------|
| T4-1 | `frontend/src/api/portfolio.ts` | `apiGetRiskAnalysis(portfolioId, period?)` 함수 + `RiskAnalysisResult`/`HoldingVolatility` 타입. |
| T4-2 | `frontend/src/components/RiskAnalysisPanel.tsx` (신규) | 상관관계 히트맵(적색↔흰색↔청색 그라데이션) + 변동성 테이블(종목명/연환산 변동성%) + 포트폴리오 변동성·분산투자 효익 요약 + 기간 선택기(30/60/90/180/252). 과거 데이터 기반 면책 명시. |
| T4-3 | `frontend/src/pages/Portfolio.tsx` | `PortfolioScoreCard` 아래에 `RiskAnalysisPanel` import·렌더(기존 섹션 보존). |

**완료 기준**: 패널에서 히트맵·변동성 테이블·요약이 렌더링되고, 기간 변경 시 재조회된다.

### M5 — 테스트 (Priority: High)

| 태스크 | 파일 | 내용 |
|--------|------|------|
| T5-1 | `backend/tests/unit/test_portfolio_risk.py` (신규) | 8개 이상: 상관관계 계산·변동성 계산·포트폴리오 변동성(가중치)·캐시 적중/미적중·2종목 미만 400·포트폴리오 404·소유자 불일치 403·FDR 실패 graceful. |
| T5-2 | `backend/tests/integration/test_portfolio_router.py` | 통합 3개: risk-analysis 200 정상·period 422·2종목 미만 400. |
| T5-3 | `frontend` 컴포넌트 테스트 | `RiskAnalysisPanel` 렌더·기간 선택기 동작. |

**완료 기준**: 백엔드 단위 8개 + 통합 3개 통과, 커버리지 fail_under=85 충족.

---

## 기술 접근 요약 (Technical Approach)

- **통계 계산**: numpy만 사용(scipy 금지). 상관관계=`np.corrcoef`/pandas `.corr()`, 공분산=`np.cov`, 변동성=`std × √252 × 100`.
- **포트폴리오 변동성**: `sqrt(weightsᵀ · 공분산 · weights) × √252 × 100`. 보유 비중은 SPEC-017 성과 인프라 재사용.
- **분산투자 효익**: `(1 - port_vol / Σ(weightᵢ × volᵢ)) × 100`, 음수 클램프 0.
- **데이터 수집**: FinanceDataReader 종가 시계열, `run_in_executor`(prices.py 패턴), 실패 종목 제외.
- **캐싱**: Redis(redis.asyncio, api/deps.py), 키 `portfolio_risk:{id}:{period}:{date}`, TTL 3600s, graceful degradation.

---

## 리스크 및 완화 (Risks & Mitigation)

| 리스크 | 영향 | 완화 |
|--------|------|------|
| **FDR 종목별 가격 누락/실패** | 매트릭스 불완전 | 실패 종목 제외 후 계속(REQ-RISK-DATA-002). 유효 종목 < 2개면 400. |
| **공통 거래일 부족** | 상관계수 NaN | 공통일 부족 쌍은 0.0(중립) 설정(REQ-RISK-CONSTRAINT-002), NaN 전파 방지. |
| **포트폴리오 변동성 음수/NaN** | 분산투자 효익 손상 | 음수 효익은 0 클램프(REQ-RISK-005), NaN 가드. |
| **FDR 블로킹 I/O** | 이벤트 루프 블로킹 | `run_in_executor`로 비동기화(REQ-RISK-NFR-002, prices.py 검증된 패턴). |
| **numpy 미설치 환경** | import 실패 | pyproject.toml 직접 의존성 명시(T1-1). FDR 전이 의존성에만 의존하지 않음. |
| **period 임의 값 입력** | 의도치 않은 계산 | 허용 집합 {30,60,90,180,252} 외 422(REQ-RISK-PERIOD-002). |

---

## MX 태그 대상

- `calculate_risk_analysis()` — 외부 API(FDR) 호출 + fan_in 가능 → `@MX:NOTE` 또는 `@MX:ANCHOR`.
- 순수 통계 계산 함수(상관/공분산/포트폴리오 변동성) — 복잡도·불변 계약 → `@MX:NOTE`.
