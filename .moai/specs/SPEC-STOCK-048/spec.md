---
id: SPEC-STOCK-048
title: 공유 포트폴리오 댓글 대댓글 (Threaded Comment Replies)
status: draft
version: 0.1.0
created: 2026-07-01
updated: 2026-07-01
author: ircp
priority: medium
issue_number: null
branch: feature/SPEC-STOCK-036
labels: [portfolio, sharing, social, comments, replies, notifications]
---

# SPEC-STOCK-048 — 공유 포트폴리오 댓글 대댓글 (Threaded Comment Replies)

## HISTORY

| Version | Date | Author | Note |
|---------|------|--------|------|
| 0.1.0 | 2026-07-01 | ircp | 최초 초안 — SPEC-046(공유 포트폴리오 댓글)의 평면 댓글을 **1단계 대댓글(스레드)** 로 확장. 기존 `portfolio_comments` 테이블에 nullable 자기참조 컬럼 `parent_comment_id`(self-FK, ondelete CASCADE) 1개를 추가하는 **마이그레이션 0029** 신규(신규 테이블 없음). `add_comment`/`list_comments` 를 확장하여 대댓글 작성·중첩 조회를 지원. 대댓글 작성 시 **부모 댓글 작성자**에게 알림 생성(포트폴리오 소유자 알림은 최상위 댓글에 한정, 중복 알림 방지). 알림은 기존 `type="portfolio_comment"`·`krx_code=f"P{id}"` 규약을 재사용하여 SPEC-047 딥링크가 **inbox_router 변경 없이** 자동 동작. 프론트 `SharedPortfolio.tsx` 에 댓글별 답글 입력·중첩 렌더 추가. 댓글 서비스는 sync(`Session`) 유지. EARS REQ 15개(REQ-REPLY-001~015)·AC 12개·테스트 12개 |

---

## 1. 개요 (Overview)

SPEC-STOCK-042~047 이 공개 포트폴리오 공유·좋아요·댓글·조회통계·트렌딩 피드·알림 딥링크로 소셜 디스커버리 아크를 구축했다. SPEC-046 은 공유 포트폴리오에 **평면(flat) 댓글** 작성·조회·삭제와 소유자 알림을 도입했고, SPEC-047 은 그 댓글·좋아요 알림에 **딥링크**(`/shared/{share_token}`)를 부여해 소유자가 알림 클릭만으로 해당 포트폴리오로 이동할 수 있게 했다. 그러나 현재 댓글은 **서로 이어지지 않는다** — 소유자가 딥링크로 이동해 댓글을 확인해도, 그 댓글에 **답글을 달아 대화를 이어갈 수단이 없다**. 본 SPEC 은 댓글에 **1단계 대댓글(single-level threaded replies)** 을 도입하여, 방문자와 소유자가 특정 댓글 아래에서 대화를 주고받는 **소셜 루프**를 완성한다.

- **스키마 확장 (마이그레이션 0029)**: 기존 `portfolio_comments` 테이블에 nullable 자기참조 컬럼 `parent_comment_id`(FK → `portfolio_comments.id`, `ondelete=CASCADE`)를 추가한다. `NULL` = 최상위 댓글, 값 존재 = 해당 부모 댓글에 대한 답글. **신규 테이블 없음**.
- **대댓글 작성 (backend, sync)**: `add_comment` 를 확장하여 선택적 `parent_comment_id` 를 받는다. 부모가 존재하고 **같은 공유**에 속하며 **최상위 댓글**(부모의 `parent_comment_id` 가 NULL)일 때만 답글을 생성한다. 대댓글은 **부모 댓글 작성자**에게 알림을 생성한다(소유자 중복 알림 방지).
- **중첩 조회 (backend)**: `list_comments` 를 확장하여 **최상위 댓글만 페이지네이션**하고, 각 최상위 댓글에 `replies`(오래된순) 배열을 포함해 반환한다.
- **프론트엔드 (`SharedPortfolio.tsx`)**: 각 최상위 댓글에 답글 입력 UI 를 제공하고, 답글을 부모 댓글 아래에 중첩 렌더한다.

본 SPEC 은 **신규 테이블·외부 의존성이 없으며**, 스키마 변경은 컬럼 1개 추가(마이그레이션 0029)로 한정된다. 알림은 기존 규약(`type="portfolio_comment"`, `krx_code=f"P{portfolio.id}"`)을 재사용하므로 SPEC-047 딥링크가 **inbox_router 수정 없이** 자동으로 답글 알림에도 적용된다.

### 1.1 동기 (Why)

댓글의 사회적 가치는 "대화"에 있다. 평면 댓글만으로는 누가 무엇에 반응하는지 맥락이 끊긴다. 대댓글은 SPEC-046(댓글)·SPEC-047(딥링크)로 이미 구축된 인프라(댓글 CRUD, 소유자 알림, 알림 딥링크)를 **최소 비용(컬럼 1개)** 으로 재사용하여, 소유자가 "누가 내 포트폴리오에 댓글을 달았다 → 딥링크로 이동 → 답글로 응답"하는 완결된 소셜 루프를 만든다. 한국 개인투자자에게는 종목 선정 근거를 두고 공유 포트폴리오에서 **의견을 주고받는 토론 공간**이 참여도와 재방문을 높인다. 1단계 스레딩으로 한정하여 UX 복잡도와 구현 위험을 낮춘다.

---

## 2. 범위 (Scope)

### 2.1 In-Scope

- **DB 마이그레이션 0029**: `backend/alembic/versions/0029_portfolio_comment_replies_048.py` — `portfolio_comments` 에 nullable `parent_comment_id`(Integer, FK → `portfolio_comments.id`, `ondelete=CASCADE`) 컬럼 및 `parent_comment_id` 인덱스 추가. down revision = `0028`.
- **ORM 모델**: `backend/src/stock_picker/db/models.py` — `PortfolioComment` 에 `parent_comment_id: Mapped[int | None]` 자기참조 컬럼 추가.
- **댓글 서비스 확장 (sync)**: `backend/src/stock_picker/portfolio/sharing.py`
  - `add_comment(db, share_token, user_id, content, parent_comment_id=None)` — 답글 작성·검증·부모 작성자 알림.
  - `list_comments(db, share_token, page, size)` — 최상위 댓글 페이지네이션 + 각 항목에 `replies` 배열(오래된순) 포함.
- **엔드포인트**: `backend/src/stock_picker/portfolio/public_router.py` — POST `/shared/{token}/comments` 요청 바디에 선택적 `parent_comment_id` 수용.
- **Pydantic 스키마**: `backend/src/stock_picker/portfolio/schemas.py`(또는 기존 댓글 스키마 위치) — `CommentCreate` 에 `parent_comment_id: int | None = None` 추가, `CommentItem` 에 `parent_comment_id: int | None`·`replies: list[CommentItem]` 추가.
- **프론트엔드 API**: `frontend/src/api/feed.ts`(+빌드 산출물 `feed.js`) — `postComment(token, content, parentCommentId?)` 시그니처 확장, `CommentItem` 타입에 `parent_comment_id`·`replies` 추가.
- **프론트엔드 UI**: `frontend/src/pages/SharedPortfolio.tsx`(+`SharedPortfolio.js`) — 각 최상위 댓글에 답글 입력 폼·답글 목록 중첩 렌더.
- **백엔드 단위 테스트**: `backend/tests/unit/test_comment_replies_048.py`(pytest, sync 픽스처 DB).
- **프론트엔드 단위 테스트**: `frontend/src/__tests__/comment_replies_048.test.tsx`(vitest + React Testing Library, API 모킹).

### 2.2 Out-of-Scope (제외)

> [HARD] 본 SPEC 은 아래 항목을 명시적으로 제외한다.

- **자동 매매·자동 주문 실행** (규제·책임 리스크로 프로젝트 영구 제외).
- **신규 테이블** — 본 SPEC 은 기존 `portfolio_comments` 에 컬럼 1개만 추가한다(마이그레이션 0029, 신규 테이블 0개).
- **2단계 이상 중첩 스레딩** — 답글에 대한 답글은 허용하지 않는다(부모는 반드시 최상위 댓글). 답글에 답글 시도는 거부한다.
- **대댓글 전용 신규 알림 타입(`comment_reply`)·전용 배지** — 답글 알림은 기존 `type="portfolio_comment"` 를 재사용한다(inbox_router·Notifications 배지 미변경). SPEC-047 딥링크가 자동 적용된다.
- **답글에 대한 소유자 중복 알림** — 답글은 부모 댓글 작성자에게만 알림한다. 최상위 댓글의 소유자 알림(SPEC-046)은 유지하되, 답글이 소유자에게 추가로 알림을 발생시키지 않는다(소유자가 부모 댓글 작성자인 경우는 제외).
- **대댓글 좋아요·신고·수정** — 답글의 like/report/edit 은 제외.
- **알림 인박스 라우터(`inbox_router.py`) 변경** — 답글 알림은 기존 규약을 재사용하므로 async 인박스 라우터를 수정하지 않는다.
- **댓글 페이지의 특정 답글로의 앵커 스크롤·하이라이트** — SPEC-047 과 동일하게 공유 포트폴리오 페이지 상단 이동만(답글 앵커 없음).
- **삭제된 부모 댓글의 소프트 삭제·자리표시(placeholder)** — 부모 삭제 시 답글은 self-FK CASCADE 로 함께 물리 삭제된다(placeholder 미표시).
- **답글 목록의 서버측 페이지네이션** — 답글은 부모 댓글당 전체를 반환한다(답글 페이지네이션 없음). 페이지네이션은 최상위 댓글에만 적용.
- **이메일·텔레그램 채널 대댓글 알림 본문** — 인앱 인박스 알림만 대상(외부 채널 템플릿 미변경).

---

## 3. 요구사항 (Requirements — EARS)

> REQ 번호는 대댓글 도메인 신규 접두사 `REQ-REPLY-` 로 001 부터 부여한다(댓글 `REQ-COMMENT`/`REQ-CMT`·좋아요 `REQ-LIKE`·피드 `REQ-FEED`·딥링크 `REQ-NLINK` 와 충돌 회피). 모든 REQ 는 관찰 가능한 동작을 단일 SHALL 로 기술한다.

### 3.1 대댓글 작성·검증 (REQ-REPLY-001 ~ 005)

- **REQ-REPLY-001**: When a user submits a comment with a `parent_comment_id` that references an existing top-level comment belonging to the same shared portfolio, the system SHALL create the comment as a reply linked to that parent comment.
- **REQ-REPLY-002**: When a reply is created, the system SHALL persist the reply's parent reference so that the reply is associated with exactly one parent comment.
- **REQ-REPLY-003**: If a comment submission references a `parent_comment_id` that does not exist, then the system SHALL reject the request with a not-found error.
- **REQ-REPLY-004**: If a comment submission references a `parent_comment_id` that belongs to a different shared portfolio, then the system SHALL reject the request with an error and SHALL NOT create the reply.
- **REQ-REPLY-005**: If a comment submission references a parent comment that is itself a reply (its own parent reference is non-null), then the system SHALL reject the request to enforce single-level threading.

### 3.2 중첩 조회 (REQ-REPLY-006 ~ 007, 011)

- **REQ-REPLY-006**: When the comment list for a shared portfolio is requested, the system SHALL return each top-level comment together with its replies ordered oldest-first.
- **REQ-REPLY-007**: When the comment list is paginated, the system SHALL count and page over top-level comments only, excluding replies from the pagination total.
- **REQ-REPLY-011**: When a reply is returned in the comment list, the system SHALL include the reply author's display name in the reply item, consistent with top-level comment items.

### 3.3 대댓글 알림 (REQ-REPLY-008 ~ 009)

- **REQ-REPLY-008**: When a reply is created and the parent comment's author is a different user than the replier, the system SHALL create an inbox notification for the parent comment's author.
- **REQ-REPLY-009**: If the replier is the same user as the parent comment's author, then the system SHALL NOT create a reply notification.

### 3.4 대댓글 삭제 (REQ-REPLY-010)

- **REQ-REPLY-010**: When a top-level comment that has replies is deleted, the system SHALL also remove that comment's replies.

### 3.5 프론트엔드 (REQ-REPLY-012 ~ 015)

- **REQ-REPLY-012**: Where a top-level comment is rendered on the shared portfolio page, the page SHALL provide a reply action for that comment.
- **REQ-REPLY-013**: When the user submits a reply through a top-level comment's reply action, the page SHALL send the reply request with that comment as its parent.
- **REQ-REPLY-014**: Where a top-level comment has replies, the page SHALL render those replies nested under that parent comment.
- **REQ-REPLY-015**: When a reply submission succeeds, the page SHALL display the new reply under its parent comment without requiring a full page reload.

---

## 4. 인수 조건 (Acceptance Criteria — EARS)

> 모든 AC 는 EARS(Event-driven / State-driven / Unwanted behavior) 형식으로 작성하며, 각 AC 는 단일 관찰 가능 동작(단일 SHALL)만 검증한다. 총 12개.

### AC-048-001 — 대댓글 작성 성공 (REQ-REPLY-001·002)

When a user submits a comment with a `parent_comment_id` referencing an existing top-level comment on the same shared portfolio,
the system shall create a reply whose stored parent reference equals that `parent_comment_id`.

### AC-048-002 — 존재하지 않는 부모 (REQ-REPLY-003)

If a user submits a comment referencing a `parent_comment_id` that does not exist,
then the system shall reject the request with a not-found (404) error.

### AC-048-003 — 다른 공유의 부모 (REQ-REPLY-004)

If a user submits a comment whose `parent_comment_id` belongs to a comment on a different shared portfolio,
then the system shall reject the request and create no reply.

### AC-048-004 — 답글에 대한 답글 거부 (REQ-REPLY-005)

If a user submits a comment referencing a parent that is itself a reply,
then the system shall reject the request.

### AC-048-005 — 중첩 조회 오래된순·작성자명 포함 (REQ-REPLY-006·011)

When the comment list is requested for a shared portfolio that has a top-level comment with two replies,
the system shall return that top-level comment with its two replies ordered oldest-first, each reply including its author's display name.

### AC-048-006 — 페이지네이션은 최상위만 (REQ-REPLY-007)

When the comment list total is computed for a shared portfolio with one top-level comment and three replies,
the system shall report a total of one top-level comment.

### AC-048-007 — 답글 알림 부모 작성자 대상 (REQ-REPLY-008)

When a user posts a reply to a comment authored by a different user,
the system shall create an inbox notification addressed to the parent comment's author.

### AC-048-008 — 자기 답글 무알림 (REQ-REPLY-009)

If a user posts a reply to their own comment,
then the system shall not create a reply notification.

### AC-048-009 — 부모 삭제 시 답글 제거 (REQ-REPLY-010)

When a top-level comment that has replies is deleted,
the system shall also remove that comment's replies.

### AC-048-010 — 프론트 답글 액션 제공 (REQ-REPLY-012)

Where a top-level comment is rendered on the shared portfolio page,
the page shall render a reply action for that comment.

### AC-048-011 — 프론트 답글 전송 시 부모 지정 (REQ-REPLY-013)

When the user submits a reply through a top-level comment's reply action,
the page shall issue a comment request that includes that comment's id as the parent.

### AC-048-012 — 프론트 중첩 렌더·리로드 없는 표시 (REQ-REPLY-014·015)

Where a top-level comment has replies including a newly submitted one,
the page shall render those replies nested under the parent comment without a full page reload.

---

## 5. 기술 설계 (Technical Approach)

### 5.1 스키마 확장 (마이그레이션 0029)

- `0029_portfolio_comment_replies_048.py`: `down_revision = "0028"`.
  - `op.add_column("portfolio_comments", sa.Column("parent_comment_id", sa.Integer(), nullable=True))`.
  - `op.create_foreign_key("fk_portfolio_comments_parent", "portfolio_comments", "portfolio_comments", ["parent_comment_id"], ["id"], ondelete="CASCADE")`.
  - `op.create_index("ix_portfolio_comments_parent", "portfolio_comments", ["parent_comment_id"])`.
  - `downgrade`: 인덱스·FK·컬럼 역순 제거.
- **모델**(`models.py` `PortfolioComment`): `parent_comment_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("portfolio_comments.id", ondelete="CASCADE"), nullable=True)`. 기존 컬럼(`share_id`·`user_id`·`content`·`created_at`) 불변.

### 5.2 대댓글 작성 (`sharing.add_comment`, sync)

- 시그니처 확장: `add_comment(db, share_token, user_id, content, parent_comment_id=None)`.
- `parent_comment_id is None` (최상위 댓글): 기존 SPEC-046 동작 유지 — 저장 후 비소유자면 소유자에게 `portfolio_comment` 알림(일별 멱등, `ref_date`).
- `parent_comment_id is not None` (답글):
  1. 부모 댓글 조회. 없으면 404(REQ-REPLY-003).
  2. 부모의 `share_id != share.id` 이면 거부(REQ-REPLY-004, 400/404).
  3. 부모의 `parent_comment_id is not None` 이면 거부(REQ-REPLY-005, 400/409) — 단일 단계 스레딩 강제.
  4. 답글 저장(`parent_comment_id` 세팅).
  5. 부모 댓글 작성자(`parent.user_id`)가 답글 작성자(`user_id`)와 다르면 부모 작성자에게 알림 생성(REQ-REPLY-008): `type="portfolio_comment"`, `krx_code=f"P{portfolio.id}"`, `ref_date=kst_today` — 기존 규약 재사용으로 SPEC-047 딥링크 자동 동작. 같은 사용자면 알림 없음(REQ-REPLY-009).
  6. 답글 경로에서는 소유자 별도 알림을 생성하지 않는다(§8 중복 알림 방지 제약) — 부모 작성자 알림만.
- 삭제(`remove_comment`): 최상위 댓글 삭제 시 self-FK CASCADE 로 답글이 함께 제거된다(REQ-REPLY-010). 기존 삭제 권한(작성자 OR 소유자)·404 동작은 SPEC-046 유지.
- 알림 UNIQUE 충돌은 기존과 동일하게 `IntegrityError` → `rollback`(일별 멱등).

### 5.3 중첩 조회 (`sharing.list_comments`, sync)

- `total`: `parent_comment_id.is_(None)` 인 최상위 댓글만 count(REQ-REPLY-007).
- 최상위 페이지 조회: 기존 정렬(최신순 `created_at DESC`) 유지 + `parent_comment_id.is_(None)` 필터 + offset/limit.
- 각 최상위 댓글 id 집합에 대해 **단일 배치 쿼리**로 답글 조회: `parent_comment_id.in_(top_ids)` + User join, `created_at ASC`(오래된순, REQ-REPLY-006). 파이썬에서 `parent_comment_id` 기준 그룹핑하여 각 최상위 항목의 `replies` 배열 구성. N+1 회피.
- 각 답글 항목은 `username`(작성자 표시명, REQ-REPLY-011)·`parent_comment_id` 포함.

### 5.4 엔드포인트·스키마

- `public_router.add_comment`: 요청 바디 `CommentCreate` 에 `parent_comment_id: int | None = None` 추가, `sharing.add_comment(..., parent_comment_id=payload.parent_comment_id)` 전달. 검증 실패는 서비스가 `HTTPException` 으로 변환(라우터에서 매핑).
- `CommentItem` 스키마: `parent_comment_id: int | None`·`replies: list["CommentItem"]` 추가(자기참조 모델 — `model_rebuild()` 필요 시 적용). 최상위 항목만 `replies` 를 채우고, 답글 항목의 `replies` 는 빈 배열.

### 5.5 프론트엔드 (`SharedPortfolio.tsx`, `feed.ts`)

- `feed.ts`: `postComment(token, content, parentCommentId?)` — body 에 `parent_comment_id` 포함(있을 때만). `CommentItem` 타입에 `parent_comment_id: number | null`·`replies: CommentItem[]` 추가.
- `SharedPortfolio.tsx`:
  - 각 최상위 댓글 렌더 시 "답글" 액션(버튼) 노출(REQ-REPLY-012). 클릭 시 해당 댓글 전용 답글 입력 폼 토글.
  - 답글 제출 시 `postComment(token, text, comment.id)` 호출(REQ-REPLY-013). 성공 시 로컬 상태의 해당 부모 `replies` 에 새 답글 append 하여 리로드 없이 표시(REQ-REPLY-015).
  - 각 최상위 댓글의 `replies` 를 부모 아래 들여쓰기하여 중첩 렌더(REQ-REPLY-014).
- 기존 최상위 댓글 입력·목록·삭제 UI 는 변경 최소화(답글 UI 추가만).

### 5.6 빌드 산출물 동기화 (.js/.ts 페어)

- 본 프로젝트는 `.tsx`/`.ts` 소스와 커밋된 `.js` 빌드 산출물을 **쌍으로** 유지한다. 수정한 모든 소스(`feed.ts`, `SharedPortfolio.tsx`)는 대응 `.js`(`feed.js`, `SharedPortfolio.js`)도 함께 갱신한다. 백엔드 Python 파일은 빌드 산출물 페어가 없다.

---

## 6. 테스트 목록 (Test Plan)

- 백엔드: `backend/tests/unit/test_comment_replies_048.py`(pytest, sync 픽스처 DB). 신규 외부 의존성 없음.
- 프론트엔드: `frontend/src/__tests__/comment_replies_048.test.tsx`(vitest + React Testing Library, `feed` API 모듈 모킹).

| ID | 테스트 | 검증 REQ / AC |
|----|--------|---------------|
| T-048-001 | 최상위 댓글에 대댓글 작성 → parent_comment_id 저장 확인 | REQ-REPLY-001·002 / AC-001 |
| T-048-002 | 존재하지 않는 parent_comment_id → 404 | REQ-REPLY-003 / AC-002 |
| T-048-003 | 다른 공유의 댓글을 부모로 지정 → 거부, 답글 미생성 | REQ-REPLY-004 / AC-003 |
| T-048-004 | 답글을 부모로 지정(2단계 시도) → 거부 | REQ-REPLY-005 / AC-004 |
| T-048-005 | 최상위 댓글 + 답글 2개 → replies 오래된순 반환 | REQ-REPLY-006·011 / AC-005 |
| T-048-006 | 최상위 1 + 답글 3 → total=1 (최상위만 카운트) | REQ-REPLY-007 / AC-006 |
| T-048-007 | 타인 댓글에 답글 → 부모 작성자에게 알림 생성 | REQ-REPLY-008 / AC-007 |
| T-048-008 | 자기 댓글에 답글 → 알림 미생성 | REQ-REPLY-009 / AC-008 |
| T-048-009 | 답글 있는 부모 삭제 → 답글 CASCADE 제거 | REQ-REPLY-010 / AC-009 |
| T-048-010 | 프론트 최상위 댓글 → 답글 액션 렌더 | REQ-REPLY-012 / AC-010 |
| T-048-011 | 프론트 답글 제출 → postComment(token, text, parentId) 호출 | REQ-REPLY-013 / AC-011 |
| T-048-012 | 프론트 replies 있는 댓글(신규 답글 포함) → 리로드 없이 중첩 렌더 | REQ-REPLY-014·015 / AC-012 |

품질 게이트: 백엔드 pytest 통과(커버리지 기준 충족), 프론트 vitest 통과, ESLint·ruff 통과, 신규 외부 의존성 0, **신규 테이블 0개(마이그레이션 0029 = 컬럼 1개 추가)**, `.js`/`.ts` 페어 동기화.

---

## 7. 의존성 (Dependencies)

- **SPEC-STOCK-046** (공유 포트폴리오 댓글): `PortfolioComment` 모델(`portfolio_comments` 테이블)·`sharing.add_comment`/`list_comments`/`remove_comment`·`CommentCreate`/`CommentItem` 스키마·public_router 댓글 엔드포인트 — 본 SPEC 의 확장 대상.
- **SPEC-STOCK-042** (포트폴리오 공유 & 소셜): `PortfolioShare`(`share_token`·`is_public`·`portfolio_id`)·`_get_public_share_or_404` — 공유 검증. App 라우트 `/shared/:shareToken`·`SharedPortfolio.tsx`.
- **SPEC-STOCK-047** (알림 딥링크): `inbox_router` 의 `portfolio_comment` 타입 딥링크 산출(`krx_code=f"P{id}"` → `/shared/{token}`) — 답글 알림이 동일 규약을 재사용하므로 **inbox_router 변경 없이** 딥링크 자동 적용.
- **SPEC-STOCK-013** (알림 인박스): `Notification` 모델(`type`·`krx_code`·`ref_date` 일별 멱등 UNIQUE) — 답글 알림 생성 대상.

---

## 8. 기술 제약 (Technical Constraints)

- **댓글 서비스는 sync(`Session`)** 이다(`sharing.add_comment`/`list_comments`/`remove_comment`). 대댓글 로직은 기존 sync 컨텍스트에서 구현하며, async 인박스 라우터를 호출하지 않는다(sync/async 혼용 금지).
- **1단계 스레딩 강제**: 부모는 반드시 최상위 댓글(`parent_comment_id IS NULL`)이어야 한다. 답글에 대한 답글은 서비스에서 거부한다(REQ-REPLY-005).
- **알림 규약 재사용**: 답글 알림은 신규 타입을 만들지 않고 `type="portfolio_comment"`·`krx_code=f"P{portfolio.id}"`·`ref_date` 를 재사용한다. 이로써 SPEC-047 딥링크가 자동 동작하고 inbox_router·프론트 배지 변경이 불필요하다. 부작용: 답글 알림도 "댓글" 배지로 표시된다(허용, §2.2).
- **중복 알림 방지**: 답글은 부모 댓글 작성자에게만 알림한다. 소유자에 대한 추가 알림을 생성하지 않는다(소유자가 부모 작성자인 경우는 자연히 1건). 최상위 댓글의 소유자 알림(SPEC-046)은 그대로 유지.
- **일별 멱등**: 알림 UNIQUE 제약 충돌 시 `IntegrityError` → `rollback`(기존 SPEC-043/046 패턴 준수). 같은 날 같은 대상·포트폴리오에 다수 답글이 달리면 알림은 1건으로 병합된다(허용).
- **CASCADE 삭제**: `parent_comment_id` self-FK 는 `ondelete=CASCADE` 이다. 최상위 댓글 삭제 시 그 답글이 함께 물리 삭제된다(placeholder 미표시).
- **N+1 회피**: 목록 조회 시 답글은 최상위 id 집합에 대해 **단일 배치 쿼리**로 조회 후 파이썬에서 그룹핑한다.
- **자기참조 Pydantic 모델**: `CommentItem.replies: list[CommentItem]` 는 전방참조이며 필요 시 `model_rebuild()` 를 적용한다. 답글 항목의 `replies` 는 항상 빈 배열(단일 단계).
- **하위 호환**: `CommentCreate.parent_comment_id` 는 선택적(기본 None)이며, 기존 최상위 댓글 작성 클라이언트는 변경 없이 동작한다. `parent_comment_id` 컬럼은 nullable 추가로 기존 행에 영향 없음.
- React + TypeScript(`.tsx`/`.ts`) 소스, Vite 빌드. 커밋된 `.js` 산출물과 페어 동기화 필수.
- ESLint·ruff 통과, 신규 외부 의존성 금지, 모든 신규 동작 단위 테스트 필수.
