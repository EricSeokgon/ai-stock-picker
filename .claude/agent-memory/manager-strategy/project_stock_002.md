---
name: project-stock-002
description: SPEC-STOCK-002 Phase 3 scope — JWT auth, Telegram bot, portfolio simulator, backtest engine
metadata:
  type: project
---

SPEC-STOCK-002 is Phase 3 of the Korean stock/ETF recommendation system ([[project-stock-001]]). Builds on Phase 1+2 (243 tests passing). Adds 4 features, priority-ordered: JWT auth (High), Telegram bot (High), portfolio simulator (Medium), backtest engine (Low), plus frontend pages.

**Why:** Turn the read-only recommendation dashboard into a personalized tool — users authenticate, get push notifications via Telegram, track a simulated portfolio, and validate the scoring strategy historically via backtesting. Still an information tool, not investment advice (disclaimer constraint from Phase 1 still applies).

**How to apply:**
- Methodology TDD (RED-GREEN-REFACTOR). Reuse existing infra, do NOT re-architect.
- Key reusable hooks confirmed by code inspection: `db/session.py:get_session` (FastAPI DB dep), `scheduler/jobs.py:run_daily_pipeline()` (Telegram auto-notify hook point — append notify step after run_recommendation), `mapping/prices.py:_fetch_price` (fdr.DataReader returns full OHLCV history — reuse for both portfolio current price and backtest historical series), `api/main.py:create_app()` (register new routers here).
- Design decisions locked: JWT secret via env SECRET_KEY (add .env.example); Telegram polling not webhook (no public URL); backtest as async background job (asyncio.create_task or APScheduler one-shot); portfolio performance fetches live prices at query time (not cached).
- New tables (Alembic, additive migrations on top of 0001_initial_tables): users, telegram_subscriptions, portfolios, portfolio_holdings, backtest_runs, backtest_daily_results.
- Backtest window 2025-01-01..2026-06-01, momentum + volume anomaly only (no historical sentiment — sentiment not stored historically), KOSPI benchmark.
- Dependency risk: passlib 1.7.4 is unmaintained and breaks with bcrypt>=4.1 — pin bcrypt<4.1 or drop passlib for direct bcrypt. See [[reference-stock-002-libs]].
