---
id: SPEC-STOCK-042
title: 포트폴리오 공유 & 소셜
status: draft
version: 0.2.0
created_at: 2026-06-30
updated_at: 2026-06-30
author: ircp
priority: medium
issue_number: null
branch: feature/SPEC-STOCK-036
labels: [portfolio, sharing, social, feed, backend, frontend]
---

# SPEC-STOCK-042 — 포트폴리오 공유 & 소셜 (Portfolio Sharing & Social)

## HISTORY

| Version | Date | Author | Note |
|---------|------|--------|------|
| 0.1.0 | 2026-06-30 | ircp | 최초 초안 — 공유 링크(토큰) 발급·읽기전용 공개뷰·조회/좋아요 카운트·디스커버리 피드·공개 ON/OFF. EARS REQ 11개·DB 마이그 0026(신규 테이블 2개)·제외 항목 정의 |
| 0.2.0 | 2026-06-30 | ircp | plan-auditor v1 지적사항 반영 — 수용 기준 14개 전부 EARS(WHEN/IF/WHERE … THE SYSTEM SHALL) 형식으로 재작성, REQ-SHARE-003·011 규범 표현 보정(SHALL), AC-13 추적성 NFR→REQ-SHARE-010(공개 피드 데이터 마스킹), REQ-SHARE-003 시나리오(a) AC-14 추가, 테스트 T-013~T-015 추가 |

---

## 1. 개요 (Overview)

사용자가 자신의 포트폴리오를 **읽기 전용 공개 링크**로 공유하고, 공개된 포트폴리오를 다른 사용자가 둘러볼 수 있는 소셜 기능을 추가한다.

- 포트폴리오별로 고유 단축 토큰(`share_token`)을 발급해 `GET /shared/{share_token}` 공개 URL로 보유 종목·수익률·(설정 시) 목표 진척도를 **읽기 전용**으로 노출한다.
- 공개 포트폴리오의 **조회수(view_count)** 와 **좋아요수(like_count)** 를 집계한다. 비로그인 사용자는 조회만, 로그인 사용자는 포트폴리오당 1회 좋아요가 가능하다.
- 최근 공개된 포트폴리오를 **디스커버리 피드(`GET /feed`)** 로 노출하며 좋아요순·최신순 정렬과 페이지네이션을 지원한다.
- 포트폴리오 소유자는 언제든 공개를 켜고 끌 수 있으며, 비공개 상태의 공유 URL 은 404 를 반환한다.

### 1.1 동기 (Why)

SPEC-026/027/030(포트폴리오 AI 최적화·리스크·성과 요약)으로 포트폴리오의 분석 가치는 높아졌으나, 사용자가 자신의 포트폴리오 성과를 **타인에게 보여줄 수단**이 없다. 본 SPEC 은 읽기 전용 공유 링크와 디스커버리 피드를 도입해 "내 포트폴리오 성과 자랑하기"와 "다른 사람의 포트폴리오 구경하기"를 가능하게 한다. 공유는 **읽기 전용 + 소유자 통제** 원칙을 따르며, 원본 포트폴리오 데이터는 변경하지 않는다.

---

## 2. 범위 (Scope)

### 2.1 In-Scope

- 포트폴리오 공유 토큰 발급·재발급(멱등)·공개 ON/OFF (`POST`/`DELETE`/`GET /portfolios/{id}/share`)
- 공개 읽기 전용 포트폴리오 뷰 (`GET /shared/{share_token}`, 무인증)
- 조회수(`view_count`) 자동 증가 — 공개 뷰 호출 시(비로그인 포함)
- 좋아요(`POST /shared/{share_token}/like`, 인증 필수, 멱등) 및 좋아요수 집계
- 디스커버리 피드 (`GET /feed`, 페이지네이션 + 정렬 likes|recent)
- 프라이버시 제어 — 비공개 시 공유 URL 404
- 신규 DB 테이블 `portfolio_shares`, `portfolio_likes` (마이그레이션 0026)
- 프론트엔드 `SharePanel` 컴포넌트(포트폴리오 상세) + `/feed` 페이지

### 2.2 Out-of-Scope (제외)

> [HARD] 본 SPEC 은 아래 항목을 명시적으로 제외한다.

- **자동 매매·자동 주문 실행** (규제·책임 리스크로 프로젝트 영구 제외)
- **팔로우/팔로워 그래프** — MVP 범위 초과, 후속 SPEC 대상
- **댓글·답글** — 소셜 상호작용은 좋아요만 지원
- **좋아요 알림** — 좋아요 발생 시 알림 발송 없음(기존 알림 인프라 미연동)
- **포트폴리오 복제/포크** — 공유는 읽기 전용 열람만, 타인 포트폴리오 복사 기능 없음
- **실시간 갱신(WebSocket)** — 공개 뷰·피드는 요청 시점 스냅샷 조회만
- **좋아요 취소(unlike)** — MVP 는 멱등 좋아요만(취소는 후속 SPEC)
- **신규 알림 채널·신규 수치 라이브러리 도입** — 추가 외부 의존성 없음
- **공유 조회 이력/시계열 저장** — 누적 카운터(view_count·like_count)만 관리

---

## 3. 요구사항 (Requirements — EARS)

> REQ 번호는 논리적 실행 순서(공유 발급 → 비공개 → 상태조회 → 소유권 → 공개뷰 → 조회수 → 좋아요 → 자기좋아요 → 비인증좋아요 → 피드 → 프라이버시)에 맞춰 부여한다.

### 3.1 공유 토큰 발급 (REQ-SHARE-001)

- **REQ-SHARE-001**: WHEN 소유자가 `POST /portfolios/{portfolio_id}/share` 를 호출하면, THEN 시스템은 해당 포트폴리오의 공유 레코드를 생성(없으면)하거나 재사용(있으면)하고 `is_public=True` 로 설정한 뒤 **200 ShareResponse**(`share_token`, `is_public`, `share_url`, `view_count`, `like_count`) 를 반환해야 한다(SHALL). 동일 포트폴리오에 대한 반복 호출은 **기존 `share_token` 을 보존**하며 새 토큰을 발급하지 않는다(멱등 재공유).

### 3.2 공유 비공개 (REQ-SHARE-002)

- **REQ-SHARE-002**: WHEN 소유자가 `DELETE /portfolios/{portfolio_id}/share` 를 호출하면, THEN 시스템은 해당 공유 레코드의 `is_public=False` 로 갱신(소프트 비공개)하고 **204** 를 반환해야 한다(SHALL). `share_token` 행과 누적 카운터(`view_count`·좋아요)는 보존하며 삭제하지 않는다(재공개 시 동일 토큰·카운터 유지).

### 3.3 공유 상태 조회 (REQ-SHARE-003)

- **REQ-SHARE-003**: WHEN 소유자가 `GET /portfolios/{portfolio_id}/share` 를 호출하면, THEN 시스템은 현재 공유 상태(`share_token`, `is_public`, `share_url`, `view_count`, `like_count`) 를 **200 ShareResponse** 로 반환해야 한다(SHALL). IF 해당 포트폴리오에 공유 레코드가 한 번도 생성된 적이 없으면, THEN **204 No Content**(본문 없음)를 반환해야 한다 (SHALL).

### 3.4 소유권·접근 제어 (REQ-SHARE-004)

- **REQ-SHARE-004**: IF 요청 사용자가 해당 포트폴리오의 소유자가 아니면, THEN 시스템은 소유자 전용 엔드포인트(`POST`/`DELETE`/`GET /portfolios/{portfolio_id}/share`) 에서 **404** 를 반환해야 한다(SHALL). (존재 여부 노출 방지를 위해 403 이 아닌 404 사용 — 기존 포트폴리오 라우터 규약 준수, REQ-GOAL-004 패턴 동일)

### 3.5 공개 읽기 전용 뷰 (REQ-SHARE-005)

- **REQ-SHARE-005**: WHEN 누구든(인증 불필요) `GET /shared/{share_token}` 를 호출하면, IF 해당 토큰의 공유 레코드가 존재하고 AND `is_public=True` 이면, THEN 시스템은 포트폴리오의 **읽기 전용** 데이터(보유 종목·평가액·수익률·설정 시 목표 진척도·`view_count`·`like_count`) 를 **200 SharePublicResponse** 로 반환해야 한다(SHALL). 공개 뷰는 포트폴리오 소유자 식별 정보(user_id·이메일 등)를 노출하지 않는다.

### 3.6 조회수 증가 (REQ-SHARE-006)

- **REQ-SHARE-006**: WHEN `GET /shared/{share_token}` 가 성공적으로 공개 뷰를 반환할 때(`is_public=True`), THEN 시스템은 해당 공유 레코드의 `view_count` 를 **1 증가**시켜야 한다(SHALL). 조회수 증가는 **비로그인 사용자 호출에도 적용**되며, 인증 여부와 무관하다. 비공개(404) 응답 시에는 증가시키지 않는다.

### 3.7 좋아요 (REQ-SHARE-007)

- **REQ-SHARE-007**: WHEN 인증된 사용자가 `POST /shared/{share_token}/like` 를 호출하면, IF 공유 레코드가 `is_public=True` 이고 AND 해당 사용자가 아직 좋아요하지 않았으면, THEN 시스템은 `portfolio_likes` 에 1행을 적재하고 **200 LikeResponse**(`like_count`, `liked=True`) 를 반환해야 한다(SHALL). IF 동일 사용자가 이미 좋아요한 포트폴리오에 재호출하면, THEN 시스템은 신규 행을 추가하지 않고 **200 LikeResponse**(현재 `like_count`, `liked=True`) 를 반환한다(멱등 — 409 가 아님).

### 3.8 자기 좋아요 금지 (REQ-SHARE-008)

- **REQ-SHARE-008**: IF 좋아요 요청 사용자가 해당 포트폴리오의 **소유자**이면, THEN 시스템은 `POST /shared/{share_token}/like` 에서 **403 Forbidden** 을 반환해야 한다(SHALL). 소유자는 자신의 포트폴리오에 좋아요할 수 없다.

### 3.9 비인증 좋아요 거부 (REQ-SHARE-009)

- **REQ-SHARE-009**: IF 좋아요 요청에 유효한 인증 정보가 없으면, THEN 시스템은 `POST /shared/{share_token}/like` 에서 **401 Unauthorized** 를 반환해야 한다(SHALL). (공개 뷰 `GET /shared/{share_token}` 는 무인증 허용이지만 좋아요는 인증 필수)

### 3.10 디스커버리 피드 (REQ-SHARE-010)

- **REQ-SHARE-010**: WHEN 누구든(인증 불필요) `GET /feed?sort={likes|recent}&page={int}&size={int}` 를 호출하면, THEN 시스템은 `is_public=True` 인 포트폴리오 목록을 **페이지네이션된 FeedResponse**(`items: FeedItem[]`, `page`, `size`, `total`) 로 반환해야 한다(SHALL).
  - `sort=likes`: `like_count` 내림차순(동률 시 최신 공유순)
  - `sort=recent`(기본값): 공유 시각(`updated_at`) 내림차순
  - `size` 는 기본 20, 최대 100 으로 제한한다(초과 입력 시 100 으로 클램핑). `page` 는 1 부터 시작하며 범위를 벗어나면 빈 `items` 를 반환한다.

### 3.11 프라이버시 제어 (REQ-SHARE-011)

- **REQ-SHARE-011**: IF 공유 레코드가 존재하지 않거나 OR `is_public=False` 이면, THEN 시스템은 `GET /shared/{share_token}` 및 `POST /shared/{share_token}/like` 에서 **404** 를 반환해야 한다(SHALL). 또한 `GET /feed` 결과에서 비공개 포트폴리오는 제외되어야 한다 (SHALL)(`is_public=False` 는 피드 미노출).

---

## 4. DB 스키마 (Migration 0026)

> 마이그레이션 경로: `backend/alembic/versions/0026_portfolio_shares_042.py`
> down_revision = `0025` (직전: `0025_portfolio_goals_041.py`)

```sql
-- portfolio_shares (신규 테이블, 마이그레이션 0026)
CREATE TABLE portfolio_shares (
    id           SERIAL PRIMARY KEY,
    portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    share_token  VARCHAR(32) NOT NULL UNIQUE,   -- secrets.token_urlsafe(16) → 22자 URL-safe 문자열
    is_public    BOOLEAN NOT NULL DEFAULT FALSE,
    view_count   INTEGER NOT NULL DEFAULT 0,
    created_at   TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX ix_portfolio_shares_portfolio_id ON portfolio_shares (portfolio_id);
CREATE INDEX        ix_portfolio_shares_is_public     ON portfolio_shares (is_public);

-- portfolio_likes (신규 테이블, 마이그레이션 0026)
CREATE TABLE portfolio_likes (
    id           SERIAL PRIMARY KEY,
    portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at   TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_portfolio_likes_portfolio_user UNIQUE (portfolio_id, user_id)
);

CREATE INDEX ix_portfolio_likes_portfolio_id ON portfolio_likes (portfolio_id);
```

### 4.1 설계 노트

- **`share_token` 타입**: 작업지시서 헤더는 "share_token UUID unique" 로 표기하나, 실제 토큰 생성은 `secrets.token_urlsafe(16)`(22자 URL-safe 문자열)을 사용한다. 따라서 컬럼 타입은 PostgreSQL `UUID` 가 아니라 **`VARCHAR(32) UNIQUE`** 로 정의한다(여유 길이 확보). 토큰은 단축 URL 용 불투명 식별자이며 추측 불가성을 위해 `secrets` 모듈을 사용한다.
- **포트폴리오당 공유 1행**: `portfolio_id` 에 **UNIQUE 인덱스**를 부여해 포트폴리오당 공유 레코드 1개를 강제한다(재공유 멱등성의 DB 레벨 보장). 비공개는 행 삭제가 아닌 `is_public` 플래그 토글로 처리한다.
- **`like_count` 비정규화 없음**: 좋아요수는 `portfolio_likes` 의 `COUNT(*)` 로 집계한다(별도 카운터 컬럼 미보유). `view_count` 만 `portfolio_shares` 에 누적 카운터로 보관한다(공개 뷰 호출마다 UPDATE).
- **CASCADE**: 포트폴리오 삭제 시 공유·좋아요 행이 함께 삭제된다(`ON DELETE CASCADE`).

---

## 5. API 엔드포인트

| Method | Path | 인증 | 응답 | 설명 |
|--------|------|------|------|------|
| POST | `/portfolios/{portfolio_id}/share` | 필수(소유자) | 200 `ShareResponse` / 404 | 공유 발급·재공유(멱등, `is_public=True`) |
| DELETE | `/portfolios/{portfolio_id}/share` | 필수(소유자) | 204 / 404 | 공유 비공개(`is_public=False`) |
| GET | `/portfolios/{portfolio_id}/share` | 필수(소유자) | 200 `ShareResponse` / 204 / 404 | 공유 상태 조회. 공유 레코드 없으면 204 |
| GET | `/shared/{share_token}` | 무인증 | 200 `SharePublicResponse` / 404 | 공개 읽기 전용 뷰(+view_count 증가) |
| POST | `/shared/{share_token}/like` | 필수 | 200 `LikeResponse` / 401 / 403 / 404 | 좋아요(멱등). 비인증 401·소유자 403·비공개 404 |
| GET | `/feed` | 무인증 | 200 `FeedResponse` | 공개 포트폴리오 목록(페이지네이션·정렬 likes\|recent) |

- 소유자 전용 엔드포인트(`/portfolios/{id}/share`)는 `get_current_user` 보호 + 소유권 검증(REQ-SHARE-004, 비소유자 404). 라우터 prefix 는 기존 `/portfolios` (복수) 를 따른다 — `portfolio/router.py` 확장.
- 공개 엔드포인트(`/shared/{share_token}`, `/feed`)는 **별도 라우터 prefix** 로 분리한다. `GET /shared/{token}` 과 `GET /feed` 는 인증 의존성 없이 동작하고, `POST /shared/{token}/like` 만 `get_current_user` 를 요구한다.
- `share_url` 은 응답에서 `f"/shared/{share_token}"` 상대 경로로 제공한다(절대 호스트 결합은 프론트 책임).

---

## 6. Pydantic 스키마

> 위치: `backend/src/stock_picker/portfolio/schemas.py` 확장. 모든 응답 스키마는 `model_config = ConfigDict(from_attributes=True)` 를 사용한다.

- **`ShareCreate`**
  - 본문 없음(빈 페이로드) 또는 향후 확장 대비 빈 모델. 공유 발급은 경로 파라미터만으로 동작한다.
- **`ShareResponse`** (소유자 응답)
  - `share_token: str`
  - `is_public: bool`
  - `share_url: str`  (예: `/shared/{share_token}`)
  - `view_count: int`
  - `like_count: int`  (`portfolio_likes` COUNT 파생)
  - `created_at: datetime`
- **`SharePublicResponse`** (공개 읽기 전용 뷰)
  - `portfolio_name: str`
  - `holdings: list[PublicHoldingItem]`  (종목명·비중·수익률 등 — 소유자 식별 정보 제외)
  - `total_return_rate: float`
  - `goal_progress: GoalProgressBrief | None`  (목표 설정 시 달성률·잔여일, 미설정 시 null — SPEC-041 `GoalWithProgressResponse` 일부 재사용)
  - `view_count: int`
  - `like_count: int`
- **`LikeResponse`**
  - `like_count: int`
  - `liked: bool`  (항상 True — 멱등 좋아요)
- **`FeedItem`**
  - `share_token: str`
  - `portfolio_name: str`
  - `total_return_rate: float`
  - `view_count: int`
  - `like_count: int`
  - `shared_at: datetime`  (= `portfolio_shares.updated_at`)
- **`FeedResponse`**
  - `items: list[FeedItem]`
  - `page: int`, `size: int`, `total: int`

---

## 7. 프론트엔드 컴포넌트

- **`SharePanel.tsx`** (+ `.js` 사이드카) — 신규 컴포넌트, 포트폴리오 상세 페이지(`frontend/src/pages/Portfolio.tsx`) 에 배치
  - "공유하기" 토글: `POST /portfolios/{id}/share`(공개) / `DELETE`(비공개) 호출
  - 공개 시 `share_url` 복사 버튼 + `view_count`·`like_count` 배지 표시
  - 공유 상태는 진입 시 `GET /portfolios/{id}/share`(204 = 미공유 빈 상태) 로 조회
- **`/feed` 페이지** (`frontend/src/pages/Feed.tsx`) — 신규 페이지
  - 공개 포트폴리오 카드 목록(`FeedItem`): 포트폴리오명·수익률·조회/좋아요 배지
  - 정렬 토글(좋아요순/최신순) + 페이지네이션(더보기 또는 페이지 버튼)
  - 카드 클릭 시 `/shared/{share_token}` 공개 뷰로 이동
  - NavBar(`App.tsx`) 에 `/feed` 라우트 추가(공개 라우트 — 인증 불필요)
- **공개 뷰 페이지** (`frontend/src/pages/SharedPortfolio.tsx`) — 신규, 무인증 라우트
  - `GET /shared/{share_token}` 응답을 읽기 전용으로 렌더(보유 종목·수익률·목표 진척도)
  - 로그인 상태면 좋아요 버튼 활성(`POST /shared/{share_token}/like`), 비로그인이면 로그인 유도
- **API 래퍼**: `frontend/src/api/portfolio.ts`(+ `.js`) 및 신규 `frontend/src/api/feed.ts`
  - `createShare(portfolioId)` / `disableShare(portfolioId)` / `getShareStatus(portfolioId)`(204 → null)
  - `getSharedPortfolio(shareToken)` / `likeSharedPortfolio(shareToken)`
  - `getFeed({ sort, page, size })`

---

## 8. 테스트 계획 (TDD · pytest)

> 위치: `backend/tests/unit/test_portfolio_sharing_042.py` (+ 필요 시 `backend/tests/integration/`)

| ID | 시나리오 |
|----|----------|
| T-001 | 공유 토큰 발급 성공 — `POST` 시 200 + `share_token` 생성 + `is_public=True` |
| T-002 | 멱등 재공유 — 동일 포트폴리오 `POST` 2회 호출 시 `share_token` 불변(새 토큰 미발급) |
| T-003 | 공유 비공개 — `DELETE` 후 `is_public=False`, 204, 토큰·카운터 보존 |
| T-004 | 비공개 → 공개 URL 404 — `is_public=False` 상태에서 `GET /shared/{token}` → 404 |
| T-005 | 공개 뷰 조회수 증가 — `GET /shared/{token}` 호출마다 `view_count` +1 |
| T-006 | 비인증 공개 뷰 허용 — 인증 없이 `GET /shared/{token}`(공개 상태) → 200 |
| T-007 | 좋아요 성공 — 인증 사용자 `POST /shared/{token}/like` → 200 + `like_count` 증가 |
| T-008 | 좋아요 멱등 — 동일 사용자 재좋아요 시 신규 행 없이 200(409 아님), `like_count` 불변 |
| T-009 | 자기 좋아요 금지 — 소유자가 자신 포트폴리오 좋아요 시 403 |
| T-010 | 비인증 좋아요 거부 — 인증 없이 `POST /shared/{token}/like` → 401 |
| T-011 | 피드 정렬 — `GET /feed?sort=likes` 좋아요순·`sort=recent` 최신순 정렬 검증 |
| T-012 | 피드 페이지네이션 — `size`/`page` 적용 + 비공개 포트폴리오 미노출 검증 |
| T-013 | 공유 상태 조회(소유자) — 공유 레코드 존재 시 `GET /portfolios/{id}/share` → 200 + `share_token`·`is_public`·`view_count` 포함 검증 |
| T-014 | 공유 상태 조회(비소유자) — 타 사용자가 `GET /portfolios/{id}/share` → 404 검증 |
| T-015 | 공유 비공개(비소유자) — 타 사용자가 `DELETE /portfolios/{id}/share` → 404 검증 |

---

## 9. 수용 기준 (Acceptance Criteria — EARS)

> 모든 수용 기준은 EARS 형식(WHEN/IF/WHERE … THE SYSTEM SHALL …)으로 기술하며, 각 기준은 단일 REQ-SHARE-NNN 에 추적된다.

- **AC-1** (REQ-SHARE-001): WHEN 포트폴리오 소유자가 `POST /portfolios/{id}/share` 를 요청하면, THE SYSTEM SHALL `share_token`, `share_url`, `is_public=True` 를 포함한 **200 응답**을 반환해야 한다.
- **AC-2** (REQ-SHARE-001): WHEN 소유자가 동일 포트폴리오에 `POST /portfolios/{id}/share` 를 2회 요청하면, THE SYSTEM SHALL 두 응답에서 **동일한 `share_token`** 을 반환해야 한다(새 토큰을 발급하지 않는다 — 멱등 재공유).
- **AC-3** (REQ-SHARE-002): WHEN 소유자가 `DELETE /portfolios/{id}/share` 를 요청하면, THE SYSTEM SHALL `is_public=False` 로 갱신한 **204 응답**을 반환하고 `share_token`·`view_count`·좋아요 행을 보존해야 한다.
- **AC-4** (REQ-SHARE-003): WHEN 포트폴리오 소유자가 `GET /portfolios/{id}/share` 를 요청하고 공유 레코드가 존재하지 않으면, THE SYSTEM SHALL **본문 없는 204 응답**을 반환해야 한다.
- **AC-5** (REQ-SHARE-004): IF 요청 사용자가 해당 포트폴리오의 소유자가 아니면, THE SYSTEM SHALL 소유자 전용 엔드포인트(`POST`/`DELETE`/`GET /portfolios/{id}/share`)에서 **404 응답**을 반환해야 한다(403 이 아님).
- **AC-6** (REQ-SHARE-005): WHEN 누구든(인증 불필요) 공개 상태의 `GET /shared/{share_token}` 를 요청하면, THE SYSTEM SHALL 보유 종목·수익률을 포함하되 소유자 `user_id`·이메일을 제외한 **200 응답**을 반환해야 한다.
- **AC-7** (REQ-SHARE-006): WHEN `GET /shared/{share_token}` 가 공개 뷰를 성공적으로 반환하면, THE SYSTEM SHALL `view_count` 를 정확히 **1 증가**시켜야 하며(비로그인 호출 포함), 404 응답 시에는 증가시키지 않아야 한다.
- **AC-8** (REQ-SHARE-007): WHEN 인증된 사용자가 `POST /shared/{share_token}/like` 를 요청하면, THE SYSTEM SHALL `like_count` 를 1 증가시킨 **200 응답**을 반환하고, 동일 사용자의 재요청 시 `like_count` 를 변경하지 않은 **200 응답**을 반환해야 한다(멱등 — 409 가 아님).
- **AC-9** (REQ-SHARE-008): IF 좋아요 요청 사용자가 해당 포트폴리오의 소유자이면, THE SYSTEM SHALL `POST /shared/{share_token}/like` 에서 **403 응답**을 반환해야 한다.
- **AC-10** (REQ-SHARE-009): IF 좋아요 요청에 유효한 인증 정보가 없으면, THE SYSTEM SHALL `POST /shared/{share_token}/like` 에서 **401 응답**을 반환해야 한다.
- **AC-11** (REQ-SHARE-010): WHEN 누구든 `GET /feed?sort={likes|recent}` 를 요청하면, THE SYSTEM SHALL `sort=likes` 는 `like_count` 내림차순, `sort=recent` 는 `updated_at` 내림차순으로 정렬하고 `size` 100 초과 입력은 100 으로 클램핑한 **FeedResponse** 를 반환해야 한다.
- **AC-12** (REQ-SHARE-011): IF 공유 레코드가 존재하지 않거나 `is_public=False` 이면, THE SYSTEM SHALL `GET /shared/{share_token}` 및 `POST /shared/{share_token}/like` 에서 **404** 를 반환하고 `GET /feed` 결과에서 해당 포트폴리오를 제외해야 한다.
- **AC-13** (REQ-SHARE-010): WHEN 누구든 `GET /feed` 를 요청하면, THE SYSTEM SHALL 각 `FeedItem` 에 소유자 식별 정보(`user_id`·이메일)를 포함하지 않아야 한다(공개 피드 데이터 마스킹).
- **AC-14** (REQ-SHARE-003): WHEN 포트폴리오 소유자가 `GET /portfolios/{id}/share` 를 요청하고 공유 레코드가 존재하면, THE SYSTEM SHALL `share_token`, `share_url`, `is_public`, `view_count` 를 포함한 **200 응답**을 반환해야 한다.

---

## 10. 비기능 요구사항 (NFR)

- **NFR-1**: 신규 외부 라이브러리·신규 알림 채널을 추가하지 않는다(표준 라이브러리 `secrets` 만 토큰 생성에 사용).
- **NFR-2**: 보유 종목·평가액·수익률은 기존 성과 계산 로직(`portfolio/service.py`)을 재사용하고 재구현하지 않는다. 목표 진척도는 SPEC-041 `portfolio/goals.py` 산출(`GoalWithProgressResponse`)을 재사용한다.
- **NFR-3**: DB 변경은 마이그레이션 **0026 단 1개**(신규 테이블 2개)로 제한한다. 기존 테이블 스키마를 변경하지 않는다.
- **NFR-4**: 자동 거래 로직을 포함하지 않는다(영구 제외 정책).
- **NFR-5**: 공개 뷰는 소유자 개인 식별 정보(user_id·이메일 등)를 노출하지 않는다(읽기 전용·익명화 원칙).
- **NFR-6**: `share_token` 은 `secrets.token_urlsafe(16)` 로 생성해 추측 불가성을 보장한다(순차 ID·예측 가능한 토큰 금지).
- **NFR-7**: 백엔드 TDD(pytest), 커버리지는 프로젝트 기준(`fail_under`)을 충족한다. 프론트엔드는 React 컴포넌트로 구현한다.

---

## 11. 코드베이스 정합성 노트 (Implementation Notes)

> RUN 단계에서 작업지시서와 실제 코드가 다른 지점 — 실제 코드를 따른다.

1. **마이그레이션 경로·번호**: 실제 경로는 **`backend/alembic/versions/`** 이며 최신 마이그레이션은 **0025**(`0025_portfolio_goals_041.py`). 따라서 신규는 0026, `down_revision="0025"`.
2. **신규 서비스 위치**: 공유 로직은 신규 모듈 **`backend/src/stock_picker/portfolio/sharing.py`** 에 둔다(`goals.py`·`ai_analysis.py`·`service.py` 형제). 라우터는 `portfolio/router.py`(소유자 엔드포인트) 확장 + 공개 엔드포인트용 신규 라우터(`/shared`·`/feed`).
3. **인증 의존성**: 소유자 엔드포인트와 좋아요는 `auth/dependencies.py` 의 **`get_current_user`** 를 사용한다. 공개 뷰(`GET /shared/{token}`)·피드(`GET /feed`)는 인증 의존성을 **부착하지 않는다**(무인증 허용).
4. **소유권 검증 규약**: 비소유자 접근은 **404**(403 아님) — 기존 포트폴리오 라우터(SPEC-041 REQ-GOAL-004 등) 규약을 따른다.
5. **성과·목표 데이터 재사용**: 공개 뷰의 보유 종목·수익률은 `portfolio/service.py` 의 성과 계산을 재사용하고, 목표 진척도는 SPEC-041 `portfolio/goals.py` 산출물을 재사용한다(공개 뷰에 목표가 설정된 경우만 포함, 미설정 시 `goal_progress=null`).
6. **공개 라우터 등록**: `/shared`·`/feed` 라우터를 `api/main.py` 에 `include_router` 한다. 기존 라우터 prefix 와 충돌하지 않도록 신규 prefix(`/shared`, `/feed`)를 사용한다.
7. **조회수 증가 동시성**: `view_count` 증가는 `UPDATE ... SET view_count = view_count + 1` 형태의 원자적 증분으로 처리한다(읽기-수정-쓰기 레이스 회피).

---

## 12. 의존성

- **SPEC-017 / SPEC-026**: 포트폴리오 성과·보유 종목 조회(`get_portfolio_with_holdings`, `service.py`) 재사용
- **SPEC-041**: 목표 진척도(`portfolio/goals.py`, `GoalWithProgressResponse`) 재사용 — 공개 뷰의 `goal_progress`
- **인증**: `auth/dependencies.py` 의 `get_current_user`
- **기술 스택**: FastAPI + SQLAlchemy 2.0(async, asyncpg) + Alembic(Python 3.12), React + TypeScript(Vite), 표준 라이브러리 `secrets`
