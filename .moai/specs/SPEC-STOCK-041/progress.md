# SPEC-STOCK-041 Progress

## Status: COMPLETED

## Implementation Summary
- TDD RED-GREEN-REFACTOR cycle: 25/25 tests passing
- DB migration: 0025_portfolio_goals_041.py
- API endpoints: POST/GET/DELETE /portfolios/{portfolio_id}/goals
- Frontend: PortfolioGoalPanel.tsx component
- Scheduler: check_portfolio_goals() 60min interval
- Achievement rate calculation: MIN(quantity_progress, return_progress) clamped >= 0.0
- Soft delete: is_active=False on DELETE
- Response rules: 204 No Content when no active goal, 409 Conflict on duplicate
- Idempotency: goal_reached_notified flag for duplicate alert prevention

## Test Coverage
- **Backend Unit Tests**: 25/25 passing
  - CRUD operations (create, read, delete)
  - Soft delete verification
  - Achievement rate calculation
  - Duplicate active goal prevention (409)
  - No active goal handling (204 response)
  - Idempotency validation (no duplicate alerts)
  - Schedule integration

## Database Schema
- Table: `portfolio_goals`
- Columns: id, portfolio_id, user_id, target_amount, current_amount, target_return_pct, current_return_pct, is_active, goal_reached_notified, created_at, updated_at
- Foreign Keys: portfolio_id → portfolios(id), user_id → users(id)
- Constraints: UNIQUE(portfolio_id, user_id) WHERE is_active=True

## API Contracts
- `POST /portfolios/{portfolio_id}/goals`: Create goal (requires auth, owner check, duplicate 409)
- `GET /portfolios/{portfolio_id}/goals`: Retrieve active goal (requires auth, 204 if none)
- `DELETE /portfolios/{portfolio_id}/goals/{goal_id}`: Soft delete (requires auth, owner check)

## Frontend Integration
- Component: PortfolioGoalPanel.tsx
- Functions: getPortfolioGoals(), createGoal(), deleteGoal() in api/portfolio.ts
- Features: Goal display, creation form, achievement rate visualization, delete button

## Commits
- feat(SPEC-STOCK-041): 포트폴리오 목표 관리 구현 — TDD (25/25 통과)
- docs(SPEC-STOCK-041): 포트폴리오 목표 관리 SPEC 초안 — v0.3.0

## Completed: 2026-06-29
