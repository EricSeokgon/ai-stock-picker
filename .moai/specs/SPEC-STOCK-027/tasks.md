# SPEC-STOCK-027 Task Decomposition

Generated: 2026-06-18 | Mode: TDD (Brownfield)

## M1 — numpy 의존성 + 순수 통계 함수

| ID | 파일 | 작업 | 상태 |
|----|------|------|------|
| T1-1 | `backend/pyproject.toml` | numpy>=1.26 추가 (scipy 금지) | pending |
| T1-2 | `backend/tests/unit/test_portfolio_risk.py` | 순수 함수 RED 테스트 8개+ | pending |
| T1-3 | `backend/src/stock_picker/portfolio/risk_analysis.py` | 순수 함수 GREEN 구현 | pending |
| T1-4 | `backend/tests/unit/test_portfolio_risk.py` | 오케스트레이션 RED 테스트 | pending |
| T1-5 | `backend/src/stock_picker/portfolio/risk_analysis.py` | calculate_risk_analysis GREEN | pending |

## M2 — 스키마 + 라우터

| ID | 파일 | 작업 | 상태 |
|----|------|------|------|
| T2-1 | `backend/src/stock_picker/portfolio/schemas.py` | HoldingVolatility, RiskAnalysisResult | pending |
| T2-2 | `backend/src/stock_picker/portfolio/router.py` | GET /{id}/risk-analysis 엔드포인트 | pending |

## M3 — 통합 테스트

| ID | 파일 | 작업 | 상태 |
|----|------|------|------|
| T3-1 | `backend/tests/integration/test_portfolio_router.py` | 통합 3개 추가 | pending |

## M4 — 프론트엔드

| ID | 파일 | 작업 | 상태 |
|----|------|------|------|
| T4-1 | `frontend/src/api/portfolio.ts` | apiGetRiskAnalysis + TS 타입 | pending |
| T4-2 | `frontend/src/components/RiskAnalysisPanel.tsx` | 히트맵+변동성테이블+기간선택기 | pending |
| T4-3 | `frontend/src/__tests__/RiskAnalysisPanel.test.tsx` | 컴포넌트 테스트 | pending |
| T5-1 | `frontend/src/pages/Portfolio.tsx` | RiskAnalysisPanel 삽입 | pending |

## 의존 사슬
T1-1 → T1-2 → T1-3 → T1-4 → T1-5 ↔ T2-1 → T2-2 → {T3-1, T4-1} → T4-2 → {T4-3, T5-1}
