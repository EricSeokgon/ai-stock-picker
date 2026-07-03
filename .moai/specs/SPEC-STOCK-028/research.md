# SPEC-STOCK-028 Research Notes — 해외 자산 지원

## 1. 현황 분석

### 1.1 PortfolioHolding 모델 (backend/src/stock_picker/db/models.py:246)

```python
class PortfolioHolding(Base):
    __tablename__ = "portfolio_holdings"
    id: Mapped[int]
    portfolio_id: Mapped[int]  # FK → portfolios.id
    krx_code: Mapped[str] = mapped_column(String(10))  # KRX 코드만 지원
    quantity: Mapped[int]
    avg_buy_price: Mapped[Decimal]  # KRW 기준
    added_at: Mapped[datetime]
```

**문제점**: `krx_code` 컬럼이 KRX(한국거래소) 코드 전용. 미국 주식(AAPL, MSFT)·ETF(SPY, VOO) 저장 불가.  
`avg_buy_price`에 통화 정보 없음 — 원화/달러 혼재 시 성과 계산 불가.

### 1.2 서비스 레이어 분석

#### add_holding (portfolio/service.py:56)
- 현재 시그니처: `(db, portfolio_id, krx_code, quantity, avg_buy_price)`
- **변경 필요**: market/currency 파라미터 추가

#### calculate_performance (portfolio/service.py:96)
- `get_current_price(h.krx_code)` → Redis에서 KRX 실시간가 조회
- `get_sector(h.krx_code)` → 섹터 조회
- **변경 필요**: 해외 종목 현재가 조회 + KRW 환율 변환

#### optimize_portfolio (portfolio/service.py:235)
- `holdings_data` 에 `krx_code`, `sector` 포함 후 Claude AI 호출
- **변경 필요**: 해외 ticker + 통화 정보를 Claude 프롬프트에 포함

### 1.3 FDR 사용 패턴 (기존 코드에서 확인)

**dividends.py** 패턴:
```python
import FinanceDataReader as fdr
# 동기 FDR → run_in_executor 격리
df = fdr.StockListing("KRX")   # KRX 종목 목록
```

**risk_analysis.py** 패턴:
```python
# FDR 가격 데이터 → np.corrcoef, np.std (scipy 금지)
# run_in_executor로 동기 FDR 격리
```

**해외 FDR API**:
- `fdr.StockListing("NYSE")` — NYSE 종목 목록
- `fdr.StockListing("NASDAQ")` — NASDAQ 종목 목록
- `fdr.DataReader("AAPL", start, end)` — 미국 주식 가격 (USD)
- `fdr.DataReader("VOO", start, end)` — 해외 ETF 가격 (USD)

### 1.4 환율 처리

**현재**: 환율 처리 로직 없음.  
**방안**: FDR 환율 조회 or 외부 API (exchangerate-api.com 등).

FDR은 `fdr.DataReader("USD/KRW")` 형태로 환율 조회 가능 (Yahoo Finance 기반).  
Redis TTL=3600s 캐시 패턴 적용 (dividends.py 패턴 재사용).

### 1.5 DB 마이그레이션 현황

최신 마이그레이션: `0018_notification_preferences.py`  
신규 마이그레이션 필요: `0019_portfolio_foreign_asset.py`

### 1.6 프론트엔드 (frontend/src/api/portfolio.ts)

```typescript
export interface Holding {
  id: number;
  portfolio_id: number;
  krx_code: string;   // 변경 필요: ticker + market 구분
  quantity: number;
  avg_buy_price: number;
  created_at: string;
}
```

`HoldingCreate` 폼에 market 선택 UI 추가 필요 (KRX / NYSE / NASDAQ).

---

## 2. 설계 결정

### 2.1 컬럼 전략: krx_code → ticker + market 분리

**옵션 A**: `krx_code` 유지, `market` 컬럼 추가 (backward compatible)  
**옵션 B**: `krx_code` → `ticker` rename + `market` + `currency` 추가

**결정**: **옵션 A** — `krx_code`를 `ticker`로 alias 처리하되, DB 컬럼명은 그대로 유지.
- 마이그레이션 단순화 (rename 없음)
- 기존 코드 수정 최소화

DB 변경: `portfolio_holdings` 테이블에 2개 컬럼 추가:
- `market` VARCHAR(10) DEFAULT 'KRX' NOT NULL — 'KRX', 'NYSE', 'NASDAQ'
- `currency` VARCHAR(3) DEFAULT 'KRW' NOT NULL — 'KRW', 'USD'

### 2.2 환율 서비스

신규 모듈: `stock_picker/portfolio/fx_rate.py`
- `async def get_usd_krw_rate(redis) -> float`
- FDR `fdr.DataReader("USD/KRW")` 동기 조회 → run_in_executor
- Redis 캐시 TTL=3600s (`fx:USD:KRW:{today}`)
- 장애 시 fallback: 하드코딩 기본값(1350.0) + 경고 로그

### 2.3 성과 계산 변경

`calculate_performance()`:
- 해외 종목: FDR `DataReader(ticker)` 최신 종가 조회 (비동기화)
- USD 현재가 → `* fx_rate` → KRW로 변환
- avg_buy_price가 USD인 경우도 KRW 환산
- `price_unavailable`은 해외 조회 실패 시에도 동일 처리

### 2.4 HoldingCreate 확장

```python
class HoldingCreate(BaseModel):
    krx_code: str          # ticker (AAPL, 005930 등)
    quantity: int
    avg_buy_price: Decimal  # 매수 당시 통화 기준
    market: Literal["KRX", "NYSE", "NASDAQ"] = "KRX"
    currency: Literal["KRW", "USD"] = "KRW"
```

### 2.5 리스크 분석 / AI 최적화 통합

- `risk_analysis.py`: 해외 ticker → FDR DataReader 경로 분기
- `optimize_portfolio()`: Claude 프롬프트에 market/currency 정보 포함
- `dividends.py`: 해외 종목은 dividend_available=False 처리 (Phase 1 스코프 외)

---

## 3. Out-of-Scope (이번 SPEC-028)

- 해외 종목 실시간 WebSocket 가격 피드 (별도 SPEC)
- 해외 종목 배당 데이터 수집 (FDR 해외 배당 API는 불안정)
- 다중 통화 (EUR, JPY 등) — USD/KRW만 지원
- 해외 종목 스크리너/추천 (recommendation, screener 도메인)

---

## 4. 영향 파일 목록

### Backend
- `db/models.py` — PortfolioHolding: market, currency 컬럼 추가
- `portfolio/schemas.py` — HoldingCreate, HoldingResponse, HoldingPerformance 확장
- `portfolio/service.py` — add_holding, calculate_performance 변경
- `portfolio/fx_rate.py` — 신규: 환율 서비스
- `portfolio/risk_analysis.py` — 해외 ticker 분기
- `portfolio/ai_analysis.py` — Claude 프롬프트 market 정보 포함
- `portfolio/router.py` — HoldingCreate 파라미터 통과
- `alembic/versions/0019_portfolio_foreign_asset.py` — 신규 마이그레이션

### Frontend
- `frontend/src/api/portfolio.ts` — Holding, HoldingCreate 타입 확장
- `frontend/src/components/Portfolio*.tsx` (보유 종목 추가 폼) — market 선택 UI

### Tests
- `tests/test_portfolio_service.py` — 해외 자산 성과 계산 테스트
- `tests/test_fx_rate.py` — 신규: 환율 서비스 TDD 테스트

---

## 5. 리스크

1. **FDR 해외 가격 조회 레이트 리밋**: Yahoo Finance 기반으로 과도한 호출 시 차단 가능  
   → Redis 캐시 TTL=86400s (하루 1회) 적용
2. **환율 변동**: 매수 당시 환율과 현재 환율 차이로 수익률 왜곡  
   → avg_buy_price를 매수 당시 통화 그대로 저장, 성과 계산 시에만 실시간 환율 적용
3. **ticker 충돌**: KRX `000020`과 NYSE ticker 구분  
   → `market` 컬럼으로 명확히 구분, DB unique constraint 변경 필요
