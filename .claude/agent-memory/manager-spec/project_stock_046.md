---
name: project-stock-046
description: SPEC-STOCK-046 공유 포트폴리오 댓글 — 소셜 아크(042~045) 텍스트 상호작용 확장, 신규 테이블 1개(0028)
metadata:
  type: project
---

SPEC-STOCK-046 = 공유 포트폴리오 댓글 (Shared Portfolio Comments).

소셜/디스커버리 아크 연속: 042(공유+좋아요) → 043(좋아요 알림+조회통계) → 044(소셜 FE) → 045(트렌딩/검색) → **046(댓글)**. 좋아요는 단일 비트뿐 → 텍스트 피드백 수단 추가가 동기.

**진짜 신규:**
- 신규 테이블 `portfolio_comments`(마이그 `0028_portfolio_comments_046.py`, down_rev=`0027`): id PK, **share_id FK portfolio_shares.id CASCADE**(좋아요와 동일하게 portfolio_id 아닌 share_id 참조), user_id FK users.id CASCADE, content String(500) NOT NULL, created_at TIMESTAMPTZ. 인덱스 (share_id, created_at). **UNIQUE 제약 없음**(다중 댓글 허용).
- `PortfolioComment` 모델(models.py, PortfolioLike 형제) + PortfolioShare.comments 관계(lazy noload).
- 서비스(portfolio/sharing.py): `add_comment`/`list_comments`/`remove_comment`(좋아요 함수 형제).
- 라우터(portfolio/public_router.py): `GET /shared/{token}/comments`(무인증 목록), `POST /shared/{token}/comments`(인증 작성), `DELETE /shared/{token}/comments/{comment_id}`(인증, 작성자 또는 소유자 삭제).
- 스키마: CommentCreate(Field min_length=1,max_length=500+strip→422), CommentItem, CommentListResponse.
- 알림: 비소유자 댓글 시 `Notification(type="portfolio_comment", krx_code=f"P{portfolio.id}", ref_date=today)` — **add_like 패턴 재사용, UNIQUE(user_id,type,krx_code,ref_date)로 일별 멱등**(하루 1건). 소유자 자기댓글=알림 미생성. portfolio_like와 type 달라 UNIQUE 충돌 없음.
- FE: SharedPortfolio.tsx 댓글 목록·작성폼(로그인시)·본인댓글 삭제컨트롤, feed.ts getComments/addComment/deleteComment, Notifications.tsx TypeBadge에 portfolio_comment='댓글'(파랑).

**REQ 접두사 신규 `REQ-COMMENT-001~021`**(좋아요 REQ-LIKE·피드 REQ-FEED 충돌회피). AC-046-001~018(18개). 테스트 18개(test_comments_046.py + comments_046.test.tsx).

**비자명 사실:**
- `PortfolioLike`/`PortfolioComment`는 portfolio_id 아닌 **share_id** 참조(공유 비활성화 시 정리, 무공유엔 댓글 불가).
- 댓글 알림은 일별 1건(좋아요와 동일 멱등) — 댓글 폭주해도 알림 1건. 의도된 동작(REQ-COMMENT-016).
- FE 삭제컨트롤=본인 댓글만(소유자 모더레이션 삭제는 백엔드만, FE 미노출 — 의도적 범위 한정).
- 공개뷰 무인증 가능, POST/DELETE만 get_current_user 보호(SPEC-044 패턴).

**제외:** 자동매매(영구)·대댓글/스레드·댓글좋아요/반응·댓글수정·신고/차단/스팸필터·알림딥링크·이메일/텔레그램 댓글알림·피드 comment_count 노출·마크다운/이미지·무한스크롤/실시간·비로그인 본인댓글 영속식별.

단일 spec.md(작업지시 명시). 마이그레이션 최신=0028.

관련: [[stock-picker-spec-conventions]] [[project_stock_043]] [[project_stock_044]] [[project_stock_045]]
