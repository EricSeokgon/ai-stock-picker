# SPEC-STOCK-048 Progress

공유 포트폴리오 댓글 대댓글 (Threaded Comment Replies)

## Plan Phase

**Status**: ✓ PASS

- **plan-auditor**: PASS (초안 완료, 1단계 스레딩 강제 외 지적사항 없음)
- **REQ**: 15개 (REQ-REPLY-001~015)
- **AC**: 12개 (AC-048-001~012)
- **설계**: 마이그레이션 0029(컬럼 1개) + ORM 모델 + 서비스 확장 + 프론트엔드 UI

---

## Run Phase

**Status**: ✓ COMPLETE

**Tests**: 12/12 PASS

### Backend (9 tests)
- T-048-001 — 최상위 댓글에 대댓글 작성 → parent_comment_id 저장 ✓
- T-048-002 — 존재하지 않는 parent_comment_id → 404 ✓
- T-048-003 — 다른 공유의 댓글을 부모로 지정 → 거부 ✓
- T-048-004 — 답글을 부모로 지정(2단계 시도) → 거부 ✓
- T-048-005 — 최상위 댓글 + 답글 2개 → replies 오래된순 반환 ✓
- T-048-006 — 최상위 1 + 답글 3 → total=1 (최상위만 카운트) ✓
- T-048-007 — 타인 댓글에 답글 → 부모 작성자에게 알림 생성 ✓
- T-048-008 — 자기 댓글에 답글 → 알림 미생성 ✓
- T-048-009 — 답글 있는 부모 삭제 → 답글 CASCADE 제거 ✓

### Frontend (3 tests)
- T-048-010 — 프론트 최상위 댓글 → 답글 액션 렌더 ✓
- T-048-011 — 프론트 답글 제출 → postComment(token, text, parentId) 호출 ✓
- T-048-012 — 프론트 replies 있는 댓글(신규 답글 포함) → 리로드 없이 중첩 렌더 ✓

**Commit**: 60736da

**Modified Files**:
- `backend/alembic/versions/0029_comment_replies_048.py` — Migration
- `backend/src/stock_picker/db/models.py` — ORM 모델
- `backend/src/stock_picker/portfolio/schemas.py` — Pydantic 스키마
- `backend/src/stock_picker/portfolio/sharing.py` — 서비스 로직 (N+1-free 배치 로딩)
- `backend/src/stock_picker/portfolio/public_router.py` — parent_comment_id 전달
- `backend/tests/unit/test_comment_replies_048.py` — 백엔드 테스트
- `frontend/src/api/feed.ts` / `feed.js` — API 함수 + CommentItem 타입
- `frontend/src/pages/SharedPortfolio.tsx` / `SharedPortfolio.js` — 답글 UI
- `frontend/src/__tests__/comment_replies_048.test.tsx` — 프론트 테스트
- `frontend/vite.config.ts` — TS 소스 우선 해석

---

## Sync Phase

**Status**: ✓ COMPLETE

**Documentation**:
- ✓ CHANGELOG.md — v0.48.0 entry 추가
- ✓ README.md — Phase 48 기능 추가
- ✓ progress.md (this file)

**Commit**: [sync commit hash]

---

## Quality Gate Summary

| 항목 | 결과 |
|------|------|
| Tests | 12/12 PASS |
| Coverage | 85% ↑ |
| ESLint | PASS |
| Ruff | PASS |
| DB Migrations | 1개 (0029) |
| Dependencies | 0개 신규 |
| TRUST 5 | PASS |

---

## Known Constraints

1. **1단계 스레딩만 지원**: 답글의 답글은 불가능 (답글 parent_comment_id 반드시 NULL)
2. **알림 규약 재사용**: `type="portfolio_comment"`, `krx_code=f"P{portfolio.id}"` (신규 타입 없음)
3. **비소유자 대댓글 제외**: 소유자에 대한 추가 알림 없음 (부모 작성자 알림만)
4. **N+1 회피**: 배치 쿼리로 모든 답글 단일 조회
5. **Sync 컨텍스트**: 댓글 서비스는 sync (async 인박스 라우터 미호출)

---

## Revision History

| Date | Action | Notes |
|------|--------|-------|
| 2026-07-01 | Sync Complete | CHANGELOG·README·progress.md 동기화 |
| 2026-07-01 | Run Complete | 12/12 테스트 통과, commit 60736da |
| 2026-07-01 | Plan Complete | SPEC v0.1.0 초안 작성 |
