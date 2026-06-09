---
name: reference-stock-002-libs
description: Verified PyPI versions for SPEC-STOCK-002 new deps (JWT, Telegram) checked 2026-06-02
metadata:
  type: reference
---

New dependency versions verified against PyPI on 2026-06-02 for SPEC-STOCK-002 (Phase 3). See [[project-stock-002]] for scope and [[reference-stock-libs]] for the Phase 1 stack. These decay — re-verify before pinning.

- python-telegram-bot: latest 22.7 — SPEC requires `>=21`; pin `>=21,<23`. v21+ is fully async (asyncio), integrates with the existing asyncio/APScheduler runtime. Use Application + polling (run_polling or initialize/start manually inside the existing event loop).
- python-jose[cryptography]: latest 3.5.0 (2025-05-28) — pin `>=3.3,<4`. Maintenance mode but stable. Alternative `pyjwt` is more actively maintained; SPEC explicitly chose python-jose, so honor it unless the user revisits.
- passlib[bcrypt]: latest 1.7.4 (2020-10-08, unmaintained). WARN: passlib 1.7.4 breaks with bcrypt>=4.1 (`AttributeError: module 'bcrypt' has no attribute '__about__'`). Mitigation: pin `bcrypt<4.1` OR use bcrypt directly without passlib. Surface this to the user as a known integration risk.

**How to apply:** Telegram bot must share the existing asyncio loop, not spawn its own — coordinate with `scheduler/jobs.py` runtime. JWT SECRET_KEY must come from env (add to .env.example), never hardcoded. Backtesting reuses `mapping/prices.py:_fetch_price` pattern: `fdr.DataReader(code, start, end)` already returns full OHLCV history, so no new price-fetch code is needed for historical series.
