---
name: project-stock-001
description: SPEC-STOCK-001 Korean stock & ETF recommendation system — scope, architecture, methodology decisions
metadata:
  type: project
---

SPEC-STOCK-001 is a greenfield monorepo (backend/ Python FastAPI + frontend/ React TypeScript) building a daily Korean stock/ETF recommendation pipeline: news collection → Claude sentiment analysis → trend aggregation → scoring engine → web dashboard.

**Why:** Replace manual reading of hundreds of financial news articles with an automated, explainable AI pipeline. Positioned as an *information tool*, NOT investment advice — disclaimer required on every screen (REQ-WEB-005) due to legal/regulatory risk.

**How to apply:**
- Methodology is TDD (greenfield, RED-GREEN-REFACTOR). Harness: standard (4 domains, 15+ files).
- Phase 1 MVP scope only: daily 06:00 batch, Claude sentiment, KRX mapping, FinanceDataReader prices, Top-10 stock scoring, FastAPI /recommendations + /news, basic React dashboard, Redis cache.
- Deferred to Phase 2: intraday 30-min refresh, sector trend charts, ETF recommendations, recommendation-detail view.
- Permanently excluded: auto-trading/order execution, auth, backtesting, portfolio simulator, overseas assets, push/email.
- Scoring formula (frozen contract): total_score = 0.40*sentiment + 0.20*volume + 0.25*momentum + 0.15*anomaly, each component normalized 0..1.
- Claude model: claude-sonnet-4-6, JSON-schema-enforced output, max 3 retries exponential backoff, failed articles isolated as `analysis_failed`.
- 5 PostgreSQL tables: articles, analysis_results, stock_mentions, sector_trends, recommendations. See [[reference-stock-libs]] for stack versions.
