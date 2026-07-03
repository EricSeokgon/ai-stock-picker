---
name: project-stock-027
description: SPEC-STOCK-027 risk analysis & correlation matrix — numpy-only stats, new GET risk-analysis endpoint, Redis cache, frontend RiskAnalysisPanel
metadata:
  type: project
---

SPEC-STOCK-027 "리스크 분석 및 상관관계 매트릭스" — Phase 3 portfolio AI 2nd SPEC, follows [[project_stock_002]]/026 lineage.

**Scope:** new `GET /portfolios/{id}/risk-analysis?period&refresh` returning Pearson correlation matrix + per-holding annualized volatility (std×√252×100) + portfolio volatility (sqrt(wᵀΣw)×√252×100) + diversification benefit. numpy ONLY (scipy FORBIDDEN by REQ-RISK-NFR-001). No DB tables (one-shot + Redis cache).

**Why:** SPEC-026 explicitly deferred the correlation matrix to this SPEC. Statistical info only, not prediction (永久 제외 원칙: no auto-trading/orders).

**How to apply (key reuse + gotchas):**
- SPEC says reuse `portfolio/mapping/prices.py` but ACTUAL path is `src/stock_picker/mapping/prices.py` (no `portfolio/` prefix). Closest precedent is `portfolio/dividends.py` (FDR + run_in_executor + redis.asyncio graceful + get_portfolio_with_holdings ownership + _safe_float NaN guard).
- Caching precedent: `portfolio/service.py::optimize_portfolio` (cache key `portfolio_optimize:{id}:{today}`, redis.get/setex, refresh flag, 403 on non-owner). New key: `portfolio_risk:{id}:{period}:{date}` TTL 3600s.
- Router precedent: `optimize_portfolio` endpoint uses `redis: aioredis.Redis = Depends(get_redis_client)`; deps in `api/deps.py`.
- price history helper `mapping/prices.py::get_stock_price_history(krx_code, days)` returns `[{date, close}]` sorted asc — usable for daily-return series, but it has its OWN redis caching (per-stock). Risk service still needs run_in_executor for fresh series or reuse this helper.
- numpy 2.4.6 already installed (transitive); scipy ABSENT. Must still add `numpy>=1.26` as direct dep in `backend/pyproject.toml`. Verify scipy stays absent.
- Tests: `asyncio_mode = "auto"` (no @pytest.mark.asyncio needed). Integration tests use in-memory SQLite + dependency_overrides + `_register_and_login`. NOTE: optimize endpoint is NOT integration-tested (only unit/service) — risk-analysis needs 3 NEW integration tests. Run via `backend/.venv/bin/pytest`.
- Frontend: api/portfolio.ts convention is `token`-first args + `authHeaders()`. Insert `<RiskAnalysisPanel>` in PortfolioDetail after `<OptimizeSection>` (Portfolio.tsx ~line 811). Tests in `frontend/src/__tests__/*.test.tsx` (vitest + @testing-library/react).
- Edge guards: FDR fail → exclude stock continue; valid holdings <2 → HTTP 400; insufficient common trading days for a pair → 0.0 neutral; diversification benefit clamp ≥0; NaN guard on all numpy outputs.
