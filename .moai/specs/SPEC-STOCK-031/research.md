# SPEC-STOCK-031 Research: 포트폴리오 알림 강화

**Research Date**: 2026-06-23  
**Target Specification**: SPEC-STOCK-031 (포트폴리오 알림 강화)  
**Scope**: Portfolio-level alert infrastructure for total return change detection and MDD threshold alerts

---

## Executive Summary

This research document provides comprehensive analysis of the existing alerts infrastructure (SPEC-020 through SPEC-025) and portfolio performance systems (SPEC-027 through SPEC-030) to support the implementation of SPEC-STOCK-031: portfolio-level alert enhancement.

The key finding is that **SPEC-STOCK-031 can be implemented by extending the existing general alerts infrastructure** (alerts table, general_alert_service) with portfolio-specific logic, avoiding duplication and maintaining consistency with established patterns.

---

## 1. 기존 알림 인프라 분석

### 1.1 Alerts 테이블 스키마 (마이그레이션 0017)

**Location**: `backend/alembic/versions/0017_alerts.py` (down_rev=0016)

**DDL 재구성**:
```sql
CREATE TABLE alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL (FK users.id CASCADE),
    krx_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(100) NULLABLE,
    alert_type VARCHAR(20) NOT NULL,  -- Enum at code level, not DB enum
    condition_value FLOAT NOT NULL,   -- Target price or threshold (%)
    condition_direction VARCHAR(8) NULLABLE,  -- 'above', 'below', 'either'
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_triggered BOOLEAN NOT NULL DEFAULT false,
    triggered_at TIMESTAMP WITH TIMEZONE NULLABLE,
    triggered_message VARCHAR(500) NULLABLE,
    created_at TIMESTAMP WITH TIMEZONE NOT NULL DEFAULT now()
);

CREATE INDEX ix_alerts_user_active ON alerts(user_id, is_active);
```

**Key Schema Notes**:
- PK is Integer autoincrement (per codebase convention)
- `alert_type` is `VARCHAR(20)` at DB level, with validation at code layer
- Supports NULL `condition_direction` (defaults applied in service layer)
- Both `triggered_at` and `triggered_message` capture event state post-firing
- No UNIQUE constraint on alerts table itself (unlike notifications)
- Index on `(user_id, is_active)` optimizes active alert queries

**ORM Model**: `backend/src/stock_picker/db/models.py:609-648`
```python
class Alert(Base):
    """사용자 정의 알림 설정 — 목표가·급등락 조건 기반 알림 (SPEC-STOCK-020)"""
    
    __tablename__ = "alerts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    krx_code: Mapped[str] = mapped_column(String(10), nullable=False)
    stock_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    alert_type: Mapped[str] = mapped_column(String(20), nullable=False)  # target_price|surge_drop|ex_dividend|volume_spike
    condition_value: Mapped[float] = mapped_column(Float, nullable=False)
    condition_direction: Mapped[str | None] = mapped_column(String(8), nullable=True)  # above|below|either
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    triggered_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ(timezone=True))
    triggered_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index("ix_alerts_user_active", "user_id", "is_active"),
    )
    user: Mapped["User"] = relationship("User", lazy="noload")
```

### 1.2 Alert Type Enum 목록 (SPEC-020, SPEC-023, SPEC-024 기준)

**Supported Alert Types** (from preferences.py:28-36):
```python
SUPPORTED_ALERT_TYPES: tuple[str, ...] = (
    "target_price",        # 목표가 알림 (SPEC-020)
    "surge_drop",          # 급등락 알림 (SPEC-020)
    "volume_spike",        # 거래량 급증 알림 (SPEC-023)
    "ex_dividend",         # 배당락일 알림 (SPEC-020)
    "rec_new",             # 신규 추천 (SPEC-024)
    "rec_dropped",         # 탈락 추천 (SPEC-024)
    "rec_score_change",    # 추천 점수 변화 (SPEC-023, §6.2)
)
```

**Implementation Status**:
- `target_price`: Fully implemented, supports `above`/`below` directions
- `surge_drop`: Fully implemented, supports `above`(급등)/`below`(급락)/`either`(both) directions
- `volume_spike`: Fully implemented, supports configurable multiplier (e.g., 2.0x avg volume)
- `ex_dividend`: Stub exists but not fully implemented (배당락일 기준 계산 미완료)
- `rec_new`, `rec_dropped`: Implemented in `rec_change.py` (추천 변동 감지)
- `rec_score_change`: Implemented in `rec_change.py` (|delta| >= 0.2 threshold)

**Missing Types** (for SPEC-STOCK-031):
- `portfolio_return_change`: Portfolio total return threshold
- `portfolio_mdd`: Portfolio MDD (Max Drawdown) threshold

These will be new types to add.

### 1.3 알림 트리거 흐름 (`check_and_trigger_all_alerts`)

**Location**: `backend/src/stock_picker/notifications/general_alert_service.py:456-540`

**High-level Flow**:
```
check_and_trigger_all_alerts(session: AsyncSession) → int
  │
  ├─ Gate check: ALERT_MARKET_HOURS_GATE=true (default) → skip outside 09:00~15:30 KST
  │
  ├─ Query: SELECT * FROM alerts WHERE is_active=true AND is_triggered=false
  │
  ├─ FOR EACH active_alert:
  │   │
  │   ├─ Get price/volume data:
  │   │   ├─ If alert_type == 'volume_spike': await get_avg_volume(krx_code)
  │   │   └─ Else: await get_stock_price_data(krx_code) → {close_price, change_rate, volume}
  │   │
  │   ├─ Evaluate condition:
  │   │   ├─ target_price: check_target_price(alert, price_data) → (triggered: bool, msg: str)
  │   │   ├─ surge_drop: check_surge_drop(alert, price_data) → (triggered: bool, msg: str)
  │   │   └─ volume_spike: check_volume_spike(alert, volume_data) → (triggered: bool, msg: str)
  │   │
  │   └─ IF triggered:
  │       ├─ UPDATE alerts SET is_triggered=true, triggered_at=now(), triggered_message=msg
  │       ├─ INSERT INTO notifications (...)  [via build_notification_payload]
  │       │   - with UNIQUE constraint conflict → on_conflict_do_nothing (idempotent)
  │       ├─ IF is_channel_enabled_async(session, user_id, alert_type, 'email'):
  │       │   └─ await _try_send_alert_email(alert, msg, session)  [best-effort]
  │       └─ IF is_channel_enabled_async(session, user_id, alert_type, 'telegram'):
  │           └─ await _try_send_telegram(alert, msg, session)  [best-effort]
  │
  └─ RETURN triggered_count

Exception handling: graceful degradation, per-alert try-catch, rollback on error
```

**Key Design Patterns**:
- **Async-first**: Uses AsyncSession exclusively, no blocking calls
- **Graceful degradation**: API failures (price/volume/email) don't block other alerts
- **Idempotency**: Leverages notifications table UNIQUE constraint + `on_conflict_do_nothing`
- **Market hours gating**: Avoids unnecessary API calls outside market hours (configurable)
- **Channel routing**: Uses `is_channel_enabled_async()` to gate email/telegram per user preference

### 1.4 멱등성 처리 방식

**Layer 1: Alerts Table State Machine**
- Once `is_triggered=true`, that alert will never fire again
- Subsequent scheduler runs skip it: `WHERE is_triggered=false`
- One-time firewall per user-alert pair

**Layer 2: Notifications Table UNIQUE Constraint**
```sql
UNIQUE CONSTRAINT uq_notification_user_type_code_date 
  ON (user_id, type, krx_code, ref_date)
```
- Prevents duplicate inbox entries on same day
- `ref_date = triggered_at.date()` ensures day-level granularity
- PostgreSQL `on_conflict_do_nothing()` silently ignores duplicates

**Code Pattern** (general_alert_service.py:522-526):
```python
ins = pg_insert(Notification).values(**notif_payload)
ins = ins.on_conflict_do_nothing(
    constraint="uq_notification_user_type_code_date"
)
await session.execute(ins)
```

**Implication for SPEC-STOCK-031**:
- Portfolio-level alerts need similar pattern
- For daily-check alerts (total return, MDD): use portfolio_id + ref_date in UNIQUE
- For continuous monitoring: track last-triggered state to avoid spam

### 1.5 알림 발송 흐름 (Inbox → Email → Telegram)

**Sequence**:
```
triggered alert
  │
  ├─ (1) Inbox (always):
  │     └─ INSERT INTO notifications (user_id, type, title, body, is_read=false, ...)
  │         via on_conflict_do_nothing (idempotent)
  │
  ├─ (2) Email (if channel enabled):
  │     ├─ is_channel_enabled_async() check
  │     ├─ SELECT EmailSubscription WHERE user_id=X AND is_active=true
  │     └─ send_general_alert_email(email, krx_code, alert_type, message)
  │         [via email_service.py, uses smtplib, graceful skip if SMTP_HOST unset]
  │
  └─ (3) Telegram (if channel enabled):
        ├─ is_channel_enabled_async() check
        ├─ SELECT TelegramSubscription WHERE user_id=X AND is_active=true
        └─ _send_message_sync(chat_id, formatted_message)
           [via telegram.notifier, async-wrapped sync call]
```

**Email Service Architecture** (email_service.py:7-85):
```python
def _get_smtp_config() -> dict[str, str] | None:
    """Read from environ: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM"""
    host = os.getenv("SMTP_HOST")
    if not host:
        return None  # Graceful skip if unconfigured
    return {
        "host": host,
        "port": int(os.getenv("SMTP_PORT", "587")),
        "user": os.getenv("SMTP_USER"),
        "password": os.getenv("SMTP_PASSWORD"),
        "from": os.getenv("SMTP_FROM"),
    }

def _send_email(to: str, subject: str, body: str, html: str | None = None) -> None:
    """Send via smtplib (synchronous, no async dependencies)"""
    config = _get_smtp_config()
    if config is None:
        logger.debug("SMTP_HOST not configured, email skipped")
        return  # Silent skip
    
    try:
        with smtplib.SMTP(config["host"], config["port"]) as server:
            server.starttls()
            server.login(config["user"], config["password"])
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = config["from"]
            msg["To"] = to
            msg.attach(MIMEText(body, "plain"))
            if html:
                msg.attach(MIMEText(html, "html"))
            server.sendmail(config["from"], [to], msg.as_string())
    except Exception as e:
        logger.error("Email send failed (ignored): %s", e)  # Best-effort
```

**For SPEC-STOCK-031**:
- Email template for portfolio alerts: "포트폴리오 알림: {portfolio_name} {alert_type} 발생"
- Follow same pattern: check channel enabled → SELECT subscription → send_email()
- Keep graceful degradation (email failures don't block notification creation)

### 1.6 스케줄러 주기 및 구동 방식

**Location**: `backend/src/stock_picker/scheduler/jobs.py:349-402`

**Scheduler Jobs**:
```python
_scheduler.add_job(
    run_daily_pipeline,
    CronTrigger(hour=6, minute=0, timezone="Asia/Seoul"),
    id="daily_collection",
    replace_existing=True,
)  # 일 배치, 06:00 KST

_scheduler.add_job(
    run_intraday_pipeline,
    CronTrigger(hour="9-15", minute="*/30", timezone="Asia/Seoul"),
    id="intraday_collection",
    replace_existing=True,
)  # 장중 30분 증분, 09:00~15:xx

_scheduler.add_job(
    check_price_alerts,
    IntervalTrigger(minutes=5),
    id="check_price_alerts",
    replace_existing=True,
)  # 가격 알림, 5분 주기

_scheduler.add_job(
    _run_general_alert_check,
    IntervalTrigger(minutes=10),
    id="check_alerts",
    replace_existing=True,
)  # 일반 알림 (목표가·급등락), 10분 주기
```

**General Alert Check Implementation** (scheduler/jobs.py:405-421):
```python
async def _run_general_alert_check() -> None:
    """일반 알림(목표가·급등락) 점검 잡 — 10분 주기 실행.
    
    예외 발생 시 로그 기록 후 종료 (graceful degradation).
    """
    from stock_picker.db.session import AsyncSessionLocal
    
    try:
        async with AsyncSessionLocal() as session:
            count = await check_and_trigger_all_alerts(session=session)
            log.info("일반 알림 점검 완료", triggered_count=count)
    except Exception:
        log.exception("일반 알림 점검 오류 (무시됨)")
```

**Implication for SPEC-STOCK-031**:
- Portfolio alerts should use same 10-minute interval (or new dedicated job)
- Can reuse existing `check_and_trigger_all_alerts` by extending it
- Or create new `check_portfolio_alerts()` function in separate job
- Recommendation: **Reuse existing job by extending alert_type support**

---

## 2. 포트폴리오 성과 인프라 분석

### 2.1 `get_performance_summary()` 반환 구조

**Location**: `backend/src/stock_picker/portfolio/performance_summary.py:311-417`

**Function Signature**:
```python
async def calculate_performance_summary(
    portfolio_id: int,
    user_id: int,
    db: Any,
    redis: Any,
    refresh: bool = False,
) -> PerformanceSummaryResponse:
    """
    포트폴리오의 5개 표준 기간(YTD/1M/3M/6M/1Y) 성과 요약을 계산한다.
    ...
    """
```

**Return Type** (schemas.py:327-335):
```python
class PerformanceSummaryResponse(BaseModel):
    """포트폴리오 기간별 성과 요약 응답"""
    
    portfolio_id: int
    periods: list[PeriodPerformance]  # 5개 기간별 성과
    calculated_at: str  # ISO 8601 UTC
    disclaimer: str  # 면책 문구
```

**PeriodPerformance Schema** (schemas.py:309-325):
```python
class PeriodPerformance(BaseModel):
    """단일 기간(YTD/1M/3M/6M/1Y)의 성과 지표"""
    
    period: Literal["ytd", "1m", "3m", "6m", "1y"]
    display_label: str  # 표시 레이블 (예: "YTD", "1개월")
    start_date: Optional[str] = None  # 기간 시작일 (YYYY-MM-DD)
    end_date: Optional[str] = None  # 기간 종료일 (YYYY-MM-DD)
    trading_days: int = 0  # 실제 거래일 수
    has_data: bool  # 데이터 존재 여부
    total_return_pct: Optional[float] = None  # 총 수익률 (%)
    annualized_return_pct: Optional[float] = None  # 연환산 수익률 (%)
    mdd_pct: Optional[float] = None  # 최대 낙폭 (%, ≤0)
```

**Key Components**:
- **5 periods**: YTD, 1M, 3M, 6M, 1Y (hardcoded in `_compute_period_dates()`)
- **Total Return**: (final_value / initial_value - 1) * 100
- **Annualized Return**: (1 + r_total)^(252 / trading_days) - 1
- **MDD (Max Drawdown)**: Uses `calculate_max_drawdown(values)` from backtest.metrics
  - Returns negative ratio, converted to percentage (e.g., -0.15 → -15.0%)

**MDD Calculation** (performance_summary.py:237-239):
```python
# 최대 낙폭 — calculate_max_drawdown은 음수 반환 (단위: 비율)
mdd_ratio = calculate_max_drawdown(values)
mdd_pct = mdd_ratio * 100.0  # % 단위로 변환
```

**Reference Implementation** (`backtest/metrics.py`):
```python
def calculate_max_drawdown(values: list[float]) -> float:
    """
    Running Maximum 대비 최대 낙폭을 계산한다.
    
    Args:
        values: Portfolio value series (first day = 1.0 baseline)
    
    Returns:
        MDD ratio as negative value (e.g., -0.15 for 15% drawdown)
    """
    if not values or len(values) < 2:
        return 0.0
    
    running_max = values[0]
    max_drawdown = 0.0
    
    for value in values[1:]:
        if value < running_max:
            drawdown = (value - running_max) / running_max
            max_drawdown = min(max_drawdown, drawdown)
        else:
            running_max = value
    
    return max_drawdown  # Always ≤ 0
```

**Caching**: Redis key `portfolio_perf_summary:{portfolio_id}:{YYYY-MM-DD}`, TTL=3600s

### 2.2 `get_portfolio_with_holdings()` 계약

**Location**: `backend/src/stock_picker/portfolio/service.py:87-100`

**Function Signature**:
```python
def get_portfolio_with_holdings(
    db: Session,
    portfolio_id: int,
    user_id: int,
) -> Portfolio | None:
    """포트폴리오와 보유 종목 함께 조회 (소유권 확인 포함)"""
    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
        .first()
    )
    if portfolio is None:
        return None
    # holdings 명시적 로드 (lazy="noload"이므로 직접 쿼리)
    portfolio.holdings = (
        db.query(PortfolioHolding).filter(PortfolioHolding.portfolio_id == portfolio_id).all()
    )
    return portfolio
```

**Return Type**: `Portfolio` with populated `holdings: list[PortfolioHolding]`

**PortfolioHolding Schema** (schemas.py:79-92):
```python
class HoldingResponse(BaseModel):
    """보유 종목 응답 (SPEC-STOCK-028: market/currency 필드 추가)"""
    
    id: int
    portfolio_id: int
    krx_code: str
    quantity: int
    avg_buy_price: Decimal
    added_at: datetime
    market: str = "KRX"  # "KRX" | "NYSE" | "NASDAQ"
    currency: str = "KRW"  # "KRW" | "USD"
```

**Key Contract**:
- Returns None if portfolio not found or ownership mismatch (401 check)
- Always populates holdings list (empty if no holdings)
- Supports mixed markets (KRX/NYSE/NASDAQ) with currency info

### 2.3 기존 MDD 계산 위치 및 재사용 경로

**Primary Implementation**: `backend/src/stock_picker/backtest/metrics.py` (inferred from imports)

**Used By**:
1. `portfolio/performance_summary.py:238` — Portfolio period performance MDD
   - Via `calculate_max_drawdown(values)` after portfolio value normalization
2. `portfolio/backtest.py` — Backtesting MDD calculation
3. Schema: `portfolio/schemas.py:299` — `BacktestResult.mdd: float`

**For SPEC-STOCK-031**:
- MDD calculation is **reusable** — same `calculate_max_drawdown()` function
- New alert type `portfolio_mdd` will use same algo
- Requires accumulating portfolio values over time (similar to performance_summary)

---

## 3. 알림 설정(Preferences) 인프라 (SPEC-STOCK-025)

### 3.1 `is_channel_enabled_async()` 시그니처와 fail-open 설계

**Location**: `backend/src/stock_picker/notifications/preferences.py:39-74`

**Async Signature**:
```python
async def is_channel_enabled_async(
    session: AsyncSession,
    user_id: int,
    alert_type: str,
    channel: str,
) -> bool:
    """알림 채널 활성 여부 판정 (비동기 — AsyncSession 사용).
    
    # @MX:NOTE: [AUTO] fail-open 설계 — 예외 시 True 반환하여 발송 누락 방지
    # @MX:SPEC: SPEC-STOCK-025 REQ-PREF-003, REQ-PREF-004, REQ-PREF-DISPATCH-006
    
    Args:
        session: AsyncSession.
        user_id: 사용자 ID.
        alert_type: 알림 유형 (예: "surge_drop").
        channel: 채널명 "email" 또는 "telegram".
    
    Returns:
        True이면 해당 채널로 발송 가능. 설정 행 없거나 예외 시 True (fail-open).
    """
    try:
        result = await session.execute(
            select(NotificationPreference).where(
                NotificationPreference.user_id == user_id,
                NotificationPreference.alert_type == alert_type,
            )
        )
        pref = result.scalar_one_or_none()
        if pref is None:
            # 설정 행 없음 → 기본 활성 (하위 호환)
            return True
        return bool(getattr(pref, f"{channel}_enabled", True))
    except Exception as e:
        # 조회 실패 시 기본 활성으로 처리 (REQ-PREF-DISPATCH-006)
        log.error("알림 채널 설정 조회 실패 — 기본값(활성) 사용", ...)
        return True  # Fail-open: always deliver on exception
```

**Synchronous Variant** (preferences.py:77-109):
```python
def is_channel_enabled_sync(db: Session, user_id: int, alert_type: str, channel: str) -> bool:
    """알림 채널 활성 여부 판정 (동기 — sync Session 사용)."""
    # Same fail-open logic for sync path
```

**Usage Pattern**:
```python
# In general_alert_service.py:543-555
if not await is_channel_enabled_async(session, alert.user_id, alert.alert_type, "email"):
    return
# Send email if enabled
```

**Opt-out Model**:
- **No entry** → default active (backward compatible)
- **Entry with email_enabled=false** → skip email
- **Entry with telegram_enabled=false** → skip telegram
- **Exception during check** → send (fail-open, REQ-PREF-DISPATCH-006)

### 3.2 신규 alert_type 추가 용이성

**Current Supported Types** (preferences.py:28-36):
```python
SUPPORTED_ALERT_TYPES: tuple[str, ...] = (
    "target_price",
    "surge_drop",
    "volume_spike",
    "ex_dividend",
    "rec_new",
    "rec_dropped",
    "rec_score_change",
)
```

**Adding New Type (e.g., `portfolio_return_change`)**:

1. **Update SUPPORTED_ALERT_TYPES tuple**:
   ```python
   SUPPORTED_ALERT_TYPES = (
       # ... existing ...
       "portfolio_return_change",
       "portfolio_mdd",
   )
   ```

2. **No DB migration needed** — `alert_type` is VARCHAR(20) at DB level, not enum
   - Supports arbitrary string values at DB
   - Validation happens in Python code

3. **Preference rows auto-created**:
   - `get_preferences()` returns all types with defaults
   - `upsert_preferences()` validates against SUPPORTED_ALERT_TYPES
   - New type queries return True by default (no entry exists)

4. **Email/Telegram delivery automatic**:
   - `is_channel_enabled_async()` checks NotificationPreference row for new type
   - If no entry, returns True (fail-open, backward compatible)
   - User can then disable via preferences API

**Schema for New Preferences Entry**:
```python
NotificationPreference(
    user_id=user_id,
    alert_type="portfolio_return_change",
    email_enabled=True,
    telegram_enabled=True,
    updated_at=now(),
)
```

**Integration Path for SPEC-STOCK-031**:
- Add `"portfolio_return_change"` and `"portfolio_mdd"` to SUPPORTED_ALERT_TYPES
- Validation in `upsert_preferences()` will auto-accept
- No additional changes needed for preferences API

---

## 4. 마이그레이션 분석

### 4.1 알림 관련 마이그레이션 연쇄

**Migration Order**:
1. **0014_notifications.py** (SPEC-013): Creates `notifications` table (inbox)
   - UNIQUE(user_id, type, krx_code, ref_date) — prevents day-level duplicates
   - Used by all alert types for inbox delivery

2. **0017_alerts.py** (SPEC-020): Creates `alerts` table (general alert rules)
   - Spans multiple alert types: target_price, surge_drop, ex_dividend, volume_spike
   - Index on (user_id, is_active) for query optimization

3. **0018_notification_preferences.py** (SPEC-025): Creates `notification_preferences` table
   - Maps (user_id, alert_type) → (email_enabled, telegram_enabled)
   - UNIQUE(user_id, alert_type) — one preference per alert type per user

**For SPEC-STOCK-031**:
- **No new migrations needed** for notification/preference tables (already support arbitrary alert_types)
- **New portfolio_alerts table MAY be needed** (separate from stock alerts)
  - Or extend existing `alerts` table with `portfolio_id` column
  - See 4.2 for schema recommendation

### 4.2 Portfolio Alert 테이블 설계 권고

**Option A: Extend Existing `alerts` Table**
- Add optional `portfolio_id` column
- Set `krx_code=NULL` for portfolio-level alerts
- Pro: Reuse existing infrastructure, unified alert query
- Con: Semantically mixes stock and portfolio domains

**Option B: Create New `portfolio_alerts` Table** (RECOMMENDED)
```sql
CREATE TABLE portfolio_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL (FK users.id CASCADE),
    portfolio_id INTEGER NOT NULL (FK portfolios.id CASCADE),
    alert_type VARCHAR(20) NOT NULL,  -- 'portfolio_return_change', 'portfolio_mdd'
    condition_value FLOAT NOT NULL,  -- Threshold return % or MDD %
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_triggered BOOLEAN NOT NULL DEFAULT false,
    triggered_at TIMESTAMP WITH TIMEZONE NULLABLE,
    triggered_message VARCHAR(500) NULLABLE,
    created_at TIMESTAMP WITH TIMEZONE NOT NULL DEFAULT now(),
    
    INDEX ix_portfolio_alerts_user_portfolio_active (user_id, portfolio_id, is_active)
);
```

**Rationale for Option B**:
- Clearer domain separation (stock alerts vs portfolio alerts)
- Portfolio-specific queries don't need `krx_code` filtering
- Aligns with SPEC-030 performance_summary logic
- Enables future portfolio-level aggregations
- **No backward compatibility burden** (new table, new feature)

---

## 5. 구현 권고사항

### 5.1 신규 Alert Type 추천 이름

**For SPEC-STOCK-031** (포트폴리오 알림 강화):

1. **`portfolio_return_change`** — Total Return Threshold Alert
   - Condition: Portfolio total return reaches/exceeds threshold
   - condition_value: Return % threshold (e.g., 5.0 for +5%)
   - direction: `above`/`below` (above = target return achieved, below = negative threshold)
   - Metric source: `PerformanceSummaryResponse.periods[0].total_return_pct` (YTD or configurable)
   - Check frequency: Daily (end-of-day) or on-demand

2. **`portfolio_mdd`** — Max Drawdown Threshold Alert
   - Condition: Portfolio MDD exceeds threshold
   - condition_value: MDD % threshold (e.g., -10.0 for -10% drawdown)
   - direction: Fixed to `below` (MDD is always ≤ 0)
   - Metric source: `PerformanceSummaryResponse.periods[period].mdd_pct`
   - Check frequency: Daily or on-demand

**Alternative Naming** (if verbosity preferred):
- `portfolio_total_return_alert` (longer, more descriptive)
- `portfolio_drawdown_alert` (shorter, but less precise)

**Recommendation**: Stick with `portfolio_return_change` and `portfolio_mdd` (consistent with existing naming)

### 5.2 포트폴리오 알림 체크 함수 설계 방향

**Approach: Extend `check_and_trigger_all_alerts()` vs New Function**

**Option A: Single Unified Function** (RECOMMENDED)
```python
async def check_and_trigger_all_alerts(session: AsyncSession) -> int:
    """Check both stock and portfolio alerts (10-minute interval)"""
    
    # Existing logic: stock alerts (SPEC-020~024)
    triggered_count = await _check_stock_alerts(session)
    
    # New logic: portfolio alerts (SPEC-031)
    triggered_count += await _check_portfolio_alerts(session)
    
    return triggered_count
```

**Option B: Separate Job**
```python
async def check_portfolio_alerts() -> None:
    """New 10-minute job for portfolio alerts"""
    # Dedicated logic
```

**Recommendation: Option A**
- Reuses existing scheduler infrastructure
- Single entry point for alert checking
- Consistent trigger frequencies
- Easier to coordinate state/transactions

**Helper Function Design** (`_check_portfolio_alerts`):
```python
async def _check_portfolio_alerts(session: AsyncSession) -> int:
    """Check active portfolio alerts and trigger notifications.
    
    Similar structure to check_and_trigger_all_alerts but portfolio-scoped:
    1. Query active portfolio alerts: is_active=true AND is_triggered=false
    2. For each alert:
       a. Fetch portfolio performance summary (use Redis cache)
       b. Extract relevant metric (total_return_pct or mdd_pct)
       c. Evaluate condition (compare against threshold)
       d. If triggered:
          - Update portfolio_alerts: is_triggered=true, triggered_at, triggered_message
          - Create notification with portfolio context
          - Send email/telegram (channel checks)
    3. Return count of triggered alerts
    """
```

### 5.3 스케줄러 연동 방안

**Current Setup**:
```python
_scheduler.add_job(
    _run_general_alert_check,
    IntervalTrigger(minutes=10),
    id="check_alerts",
    replace_existing=True,
)
```

**For SPEC-STOCK-031**:

**Minimal Change Path**:
1. Extend `_run_general_alert_check()` to call both `check_and_trigger_all_alerts()` AND `_check_portfolio_alerts()`
   ```python
   async def _run_general_alert_check() -> None:
       async with AsyncSessionLocal() as session:
           stock_count = await check_and_trigger_all_alerts(session)
           portfolio_count = await _check_portfolio_alerts(session)
           log.info("알림 점검 완료", stock=stock_count, portfolio=portfolio_count)
   ```

2. No scheduler config change needed (reuse 10-minute interval)

**Alternative Path** (if portfolio alerts need different frequency):
```python
_scheduler.add_job(
    _run_portfolio_alert_check,
    IntervalTrigger(minutes=10),  # Or different interval
    id="check_portfolio_alerts",
    replace_existing=True,
)
```

**Recommendation**: Minimal change path (extend existing job)

### 5.4 잠재적 위험 및 제약

#### 5.4.1 Performance Calculation Latency
- `calculate_performance_summary()` fetches FDR price data for all holdings (can be slow)
- Redis cache TTL=3600s (1 hour) mitigates repeated calls
- **Risk**: If portfolio has many holdings or FDR is slow, alert check may timeout
- **Mitigation**: 
  - Use cached summary if available (don't always refresh)
  - Set async timeout on portfolio alert check
  - Consider async cache update separate from alert logic

#### 5.4.2 MDD Calculation Cost
- `calculate_max_drawdown()` is O(N) on the portfolio values series
- For 1-year lookback at daily granularity: ~252 days
- **Risk**: Negligible for typical portfolios
- **No mitigation needed**

#### 5.4.3 Daily vs Intra-day Metrics
- Performance summaries use end-of-day close prices (via FDR)
- Can't detect MDD changes intra-day (only daily granularity)
- **Risk**: User misses intra-day drawdown events
- **Consideration**: Acceptable for SPEC-STOCK-031 (daily alerts reasonable for portfolio-level)

#### 5.4.4 Return Calculation Baseline
- Which period to use for "total return change"? (YTD, 1M, 1Y, custom?)
- SPEC-STOCK-031 doesn't specify
- **Recommendation**: 
  - Default to YTD (most common portfolio performance metric)
  - Allow user to configure via alert `condition_direction` or new column
  - Document clearly

#### 5.4.5 Idempotency for Daily Alerts
- Once `is_triggered=true`, alert never fires again
- **Risk**: If condition changes (e.g., return drops then rises back above threshold), no second alert
- **Workaround**: 
  - User can delete and re-create alert
  - Or implement "re-arm" logic after N days
- **Recommendation**: Document this one-time-per-alert behavior clearly in SPEC

#### 5.4.6 Notification Type Coverage
- Preferences table uses `alert_type` as key
- If portfolio alert type not in `SUPPORTED_ALERT_TYPES`, preference query returns None
- **Risk**: None (fail-open default, user can set preferences)
- **Mitigation**: Update `SUPPORTED_ALERT_TYPES` when new types added

---

## 6. 참조 구현 (Reference Implementations)

### 6.1 알림 조건 평가 순수 함수 패턴

**Location**: general_alert_service.py:117-248

**Pattern for Stock Alerts**:
```python
def check_target_price(alert: Any, price_data: dict[str, Any] | None) -> tuple[bool, str]:
    """순수 함수: 상태 변경 없음, DB 쿼리 없음"""
    if price_data is None:
        return False, ""
    
    close = price_data.get("close_price", 0.0)
    target = alert.condition_value
    direction = alert.condition_direction or "above"
    
    if direction == "above" and close >= target:
        msg = f"{alert.krx_code} 현재가 {close:,.0f}원이 목표가 {target:,.0f}원에 도달했습니다."
        return True, msg
    
    if direction == "below" and close <= target:
        msg = f"{alert.krx_code} 현재가 {close:,.0f}원이 하한 목표가 {target:,.0f}원에 도달했습니다."
        return True, msg
    
    return False, ""
```

**For Portfolio Alerts** (SPEC-031):
```python
def check_portfolio_return(
    alert: Any,  # portfolio_alerts row
    performance: PerformanceSummaryResponse,
) -> tuple[bool, str]:
    """순수 함수: 포트폴리오 수익률 조건 평가"""
    
    # Extract period (could be from alert or fixed to YTD)
    period_perf = performance.periods[0]  # YTD
    if not period_perf.has_data or period_perf.total_return_pct is None:
        return False, ""
    
    current_return = period_perf.total_return_pct
    threshold = alert.condition_value
    direction = alert.condition_direction or "above"
    
    if direction == "above" and current_return >= threshold:
        msg = f"포트폴리오 수익률이 {current_return:.2f}%에 도달했습니다 (목표: {threshold:.2f}%)"
        return True, msg
    
    if direction == "below" and current_return <= threshold:
        msg = f"포트폴리오 수익률이 {current_return:.2f}%로 하락했습니다 (경고: {threshold:.2f}%)"
        return True, msg
    
    return False, ""

def check_portfolio_mdd(
    alert: Any,
    performance: PerformanceSummaryResponse,
) -> tuple[bool, str]:
    """순수 함수: 포트폴리오 MDD 조건 평가"""
    
    period_perf = performance.periods[0]  # YTD or configurable
    if not period_perf.has_data or period_perf.mdd_pct is None:
        return False, ""
    
    current_mdd = period_perf.mdd_pct  # Negative value
    threshold = alert.condition_value  # Negative value (e.g., -10.0)
    
    # MDD alert triggers when drawdown exceeds threshold (more negative)
    if current_mdd <= threshold:  # e.g., -15% <= -10%
        msg = f"포트폴리오 최대낙폭이 {current_mdd:.2f}%에 도달했습니다 (경고: {threshold:.2f}%)"
        return True, msg
    
    return False, ""
```

### 6.2 알림 생성 → 발송 흐름

**Location**: general_alert_service.py:251-287, 543-595

**Pattern to Reuse** (for portfolio):
```python
async def _try_send_alert_email(alert: Any, message: str, session: AsyncSession) -> None:
    """이메일 구독자에게 알림 이메일 발송 (best-effort)"""
    # 1. Check channel enabled
    if not await is_channel_enabled_async(session, alert.user_id, alert.alert_type, "email"):
        return
    
    # 2. Fetch subscription
    try:
        result = await session.execute(
            select(EmailSubscription).where(
                EmailSubscription.user_id == alert.user_id,
                EmailSubscription.is_active.is_(True),
            )
        )
        sub = result.scalar_one_or_none()
        if sub:
            send_general_alert_email(sub.email, alert.krx_code, alert.alert_type, message)
    except Exception as e:
        log.error("알림 이메일 발송 실패 user_id=%s: %s", alert.user_id, e)
```

**For Portfolio Alerts**:
```python
async def _try_send_portfolio_alert_email(
    alert: Any,  # portfolio_alerts row
    portfolio_name: str,
    message: str,
    session: AsyncSession,
) -> None:
    """포트폴리오 알림 이메일 발송"""
    if not await is_channel_enabled_async(session, alert.user_id, alert.alert_type, "email"):
        return
    
    try:
        result = await session.execute(
            select(EmailSubscription).where(
                EmailSubscription.user_id == alert.user_id,
                EmailSubscription.is_active.is_(True),
            )
        )
        sub = result.scalar_one_or_none()
        if sub:
            # Use existing email_service, adapt for portfolio context
            subject = f"[포트폴리오 알림] {portfolio_name}"
            body = f"{message}\n\n발송 시각: {datetime.now(timezone.utc).isoformat()}"
            _send_email(sub.email, subject, body)
    except Exception as e:
        log.error("포트폴리오 알림 이메일 발송 실패 user_id=%s: %s", alert.user_id, e)
```

### 6.3 Notification 페이로드 생성

**Location**: general_alert_service.py:251-287

**Stock Alert Pattern**:
```python
def build_notification_payload(
    alert: Any,
    message: str,
    triggered_at: datetime,
) -> dict[str, Any]:
    """Notification 테이블 INSERT용 딕셔너리 생성"""
    type_label_map = {
        "target_price": "목표가 알림",
        "surge_drop": "급등락 알림",
        # ...
    }
    title = f"[{type_label_map.get(alert.alert_type, '알림')}] {alert.krx_code}"
    if hasattr(alert, "stock_name") and alert.stock_name:
        title = f"[{type_label_map.get(alert.alert_type, '알림')}] {alert.stock_name}({alert.krx_code})"
    
    return {
        "user_id": alert.user_id,
        "type": alert.alert_type,
        "krx_code": alert.krx_code,
        "title": title,
        "body": message,
        "is_read": False,
        "ref_date": triggered_at.date(),
        "related_alert_id": None,
    }
```

**For Portfolio Alerts**:
```python
def build_portfolio_notification_payload(
    alert: Any,  # portfolio_alerts row
    portfolio_name: str,
    message: str,
    triggered_at: datetime,
) -> dict[str, Any]:
    """포트폴리오 알림 Notification 페이로드"""
    type_label_map = {
        "portfolio_return_change": "포트폴리오 수익률 알림",
        "portfolio_mdd": "포트폴리오 낙폭 알림",
    }
    title = f"[{type_label_map.get(alert.alert_type, '알림')}] {portfolio_name}"
    
    return {
        "user_id": alert.user_id,
        "type": alert.alert_type,
        "krx_code": f"PORT_{alert.portfolio_id}",  # Pseudo-code for portfolio context
        "title": title,
        "body": message,
        "is_read": False,
        "ref_date": triggered_at.date(),
        "related_alert_id": None,  # Or link to portfolio_alerts.id if schema supports
    }
```

### 6.4 CRUD 엔드포인트 패턴

**Location**: general_alert_router.py (SPEC-020), schema validation in general_alert_service.py

**Stock Alert CRUD**:
```python
# POST /alerts — create
@router.post("/alerts", response_model=AlertSchema)
async def create_alert(
    current_user: User = Depends(get_current_user),
    data: AlertCreate = Body(...),
    session: AsyncSession = Depends(get_async_session),
):
    return await general_alert_service.create_alert(session, current_user.id, data)

# GET /alerts — list
@router.get("/alerts", response_model=list[AlertSchema])
async def list_alerts(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    return await general_alert_service.get_user_alerts(session, current_user.id)

# PUT /alerts/{id} — update (ownership check inside service)
@router.put("/alerts/{alert_id}", response_model=AlertSchema)
async def update_alert(
    alert_id: int,
    data: AlertUpdate = Body(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    return await general_alert_service.update_alert(session, alert_id, current_user.id, data)

# DELETE /alerts/{id}
@router.delete("/alerts/{alert_id}")
async def delete_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    await general_alert_service.delete_alert(session, alert_id, current_user.id)
    return {"message": "알림이 삭제되었습니다"}
```

**For Portfolio Alerts** (SPEC-031):
```python
# Similar structure, but parameterized by portfolio_id and using portfolio_alerts table

@router.post("/portfolios/{portfolio_id}/alerts", response_model=PortfolioAlertSchema)
async def create_portfolio_alert(
    portfolio_id: int,
    data: PortfolioAlertCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    # Ownership check: portfolio belongs to current_user
    # Then create alert
    pass

@router.get("/portfolios/{portfolio_id}/alerts", response_model=list[PortfolioAlertSchema])
async def list_portfolio_alerts(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    pass

# etc.
```

### 6.5 데이터베이스 트랜잭션 패턴

**Location**: general_alert_service.py:456-540

**Pattern for Alert Trigger**:
```python
try:
    # 1. Update alert state
    upd = update(Alert).where(Alert.id == alert.id).values(...)
    await session.execute(upd)
    
    # 2. Insert notification (with UNIQUE constraint conflict handling)
    notif_payload = build_notification_payload(...)
    ins = pg_insert(Notification).values(**notif_payload)
    ins = ins.on_conflict_do_nothing(constraint="uq_notification_user_type_code_date")
    await session.execute(ins)
    
    # 3. Commit (atomic, both succeed or both fail)
    await session.commit()
    
    # 4. Send emails/telegrams (outside transaction, best-effort)
    await _try_send_alert_email(...)
    await _try_send_telegram(...)
    
except Exception as e:
    await session.rollback()
    log.exception("alert trigger error", alert_id=alert.id)
```

**For Portfolio Alerts**:
Same pattern, but UPDATE portfolio_alerts instead of alerts.

---

## 7. 요약 및 다음 단계

### 7.1 SPEC-STOCK-031 구현 최소 요구사항

1. **New Table** (or extend existing):
   - `portfolio_alerts` 테이블 (user_id, portfolio_id, alert_type, condition_value, is_active, is_triggered, ...)

2. **New Alert Types**:
   - `portfolio_return_change` → in `SUPPORTED_ALERT_TYPES`
   - `portfolio_mdd` → in `SUPPORTED_ALERT_TYPES`

3. **Check Functions**:
   - `check_portfolio_return()` — pure function
   - `check_portfolio_mdd()` — pure function
   - `_check_portfolio_alerts()` — async orchestration

4. **Scheduler Integration**:
   - Extend existing `_run_general_alert_check()` job (10-minute interval)

5. **CRUD Endpoints**:
   - `POST /portfolios/{portfolio_id}/alerts` — create
   - `GET /portfolios/{portfolio_id}/alerts` — list
   - `PUT /portfolios/{portfolio_id}/alerts/{alert_id}` — update
   - `DELETE /portfolios/{portfolio_id}/alerts/{alert_id}` — delete

6. **Email/Telegram**:
   - Reuse existing `is_channel_enabled_async()` and `_send_email()` infrastructure

7. **Notification**:
   - Reuse existing `notifications` table + UNIQUE constraint
   - Insert via `on_conflict_do_nothing()` pattern

### 7.2 기존 인프라와의 정합성

- **Backward Compatible**: No changes to existing alert types or tables
- **Type-agnostic**: `is_channel_enabled_async()`, preferences work with any alert_type
- **Async-first**: Consistent with existing general_alert_service patterns
- **Error Isolation**: Graceful degradation for API failures
- **Redis Caching**: Leverage existing performance_summary Redis cache

### 7.3 위험 완화 전략

- **Performance**: Cache portfolio summaries, use Redis, set async timeouts
- **Idempotency**: Leverage notifications UNIQUE constraint + one-time-per-alert-per-day model
- **Preference Updates**: Document in-code that new alert_types must be added to SUPPORTED_ALERT_TYPES
- **Testing**: Unit tests for check functions, integration tests for full trigger flow

---

## Appendix: File Locations Reference

**Core Alert Infrastructure**:
- Alerts model: `/backend/src/stock_picker/db/models.py:609-648`
- Alert service: `/backend/src/stock_picker/notifications/general_alert_service.py`
- Alert router: `/backend/src/stock_picker/notifications/general_alert_router.py`
- Preferences: `/backend/src/stock_picker/notifications/preferences.py`
- Scheduler: `/backend/src/stock_picker/scheduler/jobs.py:349-421`

**Portfolio Infrastructure**:
- Performance summary: `/backend/src/stock_picker/portfolio/performance_summary.py`
- Portfolio service: `/backend/src/stock_picker/portfolio/service.py`
- Portfolio schemas: `/backend/src/stock_picker/portfolio/schemas.py:309-335`
- Backtest metrics: `/backend/src/stock_picker/backtest/metrics.py` (MDD calculation)

**Notification Delivery**:
- Email service: `/backend/src/stock_picker/notifications/email_service.py`
- Inbox router: `/backend/src/stock_picker/notifications/inbox_router.py`
- Rec change: `/backend/src/stock_picker/notifications/rec_change.py`

**Migrations**:
- Alerts table: `/backend/alembic/versions/0017_alerts.py`
- Notifications table: `/backend/alembic/versions/0014_notifications.py`
- Preferences table: `/backend/alembic/versions/0018_notification_preferences.py`

**Tests**:
- General alert tests: `/backend/tests/unit/test_general_alerts.py`
- Alert service tests: `/backend/tests/unit/test_alert_service.py`
- Preferences tests: `/backend/tests/unit/test_notification_preferences.py`

---

**End of Research Document**
