---
name: reference-stock-libs
description: Verified PyPI library versions for SPEC-STOCK-001 backend stack (checked 2026-06-01)
metadata:
  type: reference
---

Library versions verified against PyPI on 2026-06-01 for [[project-stock-001]]. Re-verify before pinning if significant time has passed — these decay.

- anthropic: latest 0.105.2 (2026-05-29) — pin `>=0.105,<0.106`
- finance-datareader (FinanceDataReader): latest 0.9.202 (2026-05-13) — pin `>=0.9.2,<0.10`
- fastapi: latest 0.136.3 — pin `>=0.136,<0.137`
- sqlalchemy: 2.0.x line (2.x async-capable) — pin `>=2.0,<2.1`

**How to apply:** Use these as the basis for pyproject.toml dependency constraints. FinanceDataReader package name on PyPI is `finance-datareader` (import name `FinanceDataReader`). Anthropic SDK supports native structured JSON output — use it for schema enforcement rather than hand-rolled parsing.
