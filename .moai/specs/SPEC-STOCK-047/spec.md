---
id: SPEC-STOCK-047
title: 공유 포트폴리오 알림 딥링크 (Shared Portfolio Notification Deep-Link)
status: draft
version: 0.1.0
created: 2026-07-01
updated: 2026-07-01
author: ircp
priority: medium
issue_number: null
branch: feature/SPEC-STOCK-036
labels: [portfolio, sharing, social, notifications, deep-link, discovery]
---

# SPEC-STOCK-047 — 공유 포트폴리오 알림 딥링크 (Shared Portfolio Notification Deep-Link)

## HISTORY

| Version | Date | Author | Note |
|---------|------|--------|------|
| 0.1.0 | 2026-07-01 | ircp | 최초 초안 — 인박스의 `portfolio_like`(043)·`portfolio_comment`(046) 알림에 딥링크를 추가하여 클릭 시 해당 공유 포트폴리오(`/shared/{share_token}`)로 이동. **신규 테이블·마이그레이션 없음** — 기존 `Notification.krx_code=f"P{portfolio.id}"` 규약과 활성 공개 공유(`PortfolioShare.is_public=True`)를 조인해 링크를 산출. 알림 목록 응답 스키마에 nullable `link` 필드 추가(백엔드 async 인박스 라우터). 프론트 `Notifications.tsx`에서 링크 있는 알림을 클릭 가능 요소로 렌더·읽음처리 후 이동. SPEC-046 §2.2에서 명시적으로 이연했던 후속 과제. EARS REQ 11개(REQ-NLINK-001~011)·AC 10개·테스트 10개 |

---

## 1. 개요 (Overview)

SPEC-STOCK-042~046 이 공개 포트폴리오 공유·좋아요·댓글·조회통계·트렌딩 피드로 소셜 디스커버리 아크를 구축했다. 이 과정에서 좋아요(SPEC-043)와 댓글(SPEC-046)은 포트폴리오 소유자에게 인박스 알림(`portfolio_like`·`portfolio_comment`)을 생성한다. 그러나 현재 이 알림들은 **클릭해도 아무 데도 이동하지 않는다** — 사용자는 "누가 내 포트폴리오에 좋아요/댓글을 남겼다"는 사실만 알 뿐, **어느 포트폴리오인지 확인하러 가려면 직접 찾아가야** 한다. 본 SPEC 은 이 알림들에 **딥링크(deep-link)** 를 부여하여, 클릭 시 해당 공유 포트폴리오 페이지(`/shared/{share_token}`)로 바로 이동하게 한다.

- **백엔드 링크 산출 (인박스 목록·단건 응답)**: 알림 응답에 nullable `link` 필드를 추가한다. 알림 타입이 `portfolio_like` 또는 `portfolio_comment` 이고, 그 알림이 가리키는 포트폴리오(krx_code `P{id}` 규약)에 **활성 공개 공유가 존재**하면 `link = "/shared/{share_token}"` 를 채운다. 그 외(일반 알림, 비공개/삭제된 공유, 규약 불일치)는 `link = null`.
- **프론트엔드 (`Notifications.tsx`)**: `link` 가 있는 알림을 클릭 가능한 요소로 렌더한다. 클릭 시 해당 알림을 읽음 처리한 뒤 `link` 경로로 이동한다. `link` 가 없는 알림은 기존처럼 비상호작용(non-clickable)으로 렌더한다.

본 SPEC 은 **신규 테이블·마이그레이션·외부 의존성이 전혀 없다**. 기존 `Notification`(SPEC-013)·`PortfolioShare`(SPEC-042) 인프라만 조인·재사용한다.

### 1.1 동기 (Why)

알림의 가치는 "행동 유도(call-to-action)"에 있다. 좋아요·댓글 알림을 받고도 대상 포트폴리오로 한 번에 갈 수 없으면 참여 마찰이 커진다. 딥링크는 이미 구축된 공유 라우트(`/shared/:shareToken`, SPEC-042/044)와 알림 인박스(SPEC-013)를 잇는 **마지막 연결 고리**로, 소유자가 자신의 공유 포트폴리오에 달린 반응을 즉시 확인하고 (댓글에 답 댓글을 남기는 등) 소셜 루프를 완성하게 한다. 추가 저장소나 스키마 변경 없이 순수 조회 조인만으로 구현되므로 비용 대비 사용자 가치가 높다.

---

## 2. 범위 (Scope)

### 2.1 In-Scope

- **알림 스키마 확장**: `backend/src/stock_picker/notifications/inbox_router.py` — `NotificationSchema` 에 `link: str | None = None` 필드 추가.
- **링크 산출 로직**: `inbox_router.py` — 목록(`get_notifications`)·단건 읽음(`mark_as_read`) 응답 생성 시 `portfolio_like`·`portfolio_comment` 알림의 krx_code(`P{id}`)를 파싱하여 활성 공개 `PortfolioShare` 를 조회, `link="/shared/{share_token}"` 산출. 목록은 **단일 배치 쿼리**로 페이지 내 모든 포트폴리오 공유를 한 번에 조회(N+1 회피).
- **프론트엔드 타입**: `frontend/src/api/notifications.ts`(+빌드 산출물 `notifications.js`) — `Notification` 인터페이스에 `link: string | null` 추가.
- **프론트엔드 UI**: `frontend/src/pages/Notifications.tsx`(+`Notifications.js`) — `link` 있는 알림을 클릭 가능 요소(버튼/링크)로 렌더, 클릭 시 읽음 처리 후 `useNavigate` 로 `link` 이동. `link` 없으면 비상호작용.
- **백엔드 단위 테스트**: `backend/tests/unit/test_notification_links_047.py`(pytest, async).
- **프론트엔드 단위 테스트**: `frontend/src/__tests__/notification_links_047.test.tsx`(vitest + React Testing Library, API·라우터 모킹).

### 2.2 Out-of-Scope (제외)

> [HARD] 본 SPEC 은 아래 항목을 명시적으로 제외한다.

- **자동 매매·자동 주문 실행** (규제·책임 리스크로 프로젝트 영구 제외).
- **신규 테이블·DB 마이그레이션** — 본 SPEC 은 조회 조인만 사용하며 스키마를 변경하지 않는다(최신 마이그레이션은 0028 유지).
- **일반 알림(`price_alert`·`rec_new`·`rec_dropped`) 딥링크** — 종목 상세로의 라우팅은 본 SPEC 대상 아님. 해당 타입은 `link=null`.
- **알림 저장 시점 링크 영속화** — `link` 는 응답 시점에 동적 산출하며 `notifications` 테이블에 컬럼을 추가하지 않는다(공유 상태가 변하면 링크 유효성도 자동 반영).
- **읽지 않은 알림 개수(`/unread-count`)·전체 읽음(`/read-all`) 응답의 링크** — 개수/일괄 처리 응답은 개별 알림 링크를 포함하지 않는다.
- **공유 토큰이 없는 포트폴리오에 대한 공유 생성** — 링크는 오직 활성 공개 공유가 이미 존재할 때만 산출한다(없으면 null).
- **딥링크 클릭 통계·추적(analytics)** — 클릭 수 집계는 제외.
- **이메일·텔레그램 알림 본문 딥링크** — 인앱 인박스 응답의 `link` 필드만 대상(외부 채널 템플릿 변경 없음).
- **댓글 알림에서 특정 댓글로의 앵커 스크롤·하이라이트** — 공유 포트폴리오 페이지 상단으로만 이동(댓글 섹션 앵커·스크롤 없음).
- **알림 목록의 서버측 페이지네이션 변경** — 기존 `limit` 파라미터 동작 유지.

---

## 3. 요구사항 (Requirements — EARS)

> REQ 번호는 알림 딥링크 도메인 신규 접두사 `REQ-NLINK-` 로 001 부터 부여한다(알림 인박스 `REQ-NOTI`·좋아요 `REQ-LIKE`·댓글 `REQ-COMMENT`·피드 `REQ-FEED` 와 충돌 회피). 모든 REQ 는 관찰 가능한 동작을 단일 SHALL 로 기술한다.

### 3.1 백엔드 링크 산출 (REQ-NLINK-001 ~ 007)

- **REQ-NLINK-001**: When the notification list is returned and a notification of type `portfolio_like` or `portfolio_comment` references a portfolio that has an active public share, the system SHALL include in that notification a link to the shared portfolio.
- **REQ-NLINK-002**: When the system builds the link for a portfolio notification, the system SHALL derive the link as the path `/shared/{share_token}` using the portfolio's active public share token.
- **REQ-NLINK-003**: If a notification's type is neither `portfolio_like` nor `portfolio_comment`, then the system SHALL return a null link for that notification.
- **REQ-NLINK-004**: If a portfolio notification references a portfolio whose share is not public or no longer exists, then the system SHALL return a null link for that notification.
- **REQ-NLINK-005**: If a portfolio notification's krx_code does not match the `P{portfolioId}` pattern, then the system SHALL return a null link for that notification.
- **REQ-NLINK-006**: When a single notification is returned by the mark-as-read response, the system SHALL include the same resolved link that the list response would provide for that notification.
- **REQ-NLINK-007**: When a notification list contains multiple portfolio notifications referencing different portfolios, the system SHALL return each notification's own correct link.

### 3.2 프론트엔드 (REQ-NLINK-008 ~ 011)

- **REQ-NLINK-008**: Where a rendered notification has a non-null link, the page SHALL render that notification as an activatable (clickable) element.
- **REQ-NLINK-009**: When the user activates a notification that has a link, the page SHALL navigate to that notification's link path.
- **REQ-NLINK-010**: Where a rendered notification has a null link, the page SHALL NOT render a navigation control for that notification.
- **REQ-NLINK-011**: When the user activates a linked notification that is currently unread, the page SHALL mark that notification as read before or while navigating.

---

## 4. 인수 조건 (Acceptance Criteria — EARS)

> 모든 AC 는 EARS(Event-driven / State-driven / Unwanted behavior) 형식으로 작성하며, 각 AC 는 단일 관찰 가능 동작(단일 SHALL)만 검증한다. 총 10개.

### AC-047-001 — 댓글 알림 딥링크 산출 (REQ-NLINK-001·002)

When the notification list is requested and it contains a `portfolio_comment` notification whose portfolio has an active public share with token `abc123`,
the system shall return that notification with link `/shared/abc123`.

### AC-047-002 — 좋아요 알림 딥링크 산출 (REQ-NLINK-001)

When the notification list is requested and it contains a `portfolio_like` notification whose portfolio has an active public share,
the system shall return that notification with a non-null link.

### AC-047-003 — 일반 알림 링크 없음 (REQ-NLINK-003)

If the notification list contains a `price_alert` notification,
then the system shall return that notification with a null link.

### AC-047-004 — 비공개 공유 링크 없음 (REQ-NLINK-004)

If a `portfolio_like` notification references a portfolio whose share has been made private,
then the system shall return that notification with a null link.

### AC-047-005 — 규약 불일치 krx_code 링크 없음 (REQ-NLINK-005)

If a `portfolio_comment` notification has a krx_code that does not match the `P{portfolioId}` pattern,
then the system shall return that notification with a null link.

### AC-047-006 — 단건 읽음 응답 링크 포함 (REQ-NLINK-006)

When a `portfolio_comment` notification with an active public share is marked as read,
the system shall include the resolved `/shared/{share_token}` link in the mark-as-read response.

### AC-047-007 — 다중 포트폴리오 알림 각각 산출 (REQ-NLINK-007)

When the notification list contains two portfolio notifications referencing two different portfolios each with its own active public share,
the system shall return each notification with the link matching its own portfolio's share token.

### AC-047-008 — 프론트 링크 알림 클릭 이동 (REQ-NLINK-008·009)

When the user activates a rendered notification that has link `/shared/abc123`,
the page shall navigate to `/shared/abc123`.

### AC-047-009 — 프론트 링크 없는 알림 비상호작용 (REQ-NLINK-010)

Where a rendered notification has a null link,
the page shall not render a navigation control for that notification.

### AC-047-010 — 프론트 클릭 시 읽음 처리 (REQ-NLINK-011)

When the user activates a linked notification that is unread,
the page shall issue a mark-as-read request for that notification.

---

## 5. 기술 설계 (Technical Approach)

### 5.1 알림 스키마 확장 (notifications/inbox_router.py)

- `NotificationSchema` 에 `link: str | None = None` 필드 추가. 기존 필드는 불변(하위 호환).
- `_to_schema(n)` 시그니처를 `_to_schema(n, link=None)` 로 확장하거나, 링크 맵을 받아 조립하는 헬퍼로 분리. 기존 호출부(단건)는 링크 인자를 전달.

### 5.2 링크 산출 로직 (async, N+1 회피)

- 헬퍼 `_resolve_links(db, notifications) -> dict[int, str | None]`:
  1. 각 알림에서 타입이 `portfolio_like`·`portfolio_comment` 인 항목만 필터.
  2. krx_code 를 정규식 `^P(\d+)$` 로 파싱하여 `portfolio_id` 추출(불일치 → 해당 알림 링크 없음, REQ-NLINK-005).
  3. 추출된 portfolio_id 집합에 대해 **단일 async 쿼리**: `select(PortfolioShare.portfolio_id, PortfolioShare.share_token).where(PortfolioShare.portfolio_id.in_(ids), PortfolioShare.is_public.is_(True))`. 결과로 `portfolio_id -> share_token` 맵 구성(공개 공유 없으면 부재 → null, REQ-NLINK-004).
  4. 알림 id → `/shared/{share_token}` (있을 때만) 맵 반환.
- `get_notifications`: rows 조회 후 `_resolve_links` 호출, `[_to_schema(n, links.get(n.id)) for n in rows]` 반환(REQ-NLINK-001·002·007).
- `mark_as_read`: 단건 notification 에 대해 `_resolve_links(db, [notification])` 호출 후 `_to_schema(notification, links.get(notification.id))` 반환(REQ-NLINK-006).
- 일반 타입(`price_alert`·`rec_new`·`rec_dropped`)은 필터 단계에서 제외되어 자동으로 `link=None`(REQ-NLINK-003).

### 5.3 프론트엔드 타입 (api/notifications.ts)

- `Notification` 인터페이스에 `link: string | null` 추가. `fetchNotifications`·`markAsRead` 반환 타입에 자동 반영(응답 파싱 그대로 사용, 백엔드가 없으면 `null`).

### 5.4 프론트엔드 UI (pages/Notifications.tsx)

- `import { useNavigate } from 'react-router-dom'` 사용(App 라우트 `/shared/:shareToken` 존재).
- 각 알림 렌더 시 `n.link` 가 truthy 이면 클릭 가능한 요소(`role="button"` 또는 `<button>`/`<a>`)로 감싼다(REQ-NLINK-008). `onClick`: 미읽음이면 `markAsRead(n.id)` 호출(REQ-NLINK-011) 후 `navigate(n.link)`(REQ-NLINK-009).
- `n.link` 가 없으면 기존 비상호작용 렌더 유지(내비게이션 컨트롤 미노출, REQ-NLINK-010).
- 기존 읽음 배지·타입 배지(좋아요=분홍, 댓글=파랑) 렌더는 변경 없음.

### 5.5 빌드 산출물 동기화 (.js/.ts 페어)

- 본 프로젝트는 `.tsx`/`.ts` 소스와 커밋된 `.js` 빌드 산출물을 **쌍으로** 유지한다. 수정한 모든 소스(`notifications.ts`, `Notifications.tsx`)는 대응 `.js`(`notifications.js`, `Notifications.js`)도 함께 갱신해야 한다. 백엔드 Python 파일은 빌드 산출물 페어가 없다.

---

## 6. 테스트 목록 (Test Plan)

- 백엔드: `backend/tests/unit/test_notification_links_047.py`(pytest, async 픽스처 DB). 신규 외부 의존성 없음.
- 프론트엔드: `frontend/src/__tests__/notification_links_047.test.tsx`(vitest + React Testing Library, `useNavigate`·API 모듈 모킹).

| ID | 테스트 | 검증 REQ / AC |
|----|--------|---------------|
| T-047-001 | 댓글 알림 + 공개 공유(token abc123) → link `/shared/abc123` | REQ-NLINK-001·002 / AC-001 |
| T-047-002 | 좋아요 알림 + 공개 공유 → link non-null | REQ-NLINK-001 / AC-002 |
| T-047-003 | price_alert 알림 → link null | REQ-NLINK-003 / AC-003 |
| T-047-004 | 좋아요 알림 + 비공개 공유(is_public=False) → link null | REQ-NLINK-004 / AC-004 |
| T-047-005 | 댓글 알림 + 규약 불일치 krx_code(예: `005930`) → link null | REQ-NLINK-005 / AC-005 |
| T-047-006 | 단건 읽음 응답에 link 포함 | REQ-NLINK-006 / AC-006 |
| T-047-007 | 서로 다른 두 포트폴리오 알림 → 각자 올바른 link | REQ-NLINK-007 / AC-007 |
| T-047-008 | 프론트 링크 알림 클릭 → navigate(link) 호출 | REQ-NLINK-008·009 / AC-008 |
| T-047-009 | 프론트 링크 없는 알림 → 내비게이션 컨트롤 미노출 | REQ-NLINK-010 / AC-009 |
| T-047-010 | 프론트 미읽음 링크 알림 클릭 → markAsRead(id) 호출 | REQ-NLINK-011 / AC-010 |

품질 게이트: 백엔드 pytest 통과(커버리지 기준 충족), 프론트 vitest 통과, ESLint·ruff 통과, 신규 외부 의존성 0, **신규 마이그레이션 0개(스키마 불변)**, `.js`/`.ts` 페어 동기화.

---

## 7. 의존성 (Dependencies)

- **SPEC-STOCK-013** (알림 인박스): `Notification` 모델(`krx_code` 규약)·`inbox_router.py`(async `get_notifications`/`mark_as_read`)·`NotificationSchema`·`_to_schema` — 본 SPEC 의 확장 대상.
- **SPEC-STOCK-042** (포트폴리오 공유 & 소셜): `PortfolioShare`(`share_token`·`is_public`·`portfolio_id`) — 링크 산출 조인 대상. App 라우트 `/shared/:shareToken`.
- **SPEC-STOCK-043** (공유 통계 & 좋아요 알림): `add_like` 의 `portfolio_like` 알림(`krx_code=f"P{portfolio.id}"`) — 딥링크 대상 알림.
- **SPEC-STOCK-046** (공유 포트폴리오 댓글): `add_comment` 의 `portfolio_comment` 알림(동일 `krx_code=f"P{portfolio.id}"` 규약) — 딥링크 대상 알림. §2.2 에서 딥링크를 후속 과제로 명시 이연.
- **SPEC-STOCK-044** (소셜 프론트엔드): `Notifications.tsx` 타입 배지·읽음 처리 UI — 클릭 상호작용 추가 대상.

---

## 8. 기술 제약 (Technical Constraints)

- **알림 인박스 라우터는 async(`AsyncSession`, `get_session`)** 이다. 링크 산출 쿼리는 반드시 async 컨텍스트에서 실행하며, sync `sharing.py` 함수를 직접 호출하지 않는다(sync/async 혼용 금지).
- 딥링크 대상 알림의 `krx_code` 는 좋아요·댓글 공통으로 `f"P{portfolio.id}"` 규약을 따른다. 파싱은 `^P(\d+)$` 정규식으로 하며, 종목 코드(예: `005930`)와 형식이 달라 안전하게 구분된다.
- 링크는 **응답 시점 동적 산출**이며 `notifications` 테이블에 컬럼을 추가하지 않는다. 공유가 비공개로 전환되거나 삭제되면 다음 조회부터 자동으로 `link=null` 이 된다(별도 무효화 처리 불필요).
- 목록 링크 산출은 페이지 내 포트폴리오 알림에 대해 **단일 배치 쿼리**로 수행하여 N+1 을 회피한다(`limit` 최대 200).
- `NotificationSchema.link` 는 nullable 이며 기존 필드에 추가되는 하위 호환 변경이다(기존 소비자는 새 필드를 무시할 수 있음).
- 프론트 라우트는 `/shared/:shareToken`(App.tsx) 를 사용한다. 백엔드가 산출하는 `/shared/{share_token}` 경로와 정확히 일치한다.
- React + TypeScript(`.tsx`/`.ts`) 소스, Vite 빌드. 커밋된 `.js` 산출물과 페어 동기화 필수.
- ESLint·ruff 통과, 신규 외부 의존성 금지, 모든 신규 동작 단위 테스트 필수.
