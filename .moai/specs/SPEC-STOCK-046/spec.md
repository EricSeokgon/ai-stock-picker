---
id: SPEC-STOCK-046
title: 공유 포트폴리오 댓글 (Shared Portfolio Comments)
status: draft
version: 0.1.0
created: 2026-07-01
updated: 2026-07-01
author: ircp
priority: medium
issue_number: null
branch: feature/SPEC-STOCK-036
labels: [portfolio, sharing, social, comments, discovery]
---

# SPEC-STOCK-046 — 공유 포트폴리오 댓글 (Shared Portfolio Comments)

## HISTORY

| Version | Date | Author | Note |
|---------|------|--------|------|
| 0.1.0 | 2026-07-01 | ircp | 최초 초안 — 공개 공유 포트폴리오(`/shared/{token}`)에 댓글 기능 추가. 신규 테이블 `portfolio_comments`(마이그레이션 0028, down_rev=0027)·`PortfolioComment` 모델. 작성(POST, 인증)·목록(GET, 공개)·삭제(DELETE, 작성자 또는 소유자) 엔드포인트. 댓글 작성 시 소유자에게 `portfolio_comment` 인박스 알림(좋아요 패턴 재사용, 일별 멱등). SPEC-042/043 공유·알림 인프라 재사용. EARS REQ 21개(REQ-COMMENT-001~021)·AC 18개·테스트 18개 |

---

## 1. 개요 (Overview)

SPEC-STOCK-042 가 공개 포트폴리오 공유(`/shared/{token}`)·좋아요·디스커버리 피드를 도입했고, SPEC-043~045 가 좋아요 알림·조회수 통계·트렌딩/검색을 추가하여 소셜 디스커버리 아크를 구축했다. 그러나 현재 공유 포트폴리오에 대한 상호작용은 **좋아요(단일 비트)** 뿐이며, 다른 사용자의 포트폴리오 구성에 대한 **의견·피드백을 남길 수단이 없다**. 본 SPEC 은 공유 포트폴리오에 **댓글(comment)** 기능을 추가하여 소셜 상호작용을 텍스트 수준으로 확장한다.

- **댓글 작성 (`POST /shared/{token}/comments`, 인증 필수)**: 로그인한 사용자가 공개 공유 포트폴리오에 텍스트 댓글(최대 500자)을 남긴다. 작성 시 소유자에게 `portfolio_comment` 인박스 알림을 생성한다(좋아요 알림과 동일 패턴·일별 멱등).
- **댓글 목록 (`GET /shared/{token}/comments`, 무인증)**: 공개 공유 포트폴리오의 댓글을 최신순으로 조회한다. 각 댓글은 작성자 username·내용·작성시각을 포함하며 페이지네이션을 지원한다.
- **댓글 삭제 (`DELETE /shared/{token}/comments/{comment_id}`, 인증 필수)**: 댓글 작성자 본인 또는 포트폴리오 소유자(모더레이션)가 댓글을 삭제한다.
- **SharedPortfolio 페이지 UI**: 공개 공유 뷰에 댓글 목록과 작성 폼(로그인 시)을 추가하고, 본인 댓글에 삭제 컨트롤을 노출한다.
- **알림 인박스**: `portfolio_comment` 타입 알림에 "댓글" 배지를 추가한다.

본 SPEC 은 SPEC-042/043 의 공유(`PortfolioShare`)·알림(`Notification`) 인프라를 재사용한다. 좋아요 테이블(`portfolio_likes`)과 동일하게 `share_id` 외래키 구조를 따른다.

### 1.1 동기 (Why)

좋아요는 단순 호감 표시일 뿐 **왜 그 포트폴리오가 좋은지/어떤 점이 우려되는지**를 전달하지 못한다. 한국 개인 투자자는 종목 선정·비중에 대한 동료 피드백에서 큰 가치를 얻으며, 댓글은 디스커버리 피드(SPEC-045)에서 발견한 포트폴리오에 대한 토론을 가능하게 하여 소셜 아크를 완성한다. 댓글 작성 알림은 이미 구축된 인박스(SPEC-013/043)를 재사용하여 추가 채널 비용 없이 소유자 참여를 유도한다.

---

## 2. 범위 (Scope)

### 2.1 In-Scope

- **신규 테이블·모델**: `backend/alembic/versions/0028_portfolio_comments_046.py`(down_rev=0027) — `portfolio_comments` 테이블 생성. `backend/src/stock_picker/db/models.py` — `PortfolioComment` 모델 추가, `PortfolioShare` 에 `comments` 관계 추가.
- **서비스 로직**: `backend/src/stock_picker/portfolio/sharing.py` — `add_comment`, `list_comments`, `remove_comment` 함수 추가(좋아요 함수 형제). 댓글 작성 시 `portfolio_comment` 알림 생성(`add_like` 의 알림 패턴 재사용).
- **라우터**: `backend/src/stock_picker/portfolio/public_router.py` — 공개 목록 `GET /shared/{token}/comments`(인증 불필요), 인증 `POST /shared/{token}/comments`·`DELETE /shared/{token}/comments/{comment_id}` 추가.
- **스키마**: `backend/src/stock_picker/portfolio/schemas.py` — `CommentCreate`, `CommentItem`, `CommentListResponse` 추가.
- **프론트엔드 API**: `frontend/src/api/feed.ts`(+빌드 산출물 `feed.js`) — `getComments(token, page?, size?)`, `addComment(token, content)`, `deleteComment(token, commentId)` 추가.
- **프론트엔드 UI**: `frontend/src/pages/SharedPortfolio.tsx`(+`SharedPortfolio.js`) — 댓글 목록·작성 폼·본인 댓글 삭제 컨트롤. `frontend/src/pages/Notifications.tsx`(+`Notifications.js`) — `portfolio_comment` 배지 "댓글".
- **백엔드 단위 테스트**: `backend/tests/unit/test_comments_046.py`(pytest).
- **프론트엔드 단위 테스트**: `frontend/src/__tests__/comments_046.test.tsx`(vitest + React Testing Library).

### 2.2 Out-of-Scope (제외)

> [HARD] 본 SPEC 은 아래 항목을 명시적으로 제외한다.

- **자동 매매·자동 주문 실행** (규제·책임 리스크로 프로젝트 영구 제외).
- **댓글 대댓글(스레드)·답글·멘션** — 단일 레벨 플랫 댓글만 지원. 부모-자식 구조 없음.
- **댓글 좋아요·반응(이모지)** — 댓글에 대한 별도 상호작용 없음.
- **댓글 수정(PUT/PATCH)** — 작성 후 수정 불가, 삭제 후 재작성만.
- **댓글 신고·차단·욕설 필터·스팸 방지(rate limit)** — 모더레이션은 소유자·작성자 삭제만 제공.
- **댓글 알림 딥링크** — 알림 클릭 시 해당 공유 포트폴리오로 이동하는 라우팅은 후속 과제로 이연(좋아요 알림 딥링크와 함께).
- **이메일·텔레그램 댓글 알림** — 인박스 알림만 생성(SPEC-025 채널 설정 게이트 대상 아님).
- **댓글 수 피드 노출** — 디스커버리 피드(`/feed`) 항목에 comment_count 추가는 제외(좋아요·조회수만 유지).
- **마크다운·리치 텍스트·이미지 첨부** — 평문(plain text)만.
- **댓글 페이지네이션 무한 스크롤·실시간 갱신(WebSocket)·폴링** — 페이지 단위 조회만.
- **공개 뷰 비로그인 사용자의 본인 댓글 식별 영속화** — 삭제 컨트롤은 현재 로그인 사용자 기준만(SPEC-044 의 무인증 공개뷰 패턴 일관).

---

## 3. 요구사항 (Requirements — EARS)

> REQ 번호는 댓글 도메인 신규 접두사 `REQ-COMMENT-` 로 001 부터 부여한다(좋아요=REQ-LIKE, 피드=REQ-FEED 와 충돌 회피). 모든 REQ 는 관찰 가능한 동작을 단일 SHALL 로 기술한다.

### 3.1 댓글 작성 (REQ-COMMENT-001 ~ 005)

- **REQ-COMMENT-001**: When an authenticated user submits a non-empty comment on a public shared portfolio, the system SHALL persist the comment linked to that portfolio's share and the submitting user.
- **REQ-COMMENT-002**: If a comment is submitted with content that is empty or whitespace-only, then the system SHALL reject the request with a 422 status and SHALL NOT persist any comment.
- **REQ-COMMENT-003**: If a comment is submitted with content longer than 500 characters, then the system SHALL reject the request with a 422 status.
- **REQ-COMMENT-004**: If a comment is submitted for a share token that is not public or does not exist, then the system SHALL respond with a 404 status.
- **REQ-COMMENT-005**: If an unauthenticated client attempts to create a comment, then the system SHALL respond with a 401 status.

### 3.2 댓글 목록 (REQ-COMMENT-006 ~ 009)

- **REQ-COMMENT-006**: When a client requests the comments of a public shared portfolio, the system SHALL return each comment with its author's username, content, and creation timestamp.
- **REQ-COMMENT-007**: When the system returns a comment list, it SHALL order the comments by creation time in descending order (newest first).
- **REQ-COMMENT-008**: If comments are requested for a share token that is not public or does not exist, then the system SHALL respond with a 404 status.
- **REQ-COMMENT-009**: When pagination parameters are provided for a comment list request, the system SHALL limit the returned comments to the requested page and size and SHALL include the total comment count.

### 3.3 댓글 삭제 (REQ-COMMENT-010 ~ 013)

- **REQ-COMMENT-010**: When the comment author requests deletion of their own comment, the system SHALL delete the comment and respond with a 204 status.
- **REQ-COMMENT-011**: When the portfolio owner requests deletion of a comment on their own shared portfolio, the system SHALL delete the comment and respond with a 204 status.
- **REQ-COMMENT-012**: If a user who is neither the comment author nor the portfolio owner requests deletion of a comment, then the system SHALL respond with a 403 status and SHALL NOT delete the comment.
- **REQ-COMMENT-013**: If a deletion targets a comment that does not exist under the given share, then the system SHALL respond with a 404 status.

### 3.4 댓글 알림 (REQ-COMMENT-014 ~ 016)

- **REQ-COMMENT-014**: When a user other than the portfolio owner creates a comment, the system SHALL create an in-app notification of type `portfolio_comment` for the portfolio owner.
- **REQ-COMMENT-015**: If the commenter is the portfolio owner, then the system SHALL NOT create a comment notification.
- **REQ-COMMENT-016**: When a second comment notification would be created for the same owner, portfolio, and calendar day, the system SHALL suppress the duplicate so that at most one such notification exists per day.

### 3.5 프론트엔드 (REQ-COMMENT-017 ~ 021)

- **REQ-COMMENT-017**: When an authenticated user submits the comment form on the shared portfolio page, the page SHALL send the entered content to the create-comment endpoint and SHALL display the created comment in the list.
- **REQ-COMMENT-018**: When the shared portfolio page loads, the page SHALL request and render the existing comments for that portfolio.
- **REQ-COMMENT-019**: Where a rendered comment was authored by the current logged-in user, the page SHALL display a delete control for that comment.
- **REQ-COMMENT-020**: If the comment input is empty or whitespace-only, then the page SHALL NOT issue a create-comment request.
- **REQ-COMMENT-021**: When a `portfolio_comment` notification is rendered in the inbox, the page SHALL display a "댓글" badge for it.

---

## 4. 인수 조건 (Acceptance Criteria — EARS)

> 모든 AC 는 EARS(Event-driven / Unwanted behavior) 형식으로 작성하며, 각 AC 는 단일 관찰 가능 동작(단일 SHALL)만 검증한다. 총 18개.

### AC-046-001 — 인증 사용자 댓글 작성 영속화 (REQ-COMMENT-001)

When an authenticated user posts the comment "좋은 구성이네요" to a public shared portfolio,
the system shall store a comment record linked to that share and that user.

### AC-046-002 — 빈 내용 거부 (REQ-COMMENT-002)

If a comment is posted with content consisting only of whitespace,
then the system shall respond with status 422 and store no comment.

### AC-046-003 — 500자 초과 거부 (REQ-COMMENT-003)

If a comment is posted with 501 characters of content,
then the system shall respond with status 422.

### AC-046-004 — 비공개 토큰 작성 404 (REQ-COMMENT-004)

If a comment is posted to a share token whose share is not public,
then the system shall respond with status 404.

### AC-046-005 — 미인증 작성 401 (REQ-COMMENT-005)

If an unauthenticated client posts a comment,
then the system shall respond with status 401.

### AC-046-006 — 목록 작성자·내용·시각 반환 (REQ-COMMENT-006)

When the comments of a public shared portfolio are requested,
the system shall return each comment including the author username, the content, and the creation timestamp.

### AC-046-007 — 최신순 정렬 (REQ-COMMENT-007)

When two comments were created at different times and the comment list is requested,
the system shall place the more recently created comment before the older one.

### AC-046-008 — 비공개 목록 404 (REQ-COMMENT-008)

If the comments are requested for a non-public share token,
then the system shall respond with status 404.

### AC-046-009 — 페이지네이션 total·size (REQ-COMMENT-009)

When a public shared portfolio has 5 comments and the list is requested with size 2 on page 1,
the system shall return at most 2 comments and a total of 5.

### AC-046-010 — 작성자 본인 삭제 204 (REQ-COMMENT-010)

When the author requests deletion of their own comment,
the system shall delete the comment and respond with status 204.

### AC-046-011 — 소유자 모더레이션 삭제 204 (REQ-COMMENT-011)

When the portfolio owner requests deletion of another user's comment on their shared portfolio,
the system shall delete the comment and respond with status 204.

### AC-046-012 — 제3자 삭제 403 (REQ-COMMENT-012)

If a user who is neither the comment author nor the portfolio owner requests deletion of a comment,
then the system shall respond with status 403 and leave the comment in place.

### AC-046-013 — 존재하지 않는 댓글 삭제 404 (REQ-COMMENT-013)

If a deletion targets a comment id that does not exist under the given share,
then the system shall respond with status 404.

### AC-046-014 — 비소유자 댓글 → 소유자 알림 (REQ-COMMENT-014)

When a non-owner user comments on a shared portfolio,
the system shall create a `portfolio_comment` notification addressed to the portfolio owner.

### AC-046-015 — 소유자 자기댓글 알림 없음 (REQ-COMMENT-015)

If the portfolio owner comments on their own shared portfolio,
then the system shall create no comment notification.

### AC-046-016 — 동일일 중복 알림 억제 (REQ-COMMENT-016)

When two different users comment on the same shared portfolio on the same day,
the system shall keep at most one `portfolio_comment` notification for the owner for that day.

### AC-046-017 — 프론트 작성 제출 → 요청·렌더 (REQ-COMMENT-017)

When the user submits the comment form with content "추천합니다" on the shared portfolio page,
the page shall issue a create-comment request carrying that content.

### AC-046-018 — 프론트 빈 입력 미요청 (REQ-COMMENT-020)

If the comment input is empty when the user submits the form,
then the page shall not issue a create-comment request.

> AC-046-018 은 REQ-COMMENT-018(목록 로드 렌더)·REQ-COMMENT-019(본인 삭제 컨트롤)·REQ-COMMENT-021(배지)와 함께 §6 테스트(T-046-016~018)로 커버된다.

---

## 5. 기술 설계 (Technical Approach)

### 5.1 신규 테이블·모델 (db/models.py, 마이그레이션 0028)

- 테이블 `portfolio_comments`(마이그레이션 `0028_portfolio_comments_046.py`, down_rev=`0027`):
  - `id` Integer PK autoincrement
  - `share_id` Integer FK `portfolio_shares.id` ondelete CASCADE, nullable=False — **좋아요(`portfolio_likes`)와 동일하게 `portfolio_id` 가 아닌 `share_id` 참조**(공유 비활성화·삭제 시 댓글도 정리, 무공유 포트폴리오엔 댓글 불가).
  - `user_id` Integer FK `users.id` ondelete CASCADE, nullable=False
  - `content` String(500) nullable=False — 평문 댓글, 서버측 trim 후 비어있지 않음.
  - `created_at` TIMESTAMPTZ server_default `func.now()`, nullable=False
- 인덱스: `(share_id, created_at)` — 최신순 목록 조회 최적화.
- UNIQUE 제약 없음(동일 사용자 다중 댓글 허용). 좋아요와 달리 멱등성 불필요.
- `PortfolioComment` 모델 추가(좋아요 모델 형제). `PortfolioShare` 에 `comments` 관계 추가(`lazy="noload"`, back_populates).

### 5.2 서비스 로직 (portfolio/sharing.py)

- `add_comment(db, share_token, user_id, content) -> dict`:
  - 공유 조회(좋아요와 동일: `share_token` + `is_public.is_(True)`, 없으면 404 — REQ-COMMENT-004).
  - `content.strip()` 비어있으면 호출 이전 스키마 검증에서 422 처리(REQ-COMMENT-002). 길이>500 도 스키마에서 422(REQ-COMMENT-003).
  - `PortfolioComment(share_id=share.id, user_id=user_id, content=content.strip())` INSERT.
  - 소유자(`portfolio.user_id`)와 작성자가 다르면 `portfolio_comment` 알림 생성 — `add_like` 의 알림 패턴 재사용: `Notification(user_id=portfolio.user_id, type="portfolio_comment", krx_code=f"P{portfolio.id}", title=f"{commenter_name}님이 댓글을 남겼습니다", body=None, is_read=False, ref_date=kst_today)`, `UNIQUE(user_id, type, krx_code, ref_date)` 충돌 시 `IntegrityError` rollback(일별 멱등 — REQ-COMMENT-014/016). 작성자==소유자면 알림 미생성(REQ-COMMENT-015).
  - 반환: 생성된 댓글 dict(id·username·content·created_at).
- `list_comments(db, share_token, page=1, size=20) -> dict`:
  - 공유 조회(비공개/미존재 → 404, REQ-COMMENT-008).
  - `PortfolioComment` ⨝ `User` 조인, `created_at.desc()` 정렬(REQ-COMMENT-007), `size = min(size, 100)` 캡, offset 페이지네이션(REQ-COMMENT-009). `total = base_query.count()`.
  - 각 항목: `{id, user_id, username, content, created_at}`(REQ-COMMENT-006).
- `remove_comment(db, share_token, comment_id, user_id) -> None`:
  - 공유 조회(미존재/비공개 → 404).
  - 댓글 조회(`id==comment_id` AND `share_id==share.id`); 없으면 404(REQ-COMMENT-013).
  - 권한: 작성자(`comment.user_id==user_id`) 또는 소유자(`portfolio.user_id==user_id`) → 삭제 후 204(REQ-COMMENT-010/011). 둘 다 아니면 403(REQ-COMMENT-012).

### 5.3 라우터 (portfolio/public_router.py)

- `GET /shared/{token}/comments`(`shared_router`, 인증 불필요): `list_comments` 호출, `CommentListResponse` 반환. `page`/`size` Query(기존 피드 패턴).
- `POST /shared/{token}/comments`(`comment_router` 신규 또는 `like_router` 재사용, 인증 필요 `get_current_user`): `CommentCreate` 바디, `add_comment` 호출, 201 또는 200 + `CommentItem` 반환.
- `DELETE /shared/{token}/comments/{comment_id}`(인증 필요): `remove_comment` 호출, 204.
- 신규 인증 라우터가 필요하면 `comment_router = APIRouter(tags=["sharing"])` 추가 후 `main.py` 에 `include_router(comment_router)` 등록(기존 `shared_router`/`like_router` 등록 패턴, prefix 없음).

### 5.4 스키마 (portfolio/schemas.py)

- `CommentCreate`: `content: str` — Pydantic `Field(min_length=1, max_length=500)` + `str_strip_whitespace`(공백만 입력 시 빈 문자열→min_length 위반→422, REQ-COMMENT-002/003).
- `CommentItem`: `id`, `user_id`, `username`, `content`, `created_at`.
- `CommentListResponse`: `items: list[CommentItem]`, `total: int`, `page: int`, `size: int`.

### 5.5 프론트엔드 API (api/feed.ts)

- `getComments(token, page=1, size=20)` → `GET /shared/{token}/comments`.
- `addComment(token, content)` → `POST /shared/{token}/comments`(인증 토큰 첨부).
- `deleteComment(token, commentId)` → `DELETE /shared/{token}/comments/{commentId}`.

### 5.6 SharedPortfolio 페이지 (pages/SharedPortfolio.tsx)

- 마운트 시 `getComments` 호출, 댓글 목록 렌더(REQ-COMMENT-018).
- 로그인 사용자에게 댓글 입력 폼 표시. 제출 시 입력값 trim 비어있지 않으면 `addComment` 후 목록 갱신(REQ-COMMENT-017); 비어있으면 미요청(REQ-COMMENT-020).
- 각 댓글에 작성자 username·내용·시각 표시. `comment.user_id === currentUser.id` 일 때 삭제 버튼 노출(REQ-COMMENT-019), 클릭 시 `deleteComment` 후 목록 갱신.
- 비로그인 시 작성 폼·삭제 컨트롤 미표시(목록은 조회 가능). SPEC-044 무인증 공개뷰 패턴 일관.

### 5.7 알림 배지 (pages/Notifications.tsx)

- `TypeBadge` 의 라벨 맵에 `portfolio_comment: '댓글'`, 색상 맵에 `portfolio_comment: 'bg-blue-100 text-blue-800'`(좋아요 분홍과 구분) 추가(REQ-COMMENT-021).

### 5.8 빌드 산출물 동기화 (.js/.ts 페어)

- 본 프로젝트는 `.tsx`/`.ts` 소스와 커밋된 `.js` 빌드 산출물을 **쌍으로** 유지한다. 수정한 모든 소스(`feed.ts`, `SharedPortfolio.tsx`, `Notifications.tsx`)는 대응 `.js`(`feed.js`, `SharedPortfolio.js`, `Notifications.js`)도 함께 갱신해야 한다. 백엔드 Python 파일은 빌드 산출물 페어가 없다.

---

## 6. 테스트 목록 (Test Plan)

- 백엔드: `backend/tests/unit/test_comments_046.py`(pytest, 픽스처 DB). 신규 외부 의존성 없음.
- 프론트엔드: `frontend/src/__tests__/comments_046.test.tsx`(vitest + React Testing Library, API 모듈 모킹).

| ID | 테스트 | 검증 REQ / AC |
|----|--------|---------------|
| T-046-001 | 인증 사용자 댓글 작성 → DB 영속화 | REQ-COMMENT-001 / AC-001 |
| T-046-002 | 공백만 내용 → 422, 미저장 | REQ-COMMENT-002 / AC-002 |
| T-046-003 | 501자 내용 → 422 | REQ-COMMENT-003 / AC-003 |
| T-046-004 | 비공개 토큰 작성 → 404 | REQ-COMMENT-004 / AC-004 |
| T-046-005 | 미인증 작성 → 401 | REQ-COMMENT-005 / AC-005 |
| T-046-006 | 목록: username·content·created_at 반환 | REQ-COMMENT-006 / AC-006 |
| T-046-007 | 목록: 최신순 정렬 | REQ-COMMENT-007 / AC-007 |
| T-046-008 | 비공개 토큰 목록 → 404 | REQ-COMMENT-008 / AC-008 |
| T-046-009 | 페이지네이션: size 캡·total 정확 | REQ-COMMENT-009 / AC-009 |
| T-046-010 | 작성자 본인 삭제 → 204 | REQ-COMMENT-010 / AC-010 |
| T-046-011 | 소유자 모더레이션 삭제 → 204 | REQ-COMMENT-011 / AC-011 |
| T-046-012 | 제3자 삭제 → 403, 미삭제 | REQ-COMMENT-012 / AC-012 |
| T-046-013 | 존재하지 않는 댓글 삭제 → 404 | REQ-COMMENT-013 / AC-013 |
| T-046-014 | 비소유자 댓글 → portfolio_comment 알림 생성 | REQ-COMMENT-014 / AC-014 |
| T-046-015 | 소유자 자기댓글 → 알림 미생성 + 동일일 중복 억제 | REQ-COMMENT-015·016 / AC-015·016 |
| T-046-016 | 프론트 작성 제출 → addComment(content) 요청 | REQ-COMMENT-017 / AC-017 |
| T-046-017 | 프론트 빈 입력 → 요청 없음 + 마운트 목록 렌더 | REQ-COMMENT-018·020 / AC-018 |
| T-046-018 | 프론트 본인 댓글 삭제 컨트롤 노출 + portfolio_comment 배지 "댓글" | REQ-COMMENT-019·021 / — |

품질 게이트: 백엔드 pytest 통과(커버리지 기준 충족), 프론트 vitest 통과, ESLint·ruff 통과, 신규 외부 의존성 0, 신규 마이그레이션 1개(0028, down_rev=0027), `.js`/`.ts` 페어 동기화.

---

## 7. 의존성 (Dependencies)

- **SPEC-STOCK-042** (포트폴리오 공유 & 소셜): `PortfolioShare`(share_token·is_public)·`PortfolioLike`(share_id FK 패턴)·`public_router.py`(`shared_router`/`like_router` 등록)·`SharedPortfolio.tsx`·`feed.ts` — 본 SPEC 의 확장·재사용 대상.
- **SPEC-STOCK-043** (공유 통계 & 좋아요 알림): `add_like` 의 `Notification` 생성 패턴(`krx_code=f"P{id}"`, `UNIQUE(user_id,type,krx_code,ref_date)` 일별 멱등) — 댓글 알림 산출에 재사용.
- **SPEC-STOCK-013** (알림 인박스): `Notification` 모델·인박스 라우터·`Notifications.tsx` `TypeBadge` — `portfolio_comment` 타입·배지 추가 대상.
- **SPEC-STOCK-044** (소셜 프론트엔드): 무인증 공개뷰에서 현재 로그인 사용자 식별 패턴 — 삭제 컨트롤 노출 기준.

---

## 8. 기술 제약 (Technical Constraints)

- FastAPI + SQLAlchemy(동기 Session) 기존 패턴 준수. 공유 라우터(`public_router.py`)는 동기 `get_db_session`·`get_current_user` 의존성 사용.
- `portfolio_comments.share_id` 는 `portfolio_likes` 와 동일하게 `portfolio_shares.id` 를 참조한다(좋아요와 일관, `portfolio_id` 직접 참조 금지).
- 댓글 알림 `krx_code` 는 좋아요와 동일한 `f"P{portfolio.id}"` 규약을 따른다(`Notification.krx_code` String(10) 한도 내, 종목 코드와 충돌 회피). 좋아요(`portfolio_like`)와 댓글(`portfolio_comment`)은 type 이 달라 `UNIQUE(user_id,type,krx_code,ref_date)` 충돌 없이 공존한다.
- 댓글 내용은 평문 String(500); 서버측 trim + Pydantic `min_length=1, max_length=500` 검증으로 422 보장.
- `GET /shared/{token}/comments` 는 무인증 공용; `POST`/`DELETE` 는 `get_current_user` 보호.
- React + TypeScript(`.tsx`/`.ts`) 소스, Vite 빌드. 커밋된 `.js` 산출물과 페어 동기화 필수.
- ESLint·ruff 통과, 신규 외부 의존성 금지, 모든 신규 동작 단위 테스트 필수.
