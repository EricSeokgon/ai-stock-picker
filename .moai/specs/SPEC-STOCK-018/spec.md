---
id: SPEC-STOCK-018
version: 0.1.0
status: draft
created: 2026-06-12
updated: 2026-06-12
author: ircp
priority: medium
issue_number: null
---

# SPEC-STOCK-018 — 종목 스크리너 (Phase 18)

## HISTORY

- 2026-06-12 (v0.1.0): 최초 작성. 재무 지표(PER/PBR/ROE/시가총액/배당수익률/52주 고저 대비)
  기반 종목 필터링 스크리너. 다중 조건 AND 필터·결과 리스트·스크리너 프리셋 저장(사용자당 5개)·
  결과에서 원클릭 관심종목 추가. 신규 모듈 `screener/`, 신규 테이블 `screener_presets`(마이그 0016).

---

## 1. 개요 (Overview)

### 1.1 문제 정의

현재 ai-stock-picker는 추천 시스템(`Recommendation`, 4요인 산식)·종목 검색(`GET /stocks/search`,
종목명/코드 기반)·관심종목·섹터 대시보드를 제공하지만, **사용자가 직접 재무 지표 조건을 정의해
종목을 발굴(screening)하는 기능이 없다**. 추천은 시스템이 산정한 점수 순이며, 검색은 이름·코드
일치만 지원한다. 가치투자·배당투자 관점의 정량 필터링(예: "PER 10 이하 AND 배당수익률 3% 이상")은
불가능하다.

### 1.2 본 SPEC이 추가하는 것

1. **재무 지표 필터 스크리너** — PER·PBR·ROE·시가총액·배당수익률·52주 고가/저가 대비 현재가 위치를
   최소/최대 범위 조건으로 정의하고, 조건을 모두(AND) 만족하는 종목 리스트를 반환.
2. **스크리너 프리셋 저장/불러오기** — 사용자가 자주 쓰는 필터 조합을 이름과 함께 저장(사용자당 최대 5개)·
   불러오기·삭제.
3. **결과에서 원클릭 관심종목 추가** — 스크리너 결과 행에서 기존 관심종목(`WatchlistItem`) 추가 흐름 재사용.
4. **프론트 스크리너 페이지** — `/screener` 필터 패널 + 정렬 가능한 결과 테이블.

### 1.3 핵심 제약: 재무 지표 데이터 출처 (비자명)

[HARD] 본 프로젝트 코드베이스에는 **PER·PBR·ROE·배당수익률 등 펀더멘털 지표를 저장하는 컬럼/테이블이
전무하다**. `AnalysisResult`는 뉴스 감성 전용이며 재무 지표를 담지 않는다. `mapping/prices.py`의
FinanceDataReader 래퍼는 **종가·변동률·거래량만** 제공하고 펀더멘털은 신뢰성 있게 제공하지 못한다.
따라서 본 SPEC은 재무 지표를 **신규 스케줄드 수집 + 스냅샷 테이블(`stock_fundamentals`)로 적재**하고,
스크리너는 그 스냅샷을 질의한다. 시가총액은 현재가 × 상장주식수로 산출하되, 상장주식수를 안정적으로
얻지 못하는 종목은 시가총액 필터 대상에서 제외(NULL)한다. 상세는 §4·§5.4 참조.

### 1.4 목표가 아닌 것 (요약)

자동 매매·실시간 스크리닝·OR/복합 논리 필터·기술적 지표(이동평균/RSI 등)·백테스트 연동·추천 점수
재가중은 본 SPEC 범위가 아니다. 상세는 §8 참조.

---

## 2. 기존 자산 재사용 (Existing Assets)

[HARD] 본 SPEC은 아래 자산을 **재정의하지 않고 재사용·확장**한다.

| 자산 | 위치 | 재사용 방식 |
|------|------|-------------|
| `WatchlistItem` 모델·서비스 | `db/models.py`, `watchlist/service.py` | 결과에서 관심종목 추가 (중복 시 409 패턴 재사용) |
| `Recommendation` 모델 | `db/models.py` (krx_code, trade_date) | 결과 행에 "추천 포함" 플래그 표시 (선택, search 패턴 동일) |
| KRX 마스터 로더 | `mapping/krx_master.py` `load_krx_master` | 종목 유니버스(코드→이름) 확보 |
| FinanceDataReader 래퍼 | `mapping/prices.py` `get_stock_price_data`/`_fetch_price` | 현재가·52주 데이터 수집 (스레드 풀 격리 패턴) |
| Redis 캐시 의존성 | `api/deps.py` `get_redis_client`/`get_cache` | 스크리너 실행 결과·펀더멘털 스냅샷 캐시 |
| 인증 의존성 | `auth/dependencies.py` `get_current_user`, `get_db_session` | 프리셋 CRUD·결과 관심종목 추가 보호 |
| 스케줄러 | `scheduler/jobs.py` (APScheduler) | 펀더멘털 수집을 일일 잡으로 등록 (신규 타이머 최소화, 일일 파이프라인에 연동) |
| 검색 정렬 패턴 | `search/service.py` (in_recommendations 우선) | 결과 정렬·추천 포함 표시 패턴 참고 |

[HARD] 기존 `GET /stocks/search`·`GET /recommendations`·추천 4요인 산식(`scoring/engine.py`)은
**제거·변경하지 않는다**. 스크리너는 신규 라우터로 추가한다.

---

## 3. 환경 및 가정 (Environment & Assumptions)

### 3.1 환경

- 백엔드: FastAPI + SQLAlchemy 2.0 (async 엔진 + auth용 동기 엔진), PostgreSQL, Redis
- 데이터: FinanceDataReader(동기, 스레드 풀 격리), KRX 마스터 CSV
- 프론트: React + TypeScript + Vite, 기존 `api/watchlist.ts`·`api/client.ts` 패턴 확장
- 스케줄러: APScheduler (`scheduler/jobs.py`) — 일일 파이프라인 06:00에 펀더멘털 수집 연동
- 마이그레이션: 누적 0001~0015 존재 → 본 SPEC 신규 마이그레이션 = **0016** (down_revision=`0015`)

### 3.2 가정

- 가정 1: 스크리너는 **실시간 요구가 없다**. 최신 적재된 스냅샷(일 1회 수집)을 대상으로 질의한다.
- 가정 2: 일부 종목은 PER/PBR/ROE/배당수익률/상장주식수를 얻지 못할 수 있다. 해당 지표가 NULL인 종목은
  그 지표를 조건으로 거는 필터에서 **자동 제외**된다(해당 지표 조건이 없으면 포함).
- 가정 3: 프리셋 저장은 인증 사용자만 가능하다. 스크리너 실행 자체는 인증 없이도 동작 가능하나,
  관심종목 추가·프리셋 CRUD는 인증을 요구한다.
- 가정 4: 펀더멘털 수집 실패는 일일 파이프라인을 중단시키지 않는다(섹터 집계 예외 격리 패턴 동일).
- 가정 5: 종목 유니버스는 KRX 마스터 기준이며, 수집 부하를 고려해 수집 대상 종목 수에 상한을 둔다(설정값).

### 3.3 캐싱 정책

- 펀더멘털 스냅샷: 일 1회 수집·`stock_fundamentals` 테이블 영속화. 캐시가 아닌 진실 소스.
- 스크리너 실행 결과: 동일 필터 조건(정규화 해시) 기준 Redis 캐시(키 `screener:{hash}`, TTL 300s).
  캐시 미스 시에만 DB 질의 수행.

---

## 4. 데이터 모델 (Data Model)

### 4.1 `stock_fundamentals` 테이블 (마이그레이션 0016, down_revision=`0015`)

종목별 최신 재무 지표 스냅샷. 일일 수집 잡이 upsert 한다.

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| `id` | Integer | PK, autoincrement | 기본 키 |
| `krx_code` | String(10) | NOT NULL | KRX 종목코드 |
| `name` | String(100) | NULL | 종목명 (KRX 마스터 기준) |
| `sector` | String(100) | NULL | 섹터 (가용 시) |
| `current_price` | Numeric(12,2) | NULL | 최근 종가 |
| `change_pct` | Numeric(8,4) | NULL | 전일 대비 변동률 |
| `per` | Numeric(10,2) | NULL | 주가수익비율 |
| `pbr` | Numeric(10,2) | NULL | 주가순자산비율 |
| `roe` | Numeric(8,4) | NULL | 자기자본이익률 (%) |
| `market_cap` | BigInteger | NULL | 시가총액 (현재가 × 상장주식수) |
| `dividend_yield` | Numeric(8,4) | NULL | 배당수익률 (%) |
| `week52_high` | Numeric(12,2) | NULL | 52주 고가 |
| `week52_low` | Numeric(12,2) | NULL | 52주 저가 |
| `price_vs_52w_pct` | Numeric(8,4) | NULL | 현재가의 52주 레인지 내 위치 (%) |
| `snapshot_date` | Date | NOT NULL | 스냅샷 기준일 |
| `updated_at` | TIMESTAMPTZ | server_default=now(), NOT NULL | 적재 시각 |

제약·인덱스:

- `UniqueConstraint(krx_code, snapshot_date)` 이름 `uq_fundamentals_code_date` — 동일 종목·기준일 1행(upsert 멱등성).
- `Index(snapshot_date)` — 최신 스냅샷 일괄 질의 최적화.

### 4.2 `screener_presets` 테이블 (마이그레이션 0016)

사용자별 스크리너 필터 프리셋. 사용자당 최대 5개.

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| `id` | Integer | PK, autoincrement | 기본 키 |
| `user_id` | Integer | FK→users.id (ON DELETE CASCADE), NOT NULL | 소유 사용자 |
| `name` | String(100) | NOT NULL | 프리셋 이름 |
| `criteria` | JSON / Text | NOT NULL | 필터 조건 (지표별 min/max JSON 직렬화) |
| `created_at` | TIMESTAMPTZ | server_default=now(), NOT NULL | 생성 시각 |

제약:

- `UniqueConstraint(user_id, name)` 이름 `uq_screener_preset_user_name` — 동일 사용자 동일 이름 중복 방지.

[HARD] 본 SPEC 신규 테이블은 `stock_fundamentals`·`screener_presets` **두 개뿐**이다. 기존 테이블
컬럼은 추가·변경하지 않는다.

---

## 5. EARS 요구사항 (Requirements)

### 5.1 스크리너 핵심 (REQ-SCR-*)

- REQ-SCR-001 (Event-Driven): When a user submits screener filter criteria, the system shall return
  the list of stocks whose fundamentals satisfy all provided conditions using AND logic.
- REQ-SCR-002 (Ubiquitous): The system shall support filter criteria for PER, PBR, ROE, market cap,
  dividend yield, and current price position relative to the 52-week high/low range, each as an
  optional minimum and/or maximum bound.
- REQ-SCR-003 (State-Driven): While a stock has a NULL value for a metric that is being filtered, the
  system shall exclude that stock from the result for that filter condition.
- REQ-SCR-004 (Event-Driven): When returning screener results, the system shall include for each
  matching stock the `krx_code`, `name`, `sector`, `current_price`, `change_pct`, and the values of
  the metrics that were used as filter conditions.
- REQ-SCR-005 (State-Driven): While no filter condition is provided, the system shall return the
  latest fundamentals snapshot universe (subject to a result limit) rather than an empty list.
- REQ-SCR-006 (Unwanted): If a filter condition has a minimum greater than its maximum, then the
  system shall respond with HTTP 422 and shall not execute the screen.
- REQ-SCR-007 (Ubiquitous): The system shall run the screen against the latest available
  `stock_fundamentals` snapshot and shall not require real-time data.

### 5.2 프리셋 저장/불러오기 (REQ-SCR-PRESET-*)

- REQ-SCR-PRESET-001 (Event-Driven): When an authenticated user saves a screener preset, the system
  shall persist the preset name and criteria JSON scoped to that user.
- REQ-SCR-PRESET-002 (State-Driven): While an authenticated user already owns 5 presets, the system
  shall reject a new preset creation with HTTP 409 and an informational message.
- REQ-SCR-PRESET-003 (Event-Driven): When an authenticated user lists their presets, the system shall
  return only that user's presets.
- REQ-SCR-PRESET-004 (Event-Driven): When an authenticated user deletes a preset they own, the system
  shall remove it and respond with HTTP 204.
- REQ-SCR-PRESET-005 (Unwanted): If a user attempts to delete a preset they do not own, then the
  system shall respond with HTTP 403 or 404 and shall not delete the preset.
- REQ-SCR-PRESET-006 (Unwanted): If a user saves a preset with a name that already exists for that
  user, then the system shall respond with HTTP 409 and shall not create a duplicate.

### 5.3 API (REQ-SCR-API-*)

- REQ-SCR-API-001 (Event-Driven): When `POST /screener/run` is called with filter criteria, the
  system shall execute the screen and return the matching stocks.
- REQ-SCR-API-002 (Event-Driven): When `GET /screener/presets` is called by an authenticated user,
  the system shall return that user's saved presets.
- REQ-SCR-API-003 (Event-Driven): When `POST /screener/presets` is called by an authenticated user,
  the system shall save the preset subject to the per-user limit of 5.
- REQ-SCR-API-004 (Event-Driven): When `DELETE /screener/presets/{id}` is called by the preset owner,
  the system shall delete the preset.
- REQ-SCR-API-005 (Ubiquitous): The system shall protect all preset endpoints with the existing
  `get_current_user` dependency.

### 5.4 데이터 수집 (REQ-SCR-DATA-*)

- REQ-SCR-DATA-001 (Event-Driven): When the daily fundamentals collection job runs, the system shall
  upsert a `stock_fundamentals` row per stock with the latest available metrics and `snapshot_date`.
- REQ-SCR-DATA-002 (State-Driven): While a stock's listed-share count is unavailable, the system shall
  store `market_cap` as NULL and shall still store other available metrics.
- REQ-SCR-DATA-003 (Event-Driven): When computing `price_vs_52w_pct`, the system shall use the latest
  close price relative to the 52-week high and low range.
- REQ-SCR-DATA-004 (Unwanted): If fundamentals collection for a stock fails, then the system shall log
  the failure, skip that stock, and shall not interrupt the daily pipeline or other stocks.
- REQ-SCR-DATA-005 (Event-Driven): When the fundamentals collection job is invoked, the system shall
  limit the number of collected stocks to a configurable universe cap.

### 5.5 프론트엔드 (REQ-SCR-FE-*)

- REQ-SCR-FE-001 (Ubiquitous): The frontend shall provide a `/screener` page with a filter panel and a
  results table.
- REQ-SCR-FE-002 (Event-Driven): When a user adjusts a metric filter input (range or min/max), the
  frontend shall include that condition in the next screener run request.
- REQ-SCR-FE-003 (Event-Driven): When screener results are returned, the frontend shall render them in
  a table sortable by any column.
- REQ-SCR-FE-004 (State-Driven): While a screener run is in progress, the frontend shall display a
  loading state.
- REQ-SCR-FE-005 (Event-Driven): When a user clicks "관심종목 추가" on a result row, the frontend shall
  add that stock to the watchlist using the existing watchlist add flow.
- REQ-SCR-FE-006 (Optional): Where the user is authenticated, the frontend shall provide controls to
  save the current filter as a preset and to load or delete existing presets.

### 5.6 비기능 (REQ-SCR-NFR-*)

- REQ-SCR-NFR-001 (Ubiquitous): The system shall return screener execution results within 3 seconds
  for a single screen request against the latest snapshot.
- REQ-SCR-NFR-002 (Ubiquitous): The system shall store presets in the `screener_presets` table with
  `user_id`, `name`, and a `criteria` JSON column.
- REQ-SCR-NFR-003 (Ubiquitous): The system shall not integrate any automated trading or order
  execution with the screener.
- REQ-SCR-NFR-004 (Ubiquitous): The system shall achieve backend test coverage of at least 85 percent
  for new screener modules.

---

## 6. API 계약 (API Contract)

[HARD] 신규 라우터 prefix는 **`/screener`**로 분리한다. 프리셋 엔드포인트는 `get_current_user`로
보호하며 타사용자 프리셋 접근 시 403/404를 반환한다.

| 메서드 | 경로 | 인증 | 설명 | 주요 요구사항 |
|--------|------|------|------|----------------|
| `POST` | `/screener/run` | 선택 | 필터 조건으로 스크리너 실행 | REQ-SCR-001~007, REQ-SCR-API-001 |
| `GET` | `/screener/presets` | 필수 | 사용자 프리셋 목록 | REQ-SCR-PRESET-003, REQ-SCR-API-002 |
| `POST` | `/screener/presets` | 필수 | 프리셋 저장 (최대 5개) | REQ-SCR-PRESET-001~002, REQ-SCR-API-003 |
| `DELETE` | `/screener/presets/{id}` | 필수 | 프리셋 삭제 | REQ-SCR-PRESET-004~005, REQ-SCR-API-004 |

### 6.1 요청/응답 형식 예시 (참고)

```
POST /screener/run
{
  "filters": {
    "per": {"max": 10},
    "dividend_yield": {"min": 3.0},
    "market_cap": {"min": 100000000000}
  },
  "sort_by": "dividend_yield",
  "sort_order": "desc",
  "limit": 50
}
```

```
200 OK
{
  "snapshot_date": "2026-06-12",
  "total": 23,
  "results": [
    {
      "krx_code": "005930", "name": "삼성전자", "sector": "전기전자",
      "current_price": 71000, "change_pct": -0.84,
      "per": 9.2, "dividend_yield": 3.1, "market_cap": 423000000000000
    }
  ]
}
```

[HARD] 응답 스키마의 정확한 필드명·Pydantic 모델 구조는 Run 단계에서 확정한다 (본 SPEC은 관찰 가능한
동작만 정의).

---

## 7. 마일스톤 (Milestones)

우선순위 기반 (시간 추정 없음).

| 마일스톤 | 설명 | 우선순위 |
|----------|------|----------|
| M1 | DB 모델 & 마이그레이션 0016 (`stock_fundamentals`·`screener_presets`, down_rev=0015) | High |
| M2 | 펀더멘털 수집 잡 (FDR 기반 지표 산출·upsert·일일 파이프라인 연동, REQ-SCR-DATA-*) | High |
| M3 | 스크리너 실행 서비스·라우터 (`POST /screener/run`, AND 필터·NULL 제외·캐시, REQ-SCR-001~007) | High |
| M4 | 프리셋 CRUD 라우터 (5개 상한·소유권 검증, REQ-SCR-PRESET-*·REQ-SCR-API-*) | Medium |
| M5 | 프론트 스크리너 페이지 (필터 패널·정렬 테이블·로딩·관심종목 추가·프리셋, REQ-SCR-FE-*) | Medium |
| M6 | 테스트 & 품질 게이트 (커버리지 85%+, 응답 < 3s, REQ-SCR-NFR-*) | High |

---

## 8. 제외 사항 (Exclusions — What NOT to Build)

[HARD] 아래 항목은 본 SPEC 범위에서 명시적으로 제외한다.

1. **자동 매매·주문 실행** — 프로젝트 영구 제외 (규제·책임 리스크). 스크리너는 종목 발굴·정보 제공만 한다.
2. **실시간 스크리닝** — 일 1회 수집된 스냅샷 대상. 실시간 시세 기반 즉시 재계산 없음.
3. **OR/복합 논리 필터** — 다중 조건은 AND 만 지원. 괄호·OR·그룹 조건은 범위 밖.
4. **기술적 지표 필터** — 이동평균·RSI·MACD·거래량 급증 등 기술적 지표 스크리닝 없음 (펀더멘털·가격 위치만).
5. **추천 점수 재가중·연동** — 스크리너 결과를 추천 4요인 산식에 반영하지 않는다 (독립 기능).
6. **백테스트 연동** — 스크리너 조건을 백테스트 전략으로 전환하는 기능 없음.
7. **신규 외부 데이터 공급자 도입** — FinanceDataReader·KRX 마스터만 활용. 유료 펀더멘털 API 추가 없음.
   (FDR가 특정 지표를 제공하지 못하면 해당 지표는 NULL로 둔다.)
8. **프리셋 공유·공개** — 프리셋은 사용자 비공개. 공유·즐겨찾기·복제 기능 없음.
9. **알림 연동** — 스크리너 조건 충족 시 알림 발송 없음 (조회 기반).
10. **다국어** — 한국어 UI만 제공.

---

## 9. 관련 SPEC

- SPEC-STOCK-007 (Phase 8): 종목 검색·가격 차트 — KRX 마스터·`mapping/prices.py` FDR 래퍼·검색 정렬
  패턴을 본 SPEC이 재사용.
- SPEC-STOCK-003 (Phase 4): 관심종목(`WatchlistItem`) — 결과에서 관심종목 추가 흐름 재사용.
- SPEC-STOCK-008 (Phase 9): 섹터 집계 — 섹터 분류 데이터 출처(`AnalysisResult.sector_tags`) 참고.
- SPEC-STOCK-014 (Phase 15): AI 투자 조언 — 프리셋 소유권 검증·UNIQUE 제약 설계 패턴 참조 (마이그 0015).
