---
id: SPEC-STOCK-044
title: 포트폴리오 소셜 프론트엔드 완성
status: draft
version: 0.1.0
created_at: 2026-06-30
updated_at: 2026-06-30
author: ircp
priority: medium
issue_number: null
branch: feature/SPEC-STOCK-036
labels: [portfolio, sharing, social, frontend, notification, stats]
---

# SPEC-STOCK-044 — 포트폴리오 소셜 프론트엔드 완성 (Social Frontend Completion)

## HISTORY

| Version | Date | Author | Note |
|---------|------|--------|------|
| 0.1.0 | 2026-06-30 | ircp | 최초 초안 — SPEC-043 백엔드(좋아요 취소·좋아요 알림·공유 조회수 일별 통계)의 프론트엔드 미연동분 완성. 좋아요/취소 토글·소유자 7일 조회 통계 패널·portfolio_like 알림 뱃지 라벨. EARS REQ 9개(REQ-SHARE-041~049)·AC 15개. 신규 백엔드/DB/마이그레이션 없음(프론트 전용). 좋아요 토글은 세션-로컬 옵티미스틱 상태로 설계(공개 뷰는 무인증이라 liked_by_me 제공 불가) |

---

## 1. 개요 (Overview)

SPEC-STOCK-043 은 좋아요 취소(`DELETE /shared/{share_token}/like`), 좋아요 인앱 알림(`type="portfolio_like"`), 공유 조회수 일별 통계(`GET /portfolios/{portfolio_id}/share/stats`) 를 **백엔드만** 구현하고(CHANGELOG 0.43.0), 프론트엔드 연동은 명시적으로 후속 과제로 남겼다. 본 SPEC 은 이 세 가지 백엔드 기능을 React 프론트엔드에 연결하여 사용자가 실제로 사용할 수 있게 한다.

- **좋아요/취소 토글 (SharedPortfolio)**: 공개 포트폴리오 뷰에서 좋아요를 누른 뒤 같은 버튼으로 취소할 수 있는 토글 UI 를 제공한다. 공개 뷰 엔드포인트(`GET /shared/{share_token}`)는 무인증이라 현재 사용자의 기존 좋아요 여부를 알 수 없으므로, 토글 상태는 **세션-로컬 옵티미스틱 상태**(좋아요 성공 시 취소 가능 상태로, 취소 성공 시 좋아요 가능 상태로 전환)로 관리한다.
- **공유 조회수 일별 통계 패널 (SharePanel)**: 소유자에게 최근 7일 일별 조회수(`ShareStatsResponse.stats`, 0 채움·날짜 오름차순)를 소형 시각화로 표시한다.
- **좋아요 알림 표시 (Notifications)**: 알림 인박스에서 `type="portfolio_like"` 알림을 한국어 라벨("좋아요")로 표시한다. 현재는 매핑이 없어 원시 타입 문자열이 노출된다.

본 SPEC 은 **프론트엔드 전용**이다. 신규 백엔드 엔드포인트·DB 테이블·마이그레이션·외부 의존성을 추가하지 않으며, SPEC-042/043 이 제공한 기존 API 만 호출한다.

### 1.1 동기 (Why)

SPEC-043 백엔드 출시 후, (1) 좋아요는 누를 수만 있고 화면에서 **취소할 방법이 없으며**, (2) 소유자는 공유 링크의 **일별 조회 추이를 볼 수 없고**, (3) 좋아요 알림이 인박스에 와도 **뱃지에 원시 문자열("portfolio_like")이 노출**된다. 본 SPEC 은 이미 완성된 백엔드를 사용자 인터페이스에 연결해 SPEC-042/043 소셜 기능의 완결성을 확보한다.

---

## 2. 범위 (Scope)

### 2.1 In-Scope

- `frontend/src/api/feed.ts` (+빌드 산출물 `feed.js`): `unlikeSharedPortfolio(shareToken, token)` 함수 추가 (`DELETE /shared/{share_token}/like`, 204→정상, 401/403/404 오류 메시지).
- `frontend/src/api/portfolio.ts` (+`portfolio.js`): `getShareStats(token, portfolioId)` 함수 추가 (`GET /portfolios/{portfolio_id}/share/stats`, `ShareStatsResponse` 반환).
- `frontend/src/pages/SharedPortfolio.tsx` (+`SharedPortfolio.js`): 좋아요/취소 토글 — 세션-로컬 `liked` 상태, 좋아요 성공 시 "좋아요 취소" 노출, 취소 성공 시 "좋아요" 노출.
- `frontend/src/components/SharePanel.tsx` (+`SharePanel.js`): 활성 공유 링크가 있을 때 최근 7일 일별 조회수 패널 표시(소형 막대/리스트).
- `frontend/src/pages/Notifications.tsx` (+`Notifications.js`): `TypeBadge` 라벨·색상 맵에 `portfolio_like` → "좋아요" 추가.
- 프론트엔드 단위 테스트(vitest + React Testing Library): `frontend/src/__tests__/social_frontend_044.test.tsx`.

### 2.2 Out-of-Scope (제외)

> [HARD] 본 SPEC 은 아래 항목을 명시적으로 제외한다.

- **자동 매매·자동 주문 실행** (규제·책임 리스크로 프로젝트 영구 제외).
- **신규 백엔드 엔드포인트·DB 테이블·마이그레이션** — 마이그레이션 최신은 0027 로 유지, 추가 없음.
- **공개 뷰에 `liked_by_me`(현재 사용자 좋아요 여부) 필드 추가** — `GET /shared/{share_token}` 는 무인증이므로 백엔드 스키마 변경 없이 세션-로컬 옵티미스틱 토글만 사용.
- **일별 통계의 좋아요수(per-day like_count) 표시** — 백엔드 `ShareViewStatItem` 은 `date` + `view_count` 만 제공(좋아요 일별 시계열 미제공).
- **신규 차트/수치 라이브러리 도입** — 통계는 기존 인라인 요소(div 막대/리스트)로 표시.
- **실시간 갱신(WebSocket)·자동 폴링** — 통계·좋아요는 요청 시점 스냅샷만.
- **좋아요 알림 클릭 시 포트폴리오로 이동(딥링크 네비게이션)** — 뱃지 라벨 표시까지만.
- **좋아요 알림의 이메일/텔레그램 발송** — 인앱 알림 표시만.
- **Feed 페이지(`/feed`) 변경** — 본 SPEC 은 SharedPortfolio·SharePanel·Notifications 3개 화면만 수정.

---

## 3. 요구사항 (Requirements — EARS)

> REQ 번호는 SPEC-042(001~011)·SPEC-043(031~040)에 이어 **REQ-SHARE-041** 부터 부여한다. 모든 REQ 는 관찰 가능한 프론트엔드 동작을 단일 SHALL 로 기술한다.

### 3.1 좋아요 성공 → 취소 상태 전환 (REQ-SHARE-041)

- **REQ-SHARE-041**: When an authenticated user activates the like control on the SharedPortfolio page and `POST /shared/{share_token}/like` returns 200, the page SHALL render a control labeled "좋아요 취소" reflecting the like_count from the response.

### 3.2 좋아요 취소 성공 → 좋아요 상태 복귀 (REQ-SHARE-042)

- **REQ-SHARE-042**: When the user activates the "좋아요 취소" control and `DELETE /shared/{share_token}/like` returns 204, the page SHALL render a control labeled "좋아요" with the displayed like_count decremented by 1.

### 3.3 비인증 좋아요 시도 차단 (REQ-SHARE-043)

- **REQ-SHARE-043**: If no authentication token is present, then the page SHALL NOT issue any request to the like or unlike endpoint when the like control is activated, and SHALL display a login-required message.

### 3.4 좋아요/취소 요청 실패 처리 (REQ-SHARE-044)

- **REQ-SHARE-044**: If a like or unlike request returns a non-success status, then the page SHALL keep the current control state unchanged and SHALL display an error message.

### 3.5 소유자 일별 통계 조회 (REQ-SHARE-045)

- **REQ-SHARE-045**: When the portfolio owner opens SharePanel for a portfolio that has an active share link, the panel SHALL request the share stats endpoint (`GET /portfolios/{portfolio_id}/share/stats`) and render exactly 7 daily view-count entries in ascending date order.

### 3.6 조회 없는 날 0 표시 (REQ-SHARE-046)

- **REQ-SHARE-046**: When a `ShareViewStatItem` in the stats response has `view_count=0`, the panel SHALL render that day's entry with a displayed value of 0 (all 7 days present, no omitted dates).

### 3.7 통계 조회 실패 격리 (REQ-SHARE-047)

- **REQ-SHARE-047**: If the share stats request fails, then the panel SHALL display a stats error indicator while continuing to render the existing share link and copy/disable controls.

### 3.8 공유 링크 없을 때 통계 미요청 (REQ-SHARE-048)

- **REQ-SHARE-048**: If the portfolio has no active share link in SharePanel, then the panel SHALL NOT request the share stats endpoint and SHALL NOT render the stats section.

### 3.9 좋아요 알림 뱃지 라벨 (REQ-SHARE-049)

- **REQ-SHARE-049**: When the notifications list contains an item with `type="portfolio_like"`, the Notifications page SHALL render its type badge with the localized label "좋아요" instead of the raw type string.

---

## 4. 인수 조건 (Acceptance Criteria — EARS)

> 모든 AC 는 EARS(Event-driven / Unwanted behavior) 형식으로 작성하며, 각 AC 는 단일 관찰 가능 동작(단일 SHALL)만 검증한다. 총 15개.

### AC-044-001 — 좋아요 성공 → "좋아요 취소" 노출 (REQ-SHARE-041)

When an authenticated user clicks the like control and the like request resolves with status 200,
the page shall render a control whose label is "좋아요 취소".

### AC-044-002 — 좋아요 성공 → like_count 갱신 (REQ-SHARE-041)

When the like request resolves with `like_count=N`,
the page shall display the like count as N.

### AC-044-003 — 취소 성공 → "좋아요" 복귀 (REQ-SHARE-042)

When the user clicks the "좋아요 취소" control and the unlike request resolves with status 204,
the page shall render a control whose label is "좋아요".

### AC-044-004 — 취소 성공 → like_count 1 감소 (REQ-SHARE-042)

When the unlike request resolves with status 204 and the prior displayed like count was N,
the page shall display the like count as N minus 1.

### AC-044-005 — 비인증 클릭 → 네트워크 요청 없음 (REQ-SHARE-043)

If no authentication token is present and the user clicks the like control,
then the page shall not issue any request to the like or unlike endpoint.

### AC-044-006 — 비인증 클릭 → 로그인 안내 (REQ-SHARE-043)

If no authentication token is present and the user clicks the like control,
then the page shall display a login-required message.

### AC-044-007 — 취소 실패 → 상태 불변 (REQ-SHARE-044)

If the unlike request rejects (non-204),
then the page shall keep the current control label unchanged.

### AC-044-008 — 취소 실패 → 오류 메시지 (REQ-SHARE-044)

If the unlike request rejects (non-204),
then the page shall display an error message.

### AC-044-009 — 활성 공유 시 통계 호출 (REQ-SHARE-045)

When the owner opens SharePanel for a portfolio with an active share link,
the panel shall issue a request to `GET /portfolios/{portfolio_id}/share/stats` for that portfolio.

### AC-044-010 — 통계 7개 항목·오름차순 렌더 (REQ-SHARE-045)

When the stats response contains 7 items,
the panel shall render exactly 7 daily entries in ascending date order.

### AC-044-011 — 조회 0인 날 0 표시 (REQ-SHARE-046)

When a stats item has `view_count=0`,
the panel shall render that day's entry with a displayed value of 0.

### AC-044-012 — 통계 실패 → 오류 표시 (REQ-SHARE-047)

If the share stats request fails,
then the panel shall display a stats error indicator.

### AC-044-013 — 통계 실패 → 공유 컨트롤 유지 (REQ-SHARE-047)

If the share stats request fails,
then the panel shall continue to render the share link input and copy control.

### AC-044-014 — 공유 링크 없음 → 통계 미호출 (REQ-SHARE-048)

If the portfolio has no active share link,
then the panel shall not issue any request to the share stats endpoint.

### AC-044-015 — portfolio_like 알림 라벨 "좋아요" (REQ-SHARE-049)

When the notifications list contains an item with `type="portfolio_like"`,
the page shall render its badge text as "좋아요".

---

## 5. 기술 설계 (Technical Approach)

### 5.1 API 클라이언트 (frontend/src/api)

- `feed.ts` (+`feed.js`): `unlikeSharedPortfolio(shareToken: string, token: string): Promise<void>` 추가.
  - `fetch(DELETE /shared/{shareToken}/like, Authorization: Bearer token)`.
  - 204 → resolve(void). 401 → "로그인이 필요합니다." / 403 → "자신의 포트폴리오는 취소할 수 없습니다." / 404 → "공유된 포트폴리오를 찾을 수 없습니다." 기타 비-204 → 일반 오류. (기존 `likeSharedPortfolio` 오류 메시지 패턴 일관.)
- `portfolio.ts` (+`portfolio.js`): `getShareStats(token: string, portfolioId: number): Promise<ShareStatsResponse>` 추가.
  - `fetch(GET /portfolios/{portfolioId}/share/stats, Authorization: Bearer token)`. 비-200 → 오류 throw.
  - 타입: `ShareViewStatItem { date: string; view_count: number }`, `ShareStatsResponse { stats: ShareViewStatItem[] }` 정의(기존 응답 스키마와 1:1).

### 5.2 SharedPortfolio 토글 (pages/SharedPortfolio.tsx)

- 세션-로컬 상태 `liked: boolean`(초기 false — 공개 뷰는 무인증이라 서버에서 좋아요 여부를 알 수 없음) 추가.
- 단일 토글 핸들러: `liked === false` 면 `likeSharedPortfolio` 호출(성공 시 `liked=true`, `likeCount=res.like_count`), `liked === true` 면 `unlikeSharedPortfolio` 호출(성공 시 `liked=false`, `likeCount -= 1`).
- 버튼 라벨: `liked ? "♥ 좋아요 취소" : "♡ 좋아요"`. `token` 없으면 요청 없이 `likeError`에 로그인 안내 설정.
- 실패 시 `liked`/`likeCount` 변경하지 않고 `likeError` 설정(옵티미스틱이 아닌 응답-확정 후 상태 변경).

### 5.3 SharePanel 통계 (components/SharePanel.tsx)

- `shareData`(활성 공유)가 존재할 때만 `getShareStats(token, portfolioId)` 호출(`useEffect` 의존성: `token`, `portfolioId`, `shareData?.share_token`).
- `stats: ShareViewStatItem[]`·`statsError: string | null` 상태 추가. 7개 항목을 날짜 오름차순으로 소형 막대(상대 높이) 또는 라벨-값 리스트로 렌더. `view_count=0` 도 항목으로 표시.
- 통계 실패는 기존 링크/복사/비활성화 UI 를 깨지 않고 별도 영역에서 오류 문구만 표시.

### 5.4 Notifications 뱃지 (pages/Notifications.tsx)

- `TypeBadge` 의 `colors`/`labels` 맵에 `portfolio_like` 항목 추가: `labels.portfolio_like = "좋아요"`, `colors.portfolio_like = "bg-pink-100 text-pink-800"`(기존 Tailwind 유틸 패턴 일관). 읽음/안읽음·읽음 처리 로직은 기존 제네릭 경로 재사용(변경 없음).

### 5.5 빌드 산출물 동기화 (.js/.ts 페어)

- 본 프로젝트는 `.tsx`/`.ts` 소스와 커밋된 `.js` 빌드 산출물을 **쌍으로** 유지한다. 수정한 모든 소스(`feed.ts`, `portfolio.ts`, `SharedPortfolio.tsx`, `SharePanel.tsx`, `Notifications.tsx`)는 대응 `.js` 파일도 함께 갱신해야 한다.

---

## 6. 테스트 목록 (Test Plan)

- 파일: `frontend/src/__tests__/social_frontend_044.test.tsx` (vitest + React Testing Library, API 모듈 모킹). 신규 외부 의존성 없음.

| ID | 테스트 | 검증 REQ / AC |
|----|--------|---------------|
| T-044-001 | 좋아요 성공 → "좋아요 취소" 라벨 노출 | REQ-SHARE-041 / AC-001 |
| T-044-002 | 좋아요 성공 → like_count 응답값 반영 | REQ-SHARE-041 / AC-002 |
| T-044-003 | 취소 성공(204) → "좋아요" 라벨 복귀 | REQ-SHARE-042 / AC-003 |
| T-044-004 | 취소 성공(204) → like_count 1 감소 | REQ-SHARE-042 / AC-004 |
| T-044-005 | 비인증 클릭 → like/unlike fetch 미호출 | REQ-SHARE-043 / AC-005 |
| T-044-006 | 비인증 클릭 → 로그인 안내 표시 | REQ-SHARE-043 / AC-006 |
| T-044-007 | 취소 실패 → 라벨 상태 불변 | REQ-SHARE-044 / AC-007 |
| T-044-008 | 취소 실패 → 오류 메시지 표시 | REQ-SHARE-044 / AC-008 |
| T-044-009 | 활성 공유 시 getShareStats 호출 | REQ-SHARE-045 / AC-009 |
| T-044-010 | 통계 7개 항목·날짜 asc 렌더 | REQ-SHARE-045 / AC-010 |
| T-044-011 | view_count=0 인 날도 0 으로 표시 | REQ-SHARE-046 / AC-011 |
| T-044-012 | getShareStats 실패 → 오류 표시 | REQ-SHARE-047 / AC-012 |
| T-044-013 | getShareStats 실패 → 공유 링크/복사 유지 | REQ-SHARE-047 / AC-013 |
| T-044-014 | 공유 링크 없음 → getShareStats 미호출 | REQ-SHARE-048 / AC-014 |
| T-044-015 | portfolio_like 알림 → 뱃지 "좋아요" | REQ-SHARE-049 / AC-015 |

품질 게이트: 신규 프론트 코드 단위 테스트 통과, ESLint 통과, 신규 외부 의존성 0, `.js`/`.ts` 페어 동기화.

---

## 7. 의존성 (Dependencies)

- **SPEC-STOCK-043** (공유 알림 & 소셜 확장): `DELETE /shared/{share_token}/like`(204/401/403/404), `GET /portfolios/{portfolio_id}/share/stats`(`ShareStatsResponse`, 7일·0채움), `portfolio_like` 알림 — 본 SPEC 이 연동하는 백엔드.
- **SPEC-STOCK-042** (포트폴리오 공유 & 소셜): `feed.ts`(`getSharedPortfolio`·`likeSharedPortfolio`), `SharedPortfolio.tsx`, `SharePanel.tsx`, `LikeResponse`/`SharePublicResponse`/`ShareResponse` — 확장 대상.
- **SPEC-STOCK-013** (알림 인박스): `Notifications.tsx`, `api/notifications.ts`, `markNotificationRead` — 좋아요 알림 표시에 재사용.
- 인증: `frontend/src/auth/AuthContext`(`useAuth().token`).

---

## 8. 기술 제약 (Technical Constraints)

- React + TypeScript(`.tsx`/`.ts`) 소스, Vite 빌드. 커밋된 `.js` 산출물과 페어 동기화 필수.
- 좋아요 토글은 **응답-확정 후 상태 변경**(옵티미스틱 즉시 전환 금지) — 실패 시 화면 상태가 서버와 어긋나지 않도록 한다.
- `liked` 초기값은 항상 false: 공개 뷰는 무인증이라 서버가 현재 사용자의 기존 좋아요 여부를 제공하지 않는다(설계상 한계, Out-of-Scope 참조).
- 통계 표시는 기존 인라인 마크업만 사용 — 신규 차트/수치 라이브러리 도입 금지.
- 좋아요 알림 뱃지는 `code_comments: ko` 정책에 따라 한국어 라벨("좋아요") 사용.
- ESLint 통과, 신규 외부 의존성 금지, 모든 신규 동작 단위 테스트 필수.
