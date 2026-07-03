---
id: SPEC-STOCK-045
title: 피드 디스커버리 강화 (트렌딩 정렬 & 이름 검색)
status: draft
version: 0.1.0
created_at: 2026-06-30
updated_at: 2026-06-30
author: ircp
priority: medium
issue_number: null
branch: feature/SPEC-STOCK-036
labels: [portfolio, sharing, social, feed, discovery, search, trending]
---

# SPEC-STOCK-045 — 피드 디스커버리 강화 (Feed Discovery Enhancement)

## HISTORY

| Version | Date | Author | Note |
|---------|------|--------|------|
| 0.1.0 | 2026-06-30 | ircp | 최초 초안 — 공개 디스커버리 피드(`GET /feed`)에 (1)트렌딩 정렬(`sort=trending`, 최근 7일 일별 조회수 합계 내림차순) (2)포트폴리오 이름 부분 검색(`q`, 대소문자 무시) 추가. SPEC-043 `share_view_stats`(마이그 0027) 재사용 — 신규 DB 테이블·마이그레이션 없음. EARS REQ 9개(REQ-FEED-002~010)·AC 12개. SPEC-042 피드 엔드포인트·Feed.tsx·feed.ts 확장 |

---

## 1. 개요 (Overview)

SPEC-STOCK-042 가 공개 디스커버리 피드(`GET /feed`, 무인증)를 도입했으나 정렬 기준은 `recent`(최신순)·`likes`(좋아요순) 두 가지뿐이고, 다수의 공개 포트폴리오 중 원하는 항목을 찾을 검색 수단이 없다. 본 SPEC 은 피드의 **발견성(discoverability)** 을 강화한다.

- **트렌딩 정렬 (`sort=trending`)**: SPEC-043 이 구축한 `share_view_stats`(일별 조회수 집계, 마이그레이션 0027) 테이블을 재사용하여, 각 공개 포트폴리오의 **최근 7일 일별 조회수 합계**가 큰 순서로 정렬한다. 최근 화제가 된 포트폴리오를 상단에 노출한다.
- **이름 검색 (`q`)**: 쿼리 파라미터 `q` 가 주어지면 포트폴리오 이름에 `q` 가 **대소문자 무시 부분 일치**하는 공개 포트폴리오만 반환한다. 검색은 기존 정렬·페이지네이션과 결합된다.
- **Feed 페이지 UI**: 검색 입력창과 트렌딩 정렬 토글을 추가하고, 서버가 반환한 순서를 클라이언트가 재정렬 없이 그대로 렌더한다.

본 SPEC 은 기존 SPEC-042/043 인프라만 확장한다. 신규 DB 테이블·마이그레이션·외부 의존성을 추가하지 않으며, 최신 마이그레이션은 **0027 로 유지**한다.

### 1.1 동기 (Why)

좋아요순 정렬은 누적 좋아요가 많은 오래된 포트폴리오에 유리해 **최근 인기(화제성)** 를 반영하지 못한다. 또한 공개 포트폴리오가 늘어날수록 페이지네이션만으로는 특정 포트폴리오를 찾기 어렵다. 트렌딩 정렬은 이미 수집 중인 일별 조회 데이터(`share_view_stats`)를 활용해 추가 비용 없이 화제성을 노출하고, 이름 검색은 한국 개인 투자자가 관심 포트폴리오를 빠르게 찾도록 돕는다.

---

## 2. 범위 (Scope)

### 2.1 In-Scope

- `backend/src/stock_picker/portfolio/sharing.py` (`get_feed`): `q: str | None` 파라미터 추가(이름 ILIKE 필터), `sort="trending"` 분기 추가(`share_view_stats` 최근 7일 `view_count` 합계 서브쿼리로 내림차순 정렬), `total` 을 필터 적용 후 개수로 반영.
- `backend/src/stock_picker/portfolio/public_router.py` (`get_sharing_feed`): `q: str | None = Query(default=None)` 추가 및 `get_feed` 로 전달, `sort` 설명에 `trending` 추가.
- `frontend/src/api/feed.ts` (+빌드 산출물 `feed.js`): `getFeed` 시그니처에 `sort: 'likes' | 'recent' | 'trending'` 및 선택적 `q?: string` 추가, `q` 가 비어있지 않을 때만 쿼리에 포함.
- `frontend/src/pages/Feed.tsx` (+`Feed.js`): 검색 입력창·제출 핸들러, 트렌딩 정렬 토글 버튼, 정렬/검색어 변경 시 페이지 1 리셋, 검색어 비우기 시 무필터 복원.
- 백엔드 단위 테스트: `backend/tests/unit/test_feed_discovery_045.py` (pytest).
- 프론트엔드 단위 테스트: `frontend/src/__tests__/feed_discovery_045.test.tsx` (vitest + React Testing Library).

### 2.2 Out-of-Scope (제외)

> [HARD] 본 SPEC 은 아래 항목을 명시적으로 제외한다.

- **자동 매매·자동 주문 실행** (규제·책임 리스크로 프로젝트 영구 제외).
- **신규 DB 테이블·마이그레이션** — SPEC-043 `share_view_stats`(0027) 재사용, 최신 마이그레이션 0027 유지, 추가 없음.
- **카테고리·태그 필터** — 포트폴리오에 카테고리 필드가 없으므로 본 SPEC 은 이름 부분 검색만 제공.
- **전문 검색·퍼지 매칭·형태소 분석** — 단순 대소문자 무시 부분 일치(ILIKE substring)만 사용.
- **좋아요 기반 트렌딩 점수** — 트렌딩은 `view_count` 합계만 사용(`share_view_stats` 의 per-day `like_count` 는 본 SPEC 트렌딩 점수에 미반영).
- **개인화·추천 피드** — 사용자별 맞춤 피드 없음. 피드는 무인증 공용.
- **무한 스크롤·실시간 갱신(WebSocket)·자동 폴링** — 기존 페이지네이션 유지.
- **검색어 디바운스의 강제 요구** — 제출(Enter/버튼) 기반 검색이며, 디바운스는 선택적 구현 세부.
- **좋아요 알림 딥링크·이메일/텔레그램 발송** — 후속 과제로 이연.

---

## 3. 요구사항 (Requirements — EARS)

> REQ 번호는 SPEC-042 의 피드 요구사항 **REQ-FEED-001** 에 이어 **REQ-FEED-002** 부터 부여한다. 모든 REQ 는 관찰 가능한 동작을 단일 SHALL 로 기술한다.

### 3.1 트렌딩 정렬 (REQ-FEED-002)

- **REQ-FEED-002**: When a client requests `GET /feed` with `sort=trending`, the system SHALL order the public portfolios by the sum of their daily view counts over the last 7 days in descending order.

### 3.2 최근 조회 없는 항목의 트렌딩 순위 (REQ-FEED-003)

- **REQ-FEED-003**: When a public portfolio has no view records in the last 7 days under trending sort, the system SHALL treat its trending score as 0 and SHALL rank it after every portfolio with a positive recent view sum.

### 3.3 이름 검색 필터 (REQ-FEED-004)

- **REQ-FEED-004**: When a client requests `GET /feed` with a non-empty `q` parameter, the system SHALL return only the public portfolios whose name contains the `q` value matched case-insensitively.

### 3.4 빈 검색어 통과 (REQ-FEED-005)

- **REQ-FEED-005**: When the `q` parameter is absent or empty, the system SHALL return the public portfolios without applying any name filter.

### 3.5 알 수 없는 정렬값 폴백 (REQ-FEED-006)

- **REQ-FEED-006**: If the `sort` parameter is not one of `recent`, `likes`, or `trending`, then the system SHALL fall back to the default recent sort and SHALL NOT return an error response.

### 3.6 필터 반영 total (REQ-FEED-007)

- **REQ-FEED-007**: When a non-empty `q` filter is applied, the `total` field in the feed response SHALL equal the count of public portfolios matching that filter.

### 3.7 검색 제출 동작 (REQ-FEED-008)

- **REQ-FEED-008**: When the user submits a non-empty search term on the Feed page, the page SHALL request the feed with that term as the `q` parameter and SHALL render only the returned portfolios.

### 3.8 트렌딩 토글 동작 (REQ-FEED-009)

- **REQ-FEED-009**: When the user activates the trending sort control on the Feed page, the page SHALL request the feed with `sort=trending` and SHALL render the returned items in server order without client-side reordering.

### 3.9 검색어 비우기 복원 (REQ-FEED-010)

- **REQ-FEED-010**: If the user clears the search term on the Feed page, then the page SHALL request the feed without the `q` parameter and SHALL render the unfiltered list.

---

## 4. 인수 조건 (Acceptance Criteria — EARS)

> 모든 AC 는 EARS(Event-driven / Unwanted behavior) 형식으로 작성하며, 각 AC 는 단일 관찰 가능 동작(단일 SHALL)만 검증한다. 총 12개.

### AC-045-001 — 트렌딩 정렬은 7일 조회 합계 내림차순 (REQ-FEED-002)

When two public portfolios have last-7-day view sums of 50 and 10 and `sort=trending` is requested,
the feed shall return the portfolio with sum 50 before the portfolio with sum 10.

### AC-045-002 — 트렌딩 동점 외 상위 우선 (REQ-FEED-002)

When a portfolio has a higher last-7-day view sum than another under `sort=trending`,
the feed shall place the higher-sum portfolio at an earlier index than the lower-sum portfolio.

### AC-045-003 — 최근 조회 0 항목은 양수 항목 뒤 (REQ-FEED-003)

When a portfolio has no view records in the last 7 days and another has a positive recent view sum,
the feed under `sort=trending` shall rank the zero-score portfolio after the positive-sum portfolio.

### AC-045-004 — 이름 부분 일치 필터 (REQ-FEED-004)

When `q="성장"` is provided and only one public portfolio name contains "성장",
the feed shall return exactly that one portfolio.

### AC-045-005 — 대소문자 무시 매칭 (REQ-FEED-004)

When `q="etf"` is provided and a public portfolio is named "Dividend ETF",
the feed shall include that portfolio in the results.

### AC-045-006 — 빈 q 는 무필터 (REQ-FEED-005)

When the `q` parameter is empty,
the feed shall return public portfolios without applying a name filter.

### AC-045-007 — 알 수 없는 sort 는 recent 폴백 (REQ-FEED-006)

If `sort="popular"` (an unsupported value) is requested,
then the feed shall return results ordered by the default recent sort without an error status.

### AC-045-008 — total 은 필터 후 개수 (REQ-FEED-007)

When `q` matches 3 of 10 public portfolios,
the feed response `total` shall be 3.

### AC-045-009 — 검색 제출 → q 요청·필터 렌더 (REQ-FEED-008)

When the user submits the search term "배당",
the Feed page shall issue a feed request whose `q` parameter equals "배당".

### AC-045-010 — 트렌딩 토글 → sort=trending 요청 (REQ-FEED-009)

When the user activates the trending sort control,
the Feed page shall issue a feed request whose `sort` parameter equals "trending".

### AC-045-011 — 트렌딩 결과 서버 순서 유지 (REQ-FEED-009)

When the feed responds with items in a given order under `sort=trending`,
the Feed page shall render those items in the same order received from the server.

### AC-045-012 — 검색어 비우기 → q 없는 요청 (REQ-FEED-010)

If the user clears a previously entered search term,
then the Feed page shall issue a feed request that contains no `q` parameter.

---

## 5. 기술 설계 (Technical Approach)

### 5.1 백엔드 피드 쿼리 (portfolio/sharing.py `get_feed`)

- 시그니처 확장: `get_feed(db, sort="recent", page=1, size=20, q: str | None = None)`.
- 이름 필터: `q` 가 공백 제거 후 비어있지 않으면 `base_query = base_query.filter(Portfolio.name.ilike(f"%{q}%"))`. `total` 은 이 필터가 적용된 `base_query.count()` 로 계산(기존과 동일 위치).
- 트렌딩 분기: `share_view_stats` 의 최근 7일(KST 기준 오늘 포함 7일) `view_count` 합계 서브쿼리.
  - `trending_subq = db.query(ShareViewStat.share_id, func.sum(ShareViewStat.view_count).label("recent_views")).filter(ShareViewStat.stat_date >= start_date).group_by(ShareViewStat.share_id).subquery()`
  - `base_query.outerjoin(trending_subq, trending_subq.c.share_id == PortfolioShare.id).order_by(func.coalesce(trending_subq.c.recent_views, 0).desc())`
  - `start_date` 는 SPEC-043 `get_share_stats` 의 7일 윈도 계산 패턴과 일치(KST 기준 오늘 포함 직전 7일).
- 정렬 분기 우선순위: `likes` → 좋아요 합계 desc(기존), `trending` → 위 합계 desc(신규), 그 외(빈/알 수 없는 값 포함) → `updated_at` desc(기존 else 경로 유지). 따라서 알 수 없는 sort 는 자동으로 recent 폴백(REQ-FEED-006).
- 반환 `items` 구조(FeedItem)는 변경 없음 — 스키마·마이그레이션 변경 없음.

### 5.2 백엔드 라우터 (portfolio/public_router.py `get_sharing_feed`)

- `q: str | None = Query(default=None, description="포트폴리오 이름 부분 검색(대소문자 무시)")` 추가.
- `sort` 설명에 `trending` 추가: "recent | likes | trending".
- `sharing.get_feed(db, sort=sort, page=page, size=size, q=q)` 로 전달. 응답은 기존 `FeedResponse(**result)` 유지.

### 5.3 프론트엔드 API (api/feed.ts)

- `getFeed(sort: 'likes' | 'recent' | 'trending', page: number, size: number, q?: string)`.
- `URLSearchParams` 에 `sort`, `page`, `size` 를 넣고, `q` 가 공백 아닌 값일 때만 `params.set('q', q)`. 빈/undefined `q` 는 파라미터 미포함(REQ-FEED-010 의 무-q 요청).

### 5.4 Feed 페이지 (pages/Feed.tsx)

- 상태 추가: `query: string`(입력값), `appliedQuery: string`(제출된 검색어). `sort` 유니온에 `'trending'` 추가.
- 정렬 토글 버튼 3개: 좋아요순/최신순/**트렌딩**. 선택 시 `setSort(...)` 및 `setPage(1)`.
- 검색 폼: 입력 + 제출(Enter/버튼) 시 `setAppliedQuery(query.trim())` 및 `setPage(1)`. 비우고 제출(또는 클리어 버튼) 시 `setAppliedQuery('')`.
- 데이터 로드 `useEffect` 의존성에 `appliedQuery` 포함, `getFeed(sort, page, PAGE_SIZE, appliedQuery || undefined)` 호출. 서버 반환 `items` 를 재정렬 없이 그대로 렌더(REQ-FEED-009/011).

### 5.5 빌드 산출물 동기화 (.js/.ts 페어)

- 본 프로젝트는 `.tsx`/`.ts` 소스와 커밋된 `.js` 빌드 산출물을 **쌍으로** 유지한다. 수정한 모든 소스(`feed.ts`, `Feed.tsx`)는 대응 `.js`(`feed.js`, `Feed.js`)도 함께 갱신해야 한다. 백엔드 Python 파일은 빌드 산출물 페어가 없다.

---

## 6. 테스트 목록 (Test Plan)

- 백엔드: `backend/tests/unit/test_feed_discovery_045.py` (pytest, 인메모리/픽스처 DB). 신규 외부 의존성 없음.
- 프론트엔드: `frontend/src/__tests__/feed_discovery_045.test.tsx` (vitest + React Testing Library, API 모듈 모킹).

| ID | 테스트 | 검증 REQ / AC |
|----|--------|---------------|
| T-045-001 | 트렌딩: 7일 조회 합계 큰 항목이 먼저 | REQ-FEED-002 / AC-001 |
| T-045-002 | 트렌딩: 상위 합계가 더 앞 인덱스 | REQ-FEED-002 / AC-002 |
| T-045-003 | 트렌딩: 최근 조회 0 항목은 양수 뒤 | REQ-FEED-003 / AC-003 |
| T-045-004 | 검색: 이름 부분 일치만 반환 | REQ-FEED-004 / AC-004 |
| T-045-005 | 검색: 대소문자 무시 매칭 | REQ-FEED-004 / AC-005 |
| T-045-006 | 빈 q → 무필터 전체 반환 | REQ-FEED-005 / AC-006 |
| T-045-007 | 알 수 없는 sort → recent 폴백, 200 | REQ-FEED-006 / AC-007 |
| T-045-008 | total = q 필터 후 개수 | REQ-FEED-007 / AC-008 |
| T-045-009 | 검색 제출 → q 파라미터로 요청 | REQ-FEED-008 / AC-009 |
| T-045-010 | 트렌딩 토글 → sort=trending 요청 | REQ-FEED-009 / AC-010 |
| T-045-011 | 트렌딩 결과 서버 순서 그대로 렌더 | REQ-FEED-009 / AC-011 |
| T-045-012 | 검색어 비우기 → q 없는 요청 | REQ-FEED-010 / AC-012 |

품질 게이트: 백엔드 pytest 통과(커버리지 기준 충족), 프론트 vitest 통과, ESLint·ruff 통과, 신규 외부 의존성 0, 신규 마이그레이션 0(최신 0027 유지), `.js`/`.ts` 페어 동기화.

---

## 7. 의존성 (Dependencies)

- **SPEC-STOCK-042** (포트폴리오 공유 & 소셜): `GET /feed` 엔드포인트(`get_sharing_feed`)·`get_feed`·`FeedItem`/`FeedResponse`·`Feed.tsx`·`feed.ts`(`getFeed`) — 본 SPEC 의 확장 대상.
- **SPEC-STOCK-043** (공유 통계 & 좋아요 알림): `share_view_stats` 테이블(마이그 0027)·`ShareViewStat` 모델·7일 윈도 집계 패턴(`get_share_stats`) — 트렌딩 점수 산출에 재사용.

---

## 8. 기술 제약 (Technical Constraints)

- FastAPI + SQLAlchemy(동기 Session) 기존 패턴 준수. 트렌딩 서브쿼리는 `func.sum` + `outerjoin` + `func.coalesce(..., 0).desc()` 로 구성하여 조회 이력 없는 항목도 누락 없이 포함.
- 검색은 `Portfolio.name.ilike(f"%{q}%")` 단순 부분 일치만 사용 — 전문 검색·인덱스 추가 없음.
- `/feed` 는 무인증 공용 엔드포인트 — 인증·소유권 검증 없음(기존 동작 유지).
- 트렌딩 7일 윈도는 KST 기준이며 SPEC-043 통계와 동일 기준일을 사용한다.
- React + TypeScript(`.tsx`/`.ts`) 소스, Vite 빌드. 커밋된 `.js` 산출물과 페어 동기화 필수.
- ESLint·ruff 통과, 신규 외부 의존성 금지, 모든 신규 동작 단위 테스트 필수.
