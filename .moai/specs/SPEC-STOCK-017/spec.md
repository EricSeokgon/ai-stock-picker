---
id: SPEC-STOCK-017
version: 0.1.0
status: draft
created: 2026-06-12
updated: 2026-06-12
author: ircp
priority: medium
issue_number: null
---

# SPEC-STOCK-017: 사용자 포트폴리오 성과 분석 (Portfolio Performance Analysis)

## HISTORY

- 2026-06-12 (draft): 초안 작성. 기존 `GET /portfolios/{id}/performance` 성과 계산을 확장하여 성과 분류·섹터별 집계·도넛 차트·성과 대시보드 패널을 추가.

---

## 1. 개요 (Overview)

사용자 포트폴리오의 보유 종목별 수익률과 전체 수익률을 계산하고, 성과를 고/일반/저수익으로 분류하며, 섹터별 수익률을 집계하여 도넛 차트와 성과 대시보드 패널로 시각화한다.

### 1.1 배경 및 기존 자산 (반드시 확장으로 설계)

이 SPEC은 **신규 기능이 아니라 기존 성과 계산의 확장**이다. 다음 자산이 이미 존재한다:

- **백엔드 엔드포인트**: `GET /portfolios/{portfolio_id}/performance`가 이미 존재(`portfolio/router.py`, 소유권 검증·404 포함).
- **백엔드 서비스**: `portfolio/service.py`의 `calculate_performance(db, portfolio_id, user_id)`가 보유 종목별 수익률과 전체 수익률을 이미 계산. 다만 내부에서 캐시 없는 자체 `_get_current_price`(FinanceDataReader 직접 호출)를 사용.
- **응답 스키마**: `portfolio/schemas.py`의 `PortfolioPerformance`·`HoldingPerformance`가 존재(`holdings[]`, `total_invested`, `total_current`, `total_return_pct`).
- **프론트 성과 요약**: `pages/Portfolio.tsx`의 `PortfolioDetail` 컴포넌트가 총 투자금·현재 평가금·수익률·종목 수 카드를 이미 렌더(`api/portfolio.ts`의 `apiGetPerformance` 호출).
- **섹터 매핑 함수**: `portfolio/ai_analysis.py`의 `_get_sector(krx_code)` + `_SECTOR_MAP`(KRX 코드 앞자리 → 섹터명 간이 매핑). `advice/service.py`에도 동일 패턴 복제본 존재.
- **차트 라이브러리**: 프론트에 `recharts ^2.14.1`이 이미 설치됨(`SectorTrendChart`·`PriceChart`에서 사용). 단, `PieChart`/`Pie`(도넛)는 아직 미사용.

### 1.2 이 SPEC이 새로 더하는 것

1. 보유 종목별 수익률 계산 결과에 **성과 분류 라벨**(고수익/일반/저수익) 추가.
2. **섹터별 수익률 집계** 응답 필드 추가(보유 종목의 섹터 태그 기반 가중평균).
3. 응답 스키마를 확장하여 **성과 분류 요약**(고/일반/저수익 종목 수·비중) 추가.
4. 프론트에 **성과 대시보드 패널**(분류 목록 + 섹터 집계) 추가.
5. 프론트에 **도넛 차트**(고/일반/저수익 분류 비율) 추가.
6. 가격 조회를 캐시 없는 자체 `_get_current_price`에서 **`realtime/price_feed.py`의 `get_current_price`(Redis TTL 60초 캐시 내장)로 통일**.

---

## 2. 성과 계산 아키텍처 (Performance Calculation Architecture)

```
[프론트] Portfolio.tsx
   │  apiGetPerformance(token, portfolioId)
   ▼
GET /portfolios/{portfolio_id}/performance   (portfolio/router.py · 소유권 검증)
   │
   ▼
service.calculate_performance(db, portfolio_id, user_id)   (확장)
   ├─ get_portfolio_with_holdings()                         (재사용)
   ├─ holding별:
   │    current_price ← realtime.price_feed.get_current_price(krx_code)  (가격 소스 통일)
   │    return_pct = (current_price − avg_buy_price) / avg_buy_price × 100
   │    classification ← classify(return_pct)               (신규: 고/일반/저수익)
   │    sector ← shared._get_sector(krx_code)               (신규: 섹터 태그)
   ├─ total_return_pct = Σ(invested) 기준 가중평균          (재사용)
   ├─ classification_summary ← 고/일반/저수익 종목 수·투자비중  (신규)
   └─ sector_performance ← 섹터별 invested 가중평균 수익률    (신규)
   ▼
PortfolioPerformance (스키마 확장)
   ▼
[프론트] 성과 대시보드 패널 + 도넛 차트
```

### 2.1 계산 규칙

- **보유 종목별 수익률**: `return_pct = (현재가 − 매입가) / 매입가 × 100` (소수점 2자리 반올림).
- **포트폴리오 전체 수익률**: 보유 비중(투자금액) 가중평균. 즉 `total_return_pct = (Σ현재평가금 − Σ투자금) / Σ투자금 × 100`. 이는 매입가 가중평균과 수학적으로 동치이며 기존 구현을 유지한다.
- **성과 분류**:
  - 고수익(`high`): `return_pct >= +5.0`
  - 일반(`normal`): `-5.0 < return_pct < +5.0`
  - 저수익(`low`): `return_pct <= -5.0`
- **섹터별 수익률**: 동일 섹터 보유 종목들의 투자금액 가중평균 수익률.
- **현재가 조회 실패 처리**: `get_current_price`가 `None` 반환 시 해당 종목은 매입가로 대체(`return_pct = 0.0`)하고 `price_unavailable` 플래그를 표시한다.

### 2.2 DB 스키마 결정 (신규 테이블/컬럼 없음)

**결정: 온더플라이 계산. 신규 마이그레이션 없음.**

근거:
- 성과는 현재가(변동)에 의존하므로 스냅샷 저장은 즉시 stale 데이터가 됨.
- 가격 캐시는 `get_current_price`의 Redis TTL 60초로 이미 처리됨(요청 단위 캐싱).
- 히스토리컬 성과 추이(일자별 스냅샷)는 본 SPEC **범위 밖**(아래 제외 항목 참조). 추가 시 별도 SPEC에서 `portfolio_performance_snapshots` 테이블 도입.
- 최신 마이그레이션은 `0015_ai_advice.py`이며 본 SPEC은 이를 증가시키지 않는다.

---

## 3. API 설계 (API Design)

### 3.1 엔드포인트 (기존 확장)

`GET /portfolios/{portfolio_id}/performance` — **기존 엔드포인트의 응답을 확장**(신규 경로 추가 아님).

- 인증: `get_current_user` (JWT Bearer) — 기존 유지.
- 소유권: 타 사용자 포트폴리오 접근 시 404 — 기존 유지.
- 응답 모델: `PortfolioPerformance`(확장).

### 3.2 확장 응답 스키마

기존 필드(`holdings`, `total_invested`, `total_current`, `total_return_pct`)는 **하위호환 유지**하고 아래를 추가한다.

```jsonc
{
  "holdings": [
    {
      "krx_code": "005930",
      "quantity": 10,
      "avg_buy_price": 70000.0,
      "current_price": 75000.0,
      "return_pct": 7.14,
      "classification": "high",        // 신규: high | normal | low
      "sector": "전자/반도체",          // 신규
      "price_unavailable": false        // 신규: 현재가 조회 실패 여부
    }
  ],
  "total_invested": 700000.0,
  "total_current": 750000.0,
  "total_return_pct": 7.14,
  "classification_summary": {           // 신규
    "high":   { "count": 1, "invested_pct": 60.0 },
    "normal": { "count": 0, "invested_pct": 0.0 },
    "low":    { "count": 1, "invested_pct": 40.0 }
  },
  "sector_performance": [               // 신규: 투자금 내림차순 정렬
    { "sector": "전자/반도체", "invested": 420000.0, "invested_pct": 60.0, "return_pct": 7.14 }
  ]
}
```

주의: 프론트 `api/portfolio.ts`의 기존 타입은 `total_current` 대신 `current_value`/`total_return`/`holdings_count`를 참조한다(드리프트 존재). RUN 단계에서 백엔드 응답 키와 프론트 타입을 정합화할 것(REQ-PERF-006).

---

## 4. 프론트엔드 컴포넌트 (Frontend Components)

### 4.1 성과 대시보드 패널

`pages/Portfolio.tsx`의 `PortfolioDetail` 내부 기존 성과 요약 카드 **아래**에 패널 추가:

- **수익률 요약**: 기존 요약 카드 유지(총 투자금·현재 평가금·수익률·종목 수).
- **분류 목록**: 고수익/일반/저수익 그룹별로 종목 칩 목록 표시. 각 칩은 종목코드 + 수익률(색상: 양수 녹색, 음수 적색).
- **섹터별 집계**: 섹터명 + 투자비중 + 섹터 수익률 행 목록(투자금 내림차순).

### 4.2 도넛 차트

- recharts `PieChart` + `Pie`(innerRadius 설정으로 도넛) 사용.
- 데이터: 고/일반/저수익 **종목 수 또는 투자비중** 3-슬라이스. (투자비중 권장 — 비중이 분류의 의미를 더 잘 반영).
- 색상: 고수익 녹색 / 일반 회색 / 저수익 적색.
- 슬라이스 클릭/호버 시 종목 수·비중 툴팁 표시.
- 신규 컴포넌트 파일: `frontend/src/components/PerformanceDonutChart.tsx`.

### 4.3 API 래퍼 확장

`frontend/src/api/portfolio.ts`의 `PortfolioPerformance`·`HoldingPerformance` 타입에 신규 필드(`classification`, `sector`, `classification_summary`, `sector_performance`) 추가.

---

## 5. 요구사항 (Requirements, EARS)

### 5.1 성과 계산 (REQ-PERF-*)

- **REQ-PERF-001** (Ubiquitous): The system shall 보유 종목별 수익률을 `(현재가 − 매입가) / 매입가 × 100` 공식으로 계산하고 소수점 2자리로 반올림한다.
- **REQ-PERF-002** (Ubiquitous): The system shall 포트폴리오 전체 수익률을 보유 종목 투자금액 가중평균으로 계산한다.
- **REQ-PERF-003** (Event-Driven): WHEN 보유 종목의 수익률이 계산되면, the system shall 해당 종목을 `high`(>= +5%) / `normal`(−5% 초과 +5% 미만) / `low`(<= −5%)로 분류한다.
- **REQ-PERF-004** (Ubiquitous): The system shall 보유 종목의 섹터를 KRX 코드 기반 섹터 매핑으로 판정하고 섹터별 투자금액 가중평균 수익률을 집계한다.
- **REQ-PERF-005** (Event-Driven): WHEN 성과를 계산할 때, the system shall 현재가를 `realtime.price_feed.get_current_price`(Redis TTL 60초 캐시 내장)로 조회한다.
- **REQ-PERF-006** (Ubiquitous): The system shall 기존 응답 필드(`holdings`, `total_invested`, `total_return_pct`)를 보존하고 신규 필드(`classification`, `sector`, `classification_summary`, `sector_performance`)를 추가하여 하위호환을 유지한다.
- **REQ-PERF-007** (Unwanted): IF 보유 종목의 현재가 조회가 실패하면, THEN the system shall 매입가로 대체하여 `return_pct = 0.0`으로 처리하고 `price_unavailable = true`를 표시하며, 500 오류를 발생시키지 않는다.
- **REQ-PERF-008** (Unwanted): IF 매입가가 0 이하이면, THEN the system shall 해당 종목의 `return_pct`를 0.0으로 처리하여 0 나눗셈을 방지한다.
- **REQ-PERF-009** (State-Driven): WHILE 포트폴리오에 보유 종목이 없으면, the system shall 빈 `holdings`·0 값 합계·빈 분류 요약·빈 섹터 집계를 반환한다.

### 5.2 인증·소유권 (REQ-PORT-*)

- **REQ-PORT-001** (Ubiquitous): The system shall `GET /portfolios/{portfolio_id}/performance` 요청에 `get_current_user`(JWT Bearer) 인증을 요구한다.
- **REQ-PORT-002** (Unwanted): IF 요청자가 포트폴리오 소유자가 아니면, THEN the system shall 404 Not Found를 반환한다.

### 5.3 프론트 차트·대시보드 (REQ-CHART-*)

- **REQ-CHART-001** (Ubiquitous): The system shall 포트폴리오 상세 패널에 수익률 요약·분류 목록·섹터 집계를 포함한 성과 대시보드 패널을 렌더한다.
- **REQ-CHART-002** (Ubiquitous): The system shall 고/일반/저수익 분류 비율을 recharts 도넛 차트(`PieChart`+`Pie` innerRadius)로 시각화한다.
- **REQ-CHART-003** (State-Driven): WHILE 분류 슬라이스에 호버하면, the system shall 해당 분류의 종목 수와 투자비중을 툴팁으로 표시한다.
- **REQ-CHART-004** (Event-Driven): WHEN 성과 응답에 `price_unavailable = true`인 종목이 있으면, the system shall 해당 종목에 시세 조회 실패 표식을 노출한다.
- **REQ-CHART-005** (State-Driven): WHILE 보유 종목이 없으면, the system shall 도넛 차트 대신 "보유 종목이 없습니다" 안내를 표시한다.

### 5.4 비기능 (REQ-NFR-*)

- **REQ-NFR-001** (Ubiquitous): The system shall 백엔드 변경에 대해 pytest 커버리지 85% 이상을 유지한다(`uv run pytest`).
- **REQ-NFR-002** (Ubiquitous): The system shall ruff check를 통과한다.
- **REQ-NFR-003** (Ubiquitous): The system shall 프론트 변경에 대해 vitest(`npx vitest run`)와 tsc 빌드를 통과한다.
- **REQ-NFR-004** (Ubiquitous): The system shall 섹터 매핑 로직을 단일 공용 모듈로 통합하여 `portfolio/ai_analysis.py`와 `advice/service.py`의 중복을 제거한다.

---

## 6. Exclusions (What NOT to Build)

- **자동 매매/주문 실행**: 규제·책임 리스크로 **영구 제외**. 성과가 낮은 종목에 대한 매도 자동화 등 일체 포함하지 않는다.
- **히스토리컬 성과 추이 차트**: 일자별 성과 스냅샷 저장·시계열 라인 차트는 범위 밖(별도 SPEC). 본 SPEC은 현시점 스냅샷만 계산.
- **벤치마크 대비 성과**(KOSPI/KOSDAQ 초과수익률): 범위 밖(백테스트 SPEC-012 영역).
- **실현/미실현 손익 구분, 세금·수수료 반영, 배당 수익**: 범위 밖. 단순 평가손익만 계산.
- **정확한 업종 분류 데이터 연동**(KRX 표준산업분류): 범위 밖. 기존 `_get_sector` 간이 KRX 앞자리 매핑 재사용.
- **신규 DB 테이블·마이그레이션**: 온더플라이 계산으로 불필요(0015 이후 추가 없음).
- **성과 알림·리포트 발송**(이메일/텔레그램/인앱): 범위 밖.
- **다중 포트폴리오 통합 성과**: 단일 포트폴리오 단위 성과만 계산.

---

## 7. 의존성 및 영향 범위

### 7.1 백엔드
- `backend/src/stock_picker/portfolio/service.py` — `calculate_performance` 확장(분류·섹터·가격 소스 통일).
- `backend/src/stock_picker/portfolio/schemas.py` — `HoldingPerformance`·`PortfolioPerformance` 확장 + 신규 `ClassificationSummary`·`SectorPerformance`.
- `backend/src/stock_picker/portfolio/sector.py`(신규, 또는 공용 모듈) — `_get_sector`·`_SECTOR_MAP` 통합.
- `backend/src/stock_picker/portfolio/router.py` — 응답 매핑 조정(필요 시).

### 7.2 프론트
- `frontend/src/api/portfolio.ts` — 타입 확장.
- `frontend/src/pages/Portfolio.tsx` — 성과 대시보드 패널 추가.
- `frontend/src/components/PerformanceDonutChart.tsx`(신규).

### 7.3 재사용 (변경 없음)
- `realtime/price_feed.py` `get_current_price` — 가격 소스로 호출.
- `portfolio/service.py` `get_portfolio_with_holdings` — 보유 종목 조회.

---

## 8. 전문가 자문 권고

- 백엔드(성과 계산·API 확장·기존 응답 하위호환): **expert-backend** 자문 권장.
- 프론트(도넛 차트·대시보드 패널·타입 정합화): **expert-frontend** 자문 권장.
