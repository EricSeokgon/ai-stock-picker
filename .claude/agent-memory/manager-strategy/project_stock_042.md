---
name: project-stock-042
description: SPEC-STOCK-042 portfolio sharing & social — gotchas (models.py omission, atomic view_count, derived like_count, share_url base, migration 0026)
metadata:
  type: project
---

SPEC-STOCK-042 — Portfolio Sharing & Social (Phase 3). Adds public read-only portfolio sharing, view/like counters, and a public feed. TDD mode, test file `backend/tests/unit/test_portfolio_sharing_042.py` (T-001~T-015).

**Why:** Social layer on top of existing portfolio system; reuses service.calculate_performance (perf) and goals.calculate_achievement_rate (goal progress).

**How to apply (non-obvious decisions surfaced during planning):**
- **models.py omission**: SPEC "Files to Modify" list does NOT include `backend/src/stock_picker/db/models.py`, but ORM models `PortfolioShare` + `PortfolioLike` MUST be added there (project uses `db.query(Model)`; SPEC-041 added PortfolioGoal the same way; unit tests branch on model type Portfolio/PortfolioGoal). Treat models.py as in-scope.
- **Migration 0026**: revision="0026", down_revision="0025" (0025 = SPEC-041 goals, current head). Follow 0025 pattern: op.create_table + server_default + ForeignKeyConstraint(ondelete CASCADE) + create_index. portfolio_shares has UNIQUE on portfolio_id (one share per portfolio).
- **view_count atomic**: use ORM `.update({view_count: view_count + 1}, synchronize_session=False)` then commit — NOT read-modify-write.
- **like_count derived**: COUNT(*) on portfolio_likes via `func.count`, no denormalized counter column.
- **Idempotent POST /share**: SELECT-then-write pattern (like SPEC-037 REQ-AIEX-NFR-005, NOT ON CONFLICT). If row exists → set is_public=True, keep existing token (do NOT rotate — rotating breaks existing share_url links). Surface to user if "refresh" was meant to rotate.
- **share_url base**: undefined in SPEC — recommend env var SHARE_BASE_URL, build `{base}/shared/{token}`.
- **Ownership violation → 404** (not 403), project-wide pattern. Owner-liking-own → 403; unauth like → 401 (HTTPBearer auto_error).
- **Public routers**: define shared_router (/shared) + feed_router (/feed) in new `sharing.py` (no auth dep), register in api/main.py via app.include_router. Owner endpoints (POST/DELETE/GET /portfolios/{id}/share) go in existing portfolio/router.py.
- **Feed perf risk**: FeedItem.total_return_rate per item via calculate_performance = N expensive external price calls. Limit page size; consider cache or latest-snapshot derivation.
- **No PII** in SharePublicResponse: exclude user identity/email; include portfolio_name, holdings, return rate, goal_progress only.

See [[project_stock_041]]-style lineage; reuses [[reference_stock_libs]] stack (FastAPI + SQLAlchemy sync Session + Pydantic v2). secrets.token_urlsafe(16) → 22-char token in VARCHAR(32).
