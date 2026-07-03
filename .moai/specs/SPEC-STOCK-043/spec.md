---
id: SPEC-STOCK-043
title: 공유 포트폴리오 알림 & 소셜 확장
status: draft
version: 0.4.0
created_at: 2026-06-29
updated_at: 2026-06-30
author: ircp
priority: medium
issue_number: null
branch: feature/SPEC-STOCK-036
labels: [portfolio, sharing, social, notification, stats, backend, frontend]
---

# SPEC-STOCK-043 — 공유 포트폴리오 알림 & 소셜 확장 (Portfolio Share Notification, Unlike & View Stats)

## HISTORY

| Version | Date | Author | Note |
|---------|------|--------|------|
| 0.1.0 | 2026-06-29 | ircp | 최초 초안 — SPEC-042 후속. 좋아요 취소(unlike)·좋아요 인앱 알림·공유 조회수 일별 통계. EARS REQ 10개(REQ-SHARE-031~040)·DB 마이그 0027(신규 테이블 `share_view_stats` 1개)·제외 항목 정의. 알림 UNIQUE 제약 충돌 설계 결정 명시 |
| 0.2.0 | 2026-06-30 | ircp | plan-auditor v1 지적사항 반영 — AC를 EARS 형식으로 재작성(14→15개), REQ-034/040 복합 분리(각 a/b), REQ-038 SQL 구문 제거·KST 타임존 명시, REQ-035 필드 명세 설계 노트로 이동, REQ-036 크로스 레퍼런스에 SPEC ID 추가, AC-043-012b 추가(공유 레코드 없음 케이스) |
| 0.3.0 | 2026-06-30 | ircp | plan-auditor v2 지적사항 반영 — 복합 SHALL AC 5개 분리(001→001a/b/c, 007→007a/b, 008→008a/b, 010→010a/b, 011→011a/b), REQ-031 복합 SHALL 제거, REQ-036 중복 절 제거, REQ-037 "신규 엔드포인트 없음" Out-of-Scope 이동, REQ-038→038a/b 분리, REQ-039→039a 이름변경+then 추가, REQ-039b "then" 추가. AC 총 21개. |
| 0.4.0 | 2026-06-30 | ircp | plan-auditor v3 지적사항 반영 — REQ-038b 미커버 해소(AC-011c 신설), REQ-037 읽음처리 미커버 해소(AC-010c 신설). AC 총 23개. |

---

## 1. 개요 (Overview)

SPEC-STOCK-042(포트폴리오 공유 & 소셜)에서 **명시적으로 제외**했던 후속 항목 3가지를 구현한다.

- **좋아요 취소(Unlike)**: 로그인 사용자가 자신이 누른 좋아요를 취소한다(`DELETE /shared/{share_token}/like`). 멱등 — 좋아요가 없어도 204 를 반환하며, 소유자는 취소할 수 없다(403).
- **좋아요 인앱 알림(Like Notification)**: 신규 좋아요가 발생하면 포트폴리오 **소유자**에게 기존 알림 인박스(SPEC-013)로 인앱 알림(`type="portfolio_like"`)을 발송한다. 중복 좋아요·자기 좋아요에는 알림이 발생하지 않는다.
- **공유 조회수 일별 통계(Daily View Stats)**: 공개 뷰 호출 시 누적 `view_count` 증가와 함께 일자별 조회수를 `share_view_stats` 테이블에 upsert 한다. 소유자는 `GET /portfolios/{portfolio_id}/share/stats` 로 **최근 7일** 일별 조회수(조회 없는 날은 0 채움)를 확인한다.

본 SPEC 은 SPEC-042 의 **읽기 전용 + 소유자 통제** 원칙과 기존 알림 인박스 인프라(SPEC-013)를 재사용하며, 신규 외부 의존성·신규 알림 채널을 추가하지 않는다.

### 1.1 동기 (Why)

SPEC-042 로 공유 링크·좋아요·디스커버리 피드가 도입됐으나, (1) 좋아요는 멱등 추가만 가능해 **취소 수단이 없고**, (2) 좋아요를 받아도 소유자가 **알 방법이 없으며**, (3) 소유자가 공유 링크의 **시간대별 반응(일별 조회 추이)** 을 파악할 수 없다. 본 SPEC 은 이 세 공백을 메워 소셜 상호작용의 완결성과 소유자 인사이트를 제공한다.

---

## 2. 범위 (Scope)

### 2.1 In-Scope

- 좋아요 취소 (`DELETE /shared/{share_token}/like`, 인증 필수, 멱등, 소유자 403)
- 좋아요 발생 시 소유자 인앱 알림 적재 (`type="portfolio_like"`, 기존 `/notifications` 인박스 재사용)
- 공유 조회수 일별 통계 적재 — 공개 뷰 호출 시 `share_view_stats` upsert
- 일별 통계 조회 엔드포인트 (`GET /portfolios/{portfolio_id}/share/stats`, 소유자 전용, 최근 7일·0 채움)
- 신규 DB 테이블 `share_view_stats` (마이그레이션 0027)
- 프론트엔드: `SharePanel`(취소 버튼·소유자용 통계 링크), `SharedPortfolio`(좋아요/취소 토글), `api/sharing.ts`(`unlikeSharedPortfolio`·`getShareStats`)

### 2.2 Out-of-Scope (제외)

> [HARD] 본 SPEC 은 아래 항목을 명시적으로 제외한다.

- **자동 매매·자동 주문 실행** (규제·책임 리스크로 프로젝트 영구 제외)
- **좋아요 알림의 이메일/텔레그램 발송** — 인앱 알림만 발송(기존 외부 채널 미연동)
- **좋아요 알림에 대한 `NotificationPreference` opt-out 신설** — 기존 opt-out 모델만 사용, `portfolio_like` 전용 설정 미추가
- **팔로우/팔로워 그래프** — 후속 SPEC 대상
- **댓글·답글** — 소셜 상호작용은 좋아요/취소만 지원
- **실시간 갱신(WebSocket)** — 통계·뷰는 요청 시점 스냅샷 조회만
- **7일 초과 조회 이력/장기 시계열 분석** — 통계 조회는 최근 7일 고정
- **신규 외부 의존성·신규 수치/차트 라이브러리 도입** — 프론트 통계는 기존 컴포넌트(소형 리스트/차트)로 표시
- **신규 알림 인박스 엔드포인트 추가** — `GET /notifications`, `GET /notifications/unread-count`, `PATCH /notifications/{id}/read` 기존 엔드포인트만 사용(SPEC-013)

---

## 3. 요구사항 (Requirements — EARS)

> REQ 번호는 SPEC-042(REQ-SHARE-001~011)에 이어 **REQ-SHARE-031** 부터 부여한다. 논리 순서: 취소(성공→멱등→소유자→비인증/비공개) → 좋아요 알림(생성→중복→인박스) → 일별 통계(적재→비공개 제외→조회→공유없음→접근제어).
>
> - REQ-034/040은 각각 a/b로 분리(단일 SHALL 원칙).
> - REQ-038은 a/b로 분리(Event-driven과 Unwanted behavior 패턴 분리).
> - REQ-039a/039b 쌍을 이룸(REQ-039는 REQ-039a로 명명). REQ-034/040의 a/b 분리와 동일한 패턴.

### 3.1 좋아요 취소 — 성공 (REQ-SHARE-031)

- **REQ-SHARE-031**: When an authenticated non-owner user calls `DELETE /shared/{share_token}/like` and the share record is `is_public=True` and the user's like row exists in `portfolio_likes`, the system SHALL delete the like row and return **204 No Content**.

### 3.2 좋아요 취소 — 멱등 (REQ-SHARE-032)

- **REQ-SHARE-032**: When an authenticated non-owner user calls `DELETE /shared/{share_token}/like` and no like row exists for that user, the system SHALL return **204 No Content** with no side effects. (멱등 — 좋아요가 없는 취소 호출은 404가 아닌 204로 처리한다.)

### 3.3 좋아요 취소 — 소유자 금지 (REQ-SHARE-033)

- **REQ-SHARE-033**: If the requesting user is the portfolio owner, then the system SHALL return **403 Forbidden** when `DELETE /shared/{share_token}/like` is called.

### 3.4a 좋아요 취소 — 비인증 거부 (REQ-SHARE-034a)

- **REQ-SHARE-034a**: If no valid authentication token is provided, then the system SHALL return **401 Unauthorized** when `DELETE /shared/{share_token}/like` is called.

### 3.4b 좋아요 취소 — 비공개/미존재 거부 (REQ-SHARE-034b)

- **REQ-SHARE-034b**: If the share record does not exist or `is_public=False`, then the system SHALL return **404 Not Found** when `DELETE /shared/{share_token}/like` is called by an authenticated user.

### 3.5 좋아요 알림 — 생성 (REQ-SHARE-035)

- **REQ-SHARE-035**: When `POST /shared/{share_token}/like` succeeds as a **new** like (not a duplicate), the system SHALL insert one `Notification` row for the portfolio owner (`portfolio.user_id`) with notification type `portfolio_like`.

  > 설계 결정(Section 5.3 상세): `notifications` 테이블의 `uq_notification_user_type_code_date(user_id, type, krx_code, ref_date)` UNIQUE 제약을 활용한다. 알림 적재는 **IntegrityError-안전 insert**로 수행하며, 동일 포트폴리오·동일 KST 일자의 중복 좋아요 알림은 1건으로 합쳐진다(알림 스팸 방지). `krx_code = f"P{portfolio_id}"`로 두어 서로 다른 포트폴리오의 좋아요 알림이 같은 행으로 붕괴되지 않도록 보장한다. portfolio_id는 최대 8자리(99,999,999) 범위에서 P-prefix 포함 10자 이내로 VARCHAR(10) 제약을 충족한다.

### 3.6 좋아요 알림 — 비발생 조건 (REQ-SHARE-036)

- **REQ-SHARE-036**: If the like request is a **duplicate** (the user already liked) or the requester is the portfolio owner (see SPEC-STOCK-042 REQ-SHARE-008), then the system SHALL NOT insert a new `Notification` row.

### 3.7 좋아요 알림 — 인박스 노출 (REQ-SHARE-037)

- **REQ-SHARE-037**: When the portfolio owner calls `GET /notifications`, the system SHALL include `type="portfolio_like"` notifications in the response list, unread count (`GET /notifications/unread-count`), and read-marking (`PATCH /notifications/{id}/read`) identically to other notification types.

### 3.8a 공유 조회수 일별 통계 — 적재 (REQ-SHARE-038a)

- **REQ-SHARE-038a**: When `GET /shared/{share_token}` returns a successful public view response, the system SHALL upsert a row in `share_view_stats` keyed on `(share_id, stat_date)` where `stat_date` is today's date in KST (Asia/Seoul timezone), incrementing the daily `view_count` by 1.

### 3.8b 공유 조회수 일별 통계 — 비공개 제외 (REQ-SHARE-038b)

- **REQ-SHARE-038b**: If the share record is not public (results in a 404 response), then the system SHALL NOT upsert any row in `share_view_stats`.

### 3.9a 공유 조회수 일별 통계 — 조회 (REQ-SHARE-039a)

- **REQ-SHARE-039a**: When the portfolio owner calls `GET /portfolios/{portfolio_id}/share/stats`, the system SHALL return **200** with exactly **7 items** covering the last 7 days (today inclusive, 6 prior days) in ascending date order, with `view_count=0` for days with no recorded views.

### 3.9b 공유 레코드 없음 케이스 (REQ-SHARE-039b)

- **REQ-SHARE-039b**: If the portfolio has no share record (`portfolio_shares` row does not exist), then the system SHALL return **200** with 7 items all having `view_count=0` when `GET /portfolios/{portfolio_id}/share/stats` is called by the owner.

### 3.10a 일별 통계 — 비소유자 접근 금지 (REQ-SHARE-040a)

- **REQ-SHARE-040a**: If the requesting user is not the portfolio owner, then the system SHALL return **404 Not Found** when `GET /portfolios/{portfolio_id}/share/stats` is called.

### 3.10b 일별 통계 — 비인증 접근 금지 (REQ-SHARE-040b)

- **REQ-SHARE-040b**: If no valid authentication token is provided, then the system SHALL return **401 Unauthorized** when `GET /portfolios/{portfolio_id}/share/stats` is called.

---

## 4. 인수 조건 (Acceptance Criteria — EARS)

> 모든 AC는 EARS(Event-driven / Unwanted behavior) 형식으로 작성한다. 각 AC는 단일 observable behavior 하나만 검증한다(단일 SHALL 원칙). 총 23개.

### AC-043-001a — 좋아요 취소 성공 → 204 (REQ-SHARE-031)

When an authenticated non-owner user calls `DELETE /shared/{share_token}/like` and the user's like row exists,
the system shall return **204 No Content**.

### AC-043-001b — 좋아요 취소 성공 → 행 삭제 (REQ-SHARE-031)

When an authenticated non-owner user calls `DELETE /shared/{share_token}/like` and the user's like row exists,
the system shall delete the `portfolio_likes` row for that user.

### AC-043-001c — 좋아요 취소 성공 → like_count 감소 (REQ-SHARE-031)

When an authenticated non-owner user calls `DELETE /shared/{share_token}/like` and the user's like row exists,
the system shall reflect a derived `like_count` (= COUNT of `portfolio_likes`) that is 1 less than before the deletion.

### AC-043-002 — 좋아요 없는 취소는 멱등 204 (REQ-SHARE-032)

When an authenticated non-owner user calls `DELETE /shared/{share_token}/like` and no like row exists for that user,
the system shall return **204 No Content** with no side effects (not 404).

### AC-043-003 — 소유자 좋아요 취소 금지 (REQ-SHARE-033)

If the requesting user is the portfolio owner,
then the system shall return **403 Forbidden** when `DELETE /shared/{share_token}/like` is called.

### AC-043-004 — 비인증 취소 거부 (REQ-SHARE-034a)

If no valid authentication token is provided,
then the system shall return **401 Unauthorized** when `DELETE /shared/{share_token}/like` is called.

### AC-043-005 — 비공개 포트폴리오 취소는 404 (REQ-SHARE-034b)

If the share record has `is_public=False` or does not exist,
then the system shall return **404 Not Found** when `DELETE /shared/{share_token}/like` is called by an authenticated user.

### AC-043-006 — 신규 좋아요 시 소유자 알림 생성 (REQ-SHARE-035)

When user B (username="bob") calls `POST /shared/{share_token}/like` as a new like on portfolio P7 owned by user A,
the system shall insert exactly one `Notification` row with `type="portfolio_like"`, `user_id=A.id`, `krx_code="P7"`, and a title containing "bob".

### AC-043-007a — 중복 좋아요 → 멱등 200 (REQ-SHARE-036)

When user B calls `POST /shared/{share_token}/like` again on a portfolio already liked,
the system shall return **200** (idempotent).

### AC-043-007b — 중복 좋아요 → 알림 미발생 (REQ-SHARE-036)

When user B calls `POST /shared/{share_token}/like` again on a portfolio already liked,
the system shall leave the count of `type="portfolio_like"` notifications unchanged.

### AC-043-008a — 자기 좋아요 → 403 (REQ-SHARE-036)

If the requesting user is the portfolio owner,
then the system shall return **403 Forbidden** when `POST /shared/{share_token}/like` is called.

### AC-043-008b — 자기 좋아요 → 알림 미발생 (REQ-SHARE-036)

If the requesting user is the portfolio owner and `POST /shared/{share_token}/like` returns 403,
then the system shall not create any `portfolio_like` notification row.

### AC-043-009 — 서로 다른 포트폴리오 좋아요 알림은 분리 (REQ-SHARE-035)

When user B likes portfolio P7 and portfolio P8 (both owned by user A) on the same day,
the system shall insert **two** separate `Notification` rows: one with `krx_code="P7"` and one with `krx_code="P8"`.

### AC-043-010a — 좋아요 알림이 unread-count에 포함 (REQ-SHARE-037)

When user A has one unread `portfolio_like` notification and calls `GET /notifications/unread-count`,
the system shall include that notification in the unread count.

### AC-043-010b — 좋아요 알림이 알림 목록에 포함 (REQ-SHARE-037)

When user A has one unread `portfolio_like` notification and calls `GET /notifications`,
the system shall include an item with `type="portfolio_like"` in the response list.

### AC-043-010c — 좋아요 알림 읽음 처리 (REQ-SHARE-037)

When user A calls `PATCH /notifications/{id}/read` for a `portfolio_like` notification,
the system shall mark that notification as read identically to other notification types.

### AC-043-011a — 공개 뷰 호출 시 share_view_stats 적재 (REQ-SHARE-038a)

When `GET /shared/{share_token}` is called twice for a public portfolio with no existing `share_view_stats` row for today (KST),
the system shall upsert so that `share_view_stats.view_count = 2` for `(share_id, today)`.

### AC-043-011b — 공개 뷰 호출 시 portfolio_shares.view_count 증가 (REQ-SHARE-038a)

When `GET /shared/{share_token}` is called twice for a public portfolio,
the system shall increment `portfolio_shares.view_count` by 2.

### AC-043-011c — 비공개 포트폴리오 뷰는 통계 미적재 (REQ-SHARE-038b)

If `GET /shared/{share_token}` returns 404 (share record is not public or does not exist),
then the system shall not insert or update any row in `share_view_stats`.

### AC-043-012 — 최근 7일 통계 0 채움 조회 (REQ-SHARE-039a)

When the portfolio owner calls `GET /portfolios/{portfolio_id}/share/stats` for a portfolio with 3 views today and no views yesterday,
the system shall return **200** with a `stats` array of exactly 7 items in ascending date order,
where today's item has `view_count=3` and yesterday's item has `view_count=0`.

### AC-043-012b — 공유 레코드 없는 통계 조회 (REQ-SHARE-039b)

If the portfolio has no `portfolio_shares` row,
then the system shall return **200** with a `stats` array of exactly 7 items all having `view_count=0` when `GET /portfolios/{portfolio_id}/share/stats` is called by the owner.

### AC-043-013 — 비소유자 통계 조회는 404 (REQ-SHARE-040a)

If the requesting user is not the portfolio owner,
then the system shall return **404 Not Found** when `GET /portfolios/{portfolio_id}/share/stats` is called.

### AC-043-014 — 비인증 통계 조회는 401 (REQ-SHARE-040b)

If no valid authentication token is provided,
then the system shall return **401 Unauthorized** when `GET /portfolios/{portfolio_id}/share/stats` is called.

---

## 5. 기술 설계 (Technical Design)

### 5.1 DB 마이그레이션 — 0027

- 파일: `backend/alembic/versions/0027_share_view_stats_043.py`, `down_revision = "0026"` (SPEC-042 `portfolio_shares`/`portfolio_likes`).
- 신규 테이블 `share_view_stats`:
  - `id` INT PK autoincrement
  - `share_id` INT, FK → `portfolio_shares.id` `ON DELETE CASCADE`, NOT NULL
  - `stat_date` DATE, NOT NULL
  - `view_count` INT, NOT NULL, default 0
  - `UNIQUE(share_id, stat_date)` (upsert 충돌 키, 이름 `uq_share_view_stats_share_date`)
  - 인덱스: `(share_id, stat_date)` 조회 최적화(UNIQUE 제약으로 충당)
- `notifications` 테이블은 **변경하지 않는다**(`portfolio_like` 는 기존 스키마 재사용, `type` VARCHAR(20) 에 적합).

### 5.2 모델 (models.py)

- 신규 `ShareViewStat(Base)` 모델 추가(필드는 5.1과 동일). `PortfolioShare` 에 `view_stats` relationship(`cascade="all, delete-orphan"`, `lazy="noload"`) 선택 추가.
- `Notification.type` 주석에 `portfolio_like` 추가(문서화 목적, 스키마 변경 아님).

### 5.3 서비스 계층 (portfolio/sharing.py 확장)

- `unlike_shared_portfolio(db, share_token, user_id) -> None`
  - 공유 레코드 로드 → 없거나 `is_public=False` 면 404(HTTPException). 소유자면 403. 그 외 `portfolio_likes` 에서 `(portfolio_id, user_id)` 행 삭제(없으면 no-op). 항상 멱등.
- `like_shared_portfolio(...)` 확장: 신규 좋아요 적재(`portfolio_likes` INSERT 성공) 직후에만 알림 적재 헬퍼 호출. 중복(IntegrityError 무시 경로)에서는 호출하지 않음.
- `_create_like_notification(db, owner_id, portfolio_id, portfolio_name, liker_username)`:
  - `Notification(type="portfolio_like", user_id=owner_id, krx_code=f"P{portfolio_id}", ref_date=<KST today>, title=f"{liker_username}님이 회원님의 포트폴리오를 좋아합니다", body=f"포트폴리오 '{portfolio_name}'에 좋아요를 받았습니다")` 적재.
  - `uq_notification_user_type_code_date` 충돌 시 **IntegrityError-안전**(nested transaction/savepoint) 처리. 좋아요 자체 트랜잭션을 깨지 않음.
- `get_public_shared_portfolio(...)` 확장: 기존 `view_count` 원자적 증가 직후 `share_view_stats` upsert (ON CONFLICT DO UPDATE SET view_count = view_count + 1). `stat_date` 는 KST 기준 오늘 날짜.
- `get_share_view_stats(db, portfolio_id, user_id) -> list[dict]`:
  - 소유권 검증(비소유 404, 비인증은 FastAPI 의존성 401). 공유 레코드 없으면 7일 전부 0. 있으면 최근 7일 윈도우를 생성해 `share_view_stats` 조회 결과를 매핑, 빈 날짜 0 채움, 날짜 asc 정렬.

### 5.4 라우터 변경

- `portfolio/public_router.py`(prefix `/shared`): `DELETE /shared/{share_token}/like` 추가 — `get_current_user` 의존성(401 자동), 서비스 위임(403/404/204).
- `portfolio/router.py`(prefix `/portfolios`, 소유자 전용): `GET /portfolios/{portfolio_id}/share/stats` 추가 — `get_current_user` + 소유권 검증, `ShareStatsResponse` 반환.

### 5.5 스키마 (portfolio/schemas.py)

- `ShareViewStatItem`: `date: date`, `view_count: int`.
- `ShareStatsResponse`: `stats: list[ShareViewStatItem]` (`ConfigDict(from_attributes=True)`).
- `LikeResponse`(기존, SPEC-042) 재사용 — 취소는 본문 없는 204 이므로 응답 스키마 불필요.

### 5.6 프론트엔드

- `frontend/src/api/sharing.ts`(신규 또는 기존 `api/feed.ts` 확장): `unlikeSharedPortfolio(shareToken)`, `getShareStats(portfolioId)` 함수 추가.
- `SharePanel.tsx`: 소유자에게 최근 7일 조회 통계(소형 리스트/막대)를 표시하는 링크/섹션 추가.
- `SharedPortfolio.tsx`: 좋아요 버튼을 좋아요/취소 토글 상태로 전환(이미 좋아요 시 취소 버튼 노출).
- 신규 페이지 없음 — 통계는 `SharePanel` 내 표시.

---

## 6. 테스트 목록 (Test List)

- 파일: `backend/tests/unit/test_share_social_043.py` (TDD RED → GREEN → REFACTOR, 예상 ~23 테스트)

| ID | 테스트 | 검증 REQ / AC |
|----|--------|---------------|
| T-043-001a | 좋아요 취소 성공 → 204 | REQ-SHARE-031 / AC-001a |
| T-043-001b | 좋아요 취소 성공 → like row 삭제 확인 | REQ-SHARE-031 / AC-001b |
| T-043-001c | 좋아요 취소 성공 → like_count 감소 | REQ-SHARE-031 / AC-001c |
| T-043-002 | 좋아요 없는 취소 → 멱등 204 (404 아님) | REQ-SHARE-032 / AC-002 |
| T-043-003 | 소유자 취소 → 403 | REQ-SHARE-033 / AC-003 |
| T-043-004 | 비인증 취소 → 401 | REQ-SHARE-034a / AC-004 |
| T-043-005 | 비공개 포트폴리오 취소 → 404 | REQ-SHARE-034b / AC-005 |
| T-043-006 | 신규 좋아요 → portfolio_like 알림 1행 적재 | REQ-SHARE-035 / AC-006 |
| T-043-007a | 중복 좋아요 → 멱등 200 | REQ-SHARE-036 / AC-007a |
| T-043-007b | 중복 좋아요 → 알림 건수 불변 | REQ-SHARE-036 / AC-007b |
| T-043-008a | 자기 좋아요 → 403 | REQ-SHARE-036 / AC-008a |
| T-043-008b | 자기 좋아요(403) → 알림 미발생 | REQ-SHARE-036 / AC-008b |
| T-043-009 | 서로 다른 포트폴리오 좋아요 → 알림 2행 분리 | REQ-SHARE-035 / AC-009 |
| T-043-010a | 좋아요 알림 → unread-count 반영 | REQ-SHARE-037 / AC-010a |
| T-043-010b | 좋아요 알림 → GET /notifications 목록 반영 | REQ-SHARE-037 / AC-010b |
| T-043-010c | 좋아요 알림 읽음 처리 → 정상 동작 | REQ-SHARE-037 / AC-010c |
| T-043-011a | 공개 뷰 2회 → share_view_stats view_count=2 | REQ-SHARE-038a / AC-011a |
| T-043-011b | 공개 뷰 2회 → portfolio_shares.view_count+2 | REQ-SHARE-038a / AC-011b |
| T-043-011c | 비공개 뷰 → share_view_stats 미적재 | REQ-SHARE-038b / AC-011c |
| T-043-012 | 통계 조회 → 7개 항목·0 채움·날짜 asc | REQ-SHARE-039a / AC-012 |
| T-043-012b | 공유 레코드 없음 → 7개 항목 전부 0 | REQ-SHARE-039b / AC-012b |
| T-043-013 | 비소유자 통계 조회 → 404 | REQ-SHARE-040a / AC-013 |
| T-043-014 | 비인증 통계 조회 → 401 | REQ-SHARE-040b / AC-014 |

품질 게이트: 신규 코드 단위 테스트 커버리지 ≥ 85%, Ruff 린트 통과, 신규 외부 의존성 0.

---

## 7. 의존성 (Dependencies)

- **SPEC-STOCK-042** (포트폴리오 공유 & 소셜): `portfolio_shares`·`portfolio_likes` 테이블, `portfolio/sharing.py` 서비스, `/shared`·`/portfolios/{id}/share` 라우터, `LikeResponse` 스키마 — 본 SPEC 의 직접 확장 대상.
- **SPEC-STOCK-013** (알림 인박스): `Notification` 모델 + `uq_notification_user_type_code_date` 제약, `notifications/inbox_router.py`(`GET /notifications`·`unread-count`·읽음 처리) — 좋아요 알림 적재·노출에 재사용.
- 인증: `auth/dependencies.py` `get_current_user`.
- 마이그레이션 체인: 0027 (down_revision=0026).

---

## 8. 기술 제약 (Technical Constraints)

- Python 3.12+, FastAPI async 엔드포인트, SQLAlchemy 2.x **동기 `Session` 패턴**(AsyncSession 아님 — SPEC-042 패턴 일관).
- `like_count` 는 `portfolio_likes` COUNT 파생(비정규화 카운터 없음) — 취소는 행 삭제만으로 카운트가 감소한다(별도 카운터 갱신 불필요).
- `view_count`(portfolio_shares)는 기존 누적 카운터 유지, 신규 `share_view_stats.view_count` 는 일별 카운터.
- 알림 적재는 좋아요 트랜잭션을 깨지 않도록 savepoint/IntegrityError-안전 처리 — 알림 충돌이 좋아요 성공(200)을 롤백시키지 않아야 한다.
- `stat_date` 는 KST(Asia/Seoul) 기준 오늘 날짜 — 자정 경계에서 일관성 보장.
- Ruff 린트 통과, 신규 외부 의존성 금지, 모든 신규 코드 단위 테스트 필수(TDD).
