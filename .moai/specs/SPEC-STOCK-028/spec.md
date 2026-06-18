---
id: SPEC-STOCK-028
version: 0.4.0
status: draft
created_at: 2026-06-18
updated_at: 2026-06-18
author: ircp
priority: medium
issue_number: null
labels: [portfolio, overseas, forex]
---

# SPEC-STOCK-028: 해외 자산 지원 (Overseas Asset Support)

## HISTORY

- 2026-06-18 (v0.4.0): plan-auditor v3 지적 반영 — REQ-033 함수명 제거, REQ-051 np.corrcoef 제거, REQ-081 함수명 제거, AC-14(REQ-083 409 Conflict) 신규 추가, AC-15(REQ-084 race condition) 신규 추가.
- 2026-06-18 (v0.3.0): plan-auditor v2 지적 반영 — REQ-031·032·050·080 HOW 제거, AC-6에 REQ-038 fallback 절 추가, AC-6b(REQ-016) 신규 추가, AC-11에 REQ-003 보존 절 추가, AC-13(REQ-065) 신규 추가, REQ-083·084(유니크 충돌·race condition) 추가, test_ai_analysis.py 추가.
- 2026-06-18 (v0.2.0): plan-auditor 지적 반영 — frontmatter 필드명 수정(created_at/labels), REQ-020·021·022 HOW 제거, 섹터·배당 방어 REQ 추가, 인수 조건 전체 EARS 형식 전환, 테스트 목록 보완.
- 2026-06-18 (v0.1.0): 최초 초안 작성. 해외 주식·ETF 포트폴리오 통합. SPEC-026·027이 명시적으로 본 SPEC으로 연기한 해외 자산 영역 구현.

> **REQ 번호 설계 원칙**: 본 SPEC의 REQ 번호는 10단위 그룹(001-005, 010-015, 020-025, ...)으로 구성되며 그룹 내 미사용 번호는 향후 확장을 위한 예약 슬롯이다. 연속하지 않는 구간은 의도적 설계이며 결함이 아니다.

---

## 1. 개요

### 1.1 목표

포트폴리오에 미국 주식(NYSE·NASDAQ) 및 해외 ETF를 등록·관리하고, USD/KRW 환율을 적용하여 한국 원화(KRW) 기준으로 성과·리스크·AI 최적화 분석을 통합 제공한다. 기존 KRX 전용 포트폴리오 기능을 해외 자산까지 자연스럽게 확장하되, 기존 동작과의 하위호환을 보장한다.

### 1.2 배경

- 현재 `PortfolioHolding` 모델(`db/models.py:246`)은 `krx_code` 컬럼만 보유하여 KRX(한국거래소) 코드 전용이다. AAPL·MSFT·SPY·VOO 등 해외 종목 저장이 불가능하다.
- `avg_buy_price`에 통화 정보가 없어 원화/달러 혼재 시 성과 계산이 불가능하다.
- SPEC-026(포트폴리오 AI 최적화)과 SPEC-027(리스크 상관관계 매트릭스)은 모두 "해외 자산(SPEC-028 예정)"을 명시적으로 Out-of-Scope 처리하였다. 본 SPEC이 해당 영역을 담당한다.
- 환율 처리 로직이 코드베이스에 전무하다.

### 1.3 범위

- IN: `portfolio_holdings` 테이블에 `market`·`currency` 컬럼 추가, 환율 서비스 신규(`fx_rate.py`), 성과 계산·리스크 분석·AI 최적화의 해외 종목 지원, 프론트엔드 `market` 선택 UI, Alembic 마이그레이션 0019.
- OUT: 실시간 해외 WebSocket 가격 피드, 해외 종목 배당 데이터, USD 외 다중 통화(EUR/JPY 등), 해외 종목 스크리너·추천 (상세는 §5 참조).

### 1.4 기술 스택 (확정·재사용)

FastAPI + PostgreSQL(asyncpg) + Redis + React + TypeScript + FinanceDataReader(FDR) + numpy + Claude API(claude-haiku-4-5). 신규 데이터 공급자·신규 라이브러리는 도입하지 않는다(numpy·FDR는 SPEC-027에서 이미 직접 의존성으로 명시됨).

---

## 2. 기능 요구사항

### 2.1 PortfolioHolding DB 확장 (REQ-FOREX-001 ~ 005)

- **REQ-FOREX-001**: THE `portfolio_holdings` 테이블 SHALL `market` 컬럼(`VARCHAR(10)`, `NOT NULL`, `DEFAULT 'KRX'`)을 포함한다. 허용 값은 `'KRX'`, `'NYSE'`, `'NASDAQ'`이다.
- **REQ-FOREX-002**: THE `portfolio_holdings` 테이블 SHALL `currency` 컬럼(`VARCHAR(3)`, `NOT NULL`, `DEFAULT 'KRW'`)을 포함한다. 허용 값은 `'KRW'`, `'USD'`이다.
- **REQ-FOREX-003**: THE 시스템 SHALL 기존 `krx_code` 컬럼명을 변경하지 않고 그대로 유지한다(하위호환을 위해 ticker 식별자로 재해석하되 rename 금지).
- **REQ-FOREX-004**: WHERE 기존에 적재된 보유 종목 행이 존재하는 경우 THE 마이그레이션 SHALL `market='KRX'`·`currency='KRW'` 기본값을 적용하여 기존 데이터의 의미를 보존한다.
- **REQ-FOREX-005**: IF `market`이 `'KRX'`인데 `currency`가 `'USD'`인 경우(또는 `market`이 `'NYSE'`/`'NASDAQ'`인데 `currency`가 `'KRW'`인 경우), THEN THE 시스템 SHALL 해당 조합을 유효하지 않은 입력으로 간주하고 거부한다(서버 측 검증).

### 2.2 HoldingCreate / HoldingResponse 스키마 확장 (REQ-FOREX-010 ~ 016)

- **REQ-FOREX-010**: THE `HoldingCreate` 스키마 SHALL `market` 필드(허용 값: `'KRX'`, `'NYSE'`, `'NASDAQ'`, 기본값 `'KRX'`)를 포함한다.
- **REQ-FOREX-011**: THE `HoldingCreate` 스키마 SHALL `currency` 필드(허용 값: `'KRW'`, `'USD'`, 기본값 `'KRW'`)를 포함한다.
- **REQ-FOREX-012**: WHEN `market`·`currency`가 요청 본문에서 생략된 경우 THE 시스템 SHALL 각각 기본값 `'KRX'`·`'KRW'`를 적용하여 기존 클라이언트의 요청을 변경 없이 처리한다.
- **REQ-FOREX-013**: THE `HoldingResponse` 스키마 SHALL `market`·`currency` 필드를 응답에 포함한다.
- **REQ-FOREX-014**: WHERE 성과 응답(`HoldingPerformance`)이 반환되는 경우 THE 시스템 SHALL 해당 종목의 `market`·`currency` 정보와 함께 KRW 환산 현재가·평가금액을 포함한다.
- **REQ-FOREX-015**: IF `HoldingCreate` 요청의 `market`/`currency` 값이 허용 목록에 없는 경우 THEN THE 시스템 SHALL `422 Unprocessable Entity`로 응답한다.
- **REQ-FOREX-016**: WHEN `calculate_performance()`가 `market='NYSE'` 또는 `'NASDAQ'` 종목을 처리할 때 THE 시스템 SHALL 해당 종목의 섹터 값을 `null`(또는 빈 문자열)로 반환하고 섹터 미조회를 이유로 예외를 발생시키지 않는다.

### 2.3 환율 서비스 (REQ-FOREX-020 ~ 025)

- **REQ-FOREX-020**: THE 시스템 SHALL USD/KRW 환율을 비동기로 조회하는 독립적인 환율 서비스를 제공한다.
- **REQ-FOREX-021**: THE 환율 서비스 SHALL Redis 캐시를 사용하여 조회 결과를 저장하고 재사용한다(NFR-002 TTL 준수).
- **REQ-FOREX-022**: WHEN 환율 조회가 요청되면 THE 시스템 SHALL 동기 I/O 작업을 이벤트 루프 블로킹 없이 격리하여 실행한다.
- **REQ-FOREX-023**: THE 시스템 SHALL 환율 캐시 키를 일 단위로 갱신한다(KST 기준).
- **REQ-FOREX-024**: WHEN 캐시에 유효한 환율이 존재하면 THE 시스템 SHALL 외부 조회 없이 캐시 값을 반환한다.
- **REQ-FOREX-025**: IF 환율 조회와 캐시 조회가 모두 실패한 경우 THEN THE 시스템 SHALL fallback 기본값을 반환하고 경고 로그를 남긴다(상세 NFR-003 참조).

### 2.4 성과 계산 해외 종목 지원 (REQ-FOREX-030 ~ 040)

- **REQ-FOREX-030**: WHEN `calculate_performance()`가 `market='KRX'` 종목을 처리할 때 THE 시스템 SHALL 기존 KRX 현재가 조회 경로를 변경 없이 사용한다.
- **REQ-FOREX-031**: WHEN `calculate_performance()`가 `market='NYSE'` 또는 `'NASDAQ'` 종목을 처리할 때 THE 시스템 SHALL 외부 데이터 공급자를 통해 해당 종목의 최신 USD 현재가를 조회한다.
- **REQ-FOREX-032**: THE 시스템 SHALL 해외 종목 가격 조회 시 동기 I/O 작업을 이벤트 루프 블로킹 없이 비동기 컨텍스트에서 격리 실행한다(REQ-FOREX-022와 동일 원칙).
- **REQ-FOREX-033**: WHEN 해외 종목의 USD 현재가를 산출한 후 THE 시스템 SHALL 환율 서비스를 통해 조회한 환율을 곱하여 KRW 환산 현재가를 계산한다.
- **REQ-FOREX-034**: WHERE 보유 종목의 `currency`가 `'USD'`인 경우 THE 시스템 SHALL `avg_buy_price`(매수 당시 USD 기준)도 현재 환율로 KRW 환산하여 수익률·평가손익을 계산한다.
- **REQ-FOREX-035**: THE 시스템 SHALL 매수 단가(`avg_buy_price`)를 매수 당시 통화 그대로 DB에 저장하고, KRW 환산은 성과 계산 시점에만 수행한다(환율 변동 왜곡 방지).
- **REQ-FOREX-036**: WHEN 포트폴리오 전체 평가금액·수익률을 집계할 때 THE 시스템 SHALL 모든 보유 종목을 KRW 단위로 통일하여 합산한다.
- **REQ-FOREX-037**: IF 해외 종목의 FDR 현재가 조회가 실패한 경우 THEN THE 시스템 SHALL 기존 KRX 종목과 동일한 `price_unavailable` 처리를 적용하여 해당 종목을 graceful하게 제외하고 나머지 집계를 계속한다.
- **REQ-FOREX-038**: IF 환율 조회가 실패하여 fallback 값이 사용된 경우에도 THEN THE 시스템 SHALL 성과 계산을 중단하지 않고 fallback 환율로 계산을 완료한다.
- **REQ-FOREX-039**: THE 시스템 SHALL 응답에 사용된 환율 값(`fx_rate_used`)을 포함하여 클라이언트가 환산 기준을 확인할 수 있도록 한다.
- **REQ-FOREX-040**: WHERE 해외 종목 가격 데이터가 조회된 경우 THE 시스템 SHALL Redis 캐시(NFR-001 TTL 적용)를 적용하여 FDR 레이트 리밋을 회피한다.

### 2.5 리스크 분석 해외 종목 지원 (REQ-FOREX-050 ~ 055)

- **REQ-FOREX-050**: WHEN 리스크 분석의 상관관계·변동성 계산이 `market='NYSE'`/`'NASDAQ'` 종목을 포함할 때 THE 시스템 SHALL 외부 데이터 공급자를 통해 해외 종가 시계열을 조회한다.
- **REQ-FOREX-051**: THE 시스템 SHALL 해외 종목 시계열에 대해 기존과 동일한 numpy 기반 행렬 계산(상관계수·연간화 변동성 `std×√252`)을 적용한다(scipy 사용 금지, NFR-004 참조).
- **REQ-FOREX-052**: THE 시스템 SHALL 상관관계 계산 시 해외 종목 USD 종가 시계열을 변환 없이 그대로 사용한다(상관계수는 통화에 불변이므로 KRW 환산 불필요).
- **REQ-FOREX-053**: IF 해외 종목의 시계열 데이터가 부족하거나 조회 실패한 경우 THEN THE 시스템 SHALL 기존 KRX 종목과 동일하게 해당 종목을 계산에서 제외한다.
- **REQ-FOREX-054**: WHERE 포트폴리오 변동성(`portfolio_volatility`)을 계산할 때 THE 시스템 SHALL 비중(weight) 산정을 KRW 환산 평가금액 기준으로 수행한다.
- **REQ-FOREX-055**: THE SPEC-027 리스크 분석 응답 스키마(correlation_matrix·holdings_volatility 등) SHALL 해외 종목을 포함하도록 확장되되 기존 필드 구조는 변경하지 않는다.

### 2.6 AI 최적화 해외 종목 정보 포함 (REQ-FOREX-060 ~ 065)

- **REQ-FOREX-060**: WHEN `optimize_portfolio()`가 Claude 프롬프트를 구성할 때 THE 시스템 SHALL 각 보유 종목의 `market`·`currency` 정보를 프롬프트에 포함한다.
- **REQ-FOREX-061**: THE 시스템 SHALL Claude 프롬프트에 전달하는 비중(weight_pct)·평가금액을 KRW 환산 기준으로 통일한다.
- **REQ-FOREX-062**: WHEN `analyze_portfolio()`(`POST /portfolios/{id}/ai-analysis`)가 해외 종목을 포함한 포트폴리오를 분석할 때 THE 시스템 SHALL market 정보를 포함하여 분석한다.
- **REQ-FOREX-063**: THE 시스템 SHALL 기존 Claude 모델(`claude-haiku-4-5`)과 호출 패턴을 그대로 재사용한다(신규 모델·신규 호출 도입 금지).
- **REQ-FOREX-064**: WHERE AI 최적화가 신규 종목(new_stocks)을 추천하는 경우 THE 시스템 SHALL 추천 대상을 기존 `recommendations` 테이블(KRX 종목) 범위로 한정한다(해외 종목 추천은 Out-of-Scope, §5 참조).
- **REQ-FOREX-065**: IF Claude 호출이 실패한 경우 THEN THE 시스템 SHALL 기존 동작과 동일하게 예외를 전파하지 않고 오류 딕셔너리를 반환한다.

### 2.7 프론트엔드 market 선택 UI (REQ-FOREX-070 ~ 075)

- **REQ-FOREX-070**: THE 프론트엔드 `Holding` 타입(`frontend/src/api/portfolio.ts`) SHALL `market`·`currency` 필드를 포함하도록 확장된다.
- **REQ-FOREX-071**: THE 프론트엔드 `HoldingCreate` 타입 SHALL `market`·`currency` 필드를 포함한다(기본값 `'KRX'`·`'KRW'`).
- **REQ-FOREX-072**: WHEN 사용자가 보유 종목 추가 폼을 사용할 때 THE 폼 SHALL `market` 선택 컨트롤(KRX / NYSE / NASDAQ)을 제공한다.
- **REQ-FOREX-073**: WHEN 사용자가 `market`을 `'NYSE'` 또는 `'NASDAQ'`로 선택할 때 THE 폼 SHALL `currency`를 `'USD'`로 자동 설정한다. `'KRX'` 선택 시 `'KRW'`로 자동 설정한다.
- **REQ-FOREX-074**: WHERE 보유 종목 목록·성과 화면이 렌더링될 때 THE 프론트엔드 SHALL 각 종목의 `market` 표시(예: 배지)와 KRW 환산 평가금액을 함께 표시한다.
- **REQ-FOREX-075**: THE 프론트엔드 SHALL 기존 KRX 종목의 표시 동작을 변경하지 않는다(하위호환).

### 2.8 Alembic 마이그레이션 0019 (REQ-FOREX-080 ~ 082)

- **REQ-FOREX-080**: THE 시스템 SHALL 마이그레이션 `0018` 이후에 적용될 신규 DB 마이그레이션을 제공하여 `portfolio_holdings` 테이블에 `market`·`currency` 컬럼을 추가한다.
- **REQ-FOREX-081**: THE 마이그레이션 SHALL `portfolio_holdings` 테이블에 `market`·`currency` 컬럼을 추가하고(REQ-FOREX-001·002 사양), 롤백 실행 시 두 컬럼을 제거한다.
- **REQ-FOREX-082**: WHERE `portfolio_holdings`에 기존 고유 제약(unique constraint)이 ticker 단위로 존재하는 경우 THE 마이그레이션 SHALL 해당 제약을 `(portfolio_id, krx_code, market)` 조합 기준으로 변경하여 KRX `000020`과 동일 ticker의 해외 종목이 충돌하지 않도록 한다.
- **REQ-FOREX-083**: IF `(portfolio_id, krx_code, market)` 고유 제약 위반 시 THEN THE 시스템 SHALL `409 Conflict`로 응답한다(기존 종목 중복 등록 방지).
- **REQ-FOREX-084**: THE 시스템 SHALL 환율 캐시 저장 시 동시 요청에 의한 경쟁 쓰기(race condition)를 허용한다 — 마지막 쓰기가 우선되며 동일한 날짜 환율값이므로 일관성에 영향이 없다.

---

## 3. 비기능 요구사항

- **REQ-FOREX-NFR-001**: THE 해외 종목 가격 데이터 Redis 캐시 SHALL TTL ≥ 86400초(일 1회 갱신)를 적용하여 FDR(Yahoo Finance 기반) 레이트 리밋·차단을 회피한다.
- **REQ-FOREX-NFR-002**: THE 환율(USD/KRW) Redis 캐시 SHALL TTL ≥ 3600초를 적용한다.
- **REQ-FOREX-NFR-003**: IF 환율 조회에 실패한 경우 THEN THE 시스템 SHALL fallback 기본값 `1350.0`(KRW/USD)을 사용하고 `WARNING` 레벨 로그를 기록한다. 환율 실패가 포트폴리오 조회 전체를 실패시켜서는 안 된다(graceful degradation).
- **REQ-FOREX-NFR-004**: THE 시스템 SHALL 모든 통계 계산에서 `scipy`를 사용하지 않는다. numpy만 사용한다(SPEC-027 REQ-RISK-NFR-001과의 일관성 유지).

---

## 4. 의존성

- **SPEC-017**: `get_portfolio_with_holdings`·비중 산정 로직.
- **SPEC-026**: `optimize_portfolio()`·`POST /portfolios/{id}/optimize`·Portfolio.tsx 구조.
- **SPEC-027**: `risk_analysis.py`·`POST /portfolios/{id}/risk-analysis`·numpy 의존성·scipy 금지 원칙.

---

## 5. Out-of-Scope (이번 SPEC-028)

- **실시간 해외 WebSocket 가격 피드**: 해외 종목 실시간 틱 스트리밍은 별도 SPEC. 본 SPEC은 일 1회 캐시 기반 종가만 지원.
- **해외 종목 배당 데이터**: FDR 해외 배당 API가 불안정하여 제외. 배당 서비스(`dividends.py`)는 `market != 'KRX'`인 종목을 수신했을 때 `dividend_available=False`를 반환하고 예외를 전파하지 않아야 한다(해당 방어 로직은 구현 요구사항이나 배당 데이터 수집 자체는 Out-of-Scope).
- **다중 통화(EUR/JPY 등)**: USD/KRW 단일 통화쌍만 지원. EUR·JPY 등은 미지원.
- **해외 종목 스크리너·추천**: recommendation·screener 도메인의 해외 종목 확장은 제외. AI 최적화의 신규 종목 추천도 KRX 범위로 한정(REQ-FOREX-064).
- **자동 매매/주문 실행**: 규제·책임 리스크로 프로젝트 전체에서 영구 제외.

---

## 6. 인수 조건 (Acceptance Criteria)

### AC-1: 해외 종목 등록 (REQ-FOREX-010 ~ 015)

WHEN 인증된 사용자가 `market="NASDAQ"`, `currency="USD"`, `krx_code="AAPL"`, `quantity=10`, `avg_buy_price=180.0`으로 보유 종목 추가를 요청하면 THE 시스템 SHALL 해당 종목을 `market="NASDAQ"`·`currency="USD"`로 저장하고 `HoldingResponse` 응답에 `market`·`currency` 필드를 포함하여 반환한다.

### AC-2: 기본값 하위호환 (REQ-FOREX-012)

WHEN 기존 클라이언트가 `market`·`currency` 필드 없이 `krx_code="005930"`, `quantity=5`, `avg_buy_price=70000`만 전송하면 THE 시스템 SHALL `market="KRX"`·`currency="KRW"`를 기본값으로 적용하여 기존과 동일하게 정상 처리한다.

### AC-3: 유효하지 않은 시장/통화 조합 거부 (REQ-FOREX-005, 015)

IF `HoldingCreate` 요청에서 `market="KRX"·currency="USD"`와 같이 허용되지 않는 시장·통화 조합이 전송된 경우 THEN THE 시스템 SHALL `422 Unprocessable Entity`로 응답한다.

### AC-4: 환율 캐시 동작 (REQ-FOREX-021 ~ 024, NFR-002)

WHEN 환율 서비스가 최초 호출되어 캐시가 비어 있으면 THE 시스템 SHALL 외부 환율 데이터를 조회하여 Redis에 TTL ≥ 3600초로 캐시하고 캐시 값을 반환한다. WHERE 동일 날짜 키의 캐시가 유효하게 존재하는 경우 THE 시스템 SHALL 외부 조회 없이 캐시 값을 반환한다.

### AC-5: 환율 조회 실패 시 fallback (REQ-FOREX-025, NFR-003)

IF 외부 환율 조회와 Redis 캐시 조회가 모두 실패한 경우 THEN THE 시스템 SHALL `1350.0`을 반환하고 `WARNING` 레벨 로그를 기록하며 예외를 전파하지 않는다.

### AC-6: 해외 종목 성과 KRW 환산 (REQ-FOREX-031 ~ 039)

WHEN `calculate_performance()`가 `market="NASDAQ"` 종목을 처리하면 THE 시스템 SHALL 해당 종목의 USD 현재가를 조회하여 실시간 환율로 KRW 환산 현재가를 산출하고, `avg_buy_price`(USD)도 KRW 환산하여 수익률을 계산하며, 포트폴리오 전체 평가금액을 KRW 단위로 집계하고 응답에 `fx_rate_used`를 포함한다.

IF 환율 조회가 실패하여 fallback 값이 사용된 경우에도 THEN THE 시스템 SHALL 성과 계산을 중단하지 않고 fallback 환율(`1350.0`)로 KRW 환산 현재가·수익률 계산을 완료하고 `fx_rate_used`에 fallback 값을 포함한다. (REQ-FOREX-038)

### AC-6b: 해외 종목 섹터 처리 (REQ-FOREX-016)

WHEN `calculate_performance()`가 `market='NYSE'` 또는 `'NASDAQ'` 종목을 처리할 때 THE 시스템 SHALL 해당 종목의 섹터 값을 `null`(또는 빈 문자열)로 반환하고 섹터 조회 실패를 이유로 예외를 발생시키지 않는다.

### AC-7: 해외 종목 가격 조회 실패 graceful 처리 (REQ-FOREX-037)

IF KRX 종목과 해외 종목이 혼재한 포트폴리오에서 해외 종목 가격 조회가 실패한 경우 THEN THE 시스템 SHALL 해당 종목을 `price_unavailable`로 표시하여 제외하고 나머지 KRX 종목 집계를 계속 진행한다.

### AC-8: 리스크 분석 해외 종목 포함 (REQ-FOREX-050 ~ 055)

WHEN `risk-analysis` 엔드포인트가 KRX 종목과 NASDAQ 종목을 포함한 포트폴리오에 대해 호출되면 THE 시스템 SHALL 해외 종목 USD 종가 시계열을 조회하여 numpy 기반 상관계수·변동성 계산에 포함하고, `correlation_matrix`·`holdings_volatility`에 해외 종목을 포함하며, 포트폴리오 변동성의 비중을 KRW 환산 평가금액 기준으로 산정한다.

### AC-9: AI 최적화 market 정보 포함 (REQ-FOREX-060 ~ 064)

WHEN `optimize` 엔드포인트가 해외 종목을 포함한 포트폴리오에 대해 호출되면 THE 시스템 SHALL Claude 프롬프트에 각 종목의 `market`·`currency` 정보를 포함하고, 비중을 KRW 환산 기준으로 통일하며, 신규 종목 추천(`new_stocks`)을 KRX 범위(`recommendations` 테이블)로 한정한다.

### AC-10: 프론트엔드 market 선택 UI (REQ-FOREX-070 ~ 075)

WHEN 사용자가 보유 종목 추가 폼에서 `market` 선택 컨트롤을 통해 `"NASDAQ"`를 선택하면 THE 프론트엔드 SHALL `currency`를 `"USD"`로 자동 설정하고, 폼 제출 시 `market`·`currency`를 `HoldingCreate` 요청에 포함하며, 보유 종목 목록에 `market` 배지와 KRW 환산 평가금액을 함께 표시한다.

### AC-11: 마이그레이션 0019 (REQ-FOREX-080 ~ 082, 003)

WHEN 마이그레이션 `upgrade()`를 실행하면 THE 시스템 SHALL `portfolio_holdings` 테이블에 `market`(`DEFAULT 'KRX'`)·`currency`(`DEFAULT 'KRW'`) 컬럼을 추가하고, 기존 행들에 기본값을 적용하며, 고유 제약을 `(portfolio_id, krx_code, market)` 조합으로 변경한다.

WHERE `upgrade()`가 실행된 경우 THE 시스템 SHALL 기존 `krx_code` 컬럼명을 변경하지 않고 그대로 유지한다. (REQ-FOREX-003)

WHERE `downgrade()`가 실행되는 경우 THE 시스템 SHALL 두 컬럼을 제거하고 고유 제약을 원래대로 복원한다.

### AC-12: scipy 미사용 (REQ-FOREX-NFR-004)

WHERE SPEC-028 구현이 완료된 경우 THE 백엔드 소스 SHALL `scipy`를 `import`하는 코드를 포함하지 않는다.

### AC-13: Claude 호출 실패 시 graceful 처리 (REQ-FOREX-065)

IF Claude API 호출이 실패한 경우 THEN THE 시스템 SHALL 예외를 전파하지 않고 오류 정보를 담은 딕셔너리를 반환한다.

### AC-14: 중복 보유 종목 등록 거부 (REQ-FOREX-083)

IF 이미 등록된 `(portfolio_id, krx_code, market)` 조합으로 보유 종목 추가가 요청된 경우 THEN THE 시스템 SHALL `409 Conflict`로 응답한다.

### AC-15: 환율 캐시 race condition 허용 (REQ-FOREX-084)

WHERE 환율 캐시 키에 대해 동시 쓰기가 발생한 경우 THE 시스템 SHALL 마지막 쓰기 값을 유지하고 예외를 발생시키지 않는다.

---

## 7. 영향 파일 요약

### Backend
- `db/models.py` — `PortfolioHolding`: `market`·`currency` 컬럼 추가
- `portfolio/schemas.py` — `HoldingCreate`·`HoldingResponse`·`HoldingPerformance` 확장
- `portfolio/service.py` — `add_holding`·`calculate_performance` 변경
- `portfolio/fx_rate.py` — 신규: 환율 서비스
- `portfolio/risk_analysis.py` — 해외 ticker 분기 (SPEC-027)
- `portfolio/ai_analysis.py` — Claude 프롬프트 market 정보 포함 (SPEC-026)
- `portfolio/router.py` — `HoldingCreate` 파라미터 통과
- `alembic/versions/0019_portfolio_foreign_asset.py` — 신규 마이그레이션

### Frontend
- `frontend/src/api/portfolio.ts` — `Holding`·`HoldingCreate` 타입 확장
- 보유 종목 추가 폼 컴포넌트 — market 선택 UI

### Tests (TDD: RED-GREEN-REFACTOR)
- `tests/test_fx_rate.py` — 신규: 환율 서비스 (캐시·fallback, REQ-020~025)
- `tests/test_portfolio_service.py` — 해외 자산 성과 계산 (REQ-030~039)
- `tests/test_risk_analysis.py` — 기존 파일 확장: 해외 종목 포함 리스크 분석 (REQ-050~055)
- `tests/test_ai_analysis.py` — 기존 파일 확장: AI 최적화 market 정보·Claude 실패 처리 (REQ-060~065)
