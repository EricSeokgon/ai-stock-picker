# SPEC-STOCK-030 Research: 포트폴리오 기간별 성과 요약

## 1. Architecture Overview

The SPEC-STOCK-030 feature requires calculating portfolio performance across predefined time periods (YTD, 1M, 3M, 6M, 1Y). The architecture mirrors the existing backtest engine (SPEC-029) and risk analysis service (SPEC-027):

1. **Data flow**: User requests period performance → Backend computes returns for each period using historical price data → Caches result in Redis → Returns summary to frontend
2. **Relationship to backtest**: Both use `_fetch_price_series_sync()` from FDR, both calculate daily returns and cumulative metrics, but period performance is simpler (5 fixed time periods vs. arbitrary date ranges)
3. **Key difference**: Period performance returns a summary object per period (total return %, optional trend), while backtest returns full daily data

---

## 2. Backtest Engine Analysis (SPEC-029)

### Key Functions

**`run_portfolio_backtest(portfolio_id, user_id, db, redis, start_date, end_date) -> BacktestResult`**
- **File**: `/home/sklee/moai/ai-stock-picker/backend/src/stock_picker/portfolio/backtest.py:203-334`
- **Signature**: `async def run_portfolio_backtest(...) -> BacktestResult`
- **Parameters**: 
  - `portfolio_id: int` — Portfolio ID (ownership verified)
  - `user_id: int` — Owner user ID (authorization check)
  - `db: object` — SQLAlchemy session for DB access
  - `redis: object` — redis.asyncio client for caching
  - `start_date: date` — Backtest start date
  - `end_date: date` — Backtest end date
- **Returns**: `BacktestResult` schema with daily returns, MDD, Sharpe ratio, total return, excluded tickers, used tickers, disclaimer
- **Exception handling**: Raises HTTPException with specific status codes (404, 400, 422)

**`_fetch_price_series_sync(ticker: str, start_date: date, end_date: date) -> list[dict]`**
- **File**: `/home/sklee/moai/ai-stock-picker/backend/src/stock_picker/portfolio/backtest.py:149-197`
- **Signature**: `def _fetch_price_series_sync(ticker, start_date, end_date) -> list[dict]`
- **What it does**:
  - Synchronous FDR data fetch (must run in `run_in_executor` to avoid blocking asyncio)
  - Fetches price data for KRX tickers or NYSE/NASDAQ tickers
  - Returns list of dicts: `[{"date": "YYYY-MM-DD", "close": float}, ...]`
  - Returns empty list on any failure (FDR exception, missing columns, NaN values)
- **Key detail**: NaN check uses self-comparison `close_val != close_val` instead of `math.isnan()`
- **Usage**: Called in `run_portfolio_backtest()` line 252 with `loop.run_in_executor(None, _fetch_price_series_sync, h.krx_code, start_date, end_date)`

**`BacktestResult` schema**
- **File**: `/home/sklee/moai/ai-stock-picker/backend/src/stock_picker/portfolio/schemas.py:291-305`
- **Fields**:
  - `daily: list[DailyReturn]` — List of daily records
  - `mdd: float` — Maximum drawdown (≤0)
  - `sharpe_ratio: float` — Annualized Sharpe ratio
  - `total_return: float` — Total return ratio (decimal, e.g., 0.12 = 12%)
  - `period_days: int` — Number of trading days
  - `excluded_tickers: list[str]` — Tickers excluded due to missing data
  - `used_tickers: list[str]` — Tickers actually used in calculation
  - `disclaimer: str` — Legal disclaimer

**`DailyReturn` schema**
- **File**: `/home/sklee/moai/ai-stock-picker/backend/src/stock_picker/portfolio/schemas.py:282-289`
- **Fields**:
  - `date: str` — "YYYY-MM-DD" format
  - `portfolio_value: float` — Normalized portfolio value (starting at 1.0)
  - `daily_return: float` — Daily return ratio (decimal)
  - `cumulative_return: float` — Cumulative return from start (decimal, first day = 0.0)

### Reuse Strategy for Period Performance

**Functions to reuse directly**:
1. `_fetch_price_series_sync()` — Same price fetching logic, just different date ranges
2. `get_usd_krw_rate()` from `fx_rate.py` — Same USD/KRW conversion for foreign holdings
3. `get_portfolio_with_holdings()` from `service.py` — Same portfolio loading with ownership check

**Calculation patterns to reuse**:
1. `_compute_returns()` (backtest.py:113-144) — Takes portfolio values, returns daily and cumulative returns
2. `_align_close_series()` (backtest.py:45-73) — Inner-joins price data on common trading dates
3. `calculate_total_return()`, `calculate_max_drawdown()`, `calculate_sharpe_ratio()` from `backtest/metrics.py` — Pure numpy functions

**Period date calculation logic** (NEW implementation needed):
- **YTD**: From January 1 of current year to today
- **1M**: From 30 days ago to today
- **3M**: From 90 days ago to today
- **6M**: From 180 days ago to today
- **1Y**: From 365 days ago to today
- All relative to today's date (or last trading day if desired)

---

## 3. Redis Caching Patterns

### From risk_analysis.py

**Cache key format**:
```python
# Line 265: cache_key = f"portfolio_risk:{portfolio_id}:{period}:{today}"
cache_key = f"portfolio_risk:{portfolio_id}:{period}:{today}"
```
- Format: `portfolio_risk:<portfolio_id>:<period_days>:<YYYY-MM-DD>`
- **Date key component**: Regenerates daily (key includes today's date in KST)

**TTL values used**:
```python
# Line 20: _RISK_TTL = 3600  # 1 hour
_RISK_TTL = 3600
```
- TTL = 1 hour (3600 seconds)
- Suitable for intraday metrics that don't change frequently

**Cache workflow** (risk_analysis.py:231-401):
```python
# Line 263-273: Try to read cache first
if not refresh:
    try:
        cached = await redis.get(cache_key)
        if cached:
            return RiskAnalysisResult.model_validate_json(cached)
    except Exception as e:
        logger.warning("Redis cache read failed: %s", e)

# Line 395-399: Write result to cache (error tolerant)
try:
    await redis.setex(cache_key, _RISK_TTL, result.model_dump_json())
except Exception as e:
    logger.warning("Redis cache write failed: %s", e)
```

**Async wrapper pattern** (run_in_executor):
```python
# Line 276-280: Parallel FDR calls in executor
loop = asyncio.get_event_loop()
price_tasks = [
    loop.run_in_executor(None, _fetch_stock_prices, h.krx_code, period) 
    for h in holdings
]
price_results = await asyncio.gather(*price_tasks)
```

### For SPEC-030 Implementation

**Suggested cache key pattern**:
```python
# Format: portfolio_perf_summary:<portfolio_id>:<today_kst>
cache_key = f"portfolio_perf_summary:{portfolio_id}:{today_kst}"
```
- Regenerates daily (new key each day)
- Single cache entry for all 5 periods (no need for per-period keys)
- TTL: 3600 seconds (same as risk analysis)

---

## 4. Portfolio Data Access

### From service.py

**`get_portfolio_with_holdings(db, portfolio_id, user_id) -> Portfolio | None`**
- **File**: `/home/sklee/moai/ai-stock-picker/backend/src/stock_picker/portfolio/service.py:87-100`
- **Signature**: `def get_portfolio_with_holdings(db: Session, portfolio_id: int, user_id: int) -> Portfolio | None`
- **Returns**: Portfolio model with `holdings` list explicitly loaded
- **Key detail** (line 97-99): Holdings are lazy-loaded, so code explicitly queries them:
  ```python
  portfolio.holdings = (
      db.query(PortfolioHolding).filter(PortfolioHolding.portfolio_id == portfolio_id).all()
  )
  ```

**Holdings structure** (from models.py:246-283):
- `krx_code: str` — Ticker/code identifier
- `market: str` — "KRX" (default), "NYSE", or "NASDAQ"
- `currency: str` — "KRW" (default) or "USD"
- `quantity: int` — Number of shares
- `avg_buy_price: Decimal` — Purchase price in original currency
- **KRX vs NYSE/NASDAQ distinction**: Use `market` field to determine if USD→KRW conversion needed

---

## 5. Schema Patterns

### Pydantic v2 Pattern (from schemas.py)

**Request model pattern**:
```python
class BacktestRequest(BaseModel):
    """백테스트 요청 스키마"""
    start_date: date
    end_date: date
    
    @model_validator(mode="after")
    def validate_dates(self) -> "BacktestRequest":
        if self.start_date >= self.end_date:
            raise ValueError("end_date must be after start_date")
        return self
```

**Response model pattern**:
```python
class BacktestResult(BaseModel):
    """응답 스키마"""
    daily: list[DailyReturn]
    mdd: float
    sharpe_ratio: float
    total_return: float
    period_days: int
    excluded_tickers: list[str]
    used_tickers: list[str]
    disclaimer: str
    
    # No model_config needed if no special serialization
```

**Field naming conventions**:
- Use `snake_case` for Python fields
- Pydantic auto-converts to JSON (no need for `Field(..., alias="...")`)
- Use descriptive field names matching API response intent

---

## 6. Router Patterns

### From router.py

**Endpoint URL conventions**:
- GET for read-only operations with query params: `GET /portfolios/{id}/risk-analysis?period=90&refresh=false`
- POST for side-effects or complex request bodies: `POST /portfolios/{id}/backtest` with body
- Resource hierarchy: `/portfolios/{id}/resource-name`

**Auth pattern**:
```python
# Line 209-226: Auth via dependency injection
@router.post("/{portfolio_id}/backtest", response_model=BacktestResult)
async def backtest_portfolio(
    portfolio_id: int,
    body: BacktestRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    redis: aioredis.Redis = Depends(get_redis_client),
) -> BacktestResult:
```

**Dependency injection pattern**:
- `Depends(get_db_session)` → SQLAlchemy session
- `Depends(get_current_user)` → Authenticated user object
- `Depends(get_redis_client)` → redis.asyncio.Redis instance

**Ownership check pattern** (router.py:62-72):
```python
portfolio = (
    db.query(Portfolio)
    .filter(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
    .first()
)
if portfolio is None:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="포트폴리오를 찾을 수 없습니다",
    )
```

### For SPEC-030 Implementation

**Endpoint design**: 
```python
@router.get("/{portfolio_id}/performance-summary", response_model=PerformanceSummaryResponse)
async def get_performance_summary(
    portfolio_id: int,
    periods: str = Query(default="ytd,1m,3m,6m,1y", description="Comma-separated period list"),
    refresh: bool = Query(default=False, description="Ignore cache"),
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    redis: aioredis.Redis = Depends(get_redis_client),
) -> PerformanceSummaryResponse:
```

**Rationale for GET (not POST)**:
- Period is a query parameter (not body data)
- No side effects (read-only operation)
- Aligns with risk-analysis endpoint pattern

---

## 7. Frontend Patterns

### BacktestPanel.js (SPEC-029)

**State management**:
```javascript
// Lines 24-32: Date state + result state
const [startDate, setStartDate] = useState(oneYearAgo);
const [endDate, setEndDate] = useState(today);
const [result, setResult] = useState(null);
const [loading, setLoading] = useState(false);
const [error, setError] = useState(null);
```

**API call pattern** (lines 34-56):
```javascript
async function handleRun() {
    setLoading(true);
    setError(null);
    try {
        const data = await runPortfolioBacktest(token, portfolioId, startDate, endDate);
        setResult(data);
    } catch (err) {
        setError(err.message ?? 'Default error message');
    } finally {
        setLoading(false);
    }
}
```

**Display structure** (lines 108-134):
- Metric cards in grid: `gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))'`
- Each card: label + formatted value
- Chart component below
- Disclaimer text at bottom

### BacktestChart.js (SPEC-029)

**Library used**: Recharts (LineChart, ResponsiveContainer, etc.)

**Props pattern**:
```javascript
export function BacktestChart({ daily }) {  // daily = array of {date, cumulative_return}
    const data = daily.map((d) => ({
        date: d.date,
        displayDate: formatDate(d.date),  // YYYY-MM-DD → MM/DD
        cumulative_return_pct: +(d.cumulative_return * 100).toFixed(4),
    }));
    // Render LineChart with data
}
```

**Data transformation**:
- Input: decimal returns (0.12 = 12%)
- Output: percentage values for display (12.0%)
- Date formatting: "YYYY-MM-DD" → "MM/DD" for compact axis labels

### For SPEC-030 Component Design

**New component**: `PerformanceSummaryPanel.js`

**State**:
```javascript
const [result, setResult] = useState(null);  // PerformanceSummaryResponse
const [loading, setLoading] = useState(false);
const [error, setError] = useState(null);
```

**Display**: 5 cards (one per period)
```javascript
// Each card shows: period label (e.g., "Year-to-Date") + total_return % + color (green/red)
// Layout: same grid pattern as backtest metrics
// Example card: "YTD: +12.34%" (green) | "1M: -2.10%" (red)
```

**Optional**: Small sparkline or trend indicator per period (requires additional data)

---

## 8. Testing Patterns

### Test file structure (test_portfolio_backtest.py)

**Location**: `/home/sklee/moai/ai-stock-picker/backend/tests/unit/test_portfolio_backtest.py`

**Test organization**:
- Class-based test groups (e.g., `TestBacktestRequest`, `TestBacktestResult`)
- Test methods named `test_<behavior>` with clear assertions
- Mock data fixtures for common objects

**Pydantic schema tests** (lines 17-93):
```python
def test_valid_dates_pass(self):
    req = BacktestRequest(start_date=date(2024, 1, 1), end_date=date(2024, 6, 30))
    assert req.start_date == date(2024, 1, 1)

def test_start_after_end_raises(self):
    with pytest.raises(ValidationError):
        BacktestRequest(start_date=date(2024, 6, 30), end_date=date(2024, 1, 1))
```

**Mock patterns** (inferred from test structure):
- `@patch` decorator for module-level mocks
- `AsyncMock` for async functions
- `MagicMock` for DB/Redis objects

### conftest.py fixtures

**Location**: `/home/sklee/moai/ai-stock-picker/backend/tests/conftest.py`

**Key fixtures**:
- `db_engine`: Session-scoped PostgreSQL engine via testcontainers
- `db_session`: Function-scoped async session with rollback isolation

**Fixture pattern**:
```python
@pytest_asyncio.fixture
async def db_session(db_engine):
    async with db_engine.begin() as conn:
        async with AsyncSession(bind=conn, expire_on_commit=False) as session:
            yield session
            await session.rollback()  # Data isolation
```

---

## 9. Implementation Approach for SPEC-030

### Backend: New Endpoint

**Endpoint**: `GET /portfolios/{portfolio_id}/performance-summary`

**Query parameters**:
- `periods`: Comma-separated list or default to all 5 (ytd,1m,3m,6m,1y)
- `refresh`: Boolean to bypass cache

**Rationale for GET**: 
- Periods are predefined query params, not request body
- No side effects (read-only)
- Aligns with `/portfolios/{id}/risk-analysis` pattern

### Backend: Core Service Function

**Signature**:
```python
async def calculate_performance_summary(
    portfolio_id: int,
    user_id: int,
    db: Session,
    redis: aioredis.Redis,
    refresh: bool = False,
) -> PerformanceSummaryResponse:
```

**Implementation steps**:
1. Verify portfolio ownership (`get_portfolio_with_holdings()`)
2. Check Redis cache (unless `refresh=True`)
3. Fetch USD/KRW rate if holding any USD holdings
4. For each of 5 periods:
   a. Calculate start_date based on period type
   b. Fetch price series using `_fetch_price_series_sync()` with `run_in_executor`
   c. Align closes to common trading dates
   d. Apply USD→KRW conversion if needed
   e. Calculate cumulative return using logic from `_compute_returns()`
5. Construct response with 5 `PeriodPerformance` objects
6. Cache in Redis with TTL=3600s
7. Return response

**Data reuse**:
- Reuse `_fetch_price_series_sync()` directly
- Reuse `_align_close_series()` from backtest
- Reuse `_compute_returns()` but only extract cumulative return (ignore daily)
- Reuse `get_usd_krw_rate()` for conversion

### Backend: Schemas

**New schema: `PeriodPerformance`**:
```python
class PeriodPerformance(BaseModel):
    period: Literal["ytd", "1m", "3m", "6m", "1y"]
    display_label: str  # "Year-to-Date", "1 Month", etc.
    total_return: float  # Decimal (0.12 = 12%)
    start_date: str  # "YYYY-MM-DD"
    end_date: str    # "YYYY-MM-DD"
    trading_days: int  # Number of trading days in period
    portfolio_start_value: float  # Normalized to 1.0 at period start
    portfolio_end_value: float    # Final value
```

**New schema: `PerformanceSummaryResponse`**:
```python
class PerformanceSummaryResponse(BaseModel):
    summary: list[PeriodPerformance]  # 5 items
    portfolio_id: int
    calculated_at: datetime
    caching_info: dict = {}  # Optional: cache hit/miss, TTL remaining, etc.
```

### Period Date Calculation

**Algorithm** (relative to `today`):
```python
from datetime import date, timedelta

def get_period_start_date(period: str, today: date) -> date:
    if period == "ytd":
        return date(today.year, 1, 1)  # January 1 of current year
    elif period == "1m":
        return today - timedelta(days=30)
    elif period == "3m":
        return today - timedelta(days=90)
    elif period == "6m":
        return today - timedelta(days=180)
    elif period == "1y":
        return today - timedelta(days=365)
    else:
        raise ValueError(f"Unknown period: {period}")
```

### Frontend: New Component

**File**: `/home/sklee/moai/ai-stock-picker/frontend/src/components/PerformanceSummaryPanel.js`

**State**:
```javascript
const [result, setResult] = useState(null);
const [loading, setLoading] = useState(false);
const [error, setError] = useState(null);
const [selectedPeriods, setSelectedPeriods] = useState("ytd,1m,3m,6m,1y");
```

**Render pattern**:
```javascript
// Grid of 5 cards (or fewer if selectedPeriods filtered)
// Card: period label (e.g., "YTD") + total return % + color-coded (green positive, red negative)
// Optional: show start/end dates or trading days
```

**API call pattern**:
```javascript
async function fetchPerformanceSummary() {
    setLoading(true);
    try {
        const data = await apiGetPerformanceSummary(token, portfolioId, selectedPeriods);
        setResult(data);
    } catch (err) {
        setError(err.message);
    } finally {
        setLoading(false);
    }
}
```

**In Portfolio.tsx**: Import and add below BacktestPanel or as separate section

---

## 10. Constraints Identified

1. **numpy only** (no scipy) — Per SPEC-029, project uses numpy for calculations
2. **KRX tickers**: Use FinanceDataReader for Korean market data
3. **NYSE/NASDAQ tickers**: Use FinanceDataReader with appropriate symbols
4. **USD→KRW conversion**: Use `get_usd_krw_rate(redis)` with fallback 1350.0
5. **Code location**: Implement in `/backend/src/stock_picker/portfolio/` (not `backtest/` package which is SPEC-012)
6. **Package structure**: 
   - Service function in `portfolio/performance_summary.py` (new file)
   - Schemas in `portfolio/schemas.py` (extend existing)
   - Router endpoint in `portfolio/router.py` (extend existing)
7. **Date handling**: All dates should be `date` type (not datetime) for FDR compatibility
8. **Common trading dates**: Use inner join on dates (only dates where all holdings have data)

---

## 11. Risks and Unknowns

### Data availability risks:
- **Portfolio with 0 holdings**: Handled gracefully (return empty summary or error message)
- **Period start before first trade**: Empty trading days → fallback to earliest available date or return 0.0% return
- **All holdings excluded**: Return error (similar to backtest REQ-PBT-022)
- **Partial data**: Some holdings have data, some don't → Include only valid holdings in calculation (like backtest)

### Edge cases:
- **YTD on Jan 1**: Only 1 trading day of data (or 0)
- **Last trading day of week/month**: Ensure FDR returns correct date
- **FDR data lag**: Backtest handles this with fallback; apply same pattern
- **USD rate fetch failure**: Use fallback 1350.0 (already handled in `fx_rate.py`)

### Performance considerations:
- **5 separate FDR calls**: Parallelize with `asyncio.gather()` like backtest does
- **Price alignment**: Inner join on common dates (same as backtest) — scales O(n) where n = smallest dataset size
- **Cache hit rate**: Daily cache key means same cache used all day (good), but regenerates each day

---

## 12. Reference Implementations

### Key files and line numbers for pattern reuse:

**Async/executor pattern**:
- `/home/sklee/moai/ai-stock-picker/backend/src/stock_picker/portfolio/backtest.py:250-256` — FDR parallel calls
- `/home/sklee/moai/ai-stock-picker/backend/src/stock_picker/portfolio/risk_analysis.py:276-280` — Same pattern

**Price fetching**:
- `/home/sklee/moai/ai-stock-picker/backend/src/stock_picker/portfolio/backtest.py:149-197` — `_fetch_price_series_sync()` function

**Price alignment**:
- `/home/sklee/moai/ai-stock-picker/backend/src/stock_picker/portfolio/backtest.py:45-73` — `_align_close_series()` function

**Return computation**:
- `/home/sklee/moai/ai-stock-picker/backend/src/stock_picker/portfolio/backtest.py:113-144` — `_compute_returns()` function

**Ownership verification**:
- `/home/sklee/moai/ai-stock-picker/backend/src/stock_picker/portfolio/service.py:87-100` — `get_portfolio_with_holdings()` function

**Redis caching pattern**:
- `/home/sklee/moai/ai-stock-picker/backend/src/stock_picker/portfolio/risk_analysis.py:263-273` — Cache read pattern
- `/home/sklee/moai/ai-stock-picker/backend/src/stock_picker/portfolio/risk_analysis.py:395-399` — Cache write pattern

**Router pattern**:
- `/home/sklee/moai/ai-stock-picker/backend/src/stock_picker/portfolio/router.py:157-180` — Risk analysis endpoint (similar pattern)
- `/home/sklee/moai/ai-stock-picker/backend/src/stock_picker/portfolio/router.py:209-226` — Backtest endpoint (ownership check example)

**Pydantic v2 pattern**:
- `/home/sklee/moai/ai-stock-picker/backend/src/stock_picker/portfolio/schemas.py:265-279` — BacktestRequest (validation example)
- `/home/sklee/moai/ai-stock-picker/backend/src/stock_picker/portfolio/schemas.py:291-305` — BacktestResult (response schema)

**Frontend API pattern**:
- `/home/sklee/moai/ai-stock-picker/frontend/src/api/portfolio.js:79-91` — `apiGetRiskAnalysis()` function (query params pattern)
- `/home/sklee/moai/ai-stock-picker/frontend/src/api/portfolio.js:94-105` — `runPortfolioBacktest()` function (POST pattern)

**Frontend component pattern**:
- `/home/sklee/moai/ai-stock-picker/frontend/src/components/BacktestPanel.js` — Metric card layout and async handling
- `/home/sklee/moai/ai-stock-picker/frontend/src/components/BacktestChart.js` — Recharts LineChart usage

**Test pattern**:
- `/home/sklee/moai/ai-stock-picker/backend/tests/unit/test_portfolio_backtest.py` — Pydantic schema testing
- `/home/sklee/moai/ai-stock-picker/backend/tests/conftest.py:66-80` — Async session fixture

**FX rate service**:
- `/home/sklee/moai/ai-stock-picker/backend/src/stock_picker/portfolio/fx_rate.py:47-84` — `get_usd_krw_rate()` async wrapper pattern

---

## 13. Code Comments Convention

Per project rules (`.claude/rules/moai/languages/python.md`):
- Use docstrings with Google format for functions
- Use `# @MX:ANCHOR` for functions with fan_in >= 3
- Use `# @MX:REASON` for @MX:ANCHOR and @MX:WARN tags
- Use type hints for all parameters and returns

Example:
```python
# @MX:ANCHOR: [AUTO] Portfolio period performance calculation
# @MX:REASON: router.py, frontend API wrapper, tests 3+ locations
async def calculate_performance_summary(
    portfolio_id: int,
    user_id: int,
    db: Session,
    redis: aioredis.Redis,
    refresh: bool = False,
) -> PerformanceSummaryResponse:
    """포트폴리오 기간별 성과 요약 계산.
    
    YTD/1M/3M/6M/1Y 5개 기간의 수익률을 FDR 시세 기반으로 계산한다.
    
    Args:
        portfolio_id: 포트폴리오 ID
        user_id: 소유자 사용자 ID (소유권 확인)
        db: SQLAlchemy 세션
        redis: redis.asyncio 클라이언트
        refresh: True이면 캐시 무시하고 재계산
        
    Returns:
        PerformanceSummaryResponse: 5개 기간의 성과 요약
        
    Raises:
        HTTPException 404: 포트폴리오 없음 또는 소유권 없음
        HTTPException 422: 모든 종목 조회 실패
    """
```

---

## 14. Summary of Key Patterns

| Pattern | Location | Reusable for SPEC-030 |
|---------|----------|----------------------|
| Async FDR fetch in executor | backtest.py:250-256 | Yes, direct reuse |
| Price series fetching | backtest.py:149-197 | Yes, direct reuse |
| Price alignment (inner join) | backtest.py:45-73 | Yes, direct reuse |
| Return computation | backtest.py:113-144 | Yes (extract cumulative only) |
| Portfolio ownership check | service.py:87-100 | Yes, direct reuse |
| Redis cache pattern | risk_analysis.py:263-273, 395-399 | Yes, with daily key |
| Async endpoint + dependency injection | router.py:157-180 | Yes, model for GET endpoint |
| Pydantic v2 schema | schemas.py:265-305 | Yes, create new schemas |
| Frontend async state | BacktestPanel.js:24-56 | Yes, adapt for 5 periods |
| Recharts visualization | BacktestChart.js | Optional, can show mini-charts |
| API client wrapper | portfolio.js:79-105 | Yes, new apiGetPerformanceSummary() |

