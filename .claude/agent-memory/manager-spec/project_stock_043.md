---
name: project-stock-043
description: SPEC-STOCK-043 공유 포트폴리오 알림 & 소셜 확장 — unlike·좋아요 인앱 알림·조회수 일별 통계, 신규 마이그 0027(테이블 1개)
metadata:
  type: project
---

SPEC-STOCK-043 = 공유 포트폴리오 알림 & 소셜 확장 (Portfolio Share Notification, Unlike & View Stats). status draft, version 0.1.0, branch feature/SPEC-STOCK-036. SPEC-042 후속(042가 Out-of-Scope로 명시했던 항목).

**Why:** SPEC-042 공유/좋아요/피드 도입 후 (1)좋아요 취소 불가, (2)소유자 좋아요 수신 인지 불가, (3)일별 조회 추이 부재 — 3 공백을 메움.

**How to apply:** SPEC-043 작업 시 spec.md만 작성됨(plan/acceptance 미작성, 본 요청 한정). 후속 042/043 확장 SPEC은 REQ-SHARE-041부터 부여.

**핵심 사실:**
- 신규 마이그 **0027**(`backend/alembic/versions/0027_share_view_stats_043.py`), down_revision=`0026`(SPEC-042). 신규 테이블 **1개** `share_view_stats`(id, share_id FK→portfolio_shares.id CASCADE, stat_date DATE, view_count INT default 0, UNIQUE(share_id, stat_date)=`uq_share_view_stats_share_date`). notifications 테이블 변경 없음.
- REQ 접두사 **REQ-SHARE-031~040**(042의 001~011에 이어). AC-043-001~014(14개). T-043-001~014(`backend/tests/unit/test_share_social_043.py`).
- **3 기능**: (1)Unlike `DELETE /shared/{token}/like`(인증필수, 멱등=좋아요없어도 204·404아님, 소유자 403, 비인증 401, 비공개 404). (2)좋아요 인앱 알림(신규좋아요만, 중복·자기좋아요 미발생, 기존 `/notifications` 인박스 재사용). (3)조회수 일별통계(공개뷰시 share_view_stats upsert, `GET /portfolios/{id}/share/stats` 소유자전용 최근7일·0채움·날짜asc, 비소유 404).
- **핵심 설계 결정(알림 UNIQUE 충돌)**: `notifications`의 `uq_notification_user_type_code_date(user_id,type,krx_code,ref_date)` 제약 때문에 작업지시의 `krx_code=""`는 모든 포트폴리오 좋아요 알림이 1행으로 붕괴됨. → **krx_code=`f"P{portfolio_id}"`**(VARCHAR(10) 이내), ref_date=KST today로 변경. 동일포트·동일일자 중복좋아요 알림은 1건 dedup(스팸방지). IntegrityError-안전 insert + savepoint(좋아요 200을 롤백시키지 않아야 함).
- 알림 필드: type="portfolio_like", user_id=portfolio.user_id(소유자), title=f"{liker_username}님이 회원님의 포트폴리오를 좋아합니다", body=f"포트폴리오 '{portfolio_name}'에 좋아요를 받았습니다".
- `like_count`=portfolio_likes COUNT 파생(비정규화 없음) → unlike는 행 삭제만으로 감소. 동기 Session 패턴(AsyncSession 아님).
- 서비스: portfolio/sharing.py 확장(`unlike_shared_portfolio`, `_create_like_notification`, `get_public_shared_portfolio` 통계 upsert 추가, `get_share_view_stats`). 라우터: public_router.py(DELETE like), router.py(GET share/stats). 스키마: ShareViewStatItem·ShareStatsResponse(from_attributes=True), 취소는 204 본문없음.
- 프론트: api/sharing.ts(`unlikeSharedPortfolio`·`getShareStats`), SharePanel.tsx(통계), SharedPortfolio.tsx(좋아요/취소 토글). 신규 페이지 없음.
- **제외**: 좋아요알림 이메일/텔레그램·portfolio_like NotificationPreference opt-out 신설·팔로우/팔로워·댓글·WebSocket·7일초과 이력·신규 의존성/차트라이브러리. + 자동매매(영구).
- 의존성: SPEC-042(공유인프라), SPEC-013(알림인박스), auth/dependencies.py get_current_user.
