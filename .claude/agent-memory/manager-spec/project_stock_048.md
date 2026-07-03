---
name: project-stock-048
description: SPEC-STOCK-048 공유 포트폴리오 댓글 대댓글(스레드) — 046 확장, self-FK 컬럼 1개(마이그 0029), 알림 규약 재사용으로 047 딥링크 자동
metadata:
  type: project
---

SPEC-STOCK-048 — 공유 포트폴리오 댓글 대댓글 (Threaded Comment Replies). 소셜 아크(042~047) 후속, [[project-stock-046]](댓글)+[[project-stock-047]](딥링크) 완결.

**Why:** 평면 댓글(046)만으로는 대화가 끊김. 소유자가 딥링크(047)로 이동해도 답글로 응답할 수단이 없었음. 1단계 스레딩으로 소셜 루프 완성.

**How to apply (구현 시 핵심 제약):**
- **신규 테이블 0개**. 기존 `portfolio_comments` 에 nullable self-FK `parent_comment_id`(→portfolio_comments.id, ondelete CASCADE) 컬럼 1개 추가 = **마이그레이션 0029**(down_revision 0028). NULL=최상위, 값=답글.
- **댓글 서비스는 sync**(`sharing.add_comment`/`list_comments`/`remove_comment`, `db: Session`). inbox_router(047)는 async — 절대 호출 금지(sync/async 혼용 금지).
- **1단계 스레딩 강제**: 부모는 반드시 최상위(parent IS NULL). 답글에 답글 시도 → 거부(REQ-REPLY-005). 다른 공유의 부모 → 거부(004). 없는 부모 → 404(003).
- **알림 규약 재사용**: 답글 알림 = `type="portfolio_comment"` + `krx_code=f"P{portfolio.id}"` + `ref_date`(일별 멱등). 신규 타입/배지 안 만듦 → **047 딥링크가 inbox_router 변경 없이 자동 동작**. 답글은 **부모 댓글 작성자**에게만 알림(자기답글 무알림 009). 답글 경로에서 소유자 추가 알림 안 만듦(중복 방지). 최상위 댓글의 소유자 알림(046)은 유지.
- **조회**: `list_comments` 는 최상위만 페이지네이션(total=최상위 count, 007), 각 최상위에 `replies`(오래된순 asc, 006) 배열 포함. 답글은 최상위 id 집합 단일 배치 쿼리로 N+1 회피.
- **CASCADE**: 최상위 삭제 시 self-FK CASCADE 로 답글 물리 삭제(placeholder 없음, REQ-REPLY-010).
- **프론트**: `SharedPortfolio.tsx`(+.js), `feed.ts`(+.js) — `postComment(token, content, parentCommentId?)`. 댓글별 답글 폼·중첩 렌더. `.js`/`.ts` 페어 동기화 필수.
- **주의**: 046 CHANGELOG 는 portfolio_comments 에 deleted_at/updated_at 있다고 적었으나 실제 마이그 0028·모델에는 **없음(하드 삭제)**. 048 은 하드삭제+CASCADE 전제.

REQ 15(REQ-REPLY-001~015)·AC 12·테스트 12. 프로젝트 관례상 파일은 spec.md 단일(+run 시 progress.md). 자체 감사 PASS(D1 traceability 4건 세션 내 수정).
