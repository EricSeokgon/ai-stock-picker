# Plan Audit — SPEC-STOCK-045 (Review 1)

- **SPEC**: SPEC-STOCK-045 — 피드 디스커버리 강화 (트렌딩 정렬 & 이름 검색)
- **Date**: 2026-06-30
- **Auditor**: manager-spec (self-audit)
- **Verdict**: PASS (0.97)

## 1. EARS Compliance

| Item | Result | Note |
|------|--------|------|
| REQ event/state/unwanted keywords | PASS | REQ-FEED-002/004/007/008/009 = Event-driven(When...SHALL); REQ-FEED-005 = Event(When absent/empty...SHALL); REQ-FEED-006/010 = Unwanted(If...then SHALL); REQ-FEED-003 = Event(When no records...SHALL) |
| AC event/unwanted form | PASS | 12 AC 모두 When.../If...then... 형식 |
| Observable behavior | PASS | 정렬 순서·반환 개수·요청 파라미터 등 외부 관찰 가능 동작으로 기술 |

## 2. Single SHALL per AC (Atomic)

| Item | Result | Note |
|------|--------|------|
| AC 단일 SHALL | PASS | AC-045-001~012 전부 단일 SHALL(검증 동작 1개). 복합 동작은 REQ→다중 AC 로 분해 |
| REQ 복합 SHALL | ACCEPT | REQ-FEED-003/006/008/009 는 이중 SHALL(긍정+부정 또는 요청+렌더). SPEC-044 REQ-SHARE-043 선례와 일치하는 허용 패턴. 각 REQ 는 단일 응집 동작을 표현하며 AC 단계에서 원자화됨 |

## 3. REQ Numbering Continuity

| Item | Result | Note |
|------|--------|------|
| REQ-FEED 연속성 | PASS | SPEC-042 = REQ-FEED-001(피드 도입) → 본 SPEC = REQ-FEED-002~010. 중복·누락 없음(grep 확인: 기존 REQ-FEED-001 유일) |
| AC 넘버링 | PASS | AC-045-001~012 연속, REQ 매핑 명시 |
| 접두사 일관성 | PASS | 피드 도메인은 REQ-FEED 접두사 사용(공유=REQ-SHARE, 통계=REQ-STAT 와 구분) |

## 4. Completeness

| Section | Result |
|---------|--------|
| 1. Overview + Why | PASS |
| 2. Scope (In/Out) | PASS — Out-of-Scope 9항목, 자동매매 영구 제외 명시 |
| 3. Requirements (EARS) | PASS — 9 REQ |
| 4. Acceptance Criteria | PASS — 12 AC, REQ 역추적 |
| 5. Technical Approach | PASS — 백엔드/프론트/빌드페어 |
| 6. Test Plan | PASS — 12 테스트, REQ/AC 매핑 |
| 7. Dependencies | PASS — SPEC-042/043 |
| 8. Constraints | PASS |

## 5. Consistency with Codebase (Verified)

- `GET /feed` = `get_sharing_feed`(public_router.py:77-93), `sort=recent|likes` 기존 → `trending` 추가 가능, else→recent 폴백 경로 존재(REQ-FEED-006 무비용 충족).
- `get_feed`(sharing.py:390-453) = PortfolioShare⋈Portfolio, like_count 서브쿼리 패턴 존재 → 동일 패턴으로 trending 서브쿼리 구성 가능.
- `ShareViewStat`(share_view_stats, 마이그 0027) = share_id+stat_date+view_count, 7일 윈도 집계는 `get_share_stats`(sharing.py:334-) 선례 존재 → 재사용 타당. 신규 마이그레이션 불필요 확인.
- `FeedItem` 필드 불변 → 응답 스키마 변경 없음 확인.
- 프론트 `Feed.tsx`(sort 'likes'|'recent' state, getFeed(sort,page,size)) + `feed.ts`(getFeed) → q·trending 확장 지점 확인.

## 6. Defects & Resolutions

| ID | Severity | Description | Resolution |
|----|----------|-------------|------------|
| D1 | Minor | 트렌딩 윈도 기준일(KST vs UTC) 모호 가능성 | §1·§5.1·§8 에서 "KST 기준, SPEC-043 통계와 동일 기준일" 로 명시 → 해소 |
| D2 | Info | REQ 이중 SHALL(003/006/008/009) | SPEC-044 선례와 일치, AC 단계 원자화로 허용 — 변경 불요 |

## 7. Verdict

PASS (0.97). EARS 준수, AC 단일 SHALL, REQ-FEED 연속성, 코드베이스 정합성, 자동매매 영구 제외·신규 마이그레이션 0 확인. 구현(Run) 진행 가능.
