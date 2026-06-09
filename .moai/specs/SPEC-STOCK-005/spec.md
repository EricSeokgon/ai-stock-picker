---
id: SPEC-STOCK-005
version: 0.1.0
status: draft
created: 2026-06-09
updated: 2026-06-09
author: ircp
priority: high
issue_number: null
---

# SPEC-STOCK-005: 한국 주식 & ETF 추천 시스템 — Phase 6 (성능·UX 고도화)

## HISTORY

- 2026-06-09 (v0.1.0): 최초 작성. SPEC-STOCK-001(MVP)·002(개인화)·003(실시간)·004(알림) 완료 위에 성능·UX 축을 고도화한다. 3대 영역 — (A) Redis 캐싱 레이어(추천 결과·현재가), (B) 추천 필터·정렬 API와 프론트 필터 바, (C) 모바일 반응형 레이아웃 — 을 단일 SPEC으로 정의. SPEC-STOCK-003 Exclusions에서 연기된 "AI 분석 결과 이력"은 본 SPEC 범위 밖으로 명시 제외하고, CHANGELOG Planned의 "모바일 반응형 UI"·"Redis 캐싱 실제 활용"·"추천 필터/정렬 고도화"를 구현한다.

---

## 1. 시스템 개요

### 1.1 목적

SPEC-STOCK-001~004로 추천·개인화·실시간·알림 축을 완성한 위에, **반복 조회 비용을 줄이고(성능) 사용자가 원하는 추천만 빠르게 골라 보도록(UX)** 시스템을 고도화한다. Phase 6은 다음을 추가한다.

1. **Redis 캐싱 레이어(Caching Layer)**: 추천 결과를 Redis에 TTL 30분으로 캐싱하고, 현재가를 Redis에 TTL 60초로 캐싱하여 FinanceDataReader 반복 호출(특히 알림 점검 시)을 줄인다. Redis 장애 시에도 기존 동작으로 안전하게 폴백한다.
2. **추천 필터 & 정렬(Filter & Sort)**: `GET /recommendations`에 섹터 필터·정렬 기준·최소 점수 쿼리 파라미터를 추가하고, 프론트에 필터 바 UI를 제공한다.
3. **모바일 반응형 레이아웃(Responsive Layout)**: 네비게이션·추천 목록·포트폴리오·관심 목록을 모바일(<768px)에서 가독성 있게 표시한다.

### 1.2 타겟 사용자

| 사용자 그룹 | 특성 | Phase 6에서 추가되는 핵심 니즈 |
|------------|------|------------------------------|
| 모바일 사용자 | 출퇴근 중 휴대폰으로 확인 | 작은 화면에서도 추천·포트폴리오·관심목록을 가독성 있게 확인 |
| 액티브 트레이더 | 특정 섹터·고점수 종목만 빠르게 보고 싶음 | 섹터 필터·정렬·최소 점수로 추천을 좁혀 조회 |
| 운영자 / 시스템 | 반복 조회·알림 점검으로 외부 API 부하 발생 | Redis 캐싱으로 FinanceDataReader 호출 최소화 |

### 1.3 핵심 가치 제안

- **응답 속도**: 추천·현재가를 캐시 히트로 즉시 반환하여 외부 API 왕복을 제거한다.
- **외부 API 보호**: 알림 점검(5분 주기, SPEC-STOCK-004)에서 종목당 매번 FinanceDataReader를 호출하던 부담을 60초 캐시로 완화한다.
- **선택적 탐색**: 사용자가 섹터·정렬·최소 점수로 추천을 좁혀 본인 관심에 맞는 종목만 확인한다.
- **접근성**: 모바일에서도 데스크톱과 동등한 정보 접근을 제공한다.
- **안전한 확장**: Redis가 다운되어도 기존 기능이 끊기지 않는다([HARD], REQ-CACHE-007). 자동 매매/주문은 영구 제외를 유지한다.

### 1.4 기존 시스템과의 관계 (SPEC-STOCK-001/002/003/004 재정의 금지)

다음은 이미 구현 완료된 자산이며 **본 SPEC에서 재정의하지 않고 재사용·확장**한다.

- 백엔드: FastAPI + PostgreSQL + Redis(`api/deps.py` `get_redis_client`/`get_cache`), 프론트: React 18 + TypeScript + Vite + React Router
- 추천 캐시: SPEC-STOCK-001의 `recommendation/cache.py`(`RecommendationCache`, TTL 1800초, 키 `recommendations:{date}`)와 `GET /recommendations`(`api/routes/recommendations.py`) — **본 SPEC은 이 캐시 동작을 확장**하며, 추천 결과를 캐시에 적재하는 주체는 기존 스케줄러임을 유지한다(REQ-NFR-004).
- 현재가 조회: SPEC-STOCK-003의 `realtime/price_feed.py` `get_current_price(krx_code)`(동기, FinanceDataReader, 모듈 내 in-memory `_price_cache`) — **본 SPEC은 여기에 Redis 캐시 레이어를 추가**한다. 호출처: `realtime/ws_router.py`, `scheduler/jobs.py`(알림 점검), `portfolio/service.py`(자체 `_get_current_price`).
- 섹터 데이터: `AnalysisResult.sector_tags`(기사별), `sector_trends` 테이블 — 추천 종목의 섹터는 별도 컬럼이 없으므로 본 SPEC에서 파생 방식을 정의(REQ-FILTER-002 맥락, §5.5).
- 추천 응답 스키마: `api/schemas.py` `RecommendationItem`(rank, krx_code, total_score, sentiment_score, volume_score, momentum_score, anomaly_score, reasoning) — 섹터 필드 부재(설계 결정 §5.5).
- 프론트: `App.tsx`(NavBar, 라우팅, Dashboard), `components/RecommendationList.tsx`, `pages/Portfolio.tsx`, `pages/Watchlist.tsx`, `pages/Settings.tsx`(SPEC-STOCK-004 신규).

---

## 2. 핵심 기능 요구사항 (EARS)

표기 규칙: **WHEN**(이벤트 구동), **WHILE**(상태 구동), **WHERE**(선택적 기능), **IF...THEN**(원치 않는 동작), **SHALL**(보편 요구).

### 2.1 Redis 캐싱 레이어 (REQ-CACHE) — Priority High

- **REQ-CACHE-001 (Event)**: **WHEN** `GET /recommendations`가 호출되면, the 시스템 **SHALL** 요청 파라미터(limit·sector·sort·min_score)에 대응하는 캐시 키를 구성하여 Redis를 먼저 조회하고, 히트 시 캐시된 추천 JSON을 직접 반환한다.
- **REQ-CACHE-002 (Event)**: **WHEN** 추천 조회가 캐시 미스(해당 키에 데이터 없음)이면, the 시스템 **SHALL** 기존 추천 데이터(스케줄러가 적재한 기준 추천)에서 필터·정렬을 적용해 결과를 구성하고, 그 결과를 해당 키로 Redis에 TTL 1800초(30분)로 저장한 뒤 반환한다.
- **REQ-CACHE-003 (Ubiquitous)**: the 시스템 **SHALL** 추천 캐시 키를 다음 패턴으로 관리한다 — 기준 추천 `recommendations:{date}`(기존, 변경 금지), 상위 N개 `recommendations:top:{limit}`, 섹터별 `recommendations:sector:{sector}`.
- **REQ-CACHE-004 (Event)**: **WHEN** 스케줄러가 신규 추천을 산출하여 기준 추천 캐시를 갱신하면, the 시스템 **SHALL** 본 SPEC이 추가한 파생 추천 캐시 키(`recommendations:top:*`, `recommendations:sector:*`)를 무효화(삭제 또는 만료)하여 다음 조회에서 최신 데이터로 재구성되게 한다.
- **REQ-CACHE-005 (Event)**: **WHEN** `get_current_price(krx_code)`가 호출되면, the 시스템 **SHALL** Redis 키 `price:{krx_code}`를 먼저 조회하여 히트 시 캐시된 시세를 반환하고, 미스 시 FinanceDataReader로 조회한 결과를 `price:{krx_code}`에 TTL 60초로 저장한 뒤 반환한다.
- **REQ-CACHE-006 (Ubiquitous)**: the 시스템 **SHALL** Redis 접속 정보를 환경 변수 `REDIS_URL`(기본 `redis://localhost:6379/0`)에서 읽는다.
- **REQ-CACHE-007 (Unwanted) [HARD]**: **IF** Redis가 응답하지 않거나 연결·읽기·쓰기에 실패하면, **THEN** the 시스템 **SHALL** 오류를 로그한 뒤 캐시를 우회하여 기존 데이터 소스(추천은 DB/기존 동작, 시세는 FinanceDataReader)로 정상 동작하며, 어떤 기존 기능도 중단·실패하지 않는다.
- **REQ-CACHE-008 (Unwanted)**: **IF** 캐시에 저장된 값이 손상되어 역직렬화에 실패하면, **THEN** the 시스템 **SHALL** 해당 캐시를 미스로 간주하고 원본 데이터로 재구성하며 오류로 처리하지 않는다.

### 2.2 추천 필터 & 정렬 (REQ-FILTER) — Priority High

- **REQ-FILTER-001 (Event)**: **WHEN** `GET /recommendations?limit={n}`가 호출되면, the 시스템 **SHALL** 정렬된 추천 중 상위 n개만 반환한다(기존 limit 동작 유지·확장).
- **REQ-FILTER-002 (Event)**: **WHEN** `GET /recommendations?sector={sector}`가 호출되면, the 시스템 **SHALL** 해당 섹터에 속한 추천 종목만 필터링하여 반환한다.
- **REQ-FILTER-003 (Event)**: **WHEN** `GET /recommendations?sort={field}`(field ∈ {score, sentiment, volume})가 호출되면, the 시스템 **SHALL** 지정 기준으로 내림차순 정렬한 결과를 반환하며, 미지정 시 기본값 `score`(total_score)로 정렬한다.
- **REQ-FILTER-004 (Event)**: **WHEN** `GET /recommendations?min_score={x}`가 호출되면, the 시스템 **SHALL** total_score가 x 이상인 추천만 반환한다.
- **REQ-FILTER-005 (Ubiquitous)**: the 시스템 **SHALL** 위 쿼리 파라미터(limit·sector·sort·min_score)를 조합 적용하며, 모든 파라미터가 생략된 기본 호출은 SPEC-STOCK-001과 동일한 응답(기준 추천)을 반환한다(하위 호환).
- **REQ-FILTER-006 (Unwanted)**: **IF** 유효하지 않은 파라미터(sort가 허용값 외, limit·min_score가 음수 또는 비숫자)가 전달되면, **THEN** the 시스템 **SHALL** 422로 거부하거나 안전한 기본값으로 처리하되, 서버 오류(500)를 발생시키지 않는다.
- **REQ-FILTER-007 (Unwanted)**: **IF** 필터 조건에 부합하는 추천이 없으면, **THEN** the 시스템 **SHALL** 빈 추천 목록(`recommendations: []`)을 정상 응답으로 반환하고 오류로 처리하지 않는다.

### 2.3 프론트엔드 필터 바 (REQ-FE) — Priority High

- **REQ-FE-001 (Ubiquitous)**: the 시스템 **SHALL** 대시보드 추천 목록(`RecommendationList`) 상단에 필터 바를 제공하여 섹터 드롭다운·정렬 선택(추천점수/감성점수/거래량이상)·최소 점수 입력을 표시한다.
- **REQ-FE-002 (Ubiquitous)**: the 시스템 **SHALL** 섹터 드롭다운 항목을 현재 조회된 추천 데이터에서 도출되는 섹터 목록으로 구성한다.
- **REQ-FE-003 (Event)**: **WHEN** 사용자가 필터·정렬·최소 점수를 변경하면, the 시스템 **SHALL** 해당 조건을 쿼리 파라미터로 `GET /recommendations`에 반영하여 추천 목록을 갱신한다.
- **REQ-FE-004 (Ubiquitous)**: the 시스템 **SHALL** 필터 바에 "필터 초기화" 버튼을 제공하여 모든 필터를 기본값으로 되돌린다.
- **REQ-FE-005 (Unwanted)**: **IF** 추천 조회 요청이 실패하면, **THEN** the 시스템 **SHALL** 사용자에게 오류 메시지를 표시하고 직전 추천 목록 표시 상태를 유지한다.

### 2.4 모바일 반응형 레이아웃 (REQ-RESP) — Priority Medium

- **REQ-RESP-001 (State)**: **WHILE** 뷰포트 너비가 768px 미만인 동안, the 시스템 **SHALL** 네비게이션 바를 햄버거 메뉴로 표시하고, 메뉴 항목을 토글로 펼친다.
- **REQ-RESP-002 (State)**: **WHILE** 뷰포트 너비가 768px 미만인 동안, the 시스템 **SHALL** 추천 목록을 가로 스크롤 없는 세로 카드 레이아웃으로 표시한다.
- **REQ-RESP-003 (State)**: **WHILE** 뷰포트 너비가 768px 미만인 동안, the 시스템 **SHALL** 포트폴리오 화면의 표를 가로 스크롤 또는 카드 형태로 표시하여 화면을 넘치지 않게 한다.
- **REQ-RESP-004 (State)**: **WHILE** 뷰포트 너비가 768px 미만인 동안, the 시스템 **SHALL** 관심 목록 화면을 컴팩트 카드 뷰로 표시한다.
- **REQ-RESP-005 (Ubiquitous)**: the 시스템 **SHALL** 반응형 처리를 CSS 미디어 쿼리만으로 구현하며 신규 UI 의존성(프레임워크·라이브러리)을 추가하지 않는다.
- **REQ-RESP-006 (State)**: **WHILE** 뷰포트 너비가 768px 이상인 동안, the 시스템 **SHALL** SPEC-STOCK-001~004의 데스크톱 레이아웃·동작을 변경 없이 유지한다.

### 2.5 비기능 요구사항 (REQ-NFR)

- **REQ-NFR-001 (Ubiquitous)**: the 시스템 **SHALL** 캐시 히트/미스·캐시 무효화·Redis 실패 폴백을 구조화 로그로 남기되, 자격 증명·시크릿 원문은 로그에 포함하지 않는다.
- **REQ-NFR-002 (Ubiquitous) [HARD]**: the 시스템 **SHALL** Redis 가용성과 무관하게 모든 기존 기능(추천 조회·현재가·알림 점검·포트폴리오·관심 목록)이 동작하도록 캐시 접근을 격리한다(REQ-CACHE-007 강화).
- **REQ-NFR-003 (Ubiquitous)**: the 시스템 **SHALL** Phase 6 기능 추가 시 SPEC-STOCK-001/002/003/004의 기존 API·테이블·스케줄러 작업·동작을 변경 없이 유지한다(하위 호환). 신규 DB 테이블·마이그레이션은 추가하지 않는다.
- **REQ-NFR-004 (Ubiquitous)**: the 시스템 **SHALL** 기존 추천 캐시 키 `recommendations:{date}` 및 그 적재 주체(스케줄러)를 변경하지 않고, 파생 키만 본 SPEC에서 추가·무효화한다.
- **REQ-NFR-005 (Ubiquitous)**: the 시스템 **SHALL** 현재가 Redis 캐시를 동기 호출 컨텍스트(`get_current_price`)와 호환되도록 구현하여, 비동기 전환 없이 기존 호출처(ws_router·scheduler·portfolio)가 그대로 동작하게 한다.

---

## 3. Exclusions (What NOT to Build)

본 SPEC 범위에서 명시적으로 **제외**되는 항목:

- **자동 매매/주문 실행**: 증권사 API를 통한 실제 매수/매도 주문 기능은 **영구 제외**한다 (규제·책임 리스크).
- **AI 분석 결과 이력 영구 저장**: SPEC-STOCK-003에서 연기된 "persistent AI analysis history"는 본 SPEC 범위 밖으로 제외한다(별도 SPEC 후보).
- **신규 DB 테이블·마이그레이션**: 본 SPEC은 캐싱·필터·UI에 한정하며 스키마 변경을 동반하지 않는다.
- **추천 점수 알고리즘 변경**: 정렬·필터는 기존 점수 위에서만 동작하며, 점수 산출 로직(scoring)은 변경하지 않는다.
- **신규 프론트 UI 프레임워크/라이브러리**: 반응형은 CSS 미디어 쿼리만 사용하며 Tailwind·UI 라이브러리를 도입하지 않는다(REQ-RESP-005).
- **분산 캐시·캐시 워밍/프리페치 고도화**: 다중 노드 캐시, 사전 적재(warming), 캐시 일관성 프로토콜 등은 제외한다.
- **실시간 시세 캐시 무효화 이벤트(pub/sub)**: 현재가 캐시는 TTL(60초) 만료에만 의존하며, 별도 무효화 이벤트 채널은 제외한다.
- **해외 주식/암호화폐**: 한국 주식(KRX)과 국내 상장 ETF만 대상이다.

---

## 4. 가정 및 제약 (Assumptions & Constraints)

ASSUMPTIONS I'M MAKING:
1. 기존 `GET /recommendations`가 Redis 캐시(`recommendations:{date}`)에서 추천을 읽고, 그 캐시는 스케줄러가 적재하는 구조라고 가정한다(코드 확인됨). 따라서 본 SPEC의 필터·정렬은 "캐시에 적재된 기준 추천을 메모리에서 가공"하는 방식으로 구현 가능하다고 가정한다.
2. 추천 종목의 섹터는 `RecommendationItem`·`recommendations` 테이블에 컬럼이 없으므로, 섹터 필터는 (a) 추천 산출 시 기여 기사(`AnalysisResult.sector_tags`)에서 대표 섹터를 파생해 캐시 JSON에 포함하거나, (b) 조회 시 StockMention→Article→AnalysisResult 조인으로 도출한다고 가정한다. 본 SPEC은 (a)를 우선 권장한다(§5.5).
3. `get_current_price`는 동기 함수이며 Redis 비동기 클라이언트와 직접 결합하기 어렵다 — 동기 Redis 클라이언트(`redis` 동기 API) 또는 동기 브리지를 사용해 `price:{krx_code}` 캐시를 구현한다고 가정한다(REQ-NFR-005).
4. 운영 환경에 Redis가 제공되며, 미가용 시에도 폴백으로 안전 동작해야 한다(REQ-CACHE-007, REQ-NFR-002).
5. 모바일 기준 분기점은 768px(<768px = 모바일)이며, 그 이상은 기존 데스크톱 레이아웃을 유지한다고 가정한다.
6. 필터/정렬 결과 캐시는 파라미터 조합별로 키가 분리되며, 기준 추천 갱신 시 일괄 무효화된다고 가정한다(REQ-CACHE-004).

제약:
- 본 시스템은 **투자 정보 제공 도구**이며 투자 권유·자문이 아니다. 추천 응답의 면책 고지(`DISCLAIMER`)를 유지한다.
- 신규 외부 패키지 추가는 최소화한다(Redis 클라이언트는 기존 의존성 재사용, 반응형은 CSS만 사용).
- 기존 테이블·마이그레이션·스케줄러 트리거는 변경하지 않는다(REQ-NFR-003/004).

---

## 5. 기술 접근 (Technical Approach)

### 5.1 Redis 키 패턴 및 TTL

| 키 패턴 | 용도 | TTL | 적재/무효화 주체 |
|--------|------|-----|----------------|
| `recommendations:{date}` | 기준 추천(기존, 변경 금지) | 1800s | 스케줄러(기존) |
| `recommendations:top:{limit}` | 상위 N개 캐시 | 1800s | `/recommendations` 미스 시 적재, 기준 갱신 시 무효화 |
| `recommendations:sector:{sector}` | 섹터별 캐시 | 1800s | `/recommendations` 미스 시 적재, 기준 갱신 시 무효화 |
| `price:{krx_code}` | 현재가 캐시 | 60s | `get_current_price` 미스 시 적재 |

무효화: 스케줄러가 기준 추천을 갱신할 때 `recommendations:top:*`·`recommendations:sector:*` 키를 SCAN/DEL로 제거하거나, 짧은 TTL로 자연 만료시킨다(REQ-CACHE-004).

### 5.2 API 계약 변경 (`GET /recommendations`)

기존 응답 스키마(`RecommendationsResponse`/`PreparingResponse`)는 유지한다. 신규 쿼리 파라미터(모두 선택):

| 파라미터 | 타입 | 기본 | 의미 |
|---------|------|------|------|
| `limit` | int(>0) | 기존 동작 | 상위 N개 |
| `sector` | str | 없음(전체) | 섹터 필터 |
| `sort` | enum {score, sentiment, volume} | score | 정렬 기준(내림차순) |
| `min_score` | float(>=0) | 없음(0) | 최소 total_score |

파라미터 전무 호출은 SPEC-STOCK-001과 동일 응답을 보장한다(REQ-FILTER-005).

### 5.3 백엔드 구조 (신규/변경 모듈)

- `recommendation/cache.py`(변경): 파생 키 적재/조회/무효화 메서드 추가(`get/set` 일반화, `invalidate_derived()`), 손상 데이터 미스 처리(REQ-CACHE-008). 기존 `recommendations:{date}` 동작은 보존.
- `api/routes/recommendations.py`(변경): `GET /recommendations`에 `limit/sector/sort/min_score` 파라미터 추가, 캐시 키 구성→조회→미스 시 기준 추천 가공·적재→반환(REQ-CACHE-001/002, REQ-FILTER-001~007). 유효성 검증(REQ-FILTER-006).
- `realtime/price_feed.py`(변경): `get_current_price`에 Redis `price:{krx_code}` 캐시 레이어 추가(동기 Redis 클라이언트), 실패 시 폴백(REQ-CACHE-005/007, REQ-NFR-005). 기존 in-memory `_price_cache`는 2차 폴백으로 보존 가능.
- `scheduler/jobs.py`(변경): 기준 추천 캐시 갱신 직후 파생 키 무효화 호출 추가(REQ-CACHE-004). 기존 트리거·작업은 불변(REQ-NFR-003).
- `config.py`(재사용): `redis_url`(이미 존재) 사용. 신규 환경 변수 없음.

### 5.4 프론트엔드 구조 (신규/변경)

- `components/RecommendationFilterBar.tsx`(신규): 섹터 드롭다운·정렬 select·최소 점수 입력·초기화 버튼(REQ-FE-001/002/004).
- `App.tsx` Dashboard(변경): 필터 상태 관리, 필터 변경 시 쿼리 파라미터로 추천 재조회, 실패 시 직전 상태 유지(REQ-FE-003/005). 필터 바를 `RecommendationList` 상단에 배치.
- API 클라이언트(변경): `getRecommendations`에 limit/sector/sort/min_score 쿼리 전달.
- 반응형 CSS(신규/변경): `App.tsx` NavBar 햄버거(REQ-RESP-001), `RecommendationList`/Dashboard 카드 레이아웃(REQ-RESP-002), `pages/Portfolio.tsx`(REQ-RESP-003), `pages/Watchlist.tsx`(REQ-RESP-004) — CSS 미디어 쿼리(`@media (max-width: 767px)`)만 사용(REQ-RESP-005). CSS 모듈 또는 전역 스타일시트로 구현.

### 5.5 설계 결정 — 섹터 파생 (Decision Point)

`RecommendationItem`·`recommendations` 테이블에 섹터 컬럼이 없다. 두 가지 방안:

- **방안 A (권장)**: 추천을 캐시에 적재하는 시점(스케줄러)에서 기여 기사 `AnalysisResult.sector_tags`로 대표 섹터를 파생해 캐시 JSON 항목에 비공식 필드로 포함한다. 조회 시 추가 DB 조인 불필요, DB 스키마 불변. 응답 스키마에 섹터 노출 여부는 선택(프론트 드롭다운은 응답 내 섹터로 구성, REQ-FE-002).
- **방안 B**: 조회 시 StockMention→Article→AnalysisResult 조인으로 섹터를 도출. 캐시 적재 변경 불필요하나 조회 비용↑, 캐싱 이점 상쇄.

본 SPEC은 캐싱 목적과 정합한 **방안 A**를 권장하되, run 단계에서 기존 스케줄러 추천 적재 코드 구조에 따라 확정한다. 어느 방안이든 DB 테이블·마이그레이션은 추가하지 않는다(REQ-NFR-003).

### 5.6 의존성 (Dependencies)

- **Phase A (Redis 캐싱)**: 기존 `recommendation/cache.py`·`api/deps.py`·`realtime/price_feed.py`·`scheduler/jobs.py`에 의존. 필터·정렬과 밀접하므로 Phase B와 함께 또는 직전 구현.
- **Phase B (필터·정렬 API)**: Phase A의 캐시 키 구성·섹터 파생(§5.5)에 의존. 프론트 필터 바는 API 계약 확정 후 구현.
- **Phase C (반응형)**: 독립적. Phase A/B와 병렬 가능하나 프론트 변경이 Dashboard에 집중되므로 필터 바(REQ-FE) 작업과 충돌 최소화 위해 순서 조정.

---

## 6. 수용 기준 요약 (Acceptance Summary)

### Phase A — Redis 캐싱 레이어
- 추천 조회가 캐시 히트 시 즉시 반환, 미스 시 가공·적재 후 반환, 키 패턴 준수(REQ-CACHE-001/002/003).
- 기준 추천 갱신 시 파생 키 무효화(REQ-CACHE-004).
- 현재가 `price:{krx_code}` TTL 60초 캐시 동작, FinanceDataReader 호출 감소(REQ-CACHE-005).
- [HARD] Redis 미가용 시 모든 기능 정상 폴백, 손상 데이터 미스 처리(REQ-CACHE-007/008, REQ-NFR-002).

### Phase B — 추천 필터 & 정렬
- limit/sector/sort/min_score 단독·조합 동작, 기본 호출 하위 호환(REQ-FILTER-001~005).
- 잘못된 파라미터 422/기본값 처리(500 금지), 빈 결과 정상 응답(REQ-FILTER-006/007).
- 프론트 필터 바 동작, 섹터 드롭다운 동적 구성, 초기화 버튼, 실패 시 상태 유지(REQ-FE-001~005).

### Phase C — 모바일 반응형
- <768px에서 햄버거 네비·카드형 추천·반응형 포트폴리오/관심목록 표시(REQ-RESP-001~004).
- CSS 미디어 쿼리만 사용(신규 의존성 0), >=768px 데스크톱 동작 불변(REQ-RESP-005/006).

---

## 7. 우선순위 요약

| 우선순위 | 기능 | 근거 |
|---------|------|------|
| High | REQ-CACHE (Redis 캐싱) | 외부 API 부하·응답 속도에 직접 영향, 알림 점검(SPEC-004) 비용 완화 |
| High | REQ-FILTER/REQ-FE (필터·정렬 API + 필터 바) | 사용자 탐색 경험 핵심, 캐시 키 구성과 결합 |
| Medium | REQ-RESP (모바일 반응형) | 접근성 향상, 독립적이며 CSS 한정으로 위험 낮음 |
