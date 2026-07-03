---
name: project-stock-045
description: SPEC-STOCK-045 피드 디스커버리 강화 — /feed 에 트렌딩 정렬(7일 조회합계)·이름 검색(q) 추가. SPEC-043 share_view_stats(0027) 재사용, 신규 마이그 없음
metadata:
  type: project
---

SPEC-STOCK-045 = 피드 디스커버리 강화 (Feed Discovery Enhancement). status draft, version 0.1.0, branch feature/SPEC-STOCK-036. 소셜 아크(042~044) 후속 — 공개 디스커버리 피드(`GET /feed`) 발견성 강화.

**Why:** 피드 정렬이 recent/likes 뿐이라 최근 화제성 미반영 + 검색 수단 부재. 이미 수집 중인 일별 조회 데이터를 활용해 추가비용 없이 트렌딩 노출, 이름검색으로 탐색성 개선.

**2 기능:** (1)트렌딩 정렬 `sort=trending` = `share_view_stats` 최근 7일 `view_count` 합계 내림차순 (2)이름 검색 `q` = `Portfolio.name.ilike("%q%")` 대소문자 무시 부분일치. 둘 다 기존 정렬·페이지네이션과 결합.

**핵심 비자명 사실:**
- **신규 DB/마이그레이션 0** — SPEC-043 `share_view_stats`(마이그 0027) + `ShareViewStat` 모델 재사용. 최신 마이그 0027 유지. `FeedItem` 응답 스키마 불변(변경 없음).
- **트렌딩 폴백 무비용**: `get_feed`(sharing.py:390-453) 의 기존 `if likes ... else recent` 구조에서 알 수 없는 sort 는 자동으로 else→recent 로 떨어짐 → REQ-FEED-006(invalid sort→recent, no error) 추가 코드 거의 불필요.
- **트렌딩 서브쿼리**: `func.sum(ShareViewStat.view_count)` group by share_id + `outerjoin` + `func.coalesce(...,0).desc()` (기존 like_count 서브쿼리 패턴과 동형). 조회이력 없는 항목 score=0 으로 누락 없이 후순위.
- **7일 윈도 = KST**, SPEC-043 `get_share_stats`(sharing.py:334-)와 동일 기준일.
- **트렌딩은 view_count만** — `share_view_stats` 의 per-day `like_count` 는 트렌딩 점수 미반영(Out-of-Scope).
- **프론트 .tsx/.ts + .js 빌드 페어** 동기화 필수: `feed.ts`(getFeed 에 'trending' 유니온·선택적 q)·`Feed.tsx`(검색폼·트렌딩 토글·정렬/검색 변경시 page=1 리셋). 빈/undefined q 는 쿼리 파라미터 미포함. 백엔드 Python 은 페어 없음.
- **q 검색은 단순 ILIKE substring** — 전문검색·퍼지·형태소·인덱스 추가 없음. 포트폴리오에 카테고리 필드 없어 카테고리 필터 제외.

**수정 파일**: backend sharing.py(get_feed에 q·trending), public_router.py(get_sharing_feed에 q Query). frontend feed.ts·Feed.tsx(+각 .js). 테스트=backend/tests/unit/test_feed_discovery_045.py(pytest) + frontend/src/__tests__/feed_discovery_045.test.tsx(vitest+RTL).

**REQ 접두사 REQ-FEED-002~010(9개)** — SPEC-042 REQ-FEED-001(피드 도입)에 이어. 피드 도메인은 REQ-FEED(공유=REQ-SHARE, 통계=REQ-STAT 와 구분). **AC-045-001~015 아님 → AC-045-001~012(12개)**. T-045-001~012. plan-auditor self-audit(review-1) **PASS 0.97** — D1(트렌딩 윈도 KST 명시) 해소, D2(REQ 이중 SHALL, 044 선례와 일치하여 허용).

**제외**: 자동매매(영구)·신규 DB/마이그(0027 재사용)·카테고리/태그 필터·전문검색/퍼지·좋아요 기반 트렌딩·개인화 피드·무한스크롤/WebSocket·검색 디바운스 강제·알림 딥링크·이메일/텔레그램.

**의존성**: SPEC-042(/feed·get_feed·FeedItem·Feed.tsx·feed.ts), SPEC-043(share_view_stats 0027·ShareViewStat·7일 집계 패턴).

**spec.md 단일 파일만 작성**(plan/acceptance 미작성 — 본 요청 한정).
