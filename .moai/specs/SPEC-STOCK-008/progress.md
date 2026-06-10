# SPEC-STOCK-008 진행 상황 (Progress)

- SPEC: SPEC-STOCK-008 — 섹터 분석 대시보드
- 상태: draft (계획 완료, 구현 미착수)
- 생성일: 2026-06-10
- 작성자: ircp

---

## 작업 진행률

전체: 0 / 12 완료 (0%)

| TASK | 설명 | 우선순위 | 상태 |
|------|------|----------|------|
| TASK-001 | `(sector, trade_date)` UNIQUE 제약 마이그레이션 (0011) | High | pending |
| TASK-002 | 섹터 집계 서비스 구현 | High | pending |
| TASK-003 | 섹터 집계 upsert 저장 | High | pending |
| TASK-004 | 파이프라인 연결 + 캐시 무효화 | High | pending |
| TASK-005 | 섹터 순위 API (`GET /sectors/ranking`) | High | pending |
| TASK-006 | 섹터 상세 API (`GET /sectors/{sector}/detail`) | High | pending |
| TASK-007 | 백엔드 단위·통합 테스트 | High | pending |
| TASK-008 | 섹터 API 클라이언트 + 타입 | Medium | pending |
| TASK-009 | `/sectors` 페이지 — 순위 표 + 비교 차트 | Medium | pending |
| TASK-010 | 섹터 상세 패널 (구성 종목 + 추세) | Medium | pending |
| TASK-011 | 라우팅 + NavBar 링크 + 반응형 | Medium | pending |
| TASK-012 | 프론트엔드 테스트 + 문서 갱신 | Low | pending |

---

## 인수 기준 진행률

전체: 0 / 13 통과 (0%)

| AC | 설명 | 상태 |
|----|------|------|
| AC-1 | 분석 완료 시 섹터 집계 적재 | pending |
| AC-2 | 다중 섹터 태깅 처리 | pending |
| AC-3 | 장중 재실행 시 upsert (중복 방지) | pending |
| AC-4 | 분석 결과 없음 처리 | pending |
| AC-5 | 집계 실패가 추천을 막지 않음 | pending |
| AC-6 | 집계 후 캐시 무효화 | pending |
| AC-7 | 섹터 순위 조회 | pending |
| AC-8 | 섹터 상세 조회 | pending |
| AC-9 | 존재하지 않는 섹터 | pending |
| AC-10 | 섹터 비교 화면 표시 | pending |
| AC-11 | 데이터 미적재 안내 상태 | pending |
| AC-12 | 네비게이션 + 반응형 | pending |
| AC-13 | 하위 호환 (회귀 없음) | pending |

---

## 마일스톤 (우선순위 기반)

1. **섹터 집계 생산자 (High)**: TASK-001 → TASK-002 → TASK-003 → TASK-004
   — 기존 `sector_trends` 인프라를 실제로 동작시키는 핵심.
2. **섹터 분석 API (High)**: TASK-005, TASK-006, TASK-007
3. **섹터 비교 화면 (Medium)**: TASK-008 → TASK-009 → TASK-010 → TASK-011
4. **마무리 (Low)**: TASK-012 (테스트·문서)

---

## 핵심 메모

- 본 SPEC의 동기: `SectorTrend` 모델·`GET /sectors/trends` API·프론트 `SectorTrendChart`는
  존재하나 **데이터 생산자가 없어** 섹터 차트가 항상 비어 있음. 생산자 구현이 1순위 가치.
- 마이그레이션 누적: 0001~0010 다음 0011.
- 영구 제외: 자동 매매. 본 SPEC 범위 밖: 피드백 기반 재가중, 섹터 알림/구독.
