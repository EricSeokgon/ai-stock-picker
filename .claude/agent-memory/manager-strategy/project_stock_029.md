---
name: project-stock-029
description: SPEC-STOCK-029 portfolio backtesting — buy-and-hold return sim in portfolio domain, reuses backtest/metrics.py + SPEC-028 FX/FDR infra, sync one-shot no DB
metadata:
  type: project
---

SPEC-STOCK-029 "포트폴리오 백테스팅" — user holdings (ticker+weight) held over a date range → return simulation. New `portfolio/backtest.py` module, TDD, branch feature/SPEC-STOCK-029. Deliberately SEPARATE from existing `backtest/` package (SPEC-012 strategy backtest) to avoid name/function confusion.

**Why separate:** `backtest/` = strategy backtest (SPEC-012). This is portfolio buy-and-hold. Collision avoided via `REQ-PBT-*` prefix, `test_portfolio_backtest.py`, `BacktestChart`/`BacktestPanel` components (vs existing `Backtest.tsx`). DO NOT modify `backtest/` package.

**How to apply:** Plan in `.moai/specs/SPEC-STOCK-029/plan.md` (8 tasks T-001~T-008). Algorithm: FDR price fetch → inner join common trading days → weight normalization → daily portfolio values → daily/cumulative returns → MDD + Sharpe. Sync one-shot, no DB persistence, no job table.

**Critical reuse gotcha (verified in metrics.py):** `calculate_max_drawdown(cumulative_returns)` takes CUMULATIVE returns (1.0-based value series), NOT daily returns. `calculate_sharpe_ratio(daily_returns, risk_free_rate=0.02)` takes DAILY returns — SPEC-029 must pass `risk_free_rate=0.035` explicitly. Also `calculate_total_return(cumulative_returns)` already exists — reuse it too. These are pure stdlib/math (no scipy) — NFR-001 satisfied for free.

**Other reuse:** `risk_analysis._align_returns` is the inner-join pattern for common trading days (returns daily-returns arrays); `_daily_returns(closes)` helper also there. `fx_rate.get_usd_krw_rate(redis)` async + `_FALLBACK_RATE=1350.0`. `service.get_portfolio_with_holdings(db, portfolio_id, user_id)` for ownership (None → 404).

**Router template:** `/optimize` endpoint (portfolio/router.py:129) is the exact pattern — `@router.post("/{portfolio_id}/...")` async + `Depends(get_current_user)` + `Depends(get_db_session)` + `Depends(get_redis_client)`. Note: dep is `get_redis_client` (from api.deps) NOT get_redis.

Related: [[project_stock_028]] (FX/overseas infra this builds on), [[project_stock_027]] (numpy-only/scipy-banned established), [[reference_stock_libs]] (FDR/numpy direct deps).
