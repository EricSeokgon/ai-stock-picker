---
name: project-stock-044
description: SPEC-STOCK-044 포트폴리오 소셜 프론트엔드 완성 — SPEC-043 백엔드의 프론트 미연동분(unlike 토글·7일 조회통계 패널·portfolio_like 알림 뱃지). 프론트 전용, 신규 마이그 없음
metadata:
  type: project
---

SPEC-STOCK-044 = 포트폴리오 소셜 프론트엔드 완성 (Social Frontend Completion). status draft, version 0.1.0, branch feature/SPEC-STOCK-036. **프론트엔드 전용 SPEC** — SPEC-043 이 백엔드만 출시(CHANGELOG 0.43.0)하고 미룬 프론트 연동분 완성.

**Why:** SPEC-043 백엔드(DELETE unlike, GET share/stats 7일, portfolio_like 알림)는 머지됐으나 프론트 미연동 — 좋아요 취소 UI 없음·일별 조회추이 미표시·알림 뱃지에 원시 "portfolio_like" 노출.

**3 기능:** (1)좋아요/취소 토글(SharedPortfolio) (2)소유자 7일 조회통계 패널(SharePanel) (3)portfolio_like 알림 뱃지 라벨 "좋아요"(Notifications).

**핵심 비자명 사실:**
- **신규 백엔드/DB/마이그레이션 0** — 마이그 최신 0027 유지. 신규 외부 의존성·차트 라이브러리 금지. 기존 SPEC-042/043 API만 호출.
- **좋아요 토글은 세션-로컬 옵티미스틱 상태**: `GET /shared/{token}`는 **무인증**이라 `SharePublicResponse`에 `liked_by_me` 없음(스키마 확인됨 schemas.py:918-929) → 서버가 현재 사용자 좋아요 여부 제공 불가. 초기 `liked=false`, POST 성공→liked=true·"좋아요 취소", DELETE 204 성공→liked=false·"좋아요"·count-1. **응답-확정 후 상태변경**(옵티미스틱 즉시전환 금지, 실패 시 서버와 어긋남 방지).
- **일별 통계는 view_count만**: `ShareViewStatItem`=`{date, view_count}`(schemas.py:965-969, sharing.py:384). per-day like_count 미제공 → 통계에 좋아요 시계열 표시 제외(CHANGELOG가 "좋아요수 추이" 언급했으나 실제 서비스는 view_count만 반환).
- **프론트 구조**: `.tsx/.ts` 소스 + 커밋된 `.js` 빌드 산출물 **페어**. 수정한 모든 소스의 `.js`도 함께 갱신 필수. `feed.ts`엔 `likeSharedPortfolio`만 있고 `unlikeSharedPortfolio`/`getShareStats` 없음(추가 대상). `Notifications.tsx` `TypeBadge`는 price_alert/rec_new/rec_dropped만 매핑(portfolio_like 추가 대상).
- **수정 파일**: api/feed.ts(`unlikeSharedPortfolio`), api/portfolio.ts(`getShareStats`), pages/SharedPortfolio.tsx(토글), components/SharePanel.tsx(통계패널), pages/Notifications.tsx(뱃지) + 각 .js 페어. 테스트=`frontend/src/__tests__/social_frontend_044.test.tsx`(vitest+RTL).

**REQ 접두사 REQ-SHARE-041~049**(042=001~011, 043=031~040에 이어). **AC-044-001~015(15개)**. T-044-001~015. plan-auditor self-audit(review-1) **PASS 0.97** — D1(REQ/AC에 getShareStats 함수명 노출→엔드포인트 표현으로 수정) 해소.

**제외**: 자동매매(영구)·신규 백엔드/DB/마이그·공개뷰 liked_by_me 추가·per-day like_count 표시·차트 라이브러리·WebSocket·알림 딥링크 네비·이메일/텔레그램·Feed 페이지 변경.

**의존성**: SPEC-043(unlike/stats/알림 백엔드), SPEC-042(feed.ts·SharedPortfolio·SharePanel), SPEC-013(Notifications·markNotificationRead), auth/AuthContext.

**spec.md 단일 파일만 작성**(plan/acceptance 미작성 — 본 요청 한정).
