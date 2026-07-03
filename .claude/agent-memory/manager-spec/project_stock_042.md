---
name: project-stock-042
description: SPEC-STOCK-042 포트폴리오 공유 & 소셜 — 공유 링크·조회/좋아요·디스커버리 피드, 신규 마이그 0026(테이블 2개)
metadata:
  type: project
---

SPEC-STOCK-042 = 포트폴리오 공유 & 소셜 (Portfolio Sharing & Social). status draft, version 0.1.0, branch feature/SPEC-STOCK-036.

**핵심 사실:**
- 신규 마이그레이션 **0026**(`backend/alembic/versions/0026_portfolio_shares_042.py`), down_revision=`0025`(SPEC-041 portfolio_goals). 신규 테이블 **2개**: `portfolio_shares`(id, portfolio_id FK CASCADE, share_token VARCHAR(32) UNIQUE, is_public bool default False, view_count int default 0, created_at, updated_at; portfolio_id UNIQUE 인덱스=포트폴리오당 공유 1행)·`portfolio_likes`(id, portfolio_id FK, user_id FK, created_at, UNIQUE(portfolio_id,user_id)).
- **share_token = `secrets.token_urlsafe(16)`**(22자) — 작업지시 헤더의 "UUID"는 부정확, VARCHAR로 정의. `like_count`는 비정규화 없이 portfolio_likes COUNT 파생, `view_count`만 누적 카운터.
- 신규 서비스 `portfolio/sharing.py`(goals.py 형제). 소유자 엔드포인트=`portfolio/router.py` 확장(prefix `/portfolios`), 공개 엔드포인트=신규 라우터 prefix `/shared`·`/feed`(무인증).
- 엔드포인트: POST/DELETE/GET `/portfolios/{id}/share`(소유자, 비소유자 404), GET `/shared/{token}`(무인증, view_count+1), POST `/shared/{token}/like`(인증필수, 멱등, 자기좋아요 403, 비인증 401, 비공개 404), GET `/feed`(무인증, sort=likes|recent, page/size, size max 100).
- REQ 접두사 **REQ-SHARE-001~011**. AC-1~13. T-001~T-012. 스키마: ShareCreate/ShareResponse/SharePublicResponse/LikeResponse/FeedItem/FeedResponse(전부 from_attributes=True). 프론트: SharePanel.tsx·Feed.tsx·SharedPortfolio.tsx·api/feed.ts.
- 재사용: 성과=portfolio/service.py, 목표진척도=SPEC-041 portfolio/goals.py(공개뷰 goal_progress), 인증=auth/dependencies.py get_current_user.
- **제외**: 팔로우/팔로워·댓글·좋아요알림·복제/포크·WebSocket실시간·unlike·신규알림채널·신규라이브러리·조회이력시계열. + 자동매매(영구).
- **spec.md 단일 파일만 작성**(plan.md·acceptance.md 미작성 — 본 요청 한정).
- 공개뷰 NFR: 소유자 user_id·이메일 미노출(익명화), view_count는 원자적 증분(UPDATE +1).
