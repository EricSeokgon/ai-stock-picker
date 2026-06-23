---
name: project-stock-028
description: SPEC-STOCK-028 overseas asset support — market/currency columns, FX rate service, KRW-unified perf/risk/AI for NYSE/NASDAQ stocks
metadata:
  type: project
---

SPEC-STOCK-028 "해외 자산 지원" — extends KRX-only portfolio domain to US stocks (NYSE/NASDAQ) and overseas ETFs with USD/KRW conversion. TDD brownfield, branch feature/SPEC-STOCK-028. Builds on SPEC-017/026/027 which explicitly deferred overseas assets here.

**Why:** Current `PortfolioHolding` (db/models.py:246) has only `krx_code` + KRW-implicit `avg_buy_price`; cannot store AAPL/SPY or compute mixed-currency performance.

**How to apply:** Plan is in `.moai/specs/SPEC-STOCK-028/tasks.md` (10 tasks, 7 phases). Strategy = backward-compat first: keep `krx_code` name (reinterpret as ticker), add only `market`(VARCHAR10 default KRX) + `currency`(VARCHAR3 default KRW). New `fx_rate.py` reuses dividends.py/risk_analysis.py pattern (run_in_executor sync FDR + Redis TTL + graceful fallback 1350.0). All values KRW-unified; USD converted at calc time only.

**Critical non-obvious finding (verified in models.py):** `portfolio_holdings` table currently has NO unique constraint. So REQ-FOREX-082/AC-11 premise ("change existing constraint") is false — migration 0019 must CREATE a new unique constraint `(portfolio_id, krx_code, market)`, not alter one. downgrade = drop constraint + drop 2 columns. Must flag to manager-tdd.

**Other gotcha:** `calculate_performance` is currently sync; adding overseas price+FX makes it async → `router.get_performance` must also become async/await (in-scope chained change). risk_analysis only uses `get_portfolio_with_holdings` so unaffected.

Related: [[project_stock_027]] (risk numpy-only, scipy banned — NFR-004 continues), [[reference_stock_libs]] (FDR/numpy already direct deps).
